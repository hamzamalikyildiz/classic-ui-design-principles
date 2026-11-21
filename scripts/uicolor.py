"""WCAG color math, Tailwind palettes, CSS token extraction, and backdrop compositing."""
import colorsys
import math
import pathlib
import re
import sys

_SCRIPTS_DIR = str(pathlib.Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from uiparse import (
    BG_PASSTHROUGH,
    _strip_at_blocks,
    _strip_css_blocks,
    pick,
    strip_css_comments,
)

__all__ = [
    'TW',
    'TW4',
    'SHADES',
    'NAMED',
    'HEX',
    'NEUTRALS',
    'hex2rgb',
    'rgb2hex',
    'lum',
    'ratio',
    'fix_color',
    'tw_hex',
    'tw_same_hue',
    'tw_bg_same_hue',
    'alpha_of',
    'blend',
    'is_gradient',
    'is_chromatic',
    'hsl2hex',
    'parse_color',
    '_parse_solid_bg',
    'inline_bg',
    'css_page_bg',
    'tailwind_config_colors',
    'css_tokens',
    'backdrop',
    '_px',
]

TW = {  # Tailwind v3 default palette, shades 50..950
    'slate': 'f8fafc f1f5f9 e2e8f0 cbd5e1 94a3b8 64748b 475569 334155 1e293b 0f172a 020617',
    'gray': 'f9fafb f3f4f6 e5e7eb d1d5db 9ca3af 6b7280 4b5563 374151 1f2937 111827 030712',
    'zinc': 'fafafa f4f4f5 e4e4e7 d4d4d8 a1a1aa 71717a 52525b 3f3f46 27272a 18181b 09090b',
    'neutral': 'fafafa f5f5f5 e5e5e5 d4d4d4 a3a3a3 737373 525252 404040 262626 171717 0a0a0a',
    'stone': 'fafaf9 f5f5f4 e7e5e4 d6d3d1 a8a29e 78716c 57534e 44403c 292524 1c1917 0c0a09',
    'red': 'fef2f2 fee2e2 fecaca fca5a5 f87171 ef4444 dc2626 b91c1c 991b1b 7f1d1d 450a0a',
    'orange': 'fff7ed ffedd5 fed7aa fdba74 fb923c f97316 ea580c c2410c 9a3412 7c2d12 431407',
    'amber': 'fffbeb fef3c7 fde68a fcd34d fbbf24 f59e0b d97706 b45309 92400e 78350f 451a03',
    'yellow': 'fefce8 fef9c3 fef08a fde047 facc15 eab308 ca8a04 a16207 854d0e 713f12 422006',
    'lime': 'f7fee7 ecfccb d9f99d bef264 a3e635 84cc16 65a30d 4d7c0f 3f6212 365314 1a2e05',
    'green': 'f0fdf4 dcfce7 bbf7d0 86efac 4ade80 22c55e 16a34a 15803d 166534 14532d 052e16',
    'emerald': 'ecfdf5 d1fae5 a7f3d0 6ee7b7 34d399 10b981 059669 047857 065f46 064e3b 022c22',
    'teal': 'f0fdfa ccfbf1 99f6e4 5eead4 2dd4bf 14b8a6 0d9488 0f766e 115e59 134e4a 042f2e',
    'cyan': 'ecfeff cffafe a5f3fc 67e8f9 22d3ee 06b6d4 0891b2 0e7490 155e75 164e63 083344',
    'sky': 'f0f9ff e0f2fe bae6fd 7dd3fc 38bdf8 0ea5e9 0284c7 0369a1 075985 0c4a6e 082f49',
    'blue': 'eff6ff dbeafe bfdbfe 93c5fd 60a5fa 3b82f6 2563eb 1d4ed8 1e40af 1e3a8a 172554',
    'indigo': 'eef2ff e0e7ff c7d2fe a5b4fc 818cf8 6366f1 4f46e5 4338ca 3730a3 312e81 1e1b4b',
    'violet': 'f5f3ff ede9fe ddd6fe c4b5fd a78bfa 8b5cf6 7c3aed 6d28d9 5b21b6 4c1d95 2e1065',
    'purple': 'faf5ff f3e8ff e9d5ff d8b4fe c084fc a855f7 9333ea 7e22ce 6b21a8 581c87 3b0764',
    'fuchsia': 'fdf4ff fae8ff f5d0fe f0abfc e879f9 d946ef c026d3 a21caf 86198f 701a75 4a044e',
    'pink': 'fdf2f8 fce7f3 fbcfe8 f9a8d4 f472b6 ec4899 db2777 be185d 9d174d 831843 500724',
    'rose': 'fff1f2 ffe4e6 fecdd3 fda4af fb7185 f43f5e e11d48 be123c 9f1239 881337 4c0519',
}

TW4 = {  # Tailwind v4 default OKLCH palette (CSS Color 4 gamut-mapped sRGB), shades 50..950
    'slate': 'f8fafc f1f5f9 e2e8f0 cad5e2 90a1b9 62748e 45556c 314158 1d293d 0f172b 020618',
    'gray': 'f9fafb f3f4f6 e5e7eb d1d5dc 99a1af 6a7282 4a5565 364153 1e2939 101828 030712',
    'zinc': 'fafafa f4f4f5 e4e4e7 d4d4d8 9f9fa9 71717b 52525c 3f3f46 27272a 18181b 09090b',
    'neutral': 'fafafa f5f5f5 e5e5e5 d4d4d4 a1a1a1 737373 525252 404040 262626 171717 0a0a0a',
    'stone': 'fafaf9 f5f5f4 e7e5e4 d6d3d1 a6a09b 79716b 57534d 44403b 292524 1c1917 0c0a09',
    'red': 'fef2f2 ffe2e2 ffcaca ffa3a4 ff6568 fb2c36 e40016 bf000f 9f0712 82181a 460809',
    'orange': 'fff7ed ffedd5 ffd7a8 ffb970 ff8b1f fc7100 ec5600 c43e00 9f2d00 7e2a0c 441306',
    'amber': 'fffbeb fef3c6 fee685 ffd237 fabc00 f69e00 da7700 b55200 953d00 7b3306 461901',
    'yellow': 'fefce8 fef9c2 fff085 ffe030 f7c900 eab300 ca8a00 a26200 874c00 733e0a 432004',
    'lime': 'f7fee7 ecfcca d8f999 bbf451 9de500 83cc00 64a300 4b7c00 3d6300 35530e 192e03',
    'green': 'f0fdf4 dcfce7 b9f8cf 7bf1a8 05df72 00c65a 00a447 00813a 016630 0d542b 032e15',
    'emerald': 'ecfdf5 d0fae5 a4f4cf 5ee9b5 00d294 00b981 009669 007857 005f46 004e3b 002c22',
    'teal': 'f0fdfa cbfbf1 96f7e4 46ecd5 00d3bd 00b9a6 009488 00776e 005f5a 0b4f4a 022f2e',
    'cyan': 'ecfeff cefafe a2f4fd 53eafd 00d1ec 00b6d4 0091b3 007491 005f78 104e64 053345',
    'sky': 'f0f9ff dff2fe b8e6fe 78d4ff 00bbfd 00a5ea 0084c7 0069a2 005986 024a70 052f4a',
    'blue': 'eff6ff dbeafe bedbff 91c5ff 56a2ff 3280ff 155dfc 1447e6 193cb8 1c398e 162456',
    'indigo': 'eef2ff e0e7ff c7d2ff a4b4ff 7d87ff 6260ff 4f39f6 432dd7 372aac 312c85 1e1a4d',
    'violet': 'f5f3ff ede9fe ddd6ff c4b4ff a686ff 8d56ff 7f22fe 7008e7 5d0ec0 4d179a 2f0d68',
    'purple': 'faf5ff f3e8ff e9d5ff d8b4ff bf7eff ab4eff 9810fa 8200d9 6e11b0 59168b 3c0366',
    'fuchsia': 'fdf4ff fae8ff f6cfff f2a9ff ec6dff e12afb c500da a600b4 8a0194 721378 4b004f',
    'pink': 'fdf2f8 fce7f3 fccee8 fda5d5 fb64b6 f6339a e30076 c2005c a2004c 861043 510424',
    'rose': 'fff1f2 ffe4e6 ffccd3 ffa3ae ff6880 ff2357 e60045 c1003a a30037 8b0836 4d0218',
    'olive': 'fbfbf9 f4f4f0 e8e8e3 d8d8d0 abab9c 7c7c67 5b5b4b 474739 2b2b22 1d1d16 0c0c09',
    'mist': 'f9fbfb f1f3f3 e3e7e8 d0d6d8 9ca8ab 67787c 4b585b 394447 22292b 161b1d 090b0c',
    'taupe': 'fbfaf9 f3f1f1 e8e4e3 d8d2d0 aba09c 7c6d67 5b4f4b 473c39 2b2422 1d1816 0c0a09',
}

SHADES = ['50', '100', '200', '300', '400', '500', '600', '700', '800', '900', '950']
NAMED = {'white': '#ffffff', 'black': '#000000'}
HEX = r'#(?:[0-9a-fA-F]{3}){1,2}\b'
NEUTRALS = {'slate', 'gray', 'zinc', 'neutral', 'stone'}


def hex2rgb(h):
    h = h.strip().lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    if len(h) != 6 or not re.fullmatch(r'[0-9a-fA-F]{6}', h):
        raise ValueError(f"invalid hex color: #{h}")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def rgb2hex(r):
    return '#%02x%02x%02x' % tuple(max(0, min(255, round(v))) for v in r)


def lum(h):
    def ch(c):
        c /= 255
        return c/12.92 if c <= 0.04045 else ((c+0.055)/1.055)**2.4
    r, g, b = hex2rgb(h)
    return 0.2126*ch(r) + 0.7152*ch(g) + 0.0722*ch(b)


def ratio(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la+0.05)/(lb+0.05)


def fix_color(fg, bg, target):
    """Shift fg lightness (keep hue) until contrast >= target."""
    r, g, b = [v/255 for v in hex2rgb(fg)]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    darker = lum(bg) > 0.18
    for i in range(101):
        nl = l - i/100 if darker else l + i/100
        nl = max(0, min(1, nl))
        c = rgb2hex([v*255 for v in colorsys.hls_to_rgb(h, nl, s)])
        if ratio(c, bg) >= target: return c
    return '#000000' if darker else '#ffffff'


_CSS_NAMED = {
    'white': '#ffffff', 'black': '#000000',
    'red': '#ff0000', 'green': '#008000', 'blue': '#0000ff',
    'yellow': '#ffff00', 'cyan': '#00ffff', 'aqua': '#00ffff',
    'magenta': '#ff00ff', 'fuchsia': '#ff00ff', 'gray': '#808080',
    'grey': '#808080', 'silver': '#c0c0c0', 'maroon': '#800000',
    'olive': '#808000', 'lime': '#00ff00', 'teal': '#008080',
    'navy': '#000080', 'purple': '#800080', 'orange': '#ffa500',
    'pink': '#ffc0cb', 'rebeccapurple': '#663399',
}


def _oklab_to_linear_srgb(L, a, b):
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ * l_ * l_, m_ * m_ * m_, s_ * s_ * s_
    return (
        +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    )


def _linear_to_srgb_ch(c):
    c = max(0.0, min(1.0, c))
    return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1.0 / 2.4)) - 0.055


