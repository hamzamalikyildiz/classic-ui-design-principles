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

CDN = re.compile(r'<script[^>]+src=["\']https://cdn\.tailwindcss\.com[^"\']*["\'][^>]*>\s*</script>')
INLINE_CFG = re.compile(r'<script>\s*tailwind\.config\s*=\s*(\{[\s\S]*?\})\s*;?\s*</script>')
GFONTS = re.compile(r'<link[^>]+fonts\.(?:googleapis|gstatic)\.com[^>]*>')
CACHE = pathlib.Path(os.environ.get('UITOOLS_CACHE', pathlib.Path.home() / '.cache' / 'uitools-render'))
OFFLINE_ERRS = (
    'net::ERR_NAME_NOT_RESOLVED',
    'net::ERR_INTERNET_DISCONNECTED',
    'net::ERR_CONNECTION_REFUSED',
    'net::ERR_BLOCKED_BY_CLIENT',
)


def log(msg):
    print(f"render: {msg}", file=sys.stderr)


def reachable(url):
    try:
        with urllib.request.urlopen(url, timeout=4):
            return True
    except Exception:
        return False


def npm(*args):
    npm_bin = shutil.which('npm')
    if not npm_bin:
        return subprocess.CompletedProcess(['npm', *args], 1, '', 'npm not found')
    CACHE.mkdir(parents=True, exist_ok=True)
    if not (CACHE / 'package.json').exists():
        (CACHE / 'package.json').write_text('{"name":"uitools-render","private":true}', encoding='utf-8')
    return subprocess.run([npm_bin, *args], cwd=CACHE, capture_output=True, text=True,
                          encoding='utf-8', errors='replace')


def _inject_head(html, tag):
    """Insert tag before </head> (case-insensitive), or prepend if no </head>."""
    out, n = re.subn(r'</head>', lambda m: f'{tag}{m.group(0)}', html, count=1, flags=re.I)
    return out if n else f'{tag}{html}'


def compile_tailwind(html):
    if not shutil.which('npm') or not shutil.which('node'):
        log('npm/node not found; Tailwind classes will be unstyled')
        return html
    tw_bin = CACHE / 'node_modules' / '.bin' / ('tailwindcss.cmd' if os.name == 'nt' else 'tailwindcss')
    if not tw_bin.exists():
        r = npm('install', '--silent', 'tailwindcss@3')
        if r.returncode:
            log(f'could not install tailwindcss: {r.stderr.strip()[:200]}')
            return html
    cfg = {}
    m = INLINE_CFG.search(html)
    if m:
        r = subprocess.run(['node', '-e', f'process.stdout.write(JSON.stringify(({m.group(1)})))'],
                           capture_output=True, text=True, encoding='utf-8', errors='replace')
        if r.returncode == 0:
            cfg = json.loads(r.stdout)
        else:
            log('inline tailwind.config could not be evaluated; using defaults')
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d)
        (d / 'page.html').write_text(html, encoding='utf-8')
        (d / 'tailwind.config.js').write_text(
            'module.exports=' + json.dumps({**cfg, 'content': [(d / 'page.html').as_posix()]}),
            encoding='utf-8',
        )
        (d / 'in.css').write_text('@tailwind base;@tailwind components;@tailwind utilities;', encoding='utf-8')
        r = subprocess.run([str(tw_bin), '-c', str(d / 'tailwind.config.js'),
                            '-i', str(d / 'in.css'), '-o', str(d / 'out.css'), '--minify'],
                           capture_output=True, text=True, encoding='utf-8', errors='replace')
        if r.returncode:
            log(f'tailwind build failed: {r.stderr.strip()[:200]}')
            return html
        css = (d / 'out.css').read_text(encoding='utf-8')
    html = CDN.sub('', html)
    html = INLINE_CFG.sub('', html)
    return _inject_head(html, f'<style>{css}</style>')


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
    return _inject_head(html, f"<style>{''.join(faces)}</style>") if faces else html


def chrome_path():
    for name in ('google-chrome', 'chromium', 'chromium-browser', 'chrome'):
        p = shutil.which(name)
        if p:
            return p
    candidates = [
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        '/Applications/Chromium.app/Contents/MacOS/Chromium',
    ]
    for base in (os.environ.get('PROGRAMFILES'), os.environ.get('PROGRAMFILES(X86)'), os.environ.get('LOCALAPPDATA')):
        if base:
            candidates.append(os.path.join(base, 'Google', 'Chrome', 'Application', 'chrome.exe'))
    if os.name == 'nt':
        candidates.extend([
            r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
        ])
    for c in candidates:
        if pathlib.Path(c).is_file():
            return c
    return None


