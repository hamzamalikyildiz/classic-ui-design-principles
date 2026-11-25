"""HTML/JSX markup scanning, CSS block stripping, and Tailwind class parsing helpers."""
from __future__ import annotations

from dataclasses import dataclass, field
import itertools
import pathlib
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
    'ClassCombination',
    'ClassSet',
    'ParsedNode',
    'AncestorNode',
    'JsxBranch',
    'JsxRegion',
    'CvaDefinition',
    'CvaRegistry',
    'CvaMetadata',
    'strip_css_comments',
    '_strip_at_blocks',
    '_strip_css_blocks',
    '_strip_all_comments',
    'mask_non_markup',
    'classes',
    'classset',
    'expand_combinations',
    'jsx_regions',
    'conditional_regions',
    'parse_cva_definitions',
    'discover_cva_definitions',
    'resolve_cva_classes',
    'extract_cva_metadata',
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


_SVELTE_CONTROL_PAT = (
    r'(?-i:\{(?:'
    r'#(?:if|each|await|key|snippet)\b'
    r'|:(?:else|then|catch)\b'
    r'|/(?:if|each|await|key|snippet)\b'
    r'|@(?:html|const|debug|render)\b'
    r')(?:[^{}"\']|"[^"]*"|\'[^\']*\'|\{(?:[^{}"\']|"[^"]*"|\'[^\']*\'|\{[^{}]*\})*\})*\})'
)


def mask_non_markup(txt):
    """Replace HTML/JSX comments, <script>, <style>, and Svelte control tags with spaces while preserving newlines and indices."""
    pat = rf'<!--.*?-->|\{{/\*.*?\*/\}}|<script\b[^>]*>.*?</script>|<style\b[^>]*>.*?</style>|{_SVELTE_CONTROL_PAT}'
    res = re.sub(pat, lambda m: re.sub(r'[^\n]', ' ', m.group(0)), txt, flags=re.S | re.I)
    clone_fn = getattr(txt, '_clone_with_text', None)
    if clone_fn is not None:
        return clone_fn(res)
    return res


def classes(attrs):
    out = []
    m = re.search(r"""(?<![:\w-])class(?:Name)?\s*=\s*("[^"]*"|'[^']*'|\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\})""", attrs)
    if m:
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
            out.extend(' '.join(parts).split())
        else:
            out.extend(v[1:-1].split())
    if ':class' in attrs:
        vue_expr = _extract_vue_bound_class_expr(attrs)
        if vue_expr:
            b = _ClassSetBuilder()
            b.eval_node(_JsExprParser(_tokenize_js(vue_expr), vue_expr).parse())
            out.extend(b.build().flat_classes)
    return out


# ---------------- variant class model (İP-A3) ----------------

_CLASS_HELPER_NAMES = {'cn', 'clsx', 'twMerge', 'cx', 'classNames', 'classnames'}
_MAX_COMBO_LIMIT = 8


class ClassCombination(tuple):
    """2-tuple (classes, label) carrying .classes, .label, .labels and .choices."""

    def __new__(cls, classes_list, label='', *, labels=(), choices=None):
        obj = super().__new__(cls, (classes_list, label))
        obj.classes = classes_list
        obj.label = label
        obj.labels = labels
        obj.choices = choices or {}
        return obj


@dataclass
class ClassSet:
    """Structured class list with conditional branch groups for a single node."""

    base: list[str] = field(default_factory=list)
    branches: list[tuple[str, list[list[str]]]] = field(default_factory=list)
    groups: dict[str, dict] = field(default_factory=dict)
    cva_calls: list[dict] = field(default_factory=list)
    exploded: bool = False
    tail: list[str] = field(default_factory=list)

    def expand(self, limit: int = _MAX_COMBO_LIMIT) -> list[ClassCombination]:
        """Return concrete class combinations up to `limit`, marking `exploded` if exceeded."""
        return expand_combinations(self, limit=limit)

    @property
    def flat_classes(self) -> list[str]:
        """Return `base` plus the first alternative of each branch group (plus any override `tail`)."""
        out = list(self.base)
        for _, alts in self.branches:
            if alts and alts[0]:
                out.extend(alts[0])
        if self.tail:
            out.extend(self.tail)
        return out

    def __iter__(self):
        return iter(self.flat_classes)

    def __len__(self):
        return len(self.flat_classes)

    def __contains__(self, item):
        if item in self.base or item in self.tail:
            return True
        return any(item in alt for _, alts in self.branches for alt in alts)

    def __getitem__(self, idx):
        return self.flat_classes[idx]

    def __bool__(self):
        return bool(self.base or self.tail or any(alt for _, alts in self.branches for alt in alts))


class AncestorNode(tuple):
    """4-tuple (tag, attrs, cls, start) with .classset and JSX branch metadata."""

    def __new__(cls, items, *, classset=None, branch_region=None, branch_regions=(), branch_label=None):
        obj = super().__new__(cls, items)
        obj.classset = classset
        obj.branch_region = branch_region
        obj.branch_regions = branch_regions
        obj.branch_label = branch_label
        return obj


class ParsedNode(tuple):
    """6-tuple (tag, attrs, cls, ancestors, start, end) with .classset and JSX branch metadata."""

    def __new__(cls, items, *, classset=None, branch_region=None, branch_regions=(), branch_label=None):
        obj = super().__new__(cls, items)
        obj.classset = classset
        obj.branch_region = branch_region
        obj.branch_regions = branch_regions
        obj.branch_label = branch_label
        return obj


@dataclass
class JsxBranch:
    """One branch of a mutually exclusive JSX conditional region."""

    region_id: str
    branch_index: int
    label: str
    start: int
    end: int


@dataclass
class JsxRegion:
    """Mutually exclusive JSX conditional block (ternary, paired &&, or lookup)."""

    region_id: str
    kind: str
    start: int
    end: int
    branches: list[JsxBranch] = field(default_factory=list)


def _skip_quoted(src, i, quote):
    """Return index immediately after matching `quote` (handling backslash escapes)."""
    n = len(src)
    i += 1
    while i < n:
        ch = src[i]
        if ch == '\\':
            i += 2
            continue
        if ch == quote:
            return i + 1
        i += 1
    return n


def _skip_template(src, i):
    """Return index immediately after matching backtick template literal (handling `${...}`)."""
    n = len(src)
    i += 1
    while i < n:
        ch = src[i]
        if ch == '\\':
            i += 2
            continue
        if ch == '$' and i + 1 < n and src[i + 1] == '{':
            i = _skip_balanced_braces(src, i + 1)
            continue
        if ch == '`':
            return i + 1
        i += 1
    return n


def _skip_balanced_braces(src, i):
    """Given `src[i] == '{'`, return index right after its matching `}`."""
    n = len(src)
    depth = 0
    while i < n:
        ch = src[i]
        if ch in ('"', "'"):
            i = _skip_quoted(src, i, ch)
            continue
        if ch == '`':
            i = _skip_template(src, i)
            continue
        if ch == '/' and i + 1 < n:
            if src[i + 1] == '/':
                nl = src.find('\n', i + 2)
                i = n if nl == -1 else nl + 1
                continue
            if src[i + 1] == '*':
                end = src.find('*/', i + 2)
                i = n if end == -1 else end + 2
                continue
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return n


def _extract_class_attr(attrs):
    """Extract `(value_text, is_js_expr)` for class/className attribute, or `(None, False)`."""
    m = re.search(r'(?<![:\w-])class(?:Name)?\s*=\s*', attrs)
    if not m:
        return None, False
    i = m.end()
    n = len(attrs)
    if i >= n:
        return None, False
    ch = attrs[i]
    if ch in ('"', "'"):
        end = _skip_quoted(attrs, i, ch)
        return attrs[i + 1:max(i + 1, end - 1)], False
    if ch == '{':
        end = _skip_balanced_braces(attrs, i)
        if end > i + 1 and attrs[end - 1] == '}':
            return attrs[i + 1:end - 1], True
        return attrs[i + 1:end], True
    return None, False


def _extract_vue_bound_class_expr(attrs):
    """Extract Vue `:class="..."` or `v-bind:class="..."` JS expression string, or `None`."""
    m = re.search(r'(?:(?<![\w-])v-bind:|:)class\s*=\s*', attrs)
    if not m:
        return None
    i = m.end()
    if i >= len(attrs):
        return None
    ch = attrs[i]
    if ch in ('"', "'"):
        end = _skip_quoted(attrs, i, ch)
        return attrs[i + 1:max(i + 1, end - 1)]
    return None


@dataclass
class _Tok:
    kind: str
    val: object
    start: int
    end: int


_MULTI_OPS = ('===', '!==', '==', '!=', '<=', '>=', '&&', '||', '??', '?.', '=>', '...')
_SINGLE_OPS = set('?:(){}[].,!<>+-*/%=')


def _tokenize_js(src):
    """Tokenize a JS/TSX expression inside `className={...}` using Python stdlib only."""
    tokens = []
    i = 0
    n = len(src)
    while i < n:
        ch = src[i]
        if ch.isspace():
            i += 1
            continue
        if ch == '/' and i + 1 < n:
            if src[i + 1] == '/':
                nl = src.find('\n', i + 2)
                i = n if nl == -1 else nl + 1
                continue
            if src[i + 1] == '*':
                end = src.find('*/', i + 2)
                i = n if end == -1 else end + 2
                continue
        if ch in ('"', "'"):
            end = _skip_quoted(src, i, ch)
            raw = src[i + 1:max(i + 1, end - 1)]
            tokens.append(_Tok('STR', raw, i, end))
            i = end
            continue
        if ch == '`':
            parts, end = _tokenize_template(src, i)
            tokens.append(_Tok('TPL', parts, i, end))
            i = end
            continue
        matched_op = None
        for op in _MULTI_OPS:
            if src.startswith(op, i):
                matched_op = op
                break
        if matched_op is not None:
            tokens.append(_Tok('OP', matched_op, i, i + len(matched_op)))
            i += len(matched_op)
            continue
        if ch in _SINGLE_OPS:
            tokens.append(_Tok('OP', ch, i, i + 1))
            i += 1
            continue
        if ch.isalpha() or ch in ('_', '$'):
            j = i + 1
            while j < n and (src[j].isalnum() or src[j] in ('_', '$')):
                j += 1
            tokens.append(_Tok('IDENT', src[i:j], i, j))
            i = j
            continue
        if ch.isdigit():
            j = i + 1
            while j < n and (src[j].isdigit() or src[j] == '.'):
                j += 1
            tokens.append(_Tok('NUM', src[i:j], i, j))
            i = j
            continue
        i += 1
    return tokens


