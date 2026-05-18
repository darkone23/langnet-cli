"""Text repair helpers for Bailly PDF-derived entries."""

from __future__ import annotations

import re

_LETTER = r"A-Za-zÀ-ÖØ-öø-ÿ\u0370-\u03FF\u1F00-\u1FFF"
_LINE_BREAK_HYPHEN_RE = re.compile(rf"(?<=[{_LETTER}])-\s+(?=[{_LETTER}])")


def repair_bailly_line_break_hyphenation(text: str) -> str:
    """Join words split by PDF line-break hyphenation."""
    return _LINE_BREAK_HYPHEN_RE.sub("", text)
