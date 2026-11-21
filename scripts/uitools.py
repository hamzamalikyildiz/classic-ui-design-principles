#!/usr/bin/env python3
"""UI design rule toolkit: contrast, type scale, nested radius, spacing snap, audit."""
import re, sys, argparse, colorsys, pathlib

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

def cmd_contrast(a):
    name = a.fg
    a.fg = tw_hex(a.fg, {}) or a.fg; a.bg = tw_hex(a.bg, {}) or a.bg
    try:
        hex2rgb(a.fg)
        hex2rgb(a.bg)
    except ValueError as e:
        sys.exit(f"error: {e}")
    r = ratio(a.fg, a.bg)
    out = f"{a.fg} on {a.bg}: {r:.2f}:1 | AA text(4.5): {'PASS' if r>=4.5 else 'FAIL'} | AA large/UI(3.0): {'PASS' if r>=3 else 'FAIL'}"
    print(out)
    if r < a.target:
        tw = tw_same_hue(name, a.bg, a.target)
        fixed = fix_color(a.fg, a.bg, a.target)
        note = f">= {a.target}:1" if ratio(fixed, a.bg) >= a.target else "best possible"
        print(f"  fix -> {tw + ' / ' if tw else ''}{fixed} ({note}, same hue)")

RATIOS = {'minor-second':1.067,'major-second':1.125,'minor-third':1.2,'major-third':1.25,
          'perfect-fourth':1.333,'augmented-fourth':1.414,'perfect-fifth':1.5,'golden':1.618}

def cmd_scale(a):
    if a.ratio in RATIOS:
        rt = RATIOS[a.ratio]
    else:
        try:
            rt = float(a.ratio)
        except ValueError:
            sys.exit(f"error: unknown ratio: {a.ratio}")
    if not (0 < rt < float('inf')):
        sys.exit(f"error: --ratio must be > 0 (got {rt})")
    names = ['xs','sm','base','lg','xl','2xl','3xl','4xl','5xl']
    steps = range(-2, 7)
    print(f"/* type scale base={a.base}px ratio={rt} */\n:root {{")
    rows = []
    for n, s in zip(names, steps):
        px = a.base * rt**s
        px4 = max(4, round(px/ (2 if px < 24 else 4)) * (2 if px < 24 else 4))
        px4 = max(px4, {'xs': 12, 'sm': 14}.get(n, 0))  # never shrink Tailwind's small sizes below readable floors
        lh = round((px4 * (1.6 if px4 <= 18 else 1.4 if px4 <= 24 else 1.25 if px4 <= 40 else 1.1)) / 4) * 4
        rows.append((n, px4, lh))
        print(f"  --text-{n}: {px4/16:.4g}rem; --leading-{n}: {lh/16:.4g}rem; /* {px4}px / {lh}px */")
    print("}\n/* tailwind.config theme.extend.fontSize */\nfontSize: {")
    for n, px, lh in rows:
        print(f"  '{n}': ['{px/16:.4g}rem', {{ lineHeight: '{lh/16:.4g}rem' }}],")
    print("}")

def cmd_radius(a):
    inner = max(0, a.outer - a.padding)
    print(f"outer={a.outer}px padding={a.padding}px -> inner radius = {inner}px")
    if inner == 0: print("  note: padding >= radius, inner element should be square (0) or use small 2-4px")

def cmd_snap(a):
    if a.grid <= 0:
        sys.exit(f"error: --grid must be > 0 (got {a.grid})")
    for v in a.values:
        g = a.grid
        print(f"{v}px -> {round(v/g)*g}px (grid {g})")

# ---------------- audit ----------------
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


NEUTRALS = {'slate', 'gray', 'zinc', 'neutral', 'stone'}


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


def strip_css_comments(txt):
    """Replace /* ... */ CSS comments with spaces, preserving newline count."""
    return re.sub(r'/\*.*?\*/', lambda m: re.sub(r'[^\n]', ' ', m.group(0)), txt, flags=re.S)


def _parse_solid_bg(val, tokens=None):
    val = re.sub(r'\s*!important\s*$', '', val.strip(), flags=re.I).strip()
    if not val or re.search(r'(?:gradient|url)\s*\(', val, re.I):
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
    return None


def inline_bg(attrs):
    """Return solid hex from inline style='background...', 'GRADIENT' for gradients/urls, or None."""
    m = re.search(r"""(?<![\w-])style\s*=\s*(?:"([^"]*)"|'([^']*)')""", attrs, re.I)
    if not m:
        return None
    style = strip_css_comments(m.group(1) or m.group(2) or '')
    found = None
    for dm in re.finditer(r'(?<![\w-])background(?:-color)?\s*:\s*([^;]+)', style, re.I):
        val = dm.group(1).strip()
        if re.search(r'(?:gradient|url)\s*\(', val, re.I):
            return 'GRADIENT'
        bg = _parse_solid_bg(val)
        if bg:
            found = bg
    return found


def css_page_bg(txt, tokens=None):
    """Resolve solid background color from body (preferred) or html rules in <style> or CSS files."""
    styles = re.findall(r'<style\b[^>]*>(.*?)</style>', txt, re.S | re.I)
    if styles:
        css_src = '\n'.join(styles)
    elif re.search(r'<(?:html|head|body|div|main|section|p|span)\b', txt, re.I):
        return None
    else:
        css_src = txt
    css_src = strip_css_comments(css_src)
    body_bg = html_bg = None
    for m in re.finditer(r'(?:^|(?<=[};{}]))\s*([^{};]+?)\s*\{([^{}]*)\}', css_src):
        sels = {s.strip().lower() for s in m.group(1).split(',')}
        if not (sels & {'body', 'html'}):
            continue
        for dm in re.finditer(r'(?<![\w-])background(?:-color)?\s*:\s*([^;]+)', m.group(2), re.I):
            bg = _parse_solid_bg(dm.group(1), tokens)
            if bg:
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
            ib = inline_bg(styles[idx])
            if ib == 'GRADIENT':
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


