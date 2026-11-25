import math
import pathlib
import subprocess
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))

import uicolor as uc

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _hex_to_lab(hx):
    """Convert #rrggbb to CIELAB (D65) for CIEDE2000."""
    r, g, b = [v / 255.0 for v in uc.hex2rgb(hx)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
    rl, gl, bl = lin
    x = (0.4124564 * rl + 0.3575761 * gl + 0.1804375 * bl) / 0.95047
    y = (0.2126729 * rl + 0.7151522 * gl + 0.0721750 * bl) / 1.00000
    z = (0.0193339 * rl + 0.1191920 * gl + 0.9503041 * bl) / 1.08883
    f = [t ** (1.0 / 3.0) if t > 0.008856 else 7.787 * t + 16.0 / 116.0 for t in (x, y, z)]
    return 116.0 * f[1] - 16.0, 500.0 * (f[0] - f[1]), 200.0 * (f[1] - f[2])


def delta_e2000(hex1, hex2):
    """Compute CIEDE2000 color difference between two hex colors."""
    L1, a1, b1 = _hex_to_lab(hex1)
    L2, a2, b2 = _hex_to_lab(hex2)
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2)
    C_bar = 0.5 * (C1 + C2)
    C_bar7 = C_bar ** 7
    G = 0.5 * (1.0 - math.sqrt(C_bar7 / (C_bar7 + 25.0 ** 7)))
    a1p, a2p = (1.0 + G) * a1, (1.0 + G) * a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360.0 if C1p > 1e-12 else 0.0
    h2p = math.degrees(math.atan2(b2, a2p)) % 360.0 if C2p > 1e-12 else 0.0
    dLp = L2 - L1
    dCp = C2p - C1p
    if C1p * C2p == 0.0:
        dhp = 0.0
    elif abs(h2p - h1p) <= 180.0:
        dhp = h2p - h1p
    elif h2p - h1p > 180.0:
        dhp = h2p - h1p - 360.0
    else:
        dhp = h2p - h1p + 360.0
    dHp = 2.0 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp * 0.5))
    Lbp = 0.5 * (L1 + L2)
    Cbp = 0.5 * (C1p + C2p)
    if C1p * C2p == 0.0:
        hbp = h1p + h2p
    elif abs(h1p - h2p) <= 180.0:
        hbp = 0.5 * (h1p + h2p)
    elif h1p + h2p < 360.0:
        hbp = 0.5 * (h1p + h2p + 360.0)
    else:
        hbp = 0.5 * (h1p + h2p - 360.0)
    T = (
        1.0
        - 0.17 * math.cos(math.radians(hbp - 30.0))
        + 0.24 * math.cos(math.radians(2.0 * hbp))
        + 0.32 * math.cos(math.radians(3.0 * hbp + 6.0))
        - 0.20 * math.cos(math.radians(4.0 * hbp - 63.0))
    )
    d_theta = 30.0 * math.exp(-(((hbp - 275.0) / 25.0) ** 2))
    Cbp7 = Cbp ** 7
    RC = 2.0 * math.sqrt(Cbp7 / (Cbp7 + 25.0 ** 7))
    Lbp50_2 = (Lbp - 50.0) ** 2
    SL = 1.0 + (0.015 * Lbp50_2) / math.sqrt(20.0 + Lbp50_2)
    SC = 1.0 + 0.045 * Cbp
    SH = 1.0 + 0.015 * Cbp * T
    RT = -math.sin(math.radians(2.0 * d_theta)) * RC
    return math.sqrt(
        (dLp / SL) ** 2
        + (dCp / SC) ** 2
        + (dHp / SH) ** 2
        + RT * (dCp / SC) * (dHp / SH)
    )


