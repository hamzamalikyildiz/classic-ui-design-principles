"""Unit tests for unified verification script scripts/verify.py."""
import contextlib
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))

import verify as V  # noqa: E402


CLEAN_TSX = """\
export function StatusCard() {
  return (
    <div className="rounded-xl bg-white p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-slate-900 text-balance">Deployment Ready</h2>
      <p className="mt-2 max-w-prose text-sm text-slate-700">
        All preflight checks completed cleanly across staging clusters.
      </p>
      <button className="mt-4 h-11 rounded-lg bg-slate-900 px-4 text-sm font-medium text-white">
        Promote Build
      </button>
    </div>
  );
}
"""

FAIL_CONTRAST_TSX = """\
export function LowContrastBadge() {
  return (
    <div className="bg-white p-4">
      <span className="text-sm text-slate-200">Unreadable label</span>
    </div>
  );
}
"""

WARN_GRID_HTML = """\
<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Demo</title></head>
<body class="bg-white text-slate-900">
  <main class="p-[13px]">
    <h1 class="text-2xl font-semibold text-balance">Dashboard</h1>
  </main>
</body>
</html>
"""

CLEAN_HTML = """\
<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Clean</title></head>
<body class="bg-white text-slate-900">
  <main class="p-6">
    <h1 class="text-2xl font-semibold text-balance">Overview</h1>
    <p class="mt-2 max-w-prose text-base text-slate-700">Healthy service status.</p>
  </main>
</body>
</html>
"""


