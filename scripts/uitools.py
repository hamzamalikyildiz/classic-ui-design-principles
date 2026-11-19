#!/usr/bin/env python3
"""UI design rule toolkit: contrast, type scale, nested radius, spacing snap, audit."""
import re, sys, argparse, colorsys, pathlib

def hex2rgb(h):
    h = h.strip().lstrip('#')
    if len(h) == 3: h = ''.join(c*2 for c in h)
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
    a.fg = tw_hex(a.fg, {}) or a.fg; a.bg = tw_hex(a.bg, {}) or a.bg
    r = ratio(a.fg, a.bg)
    out = f"{a.fg} on {a.bg}: {r:.2f}:1 | AA text(4.5): {'PASS' if r>=4.5 else 'FAIL'} | AA large/UI(3.0): {'PASS' if r>=3 else 'FAIL'}"
    print(out)
    if r < a.target: print(f"  fix -> {fix_color(a.fg, a.bg, a.target)} (>= {a.target}:1)")

RATIOS = {'minor-second':1.067,'major-second':1.125,'minor-third':1.2,'major-third':1.25,
          'perfect-fourth':1.333,'augmented-fourth':1.414,'perfect-fifth':1.5,'golden':1.618}

def cmd_scale(a):
    rt = RATIOS.get(a.ratio) or float(a.ratio)
    names = ['xs','sm','base','lg','xl','2xl','3xl','4xl','5xl']
    steps = range(-2, 7)
    print(f"/* type scale base={a.base}px ratio={rt} */\n:root {{")
    rows = []
    for n, s in zip(names, steps):
        px = a.base * rt**s
        px4 = max(4, round(px/ (2 if px < 24 else 4)) * (2 if px < 24 else 4))
        lh = round((px4 * (1.5 if s <= 1 else 1.2)) / 4) * 4
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
    m = re.fullmatch(r'\[(#[0-9a-fA-F]{3,6})\]', name)
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


def hsl2hex(h, s, l):
    r, g, b = colorsys.hls_to_rgb(h / 360, l / 100, s / 100)
    return rgb2hex([r * 255, g * 255, b * 255])


def css_tokens(texts):
    """CSS custom properties from :root blocks (shadcn v3 'H S% L%', hsl() or hex) -> {name: hex}."""
    tok = {}
    for txt in texts:
        for blk in re.findall(r':root\s*\{([^}]*)\}', txt):
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
TAG = re.compile(r"""<(/?)([A-Za-z][\w.]*)((?:[^>{}"']|"[^"]*"|'[^']*'|\{(?:[^{}]|\{[^{}]*\})*\})*?)(/?)>""")
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'}
READABLE_MAXW = re.compile(r'(?<![\w:-])max-w-(?:prose|xs|sm|md|lg|xl|2xl|\[(?:[4-7]\d|80)ch\])(?![\w-])|max-width\s*:\s*(?:[4-7]\d|80)ch')
BIG_TEXT = {'text-2xl', 'text-3xl', 'text-4xl', 'text-5xl', 'text-6xl', 'text-7xl', 'text-8xl', 'text-9xl'}
BOLD = {'font-semibold', 'font-bold', 'font-extrabold', 'font-black'}
BLOCK = re.compile(r'^(?:section|article|form|dialog|header|main|aside|Card|DialogContent|SheetContent|AlertDialogContent)$')
TEXT_NON_COLOR = re.compile(r'(?:xs|sm|base|lg|\d?xl|left|right|center|justify|start|end|wrap|nowrap|balance|pretty|ellipsis|clip|\[\d.*\])')


def classes(attrs):
    m = re.search(r"""class(?:Name)?\s*=\s*("[^"]*"|'[^']*'|\{(?:[^{}]|\{[^{}]*\})*\})""", attrs)
    if not m:
        return []
    v = m.group(1)
    if v.startswith('{'):
        parts = re.findall(r'"([^"]*)"|\'([^\']*)\'|`([^`]*)`', v)
        return ' '.join(''.join(p) for p in parts).split()
    return v[1:-1].split()


def walk(txt):
    """Yield (tag, attrs, classes, ancestors, start, end) for every opening tag; ancestors innermost-last."""
    stack = []
    for m in TAG.finditer(txt):
        close, tag, attrs, selfclose = m.groups()
        if close:
            for i in range(len(stack) - 1, -1, -1):
                if stack[i][0] == tag:
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
            found = val
    return found


def line_of(txt, pos):
    return txt.count('\n', 0, pos) + 1


