"""Tests for reasoned suppression (`uitools-ignore`) in scripts/uiignore.py and scripts/uitools.py."""
import contextlib
import importlib.util
import io
import os
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent

spec = importlib.util.spec_from_file_location('uitools', ROOT / 'scripts' / 'uitools.py')
ut = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ut)

import uiignore


def _audit_text(code, suffix='.tsx', mood=None):
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td) / f'Sample{suffix}'
        p.write_text(code, encoding='utf-8')
        return ut.audit(str(p), 8, {}, None, mood, txt=code)


class IgnoreTests(unittest.TestCase):
    def test_inline_jsx_and_next_line_js_suppress_with_reason(self):
        code = (
            "export function Card() {\n"
            "  return (\n"
            "    <main className=\"bg-slate-100\">\n"
            "      <p className=\"text-slate-300\">Muted</p> {/* uitools-ignore: wcag-aa — decorative watermark text */}\n"
            "      // uitools-ignore-next-line: grid — legacy 13px badge padding\n"
            "      <span className=\"p-[13px]\">Tag</span>\n"
            "    </main>\n"
            "  );\n"
            "}\n"
        )
        issues = _audit_text(code)
        rules = [r for _, r, _ in issues]
        self.assertNotIn('wcag-aa', rules)
        self.assertNotIn('grid', rules)
        self.assertNotIn('ignore-without-reason', rules)

    def test_html_comment_next_line_suppresses(self):
        code = (
            "<main>\n"
            "  <!-- uitools-ignore-next-line: grid — legacy widget spacing -->\n"
            "  <div class=\"p-[13px]\">Hello</div>\n"
            "</main>\n"
        )
        issues = _audit_text(code, suffix='.html')
        rules = [r for _, r, _ in issues]
        self.assertNotIn('grid', rules)

    def test_block_start_end_suppresses_only_inside(self):
        code = (
            "export function List() {\n"
            "  return (\n"
            "    <main className=\"bg-white\">\n"
            "      {/* uitools-ignore-start: grid — third-party chart container */}\n"
            "      <div className=\"p-[13px]\">Inside</div>\n"
            "      {/* uitools-ignore-end */}\n"
            "      <div className=\"p-[15px]\">Outside</div>\n"
            "    </main>\n"
            "  );\n"
            "}\n"
        )
        issues = _audit_text(code)
        grid_msgs = [m for _, r, m in issues if r == 'grid']
        self.assertEqual(len(grid_msgs), 1)
        self.assertIn('L7', grid_msgs[0])

    def test_file_ignore_suppresses_file_level_rule(self):
        code = (
            "// uitools-ignore-file: no-hero-surface — internal settings panel without hero\n"
            "export function Settings() {\n"
            "  return <main className=\"bg-white p-4\"><p className=\"text-slate-900 max-w-prose\">Settings</p></main>;\n"
            "}\n"
        )
        issues = _audit_text(code, mood='trust')
        rules = [r for _, r, _ in issues]
        self.assertNotIn('no-hero-surface', rules)

    def test_missing_or_short_reason_does_not_suppress_and_warns(self):
        code = (
            "<main className=\"bg-slate-100\">\n"
            "  <p className=\"text-slate-300\">One</p> {/* uitools-ignore: wcag-aa */}\n"
            "  // uitools-ignore-next-line: grid — short\n"
            "  <span className=\"p-[13px]\">Two</span>\n"
            "</main>\n"
        )
        issues = _audit_text(code)
        rules = [r for _, r, _ in issues]
        self.assertIn('wcag-aa', rules)
        self.assertIn('grid', rules)
        warns = [m for s, r, m in issues if s == 'WARN' and r == 'ignore-without-reason']
        self.assertEqual(len(warns), 2)

    def test_unknown_rule_emits_info(self):
        code = (
            "<main>\n"
            "  {/* uitools-ignore: made-up-rule — valid justification text */}\n"
            "  <div>Ok</div>\n"
            "</main>\n"
        )
        issues = _audit_text(code)
        infos = [(s, r, m) for s, r, m in issues if r == 'unknown-rule-in-ignore']
        self.assertEqual(len(infos), 1)
        self.assertEqual(infos[0][0], 'INFO')
        self.assertIn('made-up-rule', infos[0][2])

    def test_wildcard_suppresses_matching_line(self):
        code = (
            "<main>\n"
            "  <div className=\"p-[13px]\">Wildcard</div> {/* uitools-ignore: * — legacy migrated markup */}\n"
            "</main>\n"
        )
        issues = _audit_text(code)
        self.assertNotIn('grid', [r for _, r, _ in issues])

    def test_cli_show_suppressed_and_summary(self):
        with tempfile.TemporaryDirectory() as td:
            p = pathlib.Path(td) / 'Comp.tsx'
            p.write_text(
                "<main className=\"bg-slate-100\">\n"
                "  <p className=\"text-slate-300\">Muted</p> {/* uitools-ignore: wcag-aa — decorative watermark text */}\n"
                "</main>\n",
                encoding='utf-8',
            )
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                with self.assertRaises(SystemExit) as cm:
                    ut.main(['audit', str(p), '--show-suppressed'])
            self.assertEqual(cm.exception.code, 0)
            out = buf.getvalue()
            self.assertIn('[SUPPRESSED]', out)
            self.assertIn('wcag-aa', out)
            self.assertIn('decorative watermark text', out)
            self.assertIn('SUPPRESSED=1', out)

            # Without ignore comments, SUMMARY must NOT include SUPPRESSED=
            p2 = pathlib.Path(td) / 'Clean.tsx'
            p2.write_text("<main><p>Clean</p></main>\n", encoding='utf-8')
            buf2 = io.StringIO()
            with contextlib.redirect_stdout(buf2):
                with self.assertRaises(SystemExit) as cm2:
                    ut.main(['audit', str(p2)])
            self.assertEqual(cm2.exception.code, 0)
            self.assertNotIn('SUPPRESSED=', buf2.getvalue())

    def test_route_child_component_inline_and_next_line_ignores(self):
        """Child component uitools-ignore directives work in --route mode even when page.tsx has no ignores."""
        import uiroute as ur

        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            comp_dir = root / 'components'
            app_dir = root / 'app' / 'dashboard'
            comp_dir.mkdir(parents=True)
            app_dir.mkdir(parents=True)

            # Pad lines so the ignored elements sit at L13/L15 inside ScoreBars.tsx
            score_bars = comp_dir / 'ScoreBars.tsx'
            score_bars.write_text(
                'import React from "react";\n'
                '// L2\n'
                '// L3\n'
                '// L4\n'
                '// L5\n'
                '// L6\n'
                '// L7\n'
                '// L8\n'
                '// L9\n'
                'export function ScoreBars() {\n'
                '  return (\n'
                '    <div className="space-y-2">\n'
                '      <span className="text-slate-800">92%</span> {/* uitools-ignore: wcag-aa — brand score bar */}\n'
                '      // uitools-ignore-next-line: grid — custom bar track offset\n'
                '      <div className="p-[13px]">Track</div>\n'
                '    </div>\n'
                '  );\n'
                '}\n',
                encoding='utf-8',
            )
            page = app_dir / 'page.tsx'
            page.write_text(
                'import { ScoreBars } from "@/components/ScoreBars";\n'
                'export default function DashboardPage() {\n'
                '  return (\n'
                '    <main className="bg-slate-900 p-8 text-white">\n'
                '      <ScoreBars />\n'
                '    </main>\n'
                '  );\n'
                '}\n',
                encoding='utf-8',
            )

            composed = ur.compose_route(page, root_dir=root)
            self.assertIsInstance(composed.raw_txt, ur.RouteSourceText)
            self.assertIn(os.path.normcase(str(score_bars.resolve())),
                          {os.path.normcase(str(pathlib.Path(k).resolve())) for k in composed.raw_txt.source_files})

            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                with self.assertRaises(SystemExit) as cm:
                    ut.main(['audit', '--route', str(page), '--root', str(root), '--show-suppressed'])
            self.assertEqual(cm.exception.code, 0, buf.getvalue())
            out = buf.getvalue()
            self.assertIn('SUMMARY FAIL=0 WARN=0', out)
            self.assertIn('SUPPRESSED=2', out)
            self.assertIn('brand score bar', out)
            self.assertIn('custom bar track offset', out)

    def test_route_cross_file_line_collision_avoidance(self):
        """An ignore on line N of page.tsx must NOT suppress an un-ignored defect on line N of ScoreBars.tsx (and vice versa)."""
        import uiroute as ur

        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            comp_dir = root / 'components'
            app_dir = root / 'app'
            comp_dir.mkdir(parents=True)
            app_dir.mkdir(parents=True)

            # Both page.tsx and ScoreBars.tsx have a wcag-aa violation on L6!
            # Case A: page.tsx ignores its own L6 watermark, ScoreBars.tsx L6 is NOT ignored.
            (comp_dir / 'ScoreBars.tsx').write_text(
                'import React from "react";\n'
                '// L2\n'
                'export function ScoreBars() {\n'
                '  return (\n'
                '    <div className="mt-2">\n'
                '      <span className="text-slate-800">Unreadable child</span>\n'
                '    </div>\n'
                '  );\n'
                '}\n',
                encoding='utf-8',
            )
            page = app_dir / 'page.tsx'
            page.write_text(
                'import { ScoreBars } from "@/components/ScoreBars";\n'
                'export default function Page() {\n'
                '  return (\n'
                '    <main className="bg-slate-900 p-8">\n'
                '      <ScoreBars />\n'
                '      <p className="text-slate-700">Watermark</p> {/* uitools-ignore: wcag-aa — intentional page watermark */}\n'
                '    </main>\n'
                '  );\n'
                '}\n',
                encoding='utf-8',
            )

            composed_a = ur.compose_route(page, root_dir=root)
            iss_a, sup_a = ut.audit(str(page), 8, {}, txt=composed_a, route_mode=True, root_dir=root, return_suppressed=True)
            wcag_a = [m for _, r, m in iss_a if r == 'wcag-aa']
            self.assertEqual(len(wcag_a), 1, iss_a)
            self.assertIn('L6 text-slate-800 on bg-slate-900', wcag_a[0])
            self.assertEqual(len(sup_a), 1)
            self.assertIn('text-slate-700', sup_a[0][2])

            # Case B: ScoreBars.tsx ignores its own L6 bar, page.tsx L6 is NOT ignored.
            (comp_dir / 'ScoreBars.tsx').write_text(
                'import React from "react";\n'
                '// L2\n'
                'export function ScoreBars() {\n'
                '  return (\n'
                '    <div className="mt-2">\n'
                '      <span className="text-slate-800">Ignored child</span> {/* uitools-ignore: wcag-aa — brand score bar */}\n'
                '    </div>\n'
                '  );\n'
                '}\n',
                encoding='utf-8',
            )
            page.write_text(
                'import { ScoreBars } from "@/components/ScoreBars";\n'
                'export default function Page() {\n'
                '  return (\n'
                '    <main className="bg-slate-900 p-8">\n'
                '      <ScoreBars />\n'
                '      <p className="text-slate-700">Unignored page text</p>\n'
                '    </main>\n'
                '  );\n'
                '}\n',
                encoding='utf-8',
            )

            composed_b = ur.compose_route(page, root_dir=root)
            iss_b, sup_b = ut.audit(str(page), 8, {}, txt=composed_b, route_mode=True, root_dir=root, return_suppressed=True)
            wcag_b = [m for _, r, m in iss_b if r == 'wcag-aa']
            self.assertEqual(len(wcag_b), 1, iss_b)
            self.assertIn('L6 text-slate-700 on bg-slate-900', wcag_b[0])
            self.assertEqual(len(sup_b), 1)
            self.assertIn('text-slate-800', sup_b[0][2])

    def test_route_child_component_range_file_and_prefixed_meta_issues(self):
        """Child range/file ignores scope properly and child meta_issues carry component basename prefix."""
        import uiroute as ur

        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            comp_dir = root / 'components'
            app_dir = root / 'app'
            comp_dir.mkdir(parents=True)
            app_dir.mkdir(parents=True)

            (comp_dir / 'LegacyWidget.tsx').write_text(
                '// uitools-ignore-file: wcag-aa — legacy contrast tokens in widget\n'
                'export function LegacyWidget() {\n'
                '  return (\n'
                '    <div>\n'
                '      {/* uitools-ignore-start: grid — legacy chart pixel offsets */}\n'
                '      <div className="p-[13px] text-slate-800">Legacy</div>\n'
                '      {/* uitools-ignore-end */}\n'
                '      {/* uitools-ignore: bogus-rule — valid justification text */}\n'
                '      {/* uitools-ignore: grid — bad */}\n'
                '    </div>\n'
                '  );\n'
                '}\n',
                encoding='utf-8',
            )
            page = app_dir / 'page.tsx'
            page.write_text(
                'import { LegacyWidget } from "@/components/LegacyWidget";\n'
                'export default function Page() {\n'
                '  return (\n'
                '    <main className="bg-slate-900 p-8">\n'
                '      {/* uitools-ignore: grid — tiny */}\n'
                '      <LegacyWidget />\n'
                '      <p className="text-slate-700">Page contrast bug</p>\n'
                '    </main>\n'
                '  );\n'
                '}\n',
                encoding='utf-8',
            )

            composed = ur.compose_route(page, root_dir=root)
            iss, sup = ut.audit(str(page), 8, {}, txt=composed, route_mode=True, root_dir=root, return_suppressed=True)

            # Child file-level wcag-aa ignore suppresses LegacyWidget's text-slate-800, NOT page.tsx's text-slate-700!
            wcag = [m for _, r, m in iss if r == 'wcag-aa']
            self.assertEqual(len(wcag), 1, iss)
            self.assertIn('text-slate-700', wcag[0])
            self.assertTrue(any(r == 'wcag-aa' and 'text-slate-800' in m for _, r, m, _ in sup), sup)
            self.assertTrue(any(r == 'grid' and 'p-[13px]' in m for _, r, m, _ in sup), sup)

            # Meta issues from LegacyWidget.tsx are prefixed with "LegacyWidget.tsx: ", while page.tsx has no prefix
            unknown_meta = [m for _, r, m in iss if r == 'unknown-rule-in-ignore']
            self.assertEqual(len(unknown_meta), 1, iss)
            self.assertTrue(unknown_meta[0].startswith('LegacyWidget.tsx: L8 '), unknown_meta)

            no_reason_meta = [m for _, r, m in iss if r == 'ignore-without-reason']
            self.assertEqual(len(no_reason_meta), 2, iss)
            self.assertTrue(any(m.startswith('LegacyWidget.tsx: L9 ') for m in no_reason_meta), no_reason_meta)
            self.assertTrue(any(m.startswith('L5 ') for m in no_reason_meta), no_reason_meta)


if __name__ == '__main__':
    unittest.main()
