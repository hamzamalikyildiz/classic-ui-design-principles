"""Tests for scripts/render.py multi-route capture (İP-B3 & S3 acceptance test):
--routes, --viewports, --states, --out-dir, VIEWPORT_PRESETS, REPORT.md, and contact-sheet.png.
"""
import contextlib
import http.server
import importlib.util
import io
import json
import pathlib
import tempfile
import threading
import unittest
import urllib.parse
from unittest import mock

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('render', ROOT / 'scripts' / 'render.py')
rd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rd)


def _browser_available():
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            rd.launch_browser(p).close()
        return True
    except BaseException:
        return False


class _FakeRoutePage:
    """Fake Playwright Page recording calls for unit-testing render_routes."""

    def __init__(self, scroll_height=920):
        self.listeners = {}
        self.init_scripts = []
        self.visited = []
        self.screenshots = []
        self.clicked = []
        self.filled = []
        self.evaluated = []
        self.viewport = {'width': 1440, 'height': 900}
        self.closed = False
        self._scroll_height = scroll_height

    def on(self, event, fn):
        self.listeners.setdefault(event, []).append(fn)

    def remove_listener(self, event, fn):
        if event in self.listeners and fn in self.listeners[event]:
            self.listeners[event].remove(fn)

    def set_viewport_size(self, viewport):
        self.viewport = dict(viewport)

    def add_init_script(self, script):
        self.init_scripts.append(script)

    def goto(self, uri):
        self.visited.append(uri)

    def wait_for_load_state(self, state, timeout=None):
        pass

    def wait_for_selector(self, selector, state=None, timeout=None):
        pass

    def wait_for_timeout(self, ms):
        pass

    def click(self, selector):
        self.clicked.append(selector)

    def fill(self, selector, value):
        self.filled.append((selector, value))

    def screenshot(self, path, full_page=True):
        im = Image.new('RGB', (self.viewport['width'], 240), (50, 90, 160))
        im.save(path, format='PNG')
        self.screenshots.append((path, full_page, dict(self.viewport)))

    def evaluate(self, expr, arg=None):
        self.evaluated.append(expr)
        if isinstance(arg, dict) and 'quietMs' in arg:
            return {'timedOut': False, 'detected': True, 'elapsedMs': 10}
        if expr == 'document.documentElement.scrollHeight':
            return self._scroll_height
        if expr in (rd.CHECK_JS, rd.INTERACT_JS, rd.MOBILE_JS):
            return []
        return None

    def close(self):
        self.closed = True


class _FakeContext:
    def __init__(self):
        self.pages = []
        self.closed = False
        self.saved_storage_paths = []

    def new_page(self):
        page = _FakeRoutePage()
        self.pages.append(page)
        return page

    def storage_state(self, path=None):
        if path:
            pathlib.Path(path).write_text('{"cookies":[],"origins":[]}', encoding='utf-8')
            self.saved_storage_paths.append(path)
        return {'cookies': [], 'origins': []}

    def close(self):
        self.closed = True


class _FakeBrowserWithContext:
    def __init__(self):
        self.contexts = []

    def new_context(self, **kwargs):
        ctx = _FakeContext()
        ctx.kwargs = kwargs
        self.contexts.append(ctx)
        return ctx


