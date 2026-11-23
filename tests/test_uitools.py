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


def run(src, suffix='.tsx', css=None, grid=8, mood=None, strict=True):
    with tempfile.TemporaryDirectory() as d:
        f = pathlib.Path(d) / ('x' + suffix)
        f.write_text(src, encoding='utf-8')
        texts = [src] + ([css] if css else [])
        return ut.audit(str(f), grid, ut.css_tokens(texts), ut.css_tokens(texts, r'\.dark'), mood, strict=strict)


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

    def test_stock_look(self):
        stock = '<a className="bg-indigo-600 text-white h-12">Go</a><span className="text-indigo-600">x</span>'
        subject = '<a className="bg-emerald-700 text-white h-12">Go</a>'
        custom = '<script>tailwind.config = { theme: { extend: { colors: { brand: "#123" } } } }</script>' + stock
        display = '<link href="https://fonts.googleapis.com/css2?family=Fraunces&display=swap">' + stock
        self.assertTrue(rules(run(stock), 'stock-look'))
        self.assertEqual(rules(run(subject), 'stock-look'), [])
        self.assertEqual(rules(run(custom), 'stock-look'), [])
        self.assertEqual(rules(run(display), 'stock-look'), [])

    def test_no_serif_uses_loaded_faces(self):
        page = '<main><h1 className="text-4xl">x</h1></main>'
        link = lambda fam: f'<link href="https://fonts.googleapis.com/css2?family={fam}&display=swap">'
        for fam in ('Fraunces:opsz,wght@9..144,600', 'Newsreader:ital,wght@0,400', 'Source+Serif+4', 'Playfair+Display'):
            self.assertEqual(rules(run(link(fam) + page, mood='editorial'), 'no-serif'), [], fam)
        self.assertEqual(rules(run('<main><h1 className="font-serif">x</h1></main>', mood='editorial'), 'no-serif'), [])
        self.assertTrue(rules(run(link('Inter') + page, mood='editorial'), 'no-serif'))
        sans = '<style>body{font-family:Inter,sans-serif}</style>' + page
        self.assertTrue(rules(run(sans, mood='editorial'), 'no-serif'))   # sans-serif is not a serif

    def test_stock_look_ignores_common_rounded_faces(self):
        font = '<link href="https://fonts.googleapis.com/css2?family=Fredoka&display=swap">'
        stock = '<a className="bg-violet-600 text-white h-12">Go</a><span className="text-violet-600">x</span>'
        self.assertTrue(rules(run(font + stock), 'stock-look'))   # rounded kids' face alone does not make it distinctive
        serif = '<link href="https://fonts.googleapis.com/css2?family=Fraunces&display=swap">'
        self.assertEqual(rules(run(serif + stock), 'stock-look'), [])

    def test_mood_hero_surface_and_color(self):
        sterile = '<section className="p-8 bg-white"><h1 className="text-slate-900">x</h1><a className="bg-violet-600 h-12">Go</a></section>'
        lively = '<section className="p-8 bg-gradient-to-br from-violet-500 to-amber-400"><h1>x</h1></section><p className="text-sky-700">y</p>'
        self.assertTrue(rules(run(sterile, mood='playful'), 'no-hero-surface'))
        self.assertTrue(rules(run(sterile, mood='playful'), 'low-color'))
        self.assertEqual(rules(run(lively, mood='playful'), 'no-hero-surface'), [])
        self.assertEqual(rules(run(lively, mood='playful'), 'low-color'), [])
        self.assertEqual(rules(run(sterile), 'no-hero-surface'), [])  # mood checks are opt-in


