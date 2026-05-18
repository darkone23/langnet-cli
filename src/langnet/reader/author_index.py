from __future__ import annotations

import importlib
import re
import unicodedata
from typing import Any

_LATIN_SECTION_ORDER = tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
_GREEK_SECTION_ORDER = tuple("ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ")
_SANSKRIT_SECTION_ORDER = tuple("अआइईउऊऋॠऌॡएऐओऔकखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसह")
_UNKNOWN_SECTION = "#"
_NON_RESPONSIBLE_AUTHOR_KINDS = frozenset({"work_title", "anonymous_label", "ambiguous"})
_ROMAN_PRAENOMINA = {
    "A",
    "APP",
    "C",
    "CN",
    "D",
    "K",
    "L",
    "M",
    "MAM",
    "N",
    "P",
    "Q",
    "SER",
    "SEX",
    "SP",
    "T",
    "TI",
    "V",
}
_GREEK_LATIN_INITIALS = {
    "A": "Α",
    "B": "Β",
    "C": "Κ",
    "D": "Δ",
    "E": "Ε",
    "F": "Φ",
    "G": "Γ",
    "H": "Η",
    "I": "Ι",
    "J": "Ι",
    "K": "Κ",
    "L": "Λ",
    "M": "Μ",
    "N": "Ν",
    "O": "Ο",
    "P": "Π",
    "Q": "Κ",
    "R": "Ρ",
    "S": "Σ",
    "T": "Τ",
    "U": "Υ",
    "V": "Β",
    "W": "Ω",
    "X": "Ξ",
    "Y": "Υ",
    "Z": "Ζ",
}


def author_index_entry(row: dict[str, Any]) -> dict[str, Any]:
    language = str(row.get("language") or "")
    source_author_id = str(row.get("source_author_id") or row.get("author_id") or "")
    raw_name = str(row.get("author") or "").strip()
    display_name = raw_name or "Unknown"
    index_name = _index_name(language, display_name)
    native_name = _native_name(language, index_name)
    section_key = _section_key(language, index_name, native_name) if raw_name else _UNKNOWN_SECTION
    selector = _author_selector(language, source_author_id, index_name)
    alternate_names = _alternate_names(display_name)
    return {
        "author_id": selector,
        "source_author_id": source_author_id or None,
        "display_name": display_name,
        "author": display_name,
        "index_name": index_name,
        "native_name": native_name,
        "section_key": section_key,
        "language": language,
        "work_count": int(row.get("work_count") or 0),
        "word_count": int(row.get("word_count") or 0),
        "word_count_method": str(row.get("word_count_method") or "whitespace_tokens"),
        "representative_titles": str(row.get("representative_titles") or ""),
        "alternate_names": alternate_names,
        "sort_key": (
            _author_sort_key(language, index_name, native_name)
            if raw_name
            else f"9999:{_UNKNOWN_SECTION}:unknown"
        ),
    }


def author_section_sort_key(language: str | None, section_key: str) -> str:
    section_key = normalize_section_key(language, section_key)
    order = _section_order(language)
    try:
        return f"{order.index(section_key):04d}:{section_key}"
    except ValueError:
        return f"9999:{section_key}"


def normalize_section_key(language: str | None, section_key: str) -> str:
    value = section_key.strip()
    if not value:
        return _UNKNOWN_SECTION
    if language == "grc":
        return _normalize_greek_char(value[0])
    if language == "san":
        native = _native_name("san", value)
        return _first_ordered_char(native, _SANSKRIT_SECTION_ORDER) or value[0]
    if language == "lat":
        return _ascii_fold(value[0]).upper()[:1] or _UNKNOWN_SECTION
    return value[:1]


def author_selector_matches(
    *,
    selector: str,
    language: str,
    source_author_id: str | None,
    author: str,
) -> bool:
    normalized = selector.strip()
    if not normalized:
        return False
    source = source_author_id or ""
    index_name = _index_name(language, author or "Unknown")
    return normalized == _author_selector(language, source, index_name)


def author_search_key(value: object) -> str:
    return _ascii_fold(str(value or "")).casefold()


def is_synthetic_author_selector(selector: str | None) -> bool:
    return bool(selector and selector.startswith("langnet:reader:author:"))


def canonical_unknown_author_id(language: str) -> str:
    code = re.sub(r"[^A-Za-z0-9_-]+", "-", language.strip()).strip("-") or "und"
    return f"urn:cts:langnet:author.{code}.unknown"


