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


def run(src, suffix='.tsx', css=None, grid=8, mood=None):
    with tempfile.TemporaryDirectory() as d:
        f = pathlib.Path(d) / ('x' + suffix)
        f.write_text(src, encoding='utf-8')
        texts = [src] + ([css] if css else [])
        return ut.audit(str(f), grid, ut.css_tokens(texts), ut.css_tokens(texts, r'\.dark'), mood)


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
        iss = rules(run('<div className="gap-[5px] m-[13px]" />'), 'grid')
        self.assertEqual([i[0] for i in iss], ['WARN', 'WARN'])

    def test_4px_finetune_is_info_with_default_grid(self):
        iss = rules(run('<div className="p-3" />'), 'grid')
        self.assertEqual([i[0] for i in iss], ['INFO'])

    def test_finetunes_are_aggregated(self):
        iss = rules(run('<div className="p-3 gap-3" /><div className="px-5" />'), 'grid')
        self.assertEqual(len(iss), 1)
        self.assertIn('3 spacing value(s)', iss[0][2])

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

    def test_translucent_backgrounds_are_composited(self):
        # indigo-300 on indigo-500/15 over slate-900 passes; white/10 over a gradient is unknown and skipped
        ok = '<div className="bg-slate-900"><a className="bg-indigo-500/15 text-indigo-300">x</a></div>'
        grad = '<div className="bg-gradient-to-r from-indigo-600"><div className="bg-white/10"><span className="text-indigo-100">x</span></div></div>'
        bad = '<div className="bg-white"><a className="bg-indigo-500/15 text-indigo-300">x</a></div>'
        self.assertEqual(rules(run(ok), 'wcag-aa'), [])
        self.assertEqual(rules(run(grad), 'wcag-aa'), [])
        self.assertTrue(rules(run(bad), 'wcag-aa'))

    def test_dark_pass_falls_back_to_base_background(self):
        src = '<div className="bg-slate-900"><span className="text-slate-900 dark:text-slate-700">x</span></div>'
        iss = rules(run(src), 'wcag-aa')
        self.assertTrue(any('dark:text-slate-700' in i[2] for i in iss))

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
        # padding >= outer radius: inner radius is a free choice
        self.assertEqual(rules(run('<div className="rounded-2xl p-6"><div className="rounded-lg" /></div>'), 'nested-radius'), [])

    def test_miller_ignores_overflow_menu(self):
        nav = '<nav>' + '<a>x</a>' * 6 + '<details><summary>More</summary>' + '<a>y</a>' * 4 + '</details></nav>'
        self.assertEqual(rules(run(nav, suffix='.html'), 'miller-7'), [])

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