class CharacterFloor(unittest.TestCase):
    def ids(self, html, mood):
        return [f[1] for f in ut.character_floor(html, [], mood)]

    def test_reveal_needs_js(self):
        self.assertIn('reveal-needs-js', self.ids('<div class="opacity-0">x</div>', 'bold'))
        self.assertNotIn('reveal-needs-js', self.ids('<div class="opacity-0">x</div><noscript></noscript>', 'bold'))

    def test_playful_mascot(self):
        self.assertIn('no-drawn-mascot', self.ids('<svg><circle/></svg>', 'playful'))
        shapes = '<svg>' + '<circle/>' * 6 + '</svg>'
        self.assertNotIn('no-drawn-mascot', self.ids(shapes, 'playful'))

    def test_playful_card_sameness(self):
        card = '<div class="bg-white rounded-3xl p-4"></div>' * 7
        self.assertIn('card-sameness', self.ids(card, 'playful'))

    def test_bold_headline_size(self):
        self.assertIn('bold-headline-size', self.ids('<h1 class="text-4xl">x</h1>', 'bold'))
        self.assertIn('bold-headline-size', self.ids('<h1 class="text-5xl">x</h1>', 'bold'))
        self.assertIn('bold-headline-size', self.ids('<h1 class="text-6xl">x</h1>', 'bold'))
        self.assertNotIn('bold-headline-size', self.ids('<h1 class="text-7xl">x</h1>', 'bold'))
        self.assertNotIn('bold-headline-size', self.ids('<style>h1{font-size:clamp(3rem,9vw,7rem)}</style>', 'bold'))

    def test_other_moods_skip(self):
        self.assertEqual(self.ids('<h1 class="text-2xl">x</h1>', 'technical'), [])


class Expressive(unittest.TestCase):
    PAGE = '<h1 class="text-2xl">x</h1><div class="m-[13px]">y</div>'

    def sev(self, mood):
        with tempfile.TemporaryDirectory() as d:
            f = pathlib.Path(d) / 'p.html'; f.write_text(self.PAGE, encoding='utf-8')
            return {r: s for s, r, _ in ut.audit(str(f), 8, {}, None, mood, strict=True)}

    def test_style_rules_relaxed(self):
        self.assertEqual(self.sev('bold').get('bold-headline-size'), 'INFO')
        self.assertEqual(self.sev('bold').get('grid'), 'INFO')

    def test_trust_unchanged(self):
        self.assertEqual(self.sev('trust').get('grid'), 'WARN')

    def test_floor_kept(self):
        with tempfile.TemporaryDirectory() as d:
            f = pathlib.Path(d) / 'p.html'
            f.write_text('<div class="opacity-0">x</div><p class="text-gray-300 bg-white">low</p>'
                         '<button class="bg-blue-600 text-white h-8 px-4">Go</button>', encoding='utf-8')
            r = {x[1]: x[0] for x in ut.audit(str(f), 8, {}, None, 'playful', strict=True)}
        self.assertEqual(r.get('reveal-needs-js'), 'WARN')
        self.assertEqual(r.get('fitts-primary'), 'WARN')
        self.assertIn(r.get('wcag-aa'), ('WARN', 'FAIL'))


class SoftRules(unittest.TestCase):
    """Style findings are INFO by default and WARN with strict=True; the accessibility floor never moves."""
    SRC = ('<main><section class="p-8"><a class="h-9 bg-indigo-600 text-white px-4">Go</a>'
           '<a class="h-9 bg-indigo-600 text-white px-4">Two</a></section><div class="opacity-0">x</div></main>')

    def sev(self, strict, src=None):
        with tempfile.TemporaryDirectory() as d:
            f = pathlib.Path(d) / 'p.html'; f.write_text(src or self.SRC, encoding='utf-8')
            return {r: s for s, r, _ in ut.audit(str(f), 8, {}, None, None, strict=strict)}

    def test_default_is_info_strict_is_warn(self):
        soft, hard = self.sev(False), self.sev(True)
        for rule in ('single-primary-cta', 'fitts-primary'):
            self.assertEqual(soft.get(rule), 'INFO', rule)
            self.assertEqual(hard.get(rule), 'WARN', rule)

    def test_floor_never_softens(self):
        for strict in (False, True):
            self.assertEqual(self.sev(strict).get('reveal-needs-js'), 'WARN')
        low = '<main><p class="text-gray-300 bg-white">low</p></main>'
        for strict in (False, True):
            self.assertIn(self.sev(strict, low).get('wcag-aa'), ('WARN', 'FAIL'))

    def test_tiny_primary_target_stays_warn(self):
        tiny = '<main><a class="h-5 bg-indigo-600 text-white px-2">Go</a></main>'
        self.assertEqual(self.sev(False, tiny).get('fitts-primary'), 'WARN')


