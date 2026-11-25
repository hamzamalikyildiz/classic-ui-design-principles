#!/usr/bin/env python3
"""Reasoned suppression (`uitools-ignore`) parser and matcher for uitools."""
import hashlib
import json
import os
import pathlib
import re

KNOWN_RULES = frozenset({
    'bold-font-default',
    'bold-headline-size',
    'border-heavy',
    'branch-explosion',
    'card-sameness',
    'edge-align',
    'editorial-leading',
    'fitts-primary',
    'flat-hierarchy',
    'frame-wrapper',
    'grey-chart',
    'grid',
    'hardcoded-locale-format',
    'heading-wrap',
    'headline-measure',
    'landmark-main',
    'left-stacked-column',
    'line-length',
    'low-color',
    'max-2-fonts',
    'miller-7',
    'nested-radius',
    'no-drawn-mascot',
    'no-hero-surface',
    'no-mono',
    'no-serif',
    'numeric-columns',
    'radius-too-soft',
    'reveal-needs-js',
    'shadcn-defaults',
    'shadow-heavy',
    'single-primary-cta',
    'skeleton-empty',
    'stock-look',
    'theme-toggle-missing',
    'tr-uppercase',
    'wcag-aa',
    'width-funnel',
})

MIN_REASON_LEN = 8

_COMMENT_RE = re.compile(
    r'\{/\*\s*(uitools-ignore\b.*?)\s*\*/\}'
    r'|<!--\s*(uitools-ignore\b.*?)\s*-->'
    r'|/\*\s*(uitools-ignore\b.*?)\s*\*/'
    r'|//\s*(uitools-ignore\b.*?)$'
)
_DIRECTIVE_RE = re.compile(
    r'^uitools-ignore(?:-(next-line|start|end|file))?(?:\s*:\s*(.*))?$'
)


def _split_rules_reason(payload):
    """Split '<rules> <sep> <reason>' into (rules_list, reason_str)."""
    for sep_re in (r'\s*(?:—|–|--)\s*', r'\s+-\s+'):
        parts = re.split(sep_re, payload, maxsplit=1)
        if len(parts) == 2:
            rules_part, reason_part = parts
            break
    else:
        if ':' in payload:
            rules_part, reason_part = payload.split(':', 1)
        else:
            rules_part, reason_part = payload, ''
    rules = [r.strip() for r in re.split(r'[\s,]+', rules_part.strip()) if r.strip()]
    return rules, reason_part.strip()


def _issue_lines(msg):
    """Extract 1-based line numbers referenced in an audit issue message."""
    lines = set()
    for m in re.finditer(r'\bL(\d+)\b', msg):
        lines.add(int(m.group(1)))
    for m in re.finditer(r'\(lines?\s+\[?([\d,\s]+)\]?', msg):
        for num in re.findall(r'\d+', m.group(1)):
            lines.add(int(num))
    return lines


def _rule_matches(rules, rule):
    return '*' in rules or 'all' in rules or rule in rules


def parse_ignores(txt, known_rules=None):
    """Parse uitools-ignore directives from source text.

    Returns (file_ignores, line_ignores, range_ignores, meta_issues).
    """
    if known_rules is None:
        known_rules = KNOWN_RULES

    file_ignores = []   # [(rules, reason)]
    line_ignores = {}   # {line_no: [(rules, reason)]}
    range_ignores = []  # [(start_line, end_line, rules, reason)]
    meta_issues = []    # [(sev, rule, msg)]
    open_blocks = []    # [(start_line, rules, reason)]

    lines = txt.splitlines()
    for line_no, line in enumerate(lines, 1):
        for cm in _COMMENT_RE.finditer(line):
            raw = next(g for g in cm.groups() if g is not None).strip()
            dm = _DIRECTIVE_RE.match(raw)
            if not dm:
                continue
            kind = dm.group(1) or 'inline'
            payload = (dm.group(2) or '').strip()

            if kind == 'end':
                if open_blocks:
                    start_ln, rules, reason = open_blocks.pop()
                    range_ignores.append((start_ln, line_no, rules, reason))
                continue

            rules, reason = _split_rules_reason(payload)
            for r in rules:
                if r not in ('*', 'all') and r not in known_rules:
                    meta_issues.append((
                        'INFO',
                        'unknown-rule-in-ignore',
                        f"L{line_no} unknown rule '{r}' in uitools-ignore",
                    ))

            if not rules or len(reason) < MIN_REASON_LEN:
                meta_issues.append((
                    'WARN',
                    'ignore-without-reason',
                    f"L{line_no} uitools-ignore requires rules and a reason (>= {MIN_REASON_LEN} chars) after '—' or '--'",
                ))
                continue

            if kind == 'file':
                file_ignores.append((rules, reason))
            elif kind == 'inline':
                line_ignores.setdefault(line_no, []).append((rules, reason))
            elif kind == 'next-line':
                line_ignores.setdefault(line_no + 1, []).append((rules, reason))
            elif kind == 'start':
                open_blocks.append((line_no, rules, reason))

    total_lines = len(lines)
    for start_ln, rules, reason in open_blocks:
        range_ignores.append((start_ln, total_lines, rules, reason))

    return file_ignores, line_ignores, range_ignores, meta_issues


