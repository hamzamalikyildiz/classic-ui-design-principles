"""Regression tests for scripts/render.py. Run: python3 -m unittest discover -s tests"""
import importlib.util
import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('render', ROOT / 'scripts' / 'render.py')
rd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rd)


class RegexPatterns(unittest.TestCase):
    def test_cdn_matches_double_and_single_quotes(self):
        self.assertIsNotNone(rd.CDN.search('<script src="https://cdn.tailwindcss.com"></script>'))
        self.assertIsNotNone(rd.CDN.search("<script src='https://cdn.tailwindcss.com?plugins=forms'></script>"))
        self.assertIsNotNone(rd.CDN.search('<script defer src=\'https://cdn.tailwindcss.com/3.4.1\'></script>'))
        self.assertIsNone(rd.CDN.search('<script src="https://example.com/app.js"></script>'))

    def test_inline_cfg_matches_multiline_config(self):
        html = '<script>\n  tailwind.config = {\n    darkMode: "class",\n    theme: { extend: {} }\n  };\n</script>'
        m = rd.INLINE_CFG.search(html)
        self.assertIsNotNone(m)
        self.assertIn('darkMode', m.group(1))

    def test_gfonts_matches_googleapis_and_gstatic(self):
        self.assertIsNotNone(rd.GFONTS.search('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter">'))
        self.assertIsNotNone(rd.GFONTS.search("<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"))
        self.assertIsNone(rd.GFONTS.search('<link rel="stylesheet" href="styles.css">'))


class NetworkAndPaths(unittest.TestCase):
    def test_reachable_closes_response_and_handles_errors(self):
        cm = mock.MagicMock()
        cm.__enter__.return_value = cm
        cm.__exit__.return_value = False
        with mock.patch.object(rd.urllib.request, 'urlopen', return_value=cm) as urlopen:
            self.assertTrue(rd.reachable('https://example.com'))
        urlopen.assert_called_once_with('https://example.com', timeout=4)
        cm.__exit__.assert_called_once()

        with mock.patch.object(rd.urllib.request, 'urlopen', side_effect=OSError('offline')):
            self.assertFalse(rd.reachable('https://example.com'))

    def test_chrome_path_uses_which_then_platform_fallbacks(self):
        with mock.patch.object(rd.shutil, 'which', side_effect=lambda n: '/usr/bin/chromium' if n == 'chromium' else None):
            self.assertEqual(rd.chrome_path(), '/usr/bin/chromium')

        win_chrome = os.path.join(r'C:\Program Files', 'Google', 'Chrome', 'Application', 'chrome.exe')
        with mock.patch.object(rd.shutil, 'which', return_value=None), \
             mock.patch.dict(os.environ, {'PROGRAMFILES': r'C:\Program Files', 'PROGRAMFILES(X86)': '', 'LOCALAPPDATA': ''}, clear=False), \
             mock.patch.object(pathlib.Path, 'is_file', autospec=True, side_effect=lambda p: str(p) == win_chrome):
            self.assertEqual(rd.chrome_path(), win_chrome)

        with mock.patch.object(rd.shutil, 'which', return_value=None), \
             mock.patch.object(pathlib.Path, 'is_file', return_value=False):
            self.assertIsNone(rd.chrome_path())

    def test_find_axe_without_npm_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            fake_cache = pathlib.Path(d) / 'cache'
            with mock.patch.object(rd, 'CACHE', fake_cache), \
                 mock.patch.dict(os.environ, {'AXE_JS': ''}, clear=False), \
                 mock.patch.object(rd.shutil, 'which', return_value=None), \
                 mock.patch.object(pathlib.Path, 'is_file', return_value=False):
                self.assertIsNone(rd.find_axe())

    def test_find_axe_reads_env_file_when_present(self):
        with tempfile.TemporaryDirectory() as d:
            axe_file = pathlib.Path(d) / 'axe.min.js'
            axe_file.write_text('/* axe */', encoding='utf-8')
            with mock.patch.dict(os.environ, {'AXE_JS': str(axe_file)}, clear=False):
                self.assertEqual(rd.find_axe(), '/* axe */')