def _tokenize_template(src, i):
    """Scan a backtick template literal from index `i`, returning `(parts, end_idx)`."""
    parts = []
    n = len(src)
    i += 1
    buf = []
    while i < n:
        ch = src[i]
        if ch == '\\' and i + 1 < n:
            buf.append(src[i + 1])
            i += 2
            continue
        if ch == '$' and i + 1 < n and src[i + 1] == '{':
            if buf:
                parts.append(('str', ''.join(buf)))
                buf = []
            expr_end = _skip_balanced_braces(src, i + 1)
            expr_src = src[i + 2:max(i + 2, expr_end - 1)]
            parts.append(('expr', _tokenize_js(expr_src), expr_src))
            i = expr_end
            continue
        if ch == '`':
            if buf:
                parts.append(('str', ''.join(buf)))
            return parts, i + 1
        buf.append(ch)
        i += 1
    if buf:
        parts.append(('str', ''.join(buf)))
    return parts, n


@dataclass
class _StrNode:
    val: str
    src: str


@dataclass
class _BoolNode:
    val: bool
    src: str


@dataclass
class _NullNode:
    src: str


@dataclass
class _RawNode:
    src: str


@dataclass
class _TemplateNode:
    parts: list
    src: str


@dataclass
class _CallNode:
    callee: str
    args: list
    src: str


@dataclass
class _ObjNode:
    entries: list
    src: str


@dataclass
class _ArrNode:
    items: list
    src: str


@dataclass
class _AndNode:
    lhs: object
    rhs: object
    src: str


@dataclass
class _OrNode:
    lhs: object
    op: str
    rhs: object
    src: str


@dataclass
class _TernaryNode:
    cond: object
    t_expr: object
    f_expr: object
    src: str


_RAW_STOP_OPS = {'&&', '||', '??', '?', ':', ',', ')', '}', ']'}


class _JsExprParser:
    """Recursive-descent parser for JS/TSX class expressions."""

    def __init__(self, tokens, src):
        self.tokens = tokens
        self.src = src
        self.pos = 0
        self.n = len(tokens)

    def peek(self, offset=0):
        idx = self.pos + offset
        return self.tokens[idx] if 0 <= idx < self.n else None

    def next(self):
        tok = self.peek()
        if tok is not None:
            self.pos += 1
        return tok

    def match_op(self, *ops):
        tok = self.peek()
        if tok and tok.kind == 'OP' and tok.val in ops:
            self.pos += 1
            return tok
        return None

    def _slice(self, start_idx, end_idx):
        if start_idx >= self.n or end_idx <= start_idx:
            return ''
        s = self.tokens[start_idx].start
        e = self.tokens[end_idx - 1].end
        return self.src[s:e].strip()

    def parse(self):
        if self.n == 0:
            return _NullNode('')
        return self._parse_ternary()

    def _parse_ternary(self):
        start = self.pos
        cond = self._parse_or()
        if self.match_op('?'):
            t_expr = self._parse_ternary()
            if self.match_op(':'):
                f_expr = self._parse_ternary()
            else:
                f_expr = _NullNode('')
            return _TernaryNode(cond, t_expr, f_expr, self._slice(start, self.pos))
        return cond

    def _parse_or(self):
        start = self.pos
        lhs = self._parse_and()
        while (op_tok := self.match_op('||', '??')) is not None:
            rhs = self._parse_and()
            lhs = _OrNode(lhs, op_tok.val, rhs, self._slice(start, self.pos))
        return lhs

    def _parse_and(self):
        start = self.pos
        lhs = self._parse_unit()
        while self.match_op('&&') is not None:
            rhs = self._parse_unit()
            lhs = _AndNode(lhs, rhs, self._slice(start, self.pos))
        return lhs

    def _consume_raw_tail(self, start_pos):
        """Consume remaining comparison/binary/member tokens up to a delimiter."""
        depth = 0
        while (tok := self.peek()) is not None:
            if tok.kind == 'OP':
                if tok.val in ('(', '[', '{'):
                    depth += 1
                elif tok.val in (')', ']', '}'):
                    if depth == 0:
                        break
                    depth -= 1
                elif depth == 0 and tok.val in _RAW_STOP_OPS:
                    break
            self.next()
        return _RawNode(self._slice(start_pos, self.pos))

    def _skip_ts_type_assertion(self):
        tok = self.peek()
        if tok is not None and tok.kind == 'IDENT' and tok.val in ('as', 'satisfies'):
            self.next()
            depth = 0
            while (t := self.peek()) is not None:
                if t.kind == 'OP':
                    if t.val in ('(', '[', '{', '<'):
                        depth += 1
                    elif t.val in (')', ']', '}', '>'):
                        if depth == 0:
                            break
                        depth -= 1
                    elif depth == 0 and t.val in _RAW_STOP_OPS:
                        break
                self.next()

    def _has_infix_continuation(self):
        tok = self.peek()
        if tok is None or tok.kind != 'OP':
            return tok is not None and tok.kind == 'IDENT'  # e.g. TS `as Type`
        return tok.val not in _RAW_STOP_OPS

    def _parse_unit(self):
        tok = self.peek()
        if tok is None:
            return _NullNode('')
        start = self.pos

        if tok.kind == 'OP' and tok.val == '(':
            self.next()
            inner = self._parse_ternary()
            self.match_op(')')
            if self._has_infix_continuation():
                return self._consume_raw_tail(start)
            return inner

        if tok.kind == 'OP' and tok.val == '{':
            obj = self._parse_object()
            self._skip_ts_type_assertion()
            return obj

        if tok.kind == 'OP' and tok.val == '[':
            arr = self._parse_array()
            self._skip_ts_type_assertion()
            return arr

        if tok.kind == 'STR':
            self.next()
            self._skip_ts_type_assertion()
            if self._has_infix_continuation():
                return self._consume_raw_tail(start)
            return _StrNode(tok.val, tok.val)

        if tok.kind == 'TPL':
            self.next()
            self._skip_ts_type_assertion()
            if self._has_infix_continuation():
                return self._consume_raw_tail(start)
            eval_parts = []
            for item in tok.val:
                if item[0] == 'str':
                    eval_parts.append(item)
                else:
                    sub_node = _JsExprParser(item[1], item[2]).parse()
                    eval_parts.append(('expr', sub_node))
            return _TemplateNode(eval_parts, self.src[tok.start:tok.end])

        if tok.kind == 'IDENT':
            if tok.val in ('true', 'false') and not self._peek_is_member_or_infix(1):
                self.next()
                return _BoolNode(tok.val == 'true', tok.val)
            if tok.val in ('null', 'undefined') and not self._peek_is_member_or_infix(1):
                self.next()
                return _NullNode(tok.val)
            # Check for helper call like cn(...), clsx(...), twMerge(...), cx(...)
            if self._is_call_ahead():
                return self._parse_call_or_raw(start)

        return self._consume_raw_tail(start)

    def _peek_is_member_or_infix(self, offset):
        tok = self.peek(offset)
        if tok is None:
            return False
        if tok.kind == 'OP':
            return tok.val not in _RAW_STOP_OPS
        return True

    def _is_call_ahead(self):
        j = 0
        while True:
            t = self.peek(j)
            if t is None or t.kind != 'IDENT':
                return False
            nxt = self.peek(j + 1)
            if nxt is None or nxt.kind != 'OP':
                return False
            if nxt.val == '(':
                return True
            if nxt.val in ('.', '?.'):
                j += 2
                continue
            return False

    def _parse_call_or_raw(self, start):
        parts = []
        while (t := self.peek()) is not None and t.kind == 'IDENT':
            parts.append(self.next().val)
            if self.match_op('.', '?.') is None:
                break
        callee = '.'.join(parts)
        if self.match_op('(') is None:
            return self._consume_raw_tail(start)
        args = []
        while (t := self.peek()) is not None:
            if t.kind == 'OP' and t.val == ')':
                self.next()
                break
            if t.kind == 'OP' and t.val == ',':
                self.next()
                continue
            args.append(self._parse_ternary())
            self.match_op(',')
        if self._has_infix_continuation():
            return self._consume_raw_tail(start)
        return _CallNode(callee, args, self._slice(start, self.pos))

    def _parse_object(self):
        start = self.pos
        self.next()  # '{'
        entries = []
        while (tok := self.peek()) is not None:
            if tok.kind == 'OP' and tok.val == '}':
                self.next()
                break
            if tok.kind == 'OP' and tok.val == ',':
                self.next()
                continue
            if tok.kind == 'OP' and tok.val == '...':
                self._skip_obj_entry()
                continue
            if tok.kind == 'OP' and tok.val == '[':
                self._skip_obj_entry()
                continue
            if tok.kind in ('STR', 'IDENT', 'NUM'):
                key_tok = self.next()
                key_str = str(key_tok.val)
                if self.match_op(':') is not None:
                    val_node = self._parse_ternary()
                elif key_tok.kind == 'IDENT':
                    val_node = _RawNode(key_str)
                else:
                    val_node = _NullNode('')
                entries.append((key_str, val_node))
                self.match_op(',')
                continue
            self.next()
        return _ObjNode(entries, self._slice(start, self.pos))

    def _skip_obj_entry(self):
        depth = 0
        while (t := self.peek()) is not None:
            if t.kind == 'OP':
                if t.val in ('(', '[', '{'):
                    depth += 1
                elif t.val in (')', ']'):
                    if depth > 0:
                        depth -= 1
                elif t.val == '}':
                    if depth == 0:
                        break
                    depth -= 1
                elif t.val == ',' and depth == 0:
                    self.next()
                    break
            self.next()

    def _parse_array(self):
        start = self.pos
        self.next()  # '['
        items = []
        while (tok := self.peek()) is not None:
            if tok.kind == 'OP' and tok.val == ']':
                self.next()
                break
            if tok.kind == 'OP' and tok.val == ',':
                self.next()
                continue
            if tok.kind == 'OP' and tok.val == '...':
                self.next()
                self._parse_ternary()
                self.match_op(',')
                continue
            items.append(self._parse_ternary())
            self.match_op(',')
        return _ArrNode(items, self._slice(start, self.pos))


def _norm_cond_label(cond_src):
    s = ' '.join(cond_src.split())
    if len(s) > 48:
        return s[:45] + '...'
    return s


