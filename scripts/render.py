#!/usr/bin/env python3
"""Full-page screenshot of an HTML file or live URL for visual review.

Works offline for local HTML files: if the page uses the Tailwind CDN or Google Fonts and they
are unreachable, Tailwind is compiled locally (npx tailwindcss@3, using the page's inline
tailwind.config) and the fonts are inlined from @fontsource packages (npm). In --url mode,
live pages are captured directly without HTML rewriting or offline network-error suppression.
Needs Python Playwright and a Chromium/Chrome binary.

    python3 scripts/render.py page.html --out page.png [--dark] [--width 1440] [--height 900]
    python3 scripts/render.py --url http://localhost:3000/dashboard --out page.png [--check]
"""
import argparse
import base64
from dataclasses import dataclass, fields
import importlib.util
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
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
HYDRATION_MISMATCH_PATTERNS = (
    'Hydration failed',
    'did not match',
    'Text content does not match server-rendered HTML',
    'Hydration completed but contains mismatches',
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


VIEWPORT_PRESETS = {
    'desktop': (1440, 900),
    'laptop': (1280, 800),
    'tablet': (834, 1112),
    'mobile': (390, 844),
    'mobile-375': (375, 800),
    'legacy-mobile': (375, 800),
}
_CUSTOM_VP_RE = re.compile(r'^(\d+)[xX](\d+)$')


def _normalize_list_arg(val):
    """Flatten comma-separated or space-separated CLI/config string list arguments."""
    if val is None:
        return None
    items = [val] if isinstance(val, str) else list(val)
    out = []
    for item in items:
        if isinstance(item, str):
            for part in item.split(','):
                part = part.strip()
                if part:
                    out.append(part)
        elif item is not None:
            out.append(item)
    return out


def parse_viewport(spec):
    """Resolve a viewport preset name ('desktop', 'mobile', ...) or 'WxH' string into (name, width, height)."""
    if isinstance(spec, dict):
        if 'width' not in spec or 'height' not in spec:
            raise ValueError(f'viewport dict requires width and height: {spec!r}')
        w, h = int(spec['width']), int(spec['height'])
        if w <= 0 or h <= 0:
            raise ValueError(f'viewport dimensions must be positive: {spec!r}')
        name = str(spec.get('name') or f'{w}x{h}').strip()
        return name, w, h
    if isinstance(spec, (tuple, list)) and len(spec) == 2:
        w, h = int(spec[0]), int(spec[1])
        if w <= 0 or h <= 0:
            raise ValueError(f'viewport dimensions must be positive: {spec!r}')
        return f'{w}x{h}', w, h
    if not isinstance(spec, str) or not spec.strip():
        raise ValueError(f'invalid viewport specification: {spec!r}')
    key = spec.strip().lower()
    if key in VIEWPORT_PRESETS:
        w, h = VIEWPORT_PRESETS[key]
        return key, w, h
    m = _CUSTOM_VP_RE.match(key)
    if m:
        w, h = int(m.group(1)), int(m.group(2))
        if w <= 0 or h <= 0:
            raise ValueError(f'viewport dimensions must be positive: {spec!r}')
        return f'{w}x{h}', w, h
    raise ValueError(
        f'unknown viewport {spec!r}: expected one of {sorted(VIEWPORT_PRESETS)} or WxH (e.g. 375x800)'
    )


resolve_viewport = parse_viewport


@dataclass
class RenderOptions:
    """Configuration for rendering and optionally checking a local HTML file, live URL, or multi-route config."""
    html: str | None = None
    url: str | None = None
    out: str | None = None
    dark: bool = False
    width: int = 1440
    height: int = 900
    check: bool = False
    online: bool | None = None
    storage_state: str | None = None
    save_storage_state: str | None = None
    login_script: str | None = None
    wait_for: str | None = None
    actions: list | None = None
    routes: str | dict | None = None
    out_dir: str = 'shots'
    viewports: list | None = None
    states: list | None = None


def _coerce_options(opts):
    """Normalize None, dict, or RenderOptions into a RenderOptions instance."""
    if opts is None:
        return RenderOptions()
    if isinstance(opts, RenderOptions):
        return opts
    if isinstance(opts, dict):
        valid = {f.name for f in fields(RenderOptions)}
        return RenderOptions(**{k: v for k, v in opts.items() if k in valid})
    raise TypeError(f'expected RenderOptions or dict, got {type(opts).__name__}')


def is_ignored_console_error(text, online=False):
    """Ignore expected CDN/external offline errors while keeping local missing files and JS errors.

    In online (--url) mode, network errors are real application defects and are never suppressed.
    """
    if online:
        return False
    return any(err in text for err in OFFLINE_ERRS)


def is_online_target(target_uri, opts=None):
    """Return True when capturing a live HTTP(S) target rather than an offline HTML file."""
    opts = _coerce_options(opts)
    if opts.online is not None:
        return bool(opts.online)
    if opts.url:
        return True
    return str(target_uri).lower().startswith(('http://', 'https://'))


def is_hydration_mismatch_error(text):
    """Return True when a console or page error indicates a SSR/CSR hydration mismatch."""
    return any(pat in text for pat in HYDRATION_MISMATCH_PATTERNS)


_HYDRATION_STABILITY_JS = """({ quietMs, maxWaitMs, checkFramework }) => new Promise(resolve => {
  const start = performance.now();
  const hasReactKey = el => {
    if (!el) return false;
    try {
      return Object.keys(el).some(k => k.startsWith('__reactContainer$') || k === '_reactRootContainer');
    } catch (e) {
      return false;
    }
  };
  const detectFramework = () => {
    if (!checkFramework) return { detected: false, mounted: true };
    const nextRoot = document.querySelector('#__next');
    const hasNext = Boolean(nextRoot || document.querySelector('#__NEXT_DATA__') || window.__NEXT_DATA__ || (window.next && window.next.router));
    const vueRoot = document.querySelector('[data-v-app]') || document.querySelector('#app') || document.querySelector('#root');
    const hasVue = Boolean((vueRoot && vueRoot.__vue_app__) || window.__VUE__);
    const svelteNode = document.querySelector('[data-svelte-h]');
    const hasSvelte = Boolean(svelteNode);
    const candidates = [
      document.querySelector('#root'),
      document.querySelector('#app'),
      nextRoot,
      document.body,
      ...(document.body ? Array.from(document.body.children).slice(0, 6) : []),
    ].filter(Boolean);
    const hasReact = candidates.some(hasReactKey) || Boolean(
      document.querySelector('[data-reactroot]') ||
      document.querySelector('script[src*="react" i]') ||
      document.documentElement.hasAttribute('data-react-app')
    );
    const detected = hasNext || hasVue || hasSvelte || hasReact;
    if (!detected) return { detected: false, mounted: true };
    const nextMounted = !hasNext || Boolean(
      (window.next && window.next.router) ||
      hasReactKey(nextRoot) ||
      (nextRoot && nextRoot.children.length > 0 && document.readyState === 'complete')
    );
    const reactMounted = !hasReact || candidates.some(hasReactKey) || Boolean(document.querySelector('[data-reactroot]'));
    const vueMounted = !hasVue || Boolean((vueRoot && vueRoot.__vue_app__) || (document.body && Array.from(document.body.children).some(c => c.__vue_app__)));
    const svelteMounted = !hasSvelte || document.readyState === 'complete';
    return { detected: true, mounted: nextMounted && reactMounted && vueMounted && svelteMounted };
  };

  let lastMutation = performance.now();
  let settled = false;
  const root = document.documentElement || document.body;
  let mo = null;
  if (root && typeof MutationObserver !== 'undefined') {
    mo = new MutationObserver(() => {
      lastMutation = performance.now();
    });
    mo.observe(root, { subtree: true, childList: true, attributes: true, characterData: true });
  }
  const finish = status => {
    if (settled) return;
    settled = true;
    if (mo) mo.disconnect();
    resolve(status);
  };
  const tick = () => {
    if (settled) return;
    const now = performance.now();
    const elapsed = now - start;
    if (elapsed >= maxWaitMs) {
      finish({ timedOut: true, elapsedMs: Math.round(elapsed) });
      return;
    }
    const fw = detectFramework();
    const quietFor = now - lastMutation;
    if (fw.mounted && quietFor >= quietMs) {
      finish({ timedOut: false, detected: fw.detected, elapsedMs: Math.round(elapsed) });
      return;
    }
    setTimeout(tick, Math.min(50, Math.max(10, quietMs - quietFor)));
  };
  setTimeout(tick, Math.min(50, quietMs));
})"""


def wait_for_dom_stability(page, quiet_ms=300, max_wait_ms=3000):
    """Wait until the page DOM stops mutating for quiet_ms (up to max_wait_ms)."""
    if hasattr(page, 'evaluate'):
        try:
            res = page.evaluate(
                _HYDRATION_STABILITY_JS,
                {'quietMs': int(quiet_ms), 'maxWaitMs': int(max_wait_ms), 'checkFramework': False},
            )
            if isinstance(res, dict):
                return res
        except TypeError:
            pass
        except Exception:
            pass
    if hasattr(page, 'wait_for_timeout'):
        page.wait_for_timeout(quiet_ms)
    return {'timedOut': False, 'detected': False, 'elapsedMs': 0}


def wait_for_hydration(page, wait_for=None, quiet_ms=500, max_wait_ms=5000):
    """Wait for load, soft networkidle, framework hydration + DOM stability, and optional selector."""
    if hasattr(page, 'wait_for_load_state'):
        try:
            page.wait_for_load_state('load', timeout=max_wait_ms)
        except Exception:
            pass
        try:
            page.wait_for_load_state('networkidle', timeout=min(2500, max_wait_ms))
        except Exception:
            pass

    evaluated = False
    if hasattr(page, 'evaluate'):
        try:
            res = page.evaluate(
                _HYDRATION_STABILITY_JS,
                {'quietMs': int(quiet_ms), 'maxWaitMs': int(max_wait_ms), 'checkFramework': True},
            )
            evaluated = isinstance(res, dict)
        except TypeError:
            evaluated = False
        except Exception:
            evaluated = False

    if not evaluated and hasattr(page, 'wait_for_timeout'):
        page.wait_for_timeout(quiet_ms)

    if wait_for and hasattr(page, 'wait_for_selector'):
        page.wait_for_selector(wait_for, state='visible', timeout=max_wait_ms)


def run_actions(page, actions):
    """Run optional pre-check interaction actions only after hydration and DOM stability settle."""
    if not actions:
        return
    wait_for_dom_stability(page, quiet_ms=300, max_wait_ms=3000)
    for act in actions:
        if callable(act):
            act(page)
        elif isinstance(act, dict):
            kind = act.get('type') or act.get('action')
            sel = act.get('selector')
            val = act.get('value', '')
            if not kind:
                for k in ('click', 'fill', 'wait_for', 'hover', 'press', 'wait'):
                    if k in act:
                        kind = k
                        raw = act[k]
                        if k == 'fill' and isinstance(raw, (list, tuple)) and len(raw) >= 2:
                            sel, val = raw[0], raw[1]
                        elif k == 'fill' and isinstance(raw, dict):
                            sel = raw.get('selector')
                            val = raw.get('value', '')
                        else:
                            sel = raw
                        break
            if kind == 'fill' and sel is not None and hasattr(page, 'fill'):
                page.fill(sel, str(val))
            elif kind == 'click' and sel is not None and hasattr(page, 'click'):
                page.click(sel)
            elif kind == 'wait_for' and sel is not None and hasattr(page, 'wait_for_selector'):
                page.wait_for_selector(sel, state='visible', timeout=act.get('timeout', 5000))
            elif kind == 'hover' and sel is not None and hasattr(page, 'hover'):
                page.hover(sel)
            elif kind == 'press' and sel is not None and hasattr(page, 'press'):
                if isinstance(sel, (list, tuple)) and len(sel) >= 2:
                    page.press(sel[0], str(sel[1]))
                elif 'key' in act:
                    page.press(sel, str(act['key']))
            elif kind == 'wait' and sel is not None and hasattr(page, 'wait_for_timeout'):
                page.wait_for_timeout(int(sel))
        elif isinstance(act, (tuple, list)) and len(act) >= 2:
            kind, sel = act[0], act[1]
            if kind == 'fill' and hasattr(page, 'fill'):
                page.fill(sel, str(act[2] if len(act) > 2 else ''))
            elif kind == 'click' and hasattr(page, 'click'):
                page.click(sel)
        wait_for_dom_stability(page, quiet_ms=300, max_wait_ms=3000)


def _prepare_page(page, uri, dark, wait_for=None, actions=None):
    """Navigate to uri, wait for hydration/DOM stability, apply dark class, run actions, and scroll sweep."""
    page.goto(uri)
    wait_for_hydration(page, wait_for=wait_for, quiet_ms=500, max_wait_ms=5000)
    if dark:
        page.evaluate("document.documentElement.classList.add('dark')")
    if actions:
        run_actions(page, actions)
    page.evaluate(SCROLL_SWEEP_JS)
    page.wait_for_timeout(800)


def prepare_html_target(html_path):
    """Read local HTML, compile Tailwind / inline fonts if offline, and write temp render file."""
    src = pathlib.Path(html_path).resolve()
    html = src.read_text(encoding='utf-8')
    if CDN.search(html) and not reachable('https://cdn.tailwindcss.com'):
        log('Tailwind CDN unreachable; compiling locally')
        html = compile_tailwind(html)
    if GFONTS.search(html) and not reachable('https://fonts.googleapis.com/css2?family=Inter'):
        log('Google Fonts unreachable; inlining @fontsource fonts')
        html = inline_fonts(html)
    return write_temp_render(src, html)


def launch_browser(playwright):
    """Launch headless Chromium using a detected local Chrome/Chromium executable if present."""
    exe = chrome_path()
    return playwright.chromium.launch(**({'executable_path': exe} if exe else {}), args=['--no-sandbox'])


def _attach_error_listeners(page, console_errors, network_errors, online):
    """Attach pageerror, console, and (when online) network failure listeners; return detach fn."""
    def on_pageerror(err):
        console_errors.append(str(err)[:160])

    def on_console(msg):
        if msg.type == 'error' and not is_ignored_console_error(msg.text, online=online):
            console_errors.append(msg.text[:160])

    def on_response(resp):
        if online and resp.status >= 400:
            network_errors.append(f"HTTP {resp.status}: {resp.url}"[:160])

    def on_requestfailed(req):
        if online:
            failure = req.failure or 'requestfailed'
            if failure == 'net::ERR_ABORTED' and any(req.url in e for e in network_errors):
                return
            network_errors.append(f"{failure}: {req.url}"[:160])

    listeners = [
        ('pageerror', on_pageerror),
        ('console', on_console),
    ]
    if online:
        listeners.extend([
            ('response', on_response),
            ('requestfailed', on_requestfailed),
        ])
    for event, fn in listeners:
        page.on(event, fn)

    def detach():
        if hasattr(page, 'remove_listener'):
            for event, fn in listeners:
                try:
                    page.remove_listener(event, fn)
                except Exception:
                    pass

    return detach


def _run_dom_checks(page, mobile_factory, target_uri, opts, console_errors, network_errors):
    """Run layout, axe, interaction, error, and 375px mobile checks on a prepared page."""
    found = list(page.evaluate(CHECK_JS))
    found += run_axe(page)
    try:
        wait_for_dom_stability(page, quiet_ms=300, max_wait_ms=3000)
        found += page.evaluate(INTERACT_JS)
    except Exception as exc:
        found.append(['INFO', 'interact-check',
                      f'interaction check interrupted (e.g., navigation): {str(exc)[:100]}'])
    hydration_errors = [e for e in console_errors if is_hydration_mismatch_error(e)]
    other_console_errors = [e for e in console_errors if not is_hydration_mismatch_error(e)]
    if hydration_errors:
        found.append(['WARN', 'hydration-mismatch',
                      f"{len(hydration_errors)} hydration mismatch(es): {'; '.join(hydration_errors[:3])}"])
    if other_console_errors:
        found.append(['WARN', 'js-errors',
                      f"{len(other_console_errors)} console/page error(s): {'; '.join(other_console_errors[:3])}"])
    if network_errors:
        found.append(['WARN', 'network-errors',
                      f"{len(network_errors)} network error(s): {'; '.join(network_errors[:3])}"])
    if mobile_factory is not None and hasattr(mobile_factory, 'new_page'):
        m = _new_page(mobile_factory, {'width': 375, 'height': 800})
        try:
            _prepare_page(m, target_uri, opts.dark, wait_for=opts.wait_for, actions=opts.actions)
            found += m.evaluate(MOBILE_JS)
        finally:
            m.close()
    found = [list(f) for f in found if f[1] != 'dom-check']
    if not found:
        found = [['INFO', 'dom-check', 'no defects found']]
    return found


def _base_url(target_uri):
    """Scheme+host root of an http(s) target (e.g. http://localhost:3000); '' for file targets."""
    p = urllib.parse.urlparse(str(target_uri))
    if p.scheme in ('http', 'https') and p.netloc:
        return f'{p.scheme}://{p.netloc}'
    return ''


def _load_login(path):
    """Load the user's login script via importlib and return its login(page, base_url) function."""
    p = pathlib.Path(path)
    if not p.is_file():
        sys.exit(f'render: --login-script file not found: {path}')
    spec = importlib.util.spec_from_file_location('render_login_script', p)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        sys.exit(f'render: could not load --login-script {path}: {type(e).__name__}: {e}')
    fn = getattr(mod, 'login', None)
    if not callable(fn):
        sys.exit(f'render: --login-script {path} must define def login(page, base_url):')
    return fn


def _check_auth_inputs(opts):
    """Fail early with a clear message when auth input files are missing/invalid."""
    if opts.storage_state and not pathlib.Path(opts.storage_state).is_file():
        sys.exit(f'render: --storage-state file not found: {opts.storage_state}')
    if opts.login_script:
        _load_login(opts.login_script)


def _has_auth(opts):
    return bool(opts.storage_state or opts.login_script or opts.save_storage_state)


def _new_context(browser, opts):
    kw = {'viewport': {'width': opts.width, 'height': opts.height}}
    if opts.storage_state:
        kw['storage_state'] = str(opts.storage_state)
    return browser.new_context(**kw)


def _login_and_save(context, target_uri, opts):
    """Run the login script (if any) on its own page, then save storage state (if requested)."""
    if opts.login_script:
        login = _load_login(opts.login_script)
        page = context.new_page()
        try:
            login(page, _base_url(target_uri))
        finally:
            page.close()
    if opts.save_storage_state:
        p = pathlib.Path(opts.save_storage_state)
        p.parent.mkdir(parents=True, exist_ok=True)
        context.storage_state(path=str(p))
        log(f'storage state saved to {p}')  # never print cookie/token values


def _open_auth_context(browser, target_uri, opts):
    """Create a context (loading storageState), run login/save; close it on failure."""
    _check_auth_inputs(opts)
    context = _new_context(browser, opts)
    try:
        _login_and_save(context, target_uri, opts)
    except BaseException:
        context.close()
        raise
    return context


def _new_page(factory, viewport):
    """Open a new page on either a Browser (accepts viewport=...) or a BrowserContext."""
    try:
        return factory.new_page(viewport=viewport)
    except TypeError:
        page = factory.new_page()
        if hasattr(page, 'set_viewport_size'):
            page.set_viewport_size(viewport)
        return page


def capture(browser_or_page, target_uri, opts=None):
    """Capture a single target URI (file:// or http(s)://) and optionally run DOM checks.

    Accepts either a Playwright Browser/BrowserContext (preferred) or an existing Page.
    Returns: {"out": ..., "width": ..., "scroll_height": ..., "findings": [...],
              "console_errors": [...], "network_errors": [...]}.
    """
    opts = _coerce_options(opts)
    online = is_online_target(target_uri, opts)
    owns_page = hasattr(browser_or_page, 'new_page')
    owned_context = None
    if owns_page:
        if hasattr(browser_or_page, 'new_context') and _has_auth(opts):
            owned_context = _open_auth_context(browser_or_page, target_uri, opts)
            browser_or_page = owned_context
        page = _new_page(browser_or_page, {'width': opts.width, 'height': opts.height})
        mobile_factory = browser_or_page
    else:
        page = browser_or_page
        mobile_factory = getattr(page, 'context', None)

    console_errors = []
    network_errors = []
    detach = _attach_error_listeners(page, console_errors, network_errors, online=online)
    try:
        _prepare_page(page, target_uri, opts.dark, wait_for=opts.wait_for, actions=opts.actions)
        out_path = str(opts.out) if opts.out is not None else None
        if out_path is not None:
            page.screenshot(path=out_path, full_page=True)
        scroll_h = page.evaluate('document.documentElement.scrollHeight')
        found = []
        if opts.check:
            found = _run_dom_checks(page, mobile_factory, target_uri, opts,
                                    console_errors, network_errors)
        return {
            'out': out_path,
            'width': opts.width,
            'scroll_height': scroll_h,
            'findings': found,
            'console_errors': console_errors,
            'network_errors': network_errors,
        }
    finally:
        detach()
        if owns_page:
            page.close()
        if owned_context is not None:
            owned_context.close()


def validate_routes_config(cfg):
    """Validate and normalize a routes.json dictionary schema."""
    if not isinstance(cfg, dict):
        raise ValueError('routes config must be a JSON object')
    base_url = cfg.get('base_url')
    if not isinstance(base_url, str) or not base_url.strip():
        raise ValueError("routes config requires a non-empty string 'base_url'")
    routes = cfg.get('routes')
    if not isinstance(routes, list) or not routes:
        raise ValueError("routes config requires a non-empty 'routes' list")
    auth = cfg.get('auth')
    if auth is not None:
        if not isinstance(auth, dict):
            raise ValueError("'auth' in routes config must be an object")
        for k in ('storage_state', 'login_script', 'save_storage_state'):
            if auth.get(k) is not None and (not isinstance(auth[k], str) or not auth[k].strip()):
                raise ValueError(f"auth.{k} must be a non-empty string")
    if cfg.get('viewports') is not None:
        vps = _normalize_list_arg(cfg['viewports'])
        if not vps:
            raise ValueError("'viewports' in routes config cannot be empty")
        for vp in vps:
            parse_viewport(vp)
    if cfg.get('states') is not None:
        sts = _normalize_list_arg(cfg['states'])
        if not sts or not all(isinstance(s, str) and s.strip() for s in sts):
            raise ValueError("'states' in routes config must be a non-empty list of strings")

    seen_names = set()
    for idx, route in enumerate(routes):
        if not isinstance(route, dict):
            raise ValueError(f'route at index {idx} must be an object')
        name = route.get('name')
        if not isinstance(name, str) or not name.strip() or '/' in name or '\\' in name or name.strip() in ('.', '..'):
            raise ValueError(f"route at index {idx} requires a valid non-empty string 'name'")
        name = name.strip()
        if name in seen_names:
            raise ValueError(f'duplicate route name: {name!r}')
        seen_names.add(name)
        path_val = route.get('path', route.get('url'))
        if not isinstance(path_val, str):
            raise ValueError(f"route {name!r} requires a string 'path' (or 'url')")
        if route.get('states') is not None:
            r_sts = _normalize_list_arg(route['states'])
            if not r_sts or not all(isinstance(s, str) and s.strip() for s in r_sts):
                raise ValueError(f"route {name!r} has invalid 'states'")
        if route.get('viewports') is not None:
            r_vps = _normalize_list_arg(route['viewports'])
            if not r_vps:
                raise ValueError(f"route {name!r} has empty 'viewports'")
            for vp in r_vps:
                parse_viewport(vp)
        if route.get('actions') is not None and not isinstance(route['actions'], list):
            raise ValueError(f"route {name!r} 'actions' must be a list")
        if route.get('wait_for') is not None and not isinstance(route['wait_for'], str):
            raise ValueError(f"route {name!r} 'wait_for' must be a string")
    return cfg


def load_routes_config(routes_source):
    """Load and validate routes config from a file path or dict; return (cfg_dict, base_dir)."""
    if isinstance(routes_source, dict):
        return validate_routes_config(dict(routes_source)), None
    p = pathlib.Path(routes_source)
    if not p.is_file():
        raise FileNotFoundError(f'routes file not found: {routes_source}')
    try:
        cfg = json.loads(p.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise ValueError(f'invalid JSON in routes file {routes_source}: {exc}') from exc
    return validate_routes_config(cfg), p.resolve().parent


def _resolve_auth_path(path_val, base_dir, must_exist=False):
    if not path_val:
        return None
    p = pathlib.Path(path_val)
    if p.is_absolute() or base_dir is None:
        return str(p)
    candidate = base_dir / p
    if must_exist:
        return str(candidate) if candidate.exists() else str(p)
    return str(candidate)


def _resolve_base_target(base_url, base_dir=None):
    """Resolve base_url (HTTP(S), file://, or local HTML/dir path) into (base_uri, online, temp_html_file)."""
    raw = base_url.strip()
    if raw.lower().startswith(('http://', 'https://')):
        return raw, True, None
    if raw.lower().startswith('file://'):
        parsed = urllib.parse.urlsplit(raw)
        local_path = pathlib.Path(urllib.request.url2pathname(parsed.path))
        if local_path.is_file() and local_path.suffix.lower() in ('.html', '.htm'):
            temp_file = prepare_html_target(local_path)
            uri = temp_file.as_uri()
            if parsed.query or parsed.fragment:
                sp = urllib.parse.urlsplit(uri)
                uri = urllib.parse.urlunsplit((sp.scheme, sp.netloc, sp.path, parsed.query, parsed.fragment))
            return uri, False, temp_file
        return raw, False, None

    # Local path (optionally with ?query or #fragment)
    m = re.match(r'^([^?#]*)(.*)$', raw)
    file_part, tail = (m.group(1), m.group(2)) if m else (raw, '')
    p = pathlib.Path(file_part)
    if not p.is_absolute() and base_dir is not None and (base_dir / p).exists():
        p = (base_dir / p).resolve()
    else:
        p = p.resolve()
    temp_file = None
    if p.is_file() and p.suffix.lower() in ('.html', '.htm'):
        temp_file = prepare_html_target(p)
        base_uri = temp_file.as_uri()
    else:
        base_uri = p.as_uri()
    if tail:
        base_uri = f'{base_uri}{tail}'
    return base_uri, False, temp_file


def _build_route_url(base_uri, route_cfg, state_name='default'):
    """Construct target URI for a route and state, supporting HTTP(S), file://, and hash/query routes."""
    route_path = route_cfg.get('url') if route_cfg.get('url') is not None else route_cfg.get('path', '')
    overrides = route_cfg.get('state_overrides')
    has_explicit_state_path = False
    if isinstance(overrides, dict) and isinstance(overrides.get(state_name), dict):
        ov = overrides[state_name]
        if ov.get('url') is not None:
            route_path = ov['url']
            has_explicit_state_path = True
        elif ov.get('path') is not None:
            route_path = ov['path']
            has_explicit_state_path = True

    route_path = str(route_path).strip()
    if route_path.lower().startswith(('http://', 'https://', 'file://')):
        target = route_path
    elif base_uri.lower().startswith(('http://', 'https://')):
        if not route_path:
            target = base_uri
        elif route_path.startswith(('#', '?')):
            target = f'{base_uri}{route_path}'
        elif route_path.startswith('/'):
            sp = urllib.parse.urlsplit(base_uri)
            root = f'{sp.scheme}://{sp.netloc}'
            base_path = sp.path.rstrip('/')
            if base_path and not base_path.lower().endswith(('.html', '.htm')):
                target = f'{root}{base_path}{route_path}'
            else:
                target = f'{root}{route_path}'
        else:
            target = f"{base_uri.rstrip('/')}/{route_path}"
    else:
        # file:// target (single HTML with hash routing or directory)
        if not route_path or route_path == '/':
            target = base_uri
        elif route_path.startswith(('#', '?')):
            target = f'{base_uri}{route_path}'
        elif urllib.parse.urlsplit(base_uri).path.lower().endswith(('.html', '.htm')):
            target = f'{base_uri}#{route_path}'
        else:
            target = f"{base_uri.rstrip('/')}/{route_path.lstrip('/')}"

    if state_name and state_name != 'default' and not has_explicit_state_path and not route_cfg.get('disable_state_query'):
        sp = urllib.parse.urlsplit(target)
        qs = urllib.parse.parse_qs(sp.query, keep_blank_values=True)
        if 'state' not in qs and f'state={state_name}' not in sp.fragment:
            q_add = f'state={urllib.parse.quote(str(state_name))}'
            new_query = f'{sp.query}&{q_add}' if sp.query else q_add
            target = urllib.parse.urlunsplit((sp.scheme, sp.netloc, sp.path, new_query, sp.fragment))
    return target


def _apply_route_state(context, page, route_cfg, state_name):
    """Hook for applying route state (state init markers, state_overrides, and İP-B5 network mocks).

    May optionally return a cleanup callable or dict (e.g. {'target_uri': ...}).
    """
    state_name = state_name or 'default'
    if hasattr(page, 'add_init_script'):
        try:
            state_json = json.dumps(state_name)
            page.add_init_script(
                f"window.__RENDER_STATE__ = {state_json}; "
                f"window.__UI_STATE__ = {state_json}; "
                f"document.addEventListener('DOMContentLoaded', () => {{"
                f"  if (document.documentElement && !document.documentElement.dataset.state) {{"
                f"    document.documentElement.dataset.state = {state_json};"
                f"  }}"
                f"}});"
            )
        except Exception:
            pass
    return None


def _run_viewport_checks(page, vp_width, console_errors, network_errors):
    """Run viewport-appropriate DOM checks: desktop/tablet (CHECK_JS+axe+INTERACT_JS) or mobile<=480 (CHECK_JS+MOBILE_JS+axe)."""
    found = list(page.evaluate(CHECK_JS) or [])
    if vp_width <= 480:
        found += list(page.evaluate(MOBILE_JS) or [])
        found += run_axe(page)
    else:
        found += run_axe(page)
        try:
            wait_for_dom_stability(page, quiet_ms=200, max_wait_ms=2000)
            found += list(page.evaluate(INTERACT_JS) or [])
        except Exception as exc:
            found.append(['INFO', 'interact-check',
                          f'interaction check interrupted (e.g., navigation): {str(exc)[:100]}'])
    hydration_errors = [e for e in console_errors if is_hydration_mismatch_error(e)]
    other_console_errors = [e for e in console_errors if not is_hydration_mismatch_error(e)]
    if hydration_errors:
        found.append(['WARN', 'hydration-mismatch',
                      f"{len(hydration_errors)} hydration mismatch(es): {'; '.join(hydration_errors[:3])}"])
    if other_console_errors:
        found.append(['WARN', 'js-errors',
                      f"{len(other_console_errors)} console/page error(s): {'; '.join(other_console_errors[:3])}"])
    if network_errors:
        found.append(['WARN', 'network-errors',
                      f"{len(network_errors)} network error(s): {'; '.join(network_errors[:3])}"])
    found = [list(f) for f in found if f[1] != 'dom-check']
    if not found:
        found = [['INFO', 'dom-check', 'no defects found']]
    return found


def _count_severities(findings):
    fails = sum(1 for sev, _, _ in findings if sev == 'FAIL')
    warns = sum(1 for sev, _, _ in findings if sev == 'WARN')
    infos = sum(1 for sev, rule, _ in findings if sev == 'INFO' and rule != 'dom-check')
    return fails, warns, infos


def _write_route_check_file(route_dir, route_name, route_path, route_results):
    """Write per-route findings summary to shots/<route>/check.txt."""
    check_path = route_dir / 'check.txt'
    lines = [f'# Route: {route_name} ({route_path})']
    for item in route_results:
        rel_png = pathlib.Path(item['out']).name if item.get('out') else ''
        lines.append(
            f"\n## [{item['state']} / {item['viewport']}] "
            f"({item['width']}x{item['scroll_height']}) -> {rel_png}"
        )
        for sev, rule, msg in item['findings']:
            lines.append(f'  [{sev}] {rule}: {msg}')
    check_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return check_path


def _write_report_md(out_dir, results):
    """Write shots/REPORT.md containing the Markdown summary table and detailed findings list."""
    report_path = pathlib.Path(out_dir) / 'REPORT.md'
    lines = [
        '# Multi-Route UI Capture & Check Report',
        '',
        '| Route | State | Viewport | Size | FAIL | WARN | INFO | Screenshot |',
        '| --- | --- | --- | --- | --- | --- | --- | --- |',
    ]
    for item in results:
        fails, warns, infos = _count_severities(item['findings'])
        rel_shot = f"{item['route']}/{item['state']}-{item['viewport']}.png"
        size_str = f"{item['width']}x{item['scroll_height']}"
        lines.append(
            f"| {item['route']} | {item['state']} | {item['viewport']} | {size_str} | "
            f"{fails} | {warns} | {infos} | {rel_shot} |"
        )
    lines.extend(['', '## Detailed Findings', ''])
    for item in results:
        rel_shot = f"{item['route']}/{item['state']}-{item['viewport']}.png"
        lines.append(
            f"### {item['route']} — `{item['state']}` / `{item['viewport']}` "
            f"({item['width']}x{item['scroll_height']}, `{rel_shot}`)"
        )
        for sev, rule, msg in item['findings']:
            lines.append(f'- **[{sev}]** `{rule}`: {msg}')
        lines.append('')
    report_path.write_text('\n'.join(lines), encoding='utf-8')
    return report_path


def _build_contact_sheet(results, out_path, cols=4, thumb_width=320, thumb_height=220):
    """Combine all route/state-viewport screenshots into a labeled contact-sheet.png thumbnail grid."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        log('PIL (Pillow) unavailable; skipping contact-sheet.png')
        return None

    valid = [r for r in results if r.get('out') and pathlib.Path(r['out']).is_file()]
    if not valid:
        return None

    cols = max(1, min(cols, len(valid)))
    rows = (len(valid) + cols - 1) // cols
    pad = 16
    label_h = 28
    cell_w = thumb_width
    cell_h = thumb_height + label_h
    sheet_w = pad + cols * (cell_w + pad)
    sheet_h = pad + rows * (cell_h + pad)

    sheet = Image.new('RGB', (sheet_w, sheet_h), (24, 24, 27))
    draw = ImageDraw.Draw(sheet)
    resample = getattr( getattr(Image, 'Resampling', Image), 'LANCZOS', Image.BICUBIC)

    for idx, item in enumerate(valid):
        r_idx, c_idx = divmod(idx, cols)
        x0 = pad + c_idx * (cell_w + pad)
        y0 = pad + r_idx * (cell_h + pad)

        # Header label bar
        draw.rectangle([x0, y0, x0 + cell_w - 1, y0 + label_h - 1], fill=(39, 39, 42))
        label = f"{item['route']} | {item['state']} | {item['viewport']}"
        draw.text((x0 + 8, y0 + 7), label[:42], fill=(244, 244, 245))

        # Thumbnail tile
        tile_y = y0 + label_h
        draw.rectangle([x0, tile_y, x0 + cell_w - 1, tile_y + thumb_height - 1], fill=(255, 255, 255))
        try:
            with Image.open(item['out']) as im:
                im_rgb = im.convert('RGB')
                scale = cell_w / max(1, im_rgb.width)
                scaled_h = max(1, int(round(im_rgb.height * scale)))
                resized = im_rgb.resize((cell_w, scaled_h), resample=resample)
                crop_h = min(thumb_height, resized.height)
                cropped = resized.crop((0, 0, cell_w, crop_h))
                sheet.paste(cropped, (x0, tile_y))
        except Exception:
            draw.text((x0 + 12, tile_y + 16), 'preview unavailable', fill=(113, 113, 122))
        draw.rectangle([x0, y0, x0 + cell_w - 1, y0 + cell_h - 1], outline=(63, 63, 70))

    out_file = pathlib.Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(str(out_file), format='PNG')
    return out_file


def render_routes(opts, browser=None):
    """Execute multi-route × state × viewport capture and checks from routes.json and RenderOptions."""
    opts = _coerce_options(opts)
    if not opts.routes:
        raise ValueError('render_routes requires opts.routes')
    cfg, base_dir = load_routes_config(opts.routes)
    out_dir = pathlib.Path(opts.out_dir or 'shots')
    out_dir.mkdir(parents=True, exist_ok=True)

    auth_cfg = cfg.get('auth') or {}
    storage_state = opts.storage_state or _resolve_auth_path(auth_cfg.get('storage_state'), base_dir, must_exist=True)
    login_script = opts.login_script or _resolve_auth_path(auth_cfg.get('login_script'), base_dir, must_exist=True)
    save_storage_state = opts.save_storage_state or _resolve_auth_path(auth_cfg.get('save_storage_state'), base_dir, must_exist=False)

    cli_viewports = _normalize_list_arg(opts.viewports)
    cfg_viewports = _normalize_list_arg(cfg.get('viewports')) or ['desktop']
    cli_states = _normalize_list_arg(opts.states)
    cfg_states = _normalize_list_arg(cfg.get('states'))

    base_uri, online, temp_html_file = _resolve_base_target(cfg['base_url'], base_dir=base_dir)
    if opts.online is not None:
        online = bool(opts.online)

    auth_opts = RenderOptions(
        width=opts.width,
        height=opts.height,
        storage_state=storage_state,
        login_script=login_script,
        save_storage_state=save_storage_state,
    )

    def _run_with_browser(active_browser):
        context = None
        owns_context = False
        if hasattr(active_browser, 'new_context'):
            owns_context = True
            if _has_auth(auth_opts):
                context = _open_auth_context(active_browser, base_uri, auth_opts)
            else:
                context = _new_context(active_browser, auth_opts)
        else:
            context = active_browser

        all_results = []
        route_summaries = {}
        try:
            for route_cfg in cfg['routes']:
                route_name = route_cfg['name'].strip()
                route_dir = out_dir / route_name
                route_dir.mkdir(parents=True, exist_ok=True)

                vp_specs = cli_viewports or _normalize_list_arg(route_cfg.get('viewports')) or cfg_viewports
                resolved_vps = [parse_viewport(vp) for vp in vp_specs]
                states = cli_states or _normalize_list_arg(route_cfg.get('states')) or cfg_states or ['default']

                route_results = []
                for state_name in states:
                    state_name = state_name.strip()
                    overrides = route_cfg.get('state_overrides')
                    state_ov = overrides.get(state_name) if isinstance(overrides, dict) and isinstance(overrides.get(state_name), dict) else {}
                    wait_for = state_ov.get('wait_for') or route_cfg.get('wait_for') or opts.wait_for
                    actions = state_ov.get('actions') if state_ov.get('actions') is not None else (
                        route_cfg.get('actions') if route_cfg.get('actions') is not None else opts.actions
                    )
                    dark = bool(state_ov.get('dark', route_cfg.get('dark', opts.dark)))

                    for vp_name, vp_w, vp_h in resolved_vps:
                        shot_path = route_dir / f'{state_name}-{vp_name}.png'
                        target_uri = _build_route_url(base_uri, route_cfg, state_name=state_name)
                        page = _new_page(context, {'width': vp_w, 'height': vp_h})
                        console_errors = []
                        network_errors = []
                        detach = _attach_error_listeners(page, console_errors, network_errors, online=online)
                        hook_cleanup = None
                        try:
                            hook_res = _apply_route_state(context, page, route_cfg, state_name)
                            if callable(hook_res):
                                hook_cleanup = hook_res
                            elif isinstance(hook_res, dict):
                                if hook_res.get('target_uri') or hook_res.get('url'):
                                    target_uri = hook_res.get('target_uri') or hook_res.get('url')
                                if callable(hook_res.get('cleanup')):
                                    hook_cleanup = hook_res['cleanup']

                            page.goto(target_uri)
                            wait_for_hydration(page, wait_for=wait_for, quiet_ms=150, max_wait_ms=5000)
                            if dark:
                                page.evaluate("document.documentElement.classList.add('dark')")
                            if actions:
                                run_actions(page, actions)
                            page.evaluate(SCROLL_SWEEP_JS)
                            page.wait_for_timeout(150)

                            page.screenshot(path=str(shot_path), full_page=True)
                            scroll_h = page.evaluate('document.documentElement.scrollHeight') or vp_h
                            findings = _run_viewport_checks(page, vp_w, console_errors, network_errors)

                            entry = {
                                'route': route_name,
                                'path': route_cfg.get('path', route_cfg.get('url', '')),
                                'url': target_uri,
                                'state': state_name,
                                'viewport': vp_name,
                                'width': vp_w,
                                'height': vp_h,
                                'scroll_height': scroll_h,
                                'out': str(shot_path),
                                'findings': findings,
                                'console_errors': console_errors,
                                'network_errors': network_errors,
                            }
                            route_results.append(entry)
                            all_results.append(entry)
                        finally:
                            if hook_cleanup is not None:
                                try:
                                    hook_cleanup()
                                except Exception:
                                    pass
                            detach()
                            page.close()

                check_file = _write_route_check_file(
                    route_dir,
                    route_name,
                    route_cfg.get('path', route_cfg.get('url', '')),
                    route_results,
                )
                for r in route_results:
                    r['check_file'] = str(check_file)
                route_summaries[route_name] = {
                    'check_file': str(check_file),
                    'captures': route_results,
                }
        finally:
            if owns_context and context is not None:
                context.close()

        report_path = _write_report_md(out_dir, all_results)
        contact_sheet_path = _build_contact_sheet(all_results, out_dir / 'contact-sheet.png')
        return {
            'out_dir': str(out_dir),
            'report': str(report_path),
            'contact_sheet': str(contact_sheet_path) if contact_sheet_path else None,
            'results': all_results,
            'routes': route_summaries,
        }

    try:
        if browser is not None:
            return _run_with_browser(browser)
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            sys.exit('render: Playwright missing. pip install playwright && python -m playwright install chromium')
        with sync_playwright() as p:
            launched = launch_browser(p)
            try:
                return _run_with_browser(launched)
            finally:
                launched.close()
    finally:
        if temp_html_file is not None:
            temp_html_file.unlink(missing_ok=True)


def build_parser():
    """Construct the CLI argument parser for render.py."""
    ap = argparse.ArgumentParser(
        description='Full-page screenshot of an HTML file or live URL (offline-friendly for files)')
    ap.add_argument('html', nargs='?', help='path to local HTML file (omit when using --url or --routes)')
    ap.add_argument('--url', help='live HTTP(S) URL to capture (e.g. http://localhost:3000/dashboard)')
    ap.add_argument('--out', help='output PNG path (required unless --routes is used)')
    ap.add_argument('--routes', metavar='PATH',
                    help='multi-route JSON configuration file (captures route x state x viewport matrix)')
    ap.add_argument('--out-dir', metavar='DIR', default='shots',
                    help='output directory for --routes mode (default: shots)')
    ap.add_argument('--viewports', nargs='+', metavar='VP',
                    help='override viewports for --routes (presets: desktop, laptop, tablet, mobile, mobile-375, or WxH; space or comma separated)')
    ap.add_argument('--states', nargs='+', metavar='ST',
                    help='override state list for --routes (e.g. default,empty,error; space or comma separated)')
    ap.add_argument('--dark', action='store_true', help="add class 'dark' to <html> before capturing")
    ap.add_argument('--width', type=int, default=1440)
    ap.add_argument('--height', type=int, default=900)
    ap.add_argument('--storage-state', metavar='PATH',
                    help='load a Playwright storageState JSON (cookies/localStorage) into the browser context. PRIVACY: it holds live session secrets; keep it out of git and never share it')
    ap.add_argument('--save-storage-state', metavar='PATH',
                    help='save the session (after load/login) to this JSON file. PRIVACY: the file holds live cookies/tokens; add it to .gitignore')
    ap.add_argument('--login-script', metavar='PATH',
                    help='Python file defining def login(page, base_url): run once before rendering the target')
    ap.add_argument('--wait-for', metavar='SELECTOR',
                    help='wait for this CSS selector to become visible after hydration/DOM stability before capturing or interacting')
    ap.add_argument('--check', action='store_true',
                    help='also print defects found in the rendered page: layout (clipped text, blank/half-empty panels, hidden content), axe accessibility, console errors, 375px mobile, dead buttons, focus rings')
    ap.epilog = (
        'Record a session:  python -m playwright codegen --save-storage=auth.json http://localhost:3000/login\n'
        'then:              python scripts/render.py --url http://localhost:3000/dashboard --storage-state auth.json --out p.png\n'
        'auth.json contains live cookies/tokens: never commit or share it. Cookie/token values are never printed.')
    ap.formatter_class = argparse.RawDescriptionHelpFormatter
    return ap


def parse_options(argv=None):
    """Parse and validate CLI arguments into a RenderOptions instance."""
    ap = build_parser()
    a = ap.parse_args(argv)
    viewports = _normalize_list_arg(a.viewports)
    if viewports is not None:
        if not viewports:
            ap.error('--viewports cannot be empty')
        for vp in viewports:
            try:
                parse_viewport(vp)
            except ValueError as exc:
                ap.error(str(exc))
    states = _normalize_list_arg(a.states)
    if states is not None and not states:
        ap.error('--states cannot be empty')

    if a.routes:
        if a.html or a.url:
            ap.error('cannot combine --routes with an HTML file or --url')
        return RenderOptions(
            out=a.out,
            dark=a.dark,
            width=a.width,
            height=a.height,
            check=True if not a.check else a.check,
            online=None,
            storage_state=a.storage_state,
            save_storage_state=a.save_storage_state,
            login_script=a.login_script,
            wait_for=a.wait_for,
            routes=a.routes,
            out_dir=a.out_dir or 'shots',
            viewports=viewports,
            states=states,
        )

    if bool(a.html) == bool(a.url):
        if not a.html and not a.url:
            ap.error('either an HTML file or --url must be provided')
        ap.error('cannot specify both an HTML file and --url')
    if not a.out:
        ap.error('the following arguments are required: --out')
    if a.url:
        parsed = urllib.parse.urlparse(a.url)
        if parsed.scheme not in ('http', 'https') or not parsed.netloc:
            ap.error(f'invalid --url {a.url!r}: expected http:// or https:// URL')
    return RenderOptions(
        html=a.html,
        url=a.url,
        out=a.out,
        dark=a.dark,
        width=a.width,
        height=a.height,
        check=a.check,
        online=bool(a.url),
        storage_state=a.storage_state,
        save_storage_state=a.save_storage_state,
        login_script=a.login_script,
        wait_for=a.wait_for,
        viewports=viewports,
        states=states,
    )


def render(opts):
    """Execute a single render/check run (or multi-route run if opts.routes is set) from RenderOptions/dict."""
    opts = _coerce_options(opts)
    if opts.routes:
        return render_routes(opts)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit('render: Playwright missing. pip install playwright && python -m playwright install chromium')

    page_file = None
    if opts.url:
        target_uri = opts.url
    elif opts.html:
        page_file = prepare_html_target(opts.html)
        target_uri = page_file.as_uri()
    else:
        raise ValueError('RenderOptions requires either html or url')

    try:
        with sync_playwright() as p:
            browser = launch_browser(p)
            context = None
            try:
                if _has_auth(opts):
                    context = _open_auth_context(browser, target_uri, opts)
                    return capture(context, target_uri, opts)
                return capture(browser, target_uri, opts)
            finally:
                if context is not None:
                    context.close()
                browser.close()
    finally:
        if page_file is not None:
            page_file.unlink(missing_ok=True)


def main(argv=None):
    opts = parse_options(argv)
    if opts.routes:
        summary = render_routes(opts)
        for item in summary['results']:
            for sev, rule, msg in item['findings']:
                print(f"  [{sev}] {rule}: {msg}")
            print(f"{item['out']} ({item['width']}x{item['scroll_height']})")
        print(f"REPORT: {summary['report']}")
        if summary.get('contact_sheet'):
            print(f"CONTACT_SHEET: {summary['contact_sheet']}")
        return
    result = render(opts)
    if opts.check:
        for sev, rule, msg in result['findings']:
            print(f"  [{sev}] {rule}: {msg}")
    print(f"{result['out']} ({result['width']}x{result['scroll_height']})")


if __name__ == '__main__':
    main()
