"""Route/screen composition, component inlining, and route-vs-component classification (Phase A6)."""
from __future__ import annotations

import bisect
from dataclasses import dataclass, field
import json
import pathlib
import re

from uiparse import (
    TAG,
    VOID,
    CvaRegistry,
    _skip_balanced_braces,
    _skip_balanced_parens,
    _skip_quoted,
    _skip_template,
    discover_cva_definitions,
    mask_non_markup,
    parse_cva_definitions,
)

__all__ = [
    'API_VERSION',
    'COMPONENT_DIRS',
    'SCREEN_RULES',
    'COMPONENT_RULE_NOTE',
    'RouteSourceText',
    'VirtualMarkup',
    'ComponentDef',
    'find_project_root',
    'load_tsconfig_paths',
    'resolve_import',
    'parse_imports',
    'extract_components',
    'inline_local_components',
    'compose_route',
    'is_page_file',
    'is_component_file',
]

API_VERSION = '1.0'

COMPONENT_DIRS = frozenset({
    'components',
    'component',
    'ui',
    'widgets',
    'partials',
    'shared',
    'modals',
    'layout',
    'layouts',
})

SCREEN_RULES = frozenset({
    'no-hero-surface',
    'landmark-main',
    'miller-7',
    'skeleton-empty',
})

COMPONENT_RULE_NOTE = ' (bileşen dosyası; ekran kuralları için --route kullan)'

_TRANSPARENT_FRAMEWORK_TAGS = frozenset({
    'Link',
    'NavLink',
    'Fragment',
    'React.Fragment',
    'Suspense',
    'StrictMode',
    'React.StrictMode',
    'Head',
    'Script',
    'Image',
})

_TS_EXTS = ('.tsx', '.ts', '.jsx', '.js', '.vue', '.svelte')
_PAGE_FILENAMES = frozenset({'page.tsx', 'page.ts', 'page.jsx', 'page.js'})
_LAYOUT_FILENAMES = ('layout.tsx', 'layout.ts', 'layout.jsx', 'layout.js')
_JSX_FILE_EXTS = frozenset({'.tsx', '.jsx', '.ts', '.js', '.vue', '.svelte'})
_SFC_EXTS = frozenset({'.vue', '.svelte'})

_THEME_TOGGLE_HINT_RE = re.compile(
    r'(?:ThemeToggle|setTheme|next-themes|useTheme|data-theme-toggle|classList\.toggle\s*\(\s*[\'"]dark[\'"]\s*\)|toggleTheme)'
)


def _compute_line_starts(src: str) -> list[int]:
    return [0] + [i + 1 for i, ch in enumerate(src) if ch == '\n']


class RouteSourceText(str):
    """String subclass wrapping entry source text while carrying inlined component source files and active line maps."""

    def __new__(
        cls,
        text: str,
        *,
        entry_file: str | None = None,
        source_files: dict[str, str] | list[tuple[str, str]] | None = None,
        active_lines: dict[str, set[int]] | None = None,
    ):
        obj = super().__new__(cls, text)
        obj.entry_file = entry_file
        if isinstance(source_files, dict):
            obj.source_files = dict(source_files)
        elif source_files is not None:
            obj.source_files = dict(source_files)
        else:
            obj.source_files = {}
        obj.active_lines = {k: set(v) for k, v in (active_lines or {}).items()}
        return obj


class VirtualMarkup(str):
    """String subclass carrying virtual-to-source line mappings, CVA registry, and inlined file metadata."""

    def __new__(
        cls,
        text: str,
        *,
        seg_starts: list[int] | None = None,
        seg_meta: list[tuple[list[int] | None, int]] | None = None,
        cva_registry: CvaRegistry | None = None,
        inlined_files: list[str] | None = None,
        inlined_count: int = 0,
        raw_txt: str | None = None,
    ):
        obj = super().__new__(cls, text)
        obj._seg_starts = seg_starts if seg_starts is not None else []
        obj._seg_meta = seg_meta if seg_meta is not None else []
        obj.cva_registry = cva_registry
        obj.inlined_files = list(inlined_files or [])
        obj.inlined_count = int(inlined_count)
        obj.raw_txt = raw_txt if raw_txt is not None else text
        return obj

    def line_at(self, pos: int) -> int:
        if not self._seg_starts:
            return self.count('\n', 0, max(0, pos)) + 1
        if pos < 0:
            pos = 0
        idx = bisect.bisect_right(self._seg_starts, pos) - 1
        if idx < 0:
            return 1
        ls, orig_start = self._seg_meta[idx]
        if ls is None:
            return orig_start
        orig_pos = orig_start + (pos - self._seg_starts[idx])
        return max(1, bisect.bisect_right(ls, orig_pos))

    def _clone_with_text(self, new_text: str) -> 'VirtualMarkup':
        return VirtualMarkup(
            new_text,
            seg_starts=self._seg_starts,
            seg_meta=self._seg_meta,
            cva_registry=self.cva_registry,
            inlined_files=self.inlined_files,
            inlined_count=self.inlined_count,
            raw_txt=self.raw_txt,
        )


class _VirtualBuilder:
    """Incrementally builds a `VirtualMarkup` from source slices and synthetic text."""

    def __init__(self):
        self.chunks: list[str] = []
        self.seg_starts: list[int] = []
        self.seg_meta: list[tuple[list[int] | None, int]] = []
        self.offset = 0

    def append_slice(self, src: str, line_starts: list[int], start: int, end: int):
        if end <= start:
            return
        text = src[start:end]
        self.seg_starts.append(self.offset)
        self.seg_meta.append((line_starts, start))
        self.chunks.append(text)
        self.offset += len(text)

    def append_masked_spaces(self, src: str, line_starts: list[int], start: int, end: int):
        if end <= start:
            return
        masked = re.sub(r'[^\n]', ' ', src[start:end])
        self.seg_starts.append(self.offset)
        self.seg_meta.append((line_starts, start))
        self.chunks.append(masked)
        self.offset += len(masked)

    def append_synthetic(self, text: str, fixed_line: int):
        if not text:
            return
        self.seg_starts.append(self.offset)
        self.seg_meta.append((None, max(1, int(fixed_line))))
        self.chunks.append(text)
        self.offset += len(text)

    def append_segments(self, segments: list[tuple[str, list[int] | None, int]]):
        for text, ls, orig_start in segments:
            if not text:
                continue
            self.seg_starts.append(self.offset)
            self.seg_meta.append((ls, orig_start))
            self.chunks.append(text)
            self.offset += len(text)

    def build(
        self,
        *,
        cva_registry: CvaRegistry | None = None,
        inlined_files: list[str] | None = None,
        inlined_count: int = 0,
        raw_txt: str = '',
    ) -> VirtualMarkup:
        return VirtualMarkup(
            ''.join(self.chunks),
            seg_starts=self.seg_starts,
            seg_meta=self.seg_meta,
            cva_registry=cva_registry,
            inlined_files=inlined_files,
            inlined_count=inlined_count,
            raw_txt=raw_txt,
        )


@dataclass
class ComponentDef:
    """Extracted React function/arrow component and its JSX return span."""

    name: str
    body_start: int
    body_end: int
    jsx_start: int
    jsx_end: int
    is_exported: bool = False
    is_default: bool = False


# ---------------- route vs component classification ----------------

def is_page_file(path, txt=None) -> bool:
    """Return True when `path` (or full-document `txt`) represents a page/route entry."""
    if path:
        p = pathlib.Path(path)
        suf = p.suffix.lower()
        if suf in ('.html', '.htm'):
            return True
        parts = [part.lower() for part in p.parts]
        name_low = p.name.lower()
        if suf in _JSX_FILE_EXTS:
            if 'app' in parts and name_low in _PAGE_FILENAMES:
                return True
            if suf == '.svelte' and name_low == '+page.svelte':
                return True
            parent_parts = parts[:-1]
            # If a component directory appears inside pages/, routes/, or views/, prefer component classification
            if not (set(parent_parts) & COMPONENT_DIRS):
                if 'pages' in parent_parts or 'routes' in parent_parts:
                    return True
                if suf == '.vue' and 'views' in parent_parts:
                    return True
    if txt:
        head = txt[:4096]
        if re.search(r'<!doctype\b|<html\b', head, re.I):
            return True
    return False


def is_component_file(path, txt=None, route_mode=False) -> bool:
    """Return True when `path` is a reusable component file (and not in `route_mode`)."""
    if route_mode or not path:
        return False
    if is_page_file(path, txt=txt):
        return False
    p = pathlib.Path(path)
    parent_parts = [part.lower() for part in p.parts[:-1]]
    return any(part in COMPONENT_DIRS for part in parent_parts)


# ---------------- project root, tsconfig & import resolution ----------------

