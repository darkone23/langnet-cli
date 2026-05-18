from __future__ import annotations

import importlib
import re
import unicodedata
from dataclasses import dataclass

from langnet.normalizer.utils import normalize_greek_compatibility, strip_accents, unique

NORMALIZER_VERSION = "reader-search-normalizer-v1"
PUNCTUATION_RE = re.compile(r"[^\w\u0370-\u03ff\u1f00-\u1fff\u0900-\u097f]+", re.UNICODE)
WHITESPACE_RE = re.compile(r"\s+")
SANSKRIT_ANUSVARA_BEFORE_CONSONANT_RE = re.compile(
    r"[ṃṁ](?=[kgṅcjñṭḍṇtdnpbmyrlvśṣsh])",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ReaderSearchText:
    display_text: str
    search_text: str
    search_text_folded: str
    token_text: str
    normalizer_version: str = NORMALIZER_VERSION


@dataclass(frozen=True)
class ReaderSearchQuery:
    raw_query: str
    search_text: str
    search_text_folded: str
    token_text: str
    query_variants: tuple[str, ...]
    normalizer_version: str = NORMALIZER_VERSION


def normalize_segment_for_search(language: str, text: str) -> ReaderSearchText:
    search_text = _normalize_search_text(language, text, folded=False)
    folded = _normalize_search_text(language, text, folded=True)
    return ReaderSearchText(
        display_text=text,
        search_text=search_text,
        search_text_folded=folded,
        token_text=_normalize_token_text(language, text),
    )


def normalize_query_for_search(language: str, query: str) -> ReaderSearchQuery:
    search_text = _normalize_search_text(language, query, folded=False)
    folded = _normalize_search_text(language, query, folded=True)
    variants = tuple(unique(_query_variants(language, search_text, folded)))
    return ReaderSearchQuery(
        raw_query=query,
        search_text=search_text,
        search_text_folded=folded,
        token_text=folded,
        query_variants=variants,
    )


def _query_variants(language: str, search_text: str, folded: str) -> list[str]:
    variants = [search_text, folded]
    if language == "lat":
        variants.extend(_latin_spelling_variants(folded))
    elif language == "san":
        variants.extend(_sanskrit_transliteration_variants(search_text))
        variants.extend(_sanskrit_nasal_variants(folded))
    return [variant for variant in variants if variant]


def _normalize_search_text(language: str, text: str, *, folded: bool) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    if language == "grc":
        normalized = normalize_greek_compatibility(normalized).replace("ς", "σ")
        if folded:
            normalized = strip_accents(normalized)
    elif language == "san":
        normalized = _normalize_sanskrit_text(normalized, folded=folded)
    elif language == "lat" and folded:
        normalized = _latin_fold(normalized)
    elif folded:
        normalized = strip_accents(normalized)
    return _token_boundary_text(normalized)


def _normalize_sanskrit_text(text: str, *, folded: bool) -> str:
    if not folded:
        return text
    nasal_folded = SANSKRIT_ANUSVARA_BEFORE_CONSONANT_RE.sub("n", text)
    return strip_accents(nasal_folded)


def _normalize_token_text(language: str, text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    if language == "grc":
        normalized = strip_accents(normalize_greek_compatibility(normalized).replace("ς", "σ"))
    elif language == "san":
        normalized = _normalize_sanskrit_text(normalized, folded=True)
    else:
        normalized = strip_accents(normalized)
    return _token_boundary_text(normalized)


def _latin_fold(text: str) -> str:
    return strip_accents(text).replace("j", "i").replace("v", "u")


def _latin_spelling_variants(text: str) -> list[str]:
    variants = [text]
    variants.append(text.replace("j", "i").replace("v", "u"))
    variants.append(text.replace("i", "j").replace("u", "v"))
    return variants


def _sanskrit_nasal_variants(text: str) -> list[str]:
    return [text, text.replace("n", "m")]


def _sanskrit_transliteration_variants(text: str) -> list[str]:
    if not any("\u0900" <= char <= "\u097f" for char in text):
        return []
    try:
        sanscript = importlib.import_module("indic_transliteration.sanscript")
        iast = sanscript.transliterate(text, sanscript.DEVANAGARI, sanscript.IAST)
    except Exception:  # pragma: no cover - optional dependency/runtime guard
        return []
    folded = _normalize_sanskrit_text(iast.casefold(), folded=True)
    return unique([iast.casefold(), folded, *(_sanskrit_nasal_variants(folded))])


def _token_boundary_text(text: str) -> str:
    text = PUNCTUATION_RE.sub(" ", text)
    text = WHITESPACE_RE.sub(" ", text)
    return text.strip()