def _strip_css_blocks(txt, selector_pat):
    out, i = [], 0
    for m in re.finditer(selector_pat + r'\s*\{', txt):
        if m.start() < i:
            continue
        out.append(txt[i:m.start()])
        j, depth = m.end(), 1
        while j < len(txt) and depth:
            depth += (txt[j] == '{') - (txt[j] == '}')
            j += 1
        i = j
    out.append(txt[i:])
    return ''.join(out)


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


SPACE_PROPS = r'(?:margin|padding|gap|row-gap|column-gap|inset)(?:-[a-z]+)?'
TW_SPACE = re.compile(r'(?<![\w:\[-])-?(?:p|px|py|pt|pr|pb|pl|ps|pe|m|mx|my|mt|mr|mb|ml|ms|me|gap|gap-x|gap-y|space-x|space-y|inset)-(\[[^\]]+\]|[\d.]+)(?![\w.])')
TAG = re.compile(r"""(</|(?<![A-Za-z0-9_$])<)([A-Za-z][\w.]*)((?:[^>{}"']|"[^"]*"|'[^']*'|\{(?:[^{}]|\{[^{}]*\})*\})*?)(/?)>""")
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'}
READABLE_MAXW = re.compile(r'(?<![\w:-])max-w-(?:prose|xs|sm|md|lg|xl|2xl|\[(?:[4-7]\d|80)ch\])(?![\w-])|max-width\s*:\s*(?:[4-7]\d|80)ch')
BIG_TEXT = {'text-2xl', 'text-3xl', 'text-4xl', 'text-5xl', 'text-6xl', 'text-7xl', 'text-8xl', 'text-9xl'}
BOLD = {'font-semibold', 'font-bold', 'font-extrabold', 'font-black'}
BLOCK = re.compile(r'^(?:section|article|form|dialog|header|main|aside|Card|DialogContent|SheetContent|AlertDialogContent)$')
BG_NON_COLOR = re.compile(r'(?:auto|cover|contain|fixed|local|scroll|center|top|bottom|left|right|(?:left|right)-(?:top|bottom)|'
                          r'repeat|no-repeat|repeat-[xy]|repeat-round|repeat-space|none|clip-\w+|origin-\w+|blend-[\w-]+|opacity-\d+|'
                          r'\[length:[^\]]+\]|\[position:[^\]]+\]|size-[\w-]+)')
BG_PASSTHROUGH = {'transparent', 'inherit', 'current'}
TEXT_NON_COLOR = re.compile(r'(?:xs|sm|base|lg|\d?xl|left|right|center|justify|start|end|wrap|nowrap|balance|pretty|ellipsis|clip|'
                            r'\[\d.*\]|opacity-\d+|shadow(?:-[\w-]+)?|\[length:[^\]]+\])')


def mask_non_markup(txt):
    """Replace HTML/JSX comments, <script>, and <style> blocks with spaces while preserving newlines and indices."""
    pat = r'<!--.*?-->|\{/\*.*?\*/\}|<script\b[^>]*>.*?</script>|<style\b[^>]*>.*?</style>'
    return re.sub(pat, lambda m: re.sub(r'[^\n]', ' ', m.group(0)), txt, flags=re.S | re.I)


def classes(attrs):
    m = re.search(r"""(?<![\w-])class(?:Name)?\s*=\s*("[^"]*"|'[^']*'|\{(?:[^{}]|\{[^{}]*\})*\})""", attrs)
    if not m:
        return []
    v = m.group(1)
    if v.startswith('{'):
        parts = []
        for dq, sq, tpl in re.findall(r'"([^"]*)"|\'([^\']*)\'|`([^`]*)`', v):
            if tpl:
                parts.append(re.sub(r'\$\{[^{}]*\}', ' ', tpl))
            else:
                parts.append(dq or sq)
        return ' '.join(parts).split()
    return v[1:-1].split()


def walk(txt):
    """Yield (tag, attrs, classes, ancestors, start, end) for every opening tag; ancestors innermost-last."""
    stack = []
    for m in TAG.finditer(txt):
        close, tag, attrs, selfclose = m.groups()
        if close == '</':
            for i in range(len(stack) - 1, -1, -1):
                if stack[i][0].lower() == tag.lower():
                    del stack[i:]
                    break
            continue
        node = (tag, attrs, classes(attrs), m.start())
        yield tag, attrs, node[2], list(stack), m.start(), m.end()
        if not selfclose and tag.lower() not in VOID:
            stack.append(node)


def pick(cls, prefix, variant=''):
    """Last color utility for prefix ('text'/'bg'), optionally under a variant like 'dark:'."""
    found = None
    for c in cls:
        if variant:
            if not c.startswith(variant):
                continue
            c = c[len(variant):]
        elif ':' in c:
            continue
        if c.startswith(prefix + '-'):
            val = c[len(prefix) + 1:]
            if prefix == 'text' and TEXT_NON_COLOR.fullmatch(val):
                continue
            if prefix == 'bg' and BG_NON_COLOR.fullmatch(val):
                continue
            found = val
    return found


RADIUS = {'rounded-none': 0, 'rounded-sm': 2, 'rounded': 4, 'rounded-md': 6, 'rounded-lg': 8,
          'rounded-xl': 12, 'rounded-2xl': 16, 'rounded-3xl': 24}
RADIUS_NAME = {v: k for k, v in RADIUS.items()}


def radius_px(cls):
    r = None
    for c in cls:
        if c in RADIUS:
            r = RADIUS[c]
        m = re.fullmatch(r'rounded-\[(\d+)px\]', c)
        if m:
            r = int(m.group(1))
    return r