def _tag_snippet_at_line(file_lines, ln):
    """Extract line `ln` (plus any multi-line opening tag starting on `ln`) with ignore comments stripped."""
    if ln < 1 or ln > len(file_lines):
        return ''
    first = _COMMENT_RE.sub('', file_lines[ln - 1])
    parts = [first]
    if '<' in first and first.count('<') > first.count('>'):
        end_idx = min(len(file_lines), ln + 10)
        lt = first.count('<')
        gt = first.count('>')
        for k in range(ln, end_idx):
            cleaned = _COMMENT_RE.sub('', file_lines[k])
            parts.append(cleaned)
            lt += cleaned.count('<')
            gt += cleaned.count('>')
            if gt >= lt:
                break
    return '\n'.join(parts)


def _ownership_score(file_key, file_lines, ln, rule, msg, active_lines):
    """Score (0..3) how strongly 1-based line `ln` of `file_key` corresponds to `(rule, msg)`."""
    if ln < 1 or ln > len(file_lines):
        return 0
    if active_lines and file_key in active_lines and ln not in active_lines[file_key]:
        return 0
    snip = _tag_snippet_at_line(file_lines, ln)
    if not snip.strip():
        return 1

    if rule == 'wcag-aa':
        m_tw = re.search(r'\b((?:dark:)?text-[^\s]+)\s+on\s+', msg)
        if m_tw:
            fg_cls = m_tw.group(1)
            fg_bare = fg_cls.split('text-', 1)[1]
            if fg_cls in snip or fg_bare in snip:
                return 3
            if re.search(r'<[A-Z]|Variants\b', snip):
                return 2
            return 1
        m_hex = re.search(r'(#[0-9a-fA-F]{3,8})\s+on\s+(#[0-9a-fA-F]{3,8})', msg)
        if m_hex:
            return 3 if m_hex.group(1).lower() in snip.lower() else 1
    elif rule == 'grid':
        m_g = re.match(r'^L\d+\s+(.+?)\s*=\s*[\d.]+px', msg)
        if m_g:
            tok = m_g.group(1).strip()
            if tok and tok in snip:
                return 3
            if re.search(r'<[A-Z]|Variants\b', snip):
                return 2
            return 1
    elif rule in ('fitts-primary', 'single-primary-cta'):
        return 3 if re.search(r'<(?:button|a|[A-Z][\w.]*)\b', snip) else 1
    elif rule in ('nested-radius', 'radius-too-soft', 'frame-wrapper'):
        return 3 if ('rounded' in snip or re.search(r'<[A-Z]', snip)) else 1
    elif rule == 'miller-7':
        return 3 if '<nav' in snip.lower() else 1
    elif rule == 'line-length':
        return 3 if '<p' in snip.lower() else 1
    elif rule in ('headline-measure', 'edge-align'):
        return 3 if '<h1' in snip.lower() else 1
    elif rule == 'editorial-leading':
        return 3 if ('leading-' in snip or re.search(r'<(?:p|blockquote|li)\b', snip)) else 1
    elif rule == 'left-stacked-column':
        return 3 if 'max-w-' in snip else 1
    elif rule == 'branch-explosion':
        return 3 if ('class' in snip or '<' in snip) else 1

    return 2 if ('<' in snip or '{' in snip) else 1


