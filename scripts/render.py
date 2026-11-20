#!/usr/bin/env python3
"""Full-page screenshot of an HTML file for visual review.

Works offline: if the page uses the Tailwind CDN or Google Fonts and they are unreachable,
Tailwind is compiled locally (npx tailwindcss@3, using the page's inline tailwind.config)
and the fonts are inlined from @fontsource packages (npm). Needs Python Playwright and a
Chromium/Chrome binary.

    python3 scripts/render.py page.html --out page.png [--dark] [--width 1440] [--height 900]
"""
import argparse
import base64
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request

CDN = re.compile(r'<script[^>]+src="https://cdn\.tailwindcss\.com[^"]*"[^>]*>\s*</script>')
INLINE_CFG = re.compile(r'<script>\s*tailwind\.config\s*=\s*(\{[\s\S]*?\})\s*;?\s*</script>')
GFONTS = re.compile(r'<link[^>]+fonts\.(?:googleapis|gstatic)\.com[^>]*>')
CACHE = pathlib.Path(os.environ.get('UITOOLS_CACHE', pathlib.Path.home() / '.cache' / 'uitools-render'))


def log(msg):
    print(f"render: {msg}", file=sys.stderr)


def reachable(url):
    try:
        urllib.request.urlopen(url, timeout=4)
        return True
    except Exception:
        return False


def npm(*args):
    CACHE.mkdir(parents=True, exist_ok=True)
    if not (CACHE / 'package.json').exists():
        (CACHE / 'package.json').write_text('{"name":"uitools-render","private":true}')
    return subprocess.run(['npm', *args], cwd=CACHE, capture_output=True, text=True)


def compile_tailwind(html):
    if not shutil.which('npm') or not shutil.which('node'):
        log('npm/node not found; Tailwind classes will be unstyled')
        return html
    if not (CACHE / 'node_modules' / '.bin' / 'tailwindcss').exists():
        r = npm('install', '--silent', 'tailwindcss@3')
        if r.returncode:
            log(f'could not install tailwindcss: {r.stderr.strip()[:200]}')
            return html
    cfg = {}
    m = INLINE_CFG.search(html)
    if m:
        r = subprocess.run(['node', '-e', f'process.stdout.write(JSON.stringify(({m.group(1)})))'],
                           capture_output=True, text=True)
        if r.returncode == 0:
            cfg = json.loads(r.stdout)
        else:
            log('inline tailwind.config could not be evaluated; using defaults')
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d)
        (d / 'page.html').write_text(html, encoding='utf-8')
        (d / 'tailwind.config.js').write_text('module.exports=' + json.dumps({**cfg, 'content': [str(d / 'page.html')]}))
        (d / 'in.css').write_text('@tailwind base;@tailwind components;@tailwind utilities;')
        r = subprocess.run([str(CACHE / 'node_modules' / '.bin' / 'tailwindcss'), '-c', str(d / 'tailwind.config.js'),
                            '-i', str(d / 'in.css'), '-o', str(d / 'out.css'), '--minify'], capture_output=True, text=True)
        if r.returncode:
            log(f'tailwind build failed: {r.stderr.strip()[:200]}')
            return html
        css = (d / 'out.css').read_text()
    html = CDN.sub('', html)
    html = INLINE_CFG.sub('', html)
    return html.replace('</head>', f'<style>{css}</style></head>', 1)


def inline_fonts(html):
    families = set()
    for link in GFONTS.findall(html):
        for fam in re.findall(r'family=([^&:"\']+)', link):
            families.add(fam.replace('+', ' '))
    if not families or not shutil.which('npm'):
        return GFONTS.sub('', html)
    faces = []
    for fam in sorted(families):
        slug = re.sub(r'[^a-z0-9]+', '-', fam.lower()).strip('-')
        pkg = CACHE / 'node_modules' / '@fontsource' / slug / 'files'
        if not pkg.exists() and npm('install', '--silent', f'@fontsource/{slug}').returncode:
            log(f'font {fam} unavailable; falling back to system fonts')
            continue
        for f in sorted(pkg.glob('*-latin*-normal.woff2')):
            w = re.search(r'-(\d{3})-normal', f.name)
            if w and re.search(r'-(latin|latin-ext)-\d', f.name):
                b64 = base64.b64encode(f.read_bytes()).decode()
                faces.append(f"@font-face{{font-family:'{fam}';font-weight:{w.group(1)};font-style:normal;"
                             f"font-display:block;src:url(data:font/woff2;base64,{b64}) format('woff2');}}")
    html = GFONTS.sub('', html)
    return html.replace('</head>', f"<style>{''.join(faces)}</style></head>", 1)