def padding_px(cls):
    """Uniform padding in px from p-N or p-[Npx]; None if absent."""
    p = None
    for c in cls:
        m = re.fullmatch(r'p-(\d+(?:\.\d+)?)', c)
        if m:
            p = float(m.group(1)) * 4
        m = re.fullmatch(r'p-\[(\d+)px\]', c)
        if m:
            p = float(m.group(1))
    return int(p) if p is not None else None


HUE_CLASS = re.compile(r'(?<![\w-])(?:[a-z]+:)*(?:bg|text|from|via|to|border|fill|stroke|ring)-([a-z]+)-(?:50|[1-9]00|950)(?![\w-])')
CARD_RADIUS = re.compile(r'^rounded-(?:lg|xl|2xl|3xl|\[\d+px\])$')
SIZE_CLASS = re.compile(r'^text-(xs|sm|base|lg|\d?xl)$')


def height_px(cls):
    h = None
    for c in cls:
        m = re.fullmatch(r'h-(\d+(?:\.\d+)?)', c)
        if m:
            h = float(m.group(1)) * 4
        m = re.fullmatch(r'h-\[(\d+)px\]', c)
        if m:
            h = float(m.group(1))
    return h


DARK_NEUTRAL = re.compile(r'(?:slate|gray|zinc|neutral|stone)-(?:[6-9]00|950)|black')


def is_dark_page(txt, tokens=None):
    """True when the page base is a dark neutral (body/html/main/root wrapper), so dark neutral buttons are surfaces, not CTAs."""
    tokens = tokens or {}
    cbg = css_page_bg(txt, tokens)
    if cbg and lum(cbg) < 0.18:
        return True
    for m in re.finditer(r'<(?:body|html|main)\b([^>]*)>', mask_non_markup(txt), re.I):
        attrs = m.group(1)
        ib = inline_bg(attrs)
        if ib and ib != 'GRADIENT' and lum(ib) < 0.18:
            return True
        b = pick(classes(attrs), 'bg')
        if b and b not in BG_PASSTHROUGH:
            h = tw_hex(b, tokens)
            if h and lum(h) < 0.18:
                return True
    return False


def is_solid_cta(tag, attrs, cls, dark_page=False):
    if tag in ('button', 'a'):
        bg = pick(cls, 'bg')
        if dark_page and bg and DARK_NEUTRAL.fullmatch(bg):
            return False  # dark neutral on a dark page is a secondary surface
        return bool(bg) and (bg in ('primary', 'destructive') or
                             bool(re.fullmatch(r'\[(#[0-9a-fA-F]{3}|#[0-9a-fA-F]{6})\]', bg)) or
                             bool(re.fullmatch(r'[a-z]+-(?:[5-9]00|950)', bg))) or any(is_gradient(c) for c in cls)
    if tag == 'Button':
        var = re.search(r"""variant\s*=\s*(?:"([^"]*)"|'([^']*)'|\{\s*["']([^"']*)["']\s*\})""", attrs)
        v = ''.join(g or '' for g in var.groups()) if var else 'default'
        return v in ('default', 'destructive', 'primary')
    return False


GENERIC_FONTS = {
    'inherit', 'initial', 'unset', 'sans-serif', 'serif', 'monospace', 'cursive', 'fantasy',
    'system-ui', 'ui-sans-serif', 'ui-serif', 'ui-monospace', 'ui-rounded',
    '-apple-system', 'blinkmacsystemfont', 'segoe ui',
}
NEUTRAL_SANS = {'Inter', 'Roboto', 'Open Sans', 'Poppins', 'Lato', 'Montserrat', 'DM Sans', 'Nunito'}
NEUTRAL_MONO = {'JetBrains Mono', 'Fira Code', 'IBM Plex Mono', 'Source Code Pro', 'Roboto Mono', 'Geist Mono'}


def font_families(txt):
    """Extract declared/imported font families, ignoring CSS generic families and var()."""
    fams = set()
    for f in re.findall(r'font-family\s*:\s*([^;}\n]+)', txt):
        fam = f.split(',')[0].strip().strip('\'"')
        if fam and not fam.startswith('var(') and fam.lower() not in GENERIC_FONTS:
            fams.add(fam)
    for url in re.findall(r'fonts\.googleapis\.com/[^"\'\s)]+', txt):
        for raw in re.findall(r'family=([^&"\']+)', url):
            for chunk in raw.split('|'):
                fam = chunk.split(':')[0].replace('+', ' ').strip()
                if fam and fam.lower() not in GENERIC_FONTS:
                    fams.add(fam)
    for imp in re.findall(r'import\s*\{([^}]+)\}\s*from\s*["\']next/font/google["\']', txt):
        for x in imp.split(','):
            fam = x.split(' as ')[0].strip().replace('_', ' ')
            if fam and fam.lower() not in GENERIC_FONTS:
                fams.add(fam)
    return fams


def is_chromatic(h):
    """True if hex color has noticeable chroma (excludes black, white, greys, and warm off-whites)."""
    try:
        r, g, b = [v / 255 for v in hex2rgb(h)]
    except ValueError:
        return False
    _, _, s = colorsys.rgb_to_hls(r, g, b)
    return (max(r, g, b) - min(r, g, b)) >= 0.18 and s >= 0.25


