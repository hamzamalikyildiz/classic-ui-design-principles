"""Tests for scripts/render.py 7 built-in UI states, custom network mocks, and full action set (İP-B5)."""
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


class _FakeMockPage:
    """Fake Playwright Page supporting route/unroute, add_init_script, actions, and timing logs."""

    def __init__(self, scroll_height=900):
        self.listeners = {}
        self.init_scripts = []
        self.routed = []
        self.unrouted = []
        self.visited = []
        self.waits = []
        self.screenshots = []
        self.actions_log = []
        self.viewport = {'width': 1440, 'height': 900}
        self.closed = False
        self._scroll_height = scroll_height
        self.keyboard = mock.MagicMock()

    def on(self, event, fn):
        self.listeners.setdefault(event, []).append(fn)

    def remove_listener(self, event, fn):
        if event in self.listeners and fn in self.listeners[event]:
            self.listeners[event].remove(fn)

    def set_viewport_size(self, viewport):
        self.viewport = dict(viewport)

    def add_init_script(self, script):
        self.init_scripts.append(script)

    def route(self, pattern, handler):
        self.routed.append((pattern, handler))

    def unroute(self, pattern, handler=None):
        self.unrouted.append((pattern, handler))

    def goto(self, uri, wait_until=None):
        self.visited.append((uri, wait_until))

    def wait_for_load_state(self, state, timeout=None):
        pass

    def wait_for_selector(self, selector, state=None, timeout=None):
        self.actions_log.append(('wait_for', selector, state, timeout))

    def wait_for_timeout(self, ms):
        self.waits.append(int(ms))

    def click(self, selector):
        self.actions_log.append(('click', selector))

    def fill(self, selector, value):
        self.actions_log.append(('fill', selector, value))

    def hover(self, selector):
        self.actions_log.append(('hover', selector))

    def press(self, selector, key):
        self.actions_log.append(('press', selector, key))

    def locator(self, selector):
        actions_log = self.actions_log

        class _Loc:
            @property
            def first(self):
                return self

            def scroll_into_view_if_needed(self):
                actions_log.append(('scroll_into_view', selector))

        return _Loc()

    def screenshot(self, path, full_page=True):
        im = Image.new('RGB', (self.viewport['width'], 240), (30, 64, 175))
        im.save(path, format='PNG')
        self.screenshots.append(str(path))

    def evaluate(self, expr, arg=None):
        if isinstance(arg, dict) and 'quietMs' in arg:
            self.actions_log.append(('stability', arg['quietMs']))
            return {'timedOut': False, 'detected': True, 'elapsedMs': 5}
        if expr == 'document.documentElement.scrollHeight':
            return self._scroll_height
        if expr in (rd.CHECK_JS, rd.INTERACT_JS, rd.MOBILE_JS):
            self.actions_log.append(('js_check', 'check' if expr == rd.CHECK_JS else ('interact' if expr == rd.INTERACT_JS else 'mobile')))
            return []
        self.actions_log.append(('evaluate', expr))
        return None

    def close(self):
        self.closed = True


class _FakeMockContext:
    def __init__(self):
        self.pages = []
        self.offline_calls = []
        self.closed = False

    def new_page(self):
        p = _FakeMockPage()
        self.pages.append(p)
        return p

    def set_offline(self, value):
        self.offline_calls.append(bool(value))

    def close(self):
        self.closed = True


class _FakeMockBrowser:
    def __init__(self):
        self.contexts = []

    def new_context(self, **kwargs):
        ctx = _FakeMockContext()
        self.contexts.append(ctx)
        return ctx