def chrome_path():
    for name in ('google-chrome', 'chromium', 'chromium-browser', 'chrome'):
        p = shutil.which(name)
        if p:
            return p
    return None


CHECK_JS = r"""() => {
  const out = [], vw = innerWidth;
  const where = e => { const c = (e.className && e.className.baseVal === undefined ? String(e.className) : '').trim().split(/\\s+/).slice(0, 3).join('.');
                       return e.tagName.toLowerCase() + (c ? '.' + c : ''); };
  const vis = e => { const r = e.getBoundingClientRect(), cs = getComputedStyle(e);
                     return r.width > 0 && r.height > 0 && cs.display !== 'none' && cs.visibility !== 'hidden'; };
  if (document.documentElement.scrollWidth > vw + 2)
    out.push(['WARN', 'page-overflow-x', `page is ${document.documentElement.scrollWidth}px wide in a ${vw}px viewport (horizontal scrollbar)`]);
  const clipped = [], hidden = [], empty = [], edge = [], blank = [];
  for (const e of document.querySelectorAll('body *')) {
    if (!vis(e)) continue;
    const cs = getComputedStyle(e), tag = e.tagName.toLowerCase();
    if (['script', 'style', 'svg', 'path', 'circle', 'rect', 'g', 'defs', 'stop', 'line', 'polygon', 'polyline', 'ellipse', 'text', 'tspan'].includes(tag)) continue;
    const text = (e.innerText || '').trim();
    if ((cs.overflowX === 'hidden' && e.scrollWidth > e.clientWidth + 3) || (cs.overflowY === 'hidden' && e.scrollHeight > e.clientHeight + 3)) {
      if (text && e.clientHeight > 0 && !cs.textOverflow.includes('ellipsis') && !cs.webkitLineClamp) clipped.push(where(e));
    }
    if ((tag === 'pre' || tag === 'code') && e.scrollWidth > e.clientWidth + 3 && cs.display !== 'inline') clipped.push(where(e) + ' (text runs out of its box)');
    if (text && parseFloat(cs.opacity) === 0 && !e.closest('[aria-hidden=true]')) hidden.push(where(e));
    if ((tag === 'button' || tag === 'a') && !text && !e.querySelector('svg,img,canvas') && !e.getAttribute('aria-label') && !e.getAttribute('title')) empty.push(where(e));
    if (tag === 'button' && text === '' && e.querySelector('svg,img')) {}
    const r = e.getBoundingClientRect();
    if (['img', 'canvas', 'figure'].includes(tag) && r.right > vw + 2 && r.left < vw - 8) edge.push(where(e));
  }
  for (const e of document.querySelectorAll('section, main > div, header, footer')) {
    if (!vis(e)) continue;
    const r = e.getBoundingClientRect();
    if (r.height > 320 && !(e.innerText || '').trim() && !e.querySelector('svg,img,canvas,video,iframe')) blank.push(where(e) + ` (${Math.round(r.height)}px)`);
  }
  const sparse = [];
  for (const e of document.querySelectorAll('div, section, article, aside, pre')) {
    if (!vis(e)) continue;
    const r = e.getBoundingClientRect(), cs = getComputedStyle(e);
    if (r.height < 260 || r.width < 240) continue;
    if (!(parseFloat(cs.borderTopWidth) > 0 || cs.backgroundColor !== 'rgba(0, 0, 0, 0)')) continue;
    if (e.matches('body > div, main, #app, #root') || r.width > innerWidth * 0.9) continue;
    let last = r.top, n = 0;
    for (const c of e.querySelectorAll('*')) { if (!vis(c)) continue; const t = c.children.length === 0 && (c.innerText || '').trim(); if (t || ['svg','img','canvas'].includes(c.tagName.toLowerCase())) { last = Math.max(last, c.getBoundingClientRect().bottom); n++; } }
    if (n && (last - r.top) / r.height < 0.5) sparse.push(where(e) + ` (${Math.round(100 * (last - r.top) / r.height)}% filled)`);
  }
  if (sparse.length) out.push(['WARN', 'empty-panel', `${sparse.length} panel(s) are more than half empty: ${[...new Set(sparse)].slice(0, 4).join(', ')}; fill them (more rows, content) or shrink the panel`]);
  const u = a => [...new Set(a)].slice(0, 5).join(', ');
  if (clipped.length) out.push(['WARN', 'clipped-content', `${clipped.length} element(s) cut off or overflowing: ${u(clipped)}`]);
  if (hidden.length) out.push(['WARN', 'invisible-content', `${hidden.length} element(s) with text but opacity 0 after load and scroll: ${u(hidden)}`]);
  if (blank.length) out.push(['WARN', 'blank-band', `${blank.length} tall section(s) render empty: ${u(blank)}`]);
  if (empty.length) out.push(['WARN', 'empty-control', `${empty.length} button/link without text, icon or label: ${u(empty)}`]);
  if (edge.length) out.push(['INFO', 'edge-clipped-art', `art runs past the right edge: ${u(edge)}; keep the subject fully visible or bleed at least a third of it`]);
  if (!out.length) out.push(['INFO', 'dom-check', 'no layout defects found']);
  return out;
}"""


