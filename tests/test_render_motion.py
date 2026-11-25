"""Live Playwright Chromium tests and syntax/CLI checks for --motion and scripts/checks/motion.js."""
import contextlib
import functools
import http.server
import importlib.util
import json
import pathlib
import shutil
import socket
import subprocess
import tempfile
import threading
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
MOTION_JS_PATH = ROOT / 'scripts' / 'checks' / 'motion.js'
FIXTURES_DIR = ROOT / 'tests' / 'fixtures' / 'motion'

spec = importlib.util.spec_from_file_location('render', ROOT / 'scripts' / 'render.py')
rd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rd)

MOTION_RULES = {
    'motion-layout-property',
    'reduced-motion-ignored',
    'layout-shift',
    'slow-feedback',
    'long-ui-transition',
    'infinite-motion',
}


def _unused_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class MotionJsSyntaxAndCliTests(unittest.TestCase):
    def test_motion_js_loaded_and_valid_node_syntax(self):
        self.assertTrue(MOTION_JS_PATH.is_file(), f'Missing motion.js: {MOTION_JS_PATH}')
        js = MOTION_JS_PATH.read_text(encoding='utf-8').strip()
        self.assertEqual(rd.MOTION_JS, js)

        node = shutil.which('node')
        if not node:
            self.skipTest('node not on PATH')
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
            self.assertEqual(res.returncode, 0, f'motion.js syntax error: {res.stderr}')
        finally:
            path.unlink(missing_ok=True)

    def test_parse_options_motion_flags_all_modes(self):
        opts_html = rd.parse_options(['page.html', '--out', 'shot.png', '--motion', '--motion-trigger', '#go'])
        self.assertTrue(opts_html.motion)
        self.assertEqual(opts_html.motion_trigger, '#go')

        opts_url = rd.parse_options(['--url', 'http://127.0.0.1:3000/app', '--out', 'shot.png', '--motion'])
        self.assertTrue(opts_url.motion)
        self.assertIsNone(opts_url.motion_trigger)
        self.assertTrue(opts_url.online)

        opts_routes = rd.parse_options(['--routes', 'routes.json', '--motion', '--motion-trigger', '.cta'])
        self.assertTrue(opts_routes.motion)
        self.assertEqual(opts_routes.motion_trigger, '.cta')