def find_project_root(start_path) -> pathlib.Path:
    """Walk upward from `start_path` looking for tsconfig.json, jsconfig.json, or package.json."""
    p = pathlib.Path(start_path)
    try:
        resolved = p.resolve()
    except OSError:
        resolved = p.absolute()
    cur = resolved if resolved.is_dir() else resolved.parent
    while not cur.exists() and cur.parent != cur:
        cur = cur.parent
    for anc in (cur, *cur.parents):
        if any((anc / marker).is_file() for marker in ('tsconfig.json', 'jsconfig.json', 'package.json')):
            return anc
    # Fallback for marker-less layouts (`<root>/src/...` or `<root>/app/...`)
    for anc in (cur, *list(cur.parents)[:4]):
        if anc.name.lower() in ('src', 'app') and anc.parent != anc:
            return anc.parent
    return cur


def _strip_jsonc(raw: str) -> str:
    """Strip // and /* */ comments and trailing commas from JSONC (`tsconfig.json`) safely."""
    out = []
    i = 0
    n = len(raw)
    while i < n:
        ch = raw[i]
        if ch == '"':
            end = _skip_quoted(raw, i, '"')
            out.append(raw[i:end])
            i = end
            continue
        if ch == '/' and i + 1 < n:
            if raw[i + 1] == '/':
                nl = raw.find('\n', i + 2)
                i = n if nl == -1 else nl
                continue
            if raw[i + 1] == '*':
                end = raw.find('*/', i + 2)
                i = n if end == -1 else end + 2
                continue
        out.append(ch)
        i += 1
    cleaned = ''.join(out)
    # Remove trailing commas before } or ] outside strings
    res = []
    i = 0
    m = len(cleaned)
    while i < m:
        ch = cleaned[i]
        if ch == '"':
            end = _skip_quoted(cleaned, i, '"')
            res.append(cleaned[i:end])
            i = end
            continue
        if ch == ',':
            j = i + 1
            while j < m and cleaned[j].isspace():
                j += 1
            if j < m and cleaned[j] in ('}', ']'):
                i += 1
                continue
        res.append(ch)
        i += 1
    return ''.join(res)


def load_tsconfig_paths(tsconfig_path=None, root_dir=None, _seen=None) -> tuple[pathlib.Path | None, dict[str, list[str]]]:
    """Load `(base_url_path, paths_dict)` from `tsconfig.json` (or `jsconfig.json`)."""
    ts_path = pathlib.Path(tsconfig_path) if tsconfig_path else None
    if ts_path is None and root_dir is not None:
        rd = pathlib.Path(root_dir)
        for cand_name in ('tsconfig.json', 'jsconfig.json'):
            cand = rd / cand_name
            if cand.is_file():
                ts_path = cand
                break
    if ts_path is None or not ts_path.is_file():
        return (pathlib.Path(root_dir).resolve() if root_dir else None), {}

    try:
        ts_resolved = ts_path.resolve()
    except OSError:
        ts_resolved = ts_path.absolute()
    seen = set(_seen or ())
    if ts_resolved in seen:
        return ts_resolved.parent, {}
    seen.add(ts_resolved)

    try:
        raw = ts_resolved.read_text(encoding='utf-8', errors='ignore')
        data = json.loads(_strip_jsonc(raw))
    except (OSError, json.JSONDecodeError, ValueError):
        return ts_resolved.parent, {}

    if not isinstance(data, dict):
        return ts_resolved.parent, {}

    base_url = None
    paths: dict[str, list[str]] = {}
    extends = data.get('extends')
    if isinstance(extends, str) and extends.startswith('.'):
        ext_path = (ts_resolved.parent / extends)
        if not ext_path.is_file() and ext_path.with_suffix('.json').is_file():
            ext_path = ext_path.with_suffix('.json')
        if ext_path.is_file():
            base_url, ext_paths = load_tsconfig_paths(ext_path, root_dir=root_dir, _seen=seen)
            paths.update(ext_paths)

    co = data.get('compilerOptions') or {}
    if isinstance(co, dict):
        bu = co.get('baseUrl')
        if isinstance(bu, str) and bu:
            base_url = (ts_resolved.parent / bu).resolve()
        raw_paths = co.get('paths')
        if isinstance(raw_paths, dict):
            for k, v in raw_paths.items():
                if isinstance(k, str) and isinstance(v, list):
                    paths[k] = [str(item) for item in v if isinstance(item, str)]

    if base_url is None:
        base_url = ts_resolved.parent
    return base_url, paths


def _resolve_file_candidate(cand: pathlib.Path) -> pathlib.Path | None:
    try:
        if cand.is_file():
            return cand.resolve()
    except OSError:
        return None
    base_str = str(cand)
    for ext in _TS_EXTS:
        p = pathlib.Path(base_str + ext)
        if p.is_file():
            return p.resolve()
    if cand.is_dir():
        for ext in _TS_EXTS:
            idx = cand / f'index{ext}'
            if idx.is_file():
                return idx.resolve()
    return None


def _match_tsconfig_pattern(pattern: str, spec: str) -> str | None:
    if '*' not in pattern:
        return '' if spec == pattern else None
    prefix, suffix = pattern.split('*', 1)
    if not spec.startswith(prefix):
        return None
    if suffix and not spec.endswith(suffix):
        return None
    end_idx = len(spec) - len(suffix) if suffix else len(spec)
    if end_idx < len(prefix):
        return None
    return spec[len(prefix):end_idx]


def resolve_import(
    import_spec: str,
    current_file,
    root_dir=None,
    tsconfig_paths=None,
) -> pathlib.Path | None:
    """Resolve a relative, `@/`, or `tsconfig.json` `paths` import specifier to an existing file."""
    if not import_spec or not isinstance(import_spec, str):
        return None
    spec = import_spec.strip()
    if not spec:
        return None

    cur_path = pathlib.Path(current_file) if current_file else None
    cur_dir = cur_path.parent if cur_path else pathlib.Path.cwd()
    eff_root = pathlib.Path(root_dir).resolve() if root_dir else (find_project_root(cur_path) if cur_path else pathlib.Path.cwd())

    # 1. Relative imports: ./ or ../ or . or ..
    if spec.startswith('./') or spec.startswith('../') or spec in ('.', '..'):
        return _resolve_file_candidate(cur_dir / spec)

    # 2. tsconfig paths
    base_url = eff_root
    paths_dict: dict[str, list[str]] = {}
    if isinstance(tsconfig_paths, tuple) and len(tsconfig_paths) == 2:
        bu, pd = tsconfig_paths
        if bu is not None:
            base_url = pathlib.Path(bu)
        if isinstance(pd, dict):
            paths_dict = pd
    elif isinstance(tsconfig_paths, dict):
        paths_dict = tsconfig_paths

    if paths_dict:
        # Prefer longest literal prefix match
        matches = []
        for pat, targets in paths_dict.items():
            matched = _match_tsconfig_pattern(pat, spec)
            if matched is not None:
                prefix_len = len(pat.split('*', 1)[0])
                matches.append((prefix_len, pat, matched, targets))
        matches.sort(key=lambda x: x[0], reverse=True)
        for _, pat, matched, targets in matches:
            for tgt in targets:
                rel_tgt = tgt.replace('*', matched) if '*' in pat else tgt
                resolved = _resolve_file_candidate(base_url / rel_tgt)
                if resolved is not None:
                    return resolved
                if eff_root != base_url:
                    resolved_root = _resolve_file_candidate(eff_root / rel_tgt)
                    if resolved_root is not None:
                        return resolved_root

    # 3. SvelteKit $lib/ alias (<root>/src/lib/ or <root>/lib/)
    if spec.startswith('$lib/') or spec == '$lib':
        sub = spec[5:] if spec.startswith('$lib/') else ''
        for base in (eff_root / 'src' / 'lib', eff_root / 'lib'):
            resolved = _resolve_file_candidate(base / sub if sub else base)
            if resolved is not None:
                return resolved

    # 4. Default @/ alias (root_dir/src or root_dir)
    if spec.startswith('@/'):
        sub = spec[2:]
        for base in (eff_root / 'src', eff_root):
            resolved = _resolve_file_candidate(base / sub)
            if resolved is not None:
                return resolved

    # 5. Non-relative baseUrl path (only if explicitly configured via tsconfig_paths tuple and contains '/')
    if isinstance(tsconfig_paths, tuple) and tsconfig_paths[0] is not None and '/' in spec and not spec.startswith(('@', '$')):
        resolved = _resolve_file_candidate(pathlib.Path(tsconfig_paths[0]) / spec)
        if resolved is not None:
            return resolved

    return None


# ---------------- JS/TSX import & component parsing ----------------

def _strip_js_comments_preserve_strings(src: str) -> str:
    """Replace // and /* */ comments with spaces outside string/template literals."""
    out = list(src)
    i = 0
    n = len(src)
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
                end = n if nl == -1 else nl
                for k in range(i, end):
                    out[k] = ' '
                i = end
                continue
            if src[i + 1] == '*':
                end_c = src.find('*/', i + 2)
                end = n if end_c == -1 else end_c + 2
                for k in range(i, end):
                    if out[k] != '\n':
                        out[k] = ' '
                i = end
                continue
        i += 1
    return ''.join(out)


_IMPORT_RE = re.compile(
    r"""(?:^|[;\n])\s*import\s+(?!type\b)(?P<clause>[^;"']*?)\s+from\s+["'](?P<spec>[^"']+)["']""",
    re.S,
)


