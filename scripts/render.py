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


def main(argv=None):
    ap = argparse.ArgumentParser(description='Full-page screenshot of an HTML file (offline-friendly)')
    ap.add_argument('html')
    ap.add_argument('--out', required=True)
    ap.add_argument('--dark', action='store_true', help="add class 'dark' to <html> before capturing")
    ap.add_argument('--width', type=int, default=1440)
    ap.add_argument('--height', type=int, default=900)
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
            page.goto(page_file.as_uri())
            page.wait_for_timeout(500)
            if a.dark:
                page.evaluate("document.documentElement.classList.add('dark')")
            # scroll through once so scroll-triggered reveals run, then return to top
            page.evaluate("""async () => { for (let y = 0; y < document.body.scrollHeight; y += 600) {
                window.scrollTo(0, y); await new Promise(r => setTimeout(r, 60)); } window.scrollTo(0, 0); }""")
            page.wait_for_timeout(800)
            page.screenshot(path=a.out, full_page=True)
            print(f"{a.out} ({a.width}x{page.evaluate('document.documentElement.scrollHeight')})")
            browser.close()
    finally:
        page_file.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