class Helpers(unittest.TestCase):
    def test_write_temp_render_pid_scoped_and_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            src = pathlib.Path(d) / 'demo.html'
            src.write_text('<h1>Hi</h1>', encoding='utf-8')
            out = rd.write_temp_render(src, '<p>rendered</p>')
            try:
                self.assertEqual(out.parent, src.parent)
                self.assertEqual(out.name, f'.demo.{os.getpid()}.render.html')
                self.assertEqual(out.read_text(encoding='utf-8'), '<p>rendered</p>')
            finally:
                out.unlink(missing_ok=True)

            with mock.patch.object(pathlib.Path, 'write_text', side_effect=PermissionError('read-only')):
                fb = rd.write_temp_render(src, '<p>fallback</p>')
            try:
                self.assertEqual(fb.parent.resolve(), pathlib.Path(tempfile.gettempdir()).resolve())
                self.assertEqual(fb.read_text(encoding='utf-8'), '<p>fallback</p>')
            finally:
                fb.unlink(missing_ok=True)

    def test_inject_head_case_insensitive_and_fallback_prepend(self):
        self.assertEqual(
            rd._inject_head('<html><HEAD></HEAD><body></body></html>', '<style>a{content:"\\2022"}</style>'),
            '<html><HEAD><style>a{content:"\\2022"}</style></HEAD><body></body></html>',
        )
        self.assertEqual(
            rd._inject_head('<div>no head</div>', '<style>x{}</style>'),
            '<style>x{}</style><div>no head</div>',
        )

    def test_console_error_filter(self):
        for msg in (
            'Failed to load resource: net::ERR_NAME_NOT_RESOLVED',
            'Failed to load resource: net::ERR_INTERNET_DISCONNECTED',
            'Failed to load resource: net::ERR_CONNECTION_REFUSED',
            'Failed to load resource: net::ERR_BLOCKED_BY_CLIENT',
        ):
            self.assertTrue(rd.is_ignored_console_error(msg))

        self.assertFalse(rd.is_ignored_console_error('Failed to load resource: net::ERR_FILE_NOT_FOUND'))
        self.assertFalse(rd.is_ignored_console_error('Uncaught ReferenceError: ERR_HANDLER is not defined'))

    def test_compile_tailwind_uses_posix_content_path_and_utf8_replace(self):
        with tempfile.TemporaryDirectory() as d:
            cache = pathlib.Path(d) / 'cache'
            bin_dir = cache / 'node_modules' / '.bin'
            bin_dir.mkdir(parents=True)
            tw_bin = bin_dir / ('tailwindcss.cmd' if os.name == 'nt' else 'tailwindcss')
            tw_bin.write_text('', encoding='utf-8')

            captured_cfg = {}

            def fake_run(cmd, **kwargs):
                self.assertEqual(kwargs.get('encoding'), 'utf-8')
                self.assertEqual(kwargs.get('errors'), 'replace')
                if Path_cfg := next((c for c in cmd if str(c).endswith('tailwind.config.js')), None):
                    txt = pathlib.Path(Path_cfg).read_text(encoding='utf-8')
                    captured_cfg['data'] = json.loads(txt.split('module.exports=', 1)[1])
                    out_css = pathlib.Path(cmd[cmd.index('-o') + 1])
                    out_css.write_text('body{margin:0}', encoding='utf-8')
                return subprocess.CompletedProcess(cmd, 0, '{}', '')

            html = '<html><HEAD><script src=\'https://cdn.tailwindcss.com\'></script></HEAD><body></body></html>'
            with mock.patch.object(rd, 'CACHE', cache), \
                 mock.patch.object(rd.shutil, 'which', return_value='/usr/bin/tool'), \
                 mock.patch.object(rd.subprocess, 'run', side_effect=fake_run):
                result = rd.compile_tailwind(html)

            self.assertEqual(len(captured_cfg['data']['content']), 1)
            self.assertNotIn('\\', captured_cfg['data']['content'][0])
            self.assertTrue(captured_cfg['data']['content'][0].endswith('/page.html'))
            self.assertIn('<style>body{margin:0}</style></HEAD>', result)
            self.assertNotIn('cdn.tailwindcss.com', result)