class _ClassSetBuilder:
    """Evaluate a parsed JS expression AST into a ClassSet."""

    def __init__(self):
        self.base = []
        self.branches = []
        self.groups = {}
        self.cva_calls = []
        self._group_seq = 0
        self._cond_to_gid = {}

    def add_group(self, alts, labels, *, kind='ternary', cond=''):
        if not alts or all(not a for a in alts):
            return
        # Correlate identical simple boolean conditions on the same element (e.g. two `${isDark ? ...}`)
        if (
            kind in ('ternary', 'and', 'object')
            and len(alts) == 2
            and cond
            and cond in self._cond_to_gid
        ):
            gid = self._cond_to_gid[cond]
            grp = self.groups[gid]
            if len(grp['alts']) == 2:
                grp['alts'][0].extend(alts[0])
                grp['alts'][1].extend(alts[1])
                return
        gid = f'g{self._group_seq}'
        self._group_seq += 1
        self.branches.append((gid, alts))
        self.groups[gid] = {
            'cond': cond,
            'kind': kind,
            'labels': labels,
            'alts': alts,
        }
        if kind in ('ternary', 'and', 'object') and len(alts) == 2 and cond:
            self._cond_to_gid.setdefault(cond, gid)

    def eval_node(self, node):
        if isinstance(node, _StrNode):
            self.base.extend(node.val.split())
            return
        if isinstance(node, (_BoolNode, _NullNode, _RawNode)):
            return
        if isinstance(node, _TemplateNode):
            self._eval_template(node)
            return
        if isinstance(node, _CallNode):
            tail = node.callee.rsplit('.', 1)[-1]
            if tail in _CLASS_HELPER_NAMES:
                for arg in node.args:
                    self.eval_node(arg)
                return
            if tail == 'cva' or tail.endswith('Variants'):
                self.cva_calls.append({'callee': node.callee, 'src': node.src})
            return
        if isinstance(node, _ArrNode):
            for item in node.items:
                self.eval_node(item)
            return
        if isinstance(node, _ObjNode):
            for key_str, val_node in node.entries:
                cls = key_str.split()
                if not cls:
                    continue
                if isinstance(val_node, _BoolNode):
                    if val_node.val:
                        self.base.extend(cls)
                    continue
                if isinstance(val_node, _NullNode):
                    continue
                cond = _norm_cond_label(val_node.src) or key_str
                self.add_group([cls, []], [f'{cond}=true', f'{cond}=false'], kind='object', cond=cond)
            return
        if isinstance(node, _AndNode):
            cond = _norm_cond_label(node.lhs.src)
            sub_alts = _eval_branch_alts(node.rhs)
            if not any(sub_alts):
                return
            if len(sub_alts) == 1:
                alts = [sub_alts[0][0], []]
                labels = [f'{cond}=true', f'{cond}=false']
            else:
                alts = [c for c, _ in sub_alts] + [[]]
                labels = [f'{cond}=true,{lbl}' if lbl else f'{cond}=true' for _, lbl in sub_alts] + [f'{cond}=false']
            self.add_group(alts, labels, kind='and', cond=cond)
            return
        if isinstance(node, _OrNode):
            self._eval_or(node)
            return
        if isinstance(node, _TernaryNode):
            pairs = _eval_ternary_pairs(node, depth=0)
            alts = [c for c, _ in pairs]
            labels = [lbl for _, lbl in pairs]
            cond = _norm_cond_label(node.cond.src)
            kind = 'nested-ternary' if len(alts) > 2 else 'ternary'
            self.add_group(alts, labels, kind=kind, cond=cond)
            return

    def _eval_or(self, node):
        rhs_pairs = _eval_branch_alts(node.rhs)
        if isinstance(node.lhs, _AndNode):
            lhs_cond = _norm_cond_label(node.lhs.lhs.src)
            lhs_pairs = _eval_branch_alts(node.lhs.rhs)
            alts = [c for c, _ in lhs_pairs] + [c for c, _ in rhs_pairs]
            labels = (
                [f'{lhs_cond}=true,{lbl}' if lbl else f'{lhs_cond}=true' for _, lbl in lhs_pairs]
                + [f'{lhs_cond}=false,{lbl}' if lbl else f'{lhs_cond}=false' for _, lbl in rhs_pairs]
            )
            self.add_group(alts, labels, kind='ternary', cond=lhs_cond)
            return
        lhs_src = _norm_cond_label(node.lhs.src) or 'expr'
        if isinstance(node.lhs, _StrNode) and node.lhs.val.strip():
            self.base.extend(node.lhs.val.split())
            return
        if not any(c for c, _ in rhs_pairs):
            return
        alts = [c for c, _ in rhs_pairs] + [[]]
        labels = [
            f'{lhs_src}=empty,{lbl}' if lbl else f'{lhs_src}=empty' for _, lbl in rhs_pairs
        ] + [f'{lhs_src}=set']
        self.add_group(alts, labels, kind='fallback', cond=lhs_src)

    def _eval_template(self, node):
        parts = node.parts
        for idx, part in enumerate(parts):
            if part[0] == 'str':
                text = part[1]
                glued_left = idx > 0 and parts[idx - 1][0] == 'expr' and text and not text[0].isspace()
                glued_right = idx + 1 < len(parts) and parts[idx + 1][0] == 'expr' and text and not text[-1].isspace()
                tokens = text.split()
                if glued_left and tokens:
                    tokens = tokens[1:]
                if glued_right and tokens:
                    tokens = tokens[:-1]
                self.base.extend(tokens)
            else:
                self.eval_node(part[1])

    def build(self):
        cs = ClassSet(
            base=self.base,
            branches=self.branches,
            groups=self.groups,
            cva_calls=self.cva_calls,
            exploded=False,
        )
        cs.exploded = _count_combos(cs, _MAX_COMBO_LIMIT) > _MAX_COMBO_LIMIT
        return cs


def _eval_branch_alts(node):
    """Evaluate a sub-expression into a list of `(class_list, sub_label)` pairs."""
    b = _ClassSetBuilder()
    b.eval_node(node)
    sub = b.build()
    if not sub.branches:
        return [(sub.base, '')]
    combos = expand_combinations(sub, limit=_MAX_COMBO_LIMIT)
    return [(c.classes, c.label) for c in combos]


def _eval_ternary_pairs(node, depth=0):
    """Flatten up to 2 levels of nested ternaries into `[(class_list, label), ...]`."""
    cond = _norm_cond_label(node.cond.src)
    out = []
    for is_true, branch in ((True, node.t_expr), (False, node.f_expr)):
        prefix = f'{cond}={"true" if is_true else "false"}'
        if isinstance(branch, _TernaryNode) and depth < 1:
            for sub_cls, sub_lbl in _eval_ternary_pairs(branch, depth + 1):
                out.append((sub_cls, f'{prefix},{sub_lbl}'))
        elif isinstance(branch, _TernaryNode) and depth >= 1:
            # Cap nesting at 2 levels (depth 0 -> 1); flatten deeper literals safely
            sub_pairs = _eval_branch_alts(branch)
            for sub_cls, sub_lbl in sub_pairs:
                lbl = f'{prefix},{sub_lbl}' if sub_lbl else prefix
                out.append((sub_cls, lbl))
        else:
            sub_pairs = _eval_branch_alts(branch)
            for sub_cls, sub_lbl in sub_pairs:
                lbl = f'{prefix},{sub_lbl}' if sub_lbl else prefix
                out.append((sub_cls, lbl))
    return out


def _count_combos(cs, limit):
    total = 1
    for _, alts in cs.branches:
        total *= max(1, len(alts))
        if total > limit:
            return total
    return total


def classset(attrs):
    """Parse HTML/JSX/Vue/Svelte `class`, `className`, or `:class` attributes into a `ClassSet`."""
    raw, is_expr = _extract_class_attr(attrs)
    vue_expr = _extract_vue_bound_class_expr(attrs) if ':class' in attrs else None
    if raw is None and vue_expr is None:
        return ClassSet()
    if vue_expr is None:
        if not is_expr:
            return ClassSet(base=raw.split())
        tokens = _tokenize_js(raw)
        ast = _JsExprParser(tokens, raw).parse()
        builder = _ClassSetBuilder()
        builder.eval_node(ast)
        return builder.build()
    builder = _ClassSetBuilder()
    if raw is not None:
        if is_expr:
            builder.eval_node(_JsExprParser(_tokenize_js(raw), raw).parse())
        else:
            builder.base.extend(raw.split())
    builder.eval_node(_JsExprParser(_tokenize_js(vue_expr), vue_expr).parse())
    return builder.build()


def expand_combinations(cs, limit=_MAX_COMBO_LIMIT):
    """Expand a `ClassSet` into concrete `ClassCombination` items, capped at `limit`."""
    tail = getattr(cs, 'tail', None) or []
    if not cs.branches:
        cs.exploded = False
        return [ClassCombination(list(cs.base) + list(tail), '', labels=(), choices={})]

    total = _count_combos(cs, limit)
    cs.exploded = total > limit

    group_options = []
    for gid, alts in cs.branches:
        lbls = cs.groups.get(gid, {}).get('labels')
        opts = []
        for idx, alt in enumerate(alts):
            lbl = lbls[idx] if lbls and idx < len(lbls) else f'{gid}={idx}'
            opts.append((gid, idx, alt, lbl))
        group_options.append(opts)

    out = []
    for chosen in itertools.islice(itertools.product(*group_options), max(1, limit)):
        combined = list(cs.base)
        lbls = []
        choices = {}
        for gid, idx, alt, lbl in chosen:
            combined.extend(alt)
            lbls.append(lbl)
            choices[gid] = (idx, lbl)
        if tail:
            combined.extend(tail)
        out.append(ClassCombination(combined, ', '.join(lbls), labels=tuple(lbls), choices=choices))
    return out


# ---------------- JSX conditional region scanner (İP-A3) ----------------

def _skip_jsx_tag_or_fragment(txt, i, tag_map):
    """If `txt[i:]` starts a `<Tag ...>...</Tag>`, `<Tag .../>` or `<>...</>`, return end index."""
    n = len(txt)
    if txt.startswith('<>', i):
        j = i + 2
        while j < n:
            if txt.startswith('</>', j):
                return j + 3
            if txt[j] == '{':
                j = _skip_balanced_braces(txt, j)
                continue
            if txt[j] == '<' and (j in tag_map or txt.startswith('<>', j)):
                j = _skip_jsx_tag_or_fragment(txt, j, tag_map)
                continue
            j += 1
        return n

    m = tag_map.get(i)
    if m is None:
        return i + 1
    close, tag, _, selfclose = m.groups()
    if close == '</' or selfclose or tag.lower() in VOID:
        return m.end()
    j = m.end()
    depth = 1
    while j < n and depth > 0:
        if txt[j] == '{':
            j = _skip_balanced_braces(txt, j)
            continue
        if txt[j] == '<' and j in tag_map:
            cm = tag_map[j]
            c_close, c_tag, _, c_self = cm.groups()
            if c_tag.lower() == tag.lower():
                if c_close == '</':
                    depth -= 1
                    j = cm.end()
                    continue
                if not c_self:
                    depth += 1
            j = cm.end()
            continue
        j += 1
    return j


