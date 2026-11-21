"""Golden false-positive and control-group tests for real Next.js/React TSX fixtures.

Run: python -m unittest discover -s tests -v
"""
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('uitools', ROOT / 'scripts' / 'uitools.py')
ut = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ut)

FIXTURES = ROOT / 'tests' / 'fixtures' / 'real_app'


def audit_fixture(rel_path, grid=8, mood=None):
    path = FIXTURES / rel_path
    return ut.audit(str(path), grid, {}, None, mood)


def rules(issues, rule):
    return [i for i in issues if i[1] == rule]


class GoldenFalsePositives(unittest.TestCase):
    """Real-app false-positive cases; marked expectedFailure until Phase A lands."""

    @unittest.expectedFailure
    def test_scorecard_cross_component_contrast(self):
        """İP-A3: ScoreBars rendered inside ScoreCard's bg-slate-900 should not FAIL wcag-aa."""
        iss = rules(audit_fixture('ScoreCard.tsx'), 'wcag-aa')
        self.assertEqual([i for i in iss if i[0] in ('FAIL', 'WARN')], [])

    def test_chip_conditional_branch_no_cross_match(self):
        """İP-A4: cn() conditional branches must not cross-match bg from one branch with text from another."""
        iss = rules(audit_fixture('Chip.tsx'), 'wcag-aa')
        self.assertEqual([i for i in iss if i[0] in ('FAIL', 'WARN')], [])

    def test_actions_mutually_exclusive_ctas_no_warning(self):
        """İP-A4: Mutually exclusive ternary <Button> branches must not trigger single-primary-cta."""
        iss = rules(audit_fixture('Actions.tsx'), 'single-primary-cta')
        self.assertEqual([i for i in iss if i[0] in ('FAIL', 'WARN')], [])

    @unittest.expectedFailure
    def test_sidebar_component_no_hero_surface_not_warn(self):
        """İP-A6: Component file (components/Sidebar.tsx) should not emit WARN for no-hero-surface."""
        iss = rules(audit_fixture('components/Sidebar.tsx', mood='trust'), 'no-hero-surface')
        self.assertFalse(any(i[0] == 'WARN' for i in iss), f'unexpected WARN: {iss}')


class GoldenControlGroup(unittest.TestCase):
    """Control group: real defects that must continue to be reported before and after Phase A."""

    def test_bad_contrast_static_card_fails(self):
        """Control: bg-slate-100 with text-slate-300 in BadContrastCard must FAIL wcag-aa."""
        iss = rules(audit_fixture('BadContrast.tsx'), 'wcag-aa')
        self.assertTrue(any(i[0] == 'FAIL' and 'text-slate-300 on bg-slate-100' in i[2] for i in iss), iss)

    def test_bad_contrast_same_conditional_branch_fails(self):
        """Control: bg-slate-200 text-slate-400 in the same cn() branch must FAIL wcag-aa."""
        iss = rules(audit_fixture('BadContrast.tsx'), 'wcag-aa')
        self.assertTrue(any(i[0] == 'FAIL' and 'text-slate-400 on bg-slate-200' in i[2] for i in iss), iss)

    def test_two_buttons_simultaneous_ctas_warns(self):
        """Control: Two simultaneously visible solid <Button>s in one block must WARN single-primary-cta."""
        iss = rules(audit_fixture('TwoButtons.tsx'), 'single-primary-cta')
        self.assertTrue(any(i[0] == 'WARN' for i in iss), iss)

    def test_dashboard_page_no_hero_surface_warns(self):
        """Control: Full page route (app/dashboard/page.tsx) without hero surface must WARN no-hero-surface."""
        iss = rules(audit_fixture('app/dashboard/page.tsx', mood='trust'), 'no-hero-surface')
        self.assertTrue(any(i[0] == 'WARN' for i in iss), iss)

    def test_all_real_app_fixtures_exist_and_audit_cleanly(self):
        """Sanity: All expected golden fixture TSX files exist and audit() runs without error."""
        expected = [
            'ScoreCard.tsx',
            'Chip.tsx',
            'Actions.tsx',
            'components/Sidebar.tsx',
            'BadContrast.tsx',
            'TwoButtons.tsx',
            'app/dashboard/page.tsx',
        ]
        for rel in expected:
            p = FIXTURES / rel
            self.assertTrue(p.is_file(), f'missing fixture: {p}')
            res = audit_fixture(rel)
            self.assertIsInstance(res, list)

    def test_scorecard_outer_text_is_not_flagged(self):
        """Control: ScoreCard's own text-slate-300 inside bg-slate-900 passes contrast without false alarm."""
        iss = rules(audit_fixture('ScoreCard.tsx'), 'wcag-aa')
        self.assertFalse(any('text-slate-300' in i[2] for i in iss), iss)
