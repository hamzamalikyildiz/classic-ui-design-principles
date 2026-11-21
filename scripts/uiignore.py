#!/usr/bin/env python3
"""Reasoned suppression (`uitools-ignore`) parser and matcher for uitools."""
import re

KNOWN_RULES = frozenset({
    'bold-font-default',
    'bold-headline-size',
    'border-heavy',
    'card-sameness',
    'edge-align',
    'editorial-leading',
    'fitts-primary',
    'flat-hierarchy',
    'frame-wrapper',
    'grey-chart',
    'grid',
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
    'radius-too-soft',
    'reveal-needs-js',
    'shadow-heavy',
    'single-primary-cta',
    'skeleton-empty',
    'stock-look',
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


def apply_ignores(txt, issues, known_rules=None):
    """Filter audit issues using uitools-ignore directives in txt.

    Returns (kept_issues, suppressed_issues, meta_issues) where:
    - kept_issues: list of (sev, rule, msg)
    - suppressed_issues: list of (sev, rule, msg, reason)
    - meta_issues: list of (sev, rule, msg)
    """
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