class Landmark(unittest.TestCase):
    def rules(self, html):
        with tempfile.TemporaryDirectory() as d:
            f = pathlib.Path(d) / 'p.html'; f.write_text(html, encoding='utf-8')
            return [r for _, r, _ in ut.audit(str(f), 8, {}, None, None)]

    def test_main_required_for_full_pages(self):
        self.assertIn('landmark-main', self.rules('<html><body><div>x</div></body></html>'))
        self.assertNotIn('landmark-main', self.rules('<html><body><main>x</main></body></html>'))
        self.assertNotIn('landmark-main', self.rules('<div>fragment</div>'))


class CustomColors(unittest.TestCase):
    def test_inline_tailwind_config(self):
        txt = "<script>tailwind.config={theme:{extend:{colors:{ink:'#12264A',brand:{500:'#ff0000',DEFAULT:'#00ff00'}}}}}</script>"
        c = ut.tailwind_config_colors(txt)
        self.assertEqual(c['ink'], '#12264A')
        self.assertEqual(c['brand-500'], '#ff0000')
        self.assertEqual(c['brand'], '#00ff00')

    def test_v4_theme_vars(self):
        self.assertEqual(ut.tailwind_config_colors('@theme { --color-sun: #ffc933; }')['sun'], '#ffc933')

    def test_low_contrast_custom_color_flagged(self):
        html = ("<script>tailwind.config={theme:{extend:{colors:{sun:'#FFC933'}}}}</script>"
                '<p class="text-sun bg-white">hello</p>')
        with tempfile.TemporaryDirectory() as d:
            f = pathlib.Path(d) / 'p.html'; f.write_text(html, encoding='utf-8')
            iss = ut.audit(str(f), 8, ut.css_tokens([html]), None, None)
        self.assertTrue(any(r == 'wcag-aa' for _, r, _ in iss))


class Cli(unittest.TestCase):
    def test_exit_code_on_fail(self):
        with tempfile.TemporaryDirectory() as d:
            f = pathlib.Path(d) / 'a.tsx'
            f.write_text('<p className="text-slate-300">x</p>', encoding='utf-8')
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
        iss = run(bad, mood='editorial')
        self.assertTrue(rules(iss, 'edge-align'))
        self.assertFalse(any('Drop mx-auto' in msg for _, r, msg in iss if r == 'edge-align'))
        two_col_ok = '<main className="max-w-5xl mx-auto"><h1 className="text-5xl">T</h1><div className="grid lg:grid-cols-[minmax(0,65ch)_280px]"><div className="max-w-prose"><p>x</p></div><aside>R</aside></div><footer><form className="max-w-md mx-auto"></form></footer></main>'
        self.assertEqual(rules(run(two_col_ok, mood='editorial'), 'edge-align'), [])
        centered = '<div className="max-w-4xl mx-auto md:text-center"><h1 className="text-5xl">T</h1></div><div className="max-w-prose mx-auto"><p>x</p></div>'
        self.assertEqual(rules(run(centered, mood='editorial'), 'edge-align'), [])

    def test_editorial_edge_cases_v2(self):
        bottom_aside = '<main className="max-w-5xl mx-auto"><h1 className="text-5xl text-center">T</h1><div className="max-w-prose"><p>x</p></div><aside>Author bio</aside></main>'
        self.assertTrue(rules(run(bottom_aside, mood='editorial'), 'left-stacked-column'))
        wide_2xl_uncentered = '<article className="mx-auto max-w-6xl"><h1 className="text-6xl text-center">T</h1><div className="max-w-2xl"><p>x</p></div></article>'
        self.assertTrue(rules(run(wide_2xl_uncentered, mood='editorial'), 'left-stacked-column'))
        nested_ok = '<main className="max-w-5xl mx-auto text-center"><div className="max-w-prose mx-auto"><div className="max-w-prose"><p>x</p></div></div></main>'
        self.assertEqual(rules(run(nested_ok, mood='editorial'), 'left-stacked-column'), [])
        twok_grid = '<article className="mx-auto max-w-6xl"><div className="grid 2xl:grid-cols-2"><div className="max-w-prose"><p>x</p></div><div>rail</div></div></article>'
        self.assertEqual(rules(run(twok_grid, mood='editorial'), 'left-stacked-column'), [])
        js_bitter = '<link href="https://fonts.googleapis.com/css2?family=Inter"><script>const x=["Bitter","Sweet"];</script><main><h1 className="text-4xl">T</h1></main>'
        self.assertTrue(rules(run(js_bitter, suffix='.html', mood='editorial'), 'no-serif'))
        tw_single = '<script>tailwind.config={theme:{extend:{fontFamily:{display:["Playfair Display"]}}}}</script><main><h1 className="font-display text-5xl">T</h1></main>'
        self.assertEqual(rules(run(tw_single, suffix='.html', mood='editorial'), 'no-serif'), [])

    def test_editorial_h2_and_2xl_allowed_in_headline_measure(self):
        h2_ok = '<div className="max-w-prose mx-auto"><h2 className="text-4xl font-serif">Subheading</h2><p>x</p></div>'
        self.assertEqual(rules(run(h2_ok, mood='editorial'), 'headline-measure'), [])
        unified = '<main className="max-w-2xl mx-auto"><h1 className="text-4xl font-serif">Title</h1><p>x</p></main>'
        self.assertEqual(rules(run(unified, mood='editorial'), 'headline-measure'), [])
        trapped_h1 = '<main className="max-w-prose mx-auto"><h1 className="text-4xl font-serif">Big</h1></main>'
        self.assertTrue(rules(run(trapped_h1, mood='editorial'), 'headline-measure'))

    def test_editorial_left_stacked_column(self):
        bad = '<article className="mx-auto max-w-5xl"><h1 className="text-6xl text-center">T</h1><div className="max-w-prose"><p>x</p></div></article>'
        iss = run(bad, mood='editorial')
        self.assertEqual([sev for sev, r, _ in iss if r == 'left-stacked-column'], ['WARN'])
        centered = '<article className="mx-auto max-w-5xl"><h1 className="text-6xl text-center">T</h1><div className="mx-auto max-w-prose"><p>x</p></div></article>'
        self.assertEqual(rules(run(centered, mood='editorial'), 'left-stacked-column'), [])
        two_col_aside = ('<main className="mx-auto max-w-5xl grid lg:grid-cols-[minmax(0,65ch)_280px]">'
                         '<div className="max-w-prose"><p>x</p></div><aside>rail</aside></main>')
        self.assertEqual(rules(run(two_col_aside, mood='editorial'), 'left-stacked-column'), [])
        two_col_grid = ('<article className="mx-auto max-w-5xl"><div className="grid lg:grid-cols-[minmax(0,65ch)_280px]">'
                        '<div className="max-w-prose"><p>x</p></div><div>rail</div></div></article>')
        self.assertEqual(rules(run(two_col_grid, mood='editorial'), 'left-stacked-column'), [])

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