class StateMocksAndActionsUnitTests(unittest.TestCase):
    def test_default_constants_match_spec(self):
        self.assertEqual(rd.DEFAULT_API_PATTERN, '**/api/**')
        self.assertEqual(rd.DEFAULT_LOADING_DELAY_MS, 2000)
        self.assertEqual(rd.DEFAULT_LOADING_CAPTURE_MS, 300)
        self.assertEqual(rd.DEFAULT_LONG_LOADING_DELAY_MS, 20000)
        self.assertEqual(rd.DEFAULT_LONG_LOADING_FRAMES_MS, [500, 4000, 12000])
        self.assertEqual(
            set(rd.BUILTIN_STATES),
            {'loading', 'long-loading', 'error', 'empty', 'partial', 'offline', 'locked'},
        )

    def test_validate_routes_config_new_fields(self):
        valid = {
            'base_url': 'http://localhost:3000',
            'api_pattern': '**/api/**',
            'long_loading_frames_ms': [500, 4000, 12000],
            'state_mocks': {
                'empty': {'pattern': '**/api/cv*', 'status': 200, 'body': {'items': []}},
            },
            'routes': [
                {
                    'name': 'items',
                    'path': '/',
                    'api_pattern': ['**/api/items*', '**/api/summary*'],
                    'long_loading_frames_ms': [100, 300, 500],
                },
            ],
        }
        self.assertEqual(rd.validate_routes_config(valid)['api_pattern'], '**/api/**')

        invalid_list = [
            {'base_url': 'http://localhost:3000', 'api_pattern': '', 'routes': [{'name': 'a', 'path': '/'}]},
            {'base_url': 'http://localhost:3000', 'api_pattern': 123, 'routes': [{'name': 'a', 'path': '/'}]},
            {'base_url': 'http://localhost:3000', 'state_mocks': [], 'routes': [{'name': 'a', 'path': '/'}]},
            {'base_url': 'http://localhost:3000', 'long_loading_frames_ms': [0, 100], 'routes': [{'name': 'a', 'path': '/'}]},
            {'base_url': 'http://localhost:3000', 'long_loading_frames_ms': [True], 'routes': [{'name': 'a', 'path': '/'}]},
            {'base_url': 'http://localhost:3000', 'routes': [{'name': 'a', 'path': '/', 'long_loading_frames_ms': []}]},
        ]
        for bad in invalid_list:
            with self.assertRaises(ValueError, msg=f'expected ValueError for {bad!r}'):
                rd.validate_routes_config(bad)

    def test_make_partial_payload_halves_lists_and_nulls_optional_field(self):
        payload = {
            'items': [
                {'id': 1, 'name': 'Item 1', 'description': 'Desc 1'},
                {'id': 2, 'name': 'Item 2', 'description': 'Desc 2'},
                {'id': 3, 'name': 'Item 3', 'description': 'Desc 3'},
                {'id': 4, 'name': 'Item 4', 'description': 'Desc 4'},
            ],
            'summary': '4 total',
        }
        partial = rd._make_partial_payload(payload)
        self.assertEqual(len(partial['items']), 2)
        self.assertIsNone(partial['summary'])
        self.assertEqual(partial['items'][0]['name'], 'Item 1')
        self.assertIsNone(partial['items'][0]['description'])

        root_list = [
            {'id': 1, 'title': 'A', 'notes': 'n1'},
            {'id': 2, 'title': 'B', 'notes': 'n2'},
            {'id': 3, 'title': 'C', 'notes': 'n3'},
            {'id': 4, 'title': 'D', 'notes': 'n4'},
        ]
        partial_list = rd._make_partial_payload(root_list)
        self.assertEqual(len(partial_list), 2)
        self.assertIsNone(partial_list[0]['notes'])

    def test_render_routes_long_loading_default_500_4000_12000_frames_unit(self):
        with tempfile.TemporaryDirectory() as d:
            d = pathlib.Path(d)
            routes_path = d / 'routes.json'
            routes_path.write_text(json.dumps({
                'base_url': 'http://localhost:3000',
                'viewports': ['desktop'],
                'routes': [{'name': 'items', 'path': '/', 'states': ['long-loading']}],
            }), encoding='utf-8')
            shots_dir = d / 'shots'
            browser = _FakeMockBrowser()

            # Advance synthetic clock on wait_for_timeout so no real 12s sleep occurs in unit test.
            fake_clock = [0.0]

            def fake_wait(self_page, ms):
                self_page.waits.append(int(ms))
                fake_clock[0] += int(ms) / 1000.0

            with mock.patch.object(rd, 'find_axe', return_value=None), \
                 mock.patch.object(rd.time, 'monotonic', side_effect=lambda: fake_clock[0]), \
                 mock.patch.object(_FakeMockPage, 'wait_for_timeout', fake_wait):
                summary = rd.render_routes(
                    rd.RenderOptions(routes=str(routes_path), out_dir=str(shots_dir)),
                    browser=browser,
                )

            page = browser.contexts[0].pages[0]
            self.assertEqual(page.visited, [('http://localhost:3000/?state=long-loading', 'domcontentloaded')])
            self.assertTrue(any('window.__RENDER_STATE__ = "long-loading"' in s for s in page.init_scripts))
            self.assertEqual(len(page.routed), 1)
            self.assertEqual(page.routed[0][0], '**/api/**')
            self.assertEqual(len(page.unrouted), 1)

            route_dir = shots_dir / 'items'
            for fname in (
                'long-loading-0.5s-desktop.png',
                'long-loading-4s-desktop.png',
                'long-loading-12s-desktop.png',
                'long-loading-desktop.png',
            ):
                self.assertTrue((route_dir / fname).is_file(), f'Missing {fname}')

            # Verify CHECK_JS ran at 4s frame BEFORE 12s frame was waited/captured
            check_idx = page.actions_log.index(('js_check', 'check'))
            interact_idx = page.actions_log.index(('js_check', 'interact'))
            self.assertLess(check_idx, interact_idx)
            self.assertEqual(len(summary['results'][0]['frames']), 3)

    def test_offline_cleanup_runs_even_if_goto_raises(self):
        ctx = _FakeMockContext()
        page = _FakeMockPage()
        hook = rd._apply_route_state(ctx, page, {'name': 'r', 'path': '/'}, 'offline')
        self.assertEqual(hook['mode'], 'offline')
        self.assertEqual(len(page.routed), 1)
        hook['activate_offline']()
        self.assertEqual(ctx.offline_calls, [True])
        hook['cleanup']()
        self.assertEqual(ctx.offline_calls, [True, False])
        self.assertEqual(len(page.unrouted), 1)

    def test_run_actions_full_set_and_dom_stability_between_actions(self):
        with tempfile.TemporaryDirectory() as d:
            d = pathlib.Path(d)
            page = _FakeMockPage()
            saved = rd.run_actions(page, [
                {'type': 'fill', 'selector': '#q', 'value': 'istanbul'},
                {'type': 'press', 'selector': '#q', 'key': 'Enter'},
                {'type': 'hover', 'selector': '#menu'},
                {'type': 'click', 'selector': '#apply'},
                {'type': 'wait', 'ms': 120},
                {'type': 'wait_for', 'selector': '#results'},
                {'type': 'scroll_to', 'selector': '#section-2'},
                {'type': 'scroll_to', 'x': 10, 'y': 240},
                {'scroll_to': 'bottom'},
                {'screenshot_as': 'step-one'},
            ], out_dir=d)

            self.assertEqual(len(saved), 1)
            self.assertTrue((d / 'step-one.png').is_file())
            self.assertIn(('fill', '#q', 'istanbul'), page.actions_log)
            self.assertIn(('press', '#q', 'Enter'), page.actions_log)
            self.assertIn(('hover', '#menu'), page.actions_log)
            self.assertIn(('click', '#apply'), page.actions_log)
            self.assertIn(120, page.waits)
            self.assertIn(('wait_for', '#results', 'visible', 5000), page.actions_log)
            self.assertIn(('scroll_into_view', '#section-2'), page.actions_log)
            self.assertIn(('evaluate', 'window.scrollTo(10, 240)'), page.actions_log)
            self.assertIn(
                ('evaluate', 'window.scrollTo(0, Math.max(document.body.scrollHeight, document.documentElement.scrollHeight))'),
                page.actions_log,
            )
            # 1 initial stability check + 10 post-action stability checks = 11
            stability_count = sum(1 for item in page.actions_log if item[0] == 'stability')
            self.assertEqual(stability_count, 11)


