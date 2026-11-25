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
        opener = mock.MagicMock()
        opener.open.return_value = cm
        with mock.patch.object(rd.urllib.request, 'build_opener', return_value=opener) as build:
            self.assertTrue(rd.reachable('https://example.com'))
        # only http and https handlers: the opener cannot open file: or custom schemes at all
        build.assert_called_once_with(rd.urllib.request.HTTPHandler, rd.urllib.request.HTTPSHandler)
        opener.open.assert_called_once_with('https://example.com', timeout=4)
        cm.__exit__.assert_called_once()

        failing = mock.MagicMock()
        failing.open.side_effect = OSError('offline')
        with mock.patch.object(rd.urllib.request, 'build_opener', return_value=failing):
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
    PAYLOAD_FILES = (
        ('CHECK_JS', 'check.js'),
        ('MOBILE_JS', 'mobile.js'),
        ('INTERACT_JS', 'interact.js'),
        ('SCROLL_SWEEP_JS', 'sweep.js'),
    )

    def _read_payload(self, attr, fname):
        js_path = ROOT / 'scripts' / 'checks' / fname
        self.assertTrue(js_path.is_file(), f'Missing JS payload file: {js_path}')
        content = js_path.read_text(encoding='utf-8').strip()
        self.assertEqual(getattr(rd, attr), content)
        return content

    def test_js_syntax_valid_with_node(self):
        self.assertEqual(rd.CHECKS_DIR, ROOT / 'scripts' / 'checks')
        payloads = [(name, self._read_payload(name, fname)) for name, fname in self.PAYLOAD_FILES]
        node = shutil.which('node')
        if not node:
            self.skipTest('node not on PATH')
        for name, js in payloads:
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
        check_js = self._read_payload('CHECK_JS', 'check.js')
        mobile_js = self._read_payload('MOBILE_JS', 'mobile.js')
        interact_js = self._read_payload('INTERACT_JS', 'interact.js')
        sweep_js = self._read_payload('SCROLL_SWEEP_JS', 'sweep.js')

        # CHECK_JS invariants
        self.assertIn("cs.webkitLineClamp === 'none'", check_js)
        self.assertIn("cs.clipPath === 'inset(50%)'", check_js)
        self.assertIn("cs.overflowX !== 'auto' && cs.overflowX !== 'scroll'", check_js)
        self.assertIn("position !== 'absolute'", check_js)
        self.assertIn("position === 'sticky'", check_js)
        self.assertIn("getComputedStyle(ch).position === 'sticky'", check_js)
        self.assertIn("position === 'fixed'", check_js)
        self.assertIn("col.c.matches('nav') || (col.c.matches('aside') && col.c.querySelector('nav'))", check_js)
        self.assertIn('Math.abs(r.top - sib.r.top) < 80', check_js)
        self.assertIn('nd.nodeType === 3 && nd.textContent.trim()', check_js)
        for tag in ('svg', 'img', 'canvas', 'video', 'iframe', 'input', 'textarea', 'select'):
            self.assertIn(f"'{tag}'", check_js)
        self.assertIn("document.querySelectorAll('svg')", check_js)
        self.assertIn('isHiddenOrRotated', check_js)
        self.assertIn('hollow-text', check_js)
        self.assertIn('desktop-tiny-text', check_js)
        self.assertIn("cs.fill === 'none'", check_js)
        self.assertNotIn("if (tag === 'button' && text === ''", check_js)

        # INTERACT_JS invariants (focus check runs before button clicks)
        self.assertLess(interact_js.index('focusEls'), interact_js.index('b.click()'))
        self.assertIn('mo.observe(document.documentElement', interact_js)
        self.assertIn('Math.abs(scrollY - y) > 5', interact_js)
        self.assertIn('if (scrollY !== y || scrollX !== x) scrollTo(x, y)', interact_js)
        self.assertIn("b.getAttribute('aria-disabled') !== 'true'", interact_js)
        self.assertIn('[data-theme-toggle], [data-destructive]', interact_js)
        self.assertIn('savedStorage', interact_js)
        self.assertIn('finally', interact_js)
        self.assertNotIn('const focusable =', interact_js)
        focus_re = re.search(r'/(.+)/\.test\(cls\)', interact_js)
        self.assertIsNotNone(focus_re)
        py_focus_re = re.compile(focus_re.group(1))
        for bad_cls in ('focus:outline-none', 'focus:ring-0', 'focus:outline-0', 'focus:border-transparent'):
            self.assertIsNone(py_focus_re.search(bad_cls), bad_cls)
        for ok_cls in ('focus-visible:ring-2', 'focus-visible:outline', 'focus:outline-2', 'focus:border-indigo-500'):
            self.assertIsNotNone(py_focus_re.search(ok_cls), ok_cls)

        # SCROLL_SWEEP_JS & MOBILE_JS invariants
        self.assertIn("behavior: 'instant'", sweep_js)
        self.assertIn('parseFloat(cs.opacity) !== 0', mobile_js)
        self.assertIn("e.tagName === 'INPUT' && (e.type || '').toLowerCase() === 'hidden'", mobile_js)
        self.assertIn("e.tagName !== 'A' || e.getAttribute('role') === 'button'", mobile_js)
        self.assertIn('r.height < 36 && (isControl || isBtnLink || isSmallStandaloneLink)', mobile_js)
        self.assertIn("e.getAttribute('aria-label') || e.placeholder || e.tagName", mobile_js)
        self.assertIn('nd.nodeType === 3 && nd.textContent.trim().length > 3', mobile_js)

    def test_run_axe_handles_script_error(self):
        fake_page = mock.MagicMock()
        fake_page.add_script_tag.side_effect = RuntimeError('CSP blocked')
        with mock.patch.object(rd, 'find_axe', return_value='/* axe */'):
            res = rd.run_axe(fake_page)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0][:2], ('INFO', 'axe-error'))
        self.assertIn('CSP blocked', res[0][2])