def _split_top_level_ternary(txt, start, end, tag_map):
    """If `txt[start:end]` has top-level `cond ? t : f` containing `<`, return `(cond, (ts, te), (fs, fe))`."""
    i = start
    paren = brace = bracket = 0
    q_idx = -1
    colon_idx = -1
    while i < end:
        ch = txt[i]
        if ch in ('"', "'"):
            i = min(end, _skip_quoted(txt, i, ch))
            continue
        if ch == '`':
            i = min(end, _skip_template(txt, i))
            continue
        if ch == '<' and (txt.startswith('<>', i) or i in tag_map):
            i = min(end, _skip_jsx_tag_or_fragment(txt, i, tag_map))
            continue
        if ch == '(':
            paren += 1
        elif ch == ')':
            paren = max(0, paren - 1)
        elif ch == '{':
            brace += 1
        elif ch == '}':
            brace = max(0, brace - 1)
        elif ch == '[':
            bracket += 1
        elif ch == ']':
            bracket = max(0, bracket - 1)
        elif paren == 0 and brace == 0 and bracket == 0:
            if ch == '?' and not txt.startswith('?.', i) and not txt.startswith('??', i):
                if q_idx == -1:
                    q_idx = i
            elif ch == ':' and q_idx != -1:
                colon_idx = i
                break
        i += 1
    if q_idx == -1 or colon_idx == -1:
        return None
    cond = txt[start:q_idx].strip()
    t_sub = txt[q_idx + 1:colon_idx]
    f_sub = txt[colon_idx + 1:end]
    if '<' not in t_sub and '<' not in f_sub:
        return None
    t_lead = len(t_sub) - len(t_sub.lstrip())
    t_trail = len(t_sub) - len(t_sub.rstrip())
    f_lead = len(f_sub) - len(f_sub.lstrip())
    f_trail = len(f_sub) - len(f_sub.rstrip())
    ts = q_idx + 1 + t_lead
    te = colon_idx - t_trail
    fs = colon_idx + 1 + f_lead
    fe = end - f_trail
    return cond, (ts, max(ts, te)), (fs, max(fs, fe))


def _split_top_level_and(txt, start, end, tag_map):
    """If `txt[start:end]` has top-level `cond && <JSX>`, return `(cond, jsx_start, jsx_end)`."""
    i = start
    paren = brace = bracket = 0
    last_and = -1
    while i < end:
        ch = txt[i]
        if ch in ('"', "'"):
            i = min(end, _skip_quoted(txt, i, ch))
            continue
        if ch == '`':
            i = min(end, _skip_template(txt, i))
            continue
        if ch == '<' and (txt.startswith('<>', i) or i in tag_map):
            i = min(end, _skip_jsx_tag_or_fragment(txt, i, tag_map))
            continue
        if ch == '(':
            paren += 1
        elif ch == ')':
            paren = max(0, paren - 1)
        elif ch == '{':
            brace += 1
        elif ch == '}':
            brace = max(0, brace - 1)
        elif ch == '[':
            bracket += 1
        elif ch == ']':
            bracket = max(0, bracket - 1)
        elif paren == 0 and brace == 0 and bracket == 0 and txt.startswith('&&', i):
            rhs_strip = txt[i + 2:end].lstrip()
            if rhs_strip.startswith('<') or (rhs_strip.startswith('(') and '<' in rhs_strip):
                last_and = i
        i += 1
    if last_and == -1:
        return None
    cond = txt[start:last_and].strip()
    rhs = txt[last_and + 2:end]
    if '<' not in rhs:
        return None
    lead = len(rhs) - len(rhs.lstrip())
    trail = len(rhs) - len(rhs.rstrip())
    js = last_and + 2 + lead
    je = end - trail
    return cond, js, max(js, je)


def _split_top_level_lookup(txt, start, end, tag_map):
    """Detect `{ {a: <A/>, b: <B/>}[k] }` lookup branches; returns `[(label, s, e), ...]` or None."""
    expr = txt[start:end]
    stripped = expr.lstrip()
    lead = len(expr) - len(stripped)
    if not stripped:
        return None
    obj_rel = start + lead
    has_paren = False
    if stripped.startswith('('):
        has_paren = True
        inner_ws = len(stripped[1:]) - len(stripped[1:].lstrip())
        obj_rel += 1 + inner_ws
    if obj_rel >= end or txt[obj_rel] != '{':
        return None
    obj_end = min(end, _skip_balanced_braces(txt, obj_rel))
    after = txt[obj_end:end].lstrip()
    if has_paren:
        if not after.startswith(')'):
            return None
        after = after[1:].lstrip()
    if not after.startswith('['):
        return None

    inner_start = obj_rel + 1
    inner_end = obj_end - 1
    entries = []
    i = inner_start
    paren = brace = bracket = 0
    entry_start = i
    colon_pos = -1

    def _flush(end_pos):
        if colon_pos != -1:
            key = txt[entry_start:colon_pos].strip().strip('\'"')
            val_raw = txt[colon_pos + 1:end_pos]
            if '<' in val_raw:
                vl = len(val_raw) - len(val_raw.lstrip())
                vt = len(val_raw) - len(val_raw.rstrip())
                vs = colon_pos + 1 + vl
                ve = end_pos - vt
                entries.append((key or str(len(entries)), vs, max(vs, ve)))

    while i < inner_end:
        ch = txt[i]
        if ch in ('"', "'"):
            i = min(inner_end, _skip_quoted(txt, i, ch))
            continue
        if ch == '`':
            i = min(inner_end, _skip_template(txt, i))
            continue
        if ch == '<' and (txt.startswith('<>', i) or i in tag_map):
            i = min(inner_end, _skip_jsx_tag_or_fragment(txt, i, tag_map))
            continue
        if ch == '(':
            paren += 1
        elif ch == ')':
            paren = max(0, paren - 1)
        elif ch == '{':
            brace += 1
        elif ch == '}':
            brace = max(0, brace - 1)
        elif ch == '[':
            bracket += 1
        elif ch == ']':
            bracket = max(0, bracket - 1)
        elif paren == 0 and brace == 0 and bracket == 0:
            if ch == ':' and colon_pos == -1:
                colon_pos = i
            elif ch == ',':
                _flush(i)
                entry_start = i + 1
                colon_pos = -1
        i += 1
    _flush(inner_end)
    return entries if len(entries) >= 2 else None


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


def _cond_key_for_pair(cond):
    """Return `(family_key, branch_tag, is_positive)` for pairing sibling `&&` regions."""
    c = _strip_outer_parens(' '.join(cond.split()))
    m = re.fullmatch(r'(.+?)\s*(===|==|!==|!=)\s*(.+)', c)
    if m:
        lhs, op, rhs = m.group(1).strip(), m.group(2), m.group(3).strip()
        if rhs in ('true', 'false') and op in ('===', '=='):
            is_pos = rhs == 'true'
            return ('bool', lhs), f'{lhs}={rhs}', is_pos
        if op in ('===', '=='):
            return ('eq', lhs), f'{lhs}={rhs}', rhs
        if op in ('!==', '!='):
            return ('neq', lhs, rhs), f'{lhs}{op}{rhs}', False
    if c.startswith('!'):
        inner = _strip_outer_parens(c[1:])
        return ('bool', inner), f'{inner}=false', False
    return ('bool', c), f'{c}=true', True


def _are_mutually_exclusive_and_group(keys):
    """Return True if a run of >=2 sibling `&&` conditions are mutually exclusive."""
    if len(keys) < 2:
        return False
    fams = [k[0] for k in keys]
    if all(f[0] == 'bool' and f == fams[0] for f in fams) and len(keys) == 2:
        return keys[0][2] != keys[1][2]
    if all(f[0] == 'eq' and f == fams[0] for f in fams):
        vals = [k[2] for k in keys]
        return len(set(vals)) == len(vals)
    if len(keys) == 2 and {fams[0][0], fams[1][0]} == {'eq', 'neq'}:
        eq_k, neq_k = (keys[0], keys[1]) if fams[0][0] == 'eq' else (keys[1], keys[0])
        return eq_k[0][1] == neq_k[0][1] and eq_k[2] == neq_k[0][2]
    return False