def _apply_multi_file_ignores(txt, source_files, issues, known_rules=None):
    """Apply `uitools-ignore` directives across an entry file and all inlined route/component files."""
    items = list(source_files.items()) if isinstance(source_files, dict) else list(source_files)
    if not items:
        return list(issues), [], []

    if 'uitools-ignore' not in txt and not any('uitools-ignore' in f_txt for _, f_txt in items):
        return list(issues), [], []

    entry_file = getattr(txt, 'entry_file', None) or items[0][0]
    active_lines = getattr(txt, 'active_lines', None) or {}

    parsed_by_file = []
    items_lines = []
    meta_issues = []

    for f_key, f_txt in items:
        f_lines = f_txt.splitlines()
        items_lines.append((f_key, f_lines))
        is_entry = (f_key == entry_file)
        if 'uitools-ignore' in f_txt:
            f_file_ig, f_line_ig, f_range_ig, f_meta = parse_ignores(f_txt, known_rules)
            if is_entry:
                meta_issues.extend(f_meta)
            else:
                bname = pathlib.Path(f_key).name
                for m_sev, m_rule, m_msg in f_meta:
                    meta_issues.append((m_sev, m_rule, f"{bname}: {m_msg}"))
            parsed_by_file.append((f_key, is_entry, f_file_ig, f_line_ig, f_range_ig))
        else:
            parsed_by_file.append((f_key, is_entry, [], {}, []))

    kept_issues = []
    suppressed_issues = []

    for sev, rule, msg in issues:
        matched_reason = None
        iss_lines = sorted(_issue_lines(msg))

        # Precompute per-line ownership scores across all route source files
        line_owners = {}
        for ln in iss_lines:
            scores = {
                f_key: _ownership_score(f_key, f_lines, ln, rule, msg, active_lines)
                for f_key, f_lines in items_lines
            }
            max_sc = max(scores.values(), default=0)
            line_owners[ln] = {
                f_key for f_key, sc in scores.items() if sc > 0 and sc >= max_sc
            } if max_sc > 0 else set()

        # 1. Entry file-level ignores apply to the route; inlined component file-level ignores apply to owned lines (or line-less rules)
        for f_key, is_entry, f_file_ig, _, _ in parsed_by_file:
            if not f_file_ig:
                continue
            if not is_entry and iss_lines and not any(f_key in line_owners.get(ln, ()) for ln in iss_lines):
                continue
            for rules, reason in f_file_ig:
                if _rule_matches(rules, rule):
                    matched_reason = reason
                    break
            if matched_reason is not None:
                break

        # 2. Line and range ignores matched only against files that own `ln`
        if matched_reason is None and iss_lines:
            for ln in iss_lines:
                owners = line_owners.get(ln, ())
                if not owners:
                    continue
                for f_key, _is_entry, _, f_line_ig, f_range_ig in parsed_by_file:
                    if f_key not in owners:
                        continue
                    for rules, reason in f_line_ig.get(ln, ()):
                        if _rule_matches(rules, rule):
                            matched_reason = reason
                            break
                    if matched_reason is not None:
                        break
                    for start_ln, end_ln, rules, reason in f_range_ig:
                        if start_ln <= ln <= end_ln and _rule_matches(rules, rule):
                            matched_reason = reason
                            break
                    if matched_reason is not None:
                        break
                if matched_reason is not None:
                    break

        if matched_reason is not None:
            suppressed_issues.append((sev, rule, msg, matched_reason))
        else:
            kept_issues.append((sev, rule, msg))

    return kept_issues, suppressed_issues, meta_issues


