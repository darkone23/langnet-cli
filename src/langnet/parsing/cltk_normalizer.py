"""Normalize CLTK lewis_lines format to Diogenes-compatible format.

CLTK provides Lewis & Short entries in a different format than Diogenes:

CLTK format:
    "lupus\\n\\n\\n ī, \\nm\\n\\n a wolf: Torva leaena..."
    "amō āvī, ātus, āre AM-, to love: magis te..."

Target format (Diogenes-compatible):
    "lupus, -i, m."
    "amo, amare, amavi, amatum, v."

This module provides preprocessing to convert CLTK → Diogenes format.
"""

from __future__ import annotations

import re

# Minimum principal parts to identify a verb entry
MIN_VERB_PRINCIPAL_PARTS = 3


def remove_macrons(text: str) -> str:
    """Remove macrons from Latin text.

    Args:
        text: Latin text with macrons

    Returns:
        Text with macrons removed

    Example:
        >>> remove_macrons("amō āvī")
        'amo avi'
    """
    macron_map = {
        "ā": "a",
        "ē": "e",
        "ī": "i",
        "ō": "o",
        "ū": "u",
        "Ā": "A",
        "Ē": "E",
        "Ī": "I",
        "Ō": "O",
        "Ū": "U",
    }

    for macron, plain in macron_map.items():
        text = text.replace(macron, plain)

    return text


def normalize_cltk_lewis_line(lewis_line: str) -> str:
    """Normalize CLTK lewis_lines format to Diogenes-compatible format.

    Args:
        lewis_line: Raw CLTK lewis_lines entry

    Returns:
        Normalized entry in Diogenes format, or original if normalization fails

    Example:
        >>> normalize_cltk_lewis_line("lupus\\n\\n\\n ī, \\nm\\n\\n a wolf:")
        'lupus, -i, m.'
    """
    # Early detection: if input is already clean Diogenes format, return as-is
    # Clean format has: no newlines, commas present, dashes in inflections
    if "\n" not in lewis_line and "," in lewis_line:
        # Likely already in clean Diogenes format - pass through unchanged
        return lewis_line.strip()

    # Remove macrons first
    normalized = remove_macrons(lewis_line)

    # Collapse multiple newlines and excessive whitespace
    normalized = re.sub(r"\n+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = normalized.strip()

    # Extract just the first few tokens (header info before definition)
    # Strategy: Look for conjugation/declension markers (AR-, REG-, etc.) as boundaries
    # These mark the end of the header in CLTK format

    # First, try to find marker-based boundary
    marker_match = re.match(r"^(.+?)\s+[A-Z]+-,?\s+", normalized)
    if marker_match:
        # Extract up to and including the marker
        header_with_marker = marker_match.group(0).strip().rstrip(",")
        header_part = header_with_marker
    else:
        # Fall back to definition-based boundaries
        header_match = re.match(
            r"^(.+?)(?:[:;]"  # Colon or semicolon
            r"|\s+to\s+"  # " to " (infinitive marker)
            r"|\s+an?\s+(?:[a-z]+)"  # " a/an " + any word (definition start)
            r"|,\s+[a-z]{2,}\s*,"  # Comma, word, comma (definition like ", vir,")
            r"|\s+implements\s+"  # Common definition words
            r"|\s+tools?\s+"
            r"|\s+strength\s+"
            r"|\s+manliness\s+"
            r")",
            normalized,
            re.IGNORECASE,
        )
        if header_match:
            header_part = header_match.group(1).strip()
        else:
            # Take first ~8 words as header
            words = normalized.split()[:8]
            header_part = " ".join(words)

    # Try Pattern 1: Noun format "lemma principal_parts gender [MARKER]"
    # E.g.: "lupus i, m" or "rex regis, m REG-" or "arma orum, n 1 AR-"
    # Also handle: "dux ducis, m and f" (both genders)
    # Look for gender marker near the end, allow for optional markers after
    match = re.match(
        r"^([a-zA-Z]+)"  # Lemma
        r"\s+"
        r"([a-zA-Z, -]+?)"  # Principal parts (non-greedy)
        r"[,\s]+"
        r"([mfn])"  # Gender marker
        r"(?:\s+and\s+[mfn])?"  # Optional "and f/m" for dual-gender nouns
        r"(?:\s+[0-9]*\s*[A-Z]+-?,?)?"  # Optional marker (REG-, 1 AR-, etc.)
        r"\s*$",
        header_part,
        re.IGNORECASE,
    )

    if match:
        lemma = match.group(1)
        parts_raw = match.group(2).strip().rstrip(",")
        gender = match.group(3).strip()

        # Clean up parts - remove markers if any got through
        parts_raw = re.sub(r"\s*[0-9]*\s*[A-Z]+-?,?\s*", "", parts_raw)

        # Split and clean
        part_list = [
            p.strip()
            for p in re.split(r"[,\s]+", parts_raw)
            if p.strip() and p not in ("-", ",") and not p.isupper()
        ]

        # Add dash prefix if needed
        part_list = [f"-{p}" if not p.startswith("-") else p for p in part_list]
        parts_str = ", ".join(part_list)

        return f"{lemma}, {parts_str}, {gender}."

    # Try Pattern 2: Verb format "lemma part1, part2, part3 [CONJMARKER]"
    # E.g.: "amo avi, atus, are AM-" or "moneo ui, itus, ere 1 MAN-,"
    match = re.match(
        r"^([a-zA-Z]+)"  # Lemma
        r"\s+"
        r"([a-zA-Z, -]+)"  # Principal parts
        r"(?:\s+[0-9]*\s*[A-Z]+-?)?"  # Optional number + conjugation marker
        r"\s*,?\s*$",  # Optional trailing comma
        header_part,
        re.IGNORECASE,
    )

    if match:
        lemma = match.group(1)
        parts_raw = match.group(2).strip()

        # Clean up: remove conjugation markers and numbers
        parts_raw = re.sub(r"\s+[0-9]*\s*[A-Z]+-?\s*,?\s*$", "", parts_raw)
        parts_raw = re.sub(r"[0-9]*\s*[A-Z]+-?,?\s*", "", parts_raw)

        # Remove "or" as a connector (e.g., "ivi or ii" -> "ivi ii")
        parts_raw = re.sub(r"\s+or\s+", " ", parts_raw, flags=re.IGNORECASE)

        # Split and count
        part_list = [
            p.strip()
            for p in re.split(r"[,\s]+", parts_raw)
            if p.strip() and len(p.strip()) > 1 and p.lower() not in ("or", "and")
        ]

        if len(part_list) >= MIN_VERB_PRINCIPAL_PARTS:
            return f"{lemma}, {', '.join(part_list)}, v."

    # Fallback: simple "lemma gender" pattern
    match = re.match(r"^([a-zA-Z]+)\s+([mfn])\s*$", header_part, re.IGNORECASE)
    if match:
        return f"{match.group(1)}, {match.group(2)}."

    # Last resort: just return lemma with period
    words = normalized.split()
    return f"{words[0]}." if words else lewis_line


def normalize_cltk_lewis_lines(lewis_lines: list[str]) -> list[str]:
    """Normalize all CLTK lewis_lines entries.

    Args:
        lewis_lines: List of raw CLTK lewis_lines

    Returns:
        List of normalized entries

    Example:
        >>> lines = ["lupus\\n\\n\\n ī, \\nm\\n\\n a wolf:"]
        >>> normalize_cltk_lewis_lines(lines)
        ['lupus, -i, m.']
    """
    return [normalize_cltk_lewis_line(line) for line in lewis_lines]