def character_checks(txt, nodes, mood, tokens=None):
    """Checks for the 'sterile' failure mode: correct but grey, flat and boxed-in."""
    out = []
    dark = is_dark_page(txt, tokens)
    children = {}
    for n in nodes:
        anc = n[3]
        if anc:
            children.setdefault(anc[-1][3], []).append(n)

    # primary CTA too small (Fitts)
    for tag, attrs, cls, anc, s, e in nodes:
        if is_solid_cta(tag, attrs, cls, dark):
            h = height_px(cls)
            if h is not None and h < 40:
                out.append(('WARN', 'fitts-primary', f"L{line_of(txt, s)} primary CTA is {h:g}px tall; use >=44px (h-11+), hero CTA h-12..h-14"))

    # frame wrappers: rounded padded box whose only child is another rounded surface
    frames = []
    for tag, attrs, cls, anc, s, e in nodes:
        if radius_px(cls) is None or radius_px(cls) < 12:
            continue
        p = padding_px(cls)
        if p is None or p > 16 or not any(c.startswith(('bg-', 'border')) for c in cls):
            continue
        kids = children.get(s, [])
        if len(kids) == 1:
            k = kids[0][2]
            if radius_px(k) is not None and any(c.startswith(('bg-', 'border')) for c in k):
                frames.append(line_of(txt, s))
    if frames:
        out.append(('INFO', 'frame-wrapper', f"{len(frames)} box(es) whose only child is another rounded surface (lines {frames[:8]}); merge into one card"))

    # cards: border-heavy without depth
    cards = [cls for tag, attrs, cls, anc, s, e in nodes
             if any(CARD_RADIUS.match(c) for c in cls) and (padding_px(cls) or 0) >= 12
             and any(c.startswith('bg-') or c == 'border' or c.startswith('border-') for c in cls)
             and tag not in ('button', 'a', 'Button', 'input', 'span')]
    if len(cards) >= 4 and mood not in ('technical', 'editorial'):  # hairlines are the depth language there
        bordered = sum(1 for c in cards if 'border' in c or any(re.fullmatch(r'border-\d', x) for x in c))
        shadowed = sum(1 for c in cards if any(re.fullmatch(r'shadow(-sm|-md|-lg|-xl|-2xl)?', x) for x in c))
        if bordered / len(cards) >= 0.7 and shadowed <= 1:
            out.append(('INFO', 'border-heavy', f"{bordered}/{len(cards)} cards bordered, {shadowed} with shadow; separate with background shift + shadow-sm instead"))

    # flat hierarchy: one text size dominates, or most text is bold
    sizes, bolds, sized = {}, 0, 0
    for tag, attrs, cls, anc, s, e in nodes:
        sz = [c for c in cls if SIZE_CLASS.match(c)]
        if not sz:
            continue
        sized += 1
        sizes[sz[-1]] = sizes.get(sz[-1], 0) + 1
        if any(c in ('font-bold', 'font-extrabold', 'font-black') for c in cls):
            bolds += 1
    if sized >= 15:
        top, n = max(sizes.items(), key=lambda kv: kv[1])
        if bolds / sized > 0.4 and (n / sized > 0.55 or bolds / sized > 0.6):
            out.append(('INFO', 'flat-hierarchy', f"{bolds}/{sized} sized text elements are bold and {n} use {top}; "
                                                  "body 400, labels 500, headings 600-700, vary sizes"))

    # grey-only charts: bar fills inside tracks
    bars = []
    for tag, attrs, cls, anc, s, e in nodes:
        if (any(re.fullmatch(r'h-(?:1|1\.5|2|2\.5|3|full)', c) for c in cls) and
                any(re.fullmatch(r'w-(?:\d+/\d+|\[\d+%\])', c) for c in cls)) or re.search(r'style\s*=\s*["\'][^"\']*width\s*:\s*\d+%', attrs):
            if 'animate-pulse' in cls or any('animate-pulse' in a[2] for a in anc):
                continue  # skeleton placeholders, not data
            bg = pick(cls, 'bg')
            m = re.fullmatch(r'([a-z]+)-\d+', bg or '')
            if m:
                bars.append(m.group(1))
    if len(bars) >= 3 and len({b for b in bars if b not in NEUTRALS}) <= 1:
        out.append(('WARN', 'grey-chart', f"{len(bars)} chart bars use {sorted(set(bars))}; give categories distinct hues (indigo, emerald, amber, rose, sky)"))

    # stock look: default Tailwind accent, no custom palette, only neutral body fonts
    stock = [h for h in HUE_CLASS.findall(txt) if h in TW and h not in NEUTRALS]
    if stock:
        top, n = max(((h, stock.count(h)) for h in set(stock)), key=lambda x: x[1])
        custom = re.search(r'colors\s*:\s*\{|--color-[\w-]+\s*:|:root\s*\{[^}]*--[\w-]*(?:accent|brand|primary|ink|paper)', txt)
        fams = font_families(txt)
        neutral_fonts = not fams or fams <= (NEUTRAL_SANS | NEUTRAL_MONO)
        if top in ('blue', 'indigo', 'violet', 'purple', 'fuchsia') and not custom and neutral_fonts:
            out.append(('INFO', 'stock-look', f"accent is stock Tailwind {top} with no custom palette and only neutral fonts; "
                        "derive the palette from the subject (reference/visual-quality.md) and add a display or serif face"))

    # mood: color presence and hero surface
    if mood in ('playful', 'bold', 'trust'):
        hues = {h for h in HUE_CLASS.findall(txt) if h in TW and h not in NEUTRALS}
        if tokens:
            for tok_name in re.findall(r'(?<![\w-])(?:[a-z]+:)*(?:bg|text|border|from|to)-([\w-]+)(?![\w-])', txt):
                if tok_name in tokens and is_chromatic(tokens[tok_name]):
                    hues.add(tok_name)
        for hx in re.findall(r'(?<![\w-])(?:[a-z]+:)*bg-\[(#[0-9a-fA-F]{3}|#[0-9a-fA-F]{6})\]', txt):
            if is_chromatic(hx):
                hues.add(hx.lower())
        need = 3 if mood in ('playful', 'bold') else 1
        if len(hues) < need:
            out.append(('INFO', 'low-color', f"{len(hues)} hue(s) {sorted(hues)} for a {mood} mood; aim for >= {need} (accent + supporting hues)"))
        hero = False
        for tag, attrs, cls, anc, s, e in nodes:
            if tag in ('button', 'a', 'Button', 'span'):
                continue
            big = (padding_px(cls) or 0) >= 16 or any(re.match(r'p[xybt]?-(?:[5-9]|[1-9]\d)$', c) for c in cls)
            b = pick(cls, 'bg')
            b_hex = tw_hex(b, tokens or {}) if b and b not in BG_PASSTHROUGH else None
            sat = any(is_gradient(c) for c in cls) or any(
                (m := re.fullmatch(r'bg-([a-z]+)-(?:[5-9]00|950)', c)) and m.group(1) in TW and m.group(1) not in NEUTRALS
                for c in cls) or (bool(b_hex) and (b.startswith('[#') or (tokens and b.split('/')[0] in tokens)) and is_chromatic(b_hex))
            dark_band = (mood == 'bold' and tag in ('section', 'header', 'div') and
                         any(re.fullmatch(r'bg-(?:(?:slate|gray|zinc|neutral|stone)-(?:900|950)|black)', c) for c in cls) and
                         any(re.fullmatch(r'p[ty]-(?:1[6-9]|[2-9]\d)', c) for c in cls))
            if (big and sat) or dark_band:
                hero = True
                break
        if not hero:
            out.append(('WARN', 'no-hero-surface', f"no saturated or gradient surface for a {mood} mood; give the featured card / hero / CTA band the accent"))
    out.extend(mood_specific(txt, nodes, mood))
    return out