class TestShadcnV4GlobalsCss(unittest.TestCase):
    """S4 validation: shadcn v4 Neutral, Zinc, Slate globals.css OKLCH -> hex within dE2000 < 2.0."""

    def test_shadcn_v4_neutral_zinc_slate_tokens(self):
        themes = {
            'neutral': (
                """
                @import "tailwindcss";
                @theme inline {
                  --color-background: var(--background);
                  --color-foreground: var(--foreground);
                  --color-primary: var(--primary);
                  --color-destructive: var(--destructive);
                }
                :root {
                  --background: oklch(1 0 0);
                  --foreground: oklch(0.145 0 0);
                  --card: oklch(1 0 0);
                  --primary: oklch(0.205 0 0);
                  --primary-foreground: oklch(0.985 0 0);
                  --secondary: oklch(0.97 0 0);
                  --muted-foreground: oklch(0.556 0 0);
                  --border: oklch(0.922 0 0);
                  --destructive: oklch(0.577 0.245 27.325);
                }
                .dark {
                  --background: oklch(0.145 0 0);
                  --foreground: oklch(0.985 0 0);
                  --card: oklch(0.205 0 0);
                  --primary: oklch(0.922 0 0);
                  --primary-foreground: oklch(0.205 0 0);
                  --secondary: oklch(0.269 0 0);
                  --muted-foreground: oklch(0.708 0 0);
                  --destructive: oklch(0.704 0.191 22.216);
                }
                """,
                {
                    'background': '#ffffff', 'foreground': '#0a0a0a', 'card': '#ffffff',
                    'primary': '#171717', 'primary-foreground': '#fafafa',
                    'secondary': '#f5f5f5', 'muted-foreground': '#737373',
                    'border': '#e5e5e5', 'destructive': '#e40016',
                },
                {
                    'background': '#0a0a0a', 'foreground': '#fafafa', 'card': '#171717',
                    'primary': '#e5e5e5', 'primary-foreground': '#171717',
                    'secondary': '#262626', 'muted-foreground': '#a1a1a1',
                    'destructive': '#ff6568',
                },
            ),
            'zinc': (
                """
                @import "tailwindcss";
                :root {
                  --background: oklch(1 0 0);
                  --foreground: oklch(0.141 0.005 285.823);
                  --primary: oklch(0.21 0.006 285.885);
                  --primary-foreground: oklch(0.985 0 0);
                  --secondary: oklch(0.967 0.001 286.375);
                  --muted-foreground: oklch(0.552 0.016 285.938);
                  --border: oklch(0.92 0.004 286.32);
                }
                .dark {
                  --background: oklch(0.141 0.005 285.823);
                  --foreground: oklch(0.985 0 0);
                  --card: oklch(0.21 0.006 285.885);
                  --primary: oklch(0.92 0.004 286.32);
                  --primary-foreground: oklch(0.21 0.006 285.885);
                  --muted-foreground: oklch(0.705 0.015 286.067);
                }
                """,
                {
                    'background': '#ffffff', 'foreground': '#09090b', 'primary': '#18181b',
                    'primary-foreground': '#fafafa', 'secondary': '#f4f4f5',
                    'muted-foreground': '#71717b', 'border': '#e4e4e7',
                },
                {
                    'background': '#09090b', 'foreground': '#fafafa', 'card': '#18181b',
                    'primary': '#e4e4e7', 'primary-foreground': '#18181b',
                    'muted-foreground': '#9f9fa9',
                },
            ),
            'slate': (
                """
                @import "tailwindcss";
                :root {
                  --background: oklch(1 0 0);
                  --foreground: oklch(0.129 0.042 264.695);
                  --primary: oklch(0.208 0.042 265.755);
                  --primary-foreground: oklch(0.984 0.003 247.858);
                  --secondary: oklch(0.968 0.007 247.896);
                  --muted-foreground: oklch(0.554 0.046 257.417);
                  --border: oklch(0.929 0.013 255.508);
                }
                .dark {
                  --background: oklch(0.129 0.042 264.695);
                  --foreground: oklch(0.984 0.003 247.858);
                  --card: oklch(0.208 0.042 265.755);
                  --primary: oklch(0.929 0.013 255.508);
                  --primary-foreground: oklch(0.208 0.042 265.755);
                  --muted-foreground: oklch(0.704 0.04 256.788);
                }
                """,
                {
                    'background': '#ffffff', 'foreground': '#020618', 'primary': '#0f172b',
                    'primary-foreground': '#f8fafc', 'secondary': '#f1f5f9',
                    'muted-foreground': '#62748e', 'border': '#e2e8f0',
                },
                {
                    'background': '#020618', 'foreground': '#f8fafc', 'card': '#0f172b',
                    'primary': '#e2e8f0', 'primary-foreground': '#0f172b',
                    'muted-foreground': '#90a1b9',
                },
            ),
        }
        for name, (css, exp_light, exp_dark) in themes.items():
            light = uc.css_tokens([css])
            dark = uc.css_tokens([css], r'\.dark')
            for k, ref_hx in exp_light.items():
                self.assertIn(k, light, f"{name} light missing {k}")
                self.assertLess(delta_e2000(light[k], ref_hx), 2.0, f"{name} light {k}: {light[k]} vs {ref_hx}")
            for k, ref_hx in exp_dark.items():
                self.assertIn(k, dark, f"{name} dark missing {k}")
                self.assertLess(delta_e2000(dark[k], ref_hx), 2.0, f"{name} dark {k}: {dark[k]} vs {ref_hx}")


