"""Tests for reasoned suppression (`uitools-ignore`) in scripts/uiignore.py and scripts/uitools.py."""
import contextlib
import importlib.util
import io
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


if __name__ == '__main__':
    unittest.main()
