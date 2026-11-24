"""A skipped accessibility check must never read as a pass (issue #2, item 2)."""
import contextlib
import io
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import render as rd  # noqa: E402


class FakePage:
    def __init__(self, result=None, error=None):
        self.result, self.error = result, error

    def add_script_tag(self, content):
        if self.error == 'script':
            raise RuntimeError('script injection blocked')

    def evaluate(self, js):
        if self.error == 'run':
            raise RuntimeError('axe.run exploded')
        return self.result


class AxeStatusTests(unittest.TestCase):
    def tearDown(self):
        rd.REQUIRE_AXE = False

    def test_missing_axe_says_it_did_not_run(self):
        with mock.patch.object(rd, 'find_axe', return_value=None):
            sev, rule, msg = rd.run_axe(FakePage())[0]
        self.assertEqual((sev, rule), ('INFO', 'axe-not-run'))
        self.assertIn('NOT checked', msg)

    def test_missing_axe_fails_when_required(self):
        rd.REQUIRE_AXE = True
        with mock.patch.object(rd, 'find_axe', return_value=None):
            self.assertEqual(rd.run_axe(FakePage())[0][:2], ('FAIL', 'axe-not-run'))

    def test_runtime_error_is_reported_separately(self):
        for where in ('script', 'run'):
            with self.subTest(where=where), mock.patch.object(rd, 'find_axe', return_value='/* axe */'):
                sev, rule, msg = rd.run_axe(FakePage(error=where))[0]
                self.assertEqual((sev, rule), ('INFO', 'axe-error'))
                self.assertIn('NOT checked', msg)
                rd.REQUIRE_AXE = True
                self.assertEqual(rd.run_axe(FakePage(error=where))[0][:2], ('FAIL', 'axe-error'))
                rd.REQUIRE_AXE = False

    def test_normal_run_still_maps_impact_to_severity(self):
        res = [{'id': 'color-contrast', 'impact': 'serious', 'n': 1, 'help': 'contrast', 't': 'button'},
               {'id': 'region', 'impact': 'moderate', 'n': 2, 'help': 'landmarks', 't': 'html'}]
        with mock.patch.object(rd, 'find_axe', return_value='/* axe */'):
            out = rd.run_axe(FakePage(result=res))
        self.assertEqual([(s, r) for s, r, _ in out], [('WARN', 'axe-color-contrast'), ('INFO', 'axe-region')])


class RequireAxeCliTests(unittest.TestCase):
    def test_exit_code_with_axe_missing(self):
        page = pathlib.Path(tempfile.mkdtemp()) / 'ok.html'
        page.write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>t</title></head>'
                        '<body><main><h1>Hi</h1></main></body></html>', encoding='utf-8')
        out = page.with_suffix('.png')
        base = [str(page), '--out', str(out), '--check']
        codes = {}
        for flag in ([], ['--require-axe']):
            with mock.patch.object(rd, 'find_axe', return_value=None), \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                try:
                    rd.main(base + flag)
                    codes[bool(flag)] = 0
                except SystemExit as exc:
                    codes[bool(flag)] = exc.code
                except Exception as exc:  # Chromium not available on this machine
                    raise unittest.SkipTest(f'Playwright/Chromium unavailable: {exc}')
        self.assertEqual(codes[False], 0, 'default mode keeps going when axe is missing')
        self.assertEqual(codes[True], 1, '--require-axe must fail when axe is missing')


if __name__ == '__main__':
    unittest.main()