class TestColorSpaces(unittest.TestCase):
    def test_oklch_out_of_gamut_clipping(self):
        hx = uc.parse_color('oklch(0.7 0.35 150)')
        self.assertIsNotNone(hx)
        r, g, b = uc.hex2rgb(hx)
        self.assertTrue(all(0 <= ch <= 255 for ch in (r, g, b)))
        self.assertGreater(g, r)
        self.assertGreater(g, b)

    def test_oklch_units_none_and_alpha(self):
        self.assertEqual(uc.parse_color('oklch(20.5% 0 none)'), '#171717')
        self.assertEqual(uc.parse_color('oklch(0.623 53.5% 259.815deg)'), uc.parse_color('oklch(0.623 0.214 259.815)'))
        self.assertEqual(uc.parse_color('oklch(0.6 0.2 0.5turn)'), uc.parse_color('oklch(0.6 0.2 180)'))
        self.assertEqual(uc.parse_color('oklch(0.6 0.2 200grad)'), uc.parse_color('oklch(0.6 0.2 180)'))
        self.assertEqual(uc.parse_color('oklch(0.6 0.2 3.14159265rad)'), uc.parse_color('oklch(0.6 0.2 180)'))
        self.assertEqual(uc.parse_color('oklch(0.205 0 0 / 50%)'), '#171717')
        self.assertAlmostEqual(uc.alpha_of('oklch(0.205 0 0 / 50%)'), 0.5)
        self.assertAlmostEqual(uc.alpha_of('[oklch(0.205_0_0/0.25)]'), 0.25)

    def test_oklab_parsing_and_gamut_clipping(self):
        self.assertEqual(uc.parse_color('oklab(0 0 0)'), '#000000')
        self.assertEqual(uc.parse_color('oklab(100% 0 0)'), '#ffffff')
        self.assertEqual(uc.parse_color('oklab(0.5 none none / 0.4)'), '#636363')
        self.assertAlmostEqual(uc.alpha_of('oklab(0.5 0 0 / 40%)'), 0.4)
        # Out-of-gamut oklab
        hx = uc.parse_color('oklab(0.7 -0.35 0.2)')
        r, g, b = uc.hex2rgb(hx)
        self.assertTrue(all(0 <= ch <= 255 for ch in (r, g, b)))

    def test_rgb_and_rgba_modern_and_legacy(self):
        self.assertEqual(uc.parse_color('rgb(255, 0, 128)'), '#ff0080')
        self.assertEqual(uc.parse_color('rgb(100% 0% 50%)'), '#ff0080')
        self.assertEqual(uc.parse_color('rgba(16, 32, 48, 0.5)'), '#102030')
        self.assertAlmostEqual(uc.alpha_of('rgba(16, 32, 48, 0.5)'), 0.5)
        self.assertEqual(uc.parse_color('rgb(16 32 48 / 25%)'), '#102030')
        self.assertAlmostEqual(uc.alpha_of('rgb(16 32 48 / 25%)'), 0.25)

    def test_hsl_and_hsla_modern_and_legacy(self):
        self.assertEqual(uc.parse_color('hsl(0, 100%, 50%)'), '#ff0000')
        self.assertEqual(uc.parse_color('hsl(0.5turn 100% 50% / 0.5)'), '#00ffff')
        self.assertAlmostEqual(uc.alpha_of('hsl(0.5turn 100% 50% / 0.5)'), 0.5)
        self.assertEqual(uc.parse_color('hsla(240deg, 100%, 50%, 75%)'), '#0000ff')
        self.assertAlmostEqual(uc.alpha_of('hsla(240deg, 100%, 50%, 75%)'), 0.75)

    def test_color_mix(self):
        self.assertEqual(uc.parse_color('color-mix(in srgb, #000000, #ffffff)'), '#808080')
        self.assertEqual(uc.parse_color('color-mix(in srgb, red 25%, blue)'), '#4000bf')
        mix_lab = uc.parse_color('color-mix(in oklab, black, white)')
        self.assertIsNotNone(mix_lab)
        self.assertLess(delta_e2000(mix_lab, '#636363'), 2.0)
        mix_lch = uc.parse_color('color-mix(in oklch, oklch(0.6 0.2 20), oklch(0.6 0.2 100))')
        self.assertIsNotNone(mix_lch)
        self.assertAlmostEqual(uc.alpha_of('color-mix(in oklab, black 50%, transparent)'), 0.5)