MAXW = re.compile(r'^max-w-(prose|xs|sm|md|lg|xl|2xl|3xl|4xl|5xl|6xl|7xl|\[[^\]]+\])$')
NARROW = re.compile(r'^max-w-(?:prose|xs|sm|md|lg|xl|2xl|\[(?:[4-7]\d|80)ch\])$')
DISPLAY_TEXT = re.compile(r'^text-(?:3xl|4xl|5xl|6xl|7xl|8xl|9xl)$')


EXPRESSIVE = ('playful', 'bold')
# style rules that expressive moods may break on purpose; the accessibility/readability floor
# (wcag-aa, line-length, reveal-needs-js, ...) stays at full severity
RELAXED = {'grid', 'miller-7', 'single-primary-cta', 'grey-chart', 'max-2-fonts',
           'no-hero-surface', 'border-heavy', 'no-drawn-mascot', 'card-sameness', 'bold-headline-size', 'bold-font-default'}


def _px(v, unit):
    return v * 16 if unit == 'rem' else v


def character_floor(txt, nodes, mood):
    out = []
    # content that needs JS to appear
    if re.search(r'(?<![:\w-])opacity-0\b', txt) or re.search(r'\.(?:reveal|fade-in|hidden-on-load)[^{]*\{[^}]*opacity\s*:\s*0', txt):
        if not re.search(r'<noscript|animation-fill-mode|animation:[^;}]*(?:both|forwards)', txt):
            out.append(('WARN', 'reveal-needs-js', "content starts at opacity 0 and relies on a script to appear; "
                        "it renders blank without JS or in a screenshot. Keep content visible or use a CSS animation with fill-mode both"))
    if mood == 'playful':
        best = 0
        for m in re.finditer(r'<svg\b.*?</svg>', txt, re.S):
            best = max(best, len(re.findall(r'<(?:path|circle|ellipse|rect|polygon|line|polyline)\b', m.group(0))))
        if best < 6:
            out.append(('WARN', 'no-drawn-mascot', f"largest inline SVG has {best} shapes; Playful needs a drawn mascot/toy "
                        "(6+ shapes, 120px+) in the hero, emoji alone does not count"))
        whites = len(re.findall(r'bg-white[^"\']*rounded-(?:2xl|3xl)|rounded-(?:2xl|3xl)[^"\']*bg-white', txt))
        if whites >= 7:
            out.append(('WARN', 'card-sameness', f"{whites} white rounded cards; alternate section treatments "
                        "(color band, tilted sticker, outline shape) so the page is not one repeated card"))
    if mood == 'bold':
        tw_xl = {'4': 36, '5': 48, '6': 60, '7': 72, '8': 96, '9': 128}
        sizes = []
        for m in re.finditer(r'text-([4-9])xl', txt):
            sizes.append(tw_xl[m.group(1)])
        for m in re.finditer(r'text-\[(\d+(?:\.\d+)?)(px|rem)\]', txt):
            sizes.append(_px(float(m.group(1)), m.group(2)))
        for m in re.finditer(r'clamp\([^;{}]*?,\s*(\d+(?:\.\d+)?)(px|rem)\s*\)', txt):
            sizes.append(_px(float(m.group(1)), m.group(2)))
        for m in re.finditer(r'font-size\s*:\s*(\d+(?:\.\d+)?)(px|rem)', txt):
            sizes.append(_px(float(m.group(1)), m.group(2)))
        if not sizes or max(sizes) < 72:
            out.append(('WARN', 'bold-headline-size', "no headline at 72px+ (text-7xl or clamp up to 6-7rem); "
                        "Bold needs one oversized display headline"))
        fams = font_families(txt)
        if fams and fams <= NEUTRAL_SANS:
            out.append(('INFO', 'bold-font-default', "only neutral body fonts loaded; add a display face "
                        "(Archivo Black, Anton, Space Grotesk, Sora, Bebas Neue) for the headline"))
    return out