def audit(path, grid, tokens):
    txt = pathlib.Path(path).read_text(encoding='utf-8', errors='ignore')
    issues = []

    def add(sev, rule, msg):
        issues.append((sev, rule, msg))

    def grid_check(label, v):
        v = abs(v)
        if v <= 2:
            return
        if v % 4:
            add('WARN', 'grid', f"{label} = {v:g}px, off the 4px grid")
        elif v % grid:
            add('INFO', 'grid', f"{label} = {v:g}px, 4px fine-tune; prefer {grid}px multiples")

    # spacing: CSS
    for m in re.finditer(rf'(?<![\w-]){SPACE_PROPS}\s*:\s*([^;}}"\n]+)', txt):
        for px in re.findall(r'(-?\d+(?:\.\d+)?)px', m.group(1)):
            grid_check(f"L{line_of(txt, m.start())} {m.group(0).strip()[:50]}", float(px))
    # spacing: Tailwind
    for m in TW_SPACE.finditer(txt):
        val = m.group(1)
        if val.startswith('['):
            px = re.fullmatch(r'\[(-?\d+(?:\.\d+)?)px\]', val)
            if px:
                grid_check(f"L{line_of(txt, m.start())} {m.group(0)}", float(px.group(1)))
        else:
            grid_check(f"L{line_of(txt, m.start())} {m.group(0)}", float(val) * 4)

    # fonts
    fams = set()
    for f in re.findall(r'font-family\s*:\s*([^;}\n]+)', txt):
        fam = f.split(',')[0].strip().strip('\'"')
        if not fam.startswith('var(') and fam not in ('inherit', 'initial', 'unset'):
            fams.add(fam)
    for url in re.findall(r'fonts\.googleapis\.com/[^"\'\s)]+', txt):
        for fam in re.findall(r'family=([^&:"\']+)', url):
            fams.add(fam.replace('+', ' '))
    for imp in re.findall(r'import\s*\{([^}]+)\}\s*from\s*["\']next/font/google["\']', txt):
        fams.update(x.strip() for x in imp.split(',') if x.strip())
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

    nodes = list(walk(txt))

    # contrast: Tailwind palette, arbitrary hex and shadcn tokens; background inherited from nearest ancestor
    seen = set()
    for variant, page_bg in (('', tokens.get('background', 'white')), ('dark:', None)):
        for tag, attrs, cls, anc, s, e in nodes:
            fg = pick(cls, 'text', variant)
            if not fg:
                continue
            bg = pick(cls, 'bg', variant)
            for a in reversed(anc):
                if bg:
                    break
                bg = pick(a[2], 'bg', variant)
            bg = bg or page_bg
            if not bg:
                continue
            fh, bh = tw_hex(fg, tokens), tw_hex(bg, tokens)
            if not fh or not bh:
                continue
            r = ratio(fh, bh)
            big = bool(BIG_TEXT & set(cls)) or ('text-xl' in cls and bool(BOLD & set(cls)))
            need = 3.0 if big else 4.5
            key = (variant, fg, bg, need)
            if r < need and key not in seen:
                seen.add(key)
                add('FAIL' if r < 3 else 'WARN', 'wcag-aa',
                    f"L{line_of(txt, s)} {variant}text-{fg} on {variant}bg-{bg} = {r:.2f}:1 (need {need:g}, fix -> {fix_color(fh, bh, need)})")

    # single primary CTA per block: raw buttons with solid bg, and shadcn <Button> default/destructive
    counts = {}
    for tag, attrs, cls, anc, s, e in nodes:
        solid = False
        if tag in ('button', 'a'):
            bg = pick(cls, 'bg')
            solid = bool(bg) and (bg in ('primary', 'destructive') or
                                  bool(re.fullmatch(r'\[#[0-9a-fA-F]{3,6}\]', bg)) or
                                  bool(re.fullmatch(r'[a-z]+-(?:[5-9]00|950)', bg)))
        elif tag == 'Button':
            var = re.search(r"""variant\s*=\s*(?:"([^"]*)"|'([^']*)'|\{\s*["']([^"']*)["']\s*\})""", attrs)
            v = ''.join(g or '' for g in var.groups()) if var else 'default'
            solid = v in ('default', 'destructive', 'primary')
        if not solid:
            continue
        idx = next((i for i in range(len(anc) - 1, -1, -1) if BLOCK.match(anc[i][0])), None)
        key = anc[idx][3] if idx is not None else -1
        counts.setdefault(key, []).append(line_of(txt, s))
    for lines in counts.values():
        if len(lines) > 1:
            add('WARN', 'single-primary-cta', f"{len(lines)} solid buttons in one block (lines {lines}); keep 1 solid, rest outline/ghost")

    # Miller: nav items
    for tag, attrs, cls, anc, s, e in nodes:
        if tag == 'nav':
            end = txt.find('</nav>', e)
            body = txt[e:end if end != -1 else len(txt)]
            n = len(re.findall(r'<(?:a|Link|NavLink)\b', body))
            if n > 7:
                add('WARN', 'miller-7', f"L{line_of(txt, s)} nav has {n} links (>7); group or move to an overflow menu")

    # line length: each long <p> needs a readable max-width on itself or an ancestor
    css_p = re.search(r'(?:^|[\s,}])(?:p|article|\.prose)\s*(?:,[^{]*)?\{[^}]*max-width\s*:\s*(?:[4-7]\d|80)ch', txt)
    bad = []
    for tag, attrs, cls, anc, s, e in nodes:
        if tag != 'p':
            continue
        end = txt.find('</p>', e)
        inner = re.sub(r'<[^>]+>|\{[^}]*\}', '', txt[e:end if end != -1 else e])
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
    return issues


def cmd_audit(a):
    paths = a.files + (a.css or [])
    tokens = css_tokens(pathlib.Path(p).read_text(encoding='utf-8', errors='ignore') for p in paths)
    total = {'FAIL': 0, 'WARN': 0, 'INFO': 0}
    for p in a.files:
        iss = audit(p, a.grid, tokens)
        print(f"== {p}: {len(iss)} issue(s)")
        for sev, rule, msg in iss:
            total[sev] += 1
            print(f"  [{sev}] {rule}: {msg}")
    print(f"\nSUMMARY FAIL={total['FAIL']} WARN={total['WARN']} INFO={total['INFO']}")
    sys.exit(1 if total['FAIL'] else 0)


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
d.set_defaults(f=cmd_audit)
a = ap.parse_args()
a.f(a)