class Regressions(unittest.TestCase):
    def test_invalid_hex_validation_and_tw_hex(self):
        self.assertIsNone(ut.tw_hex('[#1234]', {}))
        self.assertEqual(rules(run('<p className="text-[#1234]">x</p>'), 'wcag-aa'), [])
        with self.assertRaises(ValueError):
            ut.hex2rgb('#1234')
        with self.assertRaises(ValueError):
            ut.hex2rgb('#gggggg')

    def test_tailwind_config_comments_strings_and_dark_theme_vars(self):
        txt = """
        <style>
          /* --color-ignored: #ff0000; */
          @theme { --color-accent: #10b981; --color-bad: #1234; }
          .dark { --color-accent: #000000; --color-darkonly: #111111; }
        </style>
        <script>
          tailwind.config = {
            theme: { extend: { colors: {
              // brace } in line comment
              /* block } comment */
              note: "string with } brace",
              brand: '#ff5500',
              bad4: '#1234',
              bad8: '#12345678',
            } } }
          };
        </script>
        """
        c = ut.tailwind_config_colors(txt)
        self.assertEqual(c['accent'], '#10b981')
        self.assertNotIn('darkonly', c)
        self.assertNotIn('ignored', c)
        self.assertNotIn('bad', c)
        self.assertNotIn('bad4', c)
        self.assertNotIn('bad8', c)
        self.assertEqual(c['brand'], '#ff5500')

    def test_css_body_background_and_inline_style_bg(self):
        html = '<style>body { background: #0B0B0C; }</style><body><p class="text-white">ok</p><p class="text-zinc-900">bad</p></body>'
        iss = rules(run(html, suffix='.html'), 'wcag-aa')
        self.assertEqual(len(iss), 1)
        self.assertIn('bg-[#0B0B0C]', iss[0][2])
        self.assertTrue(ut.is_dark_page(html))
        inline = '<div style="background: #0B0B0C"><span class="text-white">ok</span><span class="text-zinc-900">bad</span></div>'
        iss_inline = rules(run(inline, suffix='.html'), 'wcag-aa')
        self.assertEqual(len(iss_inline), 1)
        self.assertIn('bg-[#0B0B0C]', iss_inline[0][2])
        after_root = '<style>:root { --a: 1; }\nbody { background: #0B0A09; color: #F4EDE4; }</style><main><p class="text-white">ok</p></main>'
        self.assertEqual(ut.css_page_bg(after_root), '#0B0A09')
        self.assertEqual(rules(run(after_root, suffix='.html'), 'wcag-aa'), [])

    def test_dark_bg_background_ancestor_caught(self):
        src = '<div className="bg-background"><p className="text-slate-700">x</p></div>'
        iss = rules(run(src, css=SHADCN_CSS), 'wcag-aa')
        self.assertTrue(any('[.dark] text-slate-700 on bg-background' in i[2] for i in iss))

    def test_unclosed_html_comment_does_not_poison_and_script_masked(self):
        unclosed = '<!-- unclosed comment\n<p class="text-slate-300">bad</p>'
        self.assertTrue(rules(run(unclosed, suffix='.html'), 'wcag-aa'))
        closed = '<!-- <p class="text-slate-300">ignored</p> --><p class="text-slate-900">ok</p>'
        self.assertEqual(rules(run(closed, suffix='.html'), 'wcag-aa'), [])
        scripted = '<script>const s = `<span class="text-muted">x</span>`;</script><p class="text-slate-900">ok</p>'
        self.assertEqual(rules(run(scripted, suffix='.html'), 'wcag-aa'), [])

    def test_ts_generics_and_template_literal_classes(self):
        src = ('const x: Array<string> = [];\n'
               'export function C({a}: {a: boolean}) {\n'
               '  return <div className={`bg-slate-900 ${a ? "p-4" : "p-2"}`}><span className="text-slate-700">x</span></div>;\n'
               '}')
        iss = rules(run(src), 'wcag-aa')
        self.assertTrue(any('bg-slate-900' in i[2] for i in iss))
        ternary = "<div className={cond ? 'bg-white' : 'bg-slate-900'}><span className=\"text-slate-700\">x</span></div>"
        self.assertTrue(rules(run(ternary), 'wcag-aa'))
        adj = '<div class="bg-zinc-950"><a class="bg-lime text-zinc-950">See work</a><a class="text-white">Contact</a></div>'
        self.assertEqual(rules(run(adj, suffix='.html'), 'wcag-aa'), [])

    def test_tailwind_v4_gradients(self):
        self.assertTrue(ut.is_gradient('bg-linear-to-r'))
        self.assertTrue(ut.is_gradient('bg-radial'))
        self.assertTrue(ut.is_gradient('bg-conic-180'))
        bad = '<div className="bg-linear-to-r from-yellow-300 to-pink-600"><p className="text-white">Hi</p></div>'
        msg = rules(run(bad), 'wcag-aa')
        self.assertTrue(msg and 'gradient stop from-yellow-300' in msg[0][2])
        hero = '<section className="py-12 bg-linear-to-r from-indigo-600 to-violet-700"><h1>Hi</h1></section>'
        self.assertEqual(rules(run(hero, mood='bold'), 'no-hero-surface'), [])

    def test_no_serif_excludes_sans_serif_and_arbitrary_size(self):
        sans = '<style>body{font-family:Inter,sans-serif}</style><h1 class="font-[700]">Hi</h1>'
        self.assertTrue(rules(run(sans, suffix='.html', mood='editorial'), 'no-serif'))
        serif = '<h1 class="font-serif">Hi</h1>'
        self.assertEqual(rules(run(serif, suffix='.html', mood='editorial'), 'no-serif'), [])

    def test_max_2_fonts_generics_and_v1_pipe(self):
        ok = ('<link href="https://fonts.googleapis.com/css2?family=Inter&family=Fraunces">'
              '<style>body{font-family:system-ui,sans-serif} code{font-family:ui-monospace,monospace}</style>')
        self.assertEqual(rules(run(ok, suffix='.html'), 'max-2-fonts'), [])
        v1 = '<link href="https://fonts.googleapis.com/css?family=Roboto:400,700|Open+Sans:400|Lato:400">'
        self.assertEqual(rules(run(v1, suffix='.html'), 'max-2-fonts')[0][0], 'FAIL')

    def test_text_and_bg_non_color_utilities(self):
        src = '<div className="bg-white bg-size-auto bg-[length:10px]"><p className="text-slate-900 text-opacity-50 text-shadow-sm text-[length:14px]">x</p></div>'
        self.assertEqual(rules(run(src), 'wcag-aa'), [])

    def test_edge_align_allows_h1_inside_centered_column(self):
        inside = '<div className="max-w-prose mx-auto"><h1 className="text-3xl">T</h1><p>x</p></div>'
        self.assertEqual(rules(run(inside, mood='editorial'), 'edge-align'), [])

    def test_hover_opacity_zero_does_not_trigger_reveal_needs_js(self):
        src = '<button className="hover:opacity-0 disabled:opacity-0">x</button>'
        self.assertEqual(rules(run(src, mood='bold'), 'reveal-needs-js'), [])
        self.assertTrue(rules(run('<div className="opacity-0">x</div>', mood='bold'), 'reveal-needs-js'))

    def test_custom_palette_hero_surface_and_low_color(self):
        src = ('<script>tailwind.config={theme:{extend:{colors:{ink:"#0B0B0C",lime:"#C6FF3D",coral:"#FF5A36",sky2:"#38BDF8"}}}}</script>'
               '<section class="bg-coral py-16"><h1>Hi</h1></section><p class="text-lime">A</p><p class="text-sky2">B</p>')
        self.assertEqual(rules(run(src, suffix='.html', mood='bold'), 'no-hero-surface'), [])
        self.assertEqual(rules(run(src, suffix='.html', mood='bold'), 'low-color'), [])

    def test_stock_look_with_mono_font_and_next_font(self):
        mono = '<link href="https://fonts.googleapis.com/css2?family=Inter&family=JetBrains+Mono"><a className="bg-indigo-600 text-white h-12">Go</a>'
        self.assertTrue(rules(run(mono), 'stock-look'))
        nxt = "import { Inter } from 'next/font/google';\n<a className=\"bg-indigo-600 text-white h-12\">Go</a>"
        self.assertTrue(rules(run(nxt), 'stock-look'))
        self.assertTrue(rules(run(nxt, mood='bold'), 'bold-font-default'))

    def test_cli_guards_and_file_token_isolation(self):
        for args in (['snap', '10', '--grid', '0'], ['audit', 'x.html', '--grid', '0'],
                     ['scale', '--ratio', 'bogus'], ['scale', '--ratio', '0'],
                     ['contrast', '#1234', '#ffffff'], ['contrast', '#ffffff', 'notacolor']):
            with self.assertRaises(SystemExit):
                ut.main(args)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ut.main(['contrast', '#777777', '#888888', '--target', '7'])
        self.assertIn('best possible', out.getvalue())
        self.assertNotIn('>= 7', out.getvalue())
        with tempfile.TemporaryDirectory() as d:
            a = pathlib.Path(d) / 'a.html'
            b = pathlib.Path(d) / 'b.html'
            a.write_text('<script>tailwind.config={theme:{extend:{colors:{brand:"#000000"}}}}</script><p class="text-brand">a</p>', encoding='utf-8')
            b.write_text('<div class="bg-brand"><p class="text-slate-700">b</p></div>', encoding='utf-8')
            out = io.StringIO()
            with self.assertRaises(SystemExit) as cm, contextlib.redirect_stdout(out):
                ut.main(['audit', str(a), str(b)])
            self.assertEqual(cm.exception.code, 0)
            self.assertNotIn('bg-brand', out.getvalue())

    def test_v2_hardening_regressions(self):
        inline_var = '<style>:root { --surface: #0b0b0c; }</style><div style="background: var(--surface)"><p className="text-white">Hi</p></div><div style="background: rgb(15, 23, 42)"><p className="text-white">Hi</p></div>'
        self.assertEqual(rules(run(inline_var, suffix='.html'), 'wcag-aa'), [])

        dark_media = '<style>body { background: #ffffff; } @media (prefers-color-scheme: dark) { body { background: #0b0b0c; } }</style><body><p class="text-slate-900">Hi</p></body>'
        self.assertEqual(rules(run(dark_media, suffix='.html'), 'wcag-aa'), [])

        jsx_3 = '<div className="bg-slate-900" onClick={() => { if (a) { b(); } }}><p className="text-white">Hi</p></div>'
        self.assertEqual(rules(run(jsx_3), 'wcag-aa'), [])
        tpl_cls = '<div className={`p-4 ${dark ? "bg-slate-900" : "bg-slate-800"}`}><span className="text-white">x</span></div>'
        self.assertEqual(rules(run(tpl_cls), 'wcag-aa'), [])

        f_ok = ('<link href="https://fonts.googleapis.com/css2?family=Inter&family=Playfair%20Display">'
                '<style>/* font-family: Lobster; */ h1 { font-family: "playfair display", serif; }</style>'
                '<h2 style="font-family: \'Playfair Display\'">X</h2>')
        self.assertEqual(rules(run(f_ok, suffix='.html'), 'max-2-fonts'), [])

        css_wcag = '.a { /* color: #cccccc; */ color: #111111; background: #ffffff; } .b { background: #ffffff; background: #0f172a; color: #f8fafc; } h1 { font-size: 48px; color: #949494; background: #ffffff; }'
        self.assertEqual(rules(run(css_wcag, suffix='.css'), 'wcag-aa'), [])

        grid_prose = '<style>/* padding: 13px; */ .a { padding: 16px; }</style><p>Avoid padding: 13px and p-3</p>'
        self.assertEqual(rules(run(grid_prose, suffix='.html'), 'grid'), [])
        self.assertTrue(rules(run('<div className="md:p-[13px]">x</div>'), 'grid'))

        long_p = 'x ' * 50
        self.assertEqual(rules(run(f'<section class="grid md:grid-cols-3"><div><p>{long_p}</p></div></section>', suffix='.html'), 'line-length'), [])
        self.assertEqual(rules(run(f'<main class="max-w-7xl"><div class="lg:max-w-prose"><p>{long_p}</p></div></main>', suffix='.html'), 'line-length'), [])
        self.assertTrue(rules(run(f'<style>.footer p {{ max-width: 65ch; }}</style><main class="max-w-7xl"><p>{long_p}</p></main>', suffix='.html'), 'line-length'))

        pad_clamp = '<style>section { padding-block: clamp(2rem, 8vw, 6rem); }</style><h1 className="text-2xl">Tiny</h1>'
        self.assertTrue(rules(run(pad_clamp, suffix='.html', mood='bold'), 'bold-headline-size'))
        u_clamp = '<h1 className="text-[clamp(3rem,_8vw,_6rem)]">Huge</h1>'
        self.assertEqual(rules(run(u_clamp, mood='bold'), 'bold-headline-size'), [])

        cta_ok = '<section><a className="bg-[#ffffff] border">A</a><a className="bg-[#f8fafc] border">B</a><a className="bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-transparent">Brand</a></section>'
        self.assertEqual(rules(run(cta_ok), 'single-primary-cta'), [])
        cta_tok = '<script>tailwind.config={theme:{extend:{colors:{coral:"#FF5A36"}}}}</script><section><button class="bg-coral text-white h-8">A</button><button class="bg-coral text-white h-8">B</button></section>'
        self.assertTrue(rules(run(cta_tok, suffix='.html'), 'single-primary-cta'))
        self.assertTrue(rules(run(cta_tok, suffix='.html'), 'fitts-primary'))