def mood_specific(txt, nodes, mood):
    out = list(character_floor(txt, nodes, mood))
    if mood == 'editorial':
        # headline trapped in the reading measure
        trapped = []
        for tag, attrs, cls, anc, s, e in nodes:
            if tag in ('h1', 'h2') and any(DISPLAY_TEXT.match(c) for c in cls):
                chain = [cls] + [a[2] for a in anc if a[0] not in ('body', 'html')]
                if any(NARROW.match(c) for cl in chain for c in cl):
                    trapped.append(line_of(txt, s))
        if trapped:
            out.append(('WARN', 'headline-measure', f"{len(trapped)} display headline(s) inside the reading measure (lines {trapped[:6]}); "
                        "keep body at 65ch but let headlines, figures and pull quotes span the wide frame (max-w-4xl/5xl)"))
        # too many container widths
        widths = {c for tag, attrs, cls, anc, s, e in nodes for c in cls if MAXW.match(c) and 'mx-auto' in cls}
        widths = {('prose' if w == 'max-w-prose' else w) for w in widths}
        if len(widths) >= 3:
            out.append(('INFO', 'width-funnel', f"{len(widths)} container widths {sorted(widths)}; use two: one wide frame + one reading column, aligned to the same left edge or centered together"))
        # reading column centered while the headline is left-aligned: left edges drift apart
        cols = [n for n in nodes if any(NARROW.match(c) for c in n[2]) and 'mx-auto' in n[2]]
        if cols:
            col_starts = {n[4] for n in cols}
            drift = []
            for tag, attrs, cls, anc, s, e in nodes:
                if tag == 'h1':
                    if s in col_starts or any(a[3] in col_starts for a in anc) or any(any(a[3] == s for a in col[3]) for col in cols):
                        continue
                    chain = [cls] + [a[2] for a in anc]
                    if not any('text-center' in c for c in chain):
                        drift.append(line_of(txt, s))
            if drift:
                out.append(('WARN', 'edge-align', f"reading column is centered (mx-auto) but the headline is left-aligned (line {drift[0]}); "
                            "left edges do not line up. Drop mx-auto on the column so it shares the frame's left edge, or center the headline too"))
        # cramped leading on long text
        tight = [line_of(txt, s) for tag, attrs, cls, anc, s, e in nodes
                 if tag in ('p', 'blockquote', 'li') and any(c in ('leading-none', 'leading-tight', 'leading-snug') for c in cls)
                 and any(c in ('text-lg', 'text-xl', 'text-2xl', 'text-base') for c in cls)]
        if tight:
            out.append(('WARN', 'editorial-leading', f"{len(tight)} long-form text element(s) with tight leading (lines {tight[:6]}); body 1.65-1.8 (leading-relaxed/loose), quotes >= 1.4"))
        if not re.search(r'font-serif|(?:font-family\s*:[^;}]*|font-\[[^\]]*)(?:(?<!sans-)\bserif\b|Merriweather|Lora|Playfair|Source Serif|Source_Serif|Fraunces)', txt, re.I):
            out.append(('INFO', 'no-serif', "no serif face found; editorial mood usually pairs a serif display (or body) with a sans"))
    elif mood == 'technical':
        soft = [line_of(txt, s) for tag, attrs, cls, anc, s, e in nodes
                if (radius_px(cls) or 0) > 12 and tag not in ('span', 'img') and not any(c in ('rounded-full',) for c in cls)]
        if len(soft) >= 3:
            out.append(('INFO', 'radius-too-soft', f"{len(soft)} elements with radius > 12px (lines {soft[:6]}); technical mood uses 4-8px"))
        if 'font-mono' not in txt and not re.search(r'font-family\s*:[^;]*(?:mono|Mono|Consolas|Menlo)', txt):
            out.append(('INFO', 'no-mono', "no monospace face; use mono for labels, numbers, code and IDs"))
        heavy = sum(1 for tag, attrs, cls, anc, s, e in nodes if any(re.fullmatch(r'shadow-(?:lg|xl|2xl)', c) for c in cls))
        if heavy >= 3:
            out.append(('INFO', 'shadow-heavy', f"{heavy} large shadows; technical mood separates layers with 1px borders and bg steps"))
    return out


def line_of(txt, pos):
    return txt.count('\n', 0, pos) + 1


