"""HTML/JSX markup scanning, CSS block stripping, and Tailwind class parsing helpers."""
import re

__all__ = [
    'SPACE_PROPS',
    'TW_SPACE_CLS',
    'TAG',
    'VOID',
    'READABLE_MAXW',
    'BIG_TEXT',
    'BOLD',
    'BLOCK',
    'BG_NON_COLOR',
    'BG_PASSTHROUGH',
    'TEXT_NON_COLOR',
    'RADIUS',
    'RADIUS_NAME',
    'HUE_CLASS',
    'CARD_RADIUS',
    'SIZE_CLASS',
    'DARK_NEUTRAL',
    'MAXW',
    'NARROW',
    'NARROW_COL',
    'COL_NARROW',
    'COL_MED',
    'WIDE_FRAME',
    'WIDE_XL',
    'MULTI_COL',
    'HEADLINE_TEXT',
    'strip_css_comments',
    '_strip_at_blocks',
    '_strip_css_blocks',
    '_strip_all_comments',
    'mask_non_markup',
    'classes',
    'walk',
    'pick',
    'radius_px',
    'padding_px',
    'height_px',
    '_has_row_flex',
    'line_of',
]

SPACE_PROPS = r'(?:margin|padding|gap|row-gap|column-gap|inset)(?:-[a-z]+)?'
TW_SPACE_CLS = re.compile(r'^(?:[a-z0-9]+:)*-?(?:p|px|py|pt|pr|pb|pl|ps|pe|m|mx|my|mt|mr|mb|ml|ms|me|gap|gap-x|gap-y|space-x|space-y|inset)-(\[[^\]]+\]|[\d.]+)$')
TAG = re.compile(r"""(</|(?<![A-Za-z0-9_$])<)([A-Za-z][\w.-]*)((?:[^>{}"']|"[^"]*"|'[^']*'|\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\})*?)(/?)>""")
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'}
READABLE_MAXW = re.compile(r'(?<![\w-])(?:[a-z0-9]+:)*max-w-(?:prose|xs|sm|md|lg|xl|2xl|\[(?:[4-7]\d|80)ch\])(?![\w-])|max-width\s*:\s*(?:[4-7]\d|80)ch')
BIG_TEXT = {'text-2xl', 'text-3xl', 'text-4xl', 'text-5xl', 'text-6xl', 'text-7xl', 'text-8xl', 'text-9xl'}
BOLD = {'font-semibold', 'font-bold', 'font-extrabold', 'font-black'}
BLOCK = re.compile(r'^(?:section|article|form|dialog|header|main|aside|Card|DialogContent|SheetContent|AlertDialogContent)$')
BG_NON_COLOR = re.compile(r'(?:auto|cover|contain|fixed|local|scroll|center|top|bottom|left|right|(?:left|right)-(?:top|bottom)|'
                          r'repeat|no-repeat|repeat-[xy]|repeat-round|repeat-space|none|clip-\w+|origin-\w+|blend-[\w-]+|opacity-\d+|'
                          r'\[length:[^\]]+\]|\[position:[^\]]+\]|size-[\w-]+)')
BG_PASSTHROUGH = {'transparent', 'inherit', 'current'}
TEXT_NON_COLOR = re.compile(r'(?:xs|sm|base|lg|\d?xl|left|right|center|justify|start|end|wrap|nowrap|balance|pretty|ellipsis|clip|'
                            r'\[\d.*\]|opacity-\d+|shadow(?:-[\w-]+)?|\[length:[^\]]+\])')

RADIUS = {'rounded-none': 0, 'rounded-sm': 2, 'rounded': 4, 'rounded-md': 6, 'rounded-lg': 8,
          'rounded-xl': 12, 'rounded-2xl': 16, 'rounded-3xl': 24}
RADIUS_NAME = {v: k for k, v in RADIUS.items()}

HUE_CLASS = re.compile(r'(?<![\w-])(?:[a-z]+:)*(?:bg|text|from|via|to|border|fill|stroke|ring)-([a-z]+)-(?:50|[1-9]00|950)(?![\w-])')
CARD_RADIUS = re.compile(r'^rounded-(?:lg|xl|2xl|3xl|\[\d+px\])$')
SIZE_CLASS = re.compile(r'^text-(xs|sm|base|lg|\d?xl)$')
DARK_NEUTRAL = re.compile(r'(?:slate|gray|zinc|neutral|stone)-(?:[6-9]00|950)|black')