MOBILE_JS = r"""() => {
  const out = [], vw = innerWidth;
  if (document.documentElement.scrollWidth > vw + 2)
    out.push(['WARN', 'mobile-overflow-x', `page is ${document.documentElement.scrollWidth}px wide at ${vw}px (horizontal scroll)`]);
  const small = [], tiny = [];
  for (const e of document.querySelectorAll('a, button, input, select, textarea, [role=button]')) {
    const r = e.getBoundingClientRect(), cs = getComputedStyle(e);
    if (!r.width || cs.display === 'none' || cs.visibility === 'hidden') continue;
    if ((e.innerText || '').trim().length && r.height < 36 && r.width < 120 && !e.closest('p, li')) small.push((e.innerText || e.tagName).trim().slice(0, 18) + ` (${Math.round(r.width)}x${Math.round(r.height)})`);
  }
  for (const e of document.querySelectorAll('p, li, span, a, button, td')) {
    const cs = getComputedStyle(e);
    if ((e.childNodes[0] && e.childNodes[0].nodeType === 3 && e.textContent.trim().length > 3) && parseFloat(cs.fontSize) < 11) tiny.push(e.textContent.trim().slice(0, 14));
  }
  if (small.length) out.push(['INFO', 'mobile-tap-targets', `${small.length} control(s) under 36px tall: ${small.slice(0, 4).join(', ')}`]);
  if (tiny.length) out.push(['WARN', 'mobile-tiny-text', `${tiny.length} text run(s) under 11px: ${tiny.slice(0, 4).join(', ')}`]);
  return out;
}"""

INTERACT_JS = r"""async () => {
  const out = [], btns = [...document.querySelectorAll('button, [role=button]')]
    .filter(b => (b.innerText || '').trim() && b.getBoundingClientRect().width && getComputedStyle(b).display !== 'none' && b.type !== 'submit').slice(0, 8);
  let dead = [];
  for (const b of btns) {
    let changed = false;
    const mo = new MutationObserver(() => { changed = true; });
    mo.observe(document.body, { subtree: true, attributes: true, childList: true, characterData: true });
    const y = scrollY; try { b.click(); } catch (e) {}
    await new Promise(r => setTimeout(r, 120)); mo.disconnect(); scrollTo(0, y);
    if (!changed && !b.closest('a, form')) dead.push(b.innerText.trim().slice(0, 18));
  }
  if (dead.length) out.push(['INFO', 'dead-buttons', `${dead.length} button(s) changed nothing when clicked: ${dead.slice(0, 5).join(', ')}`]);
  const focusable = document.querySelectorAll('a[href], button, input, select, textarea, [tabindex]').length;
  let noRing = 0;
  for (const e of [...document.querySelectorAll('a[href], button')].slice(0, 6)) {
    e.focus({ focusVisible: true });
    const cs = getComputedStyle(e);
    if (document.activeElement === e && cs.outlineStyle === 'none' && cs.boxShadow === 'none' && !e.className.toString().match(/focus/)) noRing++;
  }
  if (noRing >= 3) out.push(['WARN', 'no-focus-ring', `${noRing} of the first 6 controls show no focus indicator (add focus-visible:ring-2)`]);
  return out;
}"""


