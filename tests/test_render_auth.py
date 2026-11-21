"""Tests for render.py session support: --storage-state, --login-script, --save-storage-state."""
import contextlib
import http.server
import importlib.util
import io
import json
import pathlib
import tempfile
import threading
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('render', ROOT / 'scripts' / 'render.py')
rd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rd)

LOGIN_HTML = b'<html><body><h1 id="kind">LOGIN</h1></body></html>'
DASH_HTML = b'<html><body><h1 id="kind">DASHBOARD</h1><div style="height:1800px">secret area</div></body></html>'
COOKIE_VALUE = 'topsecretvalue123'
LOGIN_SCRIPT = f'''
def login(page, base_url):
    page.goto(base_url + "/login")
    page.evaluate("document.cookie = 'session={COOKIE_VALUE}; path=/'")
'''


class _Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith('/protected'):
            ok = f'session={COOKIE_VALUE}' in (self.headers.get('Cookie') or '')
            self.server.served.append('dashboard' if ok else 'login')
            body = DASH_HTML if ok else LOGIN_HTML
        else:
            body = LOGIN_HTML
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _browser_available():
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            rd.launch_browser(p).close()
        return True
    except BaseException:
        return False


class AuthUnitTests(unittest.TestCase):
    def test_missing_storage_state_exits_cleanly(self):
        with tempfile.TemporaryDirectory() as d:
            opts = rd.RenderOptions(url='http://127.0.0.1:1/', out='x.png',
                                    storage_state=str(pathlib.Path(d) / 'nope.json'))
            with self.assertRaises(SystemExit) as cm:
                rd._check_auth_inputs(opts)
            self.assertIn('--storage-state file not found', str(cm.exception))

    def test_login_script_without_login_function_exits_cleanly(self):
        with tempfile.TemporaryDirectory() as d:
            script = pathlib.Path(d) / 'bad.py'
            script.write_text('x = 1\n', encoding='utf-8')
            with self.assertRaises(SystemExit) as cm:
                rd._load_login(script)
            self.assertIn('def login(page, base_url)', str(cm.exception))

    def test_missing_login_script_exits_cleanly(self):
        with self.assertRaises(SystemExit) as cm:
            rd._load_login('/no/such/login.py')
        self.assertIn('not found', str(cm.exception))

    def test_capture_closes_context_and_passes_options(self):
        with tempfile.TemporaryDirectory() as d:
            state = pathlib.Path(d) / 'auth.json'
            state.write_text('{"cookies":[],"origins":[]}', encoding='utf-8')
            script = pathlib.Path(d) / 'login.py'
            script.write_text('calls = []\ndef login(page, base_url):\n    calls.append(base_url)\n', encoding='utf-8')
            save = pathlib.Path(d) / 'sub' / 'saved.json'
            browser = mock.MagicMock()
            context = browser.new_context.return_value
            context.storage_state.side_effect = lambda path: pathlib.Path(path).write_text('{}')
            page = context.new_page.return_value
            page.evaluate.return_value = 100
            opts = rd.RenderOptions(url='http://localhost:3000/dash', out=None, storage_state=str(state),
                                    login_script=str(script), save_storage_state=str(save))
            out_err = io.StringIO()
            with contextlib.redirect_stderr(out_err):
                res = rd.capture(browser, opts.url, opts)
            self.assertEqual(res['scroll_height'], 100)
            self.assertEqual(browser.new_context.call_args.kwargs['storage_state'], str(state))
            context.close.assert_called_once()
            self.assertTrue(save.exists())
            self.assertIn('storage state saved to', out_err.getvalue())

    def test_parse_options_new_flags_and_help(self):
        o = rd.parse_options(['--url', 'http://localhost:3000/', '--out', 'o.png',
                              '--storage-state', 'a.json', '--save-storage-state', 'b.json',
                              '--login-script', 'l.py'])
        self.assertEqual((o.storage_state, o.save_storage_state, o.login_script), ('a.json', 'b.json', 'l.py'))
        text = rd.build_parser().format_help()
        self.assertIn('codegen --save-storage=auth.json', text)
        self.assertIn('PRIVACY', text)


@unittest.skipUnless(_browser_available(), 'Playwright/Chromium not available')
class AuthIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), _Handler)
        cls.server.served = []
        cls.base = f'http://127.0.0.1:{cls.server.server_address[1]}'
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _run(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rd.main(argv)
        return out.getvalue() + err.getvalue()

    def test_login_script_save_then_reuse_storage_state(self):
        with tempfile.TemporaryDirectory() as d:
            d = pathlib.Path(d)
            script = d / 'login.py'
            script.write_text(LOGIN_SCRIPT, encoding='utf-8')
            auth = d / 'nested' / 'auth.json'
            url = self.base + '/protected'

            # Without a session the login page is served (sanity check).
            self.server.served.clear()
            log_anon = self._run(['--url', url, '--out', str(d / 'anon.png')])
            self.assertEqual(self.server.served, ['login'])
            self.assertIn('(1440x900)', log_anon)

            self.server.served.clear()
            log1 = self._run(['--url', url, '--out', str(d / 'p1.png'),
                              '--login-script', str(script), '--save-storage-state', str(auth)])
            self.assertEqual(self.server.served, ['dashboard'])
            self.assertTrue(auth.exists())
            self.assertIn(COOKIE_VALUE, auth.read_text(encoding='utf-8'))
            self.assertTrue((d / 'p1.png').stat().st_size > 0)
            self.assertNotIn(COOKIE_VALUE, log1)
            self.assertIn('x18', log1)

            # Reuse the saved state without any login script.
            self.server.served.clear()
            log2 = self._run(['--url', url, '--out', str(d / 'p2.png'), '--storage-state', str(auth)])
            self.assertEqual(self.server.served, ['dashboard'])
            self.assertNotIn(COOKIE_VALUE, log2)
            self.assertIn('x18', log2)
            json.loads(auth.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