def jsx_regions(txt):
    """Scan TSX/JSX text for mutually exclusive conditional regions (`ternary`, `and-pair`, `and`, `lookup`)."""
    if '{' not in txt and 'return' not in txt:
        return []
    masked = mask_non_markup(txt)
    tag_matches = list(TAG.finditer(masked))
    tag_map = {m.start(): m for m in tag_matches}
    regions = []
    seq = [0]

    def next_rid():
        rid = f'r{seq[0]}'
        seq[0] += 1
        return rid

    def flush_and_candidates(cands):
        i = 0
        while i < len(cands):
            def _adjacent(idx):
                prev_e = cands[idx - 1]['ee'] + 1
                next_s = cands[idx]['es'] - 1
                return prev_e <= next_s and not masked[prev_e:next_s].strip()

            j = i + 1
            if j < len(cands) and _adjacent(j):
                k_i = _cond_key_for_pair(cands[i]['cond'])
                if k_i[0][0] == 'eq':
                    run = [cands[i]]
                    while j < len(cands) and _adjacent(j):
                        k_j = _cond_key_for_pair(cands[j]['cond'])
                        if k_j[0] == k_i[0]:
                            run.append(cands[j])
                            j += 1
                        else:
                            break
                    if _are_mutually_exclusive_and_group([_cond_key_for_pair(x['cond']) for x in run]):
                        rid = next_rid()
                        branches = [
                            JsxBranch(rid, idx, _cond_key_for_pair(x['cond'])[1], x['js'], x['je'])
                            for idx, x in enumerate(run)
                        ]
                        regions.append(JsxRegion(rid, 'and-pair', run[0]['es'], run[-1]['ee'], branches))
                        i = j
                        continue
                k0 = _cond_key_for_pair(cands[i]['cond'])
                k1 = _cond_key_for_pair(cands[i + 1]['cond'])
                if _are_mutually_exclusive_and_group([k0, k1]):
                    rid = next_rid()
                    c0, c1 = cands[i], cands[i + 1]
                    branches = [
                        JsxBranch(rid, 0, k0[1], c0['js'], c0['je']),
                        JsxBranch(rid, 1, k1[1], c1['js'], c1['je']),
                    ]
                    regions.append(JsxRegion(rid, 'and-pair', c0['es'], c1['ee'], branches))
                    i += 2
                    continue
            c0 = cands[i]
            rid = next_rid()
            lbl = _cond_key_for_pair(c0['cond'])[1]
            regions.append(JsxRegion(rid, 'and', c0['es'], c0['ee'], [JsxBranch(rid, 0, lbl, c0['js'], c0['je'])]))
            i += 1

    def _unwrap_parens_span(s, e):
        while s < e:
            while s < e and masked[s].isspace():
                s += 1
            while e > s and masked[e - 1].isspace():
                e -= 1
            if s < e and masked[s] == '(' and masked[e - 1] == ')':
                depth = 0
                ok = True
                idx = s
                while idx < e:
                    ch = masked[idx]
                    if ch in ('"', "'"):
                        idx = _skip_quoted(masked, idx, ch)
                        continue
                    if ch == '`':
                        idx = _skip_template(masked, idx)
                        continue
                    if ch == '(':
                        depth += 1
                    elif ch == ')':
                        depth -= 1
                        if depth == 0 and idx < e - 1:
                            ok = False
                            break
                    idx += 1
                if ok and depth == 0:
                    s += 1
                    e -= 1
                    continue
            break
        return s, e

    def scan_expr(expr_s, expr_e, and_cands):
        expr = masked[expr_s:expr_e]
        if '<' not in expr:
            return
        us, ue = _unwrap_parens_span(expr_s, expr_e)
        # 1. Lookup `{ {a: <A/>, b: <B/>}[k] }`
        lookup = _split_top_level_lookup(masked, us, ue, tag_map)
        if lookup:
            rid = next_rid()
            branches = [JsxBranch(rid, idx, lbl, s, e) for idx, (lbl, s, e) in enumerate(lookup)]
            regions.append(JsxRegion(rid, 'lookup', expr_s, expr_e, branches))
            for _, s, e in lookup:
                scan_branch_content(s, e)
            return
        # 2. Ternary `{cond ? <A/> : <B/>}`
        tern = _split_top_level_ternary(masked, us, ue, tag_map)
        if tern:
            cond, (ts, te), (fs, fe) = tern
            c_lbl = _norm_cond_label(cond)
            rid = next_rid()
            branches = [
                JsxBranch(rid, 0, f'{c_lbl}=true', ts, te),
                JsxBranch(rid, 1, f'{c_lbl}=false', fs, fe),
            ]
            regions.append(JsxRegion(rid, 'ternary', expr_s, expr_e, branches))
            scan_branch_content(ts, te)
            scan_branch_content(fs, fe)
            return
        # 3. Logical AND `{cond && <A/>}`
        and_res = _split_top_level_and(masked, us, ue, tag_map)
        if and_res:
            cond, js, je = and_res
            and_cands.append({'cond': cond, 'js': js, 'je': je, 'es': expr_s, 'ee': expr_e})
            scan_branch_content(js, je)
            return
        # 4. General `{...}` containing JSX (e.g. `.map(...)`)
        scan_range(expr_s, expr_e, in_jsx=False)

    def scan_branch_content(s, e):
        us, ue = _unwrap_parens_span(s, e)
        sub = masked[us:ue]
        if not sub.startswith('<'):
            nested_cands = []
            scan_expr(us, ue, nested_cands)
            if nested_cands:
                flush_and_candidates(nested_cands)
            return
        scan_range(us, ue, in_jsx=True)

    def scan_range(start, end, *, in_jsx):
        i = start
        and_cands = []
        while i < end:
            ch = masked[i]
            if in_jsx:
                if ch in ('"', "'"):
                    i += 1
                    continue
                if ch == '<':
                    if masked.startswith('</>', i):
                        i += 3
                        continue
                    if masked.startswith('<>', i):
                        frag_end = min(end, _skip_jsx_tag_or_fragment(masked, i, tag_map))
                        scan_range(i + 2, max(i + 2, frag_end - 3), in_jsx=True)
                        i = frag_end
                        continue
                    if i in tag_map:
                        m = tag_map[i]
                        close, tag_name, _, selfclose = m.groups()
                        if close != '</' and not selfclose and tag_name.lower() not in VOID:
                            el_end = min(end, _skip_jsx_tag_or_fragment(masked, i, tag_map))
                            scan_range(m.end(), el_end, in_jsx=True)
                            i = el_end
                            continue
                        i = m.end()
                        continue
                if ch == '{':
                    b_end = _skip_balanced_braces(masked, i)
                    scan_expr(i + 1, max(i + 1, b_end - 1), and_cands)
                    i = b_end
                    continue
            else:
                if ch in ('"', "'"):
                    i = _skip_quoted(masked, i, ch)
                    continue
                if ch == '`':
                    i = _skip_template(masked, i)
                    continue
                if ch == '<':
                    if masked.startswith('<>', i):
                        frag_end = min(end, _skip_jsx_tag_or_fragment(masked, i, tag_map))
                        scan_range(i + 2, max(i + 2, frag_end - 3), in_jsx=True)
                        i = frag_end
                        continue
                    if i in tag_map:
                        m = tag_map[i]
                        close, tag_name, _, selfclose = m.groups()
                        if close != '</' and not selfclose and tag_name.lower() not in VOID:
                            el_end = min(end, _skip_jsx_tag_or_fragment(masked, i, tag_map))
                            scan_range(m.end(), el_end, in_jsx=True)
                            i = el_end
                            continue
                        i = m.end()
                        continue
                # Handle bare `return cond ? <A/> : <B/>;` outside JSX tags
                if masked.startswith('return', i) and (i == 0 or not (masked[i - 1].isalnum() or masked[i - 1] == '_')):
                    nxt_ch = masked[i + 6:i + 7]
                    if nxt_ch and (nxt_ch.isspace() or nxt_ch == '('):
                        r_start = i + 6
                        r_end = _find_stmt_end(masked, r_start, end, tag_map)
                        if '<' in masked[r_start:r_end]:
                            scan_expr(r_start, r_end, and_cands)
                            i = r_end
                            continue
            i += 1
        if and_cands:
            flush_and_candidates(and_cands)

    scan_range(0, len(masked), in_jsx=False)
    return regions


def _find_stmt_end(txt, start, limit, tag_map):
    i = start
    paren = brace = bracket = 0
    while i < limit:
        ch = txt[i]
        if ch in ('"', "'"):
            i = _skip_quoted(txt, i, ch)
            continue
        if ch == '`':
            i = _skip_template(txt, i)
            continue
        if ch == '<' and (txt.startswith('<>', i) or i in tag_map):
            i = _skip_jsx_tag_or_fragment(txt, i, tag_map)
            continue
        if ch == '(':
            paren += 1
        elif ch == ')':
            if paren == 0:
                return i
            paren -= 1
        elif ch == '{':
            brace += 1
        elif ch == '}':
            if brace == 0:
                return i
            brace -= 1
        elif ch == '[':
            bracket += 1
        elif ch == ']':
            bracket = max(0, bracket - 1)
        elif ch == ';' and paren == 0 and brace == 0 and bracket == 0:
            return i
        i += 1
    return limit


conditional_regions = jsx_regions


# ---------------- cva / shadcn variant resolution (İP-A5) ----------------

_CVA_SUFFIX_RE = re.compile(r'(?:Variants?|Cva|Styles?|Classes?)$', re.I)
_CVA_CALL_HEAD_RE = re.compile(
    r'(?:(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*(?::[^=;]+)?=\s*)?'
    r'(?:[A-Za-z_$][\w$]*\.)?\bcva\s*(?:<[^{}()]*>)?\s*\('
)
_MICRO_TEXT_RE = re.compile(r'^(?:[a-z0-9]+:)*text-\[(?:1[01]|\d(?:\.\d+)?)px\]$|^(?:[a-z0-9]+:)*text-\[0\.6\d*rem\]$')


def _to_pascal_component(name):
    """Convert a variable or file stem (e.g. `buttonVariants` or `alert-dialog`) to PascalCase (`Button`, `AlertDialog`)."""
    if not name:
        return ''
    stem = _CVA_SUFFIX_RE.sub('', name) or name
    if '-' in stem or '_' in stem:
        parts = [p for p in re.split(r'[-_]+', stem) if p]
        return ''.join(p[:1].upper() + p[1:] for p in parts)
    return stem[:1].upper() + stem[1:]


@dataclass
class CvaDefinition:
    """Parsed `cva(base, { variants, defaultVariants, compoundVariants })` definition."""

    var_name: str
    component: str
    base: list[str] = field(default_factory=list)
    variants: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    default_variants: dict[str, str] = field(default_factory=dict)
    compound_variants: list[dict] = field(default_factory=list)
    components: tuple[str, ...] = ()
    line: int = 1
    source_path: str | None = None

    @property
    def defaultVariants(self) -> dict[str, str]:
        return self.default_variants

    @property
    def compoundVariants(self) -> list[dict]:
        return self.compound_variants

    def _as_dict(self):
        return {
            'var_name': self.var_name,
            'component': self.component,
            'components': self.components,
            'base': self.base,
            'variants': self.variants,
            'default_variants': self.default_variants,
            'defaultVariants': self.default_variants,
            'compound_variants': self.compound_variants,
            'compoundVariants': self.compound_variants,
            'line': self.line,
            'source_path': self.source_path,
        }

    def __getitem__(self, key):
        return self._as_dict()[key]

    def get(self, key, default=None):
        return self._as_dict().get(key, default)

    def __contains__(self, key):
        return key in self._as_dict()

    def keys(self):
        return ('var_name', 'component', 'components', 'base', 'variants', 'default_variants', 'defaultVariants', 'compound_variants', 'line', 'source_path')