def find_axe():
    for c in [os.environ.get('AXE_JS', ''), '/tmp/axe/node_modules/axe-core/axe.min.js',
              str(CACHE / 'node_modules/axe-core/axe.min.js')]:
        if c and pathlib.Path(c).is_file():
            return pathlib.Path(c).read_text()
    npm('install', 'axe-core')
    f = CACHE / 'node_modules/axe-core/axe.min.js'
    return f.read_text() if f.is_file() else None


def run_axe(page):
    js = find_axe()
    if not js:
        return [('INFO', 'axe', 'axe-core unavailable (npm install axe-core to enable)')]
    page.add_script_tag(content=js)
    res = page.evaluate("axe.run().then(r => r.violations.map(v => ({id: v.id, impact: v.impact, n: v.nodes.length, help: v.help, t: (v.nodes[0].target || []).join(' ').slice(0, 70)})))")
    out = []
    for v in res:
        sev = 'WARN' if v['impact'] in ('serious', 'critical') else 'INFO'
        out.append((sev, 'axe-' + v['id'], f"{v['help']} ({v['n']} node(s), {v['impact']}; first: {v['t']})"))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description='Full-page screenshot of an HTML file (offline-friendly)')
    ap.add_argument('html')
    ap.add_argument('--out', required=True)
    ap.add_argument('--dark', action='store_true', help="add class 'dark' to <html> before capturing")
    ap.add_argument('--width', type=int, default=1440)
    ap.add_argument('--height', type=int, default=900)
    ap.add_argument('--check', action='store_true',
                    help='also print defects found in the rendered page: layout (clipped text, blank/half-empty panels, hidden content), axe accessibility, console errors, 375px mobile, dead buttons, focus rings')
    a = ap.parse_args(argv)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit('render: Playwright missing. pip install playwright && python -m playwright install chromium')

    src = pathlib.Path(a.html).resolve()
    html = src.read_text(encoding='utf-8')
    if CDN.search(html) and not reachable('https://cdn.tailwindcss.com'):
        log('Tailwind CDN unreachable; compiling locally')
        html = compile_tailwind(html)
    if GFONTS.search(html) and not reachable('https://fonts.googleapis.com/css2?family=Inter'):
        log('Google Fonts unreachable; inlining @fontsource fonts')
        html = inline_fonts(html)
    page_file = src.with_name(f'.{src.stem}.render.html')  # same folder so relative assets resolve
    page_file.write_text(html, encoding='utf-8')

    try:
        with sync_playwright() as p:
            exe = chrome_path()
            browser = p.chromium.launch(**({'executable_path': exe} if exe else {}), args=['--no-sandbox'])
            page = browser.new_page(viewport={'width': a.width, 'height': a.height})
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)[:160]))
            page.on('console', lambda m: errors.append(m.text[:160]) if m.type == 'error' and 'ERR_' not in m.text and 'Failed to load resource' not in m.text else None)
            page.goto(page_file.as_uri())
            page.wait_for_timeout(500)
            if a.dark:
                page.evaluate("document.documentElement.classList.add('dark')")
            # scroll through once so scroll-triggered reveals run, then return to top
            page.evaluate("""async () => { for (let y = 0; y < document.body.scrollHeight; y += 600) {
                window.scrollTo(0, y); await new Promise(r => setTimeout(r, 60)); } window.scrollTo(0, 0); }""")
            page.wait_for_timeout(800)
            page.screenshot(path=a.out, full_page=True)
            if a.check:
                found = list(page.evaluate(CHECK_JS))
                found += run_axe(page)
                found += page.evaluate(INTERACT_JS)
                if errors:
                    found.append(['WARN', 'js-errors', f"{len(errors)} console/page error(s): {'; '.join(errors[:3])}"])
                m = browser.new_page(viewport={'width': 375, 'height': 800})
                m.goto(page_file.as_uri()); m.wait_for_timeout(600)
                found += m.evaluate(MOBILE_JS)
                m.close()
                found = [f for f in found if f[1] != 'dom-check']
                if not found:
                    found = [['INFO', 'dom-check', 'no defects found']]
                for sev, rule, msg in found:
                    print(f"  [{sev}] {rule}: {msg}")
            print(f"{a.out} ({a.width}x{page.evaluate('document.documentElement.scrollHeight')})")
            browser.close()
    finally:
        page_file.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
