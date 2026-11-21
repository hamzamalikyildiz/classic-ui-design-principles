"""Inline/file ignore directive parsing and filtering skeleton (Phase A1/A2).

API note (v0.1 skeleton):
    This module establishes the stdlib-only boundary for ignore directives
    (e.g. ``uitools-ignore`` comments and ``.uitoolsignore`` rules) that will
    be implemented in Phase A1/A2. Until then, helpers act as transparent
    no-ops so existing audit behavior remains unchanged.
"""

__all__ = [
    'API_VERSION',
    'parse_ignores',
    'filter_ignored',
]

API_VERSION = '0.1-skeleton'


def parse_ignores(txt, path=None):
    """Parse ignore directives from source text or config (Phase A1/A2 stub)."""
    return {}


def filter_ignored(issues, ignores=None):
    """Filter out suppressed issues according to parsed ignore rules (Phase A1/A2 stub)."""
    return list(issues)
