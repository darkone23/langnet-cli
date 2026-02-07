"""
Heritage abbreviation loader.

Parses the upstream ABBR.md to produce a reusable mapping of abbreviations.
We keep raw keys intact and tag entries as either "source" (lexicon/work)
or "grammar" (pure grammatical tags) to avoid over-expansion.
"""

from __future__ import annotations

import re
import unicodedata
import json
from pathlib import Path
from typing import Literal

AbbrKind = Literal["source", "grammar"]

REPO_ROOT = Path(__file__).resolve().parents[3]
ABBR_DOC_PATH = REPO_ROOT / "docs" / "upstream-docs" / "skt-heritage" / "ABBR.md"
ABBR_JSON_PATH = Path(__file__).resolve().parent / "abbr_data.json"

ABBR_LINE_RE = re.compile(r"^\*\*(?P<abbr>[^*]+)\*\*\s*:\s*(?P<label>[^*]+)")


def _normalize_key(text: str) -> str:
    """Normalize text to an alphanumeric lowercase key."""
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return "".join(ch for ch in stripped.lower() if ch.isalnum())


def _parse_abbreviations_from_markdown() -> dict[str, dict[str, str]]:
    """Parse abbreviations from ABBR.md."""
    mapping: dict[str, dict[str, str]] = {}

    if not ABBR_DOC_PATH.exists():
        return mapping

    try:
        content = ABBR_DOC_PATH.read_text(encoding="utf-8").splitlines()
    except Exception:
        return mapping

    for line in content:
        line = line.strip()
        if not line.startswith("**"):
            continue
        match = ABBR_LINE_RE.match(line)
        if not match:
            continue
        abbr = match.group("abbr").strip()
        label = match.group("label").strip()
        key = _normalize_key(abbr)
        if not key:
            continue

        # Heuristic: mark as grammar if it looks like a grammatical tag; else source.
        grammar_flags = {
            "abl",
            "acc",
            "dat",
            "gen",
            "loc",
            "voc",
            "nom",
            "imperf",
            "fut",
            "aor",
            "opt",
            "perf",
        }
        kind: AbbrKind = "grammar" if key in grammar_flags else "source"

        mapping[key] = {
            "display": abbr,
            "long_name": label,
            "kind": kind,
        }

    return mapping


def load_abbreviations() -> dict[str, dict[str, str]]:
    """
    Load abbreviations from the generated JSON cache, falling back to parsing ABBR.md.

    Returns:
        dict mapping normalized key -> {"display": abbr, "long_name": label, "kind": ...}
    """
    if ABBR_JSON_PATH.exists():
        try:
            return json.loads(ABBR_JSON_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass

    return _parse_abbreviations_from_markdown()


# Cache on import for simple reuse.
HERITAGE_ABBR_MAP = load_abbreviations()
