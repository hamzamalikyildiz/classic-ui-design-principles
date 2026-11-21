import contextlib
import io
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import render as render_mod  # noqa: E402


class TestRenderReport(unittest.TestCase):
    def test_extract_selector(self):
        self.assertEqual(render_mod._extract_selector('overflow on `#submit-btn`'), '#submit-btn')
        self.assertEqual(render_mod._extract_selector('clipped text in .card-title'), '.card-title')
        self.assertEqual(render_mod._extract_selector('selector: button.primary failed'), 'button.primary')
        self.assertIsNone(render_mod._extract_selector('generic layout warning'))

    def test_single_target_format_json_stdout(self):
        fake_result = {
            'out': 'shot.png',
            'width': 1440,
            'height': 900,
            'scroll_height': 1200,
            'findings': [
                ['FAIL', 'overflow-x', 'horizontal overflow on `#main-grid`'],
                ['WARN', 'contrast', 'low contrast text'],
            ],
        }
        buf = io.StringIO()
        with mock.patch.object(render_mod, 'render', return_value=fake_result):
            with contextlib.redirect_stdout(buf):
                render_mod.main(['page.html', '--out', 'shot.png', '--check', '--format', 'json'])
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload['summary'], {'FAIL': 1, 'WARN': 1, 'INFO': 0})
        self.assertEqual(len(payload['captures']), 1)
        self.assertEqual(len(payload['findings']), 2)
        f0 = payload['findings'][0]
        self.assertEqual(set(f0.keys()), {'route', 'viewport', 'state', 'rule', 'severity', 'message', 'selector'})
        self.assertEqual(f0['selector'], '#main-grid')
        self.assertIsNone(payload['findings'][1]['selector'])

    def test_routes_format_json_stdout(self):
        fake_summary = {
            'out_dir': 'shots',
            'report': 'shots/REPORT.md',
            'contact_sheet': None,
            'results': [
                {
                    'route': 'home',
                    'viewport': 'desktop',
                    'state': 'default',
                    'width': 1440,
                    'height': 900,
                    'scroll_height': 900,
                    'out': 'shots/home/default-desktop.png',
                    'findings': [['WARN', 'js-errors', 'console error']],
                }
            ],
        }
        buf = io.StringIO()
        with mock.patch.object(render_mod, 'render_routes', return_value=fake_summary):
            with contextlib.redirect_stdout(buf):
                render_mod.main(['--routes', 'routes.json', '--format', 'json'])
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload['summary'], {'FAIL': 0, 'WARN': 1, 'INFO': 0})
        self.assertEqual(payload['findings'][0]['route'], 'home')
        self.assertEqual(payload['findings'][0]['viewport'], 'desktop')
        self.assertEqual(payload['findings'][0]['state'], 'default')

    def test_fail_on_fail_exit_codes(self):
        warn_only = {'out': 's.png', 'width': 1440, 'height': 900, 'scroll_height': 900,
                     'findings': [['WARN', 'contrast', 'low contrast']]}
        with mock.patch.object(render_mod, 'render', return_value=warn_only):
            with contextlib.redirect_stdout(io.StringIO()):
                render_mod.main(['p.html', '--out', 's.png', '--check', '--fail-on', 'fail'])

        with_fail = {'out': 's.png', 'width': 1440, 'height': 900, 'scroll_height': 900,
                     'findings': [['FAIL', 'overflow-x', 'overflow']]}
        with mock.patch.object(render_mod, 'render', return_value=with_fail):
            with contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as cm:
                    render_mod.main(['p.html', '--out', 's.png', '--check', '--fail-on', 'fail'])
                self.assertEqual(cm.exception.code, 1)

    def test_fail_on_warn_and_none_exit_codes(self):
        info_only = {'out': 's.png', 'width': 1440, 'height': 900, 'scroll_height': 900,
                     'findings': [['INFO', 'dom-check', 'no defects found']]}
        with mock.patch.object(render_mod, 'render', return_value=info_only):
            with contextlib.redirect_stdout(io.StringIO()):
                render_mod.main(['p.html', '--out', 's.png', '--check', '--fail-on', 'warn'])

        warn_only = {'out': 's.png', 'width': 1440, 'height': 900, 'scroll_height': 900,
                     'findings': [['WARN', 'contrast', 'low contrast']]}
        with mock.patch.object(render_mod, 'render', return_value=warn_only):
            with contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as cm:
                    render_mod.main(['p.html', '--out', 's.png', '--check', '--fail-on', 'warn'])
                self.assertEqual(cm.exception.code, 1)

        with_fail = {'out': 's.png', 'width': 1440, 'height': 900, 'scroll_height': 900,
                     'findings': [['FAIL', 'overflow-x', 'overflow']]}
        with mock.patch.object(render_mod, 'render', return_value=with_fail):
            with contextlib.redirect_stdout(io.StringIO()):
                render_mod.main(['p.html', '--out', 's.png', '--check'])

    def test_write_report_md_includes_summary_and_artifact_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = pathlib.Path(tmp)
            (out_dir / 'contact-sheet.png').write_bytes(b'png')
            (out_dir / 'home').mkdir()
            (out_dir / 'home' / 'filmstrip.png').write_bytes(b'png')
            results = [
                {
                    'route': 'home',
                    'state': 'default',
                    'viewport': 'desktop',
                    'width': 1440,
                    'scroll_height': 900,
                    'findings': [['FAIL', 'overflow-x', 'overflow'], ['WARN', 'contrast', 'warn']],
                }
            ]
            report_path = render_mod._write_report_md(out_dir, results)
            text = report_path.read_text(encoding='utf-8')
            self.assertIn('**Summary:** FAIL: 1 | WARN: 1 | INFO: 0', text)
            self.assertIn('[contact-sheet.png](contact-sheet.png)', text)
            self.assertIn('[home/filmstrip.png](home/filmstrip.png)', text)
            self.assertIn('| home | default | desktop | 1440x900 | 1 | 1 | 0 |', text)


if __name__ == '__main__':
    unittest.main()