class ViewportAndCliUnitTests(unittest.TestCase):
    def test_viewport_presets_values(self):
        self.assertEqual(rd.VIEWPORT_PRESETS['desktop'], (1440, 900))
        self.assertEqual(rd.VIEWPORT_PRESETS['laptop'], (1280, 800))
        self.assertEqual(rd.VIEWPORT_PRESETS['tablet'], (834, 1112))
        self.assertEqual(rd.VIEWPORT_PRESETS['mobile'], (390, 844))
        self.assertEqual(rd.VIEWPORT_PRESETS['mobile-375'], (375, 800))
        self.assertEqual(rd.VIEWPORT_PRESETS['legacy-mobile'], (375, 800))

    def test_parse_viewport_presets_and_custom_wxh(self):
        self.assertEqual(rd.parse_viewport('desktop'), ('desktop', 1440, 900))
        self.assertEqual(rd.parse_viewport(' MOBILE '), ('mobile', 390, 844))
        self.assertEqual(rd.parse_viewport('tablet'), ('tablet', 834, 1112))
        self.assertEqual(rd.parse_viewport('laptop'), ('laptop', 1280, 800))
        self.assertEqual(rd.parse_viewport('mobile-375'), ('mobile-375', 375, 800))
        self.assertEqual(rd.parse_viewport('legacy-mobile'), ('legacy-mobile', 375, 800))
        self.assertEqual(rd.parse_viewport('375x800'), ('375x800', 375, 800))
        self.assertEqual(rd.parse_viewport('1920X1080'), ('1920x1080', 1920, 1080))
        self.assertEqual(rd.parse_viewport({'name': 'wide', 'width': 1600, 'height': 900}), ('wide', 1600, 900))

        for bad in ('', '   ', 'watch', '0x800', '400x0', 'abcxdef', None):
            with self.assertRaises(ValueError, msg=f'expected ValueError for {bad!r}'):
                rd.parse_viewport(bad)

    def test_cli_routes_flags_and_overrides(self):
        opts = rd.parse_options(['--routes', 'routes.json'])
        self.assertEqual(opts.routes, 'routes.json')
        self.assertEqual(opts.out_dir, 'shots')
        self.assertIsNone(opts.html)
        self.assertIsNone(opts.url)
        self.assertIsNone(opts.out)
        self.assertTrue(opts.check)
        self.assertIsNone(opts.viewports)
        self.assertIsNone(opts.states)

        opts_override = rd.parse_options([
            '--routes', 'routes.json',
            '--out-dir', 'custom-shots',
            '--viewports', 'desktop,mobile', '375x800',
            '--states', 'default,empty', 'error',
        ])
        self.assertEqual(opts_override.out_dir, 'custom-shots')
        self.assertEqual(opts_override.viewports, ['desktop', 'mobile', '375x800'])
        self.assertEqual(opts_override.states, ['default', 'empty', 'error'])

    def test_cli_rejects_routes_combined_with_html_or_url_or_bad_viewport(self):
        for argv, expected_err in (
            (['page.html', '--routes', 'routes.json'], 'cannot combine --routes'),
            (['--url', 'http://localhost:3000', '--routes', 'routes.json'], 'cannot combine --routes'),
            (['--routes', 'routes.json', '--viewports', 'not-a-viewport'], 'unknown viewport'),
        ):
            buf = io.StringIO()
            with contextlib.redirect_stderr(buf):
                with self.assertRaises(SystemExit) as ctx:
                    rd.parse_options(argv)
            self.assertEqual(ctx.exception.code, 2)
            self.assertIn(expected_err, buf.getvalue())

    def test_validate_routes_config_checks_schema(self):
        valid_cfg = {
            'base_url': 'http://localhost:3000',
            'auth': {'storage_state': 'auth.json', 'login_script': 'login.py', 'save_storage_state': 'auth.json'},
            'viewports': ['desktop', 'mobile'],
            'routes': [
                {'name': 'cv-list', 'path': '/cv', 'wait_for': '[data-ready]',
                 'states': ['default', 'empty', 'loading', 'long-loading', 'error']},
                {'name': 'cv-detail', 'path': '/cv/42', 'actions': [{'click': 'text=Öneriler'}]},
            ],
        }
        self.assertEqual(rd.validate_routes_config(valid_cfg)['base_url'], 'http://localhost:3000')

        invalid_configs = [
            [],
            {},
            {'base_url': '', 'routes': [{'name': 'a', 'path': '/'}]},
            {'base_url': 'http://localhost:3000', 'routes': []},
            {'base_url': 'http://localhost:3000', 'routes': [{'name': '', 'path': '/'}]},
            {'base_url': 'http://localhost:3000', 'routes': [{'name': '../escape', 'path': '/'}]},
            {'base_url': 'http://localhost:3000', 'routes': [{'name': 'a'}]},
            {'base_url': 'http://localhost:3000', 'routes': [{'name': 'dup', 'path': '/1'}, {'name': 'dup', 'path': '/2'}]},
            {'base_url': 'http://localhost:3000', 'viewports': ['bad_vp'], 'routes': [{'name': 'a', 'path': '/'}]},
            {'base_url': 'http://localhost:3000', 'auth': 'not-a-dict', 'routes': [{'name': 'a', 'path': '/'}]},
        ]
        for bad_cfg in invalid_configs:
            with self.assertRaises(ValueError, msg=f'expected ValueError for {bad_cfg!r}'):
                rd.validate_routes_config(bad_cfg)

    def test_build_route_url_supports_http_and_file_hash_routing(self):
        self.assertEqual(
            rd._build_route_url('http://localhost:3000', {'name': 'cv', 'path': '/cv'}, 'default'),
            'http://localhost:3000/cv',
        )
        self.assertEqual(
            rd._build_route_url('http://localhost:3000', {'name': 'cv', 'path': '/cv'}, 'empty'),
            'http://localhost:3000/cv?state=empty',
        )
        self.assertEqual(
            rd._build_route_url('file:///tmp/app.html', {'name': 'list', 'path': '#/list'}, 'default'),
            'file:///tmp/app.html#/list',
        )
        self.assertEqual(
            rd._build_route_url('file:///tmp/app.html', {'name': 'list', 'path': '/list'}, 'error'),
            'file:///tmp/app.html?state=error#/list',
        )

    def test_shorthand_actions_and_fake_browser_render_routes(self):
        with tempfile.TemporaryDirectory() as d:
            d = pathlib.Path(d)
            login_py = d / 'login.py'
            login_py.write_text('def login(page, base_url):\n    page.goto(base_url + "/login")\n', encoding='utf-8')
            routes_file = d / 'routes.json'
            routes_file.write_text(json.dumps({
                'base_url': 'http://localhost:3000',
                'auth': {'login_script': 'login.py', 'save_storage_state': 'saved_auth.json'},
                'viewports': ['desktop', 'mobile'],
                'routes': [
                    {'name': 'cv-list', 'path': '/cv', 'wait_for': '[data-ready]', 'states': ['default', 'empty']},
                    {'name': 'cv-detail', 'path': '/cv/42', 'actions': [{'click': 'text=Öneriler'}]},
                ],
            }), encoding='utf-8')
            out_dir = d / 'shots'
            browser = _FakeBrowserWithContext()

            with mock.patch.object(rd, 'find_axe', return_value=None):
                summary = rd.render_routes(
                    rd.RenderOptions(routes=str(routes_file), out_dir=str(out_dir)),
                    browser=browser,
                )

            # Single shared BrowserContext across all routes
            self.assertEqual(len(browser.contexts), 1)
            self.assertTrue(browser.contexts[0].closed)
            self.assertTrue((d / 'saved_auth.json').is_file())
            # 1 login page + (2 states * 2 viewports for cv-list) + (1 state * 2 viewports for cv-detail) = 7 pages
            self.assertEqual(len(browser.contexts[0].pages), 7)
            self.assertEqual(len(summary['results']), 6)

            for route_name, state_name, vp_name in (
                ('cv-list', 'default', 'desktop'),
                ('cv-list', 'default', 'mobile'),
                ('cv-list', 'empty', 'desktop'),
                ('cv-list', 'empty', 'mobile'),
                ('cv-detail', 'default', 'desktop'),
                ('cv-detail', 'default', 'mobile'),
            ):
                self.assertTrue((out_dir / route_name / f'{state_name}-{vp_name}.png').is_file())
            self.assertTrue((out_dir / 'cv-list' / 'check.txt').is_file())
            self.assertTrue((out_dir / 'cv-detail' / 'check.txt').is_file())
            self.assertTrue((out_dir / 'REPORT.md').is_file())
            self.assertTrue((out_dir / 'contact-sheet.png').is_file())

            # Verify shorthand click action executed on cv-detail pages
            detail_pages = [p for p in browser.contexts[0].pages if any('/cv/42' in u for u in p.visited)]
            self.assertEqual(len(detail_pages), 2)
            for dp in detail_pages:
                self.assertEqual(dp.clicked, ['text=Öneriler'])


