#!/usr/bin/env python3
"""UI design rule toolkit: contrast, type scale, nested radius, spacing snap, audit."""
import re, sys, argparse, colorsys, pathlib, urllib.parse

_SCRIPTS_DIR = str(pathlib.Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from uicolor import (
    HEX,
    NAMED,
    NEUTRALS,
    SHADES,
    TW,
    _parse_solid_bg,
    _px,
    alpha_of,
    backdrop,
    blend,
    css_page_bg,
    css_tokens,
    fix_color,
    hex2rgb,
    hsl2hex,
    inline_bg,
    is_chromatic,
    is_gradient,
    lum,
    ratio,
    rgb2hex,
    tailwind_config_colors,
    tw_bg_same_hue,
    tw_hex,
    tw_same_hue,
)
from uiparse import (
    BG_NON_COLOR,
    BG_PASSTHROUGH,
    BIG_TEXT,
    BLOCK,
    BOLD,
    CARD_RADIUS,
    COL_MED,
    COL_NARROW,
    DARK_NEUTRAL,
    HEADLINE_TEXT,
    HUE_CLASS,
    MAXW,
    MULTI_COL,
    NARROW,
    NARROW_COL,
    RADIUS,
    RADIUS_NAME,
    READABLE_MAXW,
    SIZE_CLASS,
    SPACE_PROPS,
    TAG,
    TEXT_NON_COLOR,
    TW_SPACE_CLS,
    VOID,
    WIDE_FRAME,
    WIDE_XL,
    _has_row_flex,
    _strip_all_comments,
    _strip_at_blocks,
    _strip_css_blocks,
    classes,
    height_px,
    line_of,
    mask_non_markup,
    padding_px,
    pick,
    radius_px,
    strip_css_comments,
    walk,
)


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

def is_dark_page(txt, tokens=None):
    """True when the page base is a dark neutral (body/html/main/root wrapper), so dark neutral buttons are surfaces, not CTAs."""
    tokens = tokens or {}
    cbg = css_page_bg(txt, tokens)
    if cbg and lum(cbg) < 0.18:
        return True
    for m in re.finditer(r'<(?:body|html|main)\b([^>]*)>', mask_non_markup(txt), re.I):
        attrs = m.group(1)
        ib = inline_bg(attrs, tokens)
        if ib and ib not in ('GRADIENT', 'UNKNOWN') and lum(ib) < 0.18:
            return True
        b = pick(classes(attrs), 'bg')
        if b and b not in BG_PASSTHROUGH:
            h = tw_hex(b, tokens)
            if h and lum(h) < 0.18:
                return True
    return False


def is_solid_cta(tag, attrs, cls, dark_page=False, tokens=None):
    if tag in ('button', 'a'):
        if 'bg-clip-text' in cls:
            return False
        bg = pick(cls, 'bg')
        if dark_page and bg and DARK_NEUTRAL.fullmatch(bg):
            return False  # dark neutral on a dark page is a secondary surface
        if bg:
            if bg in ('primary', 'destructive') or bool(re.fullmatch(r'[a-z]+-(?:[5-9]00|950)', bg)):
                return True
            hx = re.fullmatch(r'\[(#[0-9a-fA-F]{3}|#[0-9a-fA-F]{6})\]', bg)
            if hx:
                h = hx.group(1)
                if not dark_page and not is_chromatic(h) and lum(h) > 0.7:
                    return False  # light neutral hex on light page is a secondary/card fill
                if dark_page and not is_chromatic(h) and lum(h) < 0.15:
                    return False  # dark neutral hex on dark page is a secondary surface
                return True
            if tokens and bg.split('/')[0] in tokens and is_chromatic(tokens[bg.split('/')[0]]):
                return True
        return any(is_gradient(c) for c in cls)
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
# rounded kids' faces are the default pick for playful pages, so they do not make a page distinctive on their own
COMMON_ROUNDED = {'Fredoka', 'Baloo 2', 'Baloo', 'Chewy', 'Lilita One', 'Quicksand', 'Comfortaa'}
SERIF_FACES = {'fraunces', 'playfair display', 'newsreader', 'merriweather', 'lora', 'eb garamond', 'cormorant', 'cormorant garamond',
               'libre caslon text', 'libre caslon display', 'libre baskerville', 'crimson text', 'crimson pro', 'literata', 'spectral',
               'bitter', 'georgia', 'times new roman', 'baskerville', 'garamond', 'abril fatface', 'young serif', 'gloock',
               'instrument serif'}


def has_serif_face(txt):
    """True when the page uses a serif: the font-serif class, a serif generic in a font stack, or a loaded/declared serif face."""
    clean = _strip_all_comments(txt)
    if re.search(r'(?<![\w-])font-serif(?![\w-])', clean):
        return True
    if re.search(r'(?:font-family|fontFamily)\s*:[^;}\n]*(?<!sans-)\bserif\b', clean, re.I):
        return True
    names = {n.lower() for n in font_families(clean)}
    for blk in re.finditer(r'fontFamily\s*:\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', clean):
        for n in re.findall(r"""['"]([A-Z][A-Za-z0-9 ]+)['"]""", blk.group(1)):
            names.add(n.lower())
    return any(n in SERIF_FACES or re.search(r'\bserif\b', n) for n in names)


def font_families(txt):
    """Extract declared/imported font families, ignoring comments, CSS generic families, var(), and case duplicates."""
    clean = _strip_all_comments(txt)
    seen = {}

    def _add(fam):
        fam = fam.strip().strip('\'"')
        if fam and not fam.startswith('var(') and fam.lower() not in GENERIC_FONTS:
            seen.setdefault(fam.lower(), fam)

    for m in re.finditer(r"""font-family\s*:\s*(?:"([^"\n;{}]+)"|'([^'\n;{}]+)'|([^;}\n"'<>]+))""", clean):
        val = (m.group(1) or m.group(2) or m.group(3) or '').split(',')[0]
        _add(val)
    for url in re.findall(r'fonts\.googleapis\.com/[^"\'\s)]+', clean):
        for raw in re.findall(r'family=([^&"\']+)', url):
            for chunk in raw.split('|'):
                fam = urllib.parse.unquote(chunk.split(':')[0].replace('+', ' '))
                _add(fam)
    for imp in re.findall(r'import\s*\{([^}]+)\}\s*from\s*["\']next/font/google["\']', clean):
        for x in imp.split(','):
            _add(x.split(' as ')[0].strip().replace('_', ' '))
    return set(seen.values())


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
        if is_solid_cta(tag, attrs, cls, dark, tokens):
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
    neutral_all = {n.lower() for n in (NEUTRAL_SANS | NEUTRAL_MONO | COMMON_ROUNDED)}
    stock = [h for h in HUE_CLASS.findall(txt) if h in TW and h not in NEUTRALS]
    if stock:
        top, n = max(((h, stock.count(h)) for h in sorted(set(stock))), key=lambda x: x[1])
        custom = re.search(r'colors\s*:\s*\{|--color-[\w-]+\s*:|:root\s*\{[^}]*--[\w-]*(?:accent|brand|primary|ink|paper)', txt)
        fams = font_families(txt)
        neutral_fonts = not fams or all(f.lower() in neutral_all for f in fams)
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


EXPRESSIVE = ('playful', 'bold')
# style rules that expressive moods may break on purpose; the accessibility/readability floor
# (wcag-aa, line-length, reveal-needs-js, ...) stays at full severity
RELAXED = {'grid', 'miller-7', 'single-primary-cta', 'grey-chart', 'max-2-fonts',
           'no-hero-surface', 'border-heavy', 'no-drawn-mascot', 'card-sameness', 'bold-headline-size', 'bold-font-default'}


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
        for m in re.finditer(r'text-\[clamp\([^,\]]+,[^,\]]+,\s*[_\s]*(\d+(?:\.\d+)?)(px|rem)[_\s]*\)\]', txt):
            sizes.append(_px(float(m.group(1)), m.group(2)))
        for m in re.finditer(r'font-size\s*:\s*clamp\([^;{}]*?,\s*(\d+(?:\.\d+)?)(px|rem)\s*\)', txt):
            sizes.append(_px(float(m.group(1)), m.group(2)))
        for m in re.finditer(r'font-size\s*:\s*(\d+(?:\.\d+)?)(px|rem)', txt):
            sizes.append(_px(float(m.group(1)), m.group(2)))
        if not sizes or max(sizes) < 72:
            out.append(('WARN', 'bold-headline-size', "no headline at 72px+ (text-7xl or clamp up to 6-7rem); "
                        "Bold needs one oversized display headline"))
        fams = font_families(txt)
        neutral_sans = {n.lower() for n in NEUTRAL_SANS}
        if fams and all(f.lower() in neutral_sans for f in fams):
            out.append(('INFO', 'bold-font-default', "only neutral body fonts loaded; add a display face "
                        "(Archivo Black, Anton, Space Grotesk, Sora, Bebas Neue) for the headline"))
    return out


def mood_specific(txt, nodes, mood):
    out = list(character_floor(txt, nodes, mood))
    if mood == 'editorial':
        # display h1 trapped in the narrow reading measure
        trapped = []
        for tag, attrs, cls, anc, s, e in nodes:
            if tag == 'h1' and any(HEADLINE_TEXT.match(c) for c in cls):
                chain = [cls] + [a[2] for a in anc if a[0] not in ('body', 'html')]
                if any(NARROW_COL.match(c) for cl in chain for c in cl):
                    trapped.append(line_of(txt, s))
        if trapped:
            out.append(('WARN', 'headline-measure', f"{len(trapped)} display h1 inside the narrow reading measure (lines {trapped[:6]}); "
                        "let the h1 span a wider frame (max-w-3xl/4xl/5xl) centered above the column, or use a 2-column grid"))
        # two-column reading layout detection (aside in a multi-col grid/row-flex)
        has_sidebar = any(
            n[0].lower() == 'aside' and (
                any(MULTI_COL.match(c) for a in n[3] for c in a[2]) or
                any(_has_row_flex(a[2]) for a in n[3])
            )
            for n in nodes
        )
        has_2col_reading = has_sidebar or any(
            (any(MULTI_COL.match(c) for c in n[2]) or _has_row_flex(n[2])) and
            any(a_node[0].lower() in ('div', 'article', 'aside') and any(COL_NARROW.match(x) or COL_MED.match(x) for x in a_node[2])
                for a_node in nodes if any(an[3] == n[4] for an in a_node[3]))
            for n in nodes if n[0].lower() in ('div', 'section', 'main', 'article')
        )
        # lone uncentered reading column inside a wide frame with no sidebar
        if not has_sidebar:
            left_stacked = []
            skip_tags = {'blockquote', 'figure', 'header', 'footer', 'nav'}
            for tag, attrs, cls, anc, s, e in nodes:
                if tag.lower() not in ('div', 'article', 'section', 'main'):
                    continue
                is_col = any(COL_NARROW.match(c) for c in cls)
                is_med = any(COL_MED.match(c) for c in cls)
                if (not is_col and not is_med) or 'mx-auto' in cls:
                    continue
                if is_col and not any(WIDE_FRAME.match(c) for a in anc if a[0] not in ('body', 'html') for c in a[2]):
                    continue
                if not is_col and is_med and not any(WIDE_XL.match(c) for a in anc if a[0] not in ('body', 'html') for c in a[2]):
                    continue
                if any(a[0].lower() in skip_tags or a[0].lower() == 'aside' for a in anc):
                    continue
                if any(MULTI_COL.match(c) or _has_row_flex(a[2]) for a in anc for c in a[2]):
                    continue
                if any(('flex-col' in a[2] and 'items-center' in a[2]) or (any(NARROW.match(c) for c in a[2]) and 'mx-auto' in a[2]) for a in anc):
                    continue
                left_stacked.append(line_of(txt, s))
            if left_stacked:
                out.append(('WARN', 'left-stacked-column',
                            f"{len(left_stacked)} uncentered reading column(s) inside a wide frame with no sidebar (lines {left_stacked[:6]}); "
                            "add mx-auto (centered with the headline) or use a 2-column grid so the right half is not left blank"))
        # too many container widths
        widths = {c for tag, attrs, cls, anc, s, e in nodes for c in cls if MAXW.match(c) and 'mx-auto' in cls}
        widths = {('prose' if w == 'max-w-prose' else w) for w in widths}
        if len(widths) >= 3:
            out.append(('INFO', 'width-funnel', f"{len(widths)} container widths {sorted(widths)}; use two: one wide frame + one reading column, aligned to the same left edge or centered together"))
        # reading column centered while the headline is left-aligned: left edges drift apart
        ignore_edge = {'footer', 'header', 'nav', 'aside', 'blockquote', 'figure', 'form'}
        cols = [
            n for n in nodes
            if n[0].lower() not in ignore_edge
            and not any(a[0].lower() in ignore_edge for a in n[3])
            and any(NARROW.match(c) for c in n[2]) and 'mx-auto' in n[2]
        ]
        if cols and not has_2col_reading:
            col_starts = {n[4] for n in cols}
            drift = []
            for tag, attrs, cls, anc, s, e in nodes:
                if tag == 'h1':
                    if s in col_starts or any(a[3] in col_starts for a in anc) or any(any(a[3] == s for a in col[3]) for col in cols):
                        continue
                    chain_str = ' '.join(cls + [c for a in anc for c in a[2]])
                    if not (re.search(r'(?:^|\s)(?:[a-z0-9]+:)*(?:text-center|justify-center)(?:\s|$)', chain_str) or re.search(r'text-align\s*:\s*center', attrs, re.I)):
                        drift.append(line_of(txt, s))
            if drift:
                out.append(('WARN', 'edge-align', f"reading column is centered (mx-auto) while the wide-frame headline is left-aligned (line {drift[0]}); "
                            "center the headline with the column, keep both in one centered frame, or use a 2-column grid"))
        # cramped leading on long text
        tight = [line_of(txt, s) for tag, attrs, cls, anc, s, e in nodes
                 if tag in ('p', 'blockquote', 'li') and any(c in ('leading-none', 'leading-tight', 'leading-snug') for c in cls)
                 and any(c in ('text-lg', 'text-xl', 'text-2xl', 'text-base') for c in cls)]
        if tight:
            out.append(('WARN', 'editorial-leading', f"{len(tight)} long-form text element(s) with tight leading (lines {tight[:6]}); body 1.65-1.8 (leading-relaxed/loose), quotes >= 1.4"))
        if not has_serif_face(txt):
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


def audit(path, grid, tokens, dark_tokens=None, mood=None, txt=None):
    if txt is None:
        txt = pathlib.Path(path).read_text(encoding='utf-8', errors='ignore')
    masked = mask_non_markup(txt)
    nodes = list(walk(masked))
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

    # spacing: CSS (<style> blocks or standalone CSS files only, ignoring comments)
    styles = re.findall(r'<style\b[^>]*>(.*?)</style>', txt, re.S | re.I)
    css_for_grid = strip_css_comments('\n'.join(styles)) if styles else (
        '' if re.search(r'<(?:html|head|body|div|main|section|p|span)\b', masked, re.I) else strip_css_comments(txt)
    )
    for m in re.finditer(rf'(?<![\w-]){SPACE_PROPS}\s*:\s*([^;}}"\n]+)', css_for_grid):
        for px in re.findall(r'(-?\d+(?:\.\d+)?)px', m.group(1)):
            grid_check(f"L{line_of(css_for_grid, m.start())} {m.group(0).strip()[:50]}", float(px))
    # spacing: Tailwind classes extracted from parsed nodes (avoids matching visible prose)
    for tag, attrs, cls, anc, s, e in nodes:
        for c in cls:
            m = TW_SPACE_CLS.fullmatch(c)
            if not m:
                continue
            val = m.group(1)
            if val.startswith('['):
                px = re.fullmatch(r'\[(-?\d+(?:\.\d+)?)px\]', val)
                if px:
                    grid_check(f"L{line_of(txt, s)} {c}", float(px.group(1)))
            else:
                grid_check(f"L{line_of(txt, s)} {c}", float(val) * 4)

    if finetunes:
        share = len(finetunes)
        lines = list(dict.fromkeys(finetunes))
        add('INFO', 'grid', f"{share} spacing value(s) on the 4px fine-tune grid ({', '.join(lines[:6])}{', ...' if len(lines) > 6 else ''}); "
                            f"fine inside dense controls, prefer {grid}px multiples for layout spacing")

    # fonts
    fams = font_families(txt)
    if len(fams) > 2:
        add('FAIL', 'max-2-fonts', f"{len(fams)} font families: {sorted(fams)}")

    # contrast: plain CSS rules (comment-stripped, last declaration wins, 3:1 large text >=24px)
    css_for_wcag = strip_css_comments(re.sub(r'<!--.*?-->', ' ', txt, flags=re.S))
    for blk in re.finditer(r'\{([^{}]+)\}', css_for_wcag):
        b = blk.group(1)
        fgs = re.findall(rf'(?<![\w-])color\s*:\s*({HEX})', b)
        bgs = re.findall(rf'background(?:-color)?\s*:\s*({HEX})', b)
        if fgs and bgs:
            fg_h, bg_h = fgs[-1], bgs[-1]
            fs_m = re.findall(r'font-size\s*:\s*(\d+(?:\.\d+)?)(px|rem)', b)
            large = fs_m and _px(float(fs_m[-1][0]), fs_m[-1][1]) >= 24
            need = 3.0 if large else 4.5
            r = ratio(fg_h, bg_h)
            if r < need:
                add('FAIL' if r < 3 else 'WARN', 'wcag-aa',
                    f"L{line_of(css_for_wcag, blk.start())} {fg_h} on {bg_h} = {r:.2f}:1 (fix -> {fix_color(fg_h, bg_h, need)})")

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
        if not is_solid_cta(tag, attrs, cls, dark_page, tokens):
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
        if cr > want:
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

    # line length: each long <p> needs a readable max-width on itself or an ancestor (skipping multi-column grids)
    css_for_p = strip_css_comments('\n'.join(styles)) if styles else (
        '' if re.search(r'<(?:html|head|body|div|main|section|p|span)\b', masked, re.I) else strip_css_comments(txt)
    )
    css_p = re.search(r'(?:^|[\n}])\s*(?:p|article|\.prose)\s*(?:,\s*(?:p|article|\.prose))*\s*\{[^}]*max-width\s*:\s*(?:[4-7]\d|80)ch', css_for_p)
    bad = []
    for tag, attrs, cls, anc, s, e in nodes:
        if tag != 'p':
            continue
        if any(MULTI_COL.match(c) for a in anc for c in a[2]):
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
        iss = audit(p, a.grid, tokens, dark_tokens, a.mood, txt=p_txt)
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
