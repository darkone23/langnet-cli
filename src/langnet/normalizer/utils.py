from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

from betacode import conv as betacode_conv  # type: ignore[import]

GREEK_BASIC_START = 0x0370
GREEK_BASIC_END = 0x03FF
GREEK_EXTENDED_START = 0x1F00
GREEK_EXTENDED_END = 0x1FFF


def strip_accents(text: str) -> str:
    """Remove combining marks from a Unicode string."""
    return "".join(
        char for char in unicodedata.normalize("NFD", text) if unicodedata.category(char) != "Mn"
    )


def contains_greek(text: str) -> bool:
    """Detect if a string contains Greek code points."""
    for char in text:
        code = ord(char)
        if (
            GREEK_BASIC_START <= code <= GREEK_BASIC_END
            or GREEK_EXTENDED_START <= code <= GREEK_EXTENDED_END
        ):
            return True
    return False


def unique(seq: Iterable[str]) -> list[str]:
    """Preserve order while removing duplicates."""
    seen: set[str] = set()
    out: list[str] = []
    for item in seq:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _looks_like_betacode(text: str) -> bool:
    """
    Heuristic: betacode strings typically include *, /, \\ or () accents.
    """
    return any(ch in text for ch in ("*", "/", "\\", "(", ")", "+", "="))


def _collapse_token(text: str) -> str:
    """
    Lowercase and strip to alnum/underscore, folding final sigma to standard sigma.
    """
    normalized = strip_accents(text).lower().replace("ς", "σ")
    normalized = re.sub(r"[^a-z0-9_]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized


def normalize_greekish_token(text: str) -> str | None:
    """
    Normalize Greek/betacode/ASCII Greekish text into an ASCII-safe token.

    - If Greek code points are present: strip accents, fold final sigma,
      convert to betacode when possible, then collapse.
    - If it looks like betacode: convert to Unicode Greek first, then process.
    - Otherwise return None to let callers fall back to their default rules.
    """
    if not text:
        return None
    cleaned = strip_accents(text).strip()
    candidate: str | None = None
    if contains_greek(cleaned):
        candidate = cleaned
    elif _looks_like_betacode(cleaned):
        try:
            candidate = betacode_conv.beta_to_uni(cleaned)
        except Exception:
            candidate = None
    if not candidate:
        return None
    try:
        betacode = betacode_conv.uni_to_beta(strip_accents(candidate))
        return _collapse_token(betacode)
    except Exception:
        pass
    collapsed = _collapse_token(candidate)
    return collapsed or None