class Character(unittest.TestCase):
    """Sterility checks: correct-but-grey, flat, boxed-in output."""

    def test_same_hue_fix_suggested(self):
        self.assertEqual(ut.tw_same_hue('pink-400', '#fce7f3', 4.5), 'pink-700')
        msg = rules(run('<div className="bg-pink-100"><span className="text-pink-400">x</span></div>'), 'wcag-aa')[0][2]
        self.assertIn('text-pink-700', msg)

    def test_white_text_gets_darker_background_of_same_hue(self):
        msg = rules(run('<span className="bg-sky-500 text-white">x</span>'), 'wcag-aa')[0][2]
        self.assertIn('fix -> bg-sky-700', msg)

    def test_scale_floors(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ut.main(['scale', '--ratio', 'perfect-fourth'])
        self.assertIn('--text-xs: 0.75rem', out.getvalue())
        self.assertIn('--text-sm: 0.875rem', out.getvalue())

    def test_small_primary_cta(self):
        self.assertTrue(rules(run('<button className="h-8 bg-indigo-600">Go</button>'), 'fitts-primary'))
        self.assertEqual(rules(run('<button className="h-11 bg-indigo-600">Go</button>'), 'fitts-primary'), [])
        self.assertEqual(rules(run('<button className="h-8 border">Filter</button>'), 'fitts-primary'), [])

    def test_frame_wrapper(self):
        frame = '<div className="rounded-3xl p-4 bg-slate-50 border"><div className="rounded-lg bg-white p-6">x</div></div>'
        card = '<div className="rounded-3xl p-6 bg-white shadow-sm"><h3>t</h3><p>x</p></div>'
        self.assertTrue(rules(run(frame), 'frame-wrapper'))
        self.assertEqual(rules(run(card), 'frame-wrapper'), [])

    def test_border_heavy(self):
        bordered = '<div className="rounded-2xl p-4 bg-white border">x</div>' * 5
        shadowed = '<div className="rounded-2xl p-4 bg-white shadow-sm">x</div>' * 5
        self.assertTrue(rules(run(bordered), 'border-heavy'))
        self.assertEqual(rules(run(shadowed), 'border-heavy'), [])

    def test_flat_hierarchy(self):
        flat = '<span className="text-base font-bold">x</span>' * 20
        varied = ('<h1 className="text-3xl font-bold">t</h1>' + '<p className="text-base">x</p>' * 10 +
                  '<span className="text-sm font-medium">l</span>' * 9)
        self.assertTrue(rules(run(flat), 'flat-hierarchy'))
        self.assertEqual(rules(run(varied), 'flat-hierarchy'), [])

    def test_grey_chart_ignores_skeletons(self):
        grey = ''.join(f'<div className="h-2 w-{w} bg-slate-{s}"></div>' for w, s in (('1/2', 600), ('1/3', 500), ('1/4', 400)))
        color = ''.join(f'<div className="h-2 w-{w} bg-{c}-500"></div>' for w, c in (('1/2', 'indigo'), ('1/3', 'emerald'), ('1/4', 'amber')))
        skeleton = '<div className="animate-pulse">' + grey + '</div>'
        self.assertTrue(rules(run(grey), 'grey-chart'))
        self.assertEqual(rules(run(color), 'grey-chart'), [])
        self.assertEqual(rules(run(skeleton), 'grey-chart'), [])

    def test_mood_hero_surface_and_color(self):
        sterile = '<section className="p-8 bg-white"><h1 className="text-slate-900">x</h1><a className="bg-violet-600 h-12">Go</a></section>'
        lively = '<section className="p-8 bg-gradient-to-br from-violet-500 to-amber-400"><h1>x</h1></section><p className="text-sky-700">y</p>'
        self.assertTrue(rules(run(sterile, mood='playful'), 'no-hero-surface'))
        self.assertTrue(rules(run(sterile, mood='playful'), 'low-color'))
        self.assertEqual(rules(run(lively, mood='playful'), 'no-hero-surface'), [])
        self.assertEqual(rules(run(lively, mood='playful'), 'low-color'), [])
        self.assertEqual(rules(run(sterile), 'no-hero-surface'), [])  # mood checks are opt-in


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


class MoodSpecific(unittest.TestCase):
    def test_dark_neutral_button_on_dark_page_is_not_primary(self):
        src = ('<body className="bg-zinc-950"><div><button className="h-8 bg-zinc-800">Copy</button>'
               '<button className="h-11 bg-indigo-600">Run</button></div></body>')
        iss = run(src)
        self.assertEqual(rules(iss, 'fitts-primary'), [])
        self.assertEqual(rules(iss, 'single-primary-cta'), [])

    def test_dark_neutral_button_on_light_page_still_counts(self):
        src = '<body className="bg-white"><div><button className="bg-slate-900">A</button><button className="bg-indigo-600">B</button></div></body>'
        self.assertTrue(rules(run(src), 'single-primary-cta'))

    def test_border_heavy_skipped_for_technical_and_editorial(self):
        cards = ''.join('<div className="rounded-lg border p-4 bg-zinc-900">x</div>' for _ in range(5))
        self.assertTrue(rules(run(cards), 'border-heavy'))
        self.assertEqual(rules(run(cards, mood='technical'), 'border-heavy'), [])
        self.assertEqual(rules(run(cards, mood='editorial'), 'border-heavy'), [])

    def test_editorial_headline_trapped_in_prose(self):
        src = '<main className="max-w-prose mx-auto"><h1 className="text-4xl font-serif">Big headline</h1></main>'
        self.assertTrue(rules(run(src, mood='editorial'), 'headline-measure'))
        ok = '<main className="max-w-4xl mx-auto"><h1 className="text-4xl font-serif">Big</h1><p className="max-w-prose">x</p></main>'
        self.assertEqual(rules(run(ok, mood='editorial'), 'headline-measure'), [])

    def test_editorial_width_funnel_and_leading(self):
        src = ('<div className="max-w-5xl mx-auto"></div><div className="max-w-3xl mx-auto"></div>'
               '<div className="max-w-prose mx-auto"><blockquote className="text-xl leading-tight font-serif">q</blockquote></div>')
        iss = run(src, mood='editorial')
        self.assertTrue(rules(iss, 'width-funnel'))
        self.assertTrue(rules(iss, 'editorial-leading'))

    def test_editorial_edge_alignment(self):
        bad = '<div className="max-w-4xl mx-auto"><h1 className="text-5xl">T</h1></div><div className="max-w-prose mx-auto"><p>x</p></div>'
        self.assertTrue(rules(run(bad, mood='editorial'), 'edge-align'))
        ok = '<div className="max-w-4xl mx-auto"><h1 className="text-5xl">T</h1><div className="max-w-prose"><p>x</p></div></div>'
        self.assertEqual(rules(run(ok, mood='editorial'), 'edge-align'), [])
        centered = '<div className="max-w-4xl mx-auto text-center"><h1 className="text-5xl">T</h1></div><div className="max-w-prose mx-auto"><p>x</p></div>'
        self.assertEqual(rules(run(centered, mood='editorial'), 'edge-align'), [])

    def test_technical_checks(self):
        src = ''.join('<div className="rounded-3xl p-4 shadow-xl">x</div>' for _ in range(3))
        iss = run(src, mood='technical')
        self.assertTrue(rules(iss, 'radius-too-soft'))
        self.assertTrue(rules(iss, 'no-mono'))
        self.assertTrue(rules(iss, 'shadow-heavy'))

    def test_gradient_stops_checked(self):
        bad = '<div className="bg-gradient-to-r from-yellow-300 to-pink-600"><p className="text-white">Hi</p></div>'
        msg = rules(run(bad), 'wcag-aa')
        self.assertTrue(msg and 'gradient stop from-yellow-300' in msg[0][2])
        ok = '<div className="bg-gradient-to-r from-violet-700 to-indigo-800"><p className="text-white">Hi</p></div>'
        self.assertEqual(rules(run(ok), 'wcag-aa'), [])
        solid = '<div className="bg-gradient-to-r from-yellow-300 to-pink-300"><div className="bg-slate-900"><p className="text-white">Hi</p></div></div>'
        self.assertEqual(rules(run(solid), 'wcag-aa'), [])

    def test_bold_dark_band_counts_as_hero_surface(self):
        band = '<section className="bg-slate-950 py-24"><h1 className="text-5xl text-white">X</h1></section>'
        self.assertEqual(rules(run(band, mood='bold'), 'no-hero-surface'), [])
        self.assertTrue(rules(run('<section className="bg-white py-24"><h1>X</h1></section>', mood='bold'), 'no-hero-surface'))
        card = '<div className="bg-slate-900 p-8"><h1>X</h1></div>'
        self.assertTrue(rules(run(card, mood='bold'), 'no-hero-surface'))

    def test_half_step_spacing_is_info(self):
        iss = run('<div className="px-3.5 gap-2.5">x</div>')
        self.assertEqual(rules(iss, 'grid')[0][0], 'INFO')
        self.assertEqual(rules(run('<div className="p-[5px]">x</div>'), 'grid')[0][0], 'WARN')

    def test_scale_leading_graduated(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ut.main(['scale', '--ratio', 'major-third'])
        self.assertIn('--text-xl: 1.5rem; --leading-xl: 2rem;', out.getvalue())  # 24px / 32px, not 28


if __name__ == '__main__':
    unittest.main()
