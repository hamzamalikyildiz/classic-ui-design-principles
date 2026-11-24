"""scripts/e2e_gate.py: the demo's defects must be caught, the clean example may not regress (issue #2, item 1)."""
import contextlib
import io
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import e2e_gate as gate  # noqa: E402


def report(*pairs):
    return {'summary': {}, 'findings': [{'severity': s, 'rule': r, 'message': ''} for s, r in pairs]}


def run_gate(rep, flag, spec):
    with tempfile.TemporaryDirectory() as d:
        r, s = pathlib.Path(d) / 'r.json', pathlib.Path(d) / 's.json'
        r.write_text(json.dumps(rep), encoding='utf-8')
        s.write_text(json.dumps(spec), encoding='utf-8')
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = gate.main([str(r), flag, str(s)])
        return code, out.getvalue()


class ExpectMode(unittest.TestCase):
    def test_passes_when_every_expected_rule_is_caught(self):
        code, _ = run_gate(report(('WARN', 'a'), ('WARN', 'b'), ('INFO', 'c')), '--expect', ['a', 'b'])
        self.assertEqual(code, 0)

    def test_fails_when_a_defect_is_no_longer_caught(self):
        code, out = run_gate(report(('WARN', 'a')), '--expect', ['a', 'b'])
        self.assertEqual(code, 1)
        self.assertIn('not caught: b', out)

    def test_info_does_not_count_as_caught(self):
        code, _ = run_gate(report(('INFO', 'a')), '--expect', ['a'])
        self.assertEqual(code, 1)


class BaselineMode(unittest.TestCase):
    ALLOWED = {'allowed': {'empty-column': 2}}

    def test_within_baseline_passes(self):
        code, _ = run_gate(report(('WARN', 'empty-column'), ('INFO', 'anything')), '--baseline', self.ALLOWED)
        self.assertEqual(code, 0)

    def test_new_rule_fails(self):
        code, out = run_gate(report(('WARN', 'clipped-content')), '--baseline', self.ALLOWED)
        self.assertEqual(code, 1)
        self.assertIn('clipped-content', out)

    def test_higher_count_fails(self):
        code, _ = run_gate(report(*[('WARN', 'empty-column')] * 3), '--baseline', self.ALLOWED)
        self.assertEqual(code, 1)

    def test_fail_findings_are_never_allowed(self):
        code, out = run_gate(report(('FAIL', 'empty-column')), '--baseline', {'allowed': {'empty-column': 5}})
        self.assertEqual(code, 1)
        self.assertIn('FAIL findings are never allowed', out)


class SkippedAxe(unittest.TestCase):
    def test_axe_that_did_not_run_fails_both_modes(self):
        for rule in ('axe-not-run', 'axe-error'):
            for flag, spec in (('--expect', []), ('--baseline', {'allowed': {}})):
                with self.subTest(rule=rule, flag=flag):
                    code, out = run_gate(report(('INFO', rule)), flag, spec)
                    self.assertEqual(code, 1)
                    self.assertIn('did not run', out)

    def test_unreadable_input_is_exit_2(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(gate.main(['missing.json', '--expect', 'also-missing.json']), 2)


class CommittedSpecs(unittest.TestCase):
    def test_spec_files_are_valid(self):
        exp = json.loads((ROOT / 'examples/app-demo/expected_findings.json').read_text(encoding='utf-8'))
        self.assertTrue(exp['rules'] and all(isinstance(r, str) for r in exp['rules']))
        base = json.loads((ROOT / 'examples/app-demo-polished/baseline_findings.json').read_text(encoding='utf-8'))
        self.assertTrue(base['allowed'] and all(isinstance(n, int) for n in base['allowed'].values()))
        self.assertFalse(set(exp['rules']) & set(base['allowed']) - {'blank-band'},
                         'the clean example must not be allowed to produce the demo defects')


if __name__ == '__main__':
    unittest.main()
