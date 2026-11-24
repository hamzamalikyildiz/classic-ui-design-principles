#!/usr/bin/env python3
"""CI gate for `render.py --routes ... --format json` reports (stdlib only).

Two different questions, two modes:

  expect:    python scripts/e2e_gate.py report.json --expect examples/app-demo/expected_findings.json
             The deliberately flawed demo must still be caught: every rule in the file has to appear.
  baseline:  python scripts/e2e_gate.py report.json --baseline examples/app-demo-polished/baseline_findings.json
             The clean example may only produce findings listed in the file (rule -> highest allowed count);
             any other WARN/FAIL, or a higher count, fails the run. FAIL findings are never allowed.

Both modes also fail when the accessibility check did not run (`axe-not-run`, `axe-error`), so a skipped
axe can never look like a pass.  Exit code 0 = ok, 1 = gate failed, 2 = bad input.
"""
import argparse, collections, json, pathlib, sys

NOT_RUN = {'axe-not-run', 'axe-error'}


def findings(report):
    for f in report.get('findings', []):
        if isinstance(f, dict):
            yield f.get('severity'), f.get('rule')
        else:
            yield f[0], f[1]


def counts(report, severities=('WARN', 'FAIL')):
    c = collections.Counter()
    for sev, rule in findings(report):
        if sev in severities:
            c[rule] += 1
    return c


def seen_rules(report):
    """Every rule that appeared at any severity (a check that did not run shows up as axe-not-run/axe-error)."""
    return {rule for _, rule in findings(report)}


def gate_expect(report, expected):
    got = counts(report)
    return [f'expected finding not caught: {rule}' for rule in expected if got.get(rule, 0) == 0]


def gate_baseline(report, baseline):
    problems = []
    for rule, n in sorted(counts(report).items()):
        allowed = baseline.get(rule, 0)
        if n > allowed:
            problems.append(f'{rule}: {n} found, {allowed} allowed')
    fails = [rule for sev, rule in findings(report) if sev == 'FAIL']
    problems += [f'{rule}: FAIL findings are never allowed' for rule in sorted(set(fails)) if rule not in {p.split(':')[0] for p in problems}]
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('report', help='JSON written by render.py --format json')
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--expect', metavar='FILE', help='JSON list of rules that must be caught (demo with intentional defects)')
    g.add_argument('--baseline', metavar='FILE', help='JSON object rule -> max allowed count (clean example)')
    a = ap.parse_args(argv)
    try:
        report = json.loads(pathlib.Path(a.report).read_text(encoding='utf-8'))
        spec = json.loads(pathlib.Path(a.expect or a.baseline).read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        print(f'e2e_gate: cannot read input: {exc}', file=sys.stderr)
        return 2
    problems = [f'accessibility check did not run ({rule}); install axe-core or fix the error' for rule in sorted(seen_rules(report) & NOT_RUN)]
    if a.expect:
        problems += gate_expect(report, spec['rules'] if isinstance(spec, dict) else spec)
        ok = 'all expected findings were caught'
    else:
        problems += gate_baseline(report, spec.get('allowed', spec) if isinstance(spec, dict) else {})
        ok = 'no findings beyond the baseline'
    if problems:
        print('e2e_gate: FAILED')
        for p in problems:
            print(f'  - {p}')
        return 1
    print(f'e2e_gate: ok, {ok}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
