"""Live Playwright Chromium tests for the new DOM checks in scripts/checks/check.js."""
import importlib.util
import pathlib
import shutil
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHECK_JS_PATH = ROOT / 'scripts' / 'checks' / 'check.js'

spec = importlib.util.spec_from_file_location('render', ROOT / 'scripts' / 'render.py')
rd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rd)


def _check_js():
    return CHECK_JS_PATH.read_text(encoding='utf-8').strip()


class CheckJsSyntaxTests(unittest.TestCase):
    def test_node_syntax_check(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not on PATH')
        js = _check_js()
        with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as tf:
            tf.write(f'const _fn = ({js});\n')
            path = pathlib.Path(tf.name)
        try:
            res = subprocess.run(
                [node, '--check', str(path)],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
            )
            self.assertEqual(res.returncode, 0, f'check.js syntax error: {res.stderr}')
        finally:
            path.unlink(missing_ok=True)


class RenderDomChecksPlaywrightTests(unittest.TestCase):
    _pw = None
    _browser = None

    @classmethod
    def setUpClass(cls):
        try:
            from playwright.sync_api import sync_playwright
            cls._pw = sync_playwright().start()
            cls._browser = rd.launch_browser(cls._pw)
        except BaseException as exc:
            if cls._pw is not None:
                cls._pw.stop()
                cls._pw = None
            raise unittest.SkipTest(f'Playwright/Chromium unavailable: {exc}')

    @classmethod
    def tearDownClass(cls):
        if cls._browser is not None:
            cls._browser.close()
        if cls._pw is not None:
            cls._pw.stop()

    def _run_check(self, html, url=None):
        page = self._browser.new_page(viewport={'width': 1280, 'height': 800})
        try:
            if url:
                page.route(url, lambda route: route.fulfill(status=200, content_type='text/html; charset=utf-8', body=html))
                page.goto(url)
            else:
                page.set_content(html)
            return page.evaluate(_check_js())
        finally:
            page.close()

    def _codes(self, results):
        return [(lvl, code) for lvl, code, _ in results]

    # 1. tr-uppercase-render
    def test_tr_uppercase_render_positive_missing_lang_tr(self):
        html = """<!doctype html>
        <html lang="en">
        <body>
          <h1 style="text-transform: uppercase">Giriş ve İşlemler</h1>
        </body>
        </html>"""
        res = self._run_check(html)
        self.assertIn(('WARN', 'tr-uppercase-render'), self._codes(res))

    def test_tr_uppercase_render_negative_with_lang_tr_and_english_text(self):
        html_tr = """<!doctype html>
        <html lang="tr">
        <body>
          <h1 style="text-transform: uppercase">Giriş ve İşlemler</h1>
        </body>
        </html>"""
        res_tr = self._run_check(html_tr)
        self.assertNotIn(('WARN', 'tr-uppercase-render'), self._codes(res_tr))

        html_en = """<!doctype html>
        <html lang="en">
        <body>
          <h1 style="text-transform: uppercase">Pricing and Billing</h1>
        </body>
        </html>"""
        res_en = self._run_check(html_en)
        self.assertNotIn(('WARN', 'tr-uppercase-render'), self._codes(res_en))

    # 2. theme-toggle-missing
    def test_theme_toggle_missing_positive_dark_css_without_toggle(self):
        html = """<!doctype html>
        <html>
        <head>
          <style>
            body { background: #fff; color: #111; }
            .dark body { background: #111; color: #fff; }
          </style>
        </head>
        <body>
          <main><h1>Dashboard</h1><button>Save</button></main>
        </body>
        </html>"""
        res = self._run_check(html)
        self.assertIn(('WARN', 'theme-toggle-missing'), self._codes(res))

    def test_theme_toggle_missing_negative_with_toggle_or_no_dark_css(self):
        html_with_toggle = """<!doctype html>
        <html>
        <head>
          <style>[data-theme="dark"] body { background: #111; color: #fff; }</style>
        </head>
        <body>
          <button data-theme-toggle aria-label="Toggle dark mode">Theme</button>
        </body>
        </html>"""
        res_toggle = self._run_check(html_with_toggle)
        self.assertNotIn(('WARN', 'theme-toggle-missing'), self._codes(res_toggle))

        html_no_dark = """<!doctype html>
        <html>
        <head><style>body { background: #fff; color: #111; }</style></head>
        <body><main><h1>Light Only</h1></main></body>
        </html>"""
        res_no_dark = self._run_check(html_no_dark)
        self.assertNotIn(('WARN', 'theme-toggle-missing'), self._codes(res_no_dark))

    # 3. numeric-alignment
    def test_numeric_alignment_positive_missing_tabular_nums(self):
        html = """<!doctype html>
        <html>
        <body>
          <table>
            <thead><tr><th>Metric</th><th>Value</th></tr></thead>
            <tbody>
              <tr><td>Conversion</td><td>73%</td></tr>
              <tr><td>Revenue</td><td>1.284,50</td></tr>
            </tbody>
          </table>
        </body>
        </html>"""
        res = self._run_check(html)
        self.assertIn(('INFO', 'numeric-alignment'), self._codes(res))

    def test_numeric_alignment_negative_with_tabular_nums(self):
        html = """<!doctype html>
        <html>
        <head><style>td.num { font-variant-numeric: tabular-nums; }</style></head>
        <body>
          <table>
            <thead><tr><th>Metric</th><th>Value</th></tr></thead>
            <tbody>
              <tr><td>Conversion</td><td class="num">$42.00</td></tr>
              <tr><td>Revenue</td><td class="num">1.284,50</td></tr>
            </tbody>
          </table>
        </body>
        </html>"""
        res = self._run_check(html)
        self.assertNotIn(('INFO', 'numeric-alignment'), self._codes(res))

    # 4. long-wait-unexplained
    def test_long_wait_unexplained_positive_bare_spinner_in_long_loading(self):
        html = """<!doctype html>
        <html data-render-state="long-loading">
        <body>
          <div style="padding: 40px">
            <div class="spinner" style="width:24px;height:24px;border:2px solid #ccc"></div>
            <p>Hazırlanıyor...</p>
          </div>
        </body>
        </html>"""
        res = self._run_check(html)
        self.assertIn(('WARN', 'long-wait-unexplained'), self._codes(res))

    def test_long_wait_unexplained_negative_with_progress_or_normal_state(self):
        html_with_progress = """<!doctype html>
        <html>
        <body>
          <progress value="45" max="100"></progress>
          <p>Loading...</p>
          <button>İptal</button>
        </body>
        </html>"""
        res_progress = self._run_check(html_with_progress, url='http://localhost/app?state=long-loading')
        self.assertNotIn(('WARN', 'long-wait-unexplained'), self._codes(res_progress))

        html_normal = """<!doctype html>
        <html>
        <body><p>Hazırlanıyor...</p></body>
        </html>"""
        res_normal = self._run_check(html_normal)
        self.assertNotIn(('WARN', 'long-wait-unexplained'), self._codes(res_normal))


if __name__ == '__main__':
    unittest.main()
