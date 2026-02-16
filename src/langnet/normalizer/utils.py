from __future__ import annotations

import unicodedata
from collections.abc import Iterable

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
