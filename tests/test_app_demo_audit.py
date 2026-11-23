"""Static integration tests (S2 acceptance) for examples/app-demo using Python stdlib + scripts/uitools.py.

No Node/npm required — runs on every OS and CI.
Run: python -m unittest tests/test_app_demo_audit.py -v
"""
import contextlib
import importlib.util
import io
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / 'scripts'
APP_DEMO = ROOT / 'examples' / 'app-demo'
CSS_PATH = APP_DEMO / 'src' / 'index.css'

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import render  # noqa: E402

_spec = importlib.util.spec_from_file_location('uitools', SCRIPTS / 'uitools.py')
ut = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ut)


def _run_audit(args):
    """Run `uitools.py audit` in-process and return (exit_code, stdout_text)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            ut.main(['audit', *args])
            code = 0
        except SystemExit as exc:
            code = int(exc.code) if exc.code is not None else 0
    return code, buf.getvalue()


def _route_args(page_rel):
    return [
        '--route',
        str(APP_DEMO / 'src' / 'pages' / page_rel),
        '--root',
        str(APP_DEMO),
        '--css',
        str(CSS_PATH),
        '--mood',
        'trust',
    ]


class AppDemoStaticAuditTests(unittest.TestCase):
    def test_01_clean_pages_have_zero_fail_and_zero_warn(self):
        """LoginPage, CvListPage, and SettingsPage pass with FAIL=0 and WARN=0."""
        for page in ('LoginPage.tsx', 'CvListPage.tsx', 'SettingsPage.tsx'):
            with self.subTest(page=page):
                code, out = _run_audit(_route_args(page))
                self.assertEqual(code, 0, out)
                self.assertIn('SUMMARY FAIL=0 WARN=0', out, out)

        _, cv_list_out = _run_audit(_route_args('CvListPage.tsx'))
        self.assertIn('src/components/FilterChip.tsx', cv_list_out)
        self.assertNotIn('[FAIL] wcag-aa', cv_list_out)
        self.assertNotIn('[WARN] wcag-aa', cv_list_out)

    def test_02_cv_detail_catches_all_static_defects(self):
        """CvDetailPage catches Defect #1 (wcag-aa), Defect #2 (single-primary-cta), and Defect #4 (tr-uppercase)."""
        code, out = _run_audit(_route_args('CvDetailPage.tsx'))
        self.assertEqual(code, 1, out)
        self.assertIn('SUMMARY FAIL=1 WARN=2', out, out)
        # Defect #1: bg-slate-100 text-slate-300 -> FAIL wcag-aa
        self.assertIn('[FAIL] wcag-aa:', out)
        self.assertIn('text-slate-300 on bg-slate-100', out)
        # Defect #2: two solid primary buttons in one block -> WARN single-primary-cta
        self.assertIn('[WARN] single-primary-cta:', out)
        self.assertIn('2 solid buttons in one block', out)
        # Defect #4: Turkish uppercase without lang="tr" -> WARN tr-uppercase
        self.assertIn('[WARN] tr-uppercase:', out)

    def test_03_false_alarm_traps_produce_zero_false_positives(self):
        """ScoreCard+ScoreBars (text-white/80), FilterChip (cn ternary), and ActionBar (ternary Button) have 0 false positives."""
        _, out = _run_audit(_route_args('CvDetailPage.tsx'))
        for comp in ('ScoreCard.tsx', 'ScoreBars.tsx', 'FilterChip.tsx', 'ActionBar.tsx'):
            self.assertIn(comp, out)

        wcag_lines = [ln for ln in out.splitlines() if 'wcag-aa:' in ln]
        self.assertEqual(len(wcag_lines), 1, wcag_lines)
        self.assertIn('text-slate-300 on bg-slate-100', wcag_lines[0])
        self.assertNotIn('text-white/80', wcag_lines[0])

        cta_lines = [ln for ln in out.splitlines() if 'single-primary-cta:' in ln]
        self.assertEqual(len(cta_lines), 1, cta_lines)

    def test_04_sidebar_file_mode_no_hero_surface_is_info_not_warn(self):
        """Sidebar.tsx in component file mode emits INFO no-hero-surface, never WARN."""
        code, out = _run_audit([
            str(APP_DEMO / 'src' / 'components' / 'Sidebar.tsx'),
            '--css',
            str(CSS_PATH),
            '--mood',
            'trust',
        ])
        self.assertEqual(code, 0, out)
        self.assertIn('SUMMARY FAIL=0 WARN=0', out, out)
        self.assertIn('[INFO] no-hero-surface:', out)
        self.assertNotIn('[WARN] no-hero-surface:', out)

    def test_05_badge_file_mode_catches_shadcn_defaults_info(self):
        """Defect #3: src/components/ui/badge.tsx (text-[10px]) emits INFO shadcn-defaults."""
        code, out = _run_audit([
            str(APP_DEMO / 'src' / 'components' / 'ui' / 'badge.tsx'),
            '--css',
            str(CSS_PATH),
            '--mood',
            'trust',
        ])
        self.assertEqual(code, 0, out)
        self.assertIn('SUMMARY FAIL=0 WARN=0', out, out)
        self.assertIn('[INFO] shadcn-defaults:', out)
        self.assertIn('text-[10px]', out)

    def test_06_seed_json_schema_and_expected_records(self):
        """examples/app-demo/seed.json has 4 applications, 6 recommendations, 3 questions, and 64->69->73 history."""
        seed = json.loads((APP_DEMO / 'seed.json').read_text(encoding='utf-8'))
        apps = seed.get('applications')
        self.assertIsInstance(apps, list)
        self.assertEqual(len(apps), 4)

        app01 = apps[0]
        self.assertEqual(app01['id'], 'app_01')
        self.assertEqual(len(app01['recommendations']), 6)
        self.assertEqual(len(app01['interviewQuestions']), 3)
        self.assertEqual([h['score'] for h in app01['scoreHistory']], [64, 69, 73])

    def test_07_routes_json_validates_with_render_schema(self):
        """examples/app-demo/routes.json passes render.validate_routes_config with 4 routes."""
        cfg = json.loads((APP_DEMO / 'routes.json').read_text(encoding='utf-8'))
        render.validate_routes_config(cfg)
        self.assertEqual(
            [r['name'] for r in cfg['routes']],
            ['login', 'cv-list', 'cv-detail', 'settings'],
        )


if __name__ == '__main__':
    unittest.main()
