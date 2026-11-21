#!/usr/bin/env python3
"""Tests for baseline mode (--baseline / --write-baseline) in uiignore and uitools."""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))

from uiignore import filter_baseline, issue_hash, load_baseline, write_baseline


class BaselineUnitTests(unittest.TestCase):
    def test_issue_hash_ignores_line_numbers_and_path_prefix(self):
        src1 = '<div class="border-4">hi</div>\n'
        src2 = '\n' * 10 + '<div class="border-4">hi</div>\n'
        h1 = issue_hash('./app/page.tsx', 'border-heavy', 'L1 heavy border-4', source_txt=src1)
        h2 = issue_hash('app/page.tsx', 'border-heavy', 'L11 heavy border-4', source_txt=src2)
        self.assertEqual(h1, h2)

    def test_load_baseline_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = pathlib.Path(tmp) / 'nonexistent.json'
            self.assertEqual(load_baseline(missing), set())

    def test_write_and_filter_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            bp = pathlib.Path(tmp) / '.uitools-baseline.json'
            h1 = issue_hash('a.tsx', 'border-heavy', 'L1 border-4')
            write_baseline(bp, [h1])
            loaded = load_baseline(bp)
            self.assertEqual(loaded, {h1})

            issues = [
                ('a.tsx', 'WARN', 'border-heavy', 'L1 border-4'),
                ('a.tsx', 'FAIL', 'no-mono', 'L5 font-mono used'),
            ]
            new_issues, skipped = filter_baseline(issues, loaded)
            self.assertEqual(skipped, 1)
            self.assertEqual(len(new_issues), 1)
            self.assertEqual(new_issues[0][2], 'no-mono')


class BaselineCLITests(unittest.TestCase):
    def _run_uitools(self, *args, cwd=None):
        return subprocess.run(
            [sys.executable, str(ROOT / 'scripts' / 'uitools.py'), *args],
            cwd=cwd or str(ROOT),
            capture_output=True,
            text=True,
        )

    def test_write_baseline_and_filter_existing_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            target = tmp_path / 'sample.tsx'
            # Trigger a FAIL (e.g. shadow-2xl or font-mono or similar)
            target.write_text(
                'export default function Page() {\n'
                '  return (\n'
                '    <div>\n'
                '      <main className="bg-[#ffffff] text-[#f0f0f0] p-4">Hello</main>\n'
                '    </div>\n'
                '  );\n'
                '}\n',
                encoding='utf-8',
            )
            baseline_file = tmp_path / '.uitools-baseline.json'

            # Write baseline
            res_write = self._run_uitools(
                'audit', str(target), '--baseline', str(baseline_file), '--write-baseline',
                cwd=tmp,
            )
            self.assertEqual(res_write.returncode, 0, res_write.stderr)
            self.assertTrue(baseline_file.is_file())
            data = json.loads(baseline_file.read_text(encoding='utf-8'))
            self.assertGreaterEqual(len(data['entries']), 1)

            # Audit with baseline -> 0 new issues, exit 0
            res_check = self._run_uitools(
                'audit', str(target), '--baseline', str(baseline_file),
                cwd=tmp,
            )
            self.assertEqual(res_check.returncode, 0, res_check.stdout + res_check.stderr)
            self.assertIn('BASELINE_SKIPPED=', res_check.stdout)
            self.assertIn('FAIL=0', res_check.stdout)

    def test_line_shift_does_not_break_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            target = tmp_path / 'sample.tsx'
            original = (
                'export default function Page() {\n'
                '  return <main className="bg-[#ffffff] text-[#f0f0f0] p-4">Hello</main>;\n'
                '}\n'
            )
            target.write_text(original, encoding='utf-8')
            baseline_file = tmp_path / '.uitools-baseline.json'

            res_write = self._run_uitools(
                'audit', str(target), '--baseline', str(baseline_file), '--write-baseline',
                cwd=tmp,
            )
            self.assertEqual(res_write.returncode, 0)

            # Insert 10 blank lines at the top
            target.write_text('\n' * 10 + original, encoding='utf-8')

            res_check = self._run_uitools(
                'audit', str(target), '--baseline', str(baseline_file),
                cwd=tmp,
            )
            self.assertEqual(res_check.returncode, 0, res_check.stdout + res_check.stderr)
            self.assertIn('FAIL=0', res_check.stdout)

    def test_new_fail_is_reported_and_exits_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            target = tmp_path / 'sample.tsx'
            target.write_text(
                'export default function Page() {\n'
                '  return (\n'
                '    <div>\n'
                '      <main className="bg-[#ffffff] text-[#f0f0f0] p-4">Hello</main>\n'
                '    </div>\n'
                '  );\n'
                '}\n',
                encoding='utf-8',
            )
            baseline_file = tmp_path / '.uitools-baseline.json'

            res_write = self._run_uitools(
                'audit', str(target), '--baseline', str(baseline_file), '--write-baseline',
                cwd=tmp,
            )
            self.assertEqual(res_write.returncode, 0)

            # Add a new FAIL: low-contrast div on a new line
            target.write_text(
                'export default function Page() {\n'
                '  return (\n'
                '    <div>\n'
                '      <main className="bg-[#ffffff] text-[#f0f0f0] p-4">Hello</main>\n'
                '      <div className="bg-[#ffffff] text-[#e8e8e8]">New Fail</div>\n'
                '    </div>\n'
                '  );\n'
                '}\n',
                encoding='utf-8',
            )

            res_check = self._run_uitools(
                'audit', str(target), '--baseline', str(baseline_file),
                cwd=tmp,
            )
            self.assertEqual(res_check.returncode, 1, res_check.stdout + res_check.stderr)
            self.assertIn('FAIL=1', res_check.stdout)


if __name__ == '__main__':
    unittest.main()