class VariantAwareAudit(unittest.TestCase):
    def test_branch_labeled_contrast_failure(self):
        src = (
            '<button className={cn("px-3 py-1", selected ? "bg-slate-100 text-slate-300" : "bg-slate-900 text-white")}>'
            'Chip</button>'
        )
        iss = rules(run(src), 'wcag-aa')
        self.assertEqual(len(iss), 1)
        self.assertEqual(iss[0][0], 'FAIL')
        self.assertIn('[selected=true] text-slate-300 on bg-slate-100', iss[0][2])

        uncond = '<p className="bg-slate-100 text-slate-300">Static</p>'
        u_iss = rules(run(uncond), 'wcag-aa')
        self.assertEqual(len(u_iss), 1)
        self.assertTrue(u_iss[0][2].startswith('L1 text-slate-300 on bg-slate-100'))

        grad_branch = (
            '<div className={cn("p-4", isHero ? "bg-gradient-to-r from-yellow-300 to-pink-600" : "bg-slate-900")}>'
            '<p className="text-white">Banner</p></div>'
        )
        g_iss = rules(run(grad_branch), 'wcag-aa')
        self.assertEqual(len(g_iss), 1)
        self.assertIn('[isHero=true] text-white on gradient stop from-yellow-300', g_iss[0][2])

    def test_branch_explosion_info_emitted_once_per_node(self):
        exploded_src = (
            '<div className={cn(c1 && "p-1", c2 && "m-1", c3 && "w-4", c4 && "h-4")}>x</div>'
        )
        iss = rules(run(exploded_src), 'branch-explosion')
        self.assertEqual(len(iss), 1)
        self.assertEqual(iss[0][0], 'INFO')
        self.assertIn('>8 conditional class combinations; auditing first 8 branches', iss[0][2])

        within_limit = '<div className={cn(c1 && "p-1", c2 && "m-1", c3 && "w-4")}>x</div>'
        self.assertEqual(rules(run(within_limit), 'branch-explosion'), [])

    def test_ancestor_child_same_condition_group_consistency(self):
        consistent = (
            '<div className={cn("p-4", isDark ? "bg-slate-900" : "bg-white")}>'
            '<span className={cn("text-sm", isDark ? "text-white" : "text-slate-900")}>Text</span>'
            '</div>'
        )
        self.assertEqual(rules(run(consistent), 'wcag-aa'), [])

        negated = (
            '<div className={isDark ? "bg-slate-900" : "bg-white"}>'
            '<span className={!isDark ? "text-slate-900" : "text-white"}>Text</span>'
            '</div>'
        )
        self.assertEqual(rules(run(negated), 'wcag-aa'), [])

        bad_in_true_branch = (
            '<div className={isDark ? "bg-slate-900" : "bg-white"}>'
            '<span className={isDark ? "text-slate-700" : "text-slate-900"}>Text</span>'
            '</div>'
        )
        iss = rules(run(bad_in_true_branch), 'wcag-aa')
        self.assertEqual(len(iss), 1)
        self.assertIn('[isDark=true] text-slate-700 on bg-slate-900', iss[0][2])

    def test_fitts_primary_variant_consistency(self):
        no_cross = '<button className={cn(isPrimary ? "bg-indigo-600 text-white h-11" : "border text-slate-700 h-8")}>Act</button>'
        self.assertEqual(rules(run(no_cross), 'fitts-primary'), [])

        compact_fail = '<button className={cn("bg-indigo-600 text-white", compact ? "h-8" : "h-11")}>Act</button>'
        iss = rules(run(compact_fail), 'fitts-primary')
        self.assertEqual(len(iss), 1)
        self.assertIn('32px tall', iss[0][2])

    def test_jsx_conditional_cta_branches(self):
        ternary = '<section>{isEditing ? <Button>Save</Button> : <Button>Edit</Button>}</section>'
        self.assertEqual(rules(run(ternary), 'single-primary-cta'), [])

        paired_and = '<section>{isEditing && <Button>Save</Button>}{!isEditing && <Button>Edit</Button>}</section>'
        self.assertEqual(rules(run(paired_and), 'single-primary-cta'), [])

        lookup = '<section>{{ a: <Button>Alpha</Button>, b: <Button>Beta</Button> }[mode]}</section>'
        self.assertEqual(rules(run(lookup), 'single-primary-cta'), [])

        single_btn_variants = (
            '<section><button className={cn("px-4", isPrimary ? "bg-indigo-600 text-white" : "border text-slate-700")}>'
            'Go</button></section>'
        )
        self.assertEqual(rules(run(single_btn_variants), 'single-primary-cta'), [])

        same_branch_two = (
            '<section>{isEditing ? (<><Button>Save</Button><Button>Publish</Button></>) : <Button>Edit</Button>}</section>'
        )
        iss = rules(run(same_branch_two), 'single-primary-cta')
        self.assertEqual(len(iss), 1)
        self.assertIn('2 solid buttons in one block', iss[0][2])


if __name__ == '__main__':
    unittest.main()