MAXW = re.compile(r'^max-w-(prose|xs|sm|md|lg|xl|2xl|3xl|4xl|5xl|6xl|7xl|\[[^\]]+\])$')
NARROW = re.compile(r'^max-w-(?:prose|xs|sm|md|lg|xl|2xl|\[(?:[4-7]\d|80)ch\])$')
NARROW_COL = re.compile(r'^max-w-(?:prose|xs|sm|md|lg|xl|\[(?:[4-6]\d)ch\])$')
COL_NARROW = re.compile(r'^max-w-(?:prose|\[(?:[4-7]\d)ch\])$')
COL_MED = re.compile(r'^max-w-(?:xl|2xl)$')
WIDE_FRAME = re.compile(r'^max-w-(?:4xl|5xl|6xl|7xl)$')
WIDE_XL = re.compile(r'^max-w-(?:5xl|6xl|7xl)$')
MULTI_COL = re.compile(r'^(?:[a-z0-9]+:)*(?:grid-cols-(?:[2-9]|1[0-2]|\[[^\]]+[_ ][^\]]+\])|flex-row)$')
HEADLINE_TEXT = re.compile(r'^(?:[a-z0-9]+:)*text-(?:4xl|5xl|6xl|7xl|8xl|9xl)$')


def strip_css_comments(txt):
    """Replace /* ... */ CSS comments with spaces, preserving newline count."""
    return re.sub(r'/\*.*?\*/', lambda m: re.sub(r'[^\n]', ' ', m.group(0)), txt, flags=re.S)


def _strip_at_blocks(css):
    """Remove nested @media/@supports/@container brace blocks, preserving newlines."""
    out = []
    i = 0
    n = len(css)
    pat = re.compile(r'@(?:media|supports|container)\b[^{;]*\{', re.I)
    for m in pat.finditer(css):
        if m.start() < i:
            continue
        out.append(css[i:m.start()])
        j = m.end()
        depth = 1
        while j < n and depth > 0:
            if css[j] == '{':
                depth += 1
            elif css[j] == '}':
                depth -= 1
            j += 1
        out.append(re.sub(r'[^\n]', ' ', css[m.start():j]))
        i = j
    out.append(css[i:])
    return ''.join(out)


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


def _strip_all_comments(txt):
    """Strip HTML, JSX and CSS comments while preserving newlines."""
    txt = re.sub(r'<!--.*?-->|\{/\*.*?\*/\}', lambda m: re.sub(r'[^\n]', ' ', m.group(0)), txt, flags=re.S)
    return strip_css_comments(txt)


def mask_non_markup(txt):
    """Replace HTML/JSX comments, <script>, and <style> blocks with spaces while preserving newlines and indices."""
    pat = r'<!--.*?-->|\{/\*.*?\*/\}|<script\b[^>]*>.*?</script>|<style\b[^>]*>.*?</style>'
    return re.sub(pat, lambda m: re.sub(r'[^\n]', ' ', m.group(0)), txt, flags=re.S | re.I)


def classes(attrs):
    m = re.search(r"""(?<![\w-])class(?:Name)?\s*=\s*("[^"]*"|'[^']*'|\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\})""", attrs)
    if not m:
        return []
    v = m.group(1)
    if v.startswith('{'):
        parts = []
        for dq, sq, tpl in re.findall(r'"([^"]*)"|\'([^\']*)\'|`([^`]*)`', v):
            if tpl:
                def _expr_lits(em):
                    return ' ' + ' '.join(a or b for a, b in re.findall(r'"([^"]*)"|\'([^\']*)\'', em.group(1))) + ' '
                parts.append(re.sub(r'\$\{([^{}]*)\}', _expr_lits, tpl))
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


def _has_row_flex(cls):
    return 'flex' in cls and not any(c.endswith('flex-col') for c in cls)


def line_of(txt, pos):
    return txt.count('\n', 0, pos) + 1