def _extract_sfc_script_text(txt: str) -> str:
    """Extract inner `<script>` block text from `.vue` / `.svelte` SFCs (outside HTML comments)."""
    no_html_comments = re.sub(r'<!--.*?-->', ' ', txt, flags=re.S)
    blocks = re.findall(r'<script\b[^>]*>(.*?)</script>', no_html_comments, flags=re.S | re.I)
    return '\n'.join(blocks)


def parse_imports(txt: str, *, _from_sfc: bool = False) -> dict[str, tuple[str, str]]:
    """Parse ES imports into `{local_name: (imported_name, import_spec)}`."""
    cleaned = _strip_js_comments_preserve_strings(txt)
    out: dict[str, tuple[str, str]] = {}
    for m in _IMPORT_RE.finditer(cleaned):
        clause = m.group('clause').strip()
        spec = m.group('spec').strip()
        if not clause or clause.startswith('type '):
            continue
        # Handle `{ ... }` named imports and optional leading default import
        brace_m = re.search(r'\{([^}]*)\}', clause)
        if brace_m:
            before = clause[:brace_m.start()].strip().rstrip(',').strip()
            if before and re.fullmatch(r'[A-Za-z_$][\w$]*', before):
                out[before] = ('default', spec)
            for item in brace_m.group(1).split(','):
                item = item.strip()
                if not item or item.startswith('type '):
                    continue
                if ' as ' in item:
                    orig, local = [x.strip() for x in item.split(' as ', 1)]
                else:
                    orig = local = item
                if local:
                    out[local] = (orig, spec)
        elif clause.startswith('*'):
            ns_m = re.match(r'\*\s+as\s+([A-Za-z_$][\w$]*)', clause)
            if ns_m:
                out[ns_m.group(1)] = ('*', spec)
        elif re.fullmatch(r'[A-Za-z_$][\w$]*', clause):
            out[clause] = ('default', spec)
    if not _from_sfc and '<script' in txt.lower():
        sfc_scripts = _extract_sfc_script_text(txt)
        if sfc_scripts:
            for k, v in parse_imports(sfc_scripts, _from_sfc=True).items():
                out.setdefault(k, v)
    return out


def _is_jsx_opener(txt: str, i: int, tag_map: dict[int, re.Match]) -> bool:
    if txt.startswith('<>', i):
        return True
    m = tag_map.get(i)
    if m is None:
        return False
    close, tag, attrs, _ = m.groups()
    if close == '</':
        return False
    # Filter out TS generic parameter lists like <T,> or <T extends Foo>
    if re.match(r'^\s*(?:,|extends\b)', attrs):
        return False
    return True


def _skip_jsx_tag_or_fragment_safe(txt: str, i: int, tag_map: dict[int, re.Match], limit: int | None = None) -> int:
    """Skip `<Tag ...>...</Tag>`, `<Tag .../>`, or `<>...</>` without eating past `limit` on unclosed tags."""
    n = len(txt) if limit is None else min(len(txt), limit)
    if txt.startswith('<>', i):
        j = i + 2
        while j < n:
            if txt.startswith('</>', j):
                return j + 3
            if txt[j] == '{':
                j = min(n, _skip_balanced_braces(txt, j))
                continue
            if txt[j] == '<' and (j in tag_map or txt.startswith('<>', j)):
                j = _skip_jsx_tag_or_fragment_safe(txt, j, tag_map, n)
                continue
            j += 1
        return i + 2

    m = tag_map.get(i)
    if m is None:
        return i + 1
    close, tag, _, selfclose = m.groups()
    if close == '</' or selfclose or tag.lower() in VOID:
        return min(n, m.end())
    j = m.end()
    depth = 1
    while j < n and depth > 0:
        if txt[j] == '{':
            j = min(n, _skip_balanced_braces(txt, j))
            continue
        if txt[j] == '<' and j in tag_map:
            cm = tag_map[j]
            c_close, c_tag, _, c_self = cm.groups()
            if c_tag.lower() == tag.lower():
                if c_close == '</':
                    depth -= 1
                    j = cm.end()
                    continue
                if not c_self and not re.match(r'^\s*(?:,|extends\b)', cm.group(3)):
                    depth += 1
            j = cm.end()
            continue
        j += 1
    if depth > 0:
        return min(n, m.end())
    return j


def _unwrap_parens_span(txt: str, s: int, e: int) -> tuple[int, int]:
    while s < e:
        while s < e and txt[s].isspace():
            s += 1
        while e > s and txt[e - 1].isspace():
            e -= 1
        if s < e and txt[s] == '(' and txt[e - 1] == ')':
            end = _skip_balanced_parens(txt, s)
            if end == e:
                s += 1
                e -= 1
                continue
        break
    return s, e


def _find_js_stmt_end(txt: str, start: int, limit: int, tag_map: dict[int, re.Match]) -> int:
    i = start
    paren = brace = bracket = 0
    while i < limit:
        ch = txt[i]
        if ch in ('"', "'"):
            i = min(limit, _skip_quoted(txt, i, ch))
            continue
        if ch == '`':
            i = min(limit, _skip_template(txt, i))
            continue
        if ch == '/' and i + 1 < limit:
            if txt[i + 1] == '/':
                nl = txt.find('\n', i + 2)
                i = limit if nl == -1 else min(limit, nl + 1)
                continue
            if txt[i + 1] == '*':
                end_c = txt.find('*/', i + 2)
                i = limit if end_c == -1 else min(limit, end_c + 2)
                continue
        if ch == '<' and _is_jsx_opener(txt, i, tag_map):
            i = _skip_jsx_tag_or_fragment_safe(txt, i, tag_map, limit)
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


def _find_return_jsx_span(txt: str, b_start: int, b_end: int, tag_map: dict[int, re.Match]) -> tuple[int, int] | None:
    """Find the main JSX `return (...)` span at brace depth 0 inside `{ ... }` (`b_start..b_end`)."""
    i = b_start + 1
    limit = b_end - 1
    brace = paren = bracket = 0
    candidates: list[tuple[int, int]] = []
    while i < limit:
        ch = txt[i]
        if ch in ('"', "'"):
            i = min(limit, _skip_quoted(txt, i, ch))
            continue
        if ch == '`':
            i = min(limit, _skip_template(txt, i))
            continue
        if ch == '/' and i + 1 < limit:
            if txt[i + 1] == '/':
                nl = txt.find('\n', i + 2)
                i = limit if nl == -1 else min(limit, nl + 1)
                continue
            if txt[i + 1] == '*':
                end_c = txt.find('*/', i + 2)
                i = limit if end_c == -1 else min(limit, end_c + 2)
                continue
        if ch == '<' and _is_jsx_opener(txt, i, tag_map):
            i = _skip_jsx_tag_or_fragment_safe(txt, i, tag_map, limit)
            continue
        if ch == '{':
            brace += 1
        elif ch == '}':
            brace = max(0, brace - 1)
        elif ch == '(':
            paren += 1
        elif ch == ')':
            paren = max(0, paren - 1)
        elif ch == '[':
            bracket += 1
        elif ch == ']':
            bracket = max(0, bracket - 1)
        elif brace == 0 and paren == 0 and bracket == 0 and txt.startswith('return', i):
            prev_ok = i == 0 or not (txt[i - 1].isalnum() or txt[i - 1] in ('_', '$'))
            nxt = txt[i + 6:i + 7]
            if prev_ok and nxt and (nxt.isspace() or nxt in ('(', '<')):
                r_start = i + 6
                r_end = _find_js_stmt_end(txt, r_start, limit, tag_map)
                us, ue = _unwrap_parens_span(txt, r_start, r_end)
                if us < ue and txt[us] == '<' and _is_jsx_opener(txt, us, tag_map):
                    candidates.append((us, ue))
                i = r_end
                continue
        i += 1
    return candidates[-1] if candidates else None


def _skip_ws_and_comments(txt: str, i: int, limit: int) -> int:
    while i < limit:
        if txt[i].isspace():
            i += 1
            continue
        if txt.startswith('//', i):
            nl = txt.find('\n', i + 2)
            i = limit if nl == -1 else min(limit, nl + 1)
            continue
        if txt.startswith('/*', i):
            end_c = txt.find('*/', i + 2)
            i = limit if end_c == -1 else min(limit, end_c + 2)
            continue
        break
    return i


def _skip_ts_angles(txt: str, i: int, limit: int) -> int:
    """Skip `<...>` TypeScript generic parameters starting at `txt[i] == '<'`."""
    if i >= limit or txt[i] != '<':
        return i
    depth = 0
    while i < limit:
        ch = txt[i]
        if ch in ('"', "'"):
            i = min(limit, _skip_quoted(txt, i, ch))
            continue
        if ch == '`':
            i = min(limit, _skip_template(txt, i))
            continue
        if ch == '<':
            depth += 1
        elif ch == '>':
            if i > 0 and txt[i - 1] == '=':  # skip `=>`
                i += 1
                continue
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return limit