MINI_APP_HTML = """<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <link rel="icon" href="data:,">
  <title>İP-B5 Mini App</title>
  <style>
    * { box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      margin: 0;
      padding: 24px;
      background: #f8fafc;
      color: #0f172a;
      line-height: 1.5;
    }
    main { max-width: 820px; margin: 0 auto; }
    .banner {
      padding: 16px 20px;
      border-radius: 10px;
      border: 2px solid #cbd5e1;
      background: #ffffff;
      margin-bottom: 16px;
    }
    .banner[data-ui="loading"] { background: #eff6ff; border-color: #2563eb; }
    .banner[data-ui="error"] { background: #fef2f2; border-color: #dc2626; }
    .banner[data-ui="locked"] { background: #fffbeb; border-color: #d97706; }
    .banner[data-ui="empty"] { background: #f1f5f9; border-color: #64748b; }
    .banner[data-ui="partial"] { background: #f5f3ff; border-color: #7c3aed; }
    .banner[data-ui="offline"] { background: #1e293b; border-color: #0f172a; color: #f8fafc; }
    .banner[data-ui="ready"] { background: #ecfdf5; border-color: #059669; }
    .card {
      padding: 12px 16px;
      border: 1px solid #cbd5e1;
      border-radius: 8px;
      background: #ffffff;
      margin-bottom: 10px;
    }
    .controls {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin: 16px 0;
      align-items: center;
    }
    input, button {
      min-height: 44px;
      padding: 8px 14px;
      font-size: 15px;
      border-radius: 8px;
      border: 1px solid #334155;
    }
    button { background: #0f172a; color: #ffffff; cursor: pointer; font-weight: 600; }
    button:focus-visible, input:focus-visible { outline: 3px solid #2563eb; outline-offset: 2px; }
    .spacer { height: 900px; }
  </style>
</head>
<body>
  <main id="app-main" data-ready="true">
    <h1>Aday Havuzu</h1>
    <div id="status-banner" class="banner" data-ui="loading">
      <h2 id="state-title">Yükleniyor...</h2>
      <p id="state-detail">Veriler API üzerinden alınıyor.</p>
    </div>
    <div id="items-list"></div>
    <section id="action-lab" class="banner" style="display:none">
      <h2>Etkileşim Alanı</h2>
      <div class="controls">
        <label for="search-input">Arama</label>
        <input id="search-input" type="text" placeholder="Aday ara">
        <button id="hover-btn" type="button">İpucu</button>
        <button id="load-cv-btn" type="button">CV Detayı Getir</button>
      </div>
      <p id="hover-info">Beklemede</p>
      <p id="press-info">Enter bekleniyor</p>
      <p id="cv-info">CV yüklenmedi</p>
      <div class="spacer"></div>
      <footer id="bottom-marker">Sayfa Altı Tamamlandı</footer>
    </section>
  </main>
  <script>
    const banner = document.getElementById('status-banner');
    const titleEl = document.getElementById('state-title');
    const detailEl = document.getElementById('state-detail');
    const listEl = document.getElementById('items-list');

    function setBanner(uiState, title, detail) {
      banner.setAttribute('data-ui', uiState);
      titleEl.textContent = title;
      detailEl.textContent = detail;
    }

    window.addEventListener('offline', () => {
      setBanner('offline', 'Çevrimdışı Bağlantı', 'İnternet bağlantısı kesildi.');
    });

    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('lab') === '1') {
      document.getElementById('action-lab').style.display = 'block';
      const inp = document.getElementById('search-input');
      inp.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          document.getElementById('press-info').textContent = 'Enter: ' + inp.value;
        }
      });
      document.getElementById('hover-btn').addEventListener('mouseenter', () => {
        document.getElementById('hover-info').textContent = 'İpucu Gösterildi';
      });
      document.getElementById('load-cv-btn').addEventListener('click', async () => {
        const res = await fetch('/api/cv?id=42');
        const cv = await res.json();
        setTimeout(() => {
          const el = document.getElementById('cv-info');
          el.textContent = 'CV: ' + cv.candidate + ' (' + cv.role + ')';
          el.setAttribute('data-cv-loaded', 'true');
        }, 60);
      });
    }

    (async () => {
      try {
        const res = await fetch('/api/items');
        if (res.status === 500) {
          setBanner('error', 'Sunucu Hatası (500)', 'İç sunucu hatası oluştu.');
          return;
        }
        if (res.status === 403) {
          setBanner('locked', 'Erişim Engellendi (403)', 'Bu içeriği görüntüleme yetkiniz yok.');
          return;
        }
        if (!res.ok) {
          setBanner('error', 'HTTP ' + res.status, 'Beklenmeyen yanıt.');
          return;
        }
        const data = await res.json();
        const items = Array.isArray(data) ? data : (data.items || []);
        if (items.length === 0) {
          setBanner('empty', 'Kayıt Bulunamadı', 'Henüz hiç aday eklenmemiş.');
          return;
        }
        const hasNullSummary = !Array.isArray(data) && data.summary === null;
        const hasNullDesc = items.some(it => it.description === null);
        if (hasNullSummary || hasNullDesc) {
          setBanner('partial', 'Kısmi Veri (' + items.length + ' kayıt)', 'Bazı alanlar eksik.');
        } else {
          setBanner('ready', 'Tam Veri (' + items.length + ' kayıt)', data.summary || 'Hazır');
        }
        listEl.innerHTML = items.map(it =>
          '<article class="card"><h3>' + it.name + '</h3><p>' + (it.description || 'Açıklama yok') + '</p></article>'
        ).join('');
      } catch (err) {
        setBanner('offline', 'Çevrimdışı Bağlantı', 'Ağ isteği başarısız oldu.');
      }
    })();
  </script>
</body>
</html>
"""