class TailwindV4OfflineTests(unittest.TestCase):
    def test_linear_gradient_shorthand_rewritten_all_directions(self):
        for d in ('t', 'tr', 'r', 'br', 'b', 'bl', 'l', 'tl'):
            src = f'<div class="bg-linear-to-{d} hover:bg-linear-to-{d}/oklch !bg-linear-to-{d}"></div>'
            out = rd.normalize_tailwind_v4_offline(src)
            self.assertEqual(
                out,
                f'<div class="bg-gradient-to-{d} hover:bg-gradient-to-{d} !bg-gradient-to-{d}"></div>',
            )
        untouched = '<a href="bg-linear-to-r/docs" class="custom-bg-linear-to-r-token">Link</a>'
        self.assertEqual(rd.normalize_tailwind_v4_offline(untouched), untouched)

    def test_non_v3_opacity_steps_rewritten_outside_urls_and_font_sizes(self):
        html = (
            '<div class="bg-white/12 bg-black/8 border-white/14 text-white/65 text-white/72 '
            'ring-indigo-500/24 from-sky-500/18 via-purple-500/7 to-pink-500/99 '
            'fill-emerald-500/33 stroke-amber-400/42 dark:hover:bg-slate-900/16 '
            'text-sm/6 text-lg/8 text-2xl/9 bg-white/0 bg-white/100">'
            '<a href="to-docs/12" src="https://cdn.example.com/bg-white/12" '
            'style="background-image:url(bg-black/8.png)">Docs</a></div>'
        )
        out = rd.normalize_tailwind_v4_offline(html)
        self.assertIn('bg-white/[0.12]', out)
        self.assertIn('bg-black/[0.08]', out)
        self.assertIn('border-white/[0.14]', out)
        self.assertIn('text-white/65', out)
        self.assertIn('text-white/[0.72]', out)
        self.assertIn('ring-indigo-500/[0.24]', out)
        self.assertIn('from-sky-500/[0.18]', out)
        self.assertIn('via-purple-500/[0.07]', out)
        self.assertIn('to-pink-500/[0.99]', out)
        self.assertIn('fill-emerald-500/[0.33]', out)
        self.assertIn('stroke-amber-400/[0.42]', out)
        self.assertIn('dark:hover:bg-slate-900/[0.16]', out)
        # Preserve v3 font-size/line-height shorthands, multiples of 5, and URLs
        self.assertIn('text-sm/6', out)
        self.assertIn('text-lg/8', out)
        self.assertIn('text-2xl/9', out)
        self.assertIn('bg-white/0', out)
        self.assertIn('bg-white/100', out)
        self.assertIn('href="to-docs/12"', out)
        self.assertIn('src="https://cdn.example.com/bg-white/12"', out)
        self.assertIn('url(bg-black/8.png)', out)
        # Idempotence check
        self.assertEqual(rd.normalize_tailwind_v4_offline(out), out)

    def test_prepare_html_target_extracts_at_theme_without_mutating_source(self):
        orig_html = (
            '<!doctype html><html><head>'
            '<style type="text/tailwindcss">'
            '@import "tailwindcss";\n'
            '@theme {\n'
            '  --color-brand: #4f46e5;\n'
            '  --color-surface: oklch(0.97 0.01 250);\n'
            '  --radius-card: 1rem;\n'
            '}'
            '</style></head>'
            '<body class="bg-surface text-brand">'
            '<div class="bg-linear-to-br from-brand/12 to-black/8 border border-white/14">Hi</div>'
            '</body></html>'
        )
        with tempfile.TemporaryDirectory() as d:
            src = pathlib.Path(d) / 'v4_card.html'
            src.write_text(orig_html, encoding='utf-8')
            with mock.patch.object(rd, 'reachable', return_value=False), \
                 mock.patch.object(rd, 'compile_tailwind', side_effect=lambda h: h):
                temp_file = rd.prepare_html_target(src)
            try:
                self.assertEqual(src.read_text(encoding='utf-8'), orig_html)
                rendered_copy = temp_file.read_text(encoding='utf-8')
                self.assertNotIn('@import "tailwindcss"', rendered_copy)
                self.assertNotIn('@theme', rendered_copy)
                self.assertNotIn('text/tailwindcss', rendered_copy)
                self.assertIn(':root {', rendered_copy)
                self.assertIn('--color-brand: #4f46e5;', rendered_copy)
                self.assertIn('--color-surface: oklch(0.97 0.01 250);', rendered_copy)
                self.assertIn('bg-gradient-to-br', rendered_copy)
                self.assertIn('from-brand/[0.12]', rendered_copy)
                self.assertIn('to-black/[0.08]', rendered_copy)
                self.assertIn('border-white/[0.14]', rendered_copy)
                cfg_match = rd.INLINE_CFG.search(rendered_copy)
                self.assertIsNotNone(cfg_match)
                cfg_data = json.loads(cfg_match.group(1))
                colors = cfg_data['theme']['extend']['colors']
                self.assertEqual(colors['brand'], '#4f46e5')
                self.assertIn('var(--color-surface)', colors['surface'])
            finally:
                temp_file.unlink(missing_ok=True)

    def test_at_theme_merges_with_existing_inline_tailwind_config(self):
        html = (
            '<html><head>'
            '<script>tailwind.config = {"darkMode": "class", "theme": {"extend": {"colors": {"existing": "#111827"}}}}</script>'
            '<style>@theme { --color-brand: #4f46e5; --color-existing: #999999; }</style>'
            '</head><body class="bg-brand/12 bg-existing"></body></html>'
        )
        out = rd.normalize_tailwind_v4_offline(html)
        cfg_match = rd.INLINE_CFG.search(out)
        self.assertIsNotNone(cfg_match)
        cfg_data = json.loads(cfg_match.group(1))
        self.assertEqual(cfg_data['darkMode'], 'class')
        colors = cfg_data['theme']['extend']['colors']
        self.assertEqual(colors['existing'], '#111827')
        self.assertEqual(colors['brand'], '#4f46e5')
        self.assertIn('bg-brand/[0.12]', out)


if __name__ == '__main__':
    unittest.main()