def canonical_author_id_for_source(
    language: str,
    source_author_id: str | None,
    fallback_selector: str,
    fallback_name: str,
) -> str:
    source = (source_author_id or "").strip()
    if source.startswith("urn:cts:"):
        return source
    compact = compact_author_id(source)
    if language == "grc" and re.fullmatch(r"tlg\d+[A-Za-z]?", compact):
        return f"urn:cts:greekLit:{compact}"
    if language == "lat" and re.fullmatch(r"phi\d+[A-Za-z]?", compact):
        return f"urn:cts:latinLit:{compact}"
    if fallback_selector.startswith("urn:cts:"):
        return fallback_selector
    if is_synthetic_author_selector(fallback_selector):
        return f"urn:cts:langnet:author.{language}.{_slug(fallback_name)}"
    return fallback_selector


def author_kind_uses_unknown_authority(agent_kind: str | None) -> bool:
    return (agent_kind or "").strip() in _NON_RESPONSIBLE_AUTHOR_KINDS


def compact_author_id(source_author_id: str) -> str:
    value = source_author_id.strip()
    if not value:
        return ""
    match = re.search(r"(?:^|[:/.])((?:phi|tlg)\d+[A-Za-z]?)$", value)
    if match:
        return match.group(1)
    return value


def _section_order(language: str | None) -> tuple[str, ...]:
    if language == "grc":
        return _GREEK_SECTION_ORDER
    if language == "san":
        return _SANSKRIT_SECTION_ORDER
    if language == "lat":
        return _LATIN_SECTION_ORDER
    return ()


def _index_name(language: str, display_name: str) -> str:
    name = _strip_parenthetical(display_name).strip()
    if language == "lat":
        name = _strip_latin_praenomina(name)
    return re.sub(r"\s+", " ", name).strip() or "Unknown"


def _native_name(language: str, index_name: str) -> str:
    if language == "san":
        return _sanskrit_iast_to_devanagari(index_name) or index_name
    return index_name


def _section_key(language: str, index_name: str, native_name: str) -> str:
    if language == "grc":
        greek = _first_greek_char(index_name)
        if greek:
            return _normalize_greek_char(greek)
        first_ascii = _ascii_fold(index_name[:1]).upper()
        return _GREEK_LATIN_INITIALS.get(first_ascii, _UNKNOWN_SECTION)
    if language == "san":
        return _first_ordered_char(native_name, _SANSKRIT_SECTION_ORDER) or _UNKNOWN_SECTION
    if language == "lat":
        first = _ascii_fold(index_name[:1]).upper()
        return first if first in _LATIN_SECTION_ORDER else _UNKNOWN_SECTION
    return index_name[:1] or _UNKNOWN_SECTION


def _author_sort_key(language: str, index_name: str, native_name: str) -> str:
    section = _section_key(language, index_name, native_name)
    return f"{author_section_sort_key(language, section)}:{_ascii_fold(index_name).casefold()}"


def _author_selector(language: str, source_author_id: str, index_name: str) -> str:
    compact = compact_author_id(source_author_id)
    if compact:
        return compact
    return f"langnet:reader:author:{language}:{_slug(index_name)}"


def _alternate_names(display_name: str) -> list[str]:
    names = []
    for value in re.findall(r"\(([^)]+)\)", display_name):
        cleaned = value.strip()
        if cleaned and cleaned not in names:
            names.append(cleaned)
    if "Virgil" in names and "Vergil" not in names:
        names.append("Vergil")
    if "Vergil" in names and "Virgil" not in names:
        names.append("Virgil")
    return names


def _strip_parenthetical(value: str) -> str:
    return re.sub(r"\s*\([^)]*\)", "", value)


def _strip_latin_praenomina(value: str) -> str:
    parts = value.split()
    while parts:
        token = parts[0].rstrip(".").upper()
        if token not in _ROMAN_PRAENOMINA:
            break
        parts = parts[1:]
    return " ".join(parts) if parts else value


def _first_greek_char(value: str) -> str | None:
    for char in value:
        normalized = _normalize_greek_char(char)
        if normalized in _GREEK_SECTION_ORDER:
            return normalized
    return None


def _normalize_greek_char(char: str) -> str:
    stripped = _strip_accents(char).upper()
    return "Σ" if stripped == "ς".upper() else stripped[:1]


def _first_ordered_char(value: str, order: tuple[str, ...]) -> str | None:
    for char in value:
        if char in order:
            return char
    return None


def _sanskrit_iast_to_devanagari(text: str) -> str | None:
    try:
        sanscript = importlib.import_module("indic_transliteration.sanscript")
        rendered = sanscript.transliterate(text, sanscript.IAST, sanscript.DEVANAGARI)
    except Exception:
        return None
    return rendered if isinstance(rendered, str) and rendered.strip() else None


def _slug(value: str) -> str:
    folded = _ascii_fold(value).casefold()
    slug = re.sub(r"[^a-z0-9]+", "-", folded).strip("-")
    return slug or "unknown"


def _ascii_fold(value: str) -> str:
    stripped = _strip_accents(value)
    return stripped.encode("ascii", "ignore").decode("ascii")


def _strip_accents(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value)
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