def _find_arrow_after_eq(txt: str, eq_pos: int, limit: int) -> tuple[int, int] | None:
    """From `=` in `const Comp = ... => ...`, return `(arrow_pos, wrap_end_min)` if it is a component arrow/fn."""
    i = _skip_ws_and_comments(txt, eq_pos + 1, limit)
    # Optional React.memo(...) / memo(...) / React.forwardRef(...) / forwardRef(...)
    m_wrap = re.match(r'(?:React\.)?(?:memo|forwardRef)\b', txt[i:limit])
    wrap_end = -1
    if m_wrap:
        j = _skip_ws_and_comments(txt, i + m_wrap.end(), limit)
        if j < limit and txt[j] == '<':
            j = _skip_ts_angles(txt, j, limit)
            j = _skip_ws_and_comments(txt, j, limit)
        if j < limit and txt[j] == '(':
            wrap_end = _skip_balanced_parens(txt, j)
            i = _skip_ws_and_comments(txt, j + 1, wrap_end)

    if txt.startswith('async', i) and (i + 5 >= limit or not (txt[i + 5].isalnum() or txt[i + 5] == '_')):
        i = _skip_ws_and_comments(txt, i + 5, limit)
    if i < limit and txt[i] == '<':
        i = _skip_ts_angles(txt, i, limit)
        i = _skip_ws_and_comments(txt, i, limit)

    # Parameter list `(...)` or single param `props`
    if i < limit and txt[i] == '(':
        i = _skip_balanced_parens(txt, i)
    else:
        m_id = re.match(r'[A-Za-z_$][\w$]*', txt[i:limit])
        if not m_id:
            return None
        i += m_id.end()

    # Scan optional `: ReturnType` up to `=>` (at brace/paren depth 0)
    paren = brace = bracket = angle = 0
    while i < limit:
        ch = txt[i]
        if ch in ('"', "'"):
            i = min(limit, _skip_quoted(txt, i, ch))
            continue
        if ch == '`':
            i = min(limit, _skip_template(txt, i))
            continue
        if ch == '/' and i + 1 < limit:
            if txt[i + 1] == '/':
                nl = txt.find('\n', i + 2)
                i = limit if nl == -1 else min(limit, nl + 1)
                continue
            if txt[i + 1] == '*':
                end_c = txt.find('*/', i + 2)
                i = limit if end_c == -1 else min(limit, end_c + 2)
                continue
        if txt.startswith('=>', i):
            if paren == 0 and brace == 0 and bracket == 0:
                return i, wrap_end
            i += 2
            continue
        if ch == '(':
            paren += 1
        elif ch == ')':
            if paren == 0:
                return None
            paren -= 1
        elif ch == '{':
            if paren == 0 and brace == 0 and bracket == 0 and angle == 0:
                # Hit `{` without `=>`: not an arrow function
                return None
            brace += 1
        elif ch == '}':
            brace = max(0, brace - 1)
        elif ch == '[':
            bracket += 1
        elif ch == ']':
            bracket = max(0, bracket - 1)
        elif ch == '<':
            angle += 1
        elif ch == '>':
            angle = max(0, angle - 1)
        elif ch == ';' and paren == 0 and brace == 0 and bracket == 0:
            return None
        i += 1
    return None


def _pascal_from_stem(stem: str) -> str:
    """Convert a file stem or kebab-case tag (`score-bars`, `+page`, `Card`) into PascalCase."""
    cleaned = stem.lstrip('+')
    parts = [p for p in re.split(r'[^A-Za-z0-9]+', cleaned) if p]
    if not parts:
        return 'Component'
    res = ''.join(p[:1].upper() + p[1:] for p in parts)
    return res if res[0].isalpha() else f'Comp{res}'


def _find_vue_template_bounds(txt: str) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int]] | None:
    """Return `((open_start, open_end), (inner_start, inner_end), (close_start, close_end))` for top-level `<template>`."""
    masked = mask_non_markup(txt)
    open_span: tuple[int, int] | None = None
    depth = 0
    for m in TAG.finditer(masked):
        close, tag, _, selfclose = m.groups()
        if tag.lower() != 'template':
            continue
        if open_span is None:
            if close != '</' and not selfclose:
                open_span = (m.start(), m.end())
                depth = 1
            continue
        if close == '</':
            depth -= 1
            if depth == 0:
                close_span = (m.start(), m.end())
                return open_span, (open_span[1], close_span[0]), close_span
        elif not selfclose:
            depth += 1
    if open_span is not None:
        return open_span, (open_span[1], len(txt)), (len(txt), len(txt))
    return None


def _find_svelte_markup_bounds(txt: str) -> tuple[tuple[int, int], list[tuple[int, int]]]:
    """Return `((markup_start, markup_end), non_markup_spans)` for a `.svelte` SFC outside `<script>` and `<style>`."""
    no_comments = re.sub(r'<!--.*?-->', lambda m: re.sub(r'[^\n]', ' ', m.group(0)), txt, flags=re.S)
    non_markup_spans = [
        (m.start(), m.end())
        for m in re.finditer(r'<(?:script|style)\b[^>]*>.*?</(?:script|style)>', no_comments, flags=re.S | re.I)
    ]
    buf = list(no_comments)
    for s, e in non_markup_spans:
        for k in range(s, e):
            if buf[k] != '\n':
                buf[k] = ' '
    only_markup = ''.join(buf)
    m_first = re.search(r'\S', only_markup)
    if not m_first:
        return (0, 0), non_markup_spans
    ms = m_first.start()
    me = len(only_markup.rstrip())
    return (ms, max(ms, me)), non_markup_spans