CHECKS_DIR = pathlib.Path(__file__).resolve().parent / 'checks'


def _load_check_js(filename):
    return (CHECKS_DIR / filename).read_text(encoding='utf-8').strip()


CHECK_JS = _load_check_js('check.js')
MOBILE_JS = _load_check_js('mobile.js')
INTERACT_JS = _load_check_js('interact.js')
SCROLL_SWEEP_JS = _load_check_js('sweep.js')


def find_axe():
    for c in [os.environ.get('AXE_JS', ''), '/tmp/axe/node_modules/axe-core/axe.min.js',
              str(CACHE / 'node_modules/axe-core/axe.min.js')]:
        if c and pathlib.Path(c).is_file():
            return pathlib.Path(c).read_text(encoding='utf-8')
    if not shutil.which('npm'):
        return None
    npm('install', '--silent', 'axe-core')
    f = CACHE / 'node_modules/axe-core/axe.min.js'
    return f.read_text(encoding='utf-8') if f.is_file() else None


def run_axe(page):
    js = find_axe()
    if not js:
        return [('INFO', 'axe', 'axe-core unavailable (npm install axe-core to enable)')]
    try:
        page.add_script_tag(content=js)
        res = page.evaluate("axe.run().then(r => r.violations.map(v => ({id: v.id, impact: v.impact, n: v.nodes.length, help: v.help, t: (v.nodes[0].target || []).join(' ').slice(0, 70)})))")
    except Exception as exc:
        return [('INFO', 'axe', f'axe-core error: {str(exc)[:120]}')]
    out = []
    for v in res:
        sev = 'WARN' if v['impact'] in ('serious', 'critical') else 'INFO'
        out.append((sev, 'axe-' + v['id'], f"{v['help']} ({v['n']} node(s), {v['impact']}; first: {v['t']})"))
    return out


def write_temp_render(src, html):
    """Write rendered HTML beside src so relative assets resolve, or fall back to tempdir."""
    page_file = src.with_name(f'.{src.stem}.{os.getpid()}.render.html')
    try:
        page_file.write_text(html, encoding='utf-8')
        return page_file
    except OSError:
        with tempfile.NamedTemporaryFile('w', suffix='.render.html', prefix=f'.{src.stem}.',
                                         dir=tempfile.gettempdir(), delete=False, encoding='utf-8') as tf:
            tf.write(html)
            return pathlib.Path(tf.name)


def is_ignored_console_error(text):
    """Ignore expected CDN/external offline errors while keeping local missing files and JS errors."""
    return any(err in text for err in OFFLINE_ERRS)


def _prepare_page(page, uri, dark):
    """Navigate to uri, apply dark class if requested, and run scroll-reveal sweep."""
    page.goto(uri)
    page.wait_for_timeout(500)
    if dark:
        page.evaluate("document.documentElement.classList.add('dark')")
    page.evaluate(SCROLL_SWEEP_JS)
    page.wait_for_timeout(800)


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
    page_file = write_temp_render(src, html)

    try:
        with sync_playwright() as p:
            exe = chrome_path()
            browser = p.chromium.launch(**({'executable_path': exe} if exe else {}), args=['--no-sandbox'])
            page = browser.new_page(viewport={'width': a.width, 'height': a.height})
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)[:160]))
            page.on('console', lambda m: errors.append(m.text[:160])
                    if m.type == 'error' and not is_ignored_console_error(m.text) else None)
            _prepare_page(page, page_file.as_uri(), a.dark)
            page.screenshot(path=a.out, full_page=True)
            scroll_h = page.evaluate('document.documentElement.scrollHeight')
            if a.check:
                found = list(page.evaluate(CHECK_JS))
                found += run_axe(page)
                try:
                    found += page.evaluate(INTERACT_JS)
                except Exception as exc:
                    found.append(['INFO', 'interact-check',
                                  f'interaction check interrupted (e.g., navigation): {str(exc)[:100]}'])
                if errors:
                    found.append(['WARN', 'js-errors', f"{len(errors)} console/page error(s): {'; '.join(errors[:3])}"])
                m = browser.new_page(viewport={'width': 375, 'height': 800})
                _prepare_page(m, page_file.as_uri(), a.dark)
                found += m.evaluate(MOBILE_JS)
                m.close()
                found = [f for f in found if f[1] != 'dom-check']
                if not found:
                    found = [['INFO', 'dom-check', 'no defects found']]
                for sev, rule, msg in found:
                    print(f"  [{sev}] {rule}: {msg}")
            print(f"{a.out} ({a.width}x{scroll_h})")
            browser.close()
    finally:
        page_file.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