SESSION_TOKEN = 's3_authenticated_token_987'


def _render_app_page(route_key, state, is_authed):
    if not is_authed and route_key != 'login':
        return 401, (
            '<!doctype html><html lang="tr"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Giriş Gerekli</title></head><body><main><h1>401 Yetkisiz</h1></main></body></html>'
        ).encode('utf-8')

    titles = {
        'dashboard': 'Genel Bakış Paneli',
        'cv': 'Özgeçmiş Listesi',
        'cv-detail': 'Özgeçmiş #42 İncelemesi',
        'settings': 'Hesap ve Bildirim Ayarları',
        'login': 'Kullanıcı Girişi',
    }
    title = titles.get(route_key, 'Uygulama')

    if state == 'empty':
        content_block = (
            '<section class="panel" data-state-view="empty">'
            '<h2>Henüz kayıt bulunmuyor</h2>'
            '<p>Yeni bir özgeçmiş yükleyerek analizi başlatabilirsiniz.</p>'
            '<button type="button" class="btn" onclick="this.dataset.clicked=\'1\'">Yeni Özgeçmiş Yükle</button>'
            '</section>'
        )
    elif state == 'error':
        content_block = (
            '<section class="panel error-banner" role="alert" data-state-view="error">'
            '<h2>Veri yüklenirken bağlantı hatası oluştu</h2>'
            '<p>Sunucu yanıt vermedi (kod: E_TIMEOUT). Lütfen tekrar deneyin.</p>'
            '<button type="button" class="btn" onclick="this.dataset.retried=\'1\'">Tekrar Dene</button>'
            '</section>'
        )
    else:
        content_block = (
            '<section class="grid" data-state-view="default">'
            '<article class="card"><h2>Çağla İnanç — Kıdemli Ürün Tasarımcısı</h2>'
            '<p>Uyum Skoru: 73 / 100 · Son güncelleme: 14 dk önce</p></article>'
            '<article class="card"><h2>Şahin Öztürk — Veri Mühendisi</h2>'
            '<p>Uyum Skoru: 81 / 100 · Son güncelleme: Dün</p></article>'
            '</section>'
        )

    extra_detail = ''
    if route_key == 'cv-detail':
        extra_detail = (
            '<div class="tabs">'
            '<button type="button" class="btn" '
            'onclick="document.getElementById(\'recommendations-panel\').textContent=\'6 Yapay Zeka Önerisi Hazır\'">'
            'Öneriler</button>'
            '<div id="recommendations-panel" class="rec-box">Sekme seçilmedi</div>'
            '</div>'
        )

    html = f"""<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <link rel="icon" href="data:,">
  <title>{title} ({state})</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      margin: 0;
      padding: 20px;
      background: #f8fafc;
      color: #0f172a;
      line-height: 1.5;
    }}
    header, main {{
      max-width: 960px;
      margin: 0 auto;
    }}
    header {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding-bottom: 16px;
      margin-bottom: 20px;
      border-bottom: 1px solid #cbd5e1;
    }}
    nav {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    nav a, .btn {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 44px;
      padding: 10px 16px;
      border-radius: 8px;
      border: 1px solid #334155;
      background: #1e293b;
      color: #ffffff;
      font-size: 15px;
      font-weight: 600;
      text-decoration: none;
      cursor: pointer;
    }}
    nav a:focus-visible, .btn:focus-visible {{
      outline: 3px solid #2563eb;
      outline-offset: 2px;
    }}
    h1 {{ font-size: 24px; margin: 0 0 12px; color: #0f172a; }}
    h2 {{ font-size: 18px; margin: 0 0 8px; color: #0f172a; }}
    p {{ font-size: 15px; margin: 0 0 12px; color: #334155; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 16px;
    }}
    .card, .panel {{
      background: #ffffff;
      border: 1px solid #cbd5e1;
      border-radius: 10px;
      padding: 18px;
    }}
    .error-banner {{
      border-color: #dc2626;
      background: #fef2f2;
    }}
    .tabs {{ margin-top: 16px; }}
    .rec-box {{
      margin-top: 12px;
      padding: 14px;
      background: #ffffff;
      border: 1px solid #94a3b8;
      border-radius: 8px;
      font-size: 15px;
      color: #0f172a;
    }}
  </style>
</head>
<body>
  <header>
    <strong>CV Optimizasyon Platformu</strong>
    <nav aria-label="Ana menü">
      <a href="/dashboard">Panel</a>
      <a href="/cv">Özgeçmişler</a>
      <a href="/settings">Ayarlar</a>
    </nav>
  </header>
  <main id="app-root" data-ready="true" data-route="{route_key}" data-state="{state}">
    <h1>{title}</h1>
    <p>Aktif görünüm durumu: <strong>{state}</strong></p>
    {content_block}
    {extra_detail}
  </main>
</body>
</html>"""
    return 200, html.encode('utf-8')