def extract_components(txt: str, file_path=None) -> dict[str, ComponentDef]:
    """Extract top-level PascalCase React components (or Vue/Svelte SFC default component) from `txt`."""
    suf = pathlib.Path(file_path).suffix.lower() if file_path else ''
    if suf == '.vue':
        comp_name = _pascal_from_stem(pathlib.Path(file_path).stem)
        bounds = _find_vue_template_bounds(txt)
        inner_s, inner_e = bounds[1] if bounds is not None else (0, 0)
        cdef = ComponentDef(
            name=comp_name,
            body_start=0,
            body_end=len(txt),
            jsx_start=inner_s,
            jsx_end=inner_e,
            is_exported=True,
            is_default=True,
        )
        return {comp_name: cdef, 'default': cdef}
    if suf == '.svelte':
        comp_name = _pascal_from_stem(pathlib.Path(file_path).stem)
        (ms, me), _ = _find_svelte_markup_bounds(txt)
        cdef = ComponentDef(
            name=comp_name,
            body_start=0,
            body_end=len(txt),
            jsx_start=ms,
            jsx_end=me,
            is_exported=True,
            is_default=True,
        )
        return {comp_name: cdef, 'default': cdef}

    masked = mask_non_markup(txt)
    tag_map = {m.start(): m for m in TAG.finditer(masked)}
    comps: dict[str, ComponentDef] = {}
    n = len(txt)

    def _register(cdef: ComponentDef):
        if cdef.name:
            comps[cdef.name] = cdef
        if cdef.is_default:
            comps['default'] = cdef

    i = 0
    brace = paren = bracket = 0
    while i < n:
        ch = txt[i]
        if ch in ('"', "'"):
            i = _skip_quoted(txt, i, ch)
            continue
        if ch == '`':
            i = _skip_template(txt, i)
            continue
        if ch == '/' and i + 1 < n:
            if txt[i + 1] == '/':
                nl = txt.find('\n', i + 2)
                i = n if nl == -1 else nl + 1
                continue
            if txt[i + 1] == '*':
                end_c = txt.find('*/', i + 2)
                i = n if end_c == -1 else end_c + 2
                continue
        if ch == '<' and _is_jsx_opener(txt, i, tag_map):
            i = _skip_jsx_tag_or_fragment_safe(txt, i, tag_map, n)
            continue

        if brace == 0 and paren == 0 and bracket == 0:
            # 1. [export [default]] [async] function Name(...) { ... }
            m_fn = re.match(
                r'(?:(export)\s+(?:(default)\s+)?)?(?:async\s+)?function\b',
                txt[i:],
            )
            if m_fn and (i == 0 or not (txt[i - 1].isalnum() or txt[i - 1] in ('_', '$'))):
                is_exp = bool(m_fn.group(1))
                is_def = bool(m_fn.group(2))
                k = _skip_ws_and_comments(txt, i + m_fn.end(), n)
                m_nm = re.match(r'[A-Z][\w$]*', txt[k:])
                name = m_nm.group(0) if m_nm else ('default' if is_def else '')
                if m_nm:
                    k = _skip_ws_and_comments(txt, k + m_nm.end(), n)
                if k < n and txt[k] == '<':
                    k = _skip_ts_angles(txt, k, n)
                    k = _skip_ws_and_comments(txt, k, n)
                if name and k < n and txt[k] == '(':
                    p_open = k
                    p_end = _skip_balanced_parens(txt, p_open)
                    # Find opening `{` after optional `: ReturnType`
                    j = p_end
                    p2 = b2 = k2 = 0
                    body_open = -1
                    while j < n:
                        c2 = txt[j]
                        if c2 in ('"', "'"):
                            j = _skip_quoted(txt, j, c2)
                            continue
                        if c2 == '`':
                            j = _skip_template(txt, j)
                            continue
                        if c2 == '{' and p2 == 0 and k2 == 0 and b2 == 0:
                            # Skip object return type `{ ... }`? No, function body `{` follows `)` or `: Type`
                            body_open = j
                            break
                        if c2 == '(':
                            p2 += 1
                        elif c2 == ')':
                            p2 = max(0, p2 - 1)
                        elif c2 == '[':
                            k2 += 1
                        elif c2 == ']':
                            k2 = max(0, k2 - 1)
                        elif c2 == ';' and p2 == 0 and k2 == 0:
                            break
                        j += 1
                    if body_open != -1:
                        body_end = _skip_balanced_braces(txt, body_open)
                        jsx_span = _find_return_jsx_span(txt, body_open, body_end, tag_map)
                        if jsx_span is not None:
                            _register(ComponentDef(
                                name=name,
                                body_start=i,
                                body_end=body_end,
                                jsx_start=jsx_span[0],
                                jsx_end=jsx_span[1],
                                is_exported=is_exp,
                                is_default=is_def,
                            ))
                        i = body_end
                        continue

            # 2. [export] const|let|var Name[: Type] = ... => ...
            m_var = re.match(
                r'(?:(export)\s+)?(?:const|let|var)\s+([A-Z][\w$]*)\b',
                txt[i:],
            )
            if m_var and (i == 0 or not (txt[i - 1].isalnum() or txt[i - 1] in ('_', '$'))):
                is_exp = bool(m_var.group(1))
                name = m_var.group(2)
                # Find top-level `=` before `;`
                j = i + m_var.end()
                p2 = b2 = k2 = a2 = 0
                eq_pos = -1
                while j < n:
                    c2 = txt[j]
                    if c2 in ('"', "'"):
                        j = _skip_quoted(txt, j, c2)
                        continue
                    if c2 == '`':
                        j = _skip_template(txt, j)
                        continue
                    if c2 == '=' and not txt.startswith('=>', j) and not txt.startswith('==', j) and p2 == 0 and b2 == 0 and k2 == 0 and a2 == 0:
                        eq_pos = j
                        break
                    if txt.startswith('=>', j):
                        j += 2
                        continue
                    if c2 == '(':
                        p2 += 1
                    elif c2 == ')':
                        p2 = max(0, p2 - 1)
                    elif c2 == '{':
                        b2 += 1
                    elif c2 == '}':
                        b2 = max(0, b2 - 1)
                    elif c2 == '[':
                        k2 += 1
                    elif c2 == ']':
                        k2 = max(0, k2 - 1)
                    elif c2 == '<':
                        a2 += 1
                    elif c2 == '>':
                        a2 = max(0, a2 - 1)
                    elif c2 == ';' and p2 == 0 and b2 == 0 and k2 == 0:
                        break
                    j += 1
                if eq_pos != -1:
                    arrow_info = _find_arrow_after_eq(txt, eq_pos, n)
                    if arrow_info is not None:
                        arrow_pos, wrap_end = arrow_info
                        rhs = _skip_ws_and_comments(txt, arrow_pos + 2, n)
                        jsx_span = None
                        stmt_end = rhs
                        if rhs < n and txt[rhs] == '{':
                            stmt_end = _skip_balanced_braces(txt, rhs)
                            jsx_span = _find_return_jsx_span(txt, rhs, stmt_end, tag_map)
                        elif rhs < n and txt[rhs] == '(':
                            stmt_end = _skip_balanced_parens(txt, rhs)
                            us, ue = _unwrap_parens_span(txt, rhs, stmt_end)
                            if us < ue and txt[us] == '<' and _is_jsx_opener(txt, us, tag_map):
                                jsx_span = (us, ue)
                        elif rhs < n and txt[rhs] == '<' and _is_jsx_opener(txt, rhs, tag_map):
                            stmt_end = _skip_jsx_tag_or_fragment_safe(txt, rhs, tag_map, n)
                            jsx_span = (rhs, stmt_end)
                        final_end = max(stmt_end, wrap_end) if wrap_end != -1 else stmt_end
                        if jsx_span is not None:
                            _register(ComponentDef(
                                name=name,
                                body_start=i,
                                body_end=final_end,
                                jsx_start=jsx_span[0],
                                jsx_end=jsx_span[1],
                                is_exported=is_exp,
                                is_default=False,
                            ))
                        i = final_end
                        continue

            # 3. `export default Name;` (with or without trailing semicolon)
            m_def_ref = re.match(r'export\s+default\s+([A-Z][\w$]*)\s*(?:;|(?=\r?\n|$))', txt[i:])
            if m_def_ref and (i == 0 or not (txt[i - 1].isalnum() or txt[i - 1] in ('_', '$'))):
                ref_name = m_def_ref.group(1)
                if ref_name in comps:
                    comps['default'] = comps[ref_name]
                i += m_def_ref.end()
                continue

        if ch == '{':
            brace += 1
        elif ch == '}':
            brace = max(0, brace - 1)
        elif ch == '(':
            paren += 1
        elif ch == ')':
            paren = max(0, paren - 1)
        elif ch == '[':
            bracket += 1
        elif ch == ']':
            bracket = max(0, bracket - 1)
        i += 1
    if not comps and '<template' in txt.lower():
        bounds = _find_vue_template_bounds(txt)
        if bounds is not None:
            cdef = ComponentDef(
                name='VueComponent',
                body_start=0,
                body_end=len(txt),
                jsx_start=bounds[1][0],
                jsx_end=bounds[1][1],
                is_exported=True,
                is_default=True,
            )
            comps['VueComponent'] = cdef
            comps['default'] = cdef
    return comps


# ---------------- component inlining & route composition ----------------

@dataclass
class _FileContext:
    file_path: pathlib.Path | None
    txt: str
    masked: str
    line_starts: list[int]
    tag_map: dict[int, re.Match]
    components: dict[str, ComponentDef]
    imports: dict[str, tuple[str, str]]
    cva_registry: CvaRegistry
    route_mode: bool
    root_dir: pathlib.Path | None
    tsconfig_paths: tuple | None
    sfc_ext: str = ''
    root_masked_spans: list[tuple[int, int]] = field(default_factory=list)
    sfc_non_markup_spans: list[tuple[int, int]] = field(default_factory=list)
    extra_active_lines: set[int] = field(default_factory=set)
    masked_jsx_spans: list[tuple[int, int]] = field(default_factory=list)
    resolved_cache: dict[str, '_FileContext | None'] = field(default_factory=dict)


@dataclass
class _CompositionState:
    cva_registry: CvaRegistry
    inlined_files: list[str] = field(default_factory=list)
    inlined_files_set: set[str] = field(default_factory=set)
    inlined_count: int = 0
    file_ctx_cache: dict[str, _FileContext] = field(default_factory=dict)
    max_depth: int = 4


def _build_file_context(
    txt: str,
    file_path,
    *,
    route_mode: bool,
    root_dir,
    tsconfig_paths,
    state: _CompositionState,
) -> _FileContext:
    p_obj = pathlib.Path(file_path) if file_path else None
    key = str(p_obj.resolve()) if p_obj else None
    if key and key in state.file_ctx_cache:
        return state.file_ctx_cache[key]
    suf = p_obj.suffix.lower() if p_obj else ''
    masked = mask_non_markup(txt)
    tag_map = {m.start(): m for m in TAG.finditer(masked)}
    components = extract_components(txt, file_path=p_obj)
    if suf in _SFC_EXTS:
        imports = parse_imports(_extract_sfc_script_text(txt), _from_sfc=True)
    else:
        imports = parse_imports(txt)
    root_masked_spans: list[tuple[int, int]] = []
    sfc_non_markup_spans: list[tuple[int, int]] = []
    if suf == '.vue':
        v_bounds = _find_vue_template_bounds(txt)
        if v_bounds is not None:
            root_masked_spans = [v_bounds[0], v_bounds[2]]
    elif suf == '.svelte':
        _, sfc_non_markup_spans = _find_svelte_markup_bounds(txt)

    if route_mode and file_path:
        cva_reg = discover_cva_definitions(file_path, txt)
    else:
        cva_reg = parse_cva_definitions(txt, source_path=file_path) if 'cva' in txt else CvaRegistry()
    state.cva_registry.merge_from(cva_reg)
    ctx = _FileContext(
        file_path=p_obj,
        txt=txt,
        masked=masked,
        line_starts=_compute_line_starts(txt),
        tag_map=tag_map,
        components=components,
        imports=imports,
        cva_registry=cva_reg,
        route_mode=route_mode,
        root_dir=root_dir,
        tsconfig_paths=tsconfig_paths,
        sfc_ext=suf if suf in _SFC_EXTS else '',
        root_masked_spans=root_masked_spans,
        sfc_non_markup_spans=sfc_non_markup_spans,
    )
    if key:
        state.file_ctx_cache[key] = ctx
    return ctx


