"""Regression tests for scripts/uitools.py. Run: python3 -m unittest discover -s tests"""
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

SHADCN_CSS = """
:root { --background: 0 0% 100%; --foreground: 222.2 84% 4.9%; --primary: 222.2 47.4% 11.2%;
        --muted-foreground: 215.4 16.3% 46.9%; }
.dark { --background: 222.2 84% 4.9%; --foreground: 210 40% 98%; --muted-foreground: 215 20% 25%; }
"""


def run(src, suffix='.tsx', css=None, grid=8):
    with tempfile.TemporaryDirectory() as d:
        f = pathlib.Path(d) / ('x' + suffix)
        f.write_text(src, encoding='utf-8')
        texts = [src] + ([css] if css else [])
        return ut.audit(str(f), grid, ut.css_tokens(texts), ut.css_tokens(texts, r'\.dark'))


def rules(issues, rule):
    return [i for i in issues if i[1] == rule]


class Color(unittest.TestCase):
    def test_wcag_reference_ratios(self):
        self.assertAlmostEqual(ut.ratio('#000000', '#ffffff'), 21.0, places=2)
        self.assertAlmostEqual(ut.ratio('#777777', '#ffffff'), 4.48, places=2)

    def test_fix_color_reaches_target(self):
        fixed = ut.fix_color('#9ca3af', '#ffffff', 4.5)
        self.assertGreaterEqual(ut.ratio(fixed, '#ffffff'), 4.5)

    def test_tailwind_and_token_resolution(self):
        self.assertEqual(ut.tw_hex('slate-400', {}), '#94a3b8')
        self.assertEqual(ut.tw_hex('white/50', {}), '#ffffff')
        self.assertEqual(ut.tw_hex('[#abc]', {}), '#abc')
        self.assertEqual(ut.tw_hex('primary', ut.css_tokens([SHADCN_CSS])), ut.hsl2hex(222.2, 47.4, 11.2))
        self.assertIsNone(ut.tw_hex('brand', {}))

    def test_dark_tokens_parsed_separately(self):
        light, dark = ut.css_tokens([SHADCN_CSS]), ut.css_tokens([SHADCN_CSS], r'\.dark')
        self.assertNotEqual(light['background'], dark['background'])


class Spacing(unittest.TestCase):
    def test_off_4px_is_warn(self):
        iss = rules(run('<div className="gap-1.5 m-[10px]" />'), 'grid')
        self.assertEqual([i[0] for i in iss], ['WARN', 'WARN'])

    def test_4px_finetune_is_info_with_default_grid(self):
        iss = rules(run('<div className="p-3" />'), 'grid')
        self.assertEqual([i[0] for i in iss], ['INFO'])

    def test_8px_values_pass(self):
        self.assertEqual(rules(run('<div className="p-4 gap-6 m-[16px]" />'), 'grid'), [])

    def test_css_spacing(self):
        iss = rules(run('.a{padding:13px 16px}', suffix='.css'), 'grid')
        self.assertEqual(len(iss), 1)
        self.assertIn('13', iss[0][2])


class Contrast(unittest.TestCase):
    def test_tailwind_pair_on_page_background(self):
        iss = rules(run('<p className="text-slate-400">x</p>'), 'wcag-aa')
        self.assertEqual(iss[0][0], 'FAIL')

    def test_background_inherited_from_ancestor(self):
        iss = rules(run('<div className="bg-slate-900"><span className="text-slate-600">x</span></div>'), 'wcag-aa')
        self.assertIn('bg-slate-900', iss[0][2])

    def test_bg_utility_does_not_hide_color(self):
        iss = rules(run('<div className="bg-white bg-cover bg-no-repeat"><span className="text-slate-300">x</span></div>'), 'wcag-aa')
        self.assertEqual(len(iss), 1)
        self.assertIn('bg-white', iss[0][2])

    def test_transparent_passes_through(self):
        src = '<div className="bg-slate-900"><div className="bg-transparent"><span className="text-slate-600">x</span></div></div>'
        self.assertIn('bg-slate-900', rules(run(src), 'wcag-aa')[0][2])

    def test_unknown_backdrop_is_skipped(self):
        src = ('<div className="bg-slate-900"><div className="bg-gradient-to-r"><span className="text-slate-600">a</span></div>'
               '<div className="bg-brand"><span className="text-slate-600">b</span></div></div>')
        self.assertEqual(rules(run(src), 'wcag-aa'), [])

    def test_large_text_uses_3_to_1(self):
        # #949494 on white = 3.03:1: passes as large text, fails as body text
        self.assertEqual(rules(run('<h1 className="text-3xl text-[#949494]">x</h1>'), 'wcag-aa'), [])
        self.assertTrue(rules(run('<p className="text-[#949494]">x</p>'), 'wcag-aa'))

    def test_dark_variant_pairs(self):
        iss = rules(run('<div className="dark:bg-white"><span className="dark:text-slate-300">x</span></div>'), 'wcag-aa')
        self.assertIn('dark:text-slate-300', iss[0][2])

    def test_shadcn_dark_theme_tokens(self):
        iss = rules(run('<p className="text-muted-foreground">x</p>', css=SHADCN_CSS), 'wcag-aa')
        self.assertEqual(len(iss), 1)
        self.assertTrue(iss[0][2].startswith('L1 [.dark]'))

    def test_css_rule_contrast(self):
        self.assertTrue(rules(run('.c{color:#9ca3af;background:#ffffff}', suffix='.css'), 'wcag-aa'))


