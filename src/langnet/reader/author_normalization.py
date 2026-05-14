from __future__ import annotations

import re

_PSEUDO_PREFIX_RE = re.compile(r"^(?:Ps\.?|Pseudo)[\s.-]+(.+)$", re.IGNORECASE)
_PSEUDO_SUFFIX_RE = re.compile(r"^(.+?)\s*\((?:Ps\.?|Pseudo)\)$", re.IGNORECASE)
_HTML_INDEX_ITEM_RE = re.compile(r"^(?P<num>\d{4})\s+(?P<label>.+)$")
_AUTHORITY_ROLE_RE = re.compile(
    r"\s+(?:"
    r"Apol\.|Astrol\.|Biogr\.|Chronogr\.|Comic\.|Eleg\.|Epic\.|Epigr\.|"
    r"Geogr\.|Geom\.|Gramm\.|Hist\.|Hymnographus|Lexicogr\.|Lyr\.|Math\.|"
    r"Med\.|Mech\.|Mimogr\.|Myth\.|Nomographus|Paradox\.|Paroemiogr\.|"
    r"Perieg\.|Phil\.|Philol\.|Poet\.|Poeta|Rhet\.|Scr\.|Soph\.|Theol\.|"
    r"Trag\."
    r").*$"
)


def normalize_reader_author(author: str) -> str:
    value = _normalize_space(author)
    if not value:
        return value
    if value.casefold() == "anonymus":
        return "Anonymous"
    suffix_match = _PSEUDO_SUFFIX_RE.fullmatch(value)
    if suffix_match:
        base = _normalize_comma_name(_normalize_space(suffix_match.group(1)))
        return f"Pseudo-{base}" if base else "Pseudo"
    prefix_match = _PSEUDO_PREFIX_RE.fullmatch(value)
    if prefix_match:
        base = _normalize_comma_name(_normalize_space(prefix_match.group(1)))
        return f"Pseudo-{base}" if base else "Pseudo"
    if value.casefold() in {"pseudo-", "pseudo"}:
        return "Pseudo"
    return _normalize_comma_name(value)


def canonical_author_from_html_index_item(item: str) -> tuple[str, str] | None:
    text = _normalize_space(item)
    match = _HTML_INDEX_ITEM_RE.fullmatch(text)
    if not match:
        return None
    label = _clean_authority_label(match.group("label"))
    if not label.startswith("Pseudo-"):
        return None
    return f"tlg{match.group('num')}", normalize_reader_author(label)


def _clean_authority_label(label: str) -> str:
    text = label.replace("<", "").replace(">", "")
    text = _AUTHORITY_ROLE_RE.sub("", text)
    return _normalize_space(text)


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _normalize_comma_name(value: str) -> str:
    if value.count(",") != 1:
        return value
    family, given = (_normalize_space(part) for part in value.split(",", 1))
    if not family or not given:
        return value
    return f"{given} {family}"