def _extract_caller_classname_expr(attrs: str) -> tuple[str, bool] | None:
    """Extract caller's `className` / `class` value as `(val, is_js_expr)` or None."""
    m = re.search(r'(?<![:\w-])class(?:Name)?\s*=\s*', attrs)
    if not m:
        return None
    i = m.end()
    n = len(attrs)
    if i >= n:
        return None
    ch = attrs[i]
    if ch in ('"', "'"):
        end = _skip_quoted(attrs, i, ch)
        return attrs[i + 1:max(i + 1, end - 1)], False
    if ch == '{':
        end = _skip_balanced_braces(attrs, i)
        inner = attrs[i + 1:max(i + 1, end - 1)] if end > i + 1 and attrs[end - 1] == '}' else attrs[i + 1:end]
        return inner.strip(), True
    return None


def _attrs_has_own_bg(attrs: str) -> bool:
    if re.search(r'(?<![\w-])style\s*=\s*["\'][^"\']*background', attrs, re.I):
        return True
    if re.search(r'(?<![\w-])bg-(?!clip-text\b|transparent\b|inherit\b|current\b)', attrs):
        return True
    return False


def _inject_classname_into_root_tag(tag_text: str, caller_cls: tuple[str, bool], *, sfc_ext: str = '') -> str:
    """Substitute standalone `className` / `props.className` (or Vue fallthrough `class`) inside a component's root tag."""
    val, is_expr = caller_cls
    if not val:
        return tag_text
    replacement = f'({val})' if is_expr else json.dumps(val)
    if sfc_ext == '.vue' and not is_expr:
        m_cls = re.search(r'(?<![:\w-])class\s*=\s*"([^"]*)"', tag_text)
        if m_cls:
            merged = f'{m_cls.group(1)} {val}'.strip()
            return tag_text[:m_cls.start()] + f'class={json.dumps(merged)}' + tag_text[m_cls.end():]
        if not re.search(r'(?<![:\w-])class\s*=', tag_text):
            if tag_text.endswith('/>'):
                return tag_text[:-2] + f' class={replacement}/>'
            return tag_text[:-1] + f' class={replacement}>'
    if re.search(r'(?<![:\w-])class(?:Name)?\s*=', tag_text):
        return re.sub(
            r'\b(?:props\.)?className\b(?!\s*=)',
            lambda _m: replacement,
            tag_text,
        )
    if '{...props}' in tag_text or '{...rest}' in tag_text or '{...$$restProps}' in tag_text:
        if tag_text.endswith('/>'):
            return tag_text[:-2] + f' className={replacement}/>'
        return tag_text[:-1] + f' className={replacement}>'
    return tag_text


def _find_children_placeholders(
    src: str,
    start: int,
    end: int,
    *,
    sfc_mode: bool = False,
    has_caller_children: bool = False,
) -> list[tuple[int, int]]:
    """Find `{children}`, `{props.children}`, Svelte `{@render children?.()}`, and Vue/Svelte `<slot>` spans."""
    spans = []
    i = start
    in_tag = False
    while i < end:
        ch = src[i]
        if in_tag:
            if ch in ('"', "'"):
                i = min(end, _skip_quoted(src, i, ch))
                continue
            if ch == '{':
                i = min(end, _skip_balanced_braces(src, i))
                continue
            if ch == '>':
                in_tag = False
            i += 1
            continue
        if ch == '<':
            if sfc_mode and src[i:i + 5].lower() == '<slot' and (i + 5 < end and (src[i + 5].isspace() or src[i + 5] in ('/', '>'))):
                m_slot = TAG.match(src, i, end)
                if m_slot and m_slot.group(1) != '</' and m_slot.group(2).lower() == 'slot':
                    slot_attrs = m_slot.group(3)
                    slot_self = bool(m_slot.group(4))
                    m_nm = re.search(r'\bname\s*=\s*["\']([^"\']+)["\']', slot_attrs)
                    slot_name = m_nm.group(1) if m_nm else 'default'
                    if slot_name == 'default':
                        if slot_self:
                            spans.append((i, m_slot.end()))
                            i = m_slot.end()
                            continue
                        m_close = re.search(r'</slot\s*>', src[m_slot.end():end], re.I)
                        if m_close and has_caller_children:
                            slot_end = m_slot.end() + m_close.end()
                            spans.append((i, slot_end))
                            i = slot_end
                            continue
            in_tag = True
            i += 1
            continue
        if ch == '{':
            b_end = min(end, _skip_balanced_braces(src, i))
            inner = src[i + 1:max(i + 1, b_end - 1)].strip()
            if inner in ('children', 'props.children') or re.fullmatch(r'@render\s+children(?:\?\.)?\(\s*\)', inner):
                spans.append((i, b_end))
            i = b_end
            continue
        i += 1
    return spans


def _resolve_imported_target(
    ctx: _FileContext,
    imp_spec: str,
    state: _CompositionState,
) -> _FileContext | None:
    if imp_spec in ctx.resolved_cache:
        return ctx.resolved_cache[imp_spec]
    resolved_path = resolve_import(
        imp_spec,
        ctx.file_path or '.',
        root_dir=ctx.root_dir,
        tsconfig_paths=ctx.tsconfig_paths,
    )
    if resolved_path is None or not resolved_path.is_file():
        ctx.resolved_cache[imp_spec] = None
        return None
    try:
        target_txt = resolved_path.read_text(encoding='utf-8', errors='ignore')
    except OSError:
        ctx.resolved_cache[imp_spec] = None
        return None
    target_ctx = _build_file_context(
        target_txt,
        resolved_path,
        route_mode=True,
        root_dir=ctx.root_dir,
        tsconfig_paths=ctx.tsconfig_paths,
        state=state,
    )
    ctx.resolved_cache[imp_spec] = target_ctx
    return target_ctx


def _lookup_imported_component(target_ctx: _FileContext, imp_name: str, local_tag: str) -> ComponentDef | None:
    if imp_name in target_ctx.components:
        return target_ctx.components[imp_name]
    if imp_name == 'default':
        if 'default' in target_ctx.components:
            return target_ctx.components['default']
        if local_tag in target_ctx.components:
            return target_ctx.components[local_tag]
        exported = [c for c in target_ctx.components.values() if c.is_exported]
        if len(exported) == 1:
            return exported[0]
        if len(target_ctx.components) == 1:
            return next(iter(target_ctx.components.values()))
    return None


