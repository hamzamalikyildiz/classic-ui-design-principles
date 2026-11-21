"""WCAG color math, Tailwind palettes, CSS token extraction, and backdrop compositing."""
import colorsys
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


def tw_hex(name, tokens):
    """Resolve 'slate-400', 'white', '[#abc]' or a shadcn token like 'primary' to hex."""
    name = name.split('/')[0]
    m = re.fullmatch(r'\[(#[0-9a-fA-F]{3}|#[0-9a-fA-F]{6})\]', name)
    if m:
        return m.group(1)
    if re.fullmatch(HEX, name):
        return name
    if name in NAMED:
        return NAMED[name]
    m = re.fullmatch(r'([a-z]+)-(\d{2,3})', name)
    if m and m.group(1) in TW and m.group(2) in SHADES:
        return '#' + TW[m.group(1)].split()[SHADES.index(m.group(2))]
    return tokens.get(name)


def tw_same_hue(name, bg_hex, need):
    """Nearest shade of the same Tailwind hue that reaches `need` on bg (e.g. pink-400 -> pink-700)."""
    m = re.fullmatch(r'([a-z]+)-(\d{2,3})', name.split('/')[0])
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
    m = re.search(r'/(\d{1,3})$', name)
    return min(int(m.group(1)), 100) / 100 if m else 1.0


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


def tailwind_config_colors(txt):
    """Custom colors from an inline `tailwind.config = {... colors: {ink:'#123', brand:{500:'#abc'}}}` and v4 `@theme { --color-x: #abc }`."""
    out = {}
    light_css = _strip_css_blocks(strip_css_comments(txt), r'\.dark')
    for m in re.finditer(r'--color-([\w-]+)\s*:\s*(' + HEX + r')', light_css):
        out[m.group(1)] = m.group(2)
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
    """CSS custom properties from `selector` blocks (shadcn v3 'H S% L%', hsl() or hex) -> {name: hex}."""
    tok = {}
    for raw in texts:
        txt = strip_css_comments(raw)
        if selector == r':root':
            tok.update(tailwind_config_colors(raw))
        for blk in re.findall(selector + r'\s*\{([^}]*)\}', txt):
            for name, val in re.findall(r'--([\w-]+)\s*:\s*([^;]+);', blk):
                val = val.strip()
                m = (re.fullmatch(r'(-?[\d.]+)(?:deg)?\s+([\d.]+)%\s+([\d.]+)%', val) or
                     re.fullmatch(r'hsl\(\s*(-?[\d.]+)(?:deg)?[\s,]+([\d.]+)%[\s,]+([\d.]+)%\s*\)', val))
                if m:
                    tok[name] = hsl2hex(*map(float, m.groups()))
                elif re.fullmatch(HEX, val):
                    tok[name] = val
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