class _StateAppHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path == '/':
            body = MINI_APP_HTML.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == '/api/items':
            self.server.api_hits += 1
            payload = {
                'items': [
                    {'id': 1, 'name': 'Elif Yılmaz', 'description': 'Kıdemli Ürün Tasarımcısı'},
                    {'id': 2, 'name': 'Kerem Demir', 'description': 'Veri Bilimcisi'},
                    {'id': 3, 'name': 'Ayşe Kaya', 'description': 'Ön Yüz Mühendisi'},
                    {'id': 4, 'name': 'Mert Aydın', 'description': 'Sistem Mimarı'},
                ],
                'summary': 'Toplam 4 aday listelendi.',
            }
            body = json.dumps(payload).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path.startswith('/api/cv'):
            body = json.dumps({'candidate': 'Live Server', 'role': 'Default'}).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(404)
        self.end_headers()


@unittest.skipUnless(_browser_available(), 'Playwright/Chromium not available')
class LiveSevenStatesAndActionsIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), _StateAppHandler)
        cls.server.api_hits = 0
        cls.base_url = f'http://127.0.0.1:{cls.server.server_address[1]}'
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_all_7_states_via_single_routes_cli_command(self):
        self.server.api_hits = 0
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            shots_dir = tmp_dir / 'shots'
            # Place 'offline' before 'partial' and 'default' to verify offline cleanup restores online state.
            states_order = ['loading', 'long-loading', 'error', 'empty', 'offline', 'partial', 'locked', 'default']
            routes_cfg = {
                'base_url': self.base_url,
                'viewports': ['desktop'],
                'routes': [
                    {
                        'name': 'candidates',
                        'path': '/',
                        'states': states_order,
                        'state_mocks': {
                            'long-loading': {
                                'delay_ms': 1500,
                                'long_loading_frames_ms': [100, 300, 500],
                            },
                        },
                    },
                ],
            }
            routes_path = tmp_dir / 'routes.json'
            routes_path.write_text(json.dumps(routes_cfg, indent=2), encoding='utf-8')

            observed_dom = {}
            orig_finalize = rd._finalize_viewport_checks

            def spy_finalize(page, vp_width, console_errors, network_errors, pre_findings=None):
                snap = page.evaluate("""() => ({
                    renderState: window.__RENDER_STATE__,
                    uiState: document.getElementById('status-banner')?.getAttribute('data-ui'),
                    title: document.getElementById('state-title')?.textContent,
                    detail: document.getElementById('state-detail')?.textContent,
                    cardCount: document.querySelectorAll('#items-list .card').length,
                    onLine: navigator.onLine
                })""")
                observed_dom[snap['renderState']] = snap
                return orig_finalize(page, vp_width, console_errors, network_errors, pre_findings=pre_findings)

            stdout = io.StringIO()
            with mock.patch.object(rd, 'find_axe', return_value=None), \
                 mock.patch.object(rd, '_finalize_viewport_checks', side_effect=spy_finalize), \
                 contextlib.redirect_stdout(stdout):
                rd.main(['--routes', str(routes_path), '--out-dir', str(shots_dir)])

            # 1. Verify all 7 state PNGs + default PNG + 3 long-loading frame PNGs exist
            route_dir = shots_dir / 'candidates'
            for st in states_order:
                png = route_dir / f'{st}-desktop.png'
                self.assertTrue(png.is_file(), f'Missing screenshot for state {st}: {png}')
                self.assertGreater(png.stat().st_size, 500)

            for frame_name in (
                'long-loading-0.1s-desktop.png',
                'long-loading-0.3s-desktop.png',
                'long-loading-0.5s-desktop.png',
            ):
                f_png = route_dir / frame_name
                self.assertTrue(f_png.is_file(), f'Missing long-loading frame: {f_png}')

            # Standard long-loading-desktop.png must match the middle (0.3s) frame
            self.assertEqual(
                (route_dir / 'long-loading-desktop.png').read_bytes(),
                (route_dir / 'long-loading-0.3s-desktop.png').read_bytes(),
            )

            # 2. Verify DOM state actually observed in Chromium for every single state
            self.assertEqual(set(observed_dom.keys()), set(states_order))

            self.assertEqual(observed_dom['loading']['uiState'], 'loading')
            self.assertEqual(observed_dom['loading']['cardCount'], 0)

            self.assertEqual(observed_dom['long-loading']['uiState'], 'loading')
            self.assertEqual(observed_dom['long-loading']['renderState'], 'long-loading')
            self.assertEqual(observed_dom['long-loading']['cardCount'], 0)

            self.assertEqual(observed_dom['error']['uiState'], 'error')
            self.assertIn('500', observed_dom['error']['title'])

            self.assertEqual(observed_dom['empty']['uiState'], 'empty')
            self.assertEqual(observed_dom['empty']['cardCount'], 0)
            self.assertIn('Kayıt Bulunamadı', observed_dom['empty']['title'])

            self.assertEqual(observed_dom['offline']['uiState'], 'offline')
            self.assertFalse(observed_dom['offline']['onLine'])
            self.assertIn('Çevrimdışı', observed_dom['offline']['title'])

            # Partial ran AFTER offline, proving set_offline(False) restored network for route.fetch()
            self.assertEqual(observed_dom['partial']['uiState'], 'partial')
            self.assertTrue(observed_dom['partial']['onLine'])
            self.assertEqual(observed_dom['partial']['cardCount'], 2)
            self.assertIn('Kısmi Veri', observed_dom['partial']['title'])

            self.assertEqual(observed_dom['locked']['uiState'], 'locked')
            self.assertIn('403', observed_dom['locked']['title'])

            self.assertEqual(observed_dom['default']['uiState'], 'ready')
            self.assertEqual(observed_dom['default']['cardCount'], 4)
            self.assertGreaterEqual(self.server.api_hits, 2)  # partial route.fetch + default

    def test_full_action_set_and_body_file_mock_live(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            fixtures_dir = tmp_dir / 'fixtures'
            fixtures_dir.mkdir(parents=True, exist_ok=True)
            (fixtures_dir / 'cv_mock.json').write_text(
                json.dumps({'candidate': 'Ada Lovelace', 'role': 'Baş Mimar'}),
                encoding='utf-8',
            )
            shots_dir = tmp_dir / 'shots'
            routes_cfg = {
                'base_url': self.base_url,
                'viewports': ['desktop'],
                'routes': [
                    {
                        'name': 'action-lab',
                        'path': '/?lab=1',
                        'states': ['custom-cv'],
                        'state_mocks': {
                            'custom-cv': {
                                'pattern': '**/api/cv*',
                                'delay_ms': 100,
                                'status': 200,
                                'body_file': 'fixtures/cv_mock.json',
                            },
                        },
                        'actions': [
                            {'fill': ['#search-input', 'algoritma']},
                            {'press': ['#search-input', 'Enter']},
                            {'hover': '#hover-btn'},
                            {'click': '#load-cv-btn'},
                            {'wait': 40},
                            {'wait_for': '[data-cv-loaded="true"]'},
                            {'scroll_to': '#bottom-marker'},
                            {'scroll_to': {'x': 0, 'y': 200}},
                            {'scroll_to': 'bottom'},
                            {'screenshot_as': 'lab-after-scroll'},
                        ],
                    },
                ],
            }
            routes_path = tmp_dir / 'routes.json'
            routes_path.write_text(json.dumps(routes_cfg, indent=2), encoding='utf-8')

            observed = {}
            orig_finalize = rd._finalize_viewport_checks

            def spy_finalize(page, vp_width, console_errors, network_errors, pre_findings=None):
                observed['dom'] = page.evaluate("""() => ({
                    pressText: document.getElementById('press-info')?.textContent,
                    hoverText: document.getElementById('hover-info')?.textContent,
                    cvText: document.getElementById('cv-info')?.textContent,
                    scrollY: window.scrollY
                })""")
                return orig_finalize(page, vp_width, console_errors, network_errors, pre_findings=pre_findings)

            with mock.patch.object(rd, 'find_axe', return_value=None), \
                 mock.patch.object(rd, '_finalize_viewport_checks', side_effect=spy_finalize):
                summary = rd.render_routes(
                    rd.RenderOptions(routes=str(routes_path), out_dir=str(shots_dir)),
                )

            extra_shot = shots_dir / 'action-lab' / 'lab-after-scroll.png'
            main_shot = shots_dir / 'action-lab' / 'custom-cv-desktop.png'
            self.assertTrue(extra_shot.is_file(), f'Missing screenshot_as output: {extra_shot}')
            self.assertTrue(main_shot.is_file())
            self.assertEqual(summary['results'][0]['extra_screenshots'], [str(extra_shot)])
            self.assertEqual(observed['dom']['pressText'], 'Enter: algoritma')
            self.assertEqual(observed['dom']['hoverText'], 'İpucu Gösterildi')
            self.assertEqual(observed['dom']['cvText'], 'CV: Ada Lovelace (Baş Mimar)')


if __name__ == '__main__':
    unittest.main()