def _expand_span_segments(
    ctx: _FileContext,
    start: int,
    end: int,
    *,
    depth: int,
    stack: frozenset[tuple[str, str]],
    state: _CompositionState,
    children_segments: list[tuple[str, list[int] | None, int]] | None = None,
    caller_cls: tuple[str, bool] | None = None,
    skip_masked_local: bool = False,
) -> list[tuple[str, list[int] | None, int]]:
    """Expand `ctx.txt[start:end]` into virtual segments `(text, line_starts_or_None, orig_start)`."""
    segments: list[tuple[str, list[int] | None, int]] = []
    src = ctx.txt
    ls = ctx.line_starts
    tag_map = ctx.tag_map
    file_id = str(ctx.file_path.resolve()) if ctx.file_path else '<mem>'

    # Collect local spans to mask (in root pass) and children placeholders (when expanding component body)
    raw_masked = (list(ctx.masked_jsx_spans) if skip_masked_local else []) + (
        list(ctx.sfc_non_markup_spans) if not skip_masked_local else []
    )
    masked_spans = sorted(raw_masked)
    masked_idx = 0
    has_caller_children = bool(children_segments and any(seg[0].strip() for seg in children_segments))
    child_ph = (
        _find_children_placeholders(
            src,
            start,
            end,
            sfc_mode=bool(ctx.sfc_ext),
            has_caller_children=has_caller_children,
        )
        if children_segments is not None
        else []
    )
    ph_idx = 0

    first_root_tag_handled = caller_cls is None

    def _emit_slice(s_idx: int, e_idx: int):
        nonlocal first_root_tag_handled
        if e_idx <= s_idx:
            return
        if not first_root_tag_handled and s_idx in tag_map:
            m0 = tag_map[s_idx]
            if m0.end() <= e_idx and m0.group(1) != '</':
                first_root_tag_handled = True
                mod_tag = _inject_classname_into_root_tag(src[s_idx:m0.end()], caller_cls, sfc_ext=ctx.sfc_ext)
                line_no = max(1, bisect.bisect_right(ls, s_idx))
                ctx.extra_active_lines.add(line_no)
                segments.append((mod_tag, None, line_no))
                if m0.end() < e_idx:
                    segments.append((src[m0.end():e_idx], ls, m0.end()))
                return
        segments.append((src[s_idx:e_idx], ls, s_idx))

    i = start
    while i < end:
        # 1. Masked local component JSX definition in root file (or SFC non-markup spans)
        while masked_idx < len(masked_spans) and masked_spans[masked_idx][1] <= i:
            masked_idx += 1
        if masked_idx < len(masked_spans):
            ms, me = masked_spans[masked_idx]
            if ms <= i < me:
                stop = min(end, me)
                masked_txt = re.sub(r'[^\n]', ' ', src[i:stop])
                segments.append((masked_txt, ls, i))
                i = stop
                continue

        # 2. `{children}` / `{props.children}` / `<slot>` placeholder
        while ph_idx < len(child_ph) and child_ph[ph_idx][1] <= i:
            ph_idx += 1
        if ph_idx < len(child_ph) and child_ph[ph_idx][0] == i:
            if children_segments:
                segments.extend(children_segments)
            i = child_ph[ph_idx][1]
            ph_idx += 1
            continue

        # 3. JSX / SFC Tag
        if i in tag_map:
            m = tag_map[i]
            close, tag, attrs, selfclose = m.groups()
            kebab_lookup = _pascal_from_stem(tag) if (ctx.sfc_ext == '.vue' and '-' in tag) else ''
            is_comp_tag = tag[0].isupper() or (bool(kebab_lookup) and kebab_lookup in ctx.imports)
            if close != '</' and is_comp_tag and m.end() <= end:
                lookup_tag = kebab_lookup if (not tag[0].isupper() and kebab_lookup) else tag
                root_tag_name = lookup_tag.split('.', 1)[0]
                is_cva = (lookup_tag in state.cva_registry) or (lookup_tag in ctx.cva_registry)

                target_comp: ComponentDef | None = None
                target_ctx: _FileContext | None = None
                unresolved_import = False

                if not is_cva:
                    if lookup_tag in ctx.components and not ctx.sfc_ext:
                        target_comp = ctx.components[lookup_tag]
                        target_ctx = ctx
                    elif lookup_tag in ctx.imports:
                        imp_name, imp_spec = ctx.imports[lookup_tag]
                        allow_cross_file = (
                            ctx.route_mode
                            or bool(ctx.sfc_ext)
                            or imp_spec.lower().endswith(('.vue', '.svelte'))
                        )
                        if allow_cross_file:
                            resolved_ctx = _resolve_imported_target(ctx, imp_spec, state)
                            if resolved_ctx is None:
                                unresolved_import = True
                            else:
                                c_def = _lookup_imported_component(resolved_ctx, imp_name, lookup_tag)
                                if c_def is not None and c_def.name not in state.cva_registry:
                                    target_comp = c_def
                                    target_ctx = resolved_ctx
                        else:
                            # File mode: mark unresolved external packages (when resolve_import fails)
                            if resolve_import(
                                imp_spec,
                                ctx.file_path or '.',
                                root_dir=ctx.root_dir,
                                tsconfig_paths=ctx.tsconfig_paths,
                            ) is None:
                                unresolved_import = True
                    elif root_tag_name in ctx.imports and '.' in lookup_tag:
                        _, imp_spec = ctx.imports[root_tag_name]
                        if resolve_import(
                            imp_spec,
                            ctx.file_path or '.',
                            root_dir=ctx.root_dir,
                            tsconfig_paths=ctx.tsconfig_paths,
                        ) is None:
                            unresolved_import = True

                if target_comp is not None and target_ctx is not None:
                    t_file_id = str(target_ctx.file_path.resolve()) if target_ctx.file_path else file_id
                    comp_key = (t_file_id, target_comp.name)
                    if depth < state.max_depth and comp_key not in stack:
                        if selfclose:
                            el_end = m.end()
                            expanded_kids: list[tuple[str, list[int] | None, int]] = []
                        else:
                            el_end = min(end, _skip_jsx_tag_or_fragment_safe(ctx.masked, i, tag_map, end))
                            close_tag_len = len(f'</{tag}>')
                            close_start = el_end - close_tag_len if src[el_end - close_tag_len:el_end].lower() == f'</{tag}>'.lower() else el_end
                            if close_start > m.end():
                                expanded_kids = _expand_span_segments(
                                    ctx,
                                    m.end(),
                                    close_start,
                                    depth=depth,
                                    stack=stack,
                                    state=state,
                                    children_segments=children_segments,
                                    skip_masked_local=False,
                                )
                            else:
                                expanded_kids = []

                        caller_class = _extract_caller_classname_expr(attrs)
                        expanded_comp = _expand_span_segments(
                            target_ctx,
                            target_comp.jsx_start,
                            target_comp.jsx_end,
                            depth=depth + 1,
                            stack=stack | {comp_key},
                            state=state,
                            children_segments=expanded_kids,
                            caller_cls=caller_class,
                            skip_masked_local=False,
                        )
                        first_root_tag_handled = True
                        if (
                            _THEME_TOGGLE_HINT_RE.search(lookup_tag)
                            or _THEME_TOGGLE_HINT_RE.search(target_comp.name)
                            or _THEME_TOGGLE_HINT_RE.search(target_ctx.txt)
                        ):
                            joined_comp = ''.join(seg[0] for seg in expanded_comp)
                            if not _THEME_TOGGLE_HINT_RE.search(joined_comp):
                                segments.append(('<!-- ThemeToggle -->', None, max(1, bisect.bisect_right(ls, i))))
                        segments.extend(expanded_comp)
                        state.inlined_count += 1
                        if target_ctx.file_path and t_file_id != file_id and t_file_id not in state.inlined_files_set:
                            state.inlined_files_set.add(t_file_id)
                            state.inlined_files.append(str(target_ctx.file_path))
                        i = el_end
                        continue

                if (
                    unresolved_import
                    and not selfclose
                    and lookup_tag not in _TRANSPARENT_FRAMEWORK_TAGS
                    and root_tag_name not in _TRANSPARENT_FRAMEWORK_TAGS
                    and not _attrs_has_own_bg(attrs)
                    and 'data-uitools-unknown-bg' not in attrs
                ):
                    el_end = min(end, _skip_jsx_tag_or_fragment_safe(ctx.masked, i, tag_map, end))
                    if el_end > m.end():
                        orig_tag = src[i:m.end()]
                        if caller_cls is not None and not first_root_tag_handled:
                            first_root_tag_handled = True
                            orig_tag = _inject_classname_into_root_tag(orig_tag, caller_cls, sfc_ext=ctx.sfc_ext)
                        line_no = max(1, bisect.bisect_right(ls, i))
                        ctx.extra_active_lines.add(line_no)
                        segments.append((orig_tag[:-1] + ' data-uitools-unknown-bg="true">', None, line_no))
                        i = m.end()
                        continue

            _emit_slice(i, min(end, m.end()))
            i = min(end, m.end())
            continue

        # Advance to next interesting position
        next_stop = end
        if masked_idx < len(masked_spans) and masked_spans[masked_idx][0] > i:
            next_stop = min(next_stop, masked_spans[masked_idx][0])
        if ph_idx < len(child_ph) and child_ph[ph_idx][0] > i:
            next_stop = min(next_stop, child_ph[ph_idx][0])
        # Find next tag start in `i+1 .. next_stop`
        next_lt = src.find('<', i + 1, next_stop)
        if next_lt != -1:
            next_stop = min(next_stop, next_lt)
        if child_ph and ph_idx < len(child_ph):
            next_brace = src.find('{', i + 1, next_stop)
            if next_brace != -1:
                next_stop = min(next_stop, next_brace)
        _emit_slice(i, next_stop)
        i = next_stop

    return segments


def _collect_used_local_components(ctx: _FileContext, state: _CompositionState) -> list[tuple[int, int]]:
    """Return JSX spans `(jsx_start, jsx_end)` of local components referenced outside their own bodies."""
    if not ctx.components or ctx.sfc_ext:
        return []
    used_spans: list[tuple[int, int]] = []
    seen_spans: set[tuple[int, int]] = set()
    for name, cdef in ctx.components.items():
        if name == 'default':
            continue
        if name in state.cva_registry or name in ctx.cva_registry:
            continue
        # Check if `<Name` appears in `ctx.tag_map` outside `[cdef.body_start, cdef.body_end)`
        called_externally = any(
            m.group(1) != '</'
            and m.group(2) == name
            and not (cdef.body_start <= pos < cdef.body_end)
            for pos, m in ctx.tag_map.items()
        )
        if called_externally:
            span = (cdef.jsx_start, cdef.jsx_end)
            if span not in seen_spans:
                seen_spans.add(span)
                used_spans.append(span)
    return used_spans