class _S3AppHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        state = (qs.get('state') or ['default'])[0]
        cookie_hdr = self.headers.get('Cookie') or ''
        is_authed = f'session={SESSION_TOKEN}' in cookie_hdr

        route_map = {
            '/login': 'login',
            '/dashboard': 'dashboard',
            '/cv': 'cv',
            '/cv/42': 'cv-detail',
            '/settings': 'settings',
        }
        route_key = route_map.get(parsed.path)
        if route_key is None:
            self.send_response(404)
            self.end_headers()
            return

        self.server.requests_log.append({
            'path': parsed.path,
            'state': state,
            'authed': is_authed,
        })
        status, body = _render_app_page(route_key, state, is_authed)
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@unittest.skipUnless(_browser_available(), 'Playwright/Chromium not available')
class S3MultiRouteLiveServerIntegrationTest(unittest.TestCase):
    """S3 acceptance test: 4 authenticated screens x 2 viewports (desktop, mobile) x 3 states (default, empty, error)."""

    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), _S3AppHandler)
        cls.server.requests_log = []
        cls.base_url = f'http://127.0.0.1:{cls.server.server_address[1]}'
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_s3_end_to_end_4_routes_2_viewports_3_states(self):
        self.server.requests_log.clear()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            login_script = tmp_dir / 'login.py'
            login_script.write_text(
                f"def login(page, base_url):\n"
                f"    page.goto(base_url + '/login')\n"
                f"    page.evaluate(\"document.cookie = 'session={SESSION_TOKEN}; path=/'\")\n",
                encoding='utf-8',
            )
            saved_auth = tmp_dir / 'auth.json'
            shots_dir = tmp_dir / 'shots'
            routes_cfg = {
                'base_url': self.base_url,
                'auth': {
                    'login_script': 'login.py',
                    'save_storage_state': 'auth.json',
                },
                'viewports': ['desktop', 'mobile'],
                'routes': [
                    {
                        'name': 'dashboard',
                        'path': '/dashboard',
                        'wait_for': '[data-ready="true"]',
                        'states': ['default', 'empty', 'error'],
                    },
                    {
                        'name': 'cv-list',
                        'path': '/cv',
                        'wait_for': '[data-ready="true"]',
                        'states': ['default', 'empty', 'error'],
                    },
                    {
                        'name': 'cv-detail',
                        'path': '/cv/42',
                        'wait_for': '[data-ready="true"]',
                        'states': ['default', 'empty', 'error'],
                        'actions': [{'click': 'text=Öneriler'}],
                    },
                    {
                        'name': 'settings',
                        'path': '/settings',
                        'wait_for': '[data-ready="true"]',
                        'states': ['default', 'empty', 'error'],
                    },
                ],
            }
            routes_path = tmp_dir / 'routes.json'
            routes_path.write_text(json.dumps(routes_cfg, ensure_ascii=False, indent=2), encoding='utf-8')

            stdout = io.StringIO()
            stderr = io.StringIO()
            with mock.patch.object(rd, 'find_axe', return_value=None), \
                 contextlib.redirect_stdout(stdout), \
                 contextlib.redirect_stderr(stderr):
                rd.main(['--routes', str(routes_path), '--out-dir', str(shots_dir)])

            # 1. Verify single authenticated session shared across all 4 routes x 3 states x 2 viewports
            self.assertTrue(saved_auth.is_file(), 'auth.json should be saved after login_script runs')
            protected_hits = [r for r in self.server.requests_log if r['path'] != '/login']
            self.assertEqual(len(protected_hits), 24, f'Expected 24 route hits, got {len(protected_hits)}')
            self.assertTrue(all(r['authed'] for r in protected_hits), 'All 24 route hits must carry session cookie')

            # 2. Verify all 24 <route>/<state>-<viewport>.png screenshots & their dimensions
            expected_routes = ('dashboard', 'cv-list', 'cv-detail', 'settings')
            expected_states = ('default', 'empty', 'error')
            expected_viewports = (('desktop', 1440), ('mobile', 390))

            for r_name in expected_routes:
                check_txt = shots_dir / r_name / 'check.txt'
                self.assertTrue(check_txt.is_file(), f'Missing {check_txt}')
                check_content = check_txt.read_text(encoding='utf-8')
                self.assertIn(f'# Route: {r_name}', check_content)

                for st_name in expected_states:
                    for vp_name, expected_w in expected_viewports:
                        png_path = shots_dir / r_name / f'{st_name}-{vp_name}.png'
                        self.assertTrue(png_path.is_file(), f'Missing screenshot: {png_path}')
                        self.assertGreater(png_path.stat().st_size, 500)
                        with Image.open(png_path) as im:
                            self.assertEqual(im.width, expected_w, f'Wrong width for {png_path}')
                            self.assertGreater(im.height, 200)
                        self.assertIn(f'[{st_name} / {vp_name}]', check_content)

            # 3. Verify REPORT.md table and rows
            report_md = shots_dir / 'REPORT.md'
            self.assertTrue(report_md.is_file(), 'Missing shots/REPORT.md')
            report_text = report_md.read_text(encoding='utf-8')
            self.assertIn('| Route | State | Viewport | Size | FAIL | WARN | INFO | Screenshot |', report_text)
            for r_name in expected_routes:
                for st_name in expected_states:
                    for vp_name, _ in expected_viewports:
                        self.assertIn(f'{r_name}/{st_name}-{vp_name}.png', report_text)

            # 4. Verify contact-sheet.png is generated and valid
            contact_sheet = shots_dir / 'contact-sheet.png'
            self.assertTrue(contact_sheet.is_file(), 'Missing shots/contact-sheet.png')
            with Image.open(contact_sheet) as sheet_im:
                self.assertGreater(sheet_im.width, 600)
                self.assertGreater(sheet_im.height, 400)

    def test_single_html_hash_routing_with_routes_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            app_html = tmp_dir / 'spa.html'
            app_html.write_text(
                '<!doctype html><html lang="tr"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                '<title>SPA</title>'
                '<style>body{font-family:sans-serif;margin:0;padding:24px;background:#fff;color:#111}'
                '.card{padding:16px;border:1px solid #ccc;border-radius:8px}</style>'
                '</head><body><main id="view" data-ready="true">'
                '<div class="card"><h1 id="title">SPA</h1><p id="info">Hazır</p></div>'
                '</main>'
                '<script>'
                'const renderHash = () => {'
                '  const h = window.location.hash || "#/list";'
                '  const st = window.__RENDER_STATE__ || "default";'
                '  document.getElementById("title").textContent = "Ekran: " + h;'
                '  document.getElementById("info").textContent = "Durum: " + st;'
                '};'
                'window.addEventListener("hashchange", renderHash);'
                'renderHash();'
                '</script></body></html>',
                encoding='utf-8',
            )
            routes_path = tmp_dir / 'routes.json'
            routes_path.write_text(json.dumps({
                'base_url': 'spa.html',
                'viewports': ['desktop', 'mobile'],
                'routes': [
                    {'name': 'list-view', 'path': '#/list', 'wait_for': '[data-ready="true"]', 'states': ['default', 'empty']},
                    {'name': 'detail-view', 'path': '#/detail/42', 'wait_for': '[data-ready="true"]'},
                ],
            }), encoding='utf-8')
            shots_dir = tmp_dir / 'spa-shots'

            with mock.patch.object(rd, 'find_axe', return_value=None):
                summary = rd.render_routes(rd.RenderOptions(routes=str(routes_path), out_dir=str(shots_dir)))

            self.assertEqual(len(summary['results']), 6)
            self.assertTrue((shots_dir / 'list-view' / 'default-desktop.png').is_file())
            self.assertTrue((shots_dir / 'list-view' / 'empty-mobile.png').is_file())
            self.assertTrue((shots_dir / 'detail-view' / 'default-desktop.png').is_file())
            self.assertTrue((shots_dir / 'REPORT.md').is_file())
            self.assertTrue((shots_dir / 'contact-sheet.png').is_file())


if __name__ == '__main__':
    unittest.main()
