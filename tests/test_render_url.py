"""Tests for scripts/render.py core refactor and --url mode."""
import contextlib
import http.server
import importlib.util
import io
import os
import pathlib
import socket
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('render', ROOT / 'scripts' / 'render.py')
rd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rd)


def _unused_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class _FakePage:
    """Minimal Playwright Page double for unit-testing capture()."""

    def __init__(self, check_result=None, scroll_height=900):
        self.listeners = {}
        self.visited = []
        self.screenshots = []
        self.closed = False
        self._check_result = check_result if check_result is not None else []
        self._scroll_height = scroll_height

    def on(self, event, fn):
        self.listeners.setdefault(event, []).append(fn)

    def remove_listener(self, event, fn):
        if event in self.listeners and fn in self.listeners[event]:
            self.listeners[event].remove(fn)

    def emit(self, event, payload):
        for fn in list(self.listeners.get(event, [])):
            fn(payload)

    def goto(self, uri):
        self.visited.append(uri)

    def wait_for_timeout(self, ms):
        pass

    def screenshot(self, path, full_page=True):
        pathlib.Path(path).write_bytes(b'\x89PNG\r\n\x1a\nfake')
        self.screenshots.append((path, full_page))

    def evaluate(self, expr):
        if expr == 'document.documentElement.scrollHeight':
            return self._scroll_height
        if expr == rd.CHECK_JS:
            return list(self._check_result)
        if expr in (rd.INTERACT_JS, rd.MOBILE_JS):
            return []
        return None

    def close(self):
        self.closed = True


class _FakeBrowser:
    def __init__(self, pages):
        self._pages = list(pages)
        self.created_viewports = []

    def new_page(self, viewport=None):
        self.created_viewports.append(viewport)
        return self._pages.pop(0)


class TestCliValidation(unittest.TestCase):
    def test_requires_either_html_or_url(self):
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            with self.assertRaises(SystemExit) as ctx:
                rd.parse_options(['--out', 'out.png'])
        self.assertEqual(ctx.exception.code, 2)
        self.assertIn('either an HTML file or --url', buf.getvalue())

    def test_rejects_both_html_and_url(self):
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            with self.assertRaises(SystemExit) as ctx:
                rd.parse_options(['page.html', '--url', 'http://localhost:3000', '--out', 'out.png'])
        self.assertEqual(ctx.exception.code, 2)
        self.assertIn('cannot specify both', buf.getvalue())

    def test_rejects_invalid_url_scheme(self):
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            with self.assertRaises(SystemExit) as ctx:
                rd.parse_options(['--url', 'localhost:3000/dashboard', '--out', 'out.png'])
        self.assertEqual(ctx.exception.code, 2)
        self.assertIn('invalid --url', buf.getvalue())

    def test_requires_out_flag(self):
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            with self.assertRaises(SystemExit) as ctx:
                rd.parse_options(['page.html'])
        self.assertEqual(ctx.exception.code, 2)
        self.assertIn('--out', buf.getvalue())

    def test_legacy_html_args_unchanged(self):
        opts = rd.parse_options([
            'page.html', '--out', 'page.png', '--dark', '--width', '1280', '--height', '720', '--check'
        ])
        self.assertEqual(opts.html, 'page.html')
        self.assertIsNone(opts.url)
        self.assertEqual(opts.out, 'page.png')
        self.assertTrue(opts.dark)
        self.assertEqual(opts.width, 1280)
        self.assertEqual(opts.height, 720)
        self.assertTrue(opts.check)
        self.assertFalse(opts.online)

    def test_url_args_parse_into_render_options(self):
        opts = rd.parse_options(['--url', 'http://localhost:3000/dashboard', '--out', 'dash.png', '--check'])
        self.assertIsNone(opts.html)
        self.assertEqual(opts.url, 'http://localhost:3000/dashboard')
        self.assertEqual(opts.out, 'dash.png')
        self.assertTrue(opts.check)
        self.assertTrue(opts.online)