class RenderMotionChromiumTests(unittest.TestCase):
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

    def _run_fixture(self, filename, tmp_dir, trigger=None):
        html_path = FIXTURES_DIR / filename
        self.assertTrue(html_path.is_file(), f'Missing fixture: {html_path}')
        out_png = pathlib.Path(tmp_dir) / 'shot.png'
        opts = rd.RenderOptions(
            html=str(html_path),
            out=str(out_png),
            motion=True,
            motion_trigger=trigger,
        )
        return rd.capture(self._browser, html_path.resolve().as_uri(), opts)

    def _assert_filmstrip_created(self, tmp_dir):
        d = pathlib.Path(tmp_dir)
        for idx in range(6):
            fpath = d / f'filmstrip-{idx}.png'
            self.assertTrue(fpath.is_file(), f'Missing filmstrip frame: {fpath}')
            self.assertGreater(fpath.stat().st_size, 0)
        try:
            import PIL  # noqa: F401
        except ImportError:
            return
        strip = d / 'filmstrip.png'
        self.assertTrue(strip.is_file(), f'Missing combined filmstrip.png in {d}')
        self.assertGreater(strip.stat().st_size, 0)

    def _assert_positive_fixture(self, filename, trigger=None):
        with tempfile.TemporaryDirectory() as d:
            res = self._run_fixture(filename, d, trigger=trigger)
            triggered_motion_rules = {
                (sev, rule) for sev, rule, _ in res['findings'] if rule in MOTION_RULES
            }
            self.assertEqual(
                triggered_motion_rules,
                set(),
                f'{filename} raised false-positive motion findings: {res["findings"]}',
            )
            self._assert_filmstrip_created(d)

    def _assert_negative_fixture(self, filename, expected_sev, expected_rule, trigger=None):
        with tempfile.TemporaryDirectory() as d:
            res = self._run_fixture(filename, d, trigger=trigger)
            codes = [(sev, rule) for sev, rule, _ in res['findings']]
            self.assertIn(
                (expected_sev, expected_rule),
                codes,
                f'{filename} did not catch ({expected_sev}, {expected_rule}); got: {res["findings"]}',
            )
            self._assert_filmstrip_created(d)

    # 6 positive fixtures -> 0 motion findings + filmstrip frames
    def test_pos_transform_fade(self):
        self._assert_positive_fixture('pos_transform_fade.html')

    def test_pos_countup_ring(self):
        self._assert_positive_fixture('pos_countup_ring.html')

    def test_pos_row_highlight(self):
        self._assert_positive_fixture('pos_row_highlight.html')

    def test_pos_toast_undo(self):
        self._assert_positive_fixture('pos_toast_undo.html', trigger='#undo-btn')

    def test_pos_tab_indicator(self):
        self._assert_positive_fixture('pos_tab_indicator.html')

    def test_pos_allowed_properties(self):
        """Every property the motion policy (reference/motion.md) allows must pass the motion audit."""
        self._assert_positive_fixture('pos_allowed_properties.html', trigger='#go')

    def test_pos_reduced_motion(self):
        self._assert_positive_fixture('pos_reduced_motion.html')

    # 6 negative fixtures -> each catches its expected rule + filmstrip frames
    def test_neg_layout_property(self):
        self._assert_negative_fixture('neg_layout_property.html', 'WARN', 'motion-layout-property')

    def test_neg_reduced_motion_ignored(self):
        self._assert_negative_fixture('neg_reduced_motion_ignored.html', 'WARN', 'reduced-motion-ignored')

    def test_neg_layout_shift(self):
        self._assert_negative_fixture('neg_layout_shift.html', 'WARN', 'layout-shift')

    def test_neg_slow_feedback(self):
        self._assert_negative_fixture('neg_slow_feedback.html', 'WARN', 'slow-feedback')

    def test_neg_long_ui_transition(self):
        self._assert_negative_fixture('neg_long_ui_transition.html', 'INFO', 'long-ui-transition')

    def test_neg_infinite_motion(self):
        self._assert_negative_fixture('neg_infinite_motion.html', 'INFO', 'infinite-motion')

    def test_reduced_motion_clip_path_policy_alignment(self):
        page = self._browser.new_page(viewport={'width': 1280, 'height': 800})
        try:
            page.emulate_media(reduced_motion='reduce')
            # 1. clip-path <= 300ms (transition 260ms + @keyframes 300ms) -> allowed
            ok_html = """<!doctype html>
            <html><head><style>
              .reveal { clip-path: inset(0 0 0 0); transition: clip-path 260ms ease; padding: 12px; }
              .anim { animation: wipe 300ms ease both; padding: 12px; }
              @keyframes wipe { from { clip-path: inset(0 100% 0 0); } to { clip-path: inset(0 0 0 0); } }
            </style></head><body>
              <div class="reveal">Short clip-path transition</div>
              <div class="anim">Short clip-path animation</div>
            </body></html>"""
            page.set_content(ok_html)
            res_ok = page.evaluate(rd.MOTION_JS, {'mode': 'reduced', 'skipTrigger': True})
            self.assertEqual([(s, r) for s, r, _ in res_ok], [])

            # 2. clip-path > 300ms (380ms) -> flagged
            slow_clip_html = """<!doctype html>
            <html><head><style>
              .reveal { clip-path: inset(0 0 0 0); transition: clip-path 380ms ease; padding: 12px; }
            </style></head><body><div class="reveal">Slow clip-path</div></body></html>"""
            page.set_content(slow_clip_html)
            res_slow_clip = page.evaluate(rd.MOTION_JS, {'mode': 'reduced', 'skipTrigger': True})
            self.assertIn(('WARN', 'reduced-motion-ignored'), [(s, r) for s, r, _ in res_slow_clip])

            # 3. transform > 150ms (220ms) -> still strictly flagged
            transform_html = """<!doctype html>
            <html><head><style>
              .slide { transform: translateY(0); transition: transform 220ms ease; padding: 12px; }
            </style></head><body><div class="slide">Spatial slide</div></body></html>"""
            page.set_content(transform_html)
            res_transform = page.evaluate(rd.MOTION_JS, {'mode': 'reduced', 'skipTrigger': True})
            self.assertIn(('WARN', 'reduced-motion-ignored'), [(s, r) for s, r, _ in res_transform])
        finally:
            page.close()

    def test_reduced_motion_media_restored_and_routes_and_url_modes(self):
        page = self._browser.new_page(viewport={'width': 1280, 'height': 800})
        try:
            page.goto((FIXTURES_DIR / 'neg_reduced_motion_ignored.html').resolve().as_uri())
            with tempfile.TemporaryDirectory() as d:
                findings = rd.run_motion_checks(page, out_dir=d)
                self.assertIn(('WARN', 'reduced-motion-ignored'), [(s, r) for s, r, _ in findings])
                self._assert_filmstrip_created(d)
            is_reduced = page.evaluate("window.matchMedia('(prefers-reduced-motion: reduce)').matches")
            self.assertFalse(is_reduced)
        finally:
            page.close()

        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(FIXTURES_DIR))
        port = _unused_port()

        class _QuietServer(http.server.ThreadingHTTPServer):
            def handle_error(self, request, client_address):
                pass

        srv = _QuietServer(('127.0.0.1', port), handler)
        th = threading.Thread(target=srv.serve_forever, daemon=True)
        th.start()
        try:
            with tempfile.TemporaryDirectory() as d:
                d_path = pathlib.Path(d)
                url_dir = d_path / 'url_shot'
                url_dir.mkdir()
                url_res = rd.capture(
                    self._browser,
                    f'http://127.0.0.1:{port}/neg_slow_feedback.html',
                    rd.RenderOptions(
                        url=f'http://127.0.0.1:{port}/neg_slow_feedback.html',
                        out=str(url_dir / 'shot.png'),
                        motion=True,
                    ),
                )
                self.assertIn(('WARN', 'slow-feedback'), [(s, r) for s, r, _ in url_res['findings']])
                self._assert_filmstrip_created(url_dir)

                routes_dir = d_path / 'routes_out'
                routes_cfg = {
                    'base_url': f'http://127.0.0.1:{port}',
                    'viewports': ['desktop'],
                    'routes': [
                        {'name': 'motion-pos', 'path': '/pos_tab_indicator.html'},
                        {'name': 'motion-neg', 'path': '/neg_layout_property.html'},
                    ],
                }
                routes_file = d_path / 'routes.json'
                routes_file.write_text(json.dumps(routes_cfg), encoding='utf-8')
                summary = rd.render_routes(
                    rd.RenderOptions(routes=str(routes_file), out_dir=str(routes_dir), check=True, motion=True),
                    browser=self._browser,
                )
                by_route = {r['route']: r for r in summary['results']}
                pos_motion = {(s, rule) for s, rule, _ in by_route['motion-pos']['findings'] if rule in MOTION_RULES}
                self.assertEqual(pos_motion, set())
                neg_codes = [(s, rule) for s, rule, _ in by_route['motion-neg']['findings']]
                self.assertIn(('WARN', 'motion-layout-property'), neg_codes)
                self._assert_filmstrip_created(routes_dir / 'motion-pos')
                self._assert_filmstrip_created(routes_dir / 'motion-neg')
        finally:
            srv.shutdown()
            srv.server_close()


if __name__ == '__main__':
    unittest.main()