def audit(path, grid, tokens, dark_tokens=None, mood=None):
    txt = pathlib.Path(path).read_text(encoding='utf-8', errors='ignore')
    masked = mask_non_markup(txt)
    issues = []

    def add(sev, rule, msg):
        issues.append((sev, rule, msg))

    finetunes = []

    def grid_check(label, v):
        v = abs(v)
        if v <= 2:
            return
        if v % 4 == 2:
            finetunes.append(label.split()[0])  # Tailwind half-steps (6, 10, 14px) are common; informational
        elif v % 4:
            add('WARN', 'grid', f"{label} = {v:g}px, off the 4px grid")
        elif v % grid:
            finetunes.append(label.split()[0])

    # spacing: CSS
    for m in re.finditer(rf'(?<![\w-]){SPACE_PROPS}\s*:\s*([^;}}"\n]+)', txt):
        for px in re.findall(r'(-?\d+(?:\.\d+)?)px', m.group(1)):
            grid_check(f"L{line_of(txt, m.start())} {m.group(0).strip()[:50]}", float(px))
    # spacing: Tailwind
    for m in TW_SPACE.finditer(masked):
        val = m.group(1)
        if val.startswith('['):
            px = re.fullmatch(r'\[(-?\d+(?:\.\d+)?)px\]', val)
            if px:
                grid_check(f"L{line_of(txt, m.start())} {m.group(0)}", float(px.group(1)))
        else:
            grid_check(f"L{line_of(txt, m.start())} {m.group(0)}", float(val) * 4)

    if finetunes:
        share = len(finetunes)
        lines = list(dict.fromkeys(finetunes))
        add('INFO', 'grid', f"{share} spacing value(s) on the 4px fine-tune grid ({', '.join(lines[:6])}{', ...' if len(lines) > 6 else ''}); "
                            f"fine inside dense controls, prefer {grid}px multiples for layout spacing")

    # fonts
    fams = font_families(txt)
    if len(fams) > 2:
        add('FAIL', 'max-2-fonts', f"{len(fams)} font families: {sorted(fams)}")

    # contrast: plain CSS rules
    for blk in re.finditer(r'\{([^{}]+)\}', txt):
        b = blk.group(1)
        fg = re.search(rf'(?<![\w-])color\s*:\s*({HEX})', b)
        bg = re.search(rf'background(?:-color)?\s*:\s*({HEX})', b)
        if fg and bg:
            r = ratio(fg.group(1), bg.group(1))
            if r < 4.5:
                add('FAIL' if r < 3 else 'WARN', 'wcag-aa',
                    f"L{line_of(txt, blk.start())} {fg.group(1)} on {bg.group(1)} = {r:.2f}:1 (fix -> {fix_color(fg.group(1), bg.group(1), 4.5)})")

    nodes = list(walk(masked))

    # contrast: Tailwind palette, arbitrary hex and shadcn tokens; background composited from ancestors
    seen = set()
    page = 'background' if 'background' in tokens else (f'[{cbg}]' if (cbg := css_page_bg(txt, tokens)) else 'white')
    passes = [('', '', tokens, page, None), ('dark:', 'dark:', tokens, None, None)]
    if dark_tokens:  # shadcn .dark theme: same classes re-evaluated with dark token values
        passes.append(('', '[.dark] ', {**tokens, **dark_tokens}, 'background' if 'background' in dark_tokens else None, dark_tokens))
    for variant, label, tokens, page_bg, only in passes:
        for tag, attrs, cls, anc, s, e in nodes:
            fg = pick(cls, 'text', variant)
            if not fg:
                continue
            res = backdrop([cls] + [a[2] for a in reversed(anc)], variant, tokens, page_bg,
                           [attrs] + [a[1] for a in reversed(anc)])
            if res is None:
                continue  # gradient, image or unknown color behind the text
            bh, bg = res
            bg_names = {part.removeprefix('bg-').split('/')[0] for part in bg.split(' over ')}
            if only is not None and fg.split('/')[0] not in only and not (bg_names & set(only)):
                continue  # theme-independent pair, already checked in the light pass
            fh = tw_hex(fg, tokens)
            if not fh:
                continue
            fa = alpha_of(fg)
            if fa < 1:
                fh = blend(fh, bh, fa)
            r = ratio(fh, bh)
            big = bool(BIG_TEXT & set(cls)) or ('text-xl' in cls and bool(BOLD & set(cls)))
            need = 3.0 if big else 4.5
            key = (label, fg, bg, need)
            if r < need and key not in seen:
                seen.add(key)
                tw = tw_same_hue(fg, bh, need)
                bg_fix = tw_bg_same_hue(bg.split(' over ')[0][3:], fh, need) if not tw else None
                fix = f"text-{tw}" if tw else (f"bg-{bg_fix}" if bg_fix else fix_color(fh, bh, need))
                add('FAIL' if r < 3 else 'WARN', 'wcag-aa',
                    f"L{line_of(txt, s)} {label}text-{fg} on {bg} = {r:.2f}:1 (need {need:g}, fix -> {fix}, keep the hue)")

    tokens = passes[0][2]

    # contrast on gradients: text must pass against every color stop of the nearest gradient
    gseen = set()
    for tag, attrs, cls, anc, s, e in nodes:
        fg = pick(cls, 'text')
        if not fg:
            continue
        g = None
        for c in [cls] + [a[2] for a in reversed(anc)]:
            if any(is_gradient(x) for x in c if ':' not in x):
                g = c
                break
            b = pick(c, 'bg')
            if b and b not in BG_PASSTHROUGH and alpha_of(b) >= 1:
                break  # an opaque solid layer sits between the text and any gradient
        if g is None:
            continue
        fh = tw_hex(fg, tokens)
        if not fh or alpha_of(fg) < 1:
            continue
        big = bool(BIG_TEXT & set(cls)) or ('text-xl' in cls and bool(BOLD & set(cls)))
        need = 3.0 if big else 4.5
        for x in g:
            m = re.fullmatch(r'(?:from|via|to)-([\w.\[\]#-]+)', x)
            if not m or alpha_of(m.group(1)) < 1 or m.group(1) in BG_PASSTHROUGH:
                continue
            sh = tw_hex(m.group(1), tokens)
            if not sh:
                continue
            r = ratio(fh, sh)
            key = (fg, m.group(1), need)
            if r < need and key not in gseen:
                gseen.add(key)
                add('FAIL' if r < 3 else 'WARN', 'wcag-aa',
                    f"L{line_of(txt, s)} text-{fg} on gradient stop {x} = {r:.2f}:1 (need {need:g}); text must pass against every stop, darken that stop within its hue")

    # single primary CTA per block: raw buttons with solid bg, and shadcn <Button> default/destructive
    dark_page = is_dark_page(txt, tokens)
    counts = {}
    for tag, attrs, cls, anc, s, e in nodes:
        if not is_solid_cta(tag, attrs, cls, dark_page):
            continue
        idx = next((i for i in range(len(anc) - 1, -1, -1) if BLOCK.match(anc[i][0])), None)
        key = anc[idx][3] if idx is not None else -1
        counts.setdefault(key, []).append(line_of(txt, s))
    for lines in counts.values():
        if len(lines) > 1:
            add('WARN', 'single-primary-cta', f"{len(lines)} solid buttons in one block (lines {lines}); keep 1 solid, rest outline/ghost")

    # nested radius: child radius should equal parent radius - parent padding
    for tag, attrs, cls, anc, s, e in nodes:
        if not anc:
            continue
        cr, (pr, pp) = radius_px(cls), (radius_px(anc[-1][2]), padding_px(anc[-1][2]))
        if cr is None or pr is None or pp is None or pr <= 0 or pp >= pr:
            continue  # with padding >= outer radius the inner radius is a free choice
        want = pr - pp
        if cr != want and cr > want:
            add('INFO', 'nested-radius', f"L{line_of(txt, s)} inner radius {cr}px inside {pr}px with {pp}px padding; use {want}px ({RADIUS_NAME.get(want, f'rounded-[{want}px]')})")

    # character / sterility checks
    issues.extend(character_checks(txt, nodes, mood, tokens))

    # Miller: nav items
    for tag, attrs, cls, anc, s, e in nodes:
        if tag == 'nav':
            end = masked.find('</nav>', e)
            body = masked[e:end if end != -1 else len(masked)]
            body = re.sub(r'<details\b.*?</details>', '', body, flags=re.S)  # overflow menu items are disclosed on demand
            n = len(re.findall(r'<(?:a|Link|NavLink)\b', body))
            if n > 7:
                add('WARN', 'miller-7', f"L{line_of(txt, s)} nav has {n} links (>7); group or move to an overflow menu")

    # line length: each long <p> needs a readable max-width on itself or an ancestor
    css_p = re.search(r'(?:^|[\s,}])(?:p|article|\.prose)\s*(?:,[^{]*)?\{[^}]*max-width\s*:\s*(?:[4-7]\d|80)ch', txt)
    bad = []
    for tag, attrs, cls, anc, s, e in nodes:
        if tag != 'p':
            continue
        end = masked.find('</p>', e)
        inner = re.sub(r'<[^>]+>|\{[^}]*\}', '', masked[e:end if end != -1 else e])
        if len(' '.join(inner.split())) < 75:
            continue
        chain = [(attrs, cls)] + [(a[1], a[2]) for a in anc]
        ok = css_p or any(READABLE_MAXW.search(' '.join(c)) or READABLE_MAXW.search(at) or 'prose' in c for at, c in chain)
        if not ok:
            bad.append(line_of(txt, s))
    if bad:
        add('WARN', 'line-length', f"{len(bad)} long paragraph(s) without a readable max-width (lines {bad[:8]}); use max-w-prose / 65ch")

    # skeleton / empty state
    if re.search(r'\.map\(|v-for|\*ngFor|\{#each', txt) and not re.search(r'(?i)skeleton|empty|no (?:data|results|items)|animate-pulse', txt):
        add('INFO', 'skeleton-empty', "list rendering without skeleton/empty state")
    if re.search(r'<(?:html|body)\b', masked, re.I) and not re.search(r'<main\b|role=["\']main', masked, re.I):
        add('WARN', 'landmark-main', 'full page without a <main> landmark; wrap the primary content in <main> (and use <header>/<footer>/<nav>)')
    if mood in EXPRESSIVE:
        issues = [(('INFO', r, m + ' [relaxed in expressive moods]') if sev != 'INFO' and r in RELAXED else (sev, r, m))
                  for sev, r, m in issues]
    return issues