class TestUrlModeRules(unittest.TestCase):
    def test_is_ignored_console_error_online_vs_offline(self):
        for err in (
            'Failed to load resource: net::ERR_CONNECTION_REFUSED',
            'Failed to load resource: net::ERR_NAME_NOT_RESOLVED',
            'Failed to load resource: net::ERR_INTERNET_DISCONNECTED',
            'Failed to load resource: net::ERR_BLOCKED_BY_CLIENT',
        ):
            self.assertTrue(rd.is_ignored_console_error(err))
            self.assertTrue(rd.is_ignored_console_error(err, online=False))
            self.assertFalse(rd.is_ignored_console_error(err, online=True))

    def test_url_mode_never_calls_tailwind_or_inline_fonts(self):
        fake_playwright = mock.MagicMock()
        fake_cm = mock.MagicMock()
        fake_cm.__enter__.return_value = fake_playwright
        fake_cm.__exit__.return_value = False
        fake_browser = mock.MagicMock()
        fake_playwright.chromium.launch.return_value = fake_browser

        expected = {
            'out': 'dash.png',
            'width': 1440,
            'scroll_height': 900,
            'findings': [],
            'console_errors': [],
            'network_errors': [],
        }
        with mock.patch.dict('sys.modules', {'playwright.sync_api': SimpleNamespace(sync_playwright=lambda: fake_cm)}), \
             mock.patch.object(rd, 'compile_tailwind') as m_tw, \
             mock.patch.object(rd, 'inline_fonts') as m_gf, \
             mock.patch.object(rd, 'reachable') as m_reach, \
             mock.patch.object(rd, 'write_temp_render') as m_tmp, \
             mock.patch.object(rd, 'capture', return_value=expected) as m_cap:
            res = rd.render(rd.RenderOptions(url='http://127.0.0.1:3000/', out='dash.png'))

        self.assertEqual(res, expected)
        m_tw.assert_not_called()
        m_gf.assert_not_called()
        m_reach.assert_not_called()
        m_tmp.assert_not_called()
        m_cap.assert_called_once()
        self.assertEqual(m_cap.call_args.args[1], 'http://127.0.0.1:3000/')

    def test_html_mode_still_rewrites_when_offline(self):
        fake_playwright = mock.MagicMock()
        fake_cm = mock.MagicMock()
        fake_cm.__enter__.return_value = fake_playwright
        fake_cm.__exit__.return_value = False

        with tempfile.TemporaryDirectory() as d:
            html_file = pathlib.Path(d) / 'page.html'
            html_file.write_text(
                '<html><head>'
                '<script src="https://cdn.tailwindcss.com"></script>'
                '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter">'
                '</head><body>Hi</body></html>',
                encoding='utf-8',
            )
            out_png = pathlib.Path(d) / 'out.png'

            with mock.patch.dict('sys.modules', {'playwright.sync_api': SimpleNamespace(sync_playwright=lambda: fake_cm)}), \
                 mock.patch.object(rd, 'reachable', return_value=False), \
                 mock.patch.object(rd, 'compile_tailwind', side_effect=lambda h: h) as m_tw, \
                 mock.patch.object(rd, 'inline_fonts', side_effect=lambda h: h) as m_gf, \
                 mock.patch.object(rd, 'capture', return_value={'out': str(out_png), 'width': 1440, 'scroll_height': 900, 'findings': [], 'console_errors': [], 'network_errors': []}):
                rd.render(rd.RenderOptions(html=str(html_file), out=str(out_png)))

            m_tw.assert_called_once()
            m_gf.assert_called_once()
            self.assertFalse((pathlib.Path(d) / f'.page.{os.getpid()}.render.html').exists())

    def test_capture_records_network_and_console_errors_only_in_online_mode(self):
        with tempfile.TemporaryDirectory() as d:
            out_png = pathlib.Path(d) / 'shot.png'

            # Online mode: ERR_CONNECTION_REFUSED console error + requestfailed + 404 response
            desktop_online = _FakePage(scroll_height=1200)
            mobile_online = _FakePage()
            orig_goto = desktop_online.goto

            def online_goto(uri):
                orig_goto(uri)
                desktop_online.emit('console', SimpleNamespace(
                    type='error',
                    text='Failed to load resource: net::ERR_CONNECTION_REFUSED',
                ))
                desktop_online.emit('response', SimpleNamespace(status=404, url='http://127.0.0.1:8000/api/data'))
                desktop_online.emit('requestfailed', SimpleNamespace(
                    url='http://127.0.0.1:9999/asset.js',
                    failure='net::ERR_CONNECTION_REFUSED',
                ))

            desktop_online.goto = online_goto
            browser_online = _FakeBrowser([desktop_online, mobile_online])

            with mock.patch.object(rd, 'run_axe', return_value=[]):
                res_online = rd.capture(
                    browser_online,
                    'http://127.0.0.1:8000/app',
                    rd.RenderOptions(url='http://127.0.0.1:8000/app', out=str(out_png), check=True),
                )

            self.assertEqual(res_online['out'], str(out_png))
            self.assertEqual(res_online['width'], 1440)
            self.assertEqual(res_online['scroll_height'], 1200)
            self.assertEqual(len(res_online['console_errors']), 1)
            self.assertIn('ERR_CONNECTION_REFUSED', res_online['console_errors'][0])
            self.assertEqual(len(res_online['network_errors']), 2)
            rules = {f[1] for f in res_online['findings']}
            self.assertIn('js-errors', rules)
            self.assertIn('network-errors', rules)
            self.assertTrue(desktop_online.closed)
            self.assertTrue(mobile_online.closed)

            # Offline mode: ERR_CONNECTION_REFUSED console error remains suppressed
            desktop_offline = _FakePage(scroll_height=900)
            mobile_offline = _FakePage()
            orig_offline_goto = desktop_offline.goto

            def offline_goto(uri):
                orig_offline_goto(uri)
                desktop_offline.emit('console', SimpleNamespace(
                    type='error',
                    text='Failed to load resource: net::ERR_CONNECTION_REFUSED',
                ))

            desktop_offline.goto = offline_goto
            browser_offline = _FakeBrowser([desktop_offline, mobile_offline])

            with mock.patch.object(rd, 'run_axe', return_value=[]):
                res_offline = rd.capture(
                    browser_offline,
                    'file:///tmp/page.html',
                    rd.RenderOptions(html='page.html', out=str(out_png), check=True),
                )

            self.assertEqual(res_offline['console_errors'], [])
            self.assertEqual(res_offline['network_errors'], [])
            self.assertEqual(res_offline['findings'], [['INFO', 'dom-check', 'no defects found']])


class TestLiveHttpServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise unittest.SkipTest(f'Playwright unavailable: {exc}')
        cls._sync_playwright = staticmethod(sync_playwright)

    def _start_server(self, routes):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path in routes:
                    status, content_type, body = routes[self.path]
                    self.send_response(status)
                    self.send_header('Content-Type', content_type)
                    self.end_headers()
                    self.wfile.write(body)
                else:
                    self.send_response(404)
                    self.send_header('Content-Type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(b'Not Found')

            def log_message(self, *args):
                pass

        srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=srv.serve_forever, daemon=True)
        thread.start()
        return srv

    def test_live_http_server_main_url_check_creates_png_and_skips_rewrites(self):
        clean_html = (
            '<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<link rel="icon" href="data:,">'
            '<title>Dashboard</title>'
            '<style>body{font-family:sans-serif;margin:0;padding:24px;background:#fff;color:#111}'
            '.card{max-width:480px;padding:16px;border:1px solid #ddd;border-radius:8px}</style>'
            '</head><body><main><div class="card"><h1>Live App</h1>'
            '<p>Rendered from local HTTP server.</p></div></main></body></html>'
        ).encode('utf-8')

        srv = self._start_server({'/dashboard': (200, 'text/html; charset=utf-8', clean_html)})
        try:
            port = srv.server_address[1]
            url = f'http://127.0.0.1:{port}/dashboard'
            with tempfile.TemporaryDirectory() as d:
                png = pathlib.Path(d) / 'live.png'
                stdout = io.StringIO()
                with mock.patch.object(rd, 'compile_tailwind') as m_tw, \
                     mock.patch.object(rd, 'inline_fonts') as m_gf, \
                     mock.patch.object(rd, 'find_axe', return_value=None), \
                     contextlib.redirect_stdout(stdout):
                    rd.main(['--url', url, '--out', str(png), '--check'])

                m_tw.assert_not_called()
                m_gf.assert_not_called()
                self.assertTrue(png.is_file(), 'PNG screenshot was not created')
                data = png.read_bytes()
                self.assertTrue(data.startswith(b'\x89PNG\r\n\x1a\n'))
                self.assertGreater(len(data), 500)
                out_text = stdout.getvalue()
                self.assertIn(str(png), out_text)
                self.assertIn('1440x', out_text)
                self.assertNotIn('[WARN]', out_text)
                self.assertNotIn('[FAIL]', out_text)
        finally:
            srv.shutdown()
            srv.server_close()

    def test_live_http_server_capture_surfaces_404_and_connection_refused(self):
        dead_port = _unused_port()
        broken_html = (
            '<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<title>Broken Live App</title></head><body>'
            '<h1>Broken App</h1>'
            '<script src="/missing.js"></script>'
            f'<script>fetch("http://127.0.0.1:{dead_port}/api/fail").catch(() => {{}});</script>'
            '</body></html>'
        ).encode('utf-8')

        srv = self._start_server({'/broken': (200, 'text/html; charset=utf-8', broken_html)})
        try:
            port = srv.server_address[1]
            url = f'http://127.0.0.1:{port}/broken'
            with tempfile.TemporaryDirectory() as d:
                png = pathlib.Path(d) / 'broken.png'
                with mock.patch.object(rd, 'find_axe', return_value=None):
                    with self._sync_playwright() as p:
                        browser = rd.launch_browser(p)
                        try:
                            res = rd.capture(
                                browser,
                                url,
                                rd.RenderOptions(url=url, out=str(png), check=True),
                            )
                        finally:
                            browser.close()

                self.assertTrue(png.is_file())
                self.assertEqual(res['out'], str(png))
                self.assertEqual(res['width'], 1440)
                self.assertGreater(res['scroll_height'], 0)
                self.assertTrue(res['console_errors'], 'Expected console errors from 404 / connection refused')
                self.assertTrue(res['network_errors'], 'Expected network errors from 404 / connection refused')
                self.assertTrue(
                    any('ERR_CONNECTION_REFUSED' in err or '404' in err for err in res['console_errors']),
                    f"Unexpected console_errors: {res['console_errors']}",
                )
                rules = {f[1] for f in res['findings']}
                self.assertIn('js-errors', rules)
                self.assertIn('network-errors', rules)
        finally:
            srv.shutdown()
            srv.server_close()


if __name__ == '__main__':
    unittest.main()