class CvaRegistry(dict):
    """Mapping of component names to `CvaDefinition`, also supporting lookup by `var_name` (e.g. `buttonVariants`)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.by_var: dict[str, CvaDefinition] = {}
        self.by_lower: dict[str, CvaDefinition] = {}

    def register(self, defn: CvaDefinition, *extra_names: str):
        names = []
        for n in (defn.component, *defn.components, *extra_names):
            if n and n not in names:
                names.append(n)
        for comp in names:
            super().__setitem__(comp, defn)
            self.by_lower[comp.lower()] = defn
        if defn.var_name:
            self.by_var[defn.var_name] = defn
            self.by_lower[defn.var_name.lower()] = defn

    def lookup(self, key):
        if not isinstance(key, str) or not key:
            return None
        if super().__contains__(key):
            return super().__getitem__(key)
        if key in self.by_var:
            return self.by_var[key]
        pascal = _to_pascal_component(key)
        if super().__contains__(pascal):
            return super().__getitem__(pascal)
        return self.by_lower.get(key.lower())

    def __contains__(self, key):
        return self.lookup(key) is not None

    def __getitem__(self, key):
        res = self.lookup(key)
        if res is None:
            raise KeyError(key)
        return res

    def get(self, key, default=None):
        res = self.lookup(key)
        return default if res is None else res

    def merge_from(self, other):
        if isinstance(other, CvaRegistry):
            for comp, defn in super(CvaRegistry, other).items():
                self.register(defn, comp)
            for vname, defn in other.by_var.items():
                self.by_var[vname] = defn
                self.by_lower[vname.lower()] = defn
        elif isinstance(other, dict):
            for k, v in other.items():
                if isinstance(v, CvaDefinition):
                    self.register(v, k)
                elif isinstance(v, dict):
                    comp = v.get('component') or _to_pascal_component(k)
                    var_name = v.get('var_name') or k
                    defn = CvaDefinition(
                        var_name=var_name,
                        component=comp,
                        base=list(v.get('base', [])),
                        variants=dict(v.get('variants', {})),
                        default_variants=dict(v.get('default_variants') or v.get('defaultVariants') or {}),
                        compound_variants=list(v.get('compound_variants') or v.get('compoundVariants') or []),
                        components=tuple(v.get('components') or (comp,)),
                        line=int(v.get('line', 1)),
                        source_path=v.get('source_path'),
                    )
                    self.register(defn, k)
        return self


class CvaMetadata(dict):
    """Structured `cva` metadata for route mode (İP-A6) and `shadcn-defaults` (İP-C5/A8)."""

    def __getattr__(self, name):
        try:
            return super().__getitem__(name)
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __contains__(self, key):
        if super().__contains__(key):
            return True
        defs = super().get('definitions')
        return defs is not None and key in defs

    def __getitem__(self, key):
        if super().__contains__(key):
            return super().__getitem__(key)
        defs = super().get('definitions')
        if defs is not None and key in defs:
            return defs[key]
        raise KeyError(key)

    def get(self, key, default=None):
        if super().__contains__(key):
            return super().__getitem__(key)
        defs = super().get('definitions')
        if defs is not None and key in defs:
            return defs[key]
        return default

    def __bool__(self):
        return bool(super().get('definitions'))


def _skip_balanced_parens(src, i):
    """Given `src[i] == '('`, return index right after its matching `)`."""
    n = len(src)
    depth = 0
    while i < n:
        ch = src[i]
        if ch in ('"', "'"):
            i = _skip_quoted(src, i, ch)
            continue
        if ch == '`':
            i = _skip_template(src, i)
            continue
        if ch == '/' and i + 1 < n:
            if src[i + 1] == '/':
                nl = src.find('\n', i + 2)
                i = n if nl == -1 else nl + 1
                continue
            if src[i + 1] == '*':
                end = src.find('*/', i + 2)
                i = n if end == -1 else end + 2
                continue
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return n


def _mask_js_comments_and_strings_for_scan(txt):
    """Blank out comments and string literals (preserving length/newlines) so top-level `cva(` matches cleanly."""
    out = list(txt)
    i = 0
    n = len(txt)
    while i < n:
        ch = txt[i]
        if ch in ('"', "'"):
            end = _skip_quoted(txt, i, ch)
            for k in range(i, min(end, n)):
                if out[k] != '\n':
                    out[k] = ' '
            i = end
            continue
        if ch == '`':
            end = _skip_template(txt, i)
            for k in range(i, min(end, n)):
                if out[k] != '\n':
                    out[k] = ' '
            i = end
            continue
        if ch == '/' and i + 1 < n:
            if txt[i + 1] == '/':
                nl = txt.find('\n', i + 2)
                end = n if nl == -1 else nl
                for k in range(i, end):
                    out[k] = ' '
                i = end
                continue
            if txt[i + 1] == '*':
                end_c = txt.find('*/', i + 2)
                end = n if end_c == -1 else end_c + 2
                for k in range(i, end):
                    if out[k] != '\n':
                        out[k] = ' '
                i = end
                continue
        i += 1
    return ''.join(out)


def _extract_static_classes(node):
    """Extract static class list from a parsed AST node (`_StrNode`, `_ArrNode`, `_TemplateNode`, `_CallNode`, `_RawNode`)."""
    if isinstance(node, _StrNode):
        return node.val.split()
    if isinstance(node, _TemplateNode):
        out = []
        for item in node.parts:
            if item[0] == 'str':
                out.extend(item[1].split())
            elif len(item) > 1:
                out.extend(_extract_static_classes(item[1]))
        return out
    if isinstance(node, _ArrNode):
        out = []
        for item in node.items:
            out.extend(_extract_static_classes(item))
        return out
    if isinstance(node, _CallNode):
        tail = node.callee.rsplit('.', 1)[-1]
        if tail in _CLASS_HELPER_NAMES:
            out = []
            for arg in node.args:
                out.extend(_extract_static_classes(arg))
            return out
        return []
    if isinstance(node, _RawNode):
        # Support string concatenation like "a b " + "c d"
        lits = [dq or sq for dq, sq in re.findall(r'"([^"]*)"|\'([^\']*)\'', node.src)]
        if lits:
            return ' '.join(lits).split()
    return []


def _extract_scalar_key(node):
    """Extract a scalar variant option key (`"default"`, `"sm"`, `"true"`, `"false"`) from an AST node."""
    if isinstance(node, _StrNode):
        return node.val
    if isinstance(node, _BoolNode):
        return 'true' if node.val else 'false'
    if isinstance(node, _RawNode):
        m = re.match(r'^["\']([^"\']*)["\']', node.src.strip())
        if m:
            return m.group(1)
    return None


def _find_component_spans(txt, scan_txt):
    """Return `[(comp_name, body_start, body_end), ...]` for PascalCase component declarations in `txt`."""
    spans = []
    n = len(txt)
    for m in re.finditer(
        r'\b(?:function\s+([A-Z][\w$]*)\s*(?:<[^{}()]*>)?\s*\(|(?:const|let|var)\s+([A-Z][\w$]*)\s*(?::[^=;]+)?=)',
        scan_txt,
    ):
        comp_name = m.group(1) or m.group(2)
        start = m.start()
        # Scan forward to find the body/expression end
        i = m.end()
        end = min(n, start + 4000)
        while i < n:
            ch = scan_txt[i]
            if ch == '{':
                end = _skip_balanced_braces(txt, i)
                break
            if ch == '(':
                end = _skip_balanced_parens(txt, i)
                # If followed by `=> { ... }` or `{ ... }`, include the following block too
                j = end
                while j < n and scan_txt[j] in ' \t\r\n:A-Za-z0-9_<>,.|[]':
                    j += 1
                if j + 1 < n and scan_txt[j:j + 2] == '=>':
                    j += 2
                    while j < n and scan_txt[j].isspace():
                        j += 1
                if j < n and scan_txt[j] == '{':
                    end = _skip_balanced_braces(txt, j)
                elif j < n and scan_txt[j] == '(':
                    end = _skip_balanced_parens(txt, j)
                break
            if ch == ';':
                end = i + 1
                break
            i += 1
        spans.append((comp_name, start, end))
    return spans


def parse_cva_definitions(txt, *, source_path=None):
    """Parse `cva(base, { variants, defaultVariants, compoundVariants })` definitions in `txt` into a `CvaRegistry`."""
    registry = CvaRegistry()
    if 'cva' not in txt:
        return registry

    scan_txt = _mask_js_comments_and_strings_for_scan(txt)
    comp_spans = _find_component_spans(txt, scan_txt)
    file_comp = None
    if source_path:
        stem = pathlib.Path(source_path).stem
        if stem and stem.lower() not in ('index', 'page', 'layout', 'route', 'app', 'main'):
            file_comp = _to_pascal_component(stem)

    parsed_defs = []
    for m in _CVA_CALL_HEAD_RE.finditer(scan_txt):
        var_name = m.group(1) or ''
        open_paren = m.end() - 1
        if open_paren >= len(txt) or txt[open_paren] != '(':
            continue
        close_paren = _skip_balanced_parens(txt, open_paren)
        inner_src = txt[open_paren + 1:max(open_paren + 1, close_paren - 1)]
        call_src = f'cva({inner_src})'
        ast = _JsExprParser(_tokenize_js(call_src), call_src).parse()
        if not isinstance(ast, _CallNode):
            continue

        base = []
        config_node = None
        if ast.args:
            if isinstance(ast.args[0], _ObjNode):
                config_node = ast.args[0]
            else:
                base = _extract_static_classes(ast.args[0])
                if len(ast.args) >= 2 and isinstance(ast.args[1], _ObjNode):
                    config_node = ast.args[1]

        variants = {}
        default_variants = {}
        compound_variants = []

        if config_node is not None:
            for key_str, val_node in config_node.entries:
                if key_str == 'variants' and isinstance(val_node, _ObjNode):
                    for axis_name, axis_node in val_node.entries:
                        if isinstance(axis_node, _ObjNode):
                            axis_map = {}
                            for opt_name, opt_val in axis_node.entries:
                                axis_map[opt_name] = _extract_static_classes(opt_val)
                            variants[axis_name] = axis_map
                elif key_str == 'defaultVariants' and isinstance(val_node, _ObjNode):
                    for axis_name, def_val in val_node.entries:
                        scalar = _extract_scalar_key(def_val)
                        if scalar is not None:
                            default_variants[axis_name] = scalar
                elif key_str == 'compoundVariants' and isinstance(val_node, _ArrNode):
                    for item in val_node.items:
                        if not isinstance(item, _ObjNode):
                            continue
                        conds = {}
                        cv_cls = []
                        for ck, cv in item.entries:
                            if ck in ('class', 'className'):
                                cv_cls.extend(_extract_static_classes(cv))
                            elif isinstance(cv, _ArrNode):
                                vals = [s for s in (_extract_scalar_key(x) for x in cv.items) if s is not None]
                                if vals:
                                    conds[ck] = vals
                            else:
                                scalar = _extract_scalar_key(cv)
                                if scalar is not None:
                                    conds[ck] = scalar
                        if conds and cv_cls:
                            compound_variants.append({'conditions': conds, 'classes': cv_cls})

        comp_names = []
        if var_name:
            inferred = _to_pascal_component(var_name)
            if inferred:
                comp_names.append(inferred)
            v_pat = re.compile(rf'\b{re.escape(var_name)}\s*\(')
            for cname, cs, ce in comp_spans:
                if v_pat.search(txt[cs:ce]) and cname not in comp_names:
                    comp_names.append(cname)
        else:
            pos = m.start()
            for cname, cs, ce in comp_spans:
                if cs <= pos < ce and cname not in comp_names:
                    comp_names.append(cname)

        if not comp_names and file_comp:
            comp_names.append(file_comp)
        primary_comp = comp_names[0] if comp_names else (var_name or 'Component')
        defn = CvaDefinition(
            var_name=var_name or f'{primary_comp[:1].lower()}{primary_comp[1:]}Variants',
            component=primary_comp,
            base=base,
            variants=variants,
            default_variants=default_variants,
            compound_variants=compound_variants,
            components=tuple(comp_names or [primary_comp]),
            line=line_of(txt, m.start()),
            source_path=str(source_path) if source_path else None,
        )
        parsed_defs.append(defn)

    if len(parsed_defs) == 1 and file_comp and file_comp not in parsed_defs[0].components:
        d0 = parsed_defs[0]
        d0.components = (*d0.components, file_comp)

    for defn in parsed_defs:
        registry.register(defn)
    return registry


_CVA_FILE_CACHE: dict[str, tuple[int, int, CvaRegistry]] = {}


def _parse_cva_file_cached(file_path: pathlib.Path) -> CvaRegistry:
    key = str(file_path)
    try:
        st = file_path.stat()
    except OSError:
        return CvaRegistry()
    cached = _CVA_FILE_CACHE.get(key)
    if cached is not None and cached[0] == st.st_mtime_ns and cached[1] == st.st_size:
        return cached[2]
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
    except OSError:
        return CvaRegistry()
    reg = parse_cva_definitions(content, source_path=key) if 'cva' in content else CvaRegistry()
    _CVA_FILE_CACHE[key] = (st.st_mtime_ns, st.st_size, reg)
    return reg


def discover_cva_definitions(source_path=None, txt=''):
    """Discover and cache `cva` definitions from `txt` and nearby `components/ui/*.tsx` files."""
    registry = CvaRegistry()
    local_txt = txt

    if source_path:
        p = pathlib.Path(source_path)
        if not local_txt and p.is_file():
            try:
                local_txt = p.read_text(encoding='utf-8', errors='ignore')
            except OSError:
                local_txt = ''

        try:
            resolved = p.resolve()
        except OSError:
            resolved = p.absolute()

        start_dir = resolved if resolved.is_dir() else resolved.parent
        while not start_dir.exists() and start_dir.parent != start_dir:
            start_dir = start_dir.parent

        ancestors = [start_dir, *list(start_dir.parents)[:7]]
        seen_ui_dirs = set()
        ui_rel_candidates = (
            ('components', 'ui'),
            ('src', 'components', 'ui'),
            ('app', 'components', 'ui'),
            ('ui',),
            ('src', 'ui'),
        )
        for anc in ancestors:
            candidates = [anc.joinpath(*rel) for rel in ui_rel_candidates]
            if anc.name == 'ui':
                candidates.append(anc)
            for ui_dir in candidates:
                if ui_dir in seen_ui_dirs or not ui_dir.is_dir():
                    continue
                seen_ui_dirs.add(ui_dir)
                for ext in ('*.tsx', '*.ts', '*.jsx', '*.js'):
                    for fp in sorted(ui_dir.glob(ext)):
                        if fp.is_file():
                            registry.merge_from(_parse_cva_file_cached(fp))

        # Also follow direct relative imports in `local_txt` if they point to local component files
        if local_txt and start_dir.is_dir():
            for imp in re.findall(r'from\s+["\'](\.\.?/[^"\']+)["\']', local_txt):
                base_imp = (start_dir / imp).resolve()
                imp_candidates = [base_imp] if base_imp.suffix else [
                    base_imp.with_suffix(ext) for ext in ('.tsx', '.ts', '.jsx', '.js')
                ] + [base_imp / f'index{ext}' for ext in ('.tsx', '.ts', '.jsx', '.js')]
                for cand in imp_candidates:
                    if cand.is_file():
                        registry.merge_from(_parse_cva_file_cached(cand))
                        break

    if local_txt and 'cva' in local_txt:
        registry.merge_from(parse_cva_definitions(local_txt, source_path=source_path))

    return registry


def _parse_jsx_attrs(attrs):
    """Scan JSX tag attributes into `{attr_name: (kind, raw_value)}` where `kind` is `'str'`, `'expr'`, or `'bool'`."""
    out = {}
    i = 0
    n = len(attrs)
    while i < n:
        while i < n and (attrs[i].isspace() or attrs[i] == '/'):
            i += 1
        if i >= n:
            break
        if attrs[i] == '{':
            i = _skip_balanced_braces(attrs, i)
            continue
        m = re.match(r'[A-Za-z_:][\w:.-]*', attrs[i:])
        if not m:
            i += 1
            continue
        name = m.group(0)
        i += m.end()
        while i < n and attrs[i].isspace():
            i += 1
        if i < n and attrs[i] == '=' and (i + 1 >= n or attrs[i + 1] != '='):
            i += 1
            while i < n and attrs[i].isspace():
                i += 1
            if i < n and attrs[i] in ('"', "'"):
                end = _skip_quoted(attrs, i, attrs[i])
                out[name] = ('str', attrs[i + 1:max(i + 1, end - 1)])
                i = end
            elif i < n and attrs[i] == '{':
                end = _skip_balanced_braces(attrs, i)
                inner = attrs[i + 1:end - 1] if end > i + 1 and attrs[end - 1] == '}' else attrs[i + 1:end]
                out[name] = ('expr', inner.strip())
                i = end
            else:
                j = i
                while j < n and not attrs[j].isspace() and attrs[j] not in ('>', '/'):
                    j += 1
                out[name] = ('str', attrs[i:j])
                i = j
        else:
            out[name] = ('bool', 'true')
    return out


def _eval_cva_prop_ast(node):
    """Evaluate a JSX prop expression AST into `[(option_key_or_None, label), ...]` and `(cond, kind)`."""
    scalar = _extract_scalar_key(node)
    if scalar is not None:
        return [(scalar, '')], '', 'static'
    if isinstance(node, _NullNode):
        return [(None, '')], '', 'null'
    if isinstance(node, _TernaryNode):
        cond = _norm_cond_label(node.cond.src)
        pairs = _eval_cva_prop_ternary(node, depth=0)
        kind = 'nested-ternary' if len(pairs) > 2 else 'ternary'
        return pairs, cond, kind
    if isinstance(node, _AndNode):
        cond = _norm_cond_label(node.lhs.src)
        rhs_pairs, _, _ = _eval_cva_prop_ast(node.rhs)
        out = []
        for opt_k, sub_lbl in rhs_pairs:
            lbl = f'{cond}=true,{sub_lbl}' if sub_lbl else f'{cond}=true'
            out.append((opt_k, lbl))
        out.append((None, f'{cond}=false'))
        return out, cond, 'and'
    if isinstance(node, _OrNode):
        if isinstance(node.lhs, _AndNode):
            cond = _norm_cond_label(node.lhs.lhs.src)
            t_pairs, _, _ = _eval_cva_prop_ast(node.lhs.rhs)
            f_pairs, _, _ = _eval_cva_prop_ast(node.rhs)
            out = (
                [(k, f'{cond}=true,{l}' if l else f'{cond}=true') for k, l in t_pairs]
                + [(k, f'{cond}=false,{l}' if l else f'{cond}=false') for k, l in f_pairs]
            )
            return out, cond, 'ternary'
        lhs_scalar = _extract_scalar_key(node.lhs)
        if lhs_scalar:
            return [(lhs_scalar, '')], '', 'static'
        cond = _norm_cond_label(node.lhs.src) or 'expr'
        rhs_pairs, _, _ = _eval_cva_prop_ast(node.rhs)
        out = [(k, f'{cond}=empty,{l}' if l else f'{cond}=empty') for k, l in rhs_pairs]
        out.append((None, f'{cond}=set'))
        return out, cond, 'fallback'
    return [(None, '')], '', 'dynamic'


def _eval_cva_prop_ternary(node, depth=0):
    cond = _norm_cond_label(node.cond.src)
    out = []
    for is_true, branch in ((True, node.t_expr), (False, node.f_expr)):
        prefix = f'{cond}={"true" if is_true else "false"}'
        if isinstance(branch, _TernaryNode) and depth < 1:
            for sub_key, sub_lbl in _eval_cva_prop_ternary(branch, depth + 1):
                out.append((sub_key, f'{prefix},{sub_lbl}'))
        else:
            sub_pairs, _, _ = _eval_cva_prop_ast(branch)
            for sub_key, sub_lbl in sub_pairs:
                lbl = f'{prefix},{sub_lbl}' if sub_lbl else prefix
                out.append((sub_key, lbl))
    return out


def _apply_cva_definition_to_builder(defn: CvaDefinition, prop_sources: dict[str, tuple[str, object]], builder: _ClassSetBuilder):
    """Apply `defn.base`, variant selections from `prop_sources`, `default_variants`, and `compound_variants` to `builder`."""
    builder.base.extend(defn.base)
    resolved_static = {}

    for axis_name, axis_options in defn.variants.items():
        default_opt = defn.default_variants.get(axis_name)
        default_cls = list(axis_options.get(default_opt, [])) if default_opt is not None else []

        if axis_name not in prop_sources:
            if default_opt is not None:
                builder.base.extend(default_cls)
                resolved_static[axis_name] = default_opt
            continue

        kind, raw_val = prop_sources[axis_name]
        if kind in ('str', 'bool'):
            opt_key = str(raw_val)
            if opt_key in axis_options:
                builder.base.extend(axis_options[opt_key])
                resolved_static[axis_name] = opt_key
            elif default_opt is not None:
                builder.base.extend(default_cls)
                resolved_static[axis_name] = default_opt
            continue

        # kind == 'expr' (string source) or 'ast' (already parsed AST node)
        ast = raw_val if kind == 'ast' else _JsExprParser(_tokenize_js(str(raw_val)), str(raw_val)).parse()
        pairs, cond, branch_kind = _eval_cva_prop_ast(ast)
        if len(pairs) == 1 and not pairs[0][1]:
            opt_key = pairs[0][0]
            if opt_key is not None and opt_key in axis_options:
                builder.base.extend(axis_options[opt_key])
                resolved_static[axis_name] = opt_key
            elif default_opt is not None:
                builder.base.extend(default_cls)
                resolved_static[axis_name] = default_opt
        else:
            alts = []
            labels = []
            for opt_key, lbl in pairs:
                if opt_key is not None and opt_key in axis_options:
                    alts.append(list(axis_options[opt_key]))
                else:
                    alts.append(list(default_cls))
                labels.append(lbl)
            builder.add_group(alts, labels, kind=branch_kind, cond=cond)

    for cv in defn.compound_variants:
        conds = cv.get('conditions', {})
        matched = True
        for ck, expected in conds.items():
            actual = resolved_static.get(ck)
            if isinstance(expected, (list, tuple, set)):
                if actual not in expected:
                    matched = False
                    break
            elif actual != expected:
                matched = False
                break
        if matched:
            builder.base.extend(cv.get('classes', []))


def _merge_classsets(cva_cs: ClassSet, attr_cs: ClassSet) -> ClassSet:
    """Merge `cva_cs` with `attr_cs` so `className` base and branches come last (overriding `cva` defaults)."""
    if not cva_cs.base and not cva_cs.branches:
        return attr_cs
    if not attr_cs.base and not attr_cs.branches and not attr_cs.cva_calls:
        return cva_cs

    builder = _ClassSetBuilder()
    builder.base.extend(cva_cs.base)
    for gid, alts in cva_cs.branches:
        grp = cva_cs.groups.get(gid, {})
        builder.add_group(
            [list(a) for a in alts],
            list(grp.get('labels', [])),
            kind=grp.get('kind', 'ternary'),
            cond=grp.get('cond', ''),
        )
    builder.base.extend(attr_cs.base)
    for gid, alts in attr_cs.branches:
        grp = attr_cs.groups.get(gid, {})
        builder.add_group(
            [list(a) for a in alts],
            list(grp.get('labels', [])),
            kind=grp.get('kind', 'ternary'),
            cond=grp.get('cond', ''),
        )
    builder.cva_calls = list(cva_cs.cva_calls) + list(attr_cs.cva_calls)
    merged = builder.build()
    # When cva has conditional branches and className has static overrides, keep attr_cs.base in tail
    # so expand_combinations() also places className overrides after branch classes.
    if cva_cs.branches and attr_cs.base:
        merged.tail = list(attr_cs.base)
    return merged


def _lookup_cva_defn(key, cva_defs):
    if not cva_defs or not key:
        return None
    if isinstance(cva_defs, CvaRegistry):
        return cva_defs.lookup(key)
    if isinstance(cva_defs, CvaMetadata):
        return cva_defs.get(key)
    if isinstance(cva_defs, dict):
        if key in cva_defs:
            val = cva_defs[key]
        else:
            var_key = f'{key[:1].lower()}{key[1:]}Variants'
            val = cva_defs.get(var_key) or cva_defs.get(_to_pascal_component(key))
        if isinstance(val, CvaDefinition):
            return val
        if isinstance(val, dict):
            reg = CvaRegistry()
            reg.merge_from({key: val})
            return reg.lookup(key)
    return None


def resolve_cva_classes(tag, attrs, cva_defs=None, *, include_class_attr=True):
    """Resolve `cva` base + selected/default/conditional variant classes for `<Tag ...attrs>` into a `ClassSet`."""
    attr_cs = classset(attrs) if include_class_attr else ClassSet()
    if not cva_defs:
        return attr_cs

    defn = _lookup_cva_defn(tag, cva_defs) if tag and tag[:1].isupper() else None
    builder = _ClassSetBuilder()

    if defn is not None:
        jsx_attrs = _parse_jsx_attrs(attrs)
        prop_sources = {k: v for k, v in jsx_attrs.items() if k not in ('class', 'className')}
        _apply_cva_definition_to_builder(defn, prop_sources, builder)
    else:
        # Check for direct `buttonVariants({ variant: "outline", size: "sm" })` calls inside `className={...}`
        probe_cs = attr_cs if include_class_attr else classset(attrs)
        for call_info in probe_cs.cva_calls:
            callee = call_info.get('callee', '').rsplit('.', 1)[-1]
            call_defn = _lookup_cva_defn(callee, cva_defs)
            if call_defn is None:
                continue
            call_src = call_info.get('src', '')
            call_ast = _JsExprParser(_tokenize_js(call_src), call_src).parse()
            if not isinstance(call_ast, _CallNode):
                continue
            prop_sources = {}
            is_template_wrapper = False
            if call_ast.args and isinstance(call_ast.args[0], _ObjNode):
                obj_entries = call_ast.args[0].entries
                passthrough_count = sum(
                    1 for k, v in obj_entries if isinstance(v, _RawNode) and v.src.strip() == k
                )
                if obj_entries and passthrough_count == len(obj_entries):
                    is_template_wrapper = True
                for k, v in obj_entries:
                    if k in ('class', 'className'):
                        continue
                    if isinstance(v, _RawNode) and v.src.strip() == k:
                        continue
                    prop_sources[k] = ('ast', v)
            if not is_template_wrapper:
                _apply_cva_definition_to_builder(call_defn, prop_sources, builder)

    cva_cs = builder.build()
    if include_class_attr:
        return _merge_classsets(cva_cs, attr_cs)
    return cva_cs


def extract_cva_metadata(txt, *, source_path=None):
    """Extract structured `cva` definitions, default resolved classes, and `shadcn-defaults` signals from `txt`."""
    defs = parse_cva_definitions(txt, source_path=source_path)
    components = dict(defs)
    by_var = dict(defs.by_var)
    default_classes = {}
    variants_map = {}
    all_classes = []
    shadcn_defaults = []
    small_heights = []
    micro_texts = []

    seen_defs = set()
    for comp_name, defn in components.items():
        variants_map[comp_name] = defn.variants
        def_builder = _ClassSetBuilder()
        _apply_cva_definition_to_builder(defn, {}, def_builder)
        default_classes[comp_name] = list(def_builder.base)

        if id(defn) in seen_defs:
            continue
        seen_defs.add(id(defn))

        def _inspect_tokens(tokens_list, axis_name, opt_name):
            for tok in tokens_list:
                all_classes.append(tok)
                raw_tok = tok.rsplit(':', 1)[-1]
                h_val = height_px([raw_tok])
                if h_val is not None and h_val < 40:
                    entry = {
                        'component': defn.component,
                        'var_name': defn.var_name,
                        'axis': axis_name,
                        'option': opt_name,
                        'token': tok,
                        'kind': 'small-height',
                        'height_px': h_val,
                        'line': defn.line,
                    }
                    shadcn_defaults.append(entry)
                    small_heights.append((defn.component, axis_name, opt_name, tok, h_val, defn.line))
                if _MICRO_TEXT_RE.match(tok):
                    entry = {
                        'component': defn.component,
                        'var_name': defn.var_name,
                        'axis': axis_name,
                        'option': opt_name,
                        'token': tok,
                        'kind': 'micro-text',
                        'line': defn.line,
                    }
                    shadcn_defaults.append(entry)
                    micro_texts.append((defn.component, axis_name, opt_name, tok, defn.line))

        _inspect_tokens(defn.base, 'base', 'base')
        for axis_name, axis_opts in defn.variants.items():
            for opt_name, opt_tokens in axis_opts.items():
                _inspect_tokens(opt_tokens, axis_name, opt_name)

    return CvaMetadata(
        definitions=defs,
        components=components,
        by_var=by_var,
        default_classes=default_classes,
        defaults=default_classes,
        variants=variants_map,
        all_classes=all_classes,
        shadcn_defaults=shadcn_defaults,
        issues=shadcn_defaults,
        small_heights=small_heights,
        micro_texts=micro_texts,
    )


def walk(txt, cva_defs=None, source_path=None):
    """Yield ParsedNode (tag, attrs, classes, ancestors, start, end) for every opening tag; ancestors innermost-last."""
    active_cva = None
    inlined_cva = getattr(txt, 'cva_registry', None)
    if cva_defs is not None:
        active_cva = CvaRegistry().merge_from(cva_defs)
        if inlined_cva:
            active_cva.merge_from(inlined_cva)
        if 'cva' in txt:
            active_cva.merge_from(parse_cva_definitions(txt, source_path=source_path))
    elif inlined_cva is not None:
        active_cva = CvaRegistry().merge_from(inlined_cva)
        if source_path is not None:
            active_cva.merge_from(discover_cva_definitions(source_path, txt))
        elif 'cva' in txt:
            active_cva.merge_from(parse_cva_definitions(txt))
    elif source_path is not None:
        active_cva = discover_cva_definitions(source_path, txt)
    elif 'cva' in txt:
        active_cva = parse_cva_definitions(txt)

    regions = jsx_regions(txt) if '{' in txt or 'return' in txt else []
    branches_flat = [
        (b.start, b.end, (b.region_id, b.branch_index), b.label)
        for r in regions
        for b in r.branches
    ]
    stack = []
    for m in TAG.finditer(txt):
        close, tag, attrs, selfclose = m.groups()
        if close == '</':
            for i in range(len(stack) - 1, -1, -1):
                if stack[i][0].lower() == tag.lower():
                    del stack[i:]
                    break
            continue
        pos = m.start()
        attr_cls = classes(attrs)
        attr_cs = classset(attrs)
        if active_cva and ((tag[:1].isupper() and tag in active_cva) or attr_cs.cva_calls):
            cva_only_cs = resolve_cva_classes(tag, attrs, active_cva, include_class_attr=False)
            if cva_only_cs.base or cva_only_cs.branches:
                cs = _merge_classsets(cva_only_cs, attr_cs)
                cls = cva_only_cs.flat_classes + attr_cls
            else:
                cs = attr_cs
                cls = attr_cls
        else:
            cs = attr_cs
            cls = attr_cls
        if 'data-uitools-unknown-bg' in attrs and pick(cls, 'bg') is None:
            cls = list(cls) + ['bg-[UNKNOWN]']
            cs.base = list(cs.base) + ['bg-[UNKNOWN]']
        b_hits = []
        if branches_flat:
            hits = [
                (end - start, ref, lbl)
                for start, end, ref, lbl in branches_flat
                if start <= pos < end
            ]
            hits.sort(key=lambda x: x[0], reverse=True)
            b_hits = hits
        b_regions = tuple(ref for _, ref, _ in b_hits)
        b_region = b_regions[-1] if b_regions else None
        b_label = b_hits[-1][2] if b_hits else None
        node = AncestorNode(
            (tag, attrs, cls, pos),
            classset=cs,
            branch_region=b_region,
            branch_regions=b_regions,
            branch_label=b_label,
        )
        yield ParsedNode(
            (tag, attrs, cls, list(stack), pos, m.end()),
            classset=cs,
            branch_region=b_region,
            branch_regions=b_regions,
            branch_label=b_label,
        )
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
        m = re.fullmatch(r'(?:h|size)-(\d+(?:\.\d+)?)', c)
        if m:
            h = float(m.group(1)) * 4
        m = re.fullmatch(r'(?:h|size)-\[(\d+)px\]', c)
        if m:
            h = float(m.group(1))
    return h


def _has_row_flex(cls):
    return 'flex' in cls and not any(c.endswith('flex-col') for c in cls)


def line_of(txt, pos):
    line_at = getattr(txt, 'line_at', None)
    if line_at is not None:
        return line_at(pos)
    return txt.count('\n', 0, pos) + 1