def cmd_audit(a):
    if a.grid <= 0:
        sys.exit(f"error: --grid must be > 0 (got {a.grid})")
    missing = [p for p in a.files + (a.css or []) if not pathlib.Path(p).is_file()]
    if missing:
        sys.exit(f"error: file not found: {', '.join(missing)}")
    css_texts = [pathlib.Path(p).read_text(encoding='utf-8', errors='ignore') for p in (a.css or [])]
    shared_tokens, shared_dark = css_tokens(css_texts), css_tokens(css_texts, r'\.dark')
    total = {'FAIL': 0, 'WARN': 0, 'INFO': 0}
    for p in a.files:
        p_txt = pathlib.Path(p).read_text(encoding='utf-8', errors='ignore')
        tokens = {**shared_tokens, **css_tokens([p_txt])}
        dark_tokens = {**shared_dark, **css_tokens([p_txt], r'\.dark')}
        iss = audit(p, a.grid, tokens, dark_tokens, a.mood)
        print(f"== {p}: {len(iss)} issue(s)")
        for sev, rule, msg in iss:
            total[sev] += 1
            print(f"  [{sev}] {rule}: {msg}")
    print(f"\nSUMMARY FAIL={total['FAIL']} WARN={total['WARN']} INFO={total['INFO']}")
    sys.exit(1 if total['FAIL'] else 0)


def main(argv=None):
    ap = argparse.ArgumentParser(description='Classic UI design principles toolkit')
    sp = ap.add_subparsers(dest='cmd', required=True)
    c = sp.add_parser('contrast', help='WCAG contrast; accepts hex or Tailwind names (slate-400)')
    c.add_argument('fg'); c.add_argument('bg'); c.add_argument('--target', type=float, default=4.5); c.set_defaults(f=cmd_contrast)
    s = sp.add_parser('scale', help='modular type scale')
    s.add_argument('--base', type=float, default=16); s.add_argument('--ratio', default='major-third'); s.set_defaults(f=cmd_scale)
    r = sp.add_parser('radius', help='nested radius = outer - padding')
    r.add_argument('outer', type=float); r.add_argument('padding', type=float); r.set_defaults(f=cmd_radius)
    n = sp.add_parser('snap', help='round values to grid')
    n.add_argument('values', type=float, nargs='+'); n.add_argument('--grid', type=int, default=8); n.set_defaults(f=cmd_snap)
    d = sp.add_parser('audit', help='scan HTML/JSX/Vue/CSS files for rule violations')
    d.add_argument('files', nargs='+')
    d.add_argument('--grid', type=int, default=8, help='soft grid (default 8); values off the 4px grid are always WARN')
    d.add_argument('--css', nargs='*', help='CSS files with :root tokens, e.g. app/globals.css for shadcn')
    d.add_argument('--mood', choices=['playful', 'trust', 'bold', 'editorial', 'technical'],
                   help='enable mood checks: color presence and hero surface')
    d.set_defaults(f=cmd_audit)
    a = ap.parse_args(argv)
    a.f(a)


if __name__ == '__main__':
    main()