class TestTokensAndTailwindV4(unittest.TestCase):
    def test_var_chain_and_cycle_protection(self):
        css = """
        @theme inline {
          --color-card: var(--card);
          --color-deep: var(--hop1);
          --color-cycle: var(--cyc1);
        }
        :root {
          --card: var(--surface);
          --surface: oklch(0.985 0 0);
          --hop1: var(--hop2);
          --hop2: var(--hop3);
          --hop3: var(--hop4);
          --hop4: var(--hop5);
          --hop5: #123456;
          --cyc1: var(--cyc2);
          --cyc2: var(--cyc1);
        }
        """
        tok = uc.css_tokens([css])
        self.assertEqual(tok['color-card'], '#fafafa')
        self.assertEqual(tok['card'], '#fafafa')
        self.assertEqual(tok['color-deep'], '#123456')
        self.assertNotIn('color-cycle', tok)
        self.assertNotIn('cyc1', tok)

    def test_dark_data_theme_and_at_theme_colors(self):
        css = """
        @theme {
          --color-brand: oklch(0.623 0.214 259.815);
          --color-mixed: color-mix(in srgb, #000000 40%, #ffffff);
        }
        [data-theme="dark"] {
          --background: oklch(0.145 0 0);
        }
        [data-theme=dark] {
          --foreground: oklch(0.985 0 0);
        }
        """
        light = uc.css_tokens([css])
        dark = uc.css_tokens([css], r'\.dark')
        self.assertEqual(light['brand'], uc.parse_color('oklch(0.623 0.214 259.815)'))
        self.assertEqual(light['mixed'], '#999999')
        self.assertEqual(dark['background'], '#0a0a0a')
        self.assertEqual(dark['foreground'], '#fafafa')

    def test_v4_palette_detection_vs_v3_default(self):
        # Default without v4 hint keeps v3 TW palette
        self.assertEqual(uc.tw_hex('slate-500', {}), '#64748b')
        self.assertEqual(uc.tw_hex('slate-500', uc.css_tokens([':root { --bg: #fff; }'])), '#64748b')
        # With @import "tailwindcss" or @theme, uses TW4 OKLCH palette
        v4_tok = uc.css_tokens(['@import "tailwindcss";'])
        self.assertEqual(uc.tw_hex('slate-500', v4_tok), '#62748e')
        self.assertEqual(uc.tw_hex('slate-500', {}, v4=True), '#62748e')

    def test_tw_hex_arbitrary_and_parse_solid_bg(self):
        self.assertEqual(uc.tw_hex('[oklch(0.205_0_0)]', {}), '#171717')
        self.assertEqual(uc.tw_hex('[rgb(10_20_30)]', {}), '#0a141e')
        self.assertEqual(uc.tw_hex('[hsl(0_100%_50%)]', {}), '#ff0000')
        self.assertEqual(uc._parse_solid_bg('oklch(0.205 0 0)'), '#171717')
        self.assertEqual(uc._parse_solid_bg('color-mix(in srgb, #000000, #ffffff)'), '#808080')
        self.assertIsNone(uc._parse_solid_bg('oklch(0.205 0 0 / 0)'))

    def test_uitools_contrast_cli_oklch(self):
        res = subprocess.run(
            [sys.executable, str(ROOT / 'scripts' / 'uitools.py'), 'contrast', 'oklch(0.205 0 0)', 'white'],
            capture_output=True, text=True, check=True,
        )
        self.assertIn('#171717 on #ffffff', res.stdout)
        self.assertIn('AA text(4.5): PASS', res.stdout)

    def test_is_tailwind_v4_detection(self):
        self.assertTrue(uc.is_tailwind_v4(['@import "tailwindcss";']))
        self.assertTrue(uc.is_tailwind_v4(["@import 'tailwindcss';"]))
        self.assertTrue(uc.is_tailwind_v4(['@theme { --color-brand: #123456; }']))
        self.assertTrue(uc.is_tailwind_v4(['<div class="bg-olive-100 text-olive-700">x</div>']))
        self.assertTrue(uc.is_tailwind_v4(['<span class="dark:text-mist-400 ring-taupe-300">x</span>']))
        self.assertTrue(uc.is_tailwind_v4('<div class="from-olive-500 via-mist-400 to-taupe-700"></div>'))
        self.assertFalse(uc.is_tailwind_v4(['/* @import "tailwindcss"; */ .a { color: #111; }']))
        self.assertFalse(uc.is_tailwind_v4(['<div class="bg-slate-900 text-white">x</div>']))
        self.assertEqual(uc.NEUTRALS, {'slate', 'gray', 'zinc', 'neutral', 'stone'})

    def test_tw4_same_hue_and_backdrop(self):
        self.assertEqual(uc.tw_hex('olive-400', {}), '#abab9c')
        self.assertEqual(uc.tw_hex('mist-400', {}), '#9ca8ab')
        self.assertEqual(uc.tw_hex('taupe-400', {}), '#aba09c')
        self.assertEqual(uc.tw_same_hue('olive-400', '#ffffff', 4.5), 'olive-600')
        self.assertEqual(uc.tw_same_hue('mist-400', '#ffffff', 4.5), 'mist-500')
        self.assertEqual(uc.tw_same_hue('taupe-400', '#ffffff', 4.5), 'taupe-500')
        self.assertEqual(uc.tw_same_hue('indigo-400', '#ffffff', 4.5, v4=False), 'indigo-600')
        self.assertEqual(uc.tw_same_hue('indigo-400', '#ffffff', 4.5, v4=True), 'indigo-500')
        self.assertEqual(uc.tw_bg_same_hue('olive-400', '#ffffff', 4.5), 'olive-600')
        self.assertEqual(uc.tw_bg_same_hue('indigo-400', '#ffffff', 4.5, v4=False), 'indigo-600')
        self.assertEqual(uc.tw_bg_same_hue('indigo-400', '#ffffff', 4.5, v4=True), 'indigo-500')
        self.assertIsNone(uc.tw_bg_same_hue('slate-400', '#ffffff', 4.5, v4=True))
        self.assertEqual(uc.backdrop([['bg-slate-500']], '', {}, 'white', v4=False), ('#64748b', 'bg-slate-500'))
        self.assertEqual(uc.backdrop([['bg-slate-500']], '', {}, 'white', v4=True), ('#62748e', 'bg-slate-500'))
        self.assertEqual(uc.backdrop([['bg-olive-100']], '', {}, 'white', v4=True), ('#f4f4f0', 'bg-olive-100'))

    def test_uitools_contrast_cli_tw4_olive(self):
        res = subprocess.run(
            [sys.executable, str(ROOT / 'scripts' / 'uitools.py'), 'contrast', 'olive-400', 'white'],
            capture_output=True, text=True, check=True,
        )
        self.assertIn('#abab9c on #ffffff', res.stdout)
        self.assertIn('AA text(4.5): FAIL', res.stdout)
        self.assertIn('fix -> olive-600 /', res.stdout)


if __name__ == '__main__':
    unittest.main()