class Structure(unittest.TestCase):
    def test_single_primary_cta_counts_shadcn_and_bg_primary(self):
        src = ('<section><Button>Save</Button><Button variant="outline">Cancel</Button>'
               '<button className="bg-primary">Go</button></section>')
        iss = rules(run(src), 'single-primary-cta')
        self.assertEqual(len(iss), 1)
        self.assertIn('2 solid', iss[0][2])

    def test_separate_cards_are_separate_blocks(self):
        self.assertEqual(rules(run('<Card><Button>A</Button></Card><Card><Button>B</Button></Card>'), 'single-primary-cta'), [])

    def test_jsx_arrow_in_attrs_does_not_break_parser(self):
        src = '<section><button className="bg-indigo-600" onClick={() => go(1 > 0)}>A</button><button className="bg-indigo-600">B</button></section>'
        self.assertEqual(len(rules(run(src), 'single-primary-cta')), 1)

    def test_line_length_per_paragraph(self):
        long = 'x ' * 50
        self.assertTrue(rules(run(f'<main className="max-w-7xl"><p>{long}</p></main>'), 'line-length'))
        self.assertEqual(rules(run(f'<article className="max-w-prose"><p>{long}</p></article>'), 'line-length'), [])
        self.assertEqual(rules(run('<main className="max-w-7xl"><p>short</p></main>'), 'line-length'), [])

    def test_nested_radius(self):
        self.assertTrue(rules(run('<div className="rounded-3xl p-2"><img className="rounded-3xl" /></div>'), 'nested-radius'))
        self.assertEqual(rules(run('<div className="rounded-3xl p-2"><img className="rounded-2xl" /></div>'), 'nested-radius'), [])

    def test_miller_nav(self):
        nav = '<nav>' + '<a>x</a>' * 8 + '</nav>'
        self.assertTrue(rules(run(nav, suffix='.html'), 'miller-7'))
        self.assertEqual(rules(run('<nav>' + '<a>x</a>' * 7 + '</nav>', suffix='.html'), 'miller-7'), [])

    def test_font_limit(self):
        src = ('<link href="https://fonts.googleapis.com/css2?family=Inter&family=Poppins">'
               '<style>h1{font-family:"Playfair Display",serif}</style>')
        self.assertEqual(rules(run(src, suffix='.html'), 'max-2-fonts')[0][0], 'FAIL')

    def test_skeleton_hint(self):
        self.assertTrue(rules(run('{items.map(i => <li>{i}</li>)}'), 'skeleton-empty'))
        self.assertEqual(rules(run('{loading ? <Skeleton /> : items.map(i => <li>{i}</li>)}'), 'skeleton-empty'), [])


class Cli(unittest.TestCase):
    def test_exit_code_on_fail(self):
        with tempfile.TemporaryDirectory() as d:
            f = pathlib.Path(d) / 'a.tsx'
            f.write_text('<p className="text-slate-300">x</p>')
            with self.assertRaises(SystemExit) as cm, contextlib.redirect_stdout(io.StringIO()):
                ut.main(['audit', str(f)])
            self.assertEqual(cm.exception.code, 1)

    def test_missing_file_message(self):
        with self.assertRaises(SystemExit) as cm:
            ut.main(['audit', '/no/such/file.tsx'])
        self.assertIn('not found', str(cm.exception.code))


if __name__ == '__main__':
    unittest.main()
