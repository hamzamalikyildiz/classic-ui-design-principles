#!/usr/bin/env python3
"""Unit tests for İP-A8 static rules in scripts/uitools.py."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))

import uiignore
import uitools


def _audit_rules(txt, *, dark_tokens=None, mood=None, route_mode=False, suffix='.html'):
    issues = uitools.audit(
        f'test_sample{suffix}',
        4,
        {},
        dark_tokens=dark_tokens,
        mood=mood,
        txt=txt,
        route_mode=route_mode,
    )
    return [(sev, rule, msg) for sev, rule, msg in issues]


class StaticRulesA8Test(unittest.TestCase):
    def test_known_rules_contains_all_a8_rules(self):
        expected = {
            'tr-uppercase',
            'numeric-columns',
            'heading-wrap',
            'theme-toggle-missing',
            'hardcoded-locale-format',
            'shadcn-defaults',
            'branch-explosion',
        }
        self.assertTrue(expected.issubset(uiignore.KNOWN_RULES))

    # 1. tr-uppercase
    def test_tr_uppercase_positive(self):
        html = '<html><body><h1 class="uppercase text-balance">İstanbul Şehirleri</h1></body></html>'
        issues = _audit_rules(html)
        self.assertIn(('WARN', 'tr-uppercase'), [(s, r) for s, r, _ in issues])

    def test_tr_uppercase_negative_with_lang_tr_and_english(self):
        html_tr = '<html lang="tr"><body><h1 class="uppercase text-balance">İstanbul Şehirleri</h1></body></html>'
        issues_tr = _audit_rules(html_tr)
        self.assertNotIn('tr-uppercase', [r for _, r, _ in issues_tr])

        html_en = '<html lang="en"><body><h1 class="uppercase text-balance">Hello World</h1></body></html>'
        issues_en = _audit_rules(html_en)
        self.assertNotIn('tr-uppercase', [r for _, r, _ in issues_en])

    # 2. numeric-columns
    def test_numeric_columns_positive(self):
        html = '<table><tr><td>123.45</td><td>678.90</td></tr></table>'
        issues = _audit_rules(html)
        self.assertIn(('INFO', 'numeric-columns'), [(s, r) for s, r, _ in issues])

    def test_numeric_columns_negative(self):
        html = '<table class="tabular-nums"><tr><td>123.45</td><td>678.90</td></tr></table>'
        issues = _audit_rules(html)
        self.assertNotIn('numeric-columns', [r for _, r, _ in issues])

    # 3. heading-wrap
    def test_heading_wrap_positive(self):
        html = '<div><h1>Main Title</h1><h2>Sub Title</h2></div>'
        issues = _audit_rules(html)
        hw = [(s, r) for s, r, _ in issues if r == 'heading-wrap']
        self.assertEqual(hw, [('INFO', 'heading-wrap')])

    def test_heading_wrap_negative(self):
        html = '<div><h1 class="text-balance">Main Title</h1><p class="text-pretty">Short paragraph.</p></div>'
        issues = _audit_rules(html)
        self.assertNotIn('heading-wrap', [r for _, r, _ in issues])

    # 4. theme-toggle-missing
    def test_theme_toggle_missing_positive_single_and_route(self):
        html = '<div class="dark:bg-slate-900 text-slate-900">Content</div>'
        issues_single = _audit_rules(html, route_mode=False)
        self.assertIn(('INFO', 'theme-toggle-missing'), [(s, r) for s, r, _ in issues_single])

        issues_route = _audit_rules(html, route_mode=True)
        self.assertIn(('WARN', 'theme-toggle-missing'), [(s, r) for s, r, _ in issues_route])

    def test_theme_toggle_missing_negative(self):
        html_with_toggle = '<div class="dark:bg-slate-900"><ThemeToggle /></div>'
        self.assertNotIn('theme-toggle-missing', [r for _, r, _ in _audit_rules(html_with_toggle)])

        html_no_dark = '<div class="bg-white text-slate-900">Light only</div>'
        self.assertNotIn('theme-toggle-missing', [r for _, r, _ in _audit_rules(html_no_dark)])

    # 5. hardcoded-locale-format
    def test_hardcoded_locale_format_positive(self):
        tsx = 'export function Price({ v }: { v: number }) { return <span>${v.toFixed(2)}</span>; }'
        issues = _audit_rules(tsx, suffix='.tsx')
        self.assertIn(('INFO', 'hardcoded-locale-format'), [(s, r) for s, r, _ in issues])

        tsx_date = 'const d = `${dt.getDate()}/${dt.getMonth() + 1}`;'
        issues_date = _audit_rules(tsx_date, suffix='.tsx')
        self.assertIn(('INFO', 'hardcoded-locale-format'), [(s, r) for s, r, _ in issues_date])

    def test_hardcoded_locale_format_negative(self):
        tsx = 'const fmt = new Intl.NumberFormat("tr-TR", { style: "currency", currency: "TRY" }).format(v);'
        issues = _audit_rules(tsx, suffix='.tsx')
        self.assertNotIn('hardcoded-locale-format', [r for _, r, _ in issues])

    # 6. shadcn-defaults
    def test_shadcn_defaults_positive(self):
        tsx = '''
        const buttonVariants = cva("inline-flex items-center", {
          variants: { size: { default: "h-8 px-4", sm: "h-8 px-3" } }
        });
        const badgeVariants = cva("inline-flex", {
          variants: { variant: { default: "text-[10px] px-2" } }
        });
        export function Demo() {
          return <Card className="border bg-white">Hi</Card>;
        }
        '''
        issues = _audit_rules(tsx, mood='trust', suffix='.tsx')
        self.assertIn(('INFO', 'shadcn-defaults'), [(s, r) for s, r, _ in issues])

    def test_shadcn_defaults_negative(self):
        tsx = '''
        const buttonVariants = cva("inline-flex items-center", {
          variants: { size: { default: "h-10 px-4", sm: "h-9 px-3" } }
        });
        export function Demo() {
          return <Card className="border shadow-sm bg-white">Hi</Card>;
        }
        '''
        issues = _audit_rules(tsx, mood='trust', suffix='.tsx')
        self.assertNotIn('shadcn-defaults', [r for _, r, _ in issues])


if __name__ == '__main__':
    unittest.main()
