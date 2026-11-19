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
        return c/12.92 if c <= 0.03928 else ((c+0.055)/1.055)**2.4
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
SPACE_PROPS = r'(?:margin|padding|gap|row-gap|column-gap|top|right|bottom|left|inset)(?:-[a-z]+)?'
TW_SPACE = re.compile(r'(?<![\w-])-?(?:p|px|py|pt|pr|pb|pl|ps|pe|m|mx|my|mt|mr|mb|ml|ms|me|gap|gap-x|gap-y|space-x|space-y|top|left|right|bottom|inset)-(\[[^\]]+\]|[\d.]+)(?![\w.])')
HEX = r'#(?:[0-9a-fA-F]{3}){1,2}\b'

def audit(path, grid):
    txt = pathlib.Path(path).read_text(encoding='utf-8', errors='ignore')
    issues = []
    def add(sev, rule, msg): issues.append((sev, rule, msg))
    # spacing in CSS
    for m in re.finditer(rf'{SPACE_PROPS}\s*:\s*([^;}}"\n]+)', txt):
        for px in re.findall(r'(-?\d+(?:\.\d+)?)px', m.group(1)):
            v = abs(float(px))
            if v not in (0, 1, 2) and v % grid:
                add('WARN', '8pt-grid', f"{m.group(0).strip()[:60]} -> {px}px not multiple of {grid}")
    # tailwind spacing
    for m in TW_SPACE.finditer(txt):
        val = m.group(1)
        if val.startswith('['):
            px = re.match(r'\[(-?\d+(?:\.\d+)?)px\]', val)
            if px and abs(float(px.group(1))) % grid and abs(float(px.group(1))) > 2:
                add('WARN', '8pt-grid', f"{m.group(0)} arbitrary value off-grid")
        else:
            v = float(val) * 4
            if v % grid and v > 2:
                add('INFO', '8pt-grid', f"{m.group(0)} = {v:g}px (4px fine-tune; prefer {grid}px multiples)")
    # fonts
    fams = set()
    for f in re.findall(r'font-family\s*:\s*([^;}\n]+)', txt):
        fams.add(f.split(',')[0].strip().strip('\'"'))
    for url in re.findall(r'fonts\.googleapis\.com/[^"\'\s)]+', txt):
        for fam in re.findall(r'family=([^&:"\']+)', url): fams.add(fam.replace('+', ' '))
    fams.discard('inherit'); fams.discard('var(--font-sans)')
    if len(fams) > 2: add('FAIL', 'max-2-fonts', f"{len(fams)} font families: {sorted(fams)}")
    # contrast: CSS rules with both color and background
    for blk in re.finditer(r'\{([^{}]+)\}', txt):
        b = blk.group(1)
        fg = re.search(rf'(?<!-)color\s*:\s*({HEX})', b)
        bg = re.search(rf'background(?:-color)?\s*:\s*({HEX})', b)
        if fg and bg:
            r = ratio(fg.group(1), bg.group(1))
            if r < 4.5:
                sev = 'FAIL' if r < 3 else 'WARN'
                add(sev, 'wcag-aa', f"{fg.group(1)} on {bg.group(1)} = {r:.2f}:1 (fix fg -> {fix_color(fg.group(1), bg.group(1), 4.5)})")
    # contrast: tailwind arbitrary hex on same element
    for cls in re.findall(r'class(?:Name)?\s*=\s*["\'`]([^"\'`]+)', txt):
        fg = re.search(rf'text-\[({HEX})\]', cls); bg = re.search(rf'bg-\[({HEX})\]', cls)
        if fg and bg:
            r = ratio(fg.group(1), bg.group(1))
            if r < 4.5: add('FAIL' if r < 3 else 'WARN', 'wcag-aa', f"text-[{fg.group(1)}] on bg-[{bg.group(1)}] = {r:.2f}:1")
    # primary CTA count per section/card
    blocks = re.split(r'<(?:section|article|form|dialog|header|main)\b', txt) or [txt]
    solid = re.compile(r'<(?:button|a)\b[^>]*class(?:Name)?\s*=\s*["\'`][^"\'`]*\bbg-(?!transparent|white|black/|gray-50|gray-100|slate-50|slate-100|zinc-50|zinc-100|neutral-50|neutral-100|inherit)[a-z]+-(?:[5-9]00|950)\b', re.S)
    for i, b in enumerate(blocks):
        n = len(solid.findall(b))
        if n > 1: add('WARN', 'single-primary-cta', f"block #{i}: {n} solid buttons; keep 1 solid, others outline/ghost")
    # nav item count (Miller)
    for nav in re.findall(r'<nav\b.*?</nav>', txt, re.S):
        n = len(re.findall(r'<a\b', nav))
        if n > 7: add('WARN', 'miller-7', f"nav has {n} links (>7); group or move to overflow menu")
    # line length
    if re.search(r'<p\b', txt) and not re.search(r'max-w-(?:prose|\[\d+ch\]|[a-z0-9]+)|max-width\s*:\s*\d+(?:ch|rem|px)', txt):
        add('WARN', 'line-length', "paragraphs present but no max-width (use max-w-prose / 65ch)")
    # empty/loading states hint
    if re.search(r'\.map\(|v-for|\*ngFor|\{#each', txt) and not re.search(r'(?i)skeleton|empty|no (?:data|results|items)|animate-pulse', txt):
        add('INFO', 'skeleton-empty', "list rendering without skeleton/empty state")
    # radius nesting hint
    if re.search(r'rounded-(?:2xl|3xl)[^"\']*p-', txt) and re.search(r'rounded-(?:2xl|3xl)', txt):
        rs = re.findall(r'rounded-(\w+)', txt)
        if len(set(rs)) > 4: add('INFO', 'nested-radius', f"{len(set(rs))} different radii; verify inner = outer - padding")
    return issues

def cmd_audit(a):
    total = {'FAIL':0,'WARN':0,'INFO':0}
    for p in a.files:
        iss = audit(p, a.grid)
        print(f"== {p}: {len(iss)} issue(s)")
        for sev, rule, msg in iss:
            total[sev] += 1
            print(f"  [{sev}] {rule}: {msg}")
    print(f"\nSUMMARY FAIL={total['FAIL']} WARN={total['WARN']} INFO={total['INFO']}")
    sys.exit(1 if total['FAIL'] else 0)

ap = argparse.ArgumentParser()
sp = ap.add_subparsers(dest='cmd', required=True)
c = sp.add_parser('contrast'); c.add_argument('fg'); c.add_argument('bg'); c.add_argument('--target', type=float, default=4.5); c.set_defaults(f=cmd_contrast)
s = sp.add_parser('scale'); s.add_argument('--base', type=float, default=16); s.add_argument('--ratio', default='major-third'); s.set_defaults(f=cmd_scale)
r = sp.add_parser('radius'); r.add_argument('outer', type=float); r.add_argument('padding', type=float); r.set_defaults(f=cmd_radius)
n = sp.add_parser('snap'); n.add_argument('values', type=float, nargs='+'); n.add_argument('--grid', type=int, default=8); n.set_defaults(f=cmd_snap)
d = sp.add_parser('audit'); d.add_argument('files', nargs='+'); d.add_argument('--grid', type=int, default=4); d.set_defaults(f=cmd_audit)
a = ap.parse_args(); a.f(a)
