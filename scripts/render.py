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


@dataclass
class RenderOptions:
    """Configuration for rendering and optionally checking a local HTML file or live URL."""
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
            if kind == 'fill' and sel is not None and hasattr(page, 'fill'):
                page.fill(sel, str(act.get('value', '')))
            elif kind == 'click' and sel is not None and hasattr(page, 'click'):
                page.click(sel)
            elif kind == 'wait_for' and sel is not None and hasattr(page, 'wait_for_selector'):
                page.wait_for_selector(sel, state='visible', timeout=act.get('timeout', 5000))
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


def build_parser():
    """Construct the CLI argument parser for render.py."""
    ap = argparse.ArgumentParser(
        description='Full-page screenshot of an HTML file or live URL (offline-friendly for files)')
    ap.add_argument('html', nargs='?', help='path to local HTML file (omit when using --url)')
    ap.add_argument('--url', help='live HTTP(S) URL to capture (e.g. http://localhost:3000/dashboard)')
    ap.add_argument('--out', required=True, help='output PNG path')
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
    if bool(a.html) == bool(a.url):
        if not a.html and not a.url:
            ap.error('either an HTML file or --url must be provided')
        ap.error('cannot specify both an HTML file and --url')
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
    )


def render(opts):
    """Execute a single render/check run from a RenderOptions (or dict) and return capture result."""
    opts = _coerce_options(opts)
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
    result = render(opts)
    if opts.check:
        for sev, rule, msg in result['findings']:
            print(f"  [{sev}] {rule}: {msg}")
    print(f"{result['out']} ({result['width']}x{result['scroll_height']})")


if __name__ == '__main__':
    main()