def _run_verify(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = V.main(argv)
    return code, out.getvalue()


class VerifyStaticOnlyTests(unittest.TestCase):
    def test_static_only_tsx_clean_does_not_attempt_render(self):
        with tempfile.TemporaryDirectory() as td:
            tsx = pathlib.Path(td) / 'StatusCard.tsx'
            tsx.write_text(CLEAN_TSX, encoding='utf-8')
            with mock.patch.object(V.R, 'render') as mock_render:
                code, stdout = _run_verify([str(tsx), '--format', 'json'])
            mock_render.assert_not_called()
            self.assertEqual(code, 0)
            data = json.loads(stdout)
            self.assertTrue(data['passed'])
            self.assertTrue(data['static']['ran'])
            self.assertFalse(data['render']['ran'])
            self.assertEqual(data['summary']['FAIL'], 0)
            self.assertEqual(data['summary']['WARN'], 0)

    def test_static_only_tsx_contrast_fail_exits_1_by_default(self):
        with tempfile.TemporaryDirectory() as td:
            tsx = pathlib.Path(td) / 'Bad.tsx'
            tsx.write_text(FAIL_CONTRAST_TSX, encoding='utf-8')
            code, stdout = _run_verify([str(tsx)])
            self.assertEqual(code, 1)
            self.assertIn('[FAIL] wcag-aa', stdout)
            self.assertIn('SUMMARY FAIL=1', stdout)

            # --fail-on none exits 0 even with FAIL
            code_none, stdout_json = _run_verify([str(tsx), '--fail-on', 'none', '--format', 'json'])
            self.assertEqual(code_none, 0)
            data = json.loads(stdout_json)
            self.assertTrue(data['passed'])
            self.assertEqual(data['summary']['FAIL'], 1)

    def test_route_and_routes_glob_inlining(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            comp_dir = root / 'components'
            app_dir = root / 'app'
            comp_dir.mkdir()
            app_dir.mkdir()
            (comp_dir / 'Hero.tsx').write_text(
                'export function Hero() { return <p className="text-slate-200 bg-white">Low contrast</p>; }\n',
                encoding='utf-8',
            )
            (app_dir / 'page.tsx').write_text(
                'import { Hero } from "../components/Hero";\n'
                'export default function Page() { return <main className="p-6"><Hero /></main>; }\n',
                encoding='utf-8',
            )
            code, stdout = _run_verify([
                '--routes-glob', 'app/**/page.tsx',
                '--root', str(root),
                '--format', 'json',
            ])
            self.assertEqual(code, 1)
            data = json.loads(stdout)
            self.assertFalse(data['passed'])
            self.assertEqual(data['static']['targets'][0]['inlined_count'], 1)
            self.assertGreaterEqual(data['summary']['FAIL'], 1)


class VerifyHtmlAndRenderIntegrationTests(unittest.TestCase):
    def test_html_no_render_runs_static_only(self):
        with tempfile.TemporaryDirectory() as td:
            html = pathlib.Path(td) / 'page.html'
            html.write_text(WARN_GRID_HTML, encoding='utf-8')
            with mock.patch.object(V.R, 'render') as mock_render:
                code_default, txt_out = _run_verify([str(html), '--no-render'])
                code_warn, json_out = _run_verify([str(html), '--no-render', '--fail-on', 'warn', '--format', 'json'])
            mock_render.assert_not_called()
            # Default --fail-on fail passes on WARN-only
            self.assertEqual(code_default, 0)
            self.assertIn('[WARN] grid', txt_out)
            # --fail-on warn exits 1 when WARN > 0
            self.assertEqual(code_warn, 1)
            data = json.loads(json_out)
            self.assertFalse(data['passed'])
            self.assertGreaterEqual(data['summary']['WARN'], 1)
            self.assertFalse(data['render']['ran'])

    def test_playwright_missing_emits_info_without_crashing(self):
        with tempfile.TemporaryDirectory() as td:
            html = pathlib.Path(td) / 'clean.html'
            html.write_text(CLEAN_HTML, encoding='utf-8')
            with mock.patch.object(V, 'is_playwright_available', return_value=False):
                code, txt_out = _run_verify([str(html)])
                code_json, json_out = _run_verify([str(html), '--format', 'json'])
            self.assertEqual(code, 0)
            self.assertIn('[INFO] render-skipped: Playwright not installed; static audit only', txt_out)
            self.assertEqual(code_json, 0)
            data = json.loads(json_out)
            self.assertTrue(data['passed'])
            self.assertTrue(data['render']['skipped'])
            self.assertEqual(data['render']['findings'][0]['rule'], 'render-skipped')

    def test_playwright_missing_with_require_axe_fails(self):
        with tempfile.TemporaryDirectory() as td:
            html = pathlib.Path(td) / 'clean.html'
            html.write_text(CLEAN_HTML, encoding='utf-8')
            with mock.patch.object(V, 'is_playwright_available', return_value=False):
                code, json_out = _run_verify([str(html), '--require-axe', '--format', 'json'])
            self.assertEqual(code, 1)
            data = json.loads(json_out)
            self.assertFalse(data['passed'])
            self.assertEqual(data['render']['findings'][0]['rule'], 'axe-not-run')
            self.assertGreaterEqual(data['summary']['FAIL'], 1)

    def test_html_static_plus_mocked_render_combines_findings(self):
        with tempfile.TemporaryDirectory() as td:
            html = pathlib.Path(td) / 'page.html'
            shot = pathlib.Path(td) / 'shot.png'
            html.write_text(WARN_GRID_HTML, encoding='utf-8')
            fake_res = {
                'out': str(shot),
                'width': 1440,
                'scroll_height': 900,
                'findings': [['WARN', 'overflow-x', 'horizontal overflow 1520px > 1440px']],
                'console_errors': [],
                'network_errors': [],
            }
            with mock.patch.object(V, 'is_playwright_available', return_value=True), \
                 mock.patch.object(V.R, 'render', return_value=fake_res) as mock_render:
                code_fail, out_json = _run_verify([
                    str(html), '--out', str(shot), '--motion', '--motion-trigger', '#go', '--format', 'json',
                ])
                code_warn, _ = _run_verify([
                    str(html), '--out', str(shot), '--fail-on', 'warn',
                ])

            opts_passed = mock_render.call_args_list[0][0][0]
            self.assertTrue(opts_passed.check)
            self.assertTrue(opts_passed.motion)
            self.assertEqual(opts_passed.motion_trigger, '#go')

            self.assertEqual(code_fail, 0)
            self.assertEqual(code_warn, 1)
            data = json.loads(out_json)
            self.assertTrue(data['static']['ran'])
            self.assertTrue(data['render']['ran'])
            # Static grid WARN (1) + rendered overflow-x WARN (1) >= 2
            self.assertGreaterEqual(data['summary']['WARN'], 2)

    def test_require_axe_fails_when_axe_not_run_returned(self):
        with tempfile.TemporaryDirectory() as td:
            html = pathlib.Path(td) / 'clean.html'
            html.write_text(CLEAN_HTML, encoding='utf-8')
            fake_res = {
                'out': None,
                'width': 1440,
                'scroll_height': 900,
                'findings': [['INFO', 'axe-not-run', 'axe-core unavailable']],
                'console_errors': [],
                'network_errors': [],
            }
            with mock.patch.object(V, 'is_playwright_available', return_value=True), \
                 mock.patch.object(V.R, 'render', return_value=fake_res):
                code, out_json = _run_verify([str(html), '--require-axe', '--fail-on', 'none', '--format', 'json'])
            self.assertEqual(code, 1)
            data = json.loads(out_json)
            self.assertFalse(data['passed'])

    def test_routes_json_with_local_html_runs_static_audit_too(self):
        with tempfile.TemporaryDirectory() as td:
            d = pathlib.Path(td)
            html = d / 'app.html'
            html.write_text(WARN_GRID_HTML, encoding='utf-8')
            routes_path = d / 'routes.json'
            routes_path.write_text(json.dumps({
                'base_url': html.resolve().as_uri(),
                'routes': [{'name': 'home', 'path': '#/home', 'states': ['default']}],
            }), encoding='utf-8')

            fake_routes_res = {
                'out_dir': str(d / 'shots'),
                'report': str(d / 'shots' / 'REPORT.md'),
                'contact_sheet': str(d / 'shots' / 'contact-sheet.png'),
                'results': [{
                    'route': 'home',
                    'viewport': 'desktop',
                    'state': 'default',
                    'width': 1440,
                    'height': 900,
                    'scroll_height': 900,
                    'out': str(d / 'shots' / 'home' / 'default-desktop.png'),
                    'findings': [['INFO', 'dom-check', 'no defects found']],
                }],
            }
            with mock.patch.object(V, 'is_playwright_available', return_value=True), \
                 mock.patch.object(V.R, 'render_routes', return_value=fake_routes_res) as mock_rr:
                code, out_json = _run_verify([
                    '--routes', str(routes_path),
                    '--out-dir', str(d / 'shots'),
                    '--format', 'json',
                ])
            mock_rr.assert_called_once()
            self.assertEqual(code, 0)
            data = json.loads(out_json)
            # Static audit ran automatically on local app.html referenced by routes.json!
            self.assertTrue(data['static']['ran'])
            self.assertEqual(len(data['static']['targets']), 1)
            self.assertTrue(any(f['rule'] == 'grid' for f in data['static']['findings']))
            self.assertTrue(data['render']['ran'])

    def test_cli_subprocess_execution(self):
        with tempfile.TemporaryDirectory() as td:
            tsx = pathlib.Path(td) / 'Card.tsx'
            tsx.write_text(CLEAN_TSX, encoding='utf-8')
            res = subprocess.run(
                [sys.executable, str(ROOT / 'scripts' / 'verify.py'), str(tsx), '--format', 'json'],
                capture_output=True,
                text=True,
                timeout=15,
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            parsed = json.loads(res.stdout)
            self.assertTrue(parsed['passed'])


if __name__ == '__main__':
    unittest.main()
