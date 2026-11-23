#!/usr/bin/env python3
"""UI design rule toolkit: contrast, type scale, nested radius, spacing snap, audit."""
import re, sys, argparse, colorsys, pathlib, urllib.parse

_SCRIPTS_DIR = str(pathlib.Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from uiignore import apply_ignores, filter_baseline, issue_hash, load_baseline, write_baseline
from uiroute import (
    COMPONENT_RULE_NOTE,
    SCREEN_RULES,
    VirtualMarkup,
    compose_route,
    find_project_root,
    inline_local_components,
    is_component_file,
)
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
    extract_cva_metadata,
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
    ClassCombination,
    ClassSet,
    _has_row_flex,
    _strip_all_comments,
    _strip_at_blocks,
    _strip_css_blocks,
    classes,
    expand_combinations,
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


def _is_solid_bg_cls(cls, dark_page=False, tokens=None):
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


def is_solid_cta(tag, attrs, cls, dark_page=False, tokens=None):
    if tag in ('button', 'a'):
        return _is_solid_bg_cls(cls, dark_page, tokens)
    if tag == 'Button':
        var = re.search(r"""variant\s*=\s*(?:"([^"]*)"|'([^']*)'|\{\s*["']([^"']*)["']\s*\})""", attrs)
        if var:
            v = ''.join(g or '' for g in var.groups())
            return v in ('default', 'destructive', 'primary')
        if _is_solid_bg_cls(cls, dark_page, tokens):
            return True
        bg = pick(cls, 'bg')
        if bg in BG_PASSTHROUGH or bg in ('background', 'secondary', 'muted', 'accent') or any(
            c == 'border' or c.startswith(('border-', 'hover:bg-', 'underline')) for c in cls
        ):
            return False
        if re.search(r'variant\s*=\s*\{', attrs):
            m = re.search(r'variant\s*=\s*(\{(?:[^{}]|\{[^{}]*\})*\})', attrs)
            if m:
                lits = [a or b for a, b in re.findall(r'"([^"]*)"|\'([^\']*)\'', m.group(1))]
                if lits:
                    return any(v in ('default', 'destructive', 'primary') for v in lits)
        return True
    return False


def _strip_outer_parens(s):
    s = s.strip()
    while s.startswith('(') and s.endswith(')'):
        depth = 0
        ok = True
        for idx, ch in enumerate(s):
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
                if depth == 0 and idx < len(s) - 1:
                    ok = False
                    break
        if ok and depth == 0:
            s = s[1:-1].strip()
        else:
            break
    return s


def _split_label_atoms(label_str):
    if not label_str:
        return []
    atoms = []
    buf = []
    depth = 0
    quote = None
    for ch in label_str:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in ('"', "'"):
            quote = ch
            buf.append(ch)
            continue
        if ch in ('(', '[', '{'):
            depth += 1
        elif ch in (')', ']', '}'):
            depth = max(0, depth - 1)
        elif ch == ',' and depth == 0:
            s = ''.join(buf).strip()
            if s:
                atoms.append(s)
            buf = []
            continue
        buf.append(ch)
    s = ''.join(buf).strip()
    if s:
        atoms.append(s)
    return atoms


def _extract_cond_bindings(labels_iter):
    """Parse condition labels into canonical bindings dict; return (bindings, is_consistent)."""
    bindings = {}

    def _bind(k, v):
        if k in bindings and bindings[k] != v:
            return False
        bindings[k] = v
        return True

    for lbl in labels_iter:
        for atom in _split_label_atoms(lbl):
            parts = re.split(r'(?<![!=<>])=(?!=)', atom, maxsplit=1)
            if len(parts) == 2:
                raw_cond, raw_val = _strip_outer_parens(parts[0]), parts[1].strip()
            else:
                raw_cond, raw_val = _strip_outer_parens(atom), 'true'
            while raw_cond.startswith('!') and not raw_cond.startswith('!='):
                raw_cond = _strip_outer_parens(raw_cond[1:])
                if raw_val == 'true':
                    raw_val = 'false'
                elif raw_val == 'false':
                    raw_val = 'true'
                else:
                    break
            m = re.fullmatch(r'(.+?)\s*(===|==|!==|!=)\s*(.+)', raw_cond)
            if m:
                lhs = _strip_outer_parens(m.group(1))
                op = m.group(2)
                rhs = _strip_outer_parens(m.group(3)).strip('\'"')
                is_eq = op in ('===', '==')
                eff_true = (raw_val == 'true') if is_eq else (raw_val == 'false')
                eff_false = (raw_val == 'false') if is_eq else (raw_val == 'true')
                if eff_true:
                    if not _bind(('eq_pair', lhs, rhs), 'true'):
                        return bindings, False
                    if not _bind(('eq_val', lhs), rhs):
                        return bindings, False
                    if rhs in ('true', 'false') and not _bind(('bool', lhs), rhs):
                        return bindings, False
                elif eff_false:
                    if not _bind(('eq_pair', lhs, rhs), 'false'):
                        return bindings, False
                    if rhs in ('true', 'false'):
                        flipped = 'false' if rhs == 'true' else 'true'
                        if not _bind(('bool', lhs), flipped):
                            return bindings, False
                else:
                    if not _bind(('raw', raw_cond), raw_val):
                        return bindings, False
                continue
            if raw_val in ('true', 'false'):
                if not _bind(('bool', raw_cond), raw_val):
                    return bindings, False
                if not _bind(('eq_pair', raw_cond, 'true'), raw_val):
                    return bindings, False
            elif raw_val in ('empty', 'set'):
                if not _bind(('fallback', raw_cond), raw_val):
                    return bindings, False
            else:
                clean_val = raw_val.strip('\'"')
                if not _bind(('eq_pair', raw_cond, clean_val), 'true'):
                    return bindings, False
                if not _bind(('eq_val', raw_cond), clean_val):
                    return bindings, False

    for (kind, *rest), val in list(bindings.items()):
        if kind == 'eq_val':
            lhs = rest[0]
            if bindings.get(('eq_pair', lhs, val)) == 'false':
                return bindings, False
    return bindings, True


def _branch_affects_contrast(alts):
    for alt in alts:
        for c in alt:
            base_c = c.rsplit(':', 1)[-1]
            if base_c.startswith(('bg-', 'from-', 'via-', 'to-')):
                return True
            if base_c.startswith('text-'):
                val = base_c[5:]
                if not TEXT_NON_COLOR.fullmatch(val) or base_c in BIG_TEXT or base_c == 'text-xl':
                    return True
            if base_c in BOLD:
                return True
    return False


def _branch_affects_bg(alts):
    for alt in alts:
        for c in alt:
            base_c = c.rsplit(':', 1)[-1]
            if base_c.startswith(('bg-', 'from-', 'via-', 'to-')):
                return True
    return False


def _get_node_combos(elem, cls_fallback, combos_cache, limit=8):
    key = id(elem)
    if key in combos_cache:
        return combos_cache[key]
    cs = getattr(elem, 'classset', None)
    if cs is None:
        cs = ClassSet(base=list(cls_fallback))
    combos = expand_combinations(cs, limit=limit)
    combos_cache[key] = (cs, combos)
    return cs, combos


def _iter_chain_combinations(node, anc, combos_cache, limit=8):
    """Yield `(chain_classes, branch_label)` for consistent combinations of `node` and `anc`."""
    node_cs, node_combos = _get_node_combos(node, node[2], combos_cache, limit=limit)
    rev_anc = list(reversed(anc))

    anc_entries = []
    any_anc_branches = False
    for a in rev_anc:
        a_cs = getattr(a, 'classset', None)
        if a_cs and a_cs.branches and any(_branch_affects_bg(alts) for _, alts in a_cs.branches):
            _, a_combos = _get_node_combos(a, a[2], combos_cache, limit=limit)
            bg_gids = {gid for gid, alts in a_cs.branches if _branch_affects_bg(alts)}
            anc_entries.append((a_cs, a_combos, bg_gids))
            if len(a_combos) > 1 or (a_combos and a_combos[0].labels):
                any_anc_branches = True
        else:
            anc_entries.append((None, [ClassCombination(list(a[2]), '', labels=(), choices={})], set()))

    if len(node_combos) == 1 and not node_combos[0].labels and not any_anc_branches:
        return [([node_combos[0].classes] + [ae[1][0].classes for ae in anc_entries], '')]

    node_contrast_gids = {gid for gid, alts in (node_cs.branches if node_cs else ()) if _branch_affects_contrast(alts)}
    all_entries = [(node_cs, node_combos, node_contrast_gids)] + anc_entries

    jsx_labels = []
    for elem in [node] + rev_anc:
        bl = getattr(elem, 'branch_label', None)
        if bl and '=' in bl:
            jsx_labels.append(bl)
    base_bindings, ok = _extract_cond_bindings(jsx_labels)
    if not ok:
        base_bindings = {}

    def _search(initial_bindings):
        out = []
        n_levels = len(all_entries)

        def _dfs(idx, acc_classes, acc_labels, cur_bindings):
            if len(out) >= limit:
                return
            if idx == n_levels:
                out.append((list(acc_classes), ', '.join(acc_labels)))
                return
            cs_i, combos_i, rel_gids = all_entries[idx]
            if len(combos_i) == 1 and not combos_i[0].labels:
                acc_classes.append(combos_i[0].classes)
                _dfs(idx + 1, acc_classes, acc_labels, cur_bindings)
                acc_classes.pop()
                return
            for combo in combos_i:
                if len(out) >= limit:
                    return
                c_bindings, c_ok = _extract_cond_bindings(combo.labels)
                if not c_ok:
                    continue
                if any(k in cur_bindings and cur_bindings[k] != v for k, v in c_bindings.items()):
                    continue
                nxt_bindings = {**cur_bindings, **c_bindings}
                conflict = False
                if cur_bindings and c_bindings:
                    for (kind, *rest), val in nxt_bindings.items():
                        if kind == 'eq_val' and nxt_bindings.get(('eq_pair', rest[0], val)) == 'false':
                            conflict = True
                            break
                if conflict:
                    continue
                nxt_labels = list(acc_labels)
                if rel_gids and combo.choices:
                    for gid, _ in (cs_i.branches if cs_i else ()):
                        if gid in rel_gids and gid in combo.choices:
                            lbl = combo.choices[gid][1]
                            if lbl and lbl not in nxt_labels:
                                nxt_labels.append(lbl)
                acc_classes.append(combo.classes)
                _dfs(idx + 1, acc_classes, nxt_labels, nxt_bindings)
                acc_classes.pop()

        _dfs(0, [], [], initial_bindings)
        return out

    results = _search(base_bindings)
    if not results and base_bindings:
        results = _search({})
    if not results:
        results = [([node_combos[0].classes] + [ae[1][0].classes for ae in anc_entries], node_combos[0].label)]
    return results


def _max_simultaneous_ctas(items):
    """Return list of line numbers for the largest subset of CTA items visible simultaneously."""
    if len(items) <= 1:
        return [it[0] for it in items]
    if all(not it[1] and it[2] == [{}] for it in items):
        return [it[0] for it in items]

    m = len(items)
    best = []
    steps = [0]
    max_steps = 512

    def _dfs(idx, chosen_lines, reg_map, cond_map):
        nonlocal best
        if len(chosen_lines) > len(best):
            best = list(chosen_lines)
        if idx >= m or len(chosen_lines) + (m - idx) <= len(best) or steps[0] >= max_steps:
            return
        steps[0] += 1
        line_no, b_regs, c_opts = items[idx]
        reg_ok = all(rid not in reg_map or reg_map[rid] == bidx for rid, bidx in b_regs)
        if reg_ok:
            nxt_reg = {**reg_map, **dict(b_regs)} if b_regs else reg_map
            for opt in c_opts:
                if all(k not in cond_map or cond_map[k] == v for k, v in opt.items()):
                    nxt_cond = {**cond_map, **opt} if opt else cond_map
                    conflict = False
                    if opt and cond_map:
                        for (kind, *rest), val in nxt_cond.items():
                            if kind == 'eq_val' and nxt_cond.get(('eq_pair', rest[0], val)) == 'false':
                                conflict = True
                                break
                    if not conflict:
                        chosen_lines.append(line_no)
                        _dfs(idx + 1, chosen_lines, nxt_reg, nxt_cond)
                        chosen_lines.pop()
                        if len(chosen_lines) + (m - idx) <= len(best) or steps[0] >= max_steps:
                            return
        if len(chosen_lines) + (m - idx - 1) > len(best) and steps[0] < max_steps:
            _dfs(idx + 1, chosen_lines, reg_map, cond_map)

    _dfs(0, [], {}, {})
    return best


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
    for node in nodes:
        tag, attrs, cls, anc, s, e = node
        cs = getattr(node, 'classset', None)
        combos = expand_combinations(cs, limit=8) if cs and cs.branches else [ClassCombination(list(cls), '')]
        for combo in combos:
            if combo.labels and not _extract_cond_bindings(combo.labels)[1]:
                continue
            c_cls = combo.classes
            if is_solid_cta(tag, attrs, c_cls, dark, tokens):
                h = height_px(c_cls)
                if h is not None and h < 40:
                    out.append(('WARN' if (_STRICT or h < 24) else 'INFO', 'fitts-primary',
                                f"L{line_of(txt, s)} primary CTA is {h:g}px tall; use >=44px (h-11+), hero CTA h-12..h-14"))
                    break

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
# Style and taste findings: INFO by default, kept at their old WARN level with --strict.
# The floor (wcag-aa, landmark-main, reveal-needs-js, line-length, tr-uppercase) never moves.
SOFT_RULES = {'grid', 'single-primary-cta', 'miller-7', 'no-hero-surface', 'card-sameness', 'bold-headline-size',
              'no-drawn-mascot', 'grey-chart', 'edge-align', 'headline-measure', 'left-stacked-column', 'editorial-leading'}
SOFT_NOTE = ' [style suggestion; --strict keeps WARN]'
_STRICT = False

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


_TR_CHARS_RE = re.compile(r'[ğüşıöçĞÜŞİÖÇ]')
_LANG_TR_RE = re.compile(r'\blang\s*=\s*(?:["\']tr(?:-[A-Za-z]+)?["\']|\{["\']tr(?:-[A-Za-z]+)?["\']\})', re.I)
_THEME_TOGGLE_RE = re.compile(
    r'(?:ThemeToggle|setTheme|next-themes|useTheme|data-theme-toggle|classList\.toggle\s*\(\s*[\'"]dark[\'"]\s*\)|toggleTheme)'
)
_HARDCODED_CURRENCY_TOFIXED_RE = re.compile(
    r'(?:[$€₺%]|\b(?:TL|USD)\b)[^;\n]{0,40}\.toFixed\s*\(|\.toFixed\s*\([^)]*\)[^;\n]{0,20}(?:[$€₺%]|\b(?:TL|USD)\b)'
)
_HARDCODED_DATE_RE = re.compile(
    r'\$\{[^}]*getDate\s*\(\s*\)\s*\}\s*/|getMonth\s*\(\s*\)\s*\+\s*1'
)
_NUMERIC_CELL_RE = re.compile(r'^[\s$€₺%+\-\u2212]*\d[\d.,\s%$€₺]*$')


def _audit_static_rules_a8(raw_txt, txt, masked, nodes, dark_tokens, mood, route_mode):
    """Run İP-A8 static rules: tr-uppercase, numeric-columns, heading-wrap, theme-toggle-missing, hardcoded-locale-format, shadcn-defaults."""
    out = []

    # 1. tr-uppercase (WARN)
    has_uppercase = (
        any('uppercase' in cls for _, _, cls, _, _, _ in nodes)
        or bool(re.search(r'text-transform\s*:\s*uppercase', txt, re.I))
    )
    if has_uppercase and _TR_CHARS_RE.search(txt) and not _LANG_TR_RE.search(txt):
        out.append(('WARN', 'tr-uppercase', 'uppercase transform with Turkish characters but missing lang="tr" on root/ancestor; i/I casing may corrupt'))

    # 2. numeric-columns (INFO)
    def _inner_text(tag, end_open):
        close_idx = masked.find(f'</{tag}>', end_open)
        if close_idx == -1:
            return ''
        return re.sub(r'<[^>]+>', '', masked[end_open:close_idx]).strip()

    has_tabular_css = bool(re.search(r'font-variant-numeric\s*:\s*tabular-nums', txt, re.I))
    if not has_tabular_css:
        numeric_td_without_tabular = 0
        for tag, attrs, cls, anc, s, e in nodes:
            if tag == 'td':
                inner = _inner_text(tag, e)
                if inner and _NUMERIC_CELL_RE.match(inner):
                    chain_cls = set(cls)
                    for a in anc:
                        chain_cls.update(a[2])
                    if 'tabular-nums' not in chain_cls:
                        numeric_td_without_tabular += 1
        has_kpi_without_tabular = False
        for tag, attrs, cls, anc, s, e in nodes:
            if tag in ('div', 'span', 'p', 'dd') and any(k in ' '.join(cls).lower() for k in ('kpi', 'metric', 'stat')):
                inner = _inner_text(tag, e)
                if inner and _NUMERIC_CELL_RE.match(inner):
                    chain_cls = set(cls)
                    for a in anc:
                        chain_cls.update(a[2])
                    if 'tabular-nums' not in chain_cls:
                        has_kpi_without_tabular = True
                        break
        if numeric_td_without_tabular >= 2 or has_kpi_without_tabular:
            out.append(('INFO', 'numeric-columns', 'numeric table cells or KPI values without tabular-nums; add tabular-nums for aligned digits'))

    # 3. heading-wrap (INFO, max 1 per file)
    has_css_balance = bool(re.search(r'text-wrap\s*:\s*balance', txt, re.I))
    has_css_pretty = bool(re.search(r'text-wrap\s*:\s*pretty', txt, re.I))
    heading_missing = False
    para_missing = False
    for tag, attrs, cls, anc, s, e in nodes:
        if tag in ('h1', 'h2', 'h3') and not has_css_balance:
            if 'text-balance' not in cls and not re.search(r'text-wrap\s*:\s*balance', attrs, re.I):
                heading_missing = True
                break
    if not heading_missing and not has_css_pretty:
        for tag, attrs, cls, anc, s, e in nodes:
            if tag == 'p':
                inner = _inner_text(tag, e)
                if len(inner) >= 80 and 'text-pretty' not in cls and not re.search(r'text-wrap\s*:\s*pretty', attrs, re.I):
                    para_missing = True
                    break
    if heading_missing or para_missing:
        out.append(('INFO', 'heading-wrap', 'headings without text-balance or long paragraphs without text-pretty; add text-balance / text-pretty'))

    # 4. theme-toggle-missing (INFO, WARN in route_mode)
    has_dark_mode = (
        bool(dark_tokens)
        or '[data-theme="dark"]' in txt
        or "[data-theme='dark']" in txt
        or any(c.startswith('dark:') for _, _, cls, _, _, _ in nodes for c in cls)
        or bool(re.search(r'\bdark:[a-zA-Z0-9_-]+', txt))
    )
    if has_dark_mode and not _THEME_TOGGLE_RE.search(txt):
        sev = 'WARN' if route_mode else 'INFO'
        out.append((sev, 'theme-toggle-missing', 'dark mode tokens or dark: classes found without a visible theme toggle (ThemeToggle / setTheme / useTheme)'))

    # 5. hardcoded-locale-format (INFO)
    if _HARDCODED_CURRENCY_TOFIXED_RE.search(txt) or _HARDCODED_DATE_RE.search(txt):
        out.append(('INFO', 'hardcoded-locale-format', 'hardcoded currency/percent .toFixed() or manual date concatenation; use Intl.NumberFormat / Intl.DateTimeFormat'))

    # 6. shadcn-defaults (INFO)
    cva_meta = extract_cva_metadata(raw_txt)
    shadcn_hits = []
    for entry in cva_meta.get('shadcn_defaults', []):
        comp = (entry.get('component') or entry.get('var_name') or '').lower()
        tok = entry.get('token', '')
        opt = (entry.get('option') or '').lower()
        if entry.get('kind') == 'small-height' and 'button' in comp and opt in ('default', 'sm', 'base') and tok == 'h-8':
            shadcn_hits.append(f"Button {opt} uses {tok}")
        elif entry.get('kind') == 'micro-text' and 'badge' in comp and tok in ('text-[10px]', 'text-[11px]'):
            shadcn_hits.append(f"Badge uses {tok}")
    if mood in ('trust', 'playful', 'bold'):
        for tag, attrs, cls, anc, s, e in nodes:
            if tag.lower() == 'card' or 'card' in ' '.join(cls).lower():
                if 'border' in cls and not any(c in cls for c in ('shadow-sm', 'shadow-md', 'shadow-lg', 'border-transparent')):
                    shadcn_hits.append(f"Card in {mood} mood uses flat border without shadow-sm/md/lg")
                    break
    if shadcn_hits:
        out.append(('INFO', 'shadcn-defaults', f"shadcn default styling detected ({'; '.join(shadcn_hits[:3])})"))

    return out


def audit(
    path,
    grid,
    tokens,
    dark_tokens=None,
    mood=None,
    txt=None,
    return_suppressed=False,
    *,
    strict=False,
    route_mode=False,
    root_dir=None,
    tsconfig_path=None,
):
    global _STRICT
    _STRICT = bool(strict)
    if txt is None:
        raw_txt = pathlib.Path(path).read_text(encoding='utf-8', errors='ignore')
    elif isinstance(txt, VirtualMarkup):
        raw_txt = txt.raw_txt
    else:
        raw_txt = txt

    if isinstance(txt, VirtualMarkup):
        pass
    elif route_mode:
        txt = compose_route(path, txt=raw_txt, root_dir=root_dir, tsconfig_path=tsconfig_path)
    else:
        suf = pathlib.Path(path).suffix.lower() if path else ''
        if suf not in ('.html', '.htm', '.css'):
            txt = inline_local_components(raw_txt, source_path=path, root_dir=root_dir, tsconfig_path=tsconfig_path)
        else:
            txt = raw_txt

    component_file = is_component_file(path, txt=raw_txt, route_mode=route_mode)
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

    # conditional branch combinations (>8 branch explosion check, at most once per node)
    combos_cache = {}
    for node in nodes:
        tag, attrs, cls, anc, s, e = node
        cs, _ = _get_node_combos(node, cls, combos_cache, limit=8)
        if cs.exploded:
            add('INFO', 'branch-explosion', f"L{line_of(txt, s)} >8 conditional class combinations; auditing first 8 branches")

    # contrast: Tailwind palette, arbitrary hex and shadcn tokens; background composited from ancestors
    seen = set()
    page = 'background' if 'background' in tokens else (f'[{cbg}]' if (cbg := css_page_bg(txt, tokens)) else 'white')
    passes = [('', '', tokens, page, None), ('dark:', 'dark:', tokens, None, None)]
    if dark_tokens:  # shadcn .dark theme: same classes re-evaluated with dark token values
        passes.append(('', '[.dark] ', {**tokens, **dark_tokens}, 'background' if 'background' in dark_tokens else None, dark_tokens))
    for variant, label, tokens, page_bg, only in passes:
        for node in nodes:
            tag, attrs, cls, anc, s, e = node
            styles_chain = [attrs] + [a[1] for a in reversed(anc)]
            for chain_cls, branch_lbl in _iter_chain_combinations(node, anc, combos_cache, limit=8):
                c_cls = chain_cls[0]
                fg = pick(c_cls, 'text', variant)
                if not fg:
                    continue
                res = backdrop(chain_cls, variant, tokens, page_bg, styles_chain)
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
                big = bool(BIG_TEXT & set(c_cls)) or ('text-xl' in c_cls and bool(BOLD & set(c_cls)))
                need = 3.0 if big else 4.5
                key = (label, fg, bg, need)
                if r < need and key not in seen:
                    seen.add(key)
                    tw = tw_same_hue(fg, bh, need)
                    bg_fix = tw_bg_same_hue(bg.split(' over ')[0][3:], fh, need) if not tw else None
                    fix = f"text-{tw}" if tw else (f"bg-{bg_fix}" if bg_fix else fix_color(fh, bh, need))
                    b_prefix = f"[{branch_lbl}] " if branch_lbl else ""
                    add('FAIL' if r < 3 else 'WARN', 'wcag-aa',
                        f"L{line_of(txt, s)} {b_prefix}{label}text-{fg} on {bg} = {r:.2f}:1 (need {need:g}, fix -> {fix}, keep the hue)")

    tokens = passes[0][2]

    # contrast on gradients: text must pass against every color stop of the nearest gradient
    gseen = set()
    for node in nodes:
        tag, attrs, cls, anc, s, e = node
        for chain_cls, branch_lbl in _iter_chain_combinations(node, anc, combos_cache, limit=8):
            c_cls = chain_cls[0]
            fg = pick(c_cls, 'text')
            if not fg:
                continue
            g = None
            for c in chain_cls:
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
            big = bool(BIG_TEXT & set(c_cls)) or ('text-xl' in c_cls and bool(BOLD & set(c_cls)))
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
                    b_prefix = f"[{branch_lbl}] " if branch_lbl else ""
                    add('FAIL' if r < 3 else 'WARN', 'wcag-aa',
                        f"L{line_of(txt, s)} {b_prefix}text-{fg} on gradient stop {x} = {r:.2f}:1 (need {need:g}); text must pass against every stop, darken that stop within its hue")

    # single primary CTA per block: raw buttons with solid bg, and shadcn <Button> default/destructive
    dark_page = is_dark_page(txt, tokens)
    counts = {}
    for node in nodes:
        tag, attrs, cls, anc, s, e = node
        if tag not in ('button', 'a', 'Button'):
            continue
        cs, raw_combos = _get_node_combos(node, cls, combos_cache, limit=8)
        if cs.branches:
            consistent_combos = []
            for c in raw_combos:
                b_map, c_ok = _extract_cond_bindings(c.labels)
                if c_ok:
                    consistent_combos.append((c, b_map))
            if not consistent_combos:
                consistent_combos = [(c, {}) for c in raw_combos]
            solid_envs = [b_map for c, b_map in consistent_combos if is_solid_cta(tag, attrs, c.classes, dark_page, tokens)]
            if not solid_envs:
                continue
            if len(solid_envs) == len(consistent_combos):
                solid_envs = [{}]
        else:
            if not is_solid_cta(tag, attrs, cls, dark_page, tokens):
                continue
            solid_envs = [{}]

        b_regions = getattr(node, 'branch_regions', ()) or ()
        jsx_lbls = [
            getattr(x, 'branch_label', None)
            for x in ([node] + list(anc))
            if getattr(x, 'branch_label', None) and '=' in getattr(x, 'branch_label', '')
        ]
        jsx_env, j_ok = _extract_cond_bindings(jsx_lbls)
        if not j_ok:
            jsx_env = {}
        cond_options = []
        for s_env in solid_envs:
            if all(k not in jsx_env or jsx_env[k] == v for k, v in s_env.items()):
                merged = {**jsx_env, **s_env}
                if merged not in cond_options:
                    cond_options.append(merged)
        if not cond_options:
            cond_options = [jsx_env]

        idx = next((i for i in range(len(anc) - 1, -1, -1) if BLOCK.match(anc[i][0])), None)
        key = anc[idx][3] if idx is not None else -1
        counts.setdefault(key, []).append((line_of(txt, s), b_regions, cond_options))
    screen_cta_issue_idxs = set()
    for block_key, block_items in counts.items():
        lines = _max_simultaneous_ctas(block_items)
        if len(lines) > 1:
            if block_key == -1:
                screen_cta_issue_idxs.add(len(issues))
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
    issues.extend(_audit_static_rules_a8(raw_txt, txt, masked, nodes, dark_tokens, mood, route_mode))
    if component_file:
        downgraded = []
        for idx_i, (sev, r, m) in enumerate(issues):
            if r in SCREEN_RULES or (r == 'single-primary-cta' and idx_i in screen_cta_issue_idxs):
                note_m = m if m.endswith(COMPONENT_RULE_NOTE) else m + COMPONENT_RULE_NOTE
                downgraded.append(('INFO', r, note_m))
            else:
                downgraded.append((sev, r, m))
        issues = downgraded
    if mood in EXPRESSIVE:
        issues = [(('INFO', r, m + ' [relaxed in expressive moods]') if sev != 'INFO' and r in RELAXED else (sev, r, m))
                  for sev, r, m in issues]
    if not strict:
        issues = [('INFO', r, m + SOFT_NOTE) if (sev == 'WARN' and r in SOFT_RULES) else (sev, r, m) for sev, r, m in issues]
    kept, suppressed, meta = apply_ignores(raw_txt, issues)
    final_issues = kept + meta
    if return_suppressed:
        return final_issues, suppressed
    return final_issues


def _expand_routes_glob(patterns, root_dir=None):
    base = pathlib.Path(root_dir).resolve() if root_dir else pathlib.Path.cwd()
    found = []
    seen = set()
    for pat in patterns:
        p_obj = pathlib.Path(pat)
        if p_obj.is_absolute():
            anchor = pathlib.Path(p_obj.anchor)
            rel_pat = str(p_obj.relative_to(anchor))
            matches = sorted(anchor.glob(rel_pat))
        else:
            matches = sorted(base.glob(pat))
        for m in matches:
            if m.is_file():
                rm = str(m.resolve())
                if rm not in seen:
                    seen.add(rm)
                    found.append(str(m))
    return found


def cmd_audit(a):
    if a.grid <= 0:
        sys.exit(f"error: --grid must be > 0 (got {a.grid})")
    route_arg_lists = getattr(a, 'routes', None) or []
    route_paths = [p for grp in route_arg_lists for p in grp]
    routes_glob_pats = getattr(a, 'routes_glob', None) or []
    root_dir = getattr(a, 'root', None)
    tsconfig_path = getattr(a, 'tsconfig', None)

    if tsconfig_path and not pathlib.Path(tsconfig_path).is_file():
        sys.exit(f"error: tsconfig not found: {tsconfig_path}")

    glob_routes = _expand_routes_glob(routes_glob_pats, root_dir=root_dir) if routes_glob_pats else []
    if routes_glob_pats and not glob_routes:
        sys.exit(f"error: no files matched --routes-glob: {', '.join(routes_glob_pats)}")

    all_routes = list(dict.fromkeys(route_paths + glob_routes))
    if not a.files and not all_routes:
        sys.exit("error: provide files, --route, or --routes-glob")

    missing = [p for p in a.files + all_routes + (a.css or []) if not pathlib.Path(p).is_file()]
    if missing:
        sys.exit(f"error: file not found: {', '.join(missing)}")
    css_texts = [pathlib.Path(p).read_text(encoding='utf-8', errors='ignore') for p in (a.css or [])]
    shared_tokens, shared_dark = css_tokens(css_texts), css_tokens(css_texts, r'\.dark')
    total = {'FAIL': 0, 'WARN': 0, 'INFO': 0}
    total_suppressed = 0
    total_baseline_skipped = 0
    show_suppressed = getattr(a, 'show_suppressed', False)
    baseline_path = getattr(a, 'baseline', None)
    write_baseline_flag = getattr(a, 'write_baseline', False)
    baseline_entries = load_baseline(baseline_path) if (baseline_path and not write_baseline_flag) else None
    collected_hashes = []
    route_summaries = []

    targets = [(p, False) for p in a.files] + [(p, True) for p in all_routes]
    for p, is_route in targets:
        p_txt = pathlib.Path(p).read_text(encoding='utf-8', errors='ignore')
        if is_route:
            eff_root = pathlib.Path(root_dir).resolve() if root_dir else find_project_root(p)
            composed = compose_route(p, txt=p_txt, root_dir=eff_root, tsconfig_path=tsconfig_path)
            extra_texts = [p_txt] + [
                pathlib.Path(fp).read_text(encoding='utf-8', errors='ignore')
                for fp in composed.inlined_files
                if pathlib.Path(fp).is_file()
            ]
            tokens = {**shared_tokens, **css_tokens(extra_texts)}
            dark_tokens = {**shared_dark, **css_tokens(extra_texts, r'\.dark')}
            iss, suppressed = audit(
                p,
                a.grid,
                tokens,
                dark_tokens,
                a.mood,
                txt=composed,
                return_suppressed=True,
                strict=getattr(a, 'strict', False),
                route_mode=True,
                root_dir=eff_root,
                tsconfig_path=tsconfig_path,
            )
        else:
            tokens = {**shared_tokens, **css_tokens([p_txt])}
            dark_tokens = {**shared_dark, **css_tokens([p_txt], r'\.dark')}
            iss, suppressed = audit(
                p,
                a.grid,
                tokens,
                dark_tokens,
                a.mood,
                txt=p_txt,
                return_suppressed=True,
                strict=getattr(a, 'strict', False),
                root_dir=root_dir,
                tsconfig_path=tsconfig_path,
            )
            composed = None

        total_suppressed += len(suppressed)
        if write_baseline_flag:
            for _sev, rule, msg in iss:
                collected_hashes.append(issue_hash(p, rule, msg, source_txt=p_txt))
        elif baseline_entries is not None:
            filtered, skipped = filter_baseline([(p, sev, rule, msg, p_txt) for sev, rule, msg in iss], baseline_entries)
            iss = [(sev, rule, msg) for _p, sev, rule, msg, _txt in filtered]
            total_baseline_skipped += skipped

        if is_route and composed is not None:
            inlined_n = composed.inlined_count
            print(f"== {p} [inlined {inlined_n} component(s)]: {len(iss)} issue(s)")
            if composed.inlined_files:
                rel_inlined = []
                for fp in composed.inlined_files:
                    try:
                        rel_inlined.append(pathlib.Path(fp).resolve().relative_to(eff_root).as_posix())
                    except ValueError:
                        rel_inlined.append(fp)
                print(f"  inlined files: {', '.join(rel_inlined)}")
            rc = {'FAIL': 0, 'WARN': 0, 'INFO': 0}
            for sev, _rule, _msg in iss:
                rc[sev] += 1
            try:
                disp_p = pathlib.Path(p).resolve().relative_to(eff_root).as_posix()
            except ValueError:
                disp_p = str(p)
            route_summaries.append((disp_p, rc, inlined_n))
        else:
            print(f"== {p}: {len(iss)} issue(s)")

        for sev, rule, msg in iss:
            total[sev] += 1
            print(f"  [{sev}] {rule}: {msg}")
        if show_suppressed and suppressed:
            for sev, rule, msg, reason in suppressed:
                print(f"  [SUPPRESSED] [{sev}] {rule}: {msg} — reason: {reason}")

    if write_baseline_flag:
        target = baseline_path or '.uitools-baseline.json'
        write_baseline(target, collected_hashes)
        print(f"\nWrote {len(set(collected_hashes))} baseline entries to {target}")
        sys.exit(0)

    if len(route_summaries) > 1:
        print("\nROUTE SUMMARY:")
        for r_name, rc, inl in route_summaries:
            print(f"  {r_name} | FAIL={rc['FAIL']} WARN={rc['WARN']} INFO={rc['INFO']} | inlined={inl}")

    summary = f"\nSUMMARY FAIL={total['FAIL']} WARN={total['WARN']} INFO={total['INFO']}"
    if total_suppressed > 0 or show_suppressed:
        summary += f" SUPPRESSED={total_suppressed}"
    if baseline_path is not None:
        summary += f" BASELINE_SKIPPED={total_baseline_skipped}"
    print(summary)
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
    d.add_argument('files', nargs='*')
    d.add_argument('--route', nargs='+', action='append', dest='routes', metavar='PATH',
                   help='route entry file(s) to audit with cross-file component inlining')
    d.add_argument('--routes-glob', action='append', metavar='GLOB',
                   help='glob pattern for route entry files (e.g. "app/**/page.tsx")')
    d.add_argument('--root', metavar='DIR',
                   help='project root directory for @/ and tsconfig path resolution')
    d.add_argument('--tsconfig', metavar='PATH',
                   help='path to tsconfig.json for alias path resolution')
    d.add_argument('--grid', type=int, default=8, help='soft grid (default 8); values off the 4px grid are always WARN')
    d.add_argument('--css', nargs='*', help='CSS files with :root tokens, e.g. app/globals.css for shadcn')
    d.add_argument('--mood', choices=['playful', 'trust', 'bold', 'editorial', 'technical'],
                   help='enable mood checks: color presence and hero surface')
    d.add_argument('--strict', action='store_true',
                   help='keep style suggestions (grid, CTA count, hero surface, editorial layout...) at WARN instead of INFO')
    d.add_argument('--show-suppressed', action='store_true',
                   help='list suppressed issues with their ignore reasons')
    d.add_argument('--baseline', metavar='PATH',
                   help='baseline JSON file to filter known issues (default for --write-baseline: .uitools-baseline.json)')
    d.add_argument('--write-baseline', action='store_true',
                   help='write current issues to baseline file (--baseline path or .uitools-baseline.json)')
    d.set_defaults(f=cmd_audit)
    a = ap.parse_args(argv)
    a.f(a)


if __name__ == '__main__':
    main()