def _srgb_to_linear_ch(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _srgb01_to_oklab(r, g, b):
    rl, gl, bl = _srgb_to_linear_ch(r), _srgb_to_linear_ch(g), _srgb_to_linear_ch(b)
    l = 0.4122214708 * rl + 0.5363325363 * gl + 0.0514459929 * bl
    m = 0.2119034982 * rl + 0.6806995451 * gl + 0.1073969566 * bl
    s = 0.0883024619 * rl + 0.2817188376 * gl + 0.6299787005 * bl
    l_ = math.copysign(abs(l) ** (1.0 / 3.0), l)
    m_ = math.copysign(abs(m) ** (1.0 / 3.0), m)
    s_ = math.copysign(abs(s) ** (1.0 / 3.0), s)
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def _oklch_to_srgb01(L, C, h_deg):
    """Convert OKLCH to sRGB [0..1] with binary-search chroma clipping at fixed L and h."""
    if L <= 0.0:
        return (0.0, 0.0, 0.0)
    if L >= 1.0:
        return (1.0, 1.0, 1.0)
    C = max(0.0, C)
    h_rad = math.radians(h_deg)
    cos_h, sin_h = math.cos(h_rad), math.sin(h_rad)
    r, g, b = _oklab_to_linear_srgb(L, C * cos_h, C * sin_h)
    if not (0.0 <= r <= 1.0 and 0.0 <= g <= 1.0 and 0.0 <= b <= 1.0):
        lo, hi = 0.0, C
        for _ in range(24):
            mid = (lo + hi) * 0.5
            tr, tg, tb = _oklab_to_linear_srgb(L, mid * cos_h, mid * sin_h)
            if 0.0 <= tr <= 1.0 and 0.0 <= tg <= 1.0 and 0.0 <= tb <= 1.0:
                lo = mid
            else:
                hi = mid
        r, g, b = _oklab_to_linear_srgb(L, lo * cos_h, lo * sin_h)
    return (_linear_to_srgb_ch(r), _linear_to_srgb_ch(g), _linear_to_srgb_ch(b))


def _oklab_to_srgb01(L, a, b):
    return _oklch_to_srgb01(L, math.hypot(a, b), math.degrees(math.atan2(b, a)))


def _parse_num(s, pct_scale=1.0):
    s = s.strip().lower()
    if s == 'none':
        return 0.0
    if s.endswith('%'):
        return float(s[:-1]) * pct_scale / 100.0
    return float(s)


def _parse_angle(s):
    s = s.strip().lower()
    if s == 'none':
        return 0.0
    m = re.fullmatch(r'([+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?)(deg|rad|grad|turn)?', s)
    if not m:
        raise ValueError(f"invalid angle: {s}")
    v = float(m.group(1))
    unit = m.group(2)
    if unit == 'rad':
        return math.degrees(v)
    if unit == 'grad':
        return v * 0.9
    if unit == 'turn':
        return v * 360.0
    return v


def _parse_alpha(s):
    return max(0.0, min(1.0, _parse_num(s, 1.0)))


def _split_top_level(s, sep=','):
    parts, buf, depth = [], [], 0
    for ch in s:
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        elif ch == sep and depth == 0:
            parts.append(''.join(buf).strip())
            buf = []
            continue
        buf.append(ch)
    if buf or parts:
        parts.append(''.join(buf).strip())
    return parts


def _parse_color_rgba(val, tokens=None, _depth=0):
    """Parse CSS color (hex, named, oklch, oklab, rgb/rgba, hsl/hsla, color-mix, var) -> (hex, alpha) or None."""
    if not val or _depth > 5:
        return None
    val = val.strip()
    low = val.lower()
    if low == 'transparent':
        return ('#000000', 0.0)
    if re.fullmatch(HEX, val):
        return (val, 1.0)
    if low in _CSS_NAMED:
        return (_CSS_NAMED[low], 1.0)
    if low.startswith('var(') and val.endswith(')'):
        inner = val[4:-1]
        parts = _split_top_level(inner, ',')
        m = re.fullmatch(r'--([\w-]+)', parts[0].strip())
        if m:
            if tokens and m.group(1) in tokens:
                return _parse_color_rgba(tokens[m.group(1)], tokens, _depth + 1)
            if len(parts) > 1:
                return _parse_color_rgba(','.join(parts[1:]), tokens, _depth + 1)
        return None

    m = re.fullmatch(r'(oklch|oklab|rgba?|hsla?|color-mix)\((.*)\)', val, re.I | re.S)
    if not m:
        return None
    fn, body = m.group(1).lower(), m.group(2).strip()
    try:
        if fn in ('oklch', 'oklab'):
            slash = _split_top_level(body, '/')
            if len(slash) > 2:
                return None
            comps = slash[0].split()
            if len(comps) != 3:
                return None
            alpha = _parse_alpha(slash[1]) if len(slash) == 2 else 1.0
            L = _parse_num(comps[0], 1.0)
            if fn == 'oklch':
                C = max(0.0, _parse_num(comps[1], 0.4))
                H = _parse_angle(comps[2])
                rgb01 = _oklch_to_srgb01(L, C, H)
            else:
                a = _parse_num(comps[1], 0.4)
                b = _parse_num(comps[2], 0.4)
                rgb01 = _oklab_to_srgb01(L, a, b)
            return (rgb2hex([c * 255.0 for c in rgb01]), alpha)

        if fn in ('rgb', 'rgba'):
            slash = _split_top_level(body, '/')
            if len(slash) == 2:
                comps = slash[0].split()
                alpha = _parse_alpha(slash[1])
            elif ',' in body:
                comps = _split_top_level(body, ',')
                if len(comps) == 4:
                    alpha = _parse_alpha(comps[3])
                    comps = comps[:3]
                else:
                    alpha = 1.0
            else:
                comps = body.split()
                alpha = 1.0
            if len(comps) != 3:
                return None
            rgb = [max(0.0, min(255.0, _parse_num(c, 255.0))) for c in comps]
            return (rgb2hex(rgb), alpha)

        if fn in ('hsl', 'hsla'):
            slash = _split_top_level(body, '/')
            if len(slash) == 2:
                comps = slash[0].split()
                alpha = _parse_alpha(slash[1])
            elif ',' in body:
                comps = _split_top_level(body, ',')
                if len(comps) == 4:
                    alpha = _parse_alpha(comps[3])
                    comps = comps[:3]
                else:
                    alpha = 1.0
            else:
                comps = body.split()
                alpha = 1.0
            if len(comps) != 3:
                return None
            h = _parse_angle(comps[0]) % 360.0
            s = max(0.0, min(100.0, _parse_num(comps[1], 100.0)))
            l = max(0.0, min(100.0, _parse_num(comps[2], 100.0)))
            r, g, b = colorsys.hls_to_rgb(h / 360.0, l / 100.0, s / 100.0)
            return (rgb2hex([r * 255.0, g * 255.0, b * 255.0]), alpha)

        if fn == 'color-mix':
            args = _split_top_level(body, ',')
            if len(args) != 3:
                return None
            sm = re.fullmatch(r'in\s+(oklab|oklch|srgb|srgb-linear)(?:\s+(shorter|longer|increasing|decreasing)\s+hue)?', args[0], re.I)
            if not sm:
                return None
            space = sm.group(1).lower()
            hue_mode = (sm.group(2) or 'shorter').lower()

            def _parse_mix_arg(arg):
                pct = None
                m_end = re.search(r'\s+([\d.]+)%\s*$', arg)
                m_start = re.match(r'^([\d.]+)%\s+', arg)
                if m_end and arg[:m_end.start()].count('(') == arg[:m_end.start()].count(')'):
                    pct = float(m_end.group(1))
                    c_str = arg[:m_end.start()].strip()
                elif m_start:
                    pct = float(m_start.group(1))
                    c_str = arg[m_start.end():].strip()
                else:
                    c_str = arg.strip()
                parsed = _parse_color_rgba(c_str, tokens, _depth + 1)
                return parsed, pct

            c1, p1 = _parse_mix_arg(args[1])
            c2, p2 = _parse_mix_arg(args[2])
            if not c1 or not c2:
                return None
            if p1 is None and p2 is None:
                p1, p2 = 50.0, 50.0
            elif p1 is None:
                p1 = 100.0 - p2
            elif p2 is None:
                p2 = 100.0 - p1
            total = p1 + p2
            if total <= 0.0:
                return None
            a_mult = min(1.0, total / 100.0)
            w1, w2 = p1 / total, p2 / total
            (hx1, a1), (hx2, a2) = c1, c2
            a_mix = (w1 * a1 + w2 * a2)
            if a_mix <= 0.0:
                return ('#000000', 0.0)
            rgb1 = [v / 255.0 for v in hex2rgb(hx1)]
            rgb2 = [v / 255.0 for v in hex2rgb(hx2)]
            if space == 'srgb':
                out01 = [(w1 * a1 * x + w2 * a2 * y) / a_mix for x, y in zip(rgb1, rgb2)]
            elif space == 'srgb-linear':
                lin1 = [_srgb_to_linear_ch(x) for x in rgb1]
                lin2 = [_srgb_to_linear_ch(x) for x in rgb2]
                out01 = [_linear_to_srgb_ch((w1 * a1 * x + w2 * a2 * y) / a_mix) for x, y in zip(lin1, lin2)]
            elif space == 'oklab':
                lab1, lab2 = _srgb01_to_oklab(*rgb1), _srgb01_to_oklab(*rgb2)
                L = (w1 * a1 * lab1[0] + w2 * a2 * lab2[0]) / a_mix
                a = (w1 * a1 * lab1[1] + w2 * a2 * lab2[1]) / a_mix
                b = (w1 * a1 * lab1[2] + w2 * a2 * lab2[2]) / a_mix
                out01 = _oklab_to_srgb01(L, a, b)
            else:  # oklch
                lab1, lab2 = _srgb01_to_oklab(*rgb1), _srgb01_to_oklab(*rgb2)
                C1, C2 = math.hypot(lab1[1], lab1[2]), math.hypot(lab2[1], lab2[2])
                H1 = math.degrees(math.atan2(lab1[2], lab1[1])) % 360.0
                H2 = math.degrees(math.atan2(lab2[2], lab2[1])) % 360.0
                if C1 < 1e-6:
                    H1 = H2
                elif C2 < 1e-6:
                    H2 = H1
                diff = H2 - H1
                if hue_mode == 'shorter':
                    diff = (diff + 180.0) % 360.0 - 180.0
                elif hue_mode == 'longer':
                    if 0 < diff < 180.0:
                        diff -= 360.0
                    elif -180.0 < diff <= 0.0:
                        diff += 360.0
                elif hue_mode == 'increasing' and diff < 0.0:
                    diff += 360.0
                elif hue_mode == 'decreasing' and diff > 0.0:
                    diff -= 360.0
                L = (w1 * a1 * lab1[0] + w2 * a2 * lab2[0]) / a_mix
                C = (w1 * a1 * C1 + w2 * a2 * C2) / a_mix
                H = (H1 + w2 * diff) % 360.0
                out01 = _oklch_to_srgb01(L, C, H)
            return (rgb2hex([c * 255.0 for c in out01]), a_mix * a_mult)
    except (ValueError, ZeroDivisionError):
        return None
    return None


def parse_color(val, tokens=None):
    """Parse a CSS color value (hex, named, oklch, oklab, rgb, hsl, color-mix) -> '#rrggbb' or None."""
    if not val or val.strip().lower() == 'transparent':
        return None
    res = _parse_color_rgba(val, tokens)
    return res[0] if res else None


_COLOR_FN_RE = re.compile(r'^(?:oklch|oklab|rgba?|hsla?|color-mix)\(', re.I)


def _strip_tw_alpha(name):
    if name.startswith('['):
        return re.sub(r'\]/\d{1,3}$', ']', name)
    if _COLOR_FN_RE.match(name):
        return name
    return name.split('/')[0]


def tw_hex(name, tokens, v4=False):
    """Resolve 'slate-400', 'white', '[#abc]', '[oklch(...)]', 'oklch(...)' or a token to hex."""
    name = _strip_tw_alpha(name)
    m = re.fullmatch(r'\[(#[0-9a-fA-F]{3}|#[0-9a-fA-F]{6})\]', name)
    if m:
        return m.group(1)
    if name.startswith('[') and name.endswith(']'):
        inner = name[1:-1].strip().replace('_', ' ')
        if re.fullmatch(HEX, inner):
            return inner
        if inner in NAMED:
            return NAMED[inner]
        if _COLOR_FN_RE.match(inner):
            return parse_color(inner, tokens)
        return None
    if re.fullmatch(HEX, name):
        return name
    if name in NAMED:
        return NAMED[name]
    if tokens and name in tokens:
        return tokens[name]
    palette = TW4 if v4 else TW
    m = re.fullmatch(r'([a-z]+)-(\d{2,3})', name)
    if m and m.group(1) in palette and m.group(2) in SHADES:
        return '#' + palette[m.group(1)].split()[SHADES.index(m.group(2))]
    if _COLOR_FN_RE.match(name):
        return parse_color(name, tokens)
    return None


def tw_same_hue(name, bg_hex, need):
    """Nearest shade of the same Tailwind hue that reaches `need` on bg (e.g. pink-400 -> pink-700)."""
    m = re.fullmatch(r'([a-z]+)-(\d{2,3})', _strip_tw_alpha(name))
    if not m or m.group(1) not in TW or m.group(2) not in SHADES:
        return None
    hexes = TW[m.group(1)].split()
    i = SHADES.index(m.group(2))
    step = 1 if lum(bg_hex) > 0.18 else -1
    j = i
    while 0 <= j < len(SHADES):
        if ratio('#' + hexes[j], bg_hex) >= need:
            return f"{m.group(1)}-{SHADES[j]}"
        j += step
    return None


def alpha_of(name):
    if not name.endswith((')', ']')):
        m = re.search(r'/(\d{1,3})$', name)
        if m:
            return min(int(m.group(1)), 100) / 100
    inner = name[1:-1].strip().replace('_', ' ') if name.startswith('[') and name.endswith(']') else name
    if '(' in inner:
        res = _parse_color_rgba(inner)
        if res:
            return res[1]
    return 1.0


def blend(top, bottom, a):
    t, b = hex2rgb(top), hex2rgb(bottom)
    return rgb2hex([a * x + (1 - a) * y for x, y in zip(t, b)])


def is_gradient(c):
    return c.startswith(('bg-gradient', 'bg-linear-', 'bg-radial', 'bg-conic'))


def _parse_solid_bg(val, tokens=None):
    val = re.sub(r'\s*!important\s*$', '', val.strip(), flags=re.I).strip()
    if not val or re.search(r'(?:gradient|url)\s*\(', val, re.I):
        return None
    if val.lower() in ('transparent', 'inherit', 'currentcolor', 'none'):
        return None
    if re.fullmatch(HEX, val):
        return val
    if val.lower() in NAMED:
        return NAMED[val.lower()]
    m = re.fullmatch(r'var\(\s*--([\w-]+)(?:\s*,\s*([^)]+))?\s*\)', val)
    if m:
        if tokens and m.group(1) in tokens:
            return tokens[m.group(1)]
        if m.group(2):
            return _parse_solid_bg(m.group(2), tokens)
    res = _parse_color_rgba(val, tokens)
    if res:
        return None if res[1] <= 0.0 else res[0]
    return 'UNKNOWN'


def inline_bg(attrs, tokens=None):
    """Return solid hex from inline style='background...', 'GRADIENT'/'UNKNOWN', or None."""
    m = re.search(r"""(?<![\w-])style\s*=\s*(?:"([^"]*)"|'([^']*)')""", attrs, re.I)
    if not m:
        return None
    style = strip_css_comments(m.group(1) or m.group(2) or '')
    found = None
    for dm in re.finditer(r'(?<![\w-])background(?:-color)?\s*:\s*([^;]+)', style, re.I):
        val = dm.group(1).strip()
        if re.search(r'(?:gradient|url)\s*\(', val, re.I):
            return 'GRADIENT'
        bg = _parse_solid_bg(val, tokens)
        if bg:
            found = bg
    return found


def css_page_bg(txt, tokens=None):
    """Resolve solid background color from top-level body (preferred) or html rules in <style> or CSS files."""
    styles = re.findall(r'<style\b[^>]*>(.*?)</style>', txt, re.S | re.I)
    if styles:
        css_src = '\n'.join(styles)
    elif re.search(r'<(?:html|head|body|div|main|section|p|span)\b', txt, re.I):
        return None
    else:
        css_src = txt
    css_src = _strip_at_blocks(strip_css_comments(css_src))
    body_bg = html_bg = None
    for m in re.finditer(r'(?:^|(?<=[};{}]))\s*([^{};]+?)\s*\{([^{}]*)\}', css_src):
        sels = {s.strip().lower() for s in m.group(1).split(',')}
        if not (sels & {'body', 'html'}):
            continue
        for dm in re.finditer(r'(?<![\w-])background(?:-color)?\s*:\s*([^;]+)', m.group(2), re.I):
            bg = _parse_solid_bg(dm.group(1), tokens)
            if bg and bg != 'UNKNOWN':
                if 'body' in sels:
                    body_bg = bg
                if 'html' in sels:
                    html_bg = bg
    return body_bg or html_bg


def backdrop(chain, variant, tokens, page_bg, styles=None):
    """Effective background behind an element: (hex, label) or None if unknown.

    Walks from the element outward, compositing semi-transparent layers (bg-white/10)
    until an opaque one. In a variant pass (dark:) a layer without a dark: class keeps its
    base class. Gradients, images and unresolvable colors make the backdrop unknown.
    """
    layers = []
    for idx, cls in enumerate(chain):
        has_var_bg = bool(variant and pick(cls, 'bg', variant))
        if styles and idx < len(styles) and not has_var_bg:
            ib = inline_bg(styles[idx], tokens)
            if ib in ('GRADIENT', 'UNKNOWN'):
                return None
            if ib:
                layers.append((ib, 1.0, f"[{ib}]"))
                break
        b = (pick(cls, 'bg', variant) if variant else None) or pick(cls, 'bg')
        grad = any(is_gradient(c) or c.startswith('bg-[url') for c in cls if ':' not in c)
        if has_var_bg:
            grad = False  # dark: color overrides a light gradient
        if grad:
            return None
        if not b or b in BG_PASSTHROUGH:
            continue
        h = tw_hex(b, tokens)
        if not h:
            return None
        layers.append((h, alpha_of(b), b))
        if alpha_of(b) >= 1:
            break
    else:
        if not page_bg:
            return None
        h = tw_hex(page_bg, tokens)
        if not h:
            return None
        layers.append((h, 1.0, page_bg))
    color = layers[-1][0]
    for h, a, _ in reversed(layers[:-1]):
        color = blend(h, color, a)
    name = ' over '.join(f"bg-{n}" for _, _, n in layers)
    return color, name


def tw_bg_same_hue(bg_name, fg_hex, need):
    """For white/black/neutral text on a colored background: the nearest bg shade of the same hue that passes."""
    m = re.fullmatch(r'([a-z]+)-(\d{2,3})', bg_name.split('/')[0])
    if not m or m.group(1) not in TW or m.group(1) in NEUTRALS or m.group(2) not in SHADES:
        return None
    hexes = TW[m.group(1)].split()
    i = SHADES.index(m.group(2))
    step = 1 if lum(fg_hex) > 0.18 else -1  # light text -> darker background
    j = i
    while 0 <= j < len(SHADES):
        if ratio(fg_hex, '#' + hexes[j]) >= need:
            return f"{m.group(1)}-{SHADES[j]}"
        j += step
    return None


def hsl2hex(h, s, l):
    r, g, b = colorsys.hls_to_rgb(h / 360, l / 100, s / 100)
    return rgb2hex([r * 255, g * 255, b * 255])


def _resolve_css_value(val, raw_vars, depth=0, seen=None):
    """Resolve a CSS color value or var(--x) chain (max 5 hops, cycle-safe) -> '#rrggbb' or None."""
    if not val or depth > 5:
        return None
    val = val.strip()
    seen = set() if seen is None else seen

    if val.lower().startswith('var(') and val.endswith(')'):
        parts = _split_top_level(val[4:-1], ',')
        m = re.fullmatch(r'--([\w-]+)', parts[0].strip())
        if not m:
            return None
        vname = m.group(1)
        if vname in seen:
            return None
        nxt_seen = seen | {vname}
        if vname in raw_vars:
            res = _resolve_css_value(raw_vars[vname], raw_vars, depth + 1, nxt_seen)
            if res:
                return res
        if len(parts) > 1:
            return _resolve_css_value(','.join(parts[1:]), raw_vars, depth + 1, nxt_seen)
        return None

    if 'var(' in val.lower() and raw_vars:
        # Substitute embedded var(--x) inside color-mix(...) etc.
        def _sub(m):
            vn = m.group(1)
            if vn in seen or vn not in raw_vars:
                return m.group(0)
            resolved = _resolve_css_value(raw_vars[vn], raw_vars, depth + 1, seen | {vn})
            return resolved or m.group(0)
        val = re.sub(r'var\(\s*--([\w-]+)\s*\)', _sub, val)

    m = re.fullmatch(r'(-?[\d.]+)(?:deg)?\s+([\d.]+)%\s+([\d.]+)%', val)
    if m:
        return hsl2hex(*map(float, m.groups()))
    if re.fullmatch(HEX, val):
        return val
    return parse_color(val)


def _extract_css_vars(blk):
    return [(n, v.strip()) for n, v in re.findall(r'--([\w-]+)\s*:\s*([^;{}]+?)\s*(?:;|(?=\}))', blk)]


def tailwind_config_colors(txt):
    """Custom colors from an inline `tailwind.config = {... colors: {ink:'#123', brand:{500:'#abc'}}}` and v4 `@theme { --color-x: ... }`."""
    out = {}
    light_css = _strip_css_blocks(strip_css_comments(txt), r'\.dark|\[data-theme\s*=\s*[\'"]?dark[\'"]?\]')
    raw_vars = dict(_extract_css_vars(light_css))
    for name, val in _extract_css_vars(light_css):
        if not name.startswith('color-'):
            continue
        hx = _resolve_css_value(val, raw_vars)
        if hx:
            out[name[6:]] = hx
    for m in re.finditer(r'\bcolors\s*:\s*\{', txt):
        i, depth, j = m.end(), 1, m.end()
        while j < len(txt) and depth:
            ch = txt[j]
            if txt[j:j+2] == '//':
                nl = txt.find('\n', j)
                j = len(txt) if nl == -1 else nl + 1
                continue
            if txt[j:j+2] == '/*':
                end = txt.find('*/', j + 2)
                j = len(txt) if end == -1 else end + 2
                continue
            if ch in ('"', "'", '`'):
                q = ch
                j += 1
                while j < len(txt) and txt[j] != q:
                    if txt[j] == '\\':
                        j += 1
                    j += 1
                j += 1
                continue
            depth += (ch == '{') - (ch == '}')
            j += 1
        body = txt[i:j - 1]
        path = []
        pat = r"""//[^\n]*|/\*[\s\S]*?\*/|(?P<key>['"]?[\w-]+['"]?)\s*:\s*(?:(?P<open>\{)|['"](?P<val>#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}))['"])|(?P<close>\})"""
        for t in re.finditer(pat, body):
            if t.group('close'):
                if path:
                    path.pop()
            elif t.group('open'):
                path.append(t.group('key').strip('\'"'))
            elif t.group('val'):
                name = '-'.join(path + [t.group('key').strip('\'"')])
                name = name[:-8] if name.endswith('-DEFAULT') else name
                out[name] = t.group('val')
    return out


def css_tokens(texts, selector=r':root'):
    """CSS custom properties from `selector` (and `@theme` for light, `[data-theme=dark]` for dark) -> {name: hex}."""
    tok = {}
    is_light = selector == r':root'
    is_dark = selector == r'\.dark'
    has_v4 = any(re.search(r'@import\s+[\'"]tailwindcss[\'"]|@theme\b', raw, re.I) for raw in texts)
    if is_light and has_v4:
        for hue, row in TW4.items():
            for shade, hx in zip(SHADES, row.split()):
                tok[f"{hue}-{shade}"] = '#' + hx

    sel_pat = (
        r'(?::root|@theme(?:\s+inline)?)' if is_light
        else r'(?:\.dark|\[data-theme\s*=\s*[\'"]?dark[\'"]?\])' if is_dark
        else selector
    )

    light_raw = {}
    target_entries = []
    for raw in texts:
        txt = strip_css_comments(raw)
        if is_light:
            tok.update(tailwind_config_colors(raw))
        for blk in re.findall(r'(?::root|@theme(?:\s+inline)?)\s*\{([^}]*)\}', txt):
            for n, v in _extract_css_vars(blk):
                light_raw[n] = v
        for blk in re.findall(sel_pat + r'\s*\{([^}]*)\}', txt):
            target_entries.extend(_extract_css_vars(blk))

    scope_vars = {**light_raw, **dict(target_entries)} if not is_light else light_raw
    for name, val in target_entries:
        hx = _resolve_css_value(val, scope_vars)
        if hx:
            tok[name] = hx
    return tok


def is_chromatic(h):
    """True if hex color has noticeable chroma (excludes black, white, greys, and warm off-whites)."""
    try:
        r, g, b = [v / 255 for v in hex2rgb(h)]
    except ValueError:
        return False
    _, _, s = colorsys.rgb_to_hls(r, g, b)
    return (max(r, g, b) - min(r, g, b)) >= 0.18 and s >= 0.25


def _px(v, unit):
    return v * 16 if unit == 'rem' else v