def apply_ignores(txt, issues, known_rules=None):
    """Filter audit issues using uitools-ignore directives in txt (and any RouteSourceText.source_files).

    Returns (kept_issues, suppressed_issues, meta_issues) where:
    - kept_issues: list of (sev, rule, msg)
    - suppressed_issues: list of (sev, rule, msg, reason)
    - meta_issues: list of (sev, rule, msg)
    """
    source_files = getattr(txt, 'source_files', None)
    if source_files:
        return _apply_multi_file_ignores(txt, source_files, issues, known_rules)

    if 'uitools-ignore' not in txt:
        return list(issues), [], []

    file_ignores, line_ignores, range_ignores, meta_issues = parse_ignores(txt, known_rules)
    kept_issues = []
    suppressed_issues = []

    for sev, rule, msg in issues:
        matched_reason = None

        for rules, reason in file_ignores:
            if _rule_matches(rules, rule):
                matched_reason = reason
                break

        if matched_reason is None:
            iss_lines = _issue_lines(msg)
            for ln in sorted(iss_lines):
                for rules, reason in line_ignores.get(ln, ()):
                    if _rule_matches(rules, rule):
                        matched_reason = reason
                        break
                if matched_reason is not None:
                    break
                for start_ln, end_ln, rules, reason in range_ignores:
                    if start_ln <= ln <= end_ln and _rule_matches(rules, rule):
                        matched_reason = reason
                        break
                if matched_reason is not None:
                    break

        if matched_reason is not None:
            suppressed_issues.append((sev, rule, msg, matched_reason))
        else:
            kept_issues.append((sev, rule, msg))

    return kept_issues, suppressed_issues, meta_issues


def _normalize_path(file_path):
    """Normalize file_path to a stable POSIX-style relative path."""
    p = pathlib.Path(file_path)
    if p.is_absolute():
        try:
            p = pathlib.Path(os.path.relpath(p))
        except ValueError:
            p = pathlib.Path(p.name)
    s = p.as_posix()
    while s.startswith('./'):
        s = s[2:]
    return s


def _normalize_msg(msg):
    """Strip line numbers from an audit message so line shifts don't break hashes."""
    s = re.sub(r'\bL\d+\b', 'L?', msg)
    s = re.sub(r'\(lines?\s+\[?[\d,\s]+\]?\)', '(lines ?)', s)
    s = re.sub(r'\bline\s+\d+\b', 'line ?', s)
    return re.sub(r'\s+', ' ', s).strip()


def issue_hash(file_path, rule, msg, source_txt=None):
    """Compute a line-shift-resilient hash for an audit issue."""
    rel_path = _normalize_path(file_path)
    norm_msg = _normalize_msg(msg)
    snippet = ''
    if source_txt is not None:
        lines = source_txt.splitlines()
        iss_lines = sorted(_issue_lines(msg))
        parts = [lines[ln - 1].strip() for ln in iss_lines if 1 <= ln <= len(lines)]
        snippet = '\n'.join(parts)
    payload = f"{rel_path}\0{rule}\0{norm_msg}\0{snippet}"
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]


def load_baseline(path):
    """Load baseline hashes from a JSON file. Returns a set of hash strings."""
    p = pathlib.Path(path)
    if not p.is_file():
        return set()
    data = json.loads(p.read_text(encoding='utf-8'))
    if isinstance(data, dict):
        return set(data.get('entries', []))
    if isinstance(data, list):
        return set(data)
    return set()


def write_baseline(path, entries):
    """Write sorted baseline hashes to a JSON file."""
    p = pathlib.Path(path)
    payload = {
        'version': 1,
        'entries': sorted(set(entries)),
    }
    p.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def filter_baseline(issues_with_files, baseline_entries):
    """Filter out issues whose hash is in baseline_entries.

    issues_with_files: iterable of (file_path, sev, rule, msg) or
                       (file_path, sev, rule, msg, source_txt).
    Returns (new_issues, skipped_count) where new_issues preserves the input tuple shape.
    """
    new_issues = []
    skipped = 0
    for item in issues_with_files:
        if len(item) == 5:
            file_path, sev, rule, msg, source_txt = item
        else:
            file_path, sev, rule, msg = item
            source_txt = None
        h = issue_hash(file_path, rule, msg, source_txt=source_txt)
        if h in baseline_entries:
            skipped += 1
        else:
            new_issues.append(item)
    return new_issues, skipped