def _discover_app_router_layouts(
    source_path,
    eff_root: pathlib.Path,
    *,
    explicit_root: bool = False,
) -> list[pathlib.Path]:
    """Discover Next.js App Router `layout.{tsx,ts,jsx,js}` files from outermost (`app/layout.tsx`) to innermost."""
    if not source_path:
        return []
    p = pathlib.Path(source_path)
    if p.name.lower() not in _PAGE_FILENAMES:
        return []
    try:
        p_res = p.resolve()
    except OSError:
        p_res = p.absolute()
    try:
        r_res = eff_root.resolve()
    except OSError:
        r_res = eff_root.absolute()

    chain: list[pathlib.Path] = []
    cur = p_res.parent
    reached_root = False
    while True:
        chain.append(cur)
        if cur == r_res:
            reached_root = True
            break
        if cur.parent == cur:
            break
        cur = cur.parent

    if not reached_root:
        return []

    if not explicit_root and not any(d.name.lower() == 'app' for d in chain):
        extra_cur = r_res.parent
        extra: list[pathlib.Path] = []
        for _ in range(4):
            if extra_cur == extra_cur.parent:
                break
            extra.append(extra_cur)
            if extra_cur.name.lower() == 'app':
                chain.extend(extra)
                break
            extra_cur = extra_cur.parent

    dirs = list(reversed(chain))
    app_idx = next((idx for idx, d in enumerate(dirs) if d.name.lower() == 'app'), None)
    if app_idx is None:
        return []

    layouts: list[pathlib.Path] = []
    for d in dirs[app_idx:]:
        for lname in _LAYOUT_FILENAMES:
            cand = d / lname
            try:
                if cand.is_file():
                    layouts.append(cand.resolve())
                    break
            except OSError:
                continue
    return layouts


def _mask_tags_in_non_jsx_slice(src: str, masked: str, start: int, end: int) -> str:
    """Return `src[start:end]` with any `<Tag>` spans replaced by spaces so `walk()` sees zero tags."""
    if end <= start:
        return ''
    buf = list(src[start:end])
    for m in TAG.finditer(masked, start, end):
        ms = max(start, m.start()) - start
        me = min(end, m.end()) - start
        for k in range(ms, me):
            if buf[k] != '\n':
                buf[k] = ' '
    return ''.join(buf)


def _build_route_source_text(
    txt: str,
    source_path,
    root_ctx: _FileContext,
    builder: _VirtualBuilder,
    state: _CompositionState,
) -> str:
    """Wrap `txt` in `RouteSourceText` carrying `.source_files` and `.active_lines` when external files were inlined."""
    if not state.inlined_files:
        return txt

    entry_key = str(source_path) if source_path else '<entry>'
    source_files: dict[str, str] = {entry_key: txt}
    active_lines: dict[str, set[int]] = {entry_key: set(root_ctx.extra_active_lines)}
    ls_to_sf_key: dict[int, str] = {id(root_ctx.line_starts): entry_key}

    for fp_str in state.inlined_files:
        try:
            res_key = str(pathlib.Path(fp_str).resolve())
        except OSError:
            res_key = fp_str
        f_ctx = state.file_ctx_cache.get(res_key)
        if f_ctx is not None:
            source_files[fp_str] = f_ctx.txt
            active_lines[fp_str] = set(f_ctx.extra_active_lines)
            ls_to_sf_key[id(f_ctx.line_starts)] = fp_str
        else:
            try:
                source_files[fp_str] = pathlib.Path(fp_str).read_text(encoding='utf-8', errors='ignore')
            except OSError:
                continue
            active_lines[fp_str] = set()

    for chunk_txt, (ls, orig_start) in zip(builder.chunks, builder.seg_meta):
        if ls is None or not chunk_txt.strip():
            continue
        sf_key = ls_to_sf_key.get(id(ls))
        if sf_key is None:
            continue
        l_start = max(1, bisect.bisect_right(ls, orig_start))
        l_end = max(1, bisect.bisect_right(ls, orig_start + len(chunk_txt) - 1))
        active_lines[sf_key].update(range(l_start, l_end + 1))

    return RouteSourceText(
        txt,
        entry_file=entry_key,
        source_files=source_files,
        active_lines=active_lines,
    )


def _run_composition(
    txt: str,
    source_path=None,
    *,
    route_mode: bool = False,
    root_dir=None,
    tsconfig_path=None,
    max_depth: int = 4,
) -> VirtualMarkup:
    if isinstance(txt, VirtualMarkup):
        return txt

    eff_root = pathlib.Path(root_dir).resolve() if root_dir else (
        find_project_root(source_path) if source_path else pathlib.Path.cwd()
    )
    tsconfig_paths = load_tsconfig_paths(tsconfig_path=tsconfig_path, root_dir=eff_root)

    state = _CompositionState(cva_registry=CvaRegistry(), max_depth=max_depth)
    root_ctx = _build_file_context(
        txt,
        source_path,
        route_mode=route_mode,
        root_dir=eff_root,
        tsconfig_paths=tsconfig_paths,
        state=state,
    )
    root_ctx.masked_jsx_spans = sorted(
        _collect_used_local_components(root_ctx, state) + list(root_ctx.root_masked_spans)
    )

    layouts = (
        _discover_app_router_layouts(source_path, eff_root, explicit_root=bool(root_dir))
        if route_mode and source_path
        else []
    )

    if layouts:
        root_file_id = str(root_ctx.file_path.resolve()) if root_ctx.file_path else '<entry>'
        page_comp = _lookup_imported_component(root_ctx, 'default', 'Page')
        page_pre: list[tuple[str, list[int] | None, int]] = []
        page_post: list[tuple[str, list[int] | None, int]] = []
        if page_comp is not None:
            cur_segments = _expand_span_segments(
                root_ctx,
                page_comp.jsx_start,
                page_comp.jsx_end,
                depth=0,
                stack=frozenset({(root_file_id, page_comp.name)}),
                state=state,
                skip_masked_local=False,
            )
            pre_txt = _mask_tags_in_non_jsx_slice(txt, root_ctx.masked, 0, page_comp.jsx_start)
            post_txt = _mask_tags_in_non_jsx_slice(txt, root_ctx.masked, page_comp.jsx_end, len(txt))
            if pre_txt.strip():
                page_pre.append((pre_txt, None, 1))
            if post_txt.strip():
                page_post.append((post_txt, None, 1))
        else:
            cur_segments = _expand_span_segments(
                root_ctx,
                0,
                len(txt),
                depth=0,
                stack=frozenset(),
                state=state,
                skip_masked_local=True,
            )

        for layout_path in reversed(layouts):
            try:
                layout_txt = layout_path.read_text(encoding='utf-8', errors='ignore')
            except OSError:
                continue
            layout_ctx = _build_file_context(
                layout_txt,
                layout_path,
                route_mode=True,
                root_dir=eff_root,
                tsconfig_paths=tsconfig_paths,
                state=state,
            )
            layout_ctx.masked_jsx_spans = _collect_used_local_components(layout_ctx, state)
            layout_comp = _lookup_imported_component(layout_ctx, 'default', 'Layout')
            if layout_comp is None:
                continue
            layout_id = str(layout_path.resolve())
            if layout_id not in state.inlined_files_set:
                state.inlined_files_set.add(layout_id)
                state.inlined_files.append(str(layout_path))
            state.inlined_count += 1

            wrapped_segments = _expand_span_segments(
                layout_ctx,
                layout_comp.jsx_start,
                layout_comp.jsx_end,
                depth=0,
                stack=frozenset({(layout_id, layout_comp.name)}),
                state=state,
                children_segments=cur_segments,
                skip_masked_local=False,
            )
            layout_prefix: list[tuple[str, list[int] | None, int]] = []
            for m_font in re.finditer(r'import\s*\{[^}]+\}\s*from\s*["\']next/font/google["\']', layout_txt):
                layout_prefix.append((m_font.group(0) + '\n', None, 1))
            if _THEME_TOGGLE_HINT_RE.search(layout_txt):
                joined_layout = ''.join(seg[0] for seg in wrapped_segments)
                if not _THEME_TOGGLE_HINT_RE.search(joined_layout):
                    layout_prefix.append(('<!-- ThemeToggle -->', None, 1))
            cur_segments = layout_prefix + wrapped_segments

        segments = page_pre + cur_segments + page_post
    else:
        segments = _expand_span_segments(
            root_ctx,
            0,
            len(txt),
            depth=0,
            stack=frozenset(),
            state=state,
            skip_masked_local=True,
        )

    builder = _VirtualBuilder()
    builder.append_segments(segments)
    raw_out = _build_route_source_text(txt, source_path, root_ctx, builder, state)
    return builder.build(
        cva_registry=state.cva_registry,
        inlined_files=state.inlined_files,
        inlined_count=state.inlined_count,
        raw_txt=raw_out,
    )


def inline_local_components(
    txt: str,
    source_path=None,
    *,
    root_dir=None,
    tsconfig_path=None,
    max_depth: int = 4,
) -> VirtualMarkup:
    """Inline same-file React components and mark unresolved external wrappers in `txt`."""
    return _run_composition(
        txt,
        source_path=source_path,
        route_mode=False,
        root_dir=root_dir,
        tsconfig_path=tsconfig_path,
        max_depth=max_depth,
    )


def compose_route(
    entry_path,
    txt: str | None = None,
    *,
    root_dir=None,
    tsconfig_path=None,
    max_depth: int = 4,
) -> VirtualMarkup:
    """Resolve cross-file imports and inline components from a route entry into a `VirtualMarkup`."""
    p = pathlib.Path(entry_path)
    if txt is None:
        txt = p.read_text(encoding='utf-8', errors='ignore')
    return _run_composition(
        txt,
        source_path=p,
        route_mode=True,
        root_dir=root_dir,
        tsconfig_path=tsconfig_path,
        max_depth=max_depth,
    )
