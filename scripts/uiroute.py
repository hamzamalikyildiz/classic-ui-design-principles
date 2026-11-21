"""Route vs component file classification skeleton (Phase A6).

API note (v0.1 skeleton):
    This module establishes the stdlib-only boundary for distinguishing full
    page/route entry files (e.g. ``app/**/page.tsx``, ``pages/*.tsx``,
    ``index.html``) from reusable UI components (e.g. ``components/*.tsx``)
    in Phase A6. Until Phase A6 lands, ``is_page_file`` acts as a safe default
    stub without altering existing audit behavior.
"""
import pathlib

__all__ = [
    'API_VERSION',
    'is_page_file',
]

API_VERSION = '0.1-skeleton'


def is_page_file(path):
    """Return whether ``path`` represents a full page/route entry (Phase A6 stub)."""
    return bool(pathlib.Path(path).name)