class JsPayloads(unittest.TestCase):
    def test_js_syntax_valid_with_node(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not on PATH')
        for name, js in (
            ('CHECK_JS', rd.CHECK_JS),
            ('MOBILE_JS', rd.MOBILE_JS),
            ('INTERACT_JS', rd.INTERACT_JS),
            ('SCROLL_SWEEP_JS', rd.SCROLL_SWEEP_JS),
        ):
            with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as tf:
                tf.write(f'const _fn = ({js});\n')
                path = pathlib.Path(tf.name)
            try:
                res = subprocess.run([node, '--check', str(path)], capture_output=True, text=True,
                                     encoding='utf-8', errors='replace')
                self.assertEqual(res.returncode, 0, f'{name} syntax error: {res.stderr}')
            finally:
                path.unlink(missing_ok=True)

    def test_js_invariants(self):
        # CHECK_JS invariants
        self.assertIn("cs.webkitLineClamp === 'none'", rd.CHECK_JS)
        self.assertIn("cs.clipPath === 'inset(50%)'", rd.CHECK_JS)
        self.assertIn("cs.overflowX !== 'auto' && cs.overflowX !== 'scroll'", rd.CHECK_JS)
        self.assertIn("position !== 'absolute'", rd.CHECK_JS)
        self.assertIn("position === 'sticky'", rd.CHECK_JS)
        self.assertIn("getComputedStyle(ch).position === 'sticky'", rd.CHECK_JS)
        self.assertIn("position === 'fixed'", rd.CHECK_JS)
        self.assertIn("col.c.matches('nav') || (col.c.matches('aside') && col.c.querySelector('nav'))", rd.CHECK_JS)
        self.assertIn('Math.abs(r.top - sib.r.top) < 80', rd.CHECK_JS)
        self.assertIn('nd.nodeType === 3 && nd.textContent.trim()', rd.CHECK_JS)
        for tag in ('svg', 'img', 'canvas', 'video', 'iframe', 'input', 'textarea', 'select'):
            self.assertIn(f"'{tag}'", rd.CHECK_JS)
        self.assertIn("document.querySelectorAll('svg')", rd.CHECK_JS)
        self.assertIn('isHiddenOrRotated', rd.CHECK_JS)
        self.assertIn('hollow-text', rd.CHECK_JS)
        self.assertIn('desktop-tiny-text', rd.CHECK_JS)
        self.assertIn("cs.fill === 'none'", rd.CHECK_JS)
        self.assertNotIn("if (tag === 'button' && text === ''", rd.CHECK_JS)

        # INTERACT_JS invariants (focus check runs before button clicks)
        self.assertLess(rd.INTERACT_JS.index('focusEls'), rd.INTERACT_JS.index('b.click()'))
        self.assertIn('mo.observe(document.documentElement', rd.INTERACT_JS)
        self.assertIn('Math.abs(scrollY - y) > 5', rd.INTERACT_JS)
        self.assertIn('if (scrollY !== y || scrollX !== x) scrollTo(x, y)', rd.INTERACT_JS)
        self.assertIn("b.getAttribute('aria-disabled') !== 'true'", rd.INTERACT_JS)
        self.assertNotIn('const focusable =', rd.INTERACT_JS)
        focus_re = re.search(r'/(.+)/\.test\(cls\)', rd.INTERACT_JS)
        self.assertIsNotNone(focus_re)
        py_focus_re = re.compile(focus_re.group(1))
        for bad_cls in ('focus:outline-none', 'focus:ring-0', 'focus:outline-0', 'focus:border-transparent'):
            self.assertIsNone(py_focus_re.search(bad_cls), bad_cls)
        for ok_cls in ('focus-visible:ring-2', 'focus-visible:outline', 'focus:outline-2', 'focus:border-indigo-500'):
            self.assertIsNotNone(py_focus_re.search(ok_cls), ok_cls)

        # SCROLL_SWEEP_JS & MOBILE_JS invariants
        self.assertIn("behavior: 'instant'", rd.SCROLL_SWEEP_JS)
        self.assertIn('parseFloat(cs.opacity) !== 0', rd.MOBILE_JS)
        self.assertIn("e.tagName === 'INPUT' && (e.type || '').toLowerCase() === 'hidden'", rd.MOBILE_JS)
        self.assertIn('r.height < 36 && r.width <= 120', rd.MOBILE_JS)
        self.assertIn("e.getAttribute('aria-label') || e.placeholder || e.tagName", rd.MOBILE_JS)
        self.assertIn('nd.nodeType === 3 && nd.textContent.trim().length > 3', rd.MOBILE_JS)

    def test_run_axe_handles_script_error(self):
        fake_page = mock.MagicMock()
        fake_page.add_script_tag.side_effect = RuntimeError('CSP blocked')
        with mock.patch.object(rd, 'find_axe', return_value='/* axe */'):
            res = rd.run_axe(fake_page)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0][:2], ('INFO', 'axe'))
        self.assertIn('CSP blocked', res[0][2])


if __name__ == '__main__':
    unittest.main()
