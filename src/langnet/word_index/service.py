from __future__ import annotations

import hashlib
import importlib
import re
import unicodedata
from collections import defaultdict
from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from langnet.databuild.lewis_1890 import normalize_lewis_1890_headword
from langnet.databuild.paths import (
    default_bailly_path,
    default_cdsl_path,
    default_dico_path,
    default_diogenes_path,
    default_gaffiot_path,
    default_georges_1913_path,
    default_lewis_1890_path,
    default_strongs_greek_path,
    default_whitakers_path,
)
from langnet.databuild.strongs_greek import normalize_strongs_greek_key
from langnet.execution.handlers.bailly import normalize_bailly_headword
from langnet.execution.handlers.cdsl import _slp1_to_iast, _strip_sanskrit_pitch_accents, _to_slp1
from langnet.execution.handlers.dico import normalize_dico_headword
from langnet.execution.handlers.gaffiot import normalize_gaffiot_headword
from langnet.execution.handlers.georges_1913 import normalize_georges_1913_headword
from langnet.heritage.velthuis_converter import to_heritage_velthuis
from langnet.storage.db import connect_duckdb_ro
from langnet.tool_catalog import LANGUAGE_LABELS, LanguageCode, canonical_language

WORD_INDEX_SCHEMA_VERSION = "langnet.word_index.v1"
WORD_INDEX_SECTIONS_SCHEMA_VERSION = "langnet.word_index_sections.v1"
WordIndexLanguage = Literal["lat", "grc", "san", "all"]
WordIndexSource = Literal[
    "all",
    "cdsl",
    "dico",
    "gaffiot",
    "georges_1913",
    "lewis_1890",
    "whitakers",
    "diogenes",
    "bailly",
    "strongs_greek",
]
WordIndexMerge = Literal["auto", "none", "lexeme"]
WordIndexHomographs = Literal["grouped", "raw"]
_SOURCE_ORDER = {
    "cdsl": 0,
    "dico": 1,
    "gaffiot": 2,
    "lewis_1890": 3,
    "georges_1913": 4,
    "whitakers": 5,
    "diogenes": 6,
    "bailly": 7,
    "strongs_greek": 8,
}
_LANGUAGE_ORDER = {"san": 0, "grc": 1, "lat": 2}
NON_ASCII_CODEPOINT_MIN = 128
ANCHOR_HYDRATION_LIMIT = 2000
SANSKRIT_FINAL_A_MIN_LENGTH = 3
_SANSKRIT_FINAL_S_STEM_MARKERS = frozenset("āīūṛṝḷḹṅñṇśṣṃṁḥ.fFxX")
_SANSKRIT_SECTION_SOURCE_PREFIXES = frozenset(
    {
        "a",
        "A",
        "i",
        "I",
        "u",
        "U",
        "f",
        "F",
        "x",
        "X",
        "e",
        "E",
        "o",
        "O",
        "aM",
        "aH",
        "k",
        "K",
        "g",
        "G",
        "N",
        "c",
        "C",
        "j",
        "J",
        "Y",
        "w",
        "W",
        "q",
        "Q",
        "R",
        "t",
        "T",
        "d",
        "D",
        "n",
        "p",
        "P",
        "b",
        "B",
        "m",
        "y",
        "r",
        "l",
        "v",
        "S",
        "z",
        "s",
        "h",
        "kz",
        "tr",
        "jY",
    }
)


@dataclass(frozen=True, slots=True)
class WordIndexPaths:
    cdsl_mw: Path
    cdsl_ap90: Path
    dico: Path
    gaffiot: Path
    diogenes_lat: Path
    diogenes_grc: Path
    lewis_1890: Path = Path("__missing_word_index_lewis_1890.duckdb__")
    georges_1913: Path = Path("__missing_word_index_georges_1913.duckdb__")
    bailly: Path = Path("__missing_word_index_bailly.duckdb__")
    strongs_greek: Path = Path("__missing_word_index_strongs_greek.duckdb__")
    whitakers: Path = Path("__missing_word_index_whitakers.duckdb__")

    @classmethod
    def defaults(cls) -> WordIndexPaths:
        return cls(
            cdsl_mw=default_cdsl_path("mw"),
            cdsl_ap90=default_cdsl_path("ap90"),
            dico=default_dico_path(),
            gaffiot=default_gaffiot_path(),
            lewis_1890=default_lewis_1890_path(),
            georges_1913=default_georges_1913_path(),
            diogenes_lat=default_diogenes_path("lat"),
            diogenes_grc=default_diogenes_path("grc"),
            bailly=default_bailly_path(),
            strongs_greek=default_strongs_greek_path(),
            whitakers=default_whitakers_path(),
        )


def word_index_sources_payload(
    language: str = "all",
    *,
    paths: WordIndexPaths | None = None,
) -> dict[str, object]:
    paths = paths or WordIndexPaths.defaults()
    languages = _languages_for_request(language)
    sources = [
        *_cdsl_statuses(paths, languages),
        _dico_status(paths, languages),
        _gaffiot_status(paths, languages),
        _lewis_1890_status(paths, languages),
        _georges_1913_status(paths, languages),
        _whitakers_status(paths, languages),
        *_diogenes_statuses(paths, languages),
        _bailly_status(paths, languages),
        _strongs_greek_status(paths, languages),
    ]
    sources = [source for source in sources if source is not None]
    return {
        "schema_version": WORD_INDEX_SCHEMA_VERSION,
        "request": {"language": language, "mode": "sources"},
        "sources": sources,
        "items": [],
        "neighborhood": None,
        "pagination": {"next_cursor": None, "prev_cursor": None},
        "warnings": [],
    }


def word_index_sections_payload(
    language: str,
    *,
    source: str = "all",
    paths: WordIndexPaths | None = None,
) -> dict[str, object]:
    paths = paths or WordIndexPaths.defaults()
    languages = _languages_for_request(language)
    if len(languages) != 1:
        raise ValueError("word-index sections requires one language: lat, grc, or san.")
    language_code = languages[0]
    warnings: list[dict[str, str]] = []
    sections = [
        _section_payload(
            spec,
            language=language_code,
            source=source,
            paths=paths,
            warnings=warnings,
        )
        for spec in _section_specs(language_code)
    ]
    if language_code == "san":
        warnings.append(
            {
                "source": source,
                "message": (
                    "Sanskrit section anchors follow varnamala buckets; source-local "
                    "neighborhood order still comes from word-index nearby."
                ),
            }
        )
    return {
        "schema_version": WORD_INDEX_SECTIONS_SCHEMA_VERSION,
        "request": {"language": language_code, "source": source},
        "order": _sections_order_metadata(language_code, source),
        "sections": sections,
        "warnings": warnings,
    }


def word_index_list_payload(  # noqa: PLR0913
    language: str,
    *,
    source: str = "all",
    prefix: str = "",
    limit: int = 50,
    cursor: str | None = None,
    paths: WordIndexPaths | None = None,
) -> dict[str, object]:
    paths = paths or WordIndexPaths.defaults()
    offset = _cursor_offset(cursor)
    warnings: list[dict[str, str]] = []
    collapse_lexemes = _collapse_list_lexemes(source)
    collection_limit = (limit + offset) * 4 if collapse_lexemes else limit + offset
    items = _collect_items(
        languages=_languages_for_request(language),
        source=source,
        prefix=prefix,
        limit=collection_limit,
        paths=paths,
        warnings=warnings,
    )
    if collapse_lexemes:
        items = _wheel_lexeme_cards(items)
        items.sort(key=_canonical_item_order_key)
    items = _interleave(items, limit=limit, offset=offset)
    return {
        "schema_version": WORD_INDEX_SCHEMA_VERSION,
        "request": {
            "language": language,
            "source": source,
            "mode": "list",
            "prefix": prefix,
            "limit": limit,
            "cursor": cursor,
        },
        "sources": word_index_sources_payload(language, paths=paths)["sources"],
        "order": _list_payload_order(language=language, source=source, prefix=prefix),
        "items": items,
        "neighborhood": None,
        "pagination": {
            "next_cursor": str(offset + limit) if len(items) == limit else None,
            "prev_cursor": str(max(0, offset - limit)) if offset else None,
        },
        "warnings": warnings,
    }


def word_index_browse_payload(  # noqa: PLR0913
    language: str,
    *,
    source: str = "all",
    prefix: str = "",
    limit: int = 50,
    homographs: WordIndexHomographs = "grouped",
    paths: WordIndexPaths | None = None,
) -> dict[str, object]:
    paths = paths or WordIndexPaths.defaults()
    homograph_policy = _homograph_policy(homographs)
    languages = _languages_for_request(language)
    if len(languages) != 1:
        raise ValueError("word-index browse requires one language: lat, grc, or san.")
    language_code = languages[0]
    warnings: list[dict[str, str]] = []
    groups = _browse_groups(
        language=language_code,
        source=source,
        prefix=prefix,
        limit=limit,
        homographs=homograph_policy,
        paths=paths,
        warnings=warnings,
    )
    items = _cross_dictionary_browse_items(groups) if homograph_policy == "grouped" else []
    return {
        "schema_version": WORD_INDEX_SCHEMA_VERSION,
        "request": {
            "language": language_code,
            "source": source,
            "mode": "browse",
            "prefix": prefix,
            "limit": limit,
            "group_limit_policy": "per_source_group",
            "homographs": homograph_policy,
        },
        "sources": word_index_sources_payload(language_code, paths=paths)["sources"],
        "order": _browse_payload_order(language=language_code, source=source, prefix=prefix),
        "items": items,
        "groups": groups,
        "neighborhood": None,
        "pagination": {"next_cursor": None, "prev_cursor": None},
        "warnings": warnings,
    }


def word_index_neighborhood_payload(  # noqa: PLR0913
    language: str,
    query: str,
    *,
    source: str = "all",
    radius: int = 10,
    merge: str = "auto",
    paths: WordIndexPaths | None = None,
) -> dict[str, object]:
    paths = paths or WordIndexPaths.defaults()
    warnings: list[dict[str, str]] = []
    languages = _languages_for_request(language)
    merge_policy = _merge_policy(merge, source)
    neighborhoods: list[dict[str, object]] = []
    for source_id in _sources_for_request(source, languages):
        neighborhoods.extend(
            _source_neighborhoods(
                source_id=source_id,
                languages=languages,
                query=query,
                radius=radius,
                paths=paths,
                warnings=warnings,
            )
        )
    neighborhood: dict[str, object] | None
    if not neighborhoods:
        warnings.append(
            {
                "source": source,
                "message": f"no indexed neighborhood found for {language}:{query}",
            }
        )
        neighborhood = None
    elif merge_policy == "lexeme":
        if source.strip().lower() == "all":
            neighborhood = _integrated_language_native_neighborhood(
                neighborhoods,
                query=query,
                radius=radius,
                languages=languages,
                source=source,
                paths=paths,
                warnings=warnings,
            )
        else:
            neighborhood = _merged_lexeme_neighborhood(
                neighborhoods,
                query=query,
                radius=radius,
                languages=languages,
                source=source,
                paths=paths,
                warnings=warnings,
            )
    else:
        neighborhood = (
            neighborhoods[0]
            if len(neighborhoods) == 1
            else {
                "groups": neighborhoods,
                "order": _grouped_neighborhood_order_metadata(neighborhoods),
            }
        )
    return {
        "schema_version": WORD_INDEX_SCHEMA_VERSION,
        "request": {
            "language": language,
            "source": source,
            "mode": "neighborhood",
            "query": query,
            "radius": radius,
            "merge": merge_policy,
        },
        "sources": word_index_sources_payload(language, paths=paths)["sources"],
        "items": [],
        "neighborhood": neighborhood,
        "pagination": {"next_cursor": None, "prev_cursor": None},
        "warnings": warnings,
    }


def _source_neighborhoods(  # noqa: C901, PLR0913
    *,
    source_id: str,
    languages: Sequence[LanguageCode],
    query: str,
    radius: int,
    paths: WordIndexPaths,
    warnings: list[dict[str, str]],
) -> list[dict[str, object]]:
    neighborhoods: list[dict[str, object]] = []
    if source_id == "cdsl" and "san" in languages:
        neighborhoods.extend(
            _neighborhood_cdsl("mw", paths.cdsl_mw, query=query, radius=radius, warnings=warnings)
        )
        neighborhoods.extend(
            _neighborhood_cdsl(
                "ap90", paths.cdsl_ap90, query=query, radius=radius, warnings=warnings
            )
        )
    elif source_id == "dico" and "san" in languages:
        neighborhoods.extend(
            _neighborhood_dico(paths.dico, query=query, radius=radius, warnings=warnings)
        )
    elif source_id == "gaffiot" and "lat" in languages:
        neighborhoods.extend(
            _neighborhood_gaffiot(paths.gaffiot, query=query, radius=radius, warnings=warnings)
        )
    elif source_id == "lewis_1890" and "lat" in languages:
        neighborhoods.extend(
            _neighborhood_lewis_1890(
                paths.lewis_1890,
                query=query,
                radius=radius,
                warnings=warnings,
            )
        )
    elif source_id == "georges_1913" and "lat" in languages:
        neighborhoods.extend(
            _neighborhood_georges_1913(
                paths.georges_1913,
                query=query,
                radius=radius,
                warnings=warnings,
            )
        )
    elif source_id == "whitakers" and "lat" in languages:
        neighborhoods.extend(
            _neighborhood_whitakers(
                paths.whitakers,
                query=query,
                radius=radius,
                warnings=warnings,
            )
        )
    elif source_id == "diogenes":
        if "lat" in languages:
            neighborhoods.extend(
                _neighborhood_diogenes(
                    paths.diogenes_lat,
                    language="lat",
                    query=query,
                    radius=radius,
                    warnings=warnings,
                )
            )
        if "grc" in languages:
            neighborhoods.extend(
                _neighborhood_diogenes(
                    paths.diogenes_grc,
                    language="grc",
                    query=query,
                    radius=radius,
                    warnings=warnings,
                )
            )
    elif source_id == "bailly" and "grc" in languages:
        neighborhoods.extend(
            _neighborhood_bailly(paths.bailly, query=query, radius=radius, warnings=warnings)
        )
    elif source_id == "strongs_greek" and "grc" in languages:
        neighborhoods.extend(
            _neighborhood_strongs_greek(
                paths.strongs_greek, query=query, radius=radius, warnings=warnings
            )
        )
    return neighborhoods


def word_index_wheel_payload(
    language: str,
    *,
    source: str = "all",
    count: int = 12,
    seed: str | None = None,
    paths: WordIndexPaths | None = None,
) -> dict[str, object]:
    paths = paths or WordIndexPaths.defaults()
    warnings: list[dict[str, str]] = []
    items = _collect_wheel_items(
        languages=_languages_for_request(language),
        source=source,
        count=count,
        seed=seed or "",
        paths=paths,
        warnings=warnings,
    )
    seed_value = seed or ""
    ranked = sorted(items, key=lambda item: _wheel_sort_key(item, seed_value))
    cards = _wheel_lexeme_cards(ranked)
    selected = _interleave_wheel(cards, limit=count)
    return {
        "schema_version": WORD_INDEX_SCHEMA_VERSION,
        "request": {
            "language": language,
            "source": source,
            "mode": "wheel",
            "count": count,
            "seed": seed,
        },
        "sources": word_index_sources_payload(language, paths=paths)["sources"],
        "order": _wheel_payload_order(language=language, source=source, seed=seed_value),
        "items": selected,
        "neighborhood": None,
        "pagination": {"next_cursor": None, "prev_cursor": None},
        "warnings": warnings,
    }


def _collect_wheel_items(  # noqa: C901, PLR0913
    *,
    languages: Sequence[LanguageCode],
    source: str,
    count: int,
    seed: str,
    paths: WordIndexPaths,
    warnings: list[dict[str, str]],
) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    limit = max(count * 4, 25)
    for source_id in _sources_for_request(source, languages):
        if source_id == "cdsl" and "san" in languages:
            items.extend(
                _wheel_cdsl("mw", paths.cdsl_mw, seed=seed, limit=limit, warnings=warnings)
            )
            items.extend(
                _wheel_cdsl("ap90", paths.cdsl_ap90, seed=seed, limit=limit, warnings=warnings)
            )
        elif source_id == "dico" and "san" in languages:
            items.extend(_wheel_dico(paths.dico, seed=seed, limit=limit, warnings=warnings))
        elif source_id == "gaffiot" and "lat" in languages:
            items.extend(_wheel_gaffiot(paths.gaffiot, seed=seed, limit=limit, warnings=warnings))
        elif source_id == "lewis_1890" and "lat" in languages:
            items.extend(
                _wheel_lewis_1890(paths.lewis_1890, seed=seed, limit=limit, warnings=warnings)
            )
        elif source_id == "georges_1913" and "lat" in languages:
            items.extend(
                _wheel_georges_1913(paths.georges_1913, seed=seed, limit=limit, warnings=warnings)
            )
        elif source_id == "whitakers" and "lat" in languages:
            items.extend(
                _wheel_whitakers(paths.whitakers, seed=seed, limit=limit, warnings=warnings)
            )
        elif source_id == "diogenes":
            if "lat" in languages:
                items.extend(
                    _wheel_diogenes(
                        paths.diogenes_lat,
                        language="lat",
                        seed=seed,
                        limit=limit,
                        warnings=warnings,
                    )
                )
            if "grc" in languages:
                items.extend(
                    _wheel_diogenes(
                        paths.diogenes_grc,
                        language="grc",
                        seed=seed,
                        limit=limit,
                        warnings=warnings,
                    )
                )
        elif source_id == "bailly" and "grc" in languages:
            items.extend(_wheel_bailly(paths.bailly, seed=seed, limit=limit, warnings=warnings))
        elif source_id == "strongs_greek" and "grc" in languages:
            items.extend(
                _wheel_strongs_greek(paths.strongs_greek, seed=seed, limit=limit, warnings=warnings)
            )
    return items


def _section_payload(
    spec: Mapping[str, str],
    *,
    language: LanguageCode,
    source: str,
    paths: WordIndexPaths,
    warnings: list[dict[str, str]],
) -> dict[str, object]:
    prefix = spec["prefix"]
    anchor_query = spec.get("source_prefix", prefix)
    languages: tuple[LanguageCode, ...] = (language,)
    items = _collect_items(
        languages=languages,
        source=source,
        prefix=anchor_query,
        limit=1,
        paths=paths,
        warnings=warnings,
    )
    anchor = _section_anchor(items[0], fallback_query=anchor_query) if items else None
    if anchor and spec.get("source_prefix"):
        anchor["query"] = anchor_query
    return {
        "id": spec["id"],
        "label": spec["label"],
        "transliteration": spec["transliteration"],
        "group_label": spec["group_label"],
        "order_key": spec["order_key"],
        "anchor": anchor
        or {
            "language": language,
            "source": source,
            "dictionary": "",
            "query": anchor_query,
            "canonical_key": anchor_query,
            "source_order_key": "",
        },
        "available": bool(items),
        "entry_count": 1 if items else 0,
    }


def _section_anchor(item: Mapping[str, object], *, fallback_query: str) -> dict[str, object]:
    return {
        "language": item.get("language") or "",
        "source": item.get("source") or "",
        "dictionary": item.get("dictionary") or "",
        "query": fallback_query,
        "canonical_key": item.get("canonical_key") or "",
        "source_order_key": item.get("source_order_key") or "",
        "lexeme_id": item.get("lexeme_id") or "",
        "index_entry_id": item.get("index_entry_id") or "",
        "source_order_id": item.get("source_order_id") or "",
        "display": item.get("display") or {},
        "order": item.get("order") or {},
    }


def _sections_order_metadata(language: LanguageCode, source: str) -> dict[str, str]:
    if language == "san":
        return {
            "policy": "language-native",
            "label": "Sanskrit varnamala sections",
            "collation": "sa-varga",
            "key": "san:varnamala",
            "display_key": "अ आ इ ई ... क ख ग घ ङ ...",
            "explanation": (
                "Section anchors follow a Sanskrit varnamala rail. Open a section with "
                "word-index nearby to use source-local dictionary order."
            ),
        }
    if language == "grc":
        return {
            "policy": "language-native",
            "label": "Greek alphabet sections",
            "collation": "grc-lexical",
            "key": "grc:alphabet",
            "display_key": "Α Β Γ Δ ...",
            "explanation": (
                f"Section anchors for source={source} follow Greek alphabet sections and "
                "preserve source-local anchors when available."
            ),
        }
    return {
        "policy": "language-native",
        "label": "Latin alphabet sections",
        "collation": "lat-lexical",
        "key": "lat:alphabet",
        "display_key": "A B C D ...",
        "explanation": (
            f"Section anchors for source={source} follow conventional Latin alphabet sections."
        ),
    }


def _section_specs(language: LanguageCode) -> list[dict[str, str]]:
    if language == "san":
        return _sanskrit_section_specs()
    if language == "grc":
        return _greek_section_specs()
    return _simple_section_specs(
        language="lat",
        group_label="Latin",
        labels=[(chr(code), chr(code).lower()) for code in range(ord("A"), ord("Z") + 1)],
    )


def _simple_section_specs(
    *,
    language: str,
    group_label: str,
    labels: Sequence[tuple[str, str]],
) -> list[dict[str, str]]:
    return [
        {
            "id": f"{language}:{transliteration}",
            "label": label,
            "transliteration": transliteration,
            "prefix": transliteration,
            "group_label": group_label,
            "order_key": f"{index:03d}",
        }
        for index, (label, transliteration) in enumerate(labels, start=1)
    ]


def _greek_section_specs() -> list[dict[str, str]]:
    labels = [
        ("Α", "a", ""),
        ("Β", "b", ""),
        ("Γ", "g", ""),
        ("Δ", "d", ""),
        ("Ε", "e", ""),
        ("Ζ", "z", ""),
        ("Η", "h", ""),
        ("Θ", "th", "q"),
        ("Ι", "i", ""),
        ("Κ", "k", ""),
        ("Λ", "l", ""),
        ("Μ", "m", ""),
        ("Ν", "n", ""),
        ("Ξ", "x", "c"),
        ("Ο", "o", ""),
        ("Π", "p", ""),
        ("Ρ", "r", ""),
        ("Σ", "s", ""),
        ("Τ", "t", ""),
        ("Υ", "u", ""),
        ("Φ", "ph", "f"),
        ("Χ", "ch", "x"),
        ("Ψ", "ps", "y"),
        ("Ω", "w", "ō"),
    ]
    specs = []
    for index, (label, transliteration, source_prefix) in enumerate(labels, start=1):
        spec = {
            "id": f"grc:{transliteration}",
            "label": label,
            "transliteration": transliteration,
            "prefix": transliteration,
            "group_label": "Greek",
            "order_key": f"{index:03d}",
        }
        if source_prefix:
            spec["source_prefix"] = source_prefix
        specs.append(spec)
    return specs


def _sanskrit_section_specs() -> list[dict[str, str]]:
    groups: list[tuple[str, list[tuple[str, str, str, str]]]] = [
        (
            "Vowels",
            [
                ("अ", "a", "a", "a"),
                ("आ", "ā", "aa", "A"),
                ("इ", "i", "i", "i"),
                ("ई", "ī", "ii", "I"),
                ("उ", "u", "u", "u"),
                ("ऊ", "ū", "uu", "U"),
                ("ऋ", "ṛ", "r", "f"),
                ("ॠ", "ṝ", "rr", "F"),
                ("ऌ", "ḷ", "l", "x"),
                ("ॡ", "ḹ", "ll", "X"),
                ("ए", "e", "e", "e"),
                ("ऐ", "ai", "ai", "E"),
                ("ओ", "o", "o", "o"),
                ("औ", "au", "au", "O"),
                ("अं", "ṃ", "anusvara", "aM"),
                ("अः", "ḥ", "visarga", "aH"),
            ],
        ),
        (
            "Velars",
            [
                ("क", "ka", "ka", "k"),
                ("ख", "kha", "kha", "K"),
                ("ग", "ga", "ga", "g"),
                ("घ", "gha", "gha", "G"),
                ("ङ", "ṅa", "nga", "N"),
            ],
        ),
        (
            "Palatals",
            [
                ("च", "ca", "ca", "c"),
                ("छ", "cha", "cha", "C"),
                ("ज", "ja", "ja", "j"),
                ("झ", "jha", "jha", "J"),
                ("ञ", "ña", "nya", "Y"),
            ],
        ),
        (
            "Retroflexes",
            [
                ("ट", "ṭa", "tta", "w"),
                ("ठ", "ṭha", "ttha", "W"),
                ("ड", "ḍa", "dda", "q"),
                ("ढ", "ḍha", "ddha", "Q"),
                ("ण", "ṇa", "nna", "R"),
            ],
        ),
        (
            "Dentals",
            [
                ("त", "ta", "ta", "t"),
                ("थ", "tha", "tha", "T"),
                ("द", "da", "da", "d"),
                ("ध", "dha", "dha", "D"),
                ("न", "na", "na", "n"),
            ],
        ),
        (
            "Labials",
            [
                ("प", "pa", "pa", "p"),
                ("फ", "pha", "pha", "P"),
                ("ब", "ba", "ba", "b"),
                ("भ", "bha", "bha", "B"),
                ("म", "ma", "ma", "m"),
            ],
        ),
        (
            "Semivowels",
            [
                ("य", "ya", "ya", "y"),
                ("र", "ra", "ra", "r"),
                ("ल", "la", "la", "l"),
                ("व", "va", "va", "v"),
            ],
        ),
        ("Sibilants", [("श", "śa", "sha", "S"), ("ष", "ṣa", "ssa", "z"), ("स", "sa", "sa", "s")]),
        ("Aspirate", [("ह", "ha", "ha", "h")]),
        (
            "Conjuncts",
            [("क्ष", "kṣa", "ksha", "kz"), ("त्र", "tra", "tra", "tr"), ("ज्ञ", "jña", "jnya", "jY")],
        ),
    ]
    specs: list[dict[str, str]] = []
    index = 1
    for group_label, labels in groups:
        group_id = _id_component(group_label)
        for label, transliteration, id_key, source_prefix in labels:
            specs.append(
                {
                    "id": f"san:{group_id}:{_id_component(id_key)}",
                    "label": label,
                    "transliteration": transliteration,
                    "prefix": id_key,
                    "source_prefix": source_prefix,
                    "group_label": group_label,
                    "order_key": f"{index:03d}",
                }
            )
            index += 1
    return specs


def _languages_for_request(language: str) -> list[LanguageCode]:
    if language.strip().lower() == "all":
        return ["lat", "grc", "san"]
    canonical = canonical_language(language)
    if canonical is None:
        supported = "|".join(["all", *LANGUAGE_LABELS])
        raise ValueError(f"Unsupported word-index language '{language}'. Use {supported}.")
    return [canonical]


def _sources_for_request(source: str, languages: Sequence[LanguageCode]) -> list[str]:
    normalized = source.strip().lower()
    if normalized == "all":
        sources: list[str] = []
        if "san" in languages:
            sources.extend(["cdsl", "dico"])
        if "lat" in languages:
            sources.append("gaffiot")
            sources.append("lewis_1890")
            sources.append("georges_1913")
            sources.append("whitakers")
        if "grc" in languages or "lat" in languages:
            sources.append("diogenes")
        if "grc" in languages:
            sources.append("bailly")
            sources.append("strongs_greek")
        return list(dict.fromkeys(sources))
    if normalized not in _SOURCE_ORDER:
        supported = "|".join(["all", *_SOURCE_ORDER])
        raise ValueError(f"Unsupported word-index source '{source}'. Use {supported}.")
    return [normalized]


def _merge_policy(merge: str, source: str) -> WordIndexMerge:
    normalized = merge.strip().lower()
    if normalized not in {"auto", "none", "lexeme"}:
        supported = "|".join(["auto", "none", "lexeme"])
        raise ValueError(f"Unsupported word-index merge policy '{merge}'. Use {supported}.")
    if normalized == "auto":
        return "lexeme" if source.strip().lower() == "all" else "none"
    return cast(WordIndexMerge, normalized)


def _collect_items(  # noqa: C901, PLR0913
    *,
    languages: Sequence[LanguageCode],
    source: str,
    prefix: str,
    limit: int,
    paths: WordIndexPaths,
    warnings: list[dict[str, str]],
) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for source_id in _sources_for_request(source, languages):
        if source_id == "cdsl" and "san" in languages:
            items.extend(
                _list_cdsl("mw", paths.cdsl_mw, prefix=prefix, limit=limit, warnings=warnings)
            )
            items.extend(
                _list_cdsl("ap90", paths.cdsl_ap90, prefix=prefix, limit=limit, warnings=warnings)
            )
        elif source_id == "dico" and "san" in languages:
            items.extend(_list_dico(paths.dico, prefix=prefix, limit=limit, warnings=warnings))
        elif source_id == "gaffiot" and "lat" in languages:
            items.extend(
                _list_gaffiot(paths.gaffiot, prefix=prefix, limit=limit, warnings=warnings)
            )
        elif source_id == "lewis_1890" and "lat" in languages:
            items.extend(
                _list_lewis_1890(paths.lewis_1890, prefix=prefix, limit=limit, warnings=warnings)
            )
        elif source_id == "georges_1913" and "lat" in languages:
            items.extend(
                _list_georges_1913(
                    paths.georges_1913, prefix=prefix, limit=limit, warnings=warnings
                )
            )
        elif source_id == "whitakers" and "lat" in languages:
            items.extend(
                _list_whitakers(paths.whitakers, prefix=prefix, limit=limit, warnings=warnings)
            )
        elif source_id == "diogenes":
            if "lat" in languages:
                items.extend(
                    _list_diogenes(
                        paths.diogenes_lat,
                        language="lat",
                        prefix=prefix,
                        limit=limit,
                        warnings=warnings,
                    )
                )
            if "grc" in languages:
                items.extend(
                    _list_diogenes(
                        paths.diogenes_grc,
                        language="grc",
                        prefix=prefix,
                        limit=limit,
                        warnings=warnings,
                    )
                )
        elif source_id == "bailly" and "grc" in languages:
            items.extend(_list_bailly(paths.bailly, prefix=prefix, limit=limit, warnings=warnings))
        elif source_id == "strongs_greek" and "grc" in languages:
            items.extend(
                _list_strongs_greek(
                    paths.strongs_greek, prefix=prefix, limit=limit, warnings=warnings
                )
            )
    items.sort(key=_item_order_key)
    return items


def _browse_groups(  # noqa: C901, PLR0913
    *,
    language: LanguageCode,
    source: str,
    prefix: str,
    limit: int,
    homographs: WordIndexHomographs,
    paths: WordIndexPaths,
    warnings: list[dict[str, str]],
) -> list[dict[str, object]]:
    groups: list[dict[str, object]] = []
    for source_id in _sources_for_request(source, (language,)):
        if source_id == "cdsl" and language == "san":
            groups.append(
                _browse_group(
                    language=language,
                    source="cdsl",
                    dictionary="mw",
                    prefix=prefix,
                    items=_list_cdsl(
                        "mw", paths.cdsl_mw, prefix=prefix, limit=limit, warnings=warnings
                    ),
                    homographs=homographs,
                )
            )
            groups.append(
                _browse_group(
                    language=language,
                    source="cdsl",
                    dictionary="ap90",
                    prefix=prefix,
                    items=_list_cdsl(
                        "ap90", paths.cdsl_ap90, prefix=prefix, limit=limit, warnings=warnings
                    ),
                    homographs=homographs,
                )
            )
        elif source_id == "dico" and language == "san":
            groups.append(
                _browse_group(
                    language=language,
                    source="dico",
                    dictionary="dico",
                    prefix=prefix,
                    items=_list_dico(paths.dico, prefix=prefix, limit=limit, warnings=warnings),
                    homographs=homographs,
                )
            )
        elif source_id == "gaffiot" and language == "lat":
            groups.append(
                _browse_group(
                    language=language,
                    source="gaffiot",
                    dictionary="gaffiot",
                    prefix=prefix,
                    items=_list_gaffiot(
                        paths.gaffiot, prefix=prefix, limit=limit, warnings=warnings
                    ),
                    homographs=homographs,
                )
            )
        elif source_id == "lewis_1890" and language == "lat":
            groups.append(
                _browse_group(
                    language=language,
                    source="lewis_1890",
                    dictionary="lewis_1890",
                    prefix=prefix,
                    items=_list_lewis_1890(
                        paths.lewis_1890, prefix=prefix, limit=limit, warnings=warnings
                    ),
                    homographs=homographs,
                )
            )
        elif source_id == "georges_1913" and language == "lat":
            groups.append(
                _browse_group(
                    language=language,
                    source="georges_1913",
                    dictionary="georges_1913",
                    prefix=prefix,
                    items=_list_georges_1913(
                        paths.georges_1913, prefix=prefix, limit=limit, warnings=warnings
                    ),
                    homographs=homographs,
                )
            )
        elif source_id == "whitakers" and language == "lat":
            groups.append(
                _browse_group(
                    language=language,
                    source="whitakers",
                    dictionary="whitakers",
                    prefix=prefix,
                    items=_list_whitakers(
                        paths.whitakers, prefix=prefix, limit=limit, warnings=warnings
                    ),
                    homographs=homographs,
                )
            )
        elif source_id == "diogenes":
            if language == "lat":
                groups.append(
                    _browse_group(
                        language=language,
                        source="diogenes",
                        dictionary="lewis_short",
                        prefix=prefix,
                        items=_list_diogenes(
                            paths.diogenes_lat,
                            language="lat",
                            prefix=prefix,
                            limit=limit,
                            warnings=warnings,
                        ),
                        homographs=homographs,
                    )
                )
            if language == "grc":
                groups.append(
                    _browse_group(
                        language=language,
                        source="diogenes",
                        dictionary="lsj",
                        prefix=prefix,
                        items=_list_diogenes(
                            paths.diogenes_grc,
                            language="grc",
                            prefix=prefix,
                            limit=limit,
                            warnings=warnings,
                        ),
                        homographs=homographs,
                    )
                )
        elif source_id == "bailly" and language == "grc":
            groups.append(
                _browse_group(
                    language=language,
                    source="bailly",
                    dictionary="bailly",
                    prefix=prefix,
                    items=_list_bailly(paths.bailly, prefix=prefix, limit=limit, warnings=warnings),
                    homographs=homographs,
                )
            )
        elif source_id == "strongs_greek" and language == "grc":
            groups.append(
                _browse_group(
                    language=language,
                    source="strongs_greek",
                    dictionary="strongs_greek",
                    prefix=prefix,
                    items=_list_strongs_greek(
                        paths.strongs_greek, prefix=prefix, limit=limit, warnings=warnings
                    ),
                    homographs=homographs,
                )
            )
    return [group for group in groups if cast(list[object], group["items"])]


def _browse_group(  # noqa: PLR0913
    *,
    language: LanguageCode,
    source: str,
    dictionary: str,
    prefix: str,
    items: list[dict[str, object]],
    homographs: WordIndexHomographs,
) -> dict[str, object]:
    grouped_items = _group_adjacent_homographs(items) if homographs == "grouped" else items
    return {
        "language": language,
        "source": source,
        "dictionary": dictionary,
        "prefix": prefix,
        "order": _browse_group_order_metadata(
            language=language,
            source=source,
            dictionary=dictionary,
            prefix=prefix,
        ),
        "items": grouped_items,
        "entry_count": len(grouped_items),
        "source_entry_count": len(items),
        "homograph_policy": ("adjacent-source-homographs" if homographs == "grouped" else "raw"),
        "limit_policy": "per_source_group",
    }


def _homograph_policy(value: str) -> WordIndexHomographs:
    normalized = value.strip().lower()
    if normalized in {"grouped", "raw"}:
        return cast(WordIndexHomographs, normalized)
    raise ValueError("homographs must be one of: grouped, raw.")


def _group_adjacent_homographs(items: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    groups: list[list[dict[str, object]]] = []
    current: list[dict[str, object]] = []
    current_key: tuple[str, str, str] | None = None
    for item in items:
        key = _homograph_key(item)
        if current and key != current_key:
            groups.append(current)
            current = []
        current.append(item)
        current_key = key
    if current:
        groups.append(current)
    return [_homograph_card(group) for group in groups]


def _homograph_key(item: Mapping[str, object]) -> tuple[str, str, str]:
    display = item.get("display")
    display_map = (
        cast(Mapping[str, object], display)
        if isinstance(display, Mapping)
        else cast(Mapping[str, object], {})
    )
    return (
        str(item.get("canonical_key") or ""),
        str(display_map.get("primary") or item.get("canonical_name") or ""),
        str(display_map.get("transliteration") or item.get("lookup") or ""),
    )


def _homograph_card(rows: Sequence[dict[str, object]]) -> dict[str, object]:
    if len(rows) == 1:
        return rows[0]
    primary = dict(rows[0])
    source_entries = [_source_entry_summary(row) for row in rows]
    ids = dict(cast(Mapping[str, object], primary.get("ids") or {}))
    ids["source_entries"] = [entry["index_entry_id"] for entry in source_entries]
    primary["ids"] = ids
    primary["source_entries"] = source_entries
    primary["source_entry_count"] = len(source_entries)
    primary["homograph_count"] = len(source_entries)
    primary["homograph_policy"] = "adjacent-source-homographs"
    return primary


def _cross_dictionary_browse_items(
    browse_groups: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, str], list[dict[str, object]]] = {}
    order: list[tuple[str, str, str]] = []
    for browse_group in browse_groups:
        items = browse_group.get("items")
        if not isinstance(items, Sequence) or isinstance(items, (str, bytes)):
            continue
        for item in items:
            if not isinstance(item, Mapping):
                continue
            item_dict = dict(cast(Mapping[str, object], item))
            key = _homograph_key(item_dict)
            if key not in grouped:
                grouped[key] = []
                order.append(key)
            grouped[key].append(item_dict)
    return [_cross_dictionary_browse_card(grouped[key]) for key in order]


def _cross_dictionary_browse_card(rows: Sequence[dict[str, object]]) -> dict[str, object]:
    primary = dict(rows[0])
    source_entries = [entry for row in rows for entry in _browse_card_source_entries(row)]
    source_counts = _source_counts(source_entries)
    sources = [
        {"source": count["source"], "dictionary": count["dictionary"]} for count in source_counts
    ]
    ids = dict(cast(Mapping[str, object], primary.get("ids") or {}))
    ids["source_entries"] = [entry["index_entry_id"] for entry in source_entries]
    primary["ids"] = ids
    primary["source_entries"] = source_entries
    primary["source_counts"] = source_counts
    primary["sources"] = sources
    primary["source_count"] = len(sources)
    primary["source_entry_count"] = len(source_entries)
    primary["homograph_count"] = len(source_entries)
    primary["homograph_policy"] = "cross-dictionary-homographs"
    primary["order"] = _cross_dictionary_browse_order_metadata(primary)
    return primary


def _browse_card_source_entries(row: Mapping[str, object]) -> list[dict[str, object]]:
    entries = row.get("source_entries")
    if isinstance(entries, Sequence) and not isinstance(entries, (str, bytes)):
        return [
            dict(cast(Mapping[str, object], entry))
            for entry in entries
            if isinstance(entry, Mapping)
        ]
    return [_source_entry_summary(row)]


def _source_counts(source_entries: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    counts: dict[tuple[str, str], int] = {}
    order: list[tuple[str, str]] = []
    for entry in source_entries:
        key = (str(entry.get("source") or ""), str(entry.get("dictionary") or ""))
        if key not in counts:
            counts[key] = 0
            order.append(key)
        counts[key] += 1
    return [
        {"source": source, "dictionary": dictionary, "count": counts[(source, dictionary)]}
        for source, dictionary in order
    ]


def _list_cdsl(
    dict_id: str,
    path: Path,
    *,
    prefix: str,
    limit: int,
    warnings: list[dict[str, str]],
) -> list[dict[str, object]]:
    if not path.exists():
        _warn_missing(warnings, "cdsl", path)
        return []
    params: list[object] = []
    where = "WHERE h.dict_id = ? AND h.is_primary = true"
    params.append(dict_id.upper())
    exact_order_sql = ""
    exact_order_params: list[object] = []
    if prefix:
        prefix_sql, prefix_params = _cdsl_prefix_predicate(prefix)
        exact_order_sql, exact_order_params = _cdsl_exact_prefix_predicate(prefix)
        where += f" AND ({prefix_sql})"
        params.extend(prefix_params)
    order_prefix = f"CASE WHEN {exact_order_sql} THEN 0 ELSE 1 END," if exact_order_sql else ""
    sql = f"""
        SELECT h.key, h.key_normalized, h.lnum, h.hom, h.search_key, e.page_ref
        FROM headwords h
        JOIN entries e ON e.dict_id = h.dict_id AND e.lnum = h.lnum
        {where}
        ORDER BY {order_prefix} h.key_normalized, h.lnum, h.hom NULLS FIRST
    """
    params.extend(exact_order_params)
    if limit > 0:
        sql += " LIMIT ?"
        params.append(limit)
    try:
        with connect_duckdb_ro(path) as conn:
            rows = conn.execute(sql, params).fetchall()
    except Exception as exc:  # noqa: BLE001
        _warn_error(warnings, "cdsl", path, exc)
        return []
    return [_cdsl_item(dict_id.lower(), row) for row in rows]


def _neighborhood_cdsl(
    dict_id: str,
    path: Path,
    *,
    query: str,
    radius: int,
    warnings: list[dict[str, str]],
) -> list[dict[str, object]]:
    if not path.exists():
        _warn_missing(warnings, "cdsl", path)
        return []
    keys = _query_keys(query)
    section_prefix = _sanskrit_section_source_prefix(query)
    if not keys and section_prefix is None:
        return []
    try:
        with connect_duckdb_ro(path) as conn:
            if section_prefix is not None:
                prefix_sql, prefix_params = _cdsl_exact_prefix_predicate(section_prefix)
                anchor_rows = conn.execute(
                    f"""
                    SELECT h.key, h.key_normalized, h.lnum, h.hom, h.search_key, e.page_ref
                    FROM headwords h
                    JOIN entries e ON e.dict_id = h.dict_id AND e.lnum = h.lnum
                    WHERE h.dict_id = ? AND h.is_primary = true
                      AND ({prefix_sql})
                    ORDER BY h.key_normalized, h.lnum, h.hom NULLS FIRST
                    LIMIT 50
                    """,
                    [dict_id.upper(), *prefix_params],
                ).fetchall()
            else:
                anchor_rows = conn.execute(
                    f"""
                    SELECT h.key, h.key_normalized, h.lnum, h.hom, h.search_key, e.page_ref
                    FROM headwords h
                    JOIN entries e ON e.dict_id = h.dict_id AND e.lnum = h.lnum
                    WHERE h.dict_id = ? AND h.is_primary = true
                      AND (
                        lower(h.key_normalized) IN ({_placeholders(keys)})
                        OR lower(h.search_key) IN ({_placeholders(keys)})
                        OR lower(h.key) IN ({_placeholders(keys)})
                      )
                    ORDER BY h.key_normalized, h.lnum, h.hom NULLS FIRST
                    LIMIT 50
                    """,
                    [dict_id.upper(), *keys, *keys, *keys],
                ).fetchall()
            anchor_items = [_cdsl_item(dict_id.lower(), row) for row in anchor_rows]
            anchor = anchor_items[0] if section_prefix is not None and anchor_items else None
            if anchor is None:
                anchor = _best_anchor(anchor_items, query)
            if anchor is None:
                return []
            metadata = cast(Mapping[str, object], anchor.get("metadata") or {})
            anchor_lnum = _as_float(metadata.get("lnum"))
            before_rows = conn.execute(
                """
                SELECT h.key, h.key_normalized, h.lnum, h.hom, h.search_key, e.page_ref
                FROM headwords h
                JOIN entries e ON e.dict_id = h.dict_id AND e.lnum = h.lnum
                WHERE h.dict_id = ? AND h.is_primary = true
                  AND h.lnum < ?
                ORDER BY h.lnum DESC, h.hom DESC NULLS LAST
                LIMIT ?
                """,
                [dict_id.upper(), anchor_lnum, radius],
            ).fetchall()
            after_rows = conn.execute(
                """
                SELECT h.key, h.key_normalized, h.lnum, h.hom, h.search_key, e.page_ref
                FROM headwords h
                JOIN entries e ON e.dict_id = h.dict_id AND e.lnum = h.lnum
                WHERE h.dict_id = ? AND h.is_primary = true
                  AND h.lnum > ?
                ORDER BY h.lnum, h.hom NULLS FIRST
                LIMIT ?
                """,
                [dict_id.upper(), anchor_lnum, radius],
            ).fetchall()
    except Exception as exc:  # noqa: BLE001
        _warn_error(warnings, "cdsl", path, exc)
        return []
    before = [_cdsl_item(dict_id.lower(), row) for row in reversed(before_rows)]
    after = [_cdsl_item(dict_id.lower(), row) for row in after_rows]
    return [_neighborhood(anchor, before=before, after=after, radius=radius, query=query)]


def _wheel_cdsl(
    dict_id: str,
    path: Path,
    *,
    seed: str,
    limit: int,
    warnings: list[dict[str, str]],
) -> list[dict[str, object]]:
    if not path.exists():
        _warn_missing(warnings, "cdsl", path)
        return []
    try:
        with connect_duckdb_ro(path) as conn:
            rows = conn.execute(
                """
                SELECT h.key, h.key_normalized, h.lnum, h.hom, h.search_key, e.page_ref
                FROM headwords h
                JOIN entries e ON e.dict_id = h.dict_id AND e.lnum = h.lnum
                WHERE h.dict_id = ? AND h.is_primary = true
                ORDER BY hash(h.key_normalized || ?), h.key_normalized, h.lnum
                LIMIT ?
                """,
                [dict_id.upper(), seed, limit],
            ).fetchall()
    except Exception as exc:  # noqa: BLE001
        _warn_error(warnings, "cdsl", path, exc)
        return []
    return [_cdsl_item(dict_id.lower(), row) for row in rows]


def _list_dico(
    path: Path,
    *,
    prefix: str,
    limit: int,
    warnings: list[dict[str, str]],
) -> list[dict[str, object]]:
    if not path.exists():
        _warn_missing(warnings, "dico", path)
        return []
    params: list[object] = []
    where = ""
    if prefix:
        norm = normalize_dico_headword(prefix)
        where = "WHERE headword_norm LIKE ? OR lower(headword_roma) LIKE ? OR headword_deva LIKE ?"
        params.extend([f"{norm}%", f"{norm}%", f"{prefix}%"])
    sql = f"""
        SELECT entry_id, occurrence, headword_deva, headword_roma, headword_norm, source_page
        FROM entries_fr
        {where}
        ORDER BY headword_norm, source_page, entry_id, occurrence
    """
    if limit > 0:
        sql += " LIMIT ?"
        params.append(limit)
    try:
        with connect_duckdb_ro(path) as conn:
            rows = conn.execute(sql, params).fetchall()
    except Exception as exc:  # noqa: BLE001
        _warn_error(warnings, "dico", path, exc)
        return []
    return [_dico_item(row) for row in rows]


def _neighborhood_dico(
    path: Path,
    *,
    query: str,
    radius: int,
    warnings: list[dict[str, str]],
) -> list[dict[str, object]]:
    if not path.exists():
        _warn_missing(warnings, "dico", path)
        return []
    keys = _query_keys(query)
    if not keys:
        return []
    try:
        with connect_duckdb_ro(path) as conn:
            anchor_rows = conn.execute(
                f"""
                SELECT entry_id, occurrence, headword_deva, headword_roma, headword_norm,
                       source_page
                FROM entries_fr
                WHERE lower(headword_norm) IN ({_placeholders(keys)})
                   OR lower(headword_roma) IN ({_placeholders(keys)})
                   OR replace(lower(headword_norm), '.', '') IN ({_placeholders(keys)})
                   OR headword_deva = ?
                ORDER BY headword_norm, source_page, entry_id, occurrence
                LIMIT 50
                """,
                [*keys, *keys, *keys, query],
            ).fetchall()
            anchor = _best_anchor([_dico_item(row) for row in anchor_rows], query)
            if anchor is None:
                return []
            metadata = cast(Mapping[str, object], anchor.get("metadata") or {})
            anchor_sort = str(anchor["sort_key"])
            source_page = str(metadata.get("source_page") or "")
            entry_id = str(metadata.get("entry_id") or "")
            occurrence = _as_int(metadata.get("occurrence"))
            before_rows = conn.execute(
                """
                SELECT entry_id, occurrence, headword_deva, headword_roma, headword_norm,
                       source_page
                FROM entries_fr
                WHERE headword_norm < ?
                   OR (
                     headword_norm = ?
                     AND (
                       source_page < ?
                       OR (source_page = ? AND entry_id < ?)
                       OR (source_page = ? AND entry_id = ? AND occurrence < ?)
                     )
                   )
                ORDER BY headword_norm DESC, source_page DESC, entry_id DESC, occurrence DESC
                LIMIT ?
                """,
                [
                    anchor_sort,
                    anchor_sort,
                    source_page,
                    source_page,
                    entry_id,
                    source_page,
                    entry_id,
                    occurrence,
                    radius,
                ],
            ).fetchall()
            after_rows = conn.execute(
                """
                SELECT entry_id, occurrence, headword_deva, headword_roma, headword_norm,
                       source_page
                FROM entries_fr
                WHERE headword_norm > ?
                   OR (
                     headword_norm = ?
                     AND (
                       source_page > ?
                       OR (source_page = ? AND entry_id > ?)
                       OR (source_page = ? AND entry_id = ? AND occurrence > ?)
                     )
                   )
                ORDER BY headword_norm, source_page, entry_id, occurrence
                LIMIT ?
                """,
                [
                    anchor_sort,
                    anchor_sort,
                    source_page,
                    source_page,
                    entry_id,
                    source_page,
                    entry_id,
                    occurrence,
                    radius,
                ],
            ).fetchall()
    except Exception as exc:  # noqa: BLE001
        _warn_error(warnings, "dico", path, exc)
        return []
    before = [_dico_item(row) for row in reversed(before_rows)]
    after = [_dico_item(row) for row in after_rows]
    return [_neighborhood(anchor, before=before, after=after, radius=radius, query=query)]


def _wheel_dico(
    path: Path,
    *,
    seed: str,
    limit: int,
    warnings: list[dict[str, str]],
) -> list[dict[str, object]]:
    if not path.exists():
        _warn_missing(warnings, "dico", path)
        return []
    try:
        with connect_duckdb_ro(path) as conn:
            rows = conn.execute(
                """
                SELECT
                    entry_id, occurrence, headword_deva, headword_roma,
                    headword_norm, source_page
                FROM entries_fr
                ORDER BY hash(headword_norm || ?), headword_norm, source_page, entry_id, occurrence
                LIMIT ?
                """,
                [seed, limit],
            ).fetchall()
    except Exception as exc:  # noqa: BLE001
        _warn_error(warnings, "dico", path, exc)
        return []
    return [_dico_item(row) for row in rows]


def _list_gaffiot(
    path: Path,
    *,
    prefix: str,
    limit: int,
    warnings: list[dict[str, str]],
) -> list[dict[str, object]]:
    if not path.exists():
        _warn_missing(warnings, "gaffiot", path)
        return []
    params: list[object] = []
    where = ""
    if prefix:
        norm = normalize_gaffiot_headword(prefix)
        where = "WHERE headword_norm LIKE ? OR lower(headword_raw) LIKE ?"
        params.extend([f"{norm}%", f"{norm}%"])
    sql = f"""
        SELECT entry_id, headword_raw, headword_norm, variant_num
        FROM entries_fr
        {where}
        ORDER BY headword_norm, entry_id
    """
    if limit > 0:
        sql += " LIMIT ?"
        params.append(limit)
    try:
        with connect_duckdb_ro(path) as conn:
            rows = conn.execute(sql, params).fetchall()
    except Exception as exc:  # noqa: BLE001
        _warn_error(warnings, "gaffiot", path, exc)
        return []
    return [_gaffiot_item(row) for row in rows]


def _neighborhood_gaffiot(
    path: Path,
    *,
    query: str,
    radius: int,
    warnings: list[dict[str, str]],
) -> list[dict[str, object]]:
    if not path.exists():
        _warn_missing(warnings, "gaffiot", path)
        return []
    keys = _query_keys(query)
    if not keys:
        return []
    try:
        with connect_duckdb_ro(path) as conn:
            anchor_rows = conn.execute(
                f"""
                SELECT entry_id, headword_raw, headword_norm, variant_num
                FROM entries_fr
                WHERE lower(headword_norm) IN ({_placeholders(keys)})
                   OR lower(headword_raw) IN ({_placeholders(keys)})
                ORDER BY headword_norm, entry_id
                LIMIT 50
                """,
                [*keys, *keys],
            ).fetchall()
            anchor = _best_anchor([_gaffiot_item(row) for row in anchor_rows], query)
            if anchor is None:
                return []
            metadata = cast(Mapping[str, object], anchor.get("metadata") or {})
            anchor_sort = str(anchor["sort_key"])
            entry_id = str(metadata.get("entry_id") or "")
            before_rows = conn.execute(
                """
                SELECT entry_id, headword_raw, headword_norm, variant_num
                FROM entries_fr
                WHERE headword_norm < ? OR (headword_norm = ? AND entry_id < ?)
                ORDER BY headword_norm DESC, entry_id DESC
                LIMIT ?
                """,
                [anchor_sort, anchor_sort, entry_id, radius],
            ).fetchall()
            after_rows = conn.execute(
                """
                SELECT entry_id, headword_raw, headword_norm, variant_num
                FROM entries_fr
                WHERE headword_norm > ? OR (headword_norm = ? AND entry_id > ?)
                ORDER BY headword_norm, entry_id
                LIMIT ?
                """,
                [anchor_sort, anchor_sort, entry_id, radius],
            ).fetchall()
    except Exception as exc:  # noqa: BLE001
        _warn_error(warnings, "gaffiot", path, exc)
        return []
    before = [_gaffiot_item(row) for row in reversed(before_rows)]
    after = [_gaffiot_item(row) for row in after_rows]
    return [_neighborhood(anchor, before=before, after=after, radius=radius, query=query)]


def _wheel_gaffiot(
    path: Path,
    *,
    seed: str,
    limit: int,
    warnings: list[dict[str, str]],
) -> list[dict[str, object]]:
    if not path.exists():
        _warn_missing(warnings, "gaffiot", path)
        return []
    try:
        with connect_duckdb_ro(path) as conn:
            rows = conn.execute(
                """
                SELECT entry_id, headword_raw, headword_norm, variant_num
                FROM entries_fr
                ORDER BY hash(headword_norm || ?), headword_norm, entry_id
                LIMIT ?
                """,
                [seed, limit],
            ).fetchall()
    except Exception as exc:  # noqa: BLE001
        _warn_error(warnings, "gaffiot", path, exc)
        return []
    return [_gaffiot_item(row) for row in rows]


def _list_lewis_1890(
    path: Path,
    *,
    prefix: str,
    limit: int,
    warnings: list[dict[str, str]],
) -> list[dict[str, object]]:
    if not path.exists():
        _warn_missing(warnings, "lewis_1890", path)
        return []
    params: list[object] = []
    where = ""
    if prefix:
        norm = normalize_lewis_1890_headword(prefix)
        where = "WHERE headword_norm LIKE ? OR lower(headword_raw) LIKE ?"
        params.extend([f"{norm}%", f"{norm}%"])
    sql = f"""
        SELECT entry_id, headword_raw, headword_norm, source_key, entry_hash
        FROM entries
        {where}
        ORDER BY headword_norm, entry_id
    """
    if limit > 0:
        sql += " LIMIT ?"
        params.append(limit)
    try:
        with connect_duckdb_ro(path) as conn:
            rows = conn.execute(sql, params).fetchall()
    except Exception as exc:  # noqa: BLE001
        _warn_error(warnings, "lewis_1890", path, exc)
        return []
    return [_lewis_1890_item(row) for row in rows]


def _neighborhood_lewis_1890(
    path: Path,
    *,
    query: str,
    radius: int,
    warnings: list[dict[str, str]],
) -> list[dict[str, object]]:
    if not path.exists():
        _warn_missing(warnings, "lewis_1890", path)
        return []
    keys = _query_keys(query)
    if not keys:
        return []
    try:
        with connect_duckdb_ro(path) as conn:
            anchor_rows = conn.execute(
                f"""
                SELECT entry_id, headword_raw, headword_norm, source_key, entry_hash
                FROM entries
                WHERE lower(headword_norm) IN ({_placeholders(keys)})
                   OR lower(headword_raw) IN ({_placeholders(keys)})
                   OR lower(source_key) IN ({_placeholders(keys)})
                ORDER BY headword_norm, entry_id
                LIMIT 50
                """,
                [*keys, *keys, *keys],
            ).fetchall()
            anchor = _best_anchor([_lewis_1890_item(row) for row in anchor_rows], query)
            if anchor is None:
                return []
            metadata = cast(Mapping[str, object], anchor.get("metadata") or {})
            anchor_sort = str(anchor["sort_key"])
            entry_id = str(metadata.get("entry_id") or "")
            before_rows = conn.execute(
                """
                SELECT entry_id, headword_raw, headword_norm, source_key, entry_hash
                FROM entries
                WHERE headword_norm < ? OR (headword_norm = ? AND entry_id < ?)
                ORDER BY headword_norm DESC, entry_id DESC
                LIMIT ?
                """,
                [anchor_sort, anchor_sort, entry_id, radius],
            ).fetchall()
            after_rows = conn.execute(
                """
                SELECT entry_id, headword_raw, headword_norm, source_key, entry_hash
                FROM entries
                WHERE headword_norm > ? OR (headword_norm = ? AND entry_id > ?)
                ORDER BY headword_norm, entry_id
                LIMIT ?
                """,
                [anchor_sort, anchor_sort, entry_id, radius],
            ).fetchall()
    except Exception as exc:  # noqa: BLE001
        _warn_error(warnings, "lewis_1890", path, exc)
        return []
    before = [_lewis_1890_item(row) for row in reversed(before_rows)]
    after = [_lewis_1890_item(row) for row in after_rows]
    return [_neighborhood(anchor, before=before, after=after, radius=radius, query=query)]


def _wheel_lewis_1890(
    path: Path,
    *,
    seed: str,
    limit: int,
    warnings: list[dict[str, str]],
) -> list[dict[str, object]]:
    if not path.exists():
        _warn_missing(warnings, "lewis_1890", path)
        return []
    try:
        with connect_duckdb_ro(path) as conn:
            rows = conn.execute(
                """
                SELECT entry_id, headword_raw, headword_norm, source_key, entry_hash
                FROM entries
                ORDER BY hash(headword_norm || ?), headword_norm, entry_id
                LIMIT ?
                """,
                [seed, limit],
            ).fetchall()
    except Exception as exc:  # noqa: BLE001
        _warn_error(warnings, "lewis_1890", path, exc)
        return []
    return [_lewis_1890_item(row) for row in rows]


def _list_georges_1913(
    path: Path,
    *,
    prefix: str,
    limit: int,
    warnings: list[dict[str, str]],
) -> list[dict[str, object]]:
    if not path.exists():
        _warn_missing(warnings, "georges_1913", path)
        return []
    params: list[object] = []
    where = ""
    if prefix:
        norm = normalize_georges_1913_headword(prefix)
        where = "WHERE headword_norm LIKE ? OR lower(headword_roma) LIKE ?"
        params.extend([f"{norm}%", f"{norm}%"])
    sql = f"""
        SELECT entry_id, occurrence, headword_roma, headword_norm, source_page
        FROM entries_fr
        {where}
        ORDER BY headword_norm, source_page, entry_id, occurrence
    """
    if limit > 0:
        sql += " LIMIT ?"
        params.append(limit)
    try:
        with connect_duckdb_ro(path) as conn:
            rows = conn.execute(sql, params).fetchall()
    except Exception as exc:  # noqa: BLE001
        _warn_error(warnings, "georges_1913", path, exc)
        return []
    return [_georges_1913_item(row) for row in rows]


def _neighborhood_georges_1913(
    path: Path,
    *,
    query: str,
    radius: int,
    warnings: list[dict[str, str]],
) -> list[dict[str, object]]:
    if not path.exists():
        _warn_missing(warnings, "georges_1913", path)
        return []
    keys = _query_keys(query)
    if not keys:
        return []
    try:
        with connect_duckdb_ro(path) as conn:
            anchor_rows = conn.execute(
                f"""
                SELECT entry_id, occurrence, headword_roma, headword_norm, source_page
                FROM entries_fr
                WHERE lower(headword_norm) IN ({_placeholders(keys)})
                   OR lower(headword_roma) IN ({_placeholders(keys)})
                ORDER BY headword_norm, source_page, entry_id, occurrence
                LIMIT 50
                """,
                [*keys, *keys],
            ).fetchall()
            anchor = _best_anchor([_georges_1913_item(row) for row in anchor_rows], query)
            if anchor is None:
                return []
            metadata = cast(Mapping[str, object], anchor.get("metadata") or {})
            anchor_sort = str(anchor["sort_key"])
            source_page = str(metadata.get("source_page") or "")
            entry_id = str(metadata.get("entry_id") or "")
            occurrence = _as_int(metadata.get("occurrence"))
            before_rows = conn.execute(
                """
                SELECT entry_id, occurrence, headword_roma, headword_norm, source_page
                FROM entries_fr
                WHERE headword_norm < ?
                   OR (
                     headword_norm = ?
                     AND (
                       source_page < ?
                       OR (source_page = ? AND entry_id < ?)
                       OR (source_page = ? AND entry_id = ? AND occurrence < ?)
                     )
                   )
                ORDER BY headword_norm DESC, source_page DESC, entry_id DESC, occurrence DESC
                LIMIT ?
                """,
                [
                    anchor_sort,
                    anchor_sort,
                    source_page,
                    source_page,
                    entry_id,
                    source_page,
                    entry_id,
                    occurrence,
                    radius,
                ],
            ).fetchall()
            after_rows = conn.execute(
                """
                SELECT entry_id, occurrence, headword_roma, headword_norm, source_page
                FROM entries_fr
                WHERE headword_norm > ?
                   OR (
                     headword_norm = ?
                     AND (
                       source_page > ?
                       OR (source_page = ? AND entry_id > ?)
                       OR (source_page = ? AND entry_id = ? AND occurrence > ?)
                     )
                   )
                ORDER BY headword_norm, source_page, entry_id, occurrence
                LIMIT ?
                """,
                [
                    anchor_sort,
                    anchor_sort,
                    source_page,
                    source_page,
                    entry_id,
                    source_page,
                    entry_id,
                    occurrence,
                    radius,
                ],
            ).fetchall()
    except Exception as exc:  # noqa: BLE001
        _warn_error(warnings, "georges_1913", path, exc)
        return []
    before = [_georges_1913_item(row) for row in reversed(before_rows)]
    after = [_georges_1913_item(row) for row in after_rows]
    return [_neighborhood(anchor, before=before, after=after, radius=radius, query=query)]


def _wheel_georges_1913(
    path: Path,
    *,
    seed: str,
    limit: int,
    warnings: list[dict[str, str]],
) -> list[dict[str, object]]:
    if not path.exists():
        _warn_missing(warnings, "georges_1913", path)
        return []
    try:
        with connect_duckdb_ro(path) as conn:
            rows = conn.execute(
                """
                SELECT entry_id, occurrence, headword_roma, headword_norm, source_page
                FROM entries_fr
                ORDER BY hash(headword_norm || ?), headword_norm, source_page, entry_id, occurrence
                LIMIT ?
                """,
                [seed, limit],
            ).fetchall()
    except Exception as exc:  # noqa: BLE001
        _warn_error(warnings, "georges_1913", path, exc)
        return []
    return [_georges_1913_item(row) for row in rows]


def _list_whitakers(
    path: Path,
    *,
    prefix: str,
    limit: int,
    warnings: list[dict[str, str]],
) -> list[dict[str, object]]:
    if not path.exists():
        _warn_missing(warnings, "whitakers", path)
        return []
    params: list[object] = []
    where = ""
    if prefix:
        norm = normalize_gaffiot_headword(prefix)
        where = (
            "WHERE headword_norm LIKE ? OR lower(source_stem) LIKE ? OR lower(headword_raw) LIKE ?"
        )
        params.extend([f"{norm}%", f"{norm}%", f"{norm}%"])
    sql = f"""
        SELECT entry_id, headword_raw, headword_norm, source_stem, pos, codes
        FROM entries
        {where}
        ORDER BY headword_norm, entry_id
    """
    if limit > 0:
        sql += " LIMIT ?"
        params.append(limit)
    try:
        with connect_duckdb_ro(path) as conn:
            rows = conn.execute(sql, params).fetchall()
    except Exception as exc:  # noqa: BLE001
        _warn_error(warnings, "whitakers", path, exc)
        return []
    return [_whitakers_item(row) for row in rows]


def _neighborhood_whitakers(
    path: Path,
    *,
    query: str,
    radius: int,
    warnings: list[dict[str, str]],
) -> list[dict[str, object]]:
    if not path.exists():
        _warn_missing(warnings, "whitakers", path)
        return []
    keys = _query_keys(query)
    if not keys:
        return []
    try:
        with connect_duckdb_ro(path) as conn:
            anchor_rows = conn.execute(
                f"""
                SELECT entry_id, headword_raw, headword_norm, source_stem, pos, codes
                FROM entries
                WHERE lower(headword_norm) IN ({_placeholders(keys)})
                   OR lower(headword_raw) IN ({_placeholders(keys)})
                   OR lower(source_stem) IN ({_placeholders(keys)})
                ORDER BY headword_norm, entry_id
                LIMIT 50
                """,
                [*keys, *keys, *keys],
            ).fetchall()
            anchor = _best_anchor([_whitakers_item(row) for row in anchor_rows], query)
            if anchor is None:
                return []
            metadata = cast(Mapping[str, object], anchor.get("metadata") or {})
            anchor_sort = str(anchor["sort_key"])
            entry_id = _as_int(metadata.get("entry_id"))
            before_rows = conn.execute(
                """
                SELECT entry_id, headword_raw, headword_norm, source_stem, pos, codes
                FROM entries
                WHERE headword_norm < ? OR (headword_norm = ? AND entry_id < ?)
                ORDER BY headword_norm DESC, entry_id DESC
                LIMIT ?
                """,
                [anchor_sort, anchor_sort, entry_id, radius],
            ).fetchall()
            after_rows = conn.execute(
                """
                SELECT entry_id, headword_raw, headword_norm, source_stem, pos, codes
                FROM entries
                WHERE headword_norm > ? OR (headword_norm = ? AND entry_id > ?)
                ORDER BY headword_norm, entry_id
                LIMIT ?
                """,
                [anchor_sort, anchor_sort, entry_id, radius],
            ).fetchall()
    except Exception as exc:  # noqa: BLE001
        _warn_error(warnings, "whitakers", path, exc)
        return []
    before = [_whitakers_item(row) for row in reversed(before_rows)]
    after = [_whitakers_item(row) for row in after_rows]
    return [_neighborhood(anchor, before=before, after=after, radius=radius, query=query)]


def _wheel_whitakers(
    path: Path,
    *,
    seed: str,
    limit: int,
    warnings: list[dict[str, str]],
) -> list[dict[str, object]]:
    if not path.exists():
        _warn_missing(warnings, "whitakers", path)
        return []
    try:
        with connect_duckdb_ro(path) as conn:
            rows = conn.execute(
                """
                SELECT entry_id, headword_raw, headword_norm, source_stem, pos, codes
                FROM entries
                ORDER BY hash(headword_norm || ?), headword_norm, entry_id
                LIMIT ?
                """,
                [seed, limit],
            ).fetchall()
    except Exception as exc:  # noqa: BLE001
        _warn_error(warnings, "whitakers", path, exc)
        return []
    return [_whitakers_item(row) for row in rows]


def _list_diogenes(
    path: Path,
    *,
    language: LanguageCode,
    prefix: str,
    limit: int,
    warnings: list[dict[str, str]],
) -> list[dict[str, object]]:
    if not path.exists():
        _warn_missing(warnings, "diogenes", path)
        return []
    params: list[object] = [language]
    where = "WHERE language = ?"
    order_by = "sort_key, entry_offset"
    if prefix:
        source_prefix = _greek_section_source_prefix(prefix) if language == "grc" else None
        if source_prefix is None:
            norm = _diogenes_query_key(prefix)
            where += " AND (headword_norm LIKE ? OR lower(headword) LIKE ? OR lower(lookup) LIKE ?)"
            params.extend([f"{norm}%", f"{prefix.strip().lower()}%", f"{norm}%"])
        else:
            norm, native = source_prefix
            where += (
                " AND (headword_norm LIKE ? OR lower(lookup) LIKE ? "
                "OR lower(sort_key) LIKE ? OR lower(headword) LIKE ?)"
            )
            params.extend([f"{norm}%", f"{norm}%", f"{native}%", f"{native}%"])
            order_by = (
                "CASE WHEN lower(sort_key) LIKE ? OR lower(headword) LIKE ? THEN 0 ELSE 1 END, "
                "sort_key, entry_offset"
            )
            params.extend([f"{native}%", f"{native}%"])
    sql = f"""
        SELECT
            language, dictionary, entry_offset, headword, headword_norm, lookup, sort_key,
            previous_offset, next_offset
        FROM entries
        {where}
        ORDER BY {order_by}
    """
    if limit > 0:
        sql += " LIMIT ?"
        params.append(limit)
    try:
        with connect_duckdb_ro(path) as conn:
            rows = conn.execute(sql, params).fetchall()
    except Exception as exc:  # noqa: BLE001
        _warn_error(warnings, "diogenes", path, exc)
        return []
    return [_diogenes_item(row) for row in rows]


def _neighborhood_diogenes(
    path: Path,
    *,
    language: LanguageCode,
    query: str,
    radius: int,
    warnings: list[dict[str, str]],
) -> list[dict[str, object]]:
    if not path.exists():
        _warn_missing(warnings, "diogenes", path)
        return []
    keys = _query_keys(query)
    if not keys:
        return []
    try:
        with connect_duckdb_ro(path) as conn:
            source_prefix = _greek_section_source_prefix(query) if language == "grc" else None
            if source_prefix is None:
                anchor_rows = conn.execute(
                    f"""
                    SELECT
                        language, dictionary, entry_offset, headword, headword_norm, lookup,
                        sort_key, previous_offset, next_offset
                    FROM entries
                    WHERE language = ?
                      AND (
                        lower(headword_norm) IN ({_placeholders(keys)})
                        OR lower(lookup) IN ({_placeholders(keys)})
                        OR lower(sort_key) IN ({_placeholders(keys)})
                      )
                    ORDER BY entry_offset
                    LIMIT 50
                    """,
                    [language, *keys, *keys, *keys],
                ).fetchall()
                anchor = _best_anchor([_diogenes_item(row) for row in anchor_rows], query)
            else:
                norm, native = source_prefix
                anchor_rows = conn.execute(
                    """
                    SELECT
                        language, dictionary, entry_offset, headword, headword_norm, lookup,
                        sort_key, previous_offset, next_offset
                    FROM entries
                    WHERE language = ?
                      AND (
                        lower(headword_norm) LIKE ?
                        OR lower(lookup) LIKE ?
                        OR lower(sort_key) LIKE ?
                        OR lower(headword) LIKE ?
                      )
                    ORDER BY
                      CASE
                        WHEN lower(sort_key) LIKE ? OR lower(headword) LIKE ? THEN 0
                        ELSE 1
                      END,
                      sort_key,
                      entry_offset
                    LIMIT 1
                    """,
                    [
                        language,
                        f"{norm}%",
                        f"{norm}%",
                        f"{native}%",
                        f"{native}%",
                        f"{native}%",
                        f"{native}%",
                    ],
                ).fetchall()
                anchor = _diogenes_item(anchor_rows[0]) if anchor_rows else None
            if anchor is None:
                return []
            metadata = cast(Mapping[str, object], anchor.get("metadata") or {})
            offset = _as_int(metadata.get("offset"))
            before_rows = conn.execute(
                """
                SELECT
                    language, dictionary, entry_offset, headword, headword_norm, lookup, sort_key,
                    previous_offset, next_offset
                FROM entries
                WHERE language = ? AND entry_offset < ?
                ORDER BY entry_offset DESC
                LIMIT ?
                """,
                [language, offset, radius],
            ).fetchall()
            after_rows = conn.execute(
                """
                SELECT
                    language, dictionary, entry_offset, headword, headword_norm, lookup, sort_key,
                    previous_offset, next_offset
                FROM entries
                WHERE language = ? AND entry_offset > ?
                ORDER BY entry_offset
                LIMIT ?
                """,
                [language, offset, radius],
            ).fetchall()
    except Exception as exc:  # noqa: BLE001
        _warn_error(warnings, "diogenes", path, exc)
        return []
    before = [_diogenes_item(row) for row in reversed(before_rows)]
    after = [_diogenes_item(row) for row in after_rows]
    return [_neighborhood(anchor, before=before, after=after, radius=radius, query=query)]


def _wheel_diogenes(
    path: Path,
    *,
    language: LanguageCode,
    seed: str,
    limit: int,
    warnings: list[dict[str, str]],
) -> list[dict[str, object]]:
    if not path.exists():
        _warn_missing(warnings, "diogenes", path)
        return []
    try:
        with connect_duckdb_ro(path) as conn:
            rows = conn.execute(
                """
                SELECT
                    language, dictionary, entry_offset, headword, headword_norm, lookup, sort_key,
                    previous_offset, next_offset
                FROM entries
                WHERE language = ?
                ORDER BY hash(sort_key || ?), sort_key, entry_offset
                LIMIT ?
                """,
                [language, seed, limit],
            ).fetchall()
    except Exception as exc:  # noqa: BLE001
        _warn_error(warnings, "diogenes", path, exc)
        return []
    return [_diogenes_item(row) for row in rows]


def _list_bailly(
    path: Path,
    *,
    prefix: str,
    limit: int,
    warnings: list[dict[str, str]],
) -> list[dict[str, object]]:
    if not path.exists():
        _warn_missing(warnings, "bailly", path)
        return []
    params: list[object] = []
    where = ""
    if prefix:
        norm = normalize_bailly_headword(prefix)
        where = "WHERE lemma_norm LIKE ? OR lower(lemma) LIKE ?"
        params.extend([f"{norm}%", f"{prefix.strip().lower()}%"])
    sql = f"""
        SELECT entry_id, lemma, lemma_norm, page_start, page_end
        FROM entries
        {where}
        ORDER BY lemma_norm, entry_id
    """
    if limit > 0:
        sql += " LIMIT ?"
        params.append(limit)
    try:
        with connect_duckdb_ro(path) as conn:
            rows = conn.execute(sql, params).fetchall()
    except Exception as exc:  # noqa: BLE001
        _warn_error(warnings, "bailly", path, exc)
        return []
    return [_bailly_item(row) for row in rows]


def _neighborhood_bailly(
    path: Path,
    *,
    query: str,
    radius: int,
    warnings: list[dict[str, str]],
) -> list[dict[str, object]]:
    if not path.exists():
        _warn_missing(warnings, "bailly", path)
        return []
    keys = _query_keys(query)
    if not keys:
        return []
    try:
        with connect_duckdb_ro(path) as conn:
            anchor_rows = conn.execute(
                f"""
                SELECT entry_id, lemma, lemma_norm, page_start, page_end
                FROM entries
                WHERE lower(lemma_norm) IN ({_placeholders(keys)})
                   OR lower(lemma) IN ({_placeholders(keys)})
                ORDER BY lemma_norm, entry_id
                LIMIT 50
                """,
                [*keys, *keys],
            ).fetchall()
            anchor = _best_anchor([_bailly_item(row) for row in anchor_rows], query)
            if anchor is None:
                return []
            metadata = cast(Mapping[str, object], anchor.get("metadata") or {})
            anchor_sort = str(anchor["sort_key"])
            entry_id = str(metadata.get("entry_id") or "")
            before_rows = conn.execute(
                """
                SELECT entry_id, lemma, lemma_norm, page_start, page_end
                FROM entries
                WHERE lemma_norm < ? OR (lemma_norm = ? AND entry_id < ?)
                ORDER BY lemma_norm DESC, entry_id DESC
                LIMIT ?
                """,
                [anchor_sort, anchor_sort, entry_id, radius],
            ).fetchall()
            after_rows = conn.execute(
                """
                SELECT entry_id, lemma, lemma_norm, page_start, page_end
                FROM entries
                WHERE lemma_norm > ? OR (lemma_norm = ? AND entry_id > ?)
                ORDER BY lemma_norm, entry_id
                LIMIT ?
                """,
                [anchor_sort, anchor_sort, entry_id, radius],
            ).fetchall()
    except Exception as exc:  # noqa: BLE001
        _warn_error(warnings, "bailly", path, exc)
        return []
    before = [_bailly_item(row) for row in reversed(before_rows)]
    after = [_bailly_item(row) for row in after_rows]
    return [_neighborhood(anchor, before=before, after=after, radius=radius, query=query)]


def _wheel_bailly(
    path: Path,
    *,
    seed: str,
    limit: int,
    warnings: list[dict[str, str]],
) -> list[dict[str, object]]:
    if not path.exists():
        _warn_missing(warnings, "bailly", path)
        return []
    try:
        with connect_duckdb_ro(path) as conn:
            rows = conn.execute(
                """
                SELECT entry_id, lemma, lemma_norm, page_start, page_end
                FROM entries
                ORDER BY hash(lemma_norm || ?), lemma_norm, entry_id
                LIMIT ?
                """,
                [seed, limit],
            ).fetchall()
    except Exception as exc:  # noqa: BLE001
        _warn_error(warnings, "bailly", path, exc)
        return []
    return [_bailly_item(row) for row in rows]


def _list_strongs_greek(
    path: Path,
    *,
    prefix: str,
    limit: int,
    warnings: list[dict[str, str]],
) -> list[dict[str, object]]:
    if not path.exists():
        _warn_missing(warnings, "strongs_greek", path)
        return []
    params: list[object] = []
    where = "WHERE a.alias_kind = 'lemma'"
    if prefix:
        norm = normalize_strongs_greek_key(prefix)
        where = "WHERE a.alias_key LIKE ?"
        params.append(f"{norm}%")
    sql = f"""
        WITH ranked AS (
            SELECT
                e.entry_id, e.strongs_number, e.strongs_int, e.lemma_unicode,
                e.lemma_translit, e.display_gloss, e.entry_hash,
                a.alias_key, a.alias_display, a.alias_kind, a.rank,
                row_number() OVER (
                    PARTITION BY e.entry_id
                    ORDER BY a.rank, a.alias_key
                ) AS rn
            FROM entries e
            JOIN aliases a ON a.entry_id = e.entry_id
            {where}
        )
        SELECT entry_id, strongs_number, strongs_int, lemma_unicode, lemma_translit,
               display_gloss, entry_hash, alias_key, alias_display, alias_kind, rank
        FROM ranked
        WHERE rn = 1
        ORDER BY strongs_int
    """
    if limit > 0:
        sql += " LIMIT ?"
        params.append(limit)
    try:
        with connect_duckdb_ro(path) as conn:
            rows = conn.execute(sql, params).fetchall()
    except Exception as exc:  # noqa: BLE001
        _warn_error(warnings, "strongs_greek", path, exc)
        return []
    return [_strongs_greek_item(row) for row in rows]


def _neighborhood_strongs_greek(
    path: Path,
    *,
    query: str,
    radius: int,
    warnings: list[dict[str, str]],
) -> list[dict[str, object]]:
    if not path.exists():
        _warn_missing(warnings, "strongs_greek", path)
        return []
    keys = _query_keys(query)
    if not keys:
        return []
    try:
        with connect_duckdb_ro(path) as conn:
            anchor_rows = conn.execute(
                f"""
                SELECT
                    e.entry_id, e.strongs_number, e.strongs_int, e.lemma_unicode,
                    e.lemma_translit, e.display_gloss, e.entry_hash,
                    a.alias_key, a.alias_display, a.alias_kind, a.rank
                FROM aliases a
                JOIN entries e ON e.entry_id = a.entry_id
                WHERE a.alias_key IN ({_placeholders(keys)})
                ORDER BY a.rank, e.strongs_int
                LIMIT 50
                """,
                keys,
            ).fetchall()
            anchor = _best_anchor([_strongs_greek_item(row) for row in anchor_rows], query)
            if anchor is None:
                return []
            metadata = cast(Mapping[str, object], anchor.get("metadata") or {})
            strongs_int = _as_int(metadata.get("strongs_int"))
            before_rows = conn.execute(
                """
                SELECT
                    e.entry_id, e.strongs_number, e.strongs_int, e.lemma_unicode,
                    e.lemma_translit, e.display_gloss, e.entry_hash,
                    a.alias_key, a.alias_display, a.alias_kind, a.rank
                FROM entries e
                JOIN aliases a ON a.entry_id = e.entry_id AND a.alias_kind = 'lemma'
                WHERE e.strongs_int < ?
                ORDER BY e.strongs_int DESC
                LIMIT ?
                """,
                [strongs_int, radius],
            ).fetchall()
            after_rows = conn.execute(
                """
                SELECT
                    e.entry_id, e.strongs_number, e.strongs_int, e.lemma_unicode,
                    e.lemma_translit, e.display_gloss, e.entry_hash,
                    a.alias_key, a.alias_display, a.alias_kind, a.rank
                FROM entries e
                JOIN aliases a ON a.entry_id = e.entry_id AND a.alias_kind = 'lemma'
                WHERE e.strongs_int > ?
                ORDER BY e.strongs_int
                LIMIT ?
                """,
                [strongs_int, radius],
            ).fetchall()
    except Exception as exc:  # noqa: BLE001
        _warn_error(warnings, "strongs_greek", path, exc)
        return []
    before = [_strongs_greek_item(row) for row in reversed(before_rows)]
    after = [_strongs_greek_item(row) for row in after_rows]
    return [_neighborhood(anchor, before=before, after=after, radius=radius, query=query)]


def _wheel_strongs_greek(
    path: Path,
    *,
    seed: str,
    limit: int,
    warnings: list[dict[str, str]],
) -> list[dict[str, object]]:
    if not path.exists():
        _warn_missing(warnings, "strongs_greek", path)
        return []
    try:
        with connect_duckdb_ro(path) as conn:
            rows = conn.execute(
                """
                SELECT
                    e.entry_id, e.strongs_number, e.strongs_int, e.lemma_unicode,
                    e.lemma_translit, e.display_gloss, e.entry_hash,
                    a.alias_key, a.alias_display, a.alias_kind, a.rank
                FROM entries e
                JOIN aliases a ON a.entry_id = e.entry_id AND a.alias_kind = 'lemma'
                ORDER BY hash(CAST(e.strongs_int AS VARCHAR) || ?), e.strongs_int
                LIMIT ?
                """,
                [seed, limit],
            ).fetchall()
    except Exception as exc:  # noqa: BLE001
        _warn_error(warnings, "strongs_greek", path, exc)
        return []
    return [_strongs_greek_item(row) for row in rows]


def _cdsl_item(dictionary: str, row: Sequence[object]) -> dict[str, object]:
    key = str(row[0] or "")
    key_normalized = str(row[1] or key)
    lnum = row[2]
    hom = row[3]
    transliteration = _slp1_to_iast(key)
    deva = _sanskrit_devanagari(key, "SLP1")
    canonical_name = deva or transliteration or key
    return _item(
        language="san",
        source="cdsl",
        dictionary=dictionary,
        canonical_name=canonical_name,
        canonical_key=_plain_index_key(transliteration or key),
        source_name=key,
        lookup=transliteration or key,
        display_primary=canonical_name,
        transliteration=transliteration,
        source_key=key,
        sort_key=key_normalized,
        source_order_key=_order_key(key_normalized, lnum, hom),
        source_ref=f"cdsl:{dictionary}:{lnum}",
        extra={
            "hom": hom,
            "lnum": lnum,
            "key_normalized": key_normalized,
            "page_ref": row[5] or "",
        },
    )


def _dico_item(row: Sequence[object]) -> dict[str, object]:
    entry_id = str(row[0] or "")
    occurrence_raw = row[1]
    occurrence = (
        occurrence_raw if isinstance(occurrence_raw, int) else int(str(occurrence_raw or 0))
    )
    headword_deva = str(row[2] or "")
    headword_roma = str(row[3] or "")
    headword_norm = str(row[4] or headword_roma or entry_id)
    source_page = str(row[5] or "")
    return _item(
        language="san",
        source="dico",
        dictionary="dico",
        canonical_name=headword_deva or headword_roma or headword_norm,
        canonical_key=_plain_index_key(headword_roma or headword_norm),
        source_name=headword_norm,
        lookup=headword_roma or headword_norm,
        display_primary=headword_deva or headword_roma or headword_norm,
        transliteration=headword_roma or headword_norm,
        source_key=headword_norm,
        sort_key=headword_norm,
        source_order_key=_order_key(headword_norm, source_page, entry_id, occurrence),
        source_ref=f"dico:{source_page}.html#{entry_id}:{occurrence}",
        extra={"entry_id": entry_id, "occurrence": occurrence, "source_page": source_page},
    )


def _gaffiot_item(row: Sequence[object]) -> dict[str, object]:
    entry_id = str(row[0] or "")
    headword_raw = str(row[1] or "")
    headword_norm = str(row[2] or normalize_gaffiot_headword(headword_raw))
    variant_num = row[3]
    learner_headword = _strip_source_variant_label(headword_raw, fallback=headword_norm)
    return _item(
        language="lat",
        source="gaffiot",
        dictionary="gaffiot",
        canonical_name=learner_headword,
        canonical_key=_plain_index_key(headword_norm),
        source_name=headword_raw or headword_norm,
        lookup=headword_norm,
        display_primary=learner_headword,
        transliteration=headword_norm,
        source_key=headword_norm,
        sort_key=headword_norm,
        source_order_key=_order_key(headword_norm, entry_id),
        source_ref=f"gaffiot:{entry_id}",
        extra={"entry_id": entry_id, "headword_norm": headword_norm, "variant_num": variant_num},
    )


def _lewis_1890_item(row: Sequence[object]) -> dict[str, object]:
    entry_id = str(row[0] or "")
    headword_raw = str(row[1] or "")
    headword_norm = str(row[2] or normalize_lewis_1890_headword(headword_raw))
    source_key = str(row[3] or headword_norm)
    entry_hash = str(row[4] or "")
    display = headword_raw or headword_norm
    return _item(
        language="lat",
        source="lewis_1890",
        dictionary="lewis_1890",
        canonical_name=display,
        canonical_key=_plain_index_key(headword_norm),
        source_name=display,
        lookup=headword_norm,
        display_primary=display,
        transliteration=headword_norm,
        source_key=source_key,
        sort_key=headword_norm,
        source_order_key=_order_key(headword_norm, entry_id),
        source_ref=f"lewis_1890:{source_key}",
        extra={
            "entry_id": entry_id,
            "headword_norm": headword_norm,
            "source_key": source_key,
            "entry_hash": entry_hash,
        },
    )


def _georges_1913_item(row: Sequence[object]) -> dict[str, object]:
    entry_id = str(row[0] or "")
    occurrence = _as_int(row[1])
    headword_roma = str(row[2] or "")
    headword_norm = str(row[3] or normalize_georges_1913_headword(headword_roma or entry_id))
    source_page = str(row[4] or "")
    display = headword_roma or headword_norm
    return _item(
        language="lat",
        source="georges_1913",
        dictionary="georges_1913",
        canonical_name=display,
        canonical_key=_plain_index_key(headword_norm),
        source_name=display,
        lookup=headword_norm,
        display_primary=display,
        transliteration=headword_norm,
        source_key=headword_norm,
        sort_key=headword_norm,
        source_order_key=_order_key(headword_norm, source_page, entry_id, occurrence),
        source_ref=f"georges_1913:{source_page}#{entry_id}:{occurrence}",
        extra={
            "entry_id": entry_id,
            "headword_norm": headword_norm,
            "occurrence": occurrence,
            "source_page": source_page,
        },
    )


def _whitakers_item(row: Sequence[object]) -> dict[str, object]:
    entry_id_raw = row[0]
    entry_id = int(entry_id_raw) if isinstance(entry_id_raw, int | float | str) else 0
    headword_raw = str(row[1] or "")
    headword_norm = str(row[2] or normalize_gaffiot_headword(headword_raw))
    source_stem = str(row[3] or "")
    pos = str(row[4] or "")
    codes = str(row[5] or "")
    return _item(
        language="lat",
        source="whitakers",
        dictionary="whitakers",
        canonical_name=headword_raw or headword_norm,
        canonical_key=_plain_index_key(headword_norm),
        source_name=headword_raw or headword_norm,
        lookup=headword_norm,
        display_primary=headword_raw or headword_norm,
        transliteration=headword_norm,
        source_key=source_stem or headword_norm,
        sort_key=headword_norm,
        source_order_key=_order_key(headword_norm, entry_id),
        source_ref=f"whitakers:{entry_id}",
        extra={
            "entry_id": entry_id,
            "headword_norm": headword_norm,
            "source_stem": source_stem,
            "pos": pos,
            "codes": codes,
        },
    )


def _diogenes_item(row: Sequence[object]) -> dict[str, object]:
    language = cast(LanguageCode, str(row[0] or "lat"))
    dictionary = str(row[1] or ("lsj" if language == "grc" else "lewis_short"))
    offset_raw = row[2]
    offset = int(offset_raw) if isinstance(offset_raw, int | float | str) else 0
    headword = str(row[3] or "")
    headword_norm = str(row[4] or headword.lower())
    lookup = str(row[5] or headword_norm or headword)
    sort_key = str(row[6] or headword_norm)
    previous_offset = row[7]
    next_offset = row[8]
    return _item(
        language=language,
        source="diogenes",
        dictionary=dictionary,
        canonical_name=headword or lookup,
        canonical_key=_plain_index_key(lookup or headword_norm or headword),
        source_name=headword or lookup,
        lookup=lookup,
        display_primary=headword or lookup,
        transliteration=lookup,
        source_key=headword,
        sort_key=sort_key,
        source_order_key=_order_key(offset),
        source_ref=f"diogenes:{language}:{offset}",
        extra={
            "offset": offset,
            "headword_norm": headword_norm,
            "previous_offset": previous_offset,
            "next_offset": next_offset,
        },
    )


def _bailly_item(row: Sequence[object]) -> dict[str, object]:
    entry_id = str(row[0] or "")
    lemma = str(row[1] or "")
    lemma_norm = str(row[2] or normalize_bailly_headword(lemma))
    page_start = row[3]
    page_end = row[4]
    return _item(
        language="grc",
        source="bailly",
        dictionary="bailly",
        canonical_name=lemma or lemma_norm,
        canonical_key=_plain_index_key(lemma_norm),
        source_name=lemma or lemma_norm,
        lookup=lemma_norm,
        display_primary=lemma or lemma_norm,
        transliteration=lemma_norm,
        source_key=lemma,
        sort_key=lemma_norm,
        source_order_key=_order_key(lemma_norm, entry_id),
        source_ref=f"bailly:{entry_id}",
        extra={
            "entry_id": entry_id,
            "lemma_norm": lemma_norm,
            "page_start": page_start,
            "page_end": page_end,
        },
    )


def _strongs_greek_item(row: Sequence[object]) -> dict[str, object]:
    entry_id = str(row[0] or "")
    strongs_number = str(row[1] or "")
    strongs_int = _as_int(row[2])
    lemma_unicode = str(row[3] or "")
    lemma_translit = str(row[4] or "")
    display_gloss = str(row[5] or "")
    entry_hash = str(row[6] or "")
    alias_key = str(row[7] or "")
    alias_display = str(row[8] or "")
    alias_kind = str(row[9] or "")
    alias_rank = _as_int(row[10])
    lemma_norm = normalize_strongs_greek_key(lemma_unicode)
    display = lemma_unicode or alias_display or strongs_number
    return _item(
        language="grc",
        source="strongs_greek",
        dictionary="strongs_greek",
        canonical_name=display,
        canonical_key=lemma_norm,
        source_name=lemma_unicode or display,
        lookup=lemma_unicode or alias_display or lemma_norm,
        display_primary=display,
        transliteration=lemma_translit or alias_key,
        source_key=alias_display or strongs_number,
        sort_key=lemma_norm,
        source_order_key=_order_key(strongs_int),
        source_ref=f"strongs_greek:{strongs_number}",
        extra={
            "entry_id": entry_id,
            "strongs_number": strongs_number,
            "strongs_int": strongs_int,
            "lemma_norm": lemma_norm,
            "lemma_translit": lemma_translit,
            "display_gloss": display_gloss,
            "entry_hash": entry_hash,
            "matched_alias_key": alias_key,
            "matched_alias_display": alias_display,
            "matched_alias_kind": alias_kind,
            "matched_alias_rank": alias_rank,
            "dictionary_genre": "religious",
        },
    )


def _item(  # noqa: PLR0913
    *,
    language: LanguageCode,
    source: str,
    dictionary: str,
    canonical_name: str,
    canonical_key: str,
    source_name: str,
    lookup: str,
    display_primary: str,
    transliteration: str,
    source_key: str,
    sort_key: str,
    source_order_key: str,
    source_ref: str,
    extra: Mapping[str, object] | None = None,
) -> dict[str, object]:
    native_order_key = _native_order_key(
        language=language,
        source=source,
        source_name=source_name,
        lookup=lookup,
        transliteration=transliteration,
        source_key=source_key,
        sort_key=sort_key,
        canonical_key=canonical_key,
    )
    lexeme_key = _lexeme_key(
        language=language,
        source=source,
        source_name=source_name,
        lookup=lookup,
        transliteration=transliteration,
        source_key=source_key,
        sort_key=sort_key,
        canonical_key=canonical_key,
    )
    lexeme_id = _lexeme_id(language, canonical_key, lexeme_key)
    wheel_id = _wheel_id(language, canonical_key, lexeme_key)
    wheel_order_key = _wheel_order_key(language, canonical_key, lexeme_key)
    source_order_id = _source_order_id(
        language=language,
        source=source,
        dictionary=dictionary,
        source_order_key=source_order_key,
        source_ref=source_ref,
    )
    index_entry_id = _index_entry_id(
        language=language,
        source=source,
        dictionary=dictionary,
        source_ref=source_ref,
    )
    payload: dict[str, object] = {
        "lexeme_id": lexeme_id,
        "wheel_id": wheel_id,
        "wheel_order_key": wheel_order_key,
        "index_entry_id": index_entry_id,
        "source_order_id": source_order_id,
        "language": language,
        "source": source,
        "dictionary": dictionary,
        "kind": "headword",
        "canonical_name": canonical_name,
        "canonical_key": canonical_key,
        "lexeme_key": lexeme_key,
        "source_name": source_name,
        "lookup": lookup,
        "display": {
            "primary": display_primary,
            "transliteration": transliteration,
            "source_key": source_key,
        },
        "sort_key": sort_key,
        "native_order_key": native_order_key,
        "source_order_key": source_order_key,
        "source_ref": source_ref,
        "order": _source_native_order_metadata(
            language=language,
            source=source,
            dictionary=dictionary,
            key=source_order_key,
            display_key=display_primary,
        ),
        "ids": {
            "lexeme": lexeme_id,
            "lexeme_key": lexeme_key,
            "wheel": wheel_id,
            "index_entry": index_entry_id,
            "source_order": source_order_id,
            "source_ref": source_ref,
        },
        "encounter": {
            "language": language,
            "q": lookup,
            "dictionary": source if source != "cdsl" else "cdsl",
        },
    }
    if extra:
        payload["metadata"] = dict(extra)
    return payload


def _lexeme_id(language: LanguageCode, canonical_key: str, lexeme_key: str) -> str:
    key = _id_component(canonical_key)
    if _lexeme_id_needs_digest(language, lexeme_key):
        digest = hashlib.sha256(f"{language}\x1f{lexeme_key}".encode()).hexdigest()[:8]
        return f"lexeme:{language}:{key}:{digest}"
    return f"lexeme:{language}:{key}"


def _wheel_id(language: LanguageCode, canonical_key: str, lexeme_key: str) -> str:
    key = _id_component(canonical_key)
    digest = hashlib.sha256(f"{language}\x1f{lexeme_key}".encode()).hexdigest()[:10]
    return f"wheel:{language}:{key}:{digest}"


def _wheel_order_key(language: LanguageCode, canonical_key: str, lexeme_key: str) -> str:
    if _lexeme_id_needs_digest(language, lexeme_key):
        digest = hashlib.sha256(f"{language}\x1f{lexeme_key}".encode()).hexdigest()[:8]
        return _order_key(_LANGUAGE_ORDER.get(language, 9), language, canonical_key, digest)
    return _order_key(_LANGUAGE_ORDER.get(language, 9), language, canonical_key)


def _lexeme_key(  # noqa: PLR0913
    *,
    language: LanguageCode,
    source: str,
    source_name: str,
    lookup: str,
    transliteration: str,
    source_key: str,
    sort_key: str,
    canonical_key: str,
) -> str:
    if language != "san":
        return canonical_key
    candidates = (
        source_name if source == "cdsl" else "",
        transliteration,
        source_key,
        lookup,
        sort_key,
        canonical_key,
    )
    for candidate in candidates:
        slp1 = _sanskrit_order_slp1(candidate)
        if slp1:
            return slp1
    return canonical_key


def _lexeme_id_needs_digest(language: LanguageCode, lexeme_key: str) -> bool:
    return language == "san" and any(char in lexeme_key for char in "MHRNYwWqQSzfxFX")


def _native_order_key(  # noqa: PLR0913
    *,
    language: LanguageCode,
    source: str,
    source_name: str,
    lookup: str,
    transliteration: str,
    source_key: str,
    sort_key: str,
    canonical_key: str,
) -> str:
    if language == "san":
        candidates = (
            source_name if source == "cdsl" else "",
            transliteration,
            source_key,
            lookup,
            sort_key,
            canonical_key,
        )
        for candidate in candidates:
            slp1 = _sanskrit_order_slp1(candidate)
            if slp1:
                return _sanskrit_native_order_key(slp1)
        return _sanskrit_native_order_key(canonical_key)
    if language == "grc":
        return _plain_index_key(sort_key or lookup or canonical_key)
    return _plain_index_key(sort_key or canonical_key or lookup)


def _index_entry_id(
    *,
    language: LanguageCode,
    source: str,
    dictionary: str,
    source_ref: str,
) -> str:
    material = "\x1f".join([language, source, dictionary, source_ref])
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]
    return f"word-index:{language}:{source}:{dictionary}:{digest}"


def _source_order_id(
    *,
    language: LanguageCode,
    source: str,
    dictionary: str,
    source_order_key: str,
    source_ref: str,
) -> str:
    order_component = _id_component(source_order_key)
    material = "\x1f".join([language, source, dictionary, source_order_key, source_ref])
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:10]
    return f"word-order:{language}:{source}:{dictionary}:{order_component}:{digest}"


def _order_key(*parts: object) -> str:
    return ":".join(_order_part(part) for part in parts)


def _order_part(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, int):
        return f"{value:020d}"
    if isinstance(value, float):
        return f"{int(round(value * 1000)):020d}"
    text = str(value).strip().lower()
    if text.isdigit():
        return f"{int(text):020d}"
    return _id_component(text)


def _source_native_order_metadata(
    *,
    language: LanguageCode | str,
    source: str,
    dictionary: str,
    key: str,
    display_key: str,
) -> dict[str, str]:
    language_code = str(language)
    return {
        "policy": "source-native" if key else "fallback",
        "label": f"{_language_order_label(language_code)} source order",
        "collation": _source_order_collation(language_code, source),
        "key": key,
        "display_key": display_key,
        "explanation": (
            f"Ordered by the {source}:{dictionary} source order key. "
            "This preserves the indexed source sequence without reconstructing a separate "
            "native grammar collation."
            if key
            else "No source order key was available; consumers should treat this as fallback order."
        ),
    }


def _lexeme_card_order_metadata(card: Mapping[str, object]) -> dict[str, str]:
    language = str(card.get("language") or "")
    key = str(card.get("wheel_order_key") or card.get("canonical_key") or "")
    display = _display_key(card)
    return {
        "policy": "canonical-key",
        "label": f"{_language_order_label(language)} canonical lexeme order",
        "collation": "canonical-key",
        "key": key,
        "display_key": display,
        "explanation": (
            "Collapsed lexeme cards are ordered by LangNet's stable wheel/canonical key. "
            "Inspect source_entries for each dictionary's native source order."
        ),
    }


def _neighborhood_order_metadata(
    anchor: Mapping[str, object],
    *,
    anchor_status: str,
) -> dict[str, str]:
    source = str(anchor.get("source") or "")
    dictionary = str(anchor.get("dictionary") or "")
    language = str(anchor.get("language") or "")
    key = str(anchor.get("source_order_key") or "")
    order = _source_native_order_metadata(
        language=language,
        source=source,
        dictionary=dictionary,
        key=key,
        display_key=_display_key(anchor),
    )
    order["explanation"] = (
        f"{order['explanation']} The neighborhood anchor is {anchor_status}; before/after "
        "items are contiguous in this source window."
    )
    return order


def _merged_neighborhood_order_metadata(
    *,
    language: str,
    query: str,
    anchor_status: str,
) -> dict[str, str]:
    return {
        "policy": "source-window-merge",
        "label": f"{_language_order_label(language)} merged source-window order",
        "collation": "merged-source-window",
        "key": query,
        "display_key": query,
        "explanation": (
            f"Merged neighborhoods combine source-local windows around the query. "
            f"The selected anchor is {anchor_status}; item order is a stable merge of "
            "source windows, not one dictionary's native order."
        ),
    }


def _integrated_language_native_order_metadata(
    *,
    language: str,
    query: str,
    anchor_status: str,
) -> dict[str, str]:
    collation = {
        "san": "sa-varga",
        "grc": "grc-lexical",
        "lat": "lat-lexical",
    }.get(language, "canonical-key")
    return {
        "policy": "language-native",
        "label": f"{_language_order_label(language)} integrated native order",
        "collation": collation,
        "key": query,
        "display_key": query,
        "explanation": (
            f"Integrated neighborhoods collapse source entries into lexeme cards and order "
            f"them by the language-native key. The selected anchor is {anchor_status}."
        ),
    }


def _grouped_neighborhood_order_metadata(
    neighborhoods: Sequence[Mapping[str, object]],
) -> dict[str, str]:
    languages = sorted({str(group.get("language") or "") for group in neighborhoods})
    return {
        "policy": "source-window-merge",
        "label": "Grouped source windows",
        "collation": "merged-source-window",
        "key": ",".join(languages),
        "display_key": ", ".join(_language_order_label(language) for language in languages),
        "explanation": (
            "This response contains multiple source-local neighborhoods. Each group carries "
            "its own source-native order metadata."
        ),
    }


def _wheel_payload_order(
    *,
    language: str,
    source: str,
    seed: str,
) -> dict[str, str]:
    return {
        "policy": "seeded-discovery",
        "label": "Seeded discovery order",
        "collation": "seeded-discovery",
        "key": seed,
        "display_key": seed or "unseeded",
        "explanation": (
            f"Wheel results for language={language} source={source} are selected by a stable "
            "seeded discovery ranking, then interleaved by language and source."
        ),
    }


def _list_payload_order(
    *,
    language: str,
    source: str,
    prefix: str,
) -> dict[str, str]:
    normalized_source = source.strip().lower()
    if normalized_source == "all":
        return {
            "policy": "canonical-key",
            "label": "Collapsed lexeme order",
            "collation": "canonical-key",
            "key": prefix,
            "display_key": prefix,
            "explanation": (
                "`word-index list --source all` collapses source entries to lexeme cards "
                "and orders them by LangNet's stable wheel/canonical key. Source-native "
                "order remains available on each source entry."
            ),
        }
    language_code = (
        "all"
        if language.strip().lower() == "all"
        else str(canonical_language(language) or language)
    )
    return {
        "policy": "source-native",
        "label": f"{_language_order_label(language_code)} source order",
        "collation": _source_order_collation(language_code, normalized_source),
        "key": prefix,
        "display_key": prefix,
        "explanation": (
            "`word-index list` preserves each source's indexed order within the requested "
            "source and prefix window."
        ),
    }


def _browse_payload_order(*, language: str, source: str, prefix: str) -> dict[str, str]:
    normalized_source = source.strip().lower()
    if normalized_source == "all":
        return {
            "policy": "grouped-source-native",
            "label": f"{_language_order_label(language)} grouped source-native browse",
            "collation": "source",
            "key": prefix,
            "display_key": prefix,
            "explanation": (
                "`word-index browse --source all` returns source/dictionary groups. "
                "Each group preserves its own source-native order; groups are not "
                "globally interleaved into a single native collation."
            ),
        }
    return {
        "policy": "source-native",
        "label": f"{_language_order_label(language)} source-native browse",
        "collation": _source_order_collation(language, normalized_source),
        "key": prefix,
        "display_key": prefix,
        "explanation": (
            "`word-index browse` preserves the requested source's indexed order "
            "within the prefix window."
        ),
    }


def _browse_group_order_metadata(
    *,
    language: LanguageCode,
    source: str,
    dictionary: str,
    prefix: str,
) -> dict[str, str]:
    return {
        "policy": "source-native",
        "label": f"{_language_order_label(language)} {source}:{dictionary} browse order",
        "collation": _source_order_collation(language, source),
        "key": prefix,
        "display_key": prefix,
        "explanation": (
            f"Rows in this group preserve {source}:{dictionary} source order for "
            "the requested prefix. Compare groups separately unless a later "
            "language-native interleaving policy is requested."
        ),
    }


def _cross_dictionary_browse_order_metadata(card: Mapping[str, object]) -> dict[str, str]:
    language = str(card.get("language") or "")
    display = _display_key(card)
    return {
        "policy": "grouped-source-native",
        "label": f"{_language_order_label(language)} cross-dictionary browse group",
        "collation": "source",
        "key": str(card.get("canonical_key") or ""),
        "display_key": display,
        "explanation": (
            "This learner browse row groups matching source-native browse rows across "
            "dictionaries. Inspect source_entries for each dictionary's exact source order."
        ),
    }


def _source_order_collation(language: str, source: str) -> str:
    if language == "lat":
        return "lat-lexical"
    if language == "grc":
        return "grc-lexical"
    if language == "san" and source == "dico":
        return "source"
    if language == "san" and source == "cdsl":
        return "source"
    return "source"


def _language_order_label(language: str) -> str:
    return {
        "lat": "Latin",
        "grc": "Greek",
        "san": "Sanskrit",
        "all": "Multilingual",
        "": "Source",
    }.get(language, language)


def _display_key(row: Mapping[str, object]) -> str:
    display = row.get("display")
    if isinstance(display, Mapping):
        display_map = cast(Mapping[str, object], display)
        primary = str(display_map.get("primary") or "").strip()
        if primary:
            return primary
        transliteration = str(display_map.get("transliteration") or "").strip()
        if transliteration:
            return transliteration
        source_key = str(display_map.get("source_key") or "").strip()
        if source_key:
            return source_key
    return str(row.get("canonical_name") or row.get("source_name") or row.get("lookup") or "")


def _id_component(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", (value or "").strip().lower())
    if not normalized.strip("-"):
        normalized = _greek_ascii_key(value)
    return normalized.strip("-") or "unknown"


def _cdsl_statuses(
    paths: WordIndexPaths,
    languages: Sequence[LanguageCode],
) -> list[dict[str, object]]:
    if "san" not in languages:
        return []
    return [
        _duckdb_status("cdsl", "san", "mw", paths.cdsl_mw, "headwords", "is_primary = true"),
        _duckdb_status("cdsl", "san", "ap90", paths.cdsl_ap90, "headwords", "is_primary = true"),
    ]


def _dico_status(
    paths: WordIndexPaths,
    languages: Sequence[LanguageCode],
) -> dict[str, object] | None:
    if "san" not in languages:
        return None
    return _duckdb_status("dico", "san", "dico", paths.dico, "entries_fr")


def _gaffiot_status(
    paths: WordIndexPaths,
    languages: Sequence[LanguageCode],
) -> dict[str, object] | None:
    if "lat" not in languages:
        return None
    return _duckdb_status("gaffiot", "lat", "gaffiot", paths.gaffiot, "entries_fr")


def _lewis_1890_status(
    paths: WordIndexPaths,
    languages: Sequence[LanguageCode],
) -> dict[str, object] | None:
    if "lat" not in languages:
        return None
    return _duckdb_status("lewis_1890", "lat", "lewis_1890", paths.lewis_1890, "entries")


def _georges_1913_status(
    paths: WordIndexPaths,
    languages: Sequence[LanguageCode],
) -> dict[str, object] | None:
    if "lat" not in languages:
        return None
    return _duckdb_status("georges_1913", "lat", "georges_1913", paths.georges_1913, "entries_fr")


def _whitakers_status(
    paths: WordIndexPaths,
    languages: Sequence[LanguageCode],
) -> dict[str, object] | None:
    if "lat" not in languages:
        return None
    return _duckdb_status("whitakers", "lat", "whitakers", paths.whitakers, "entries")


def _bailly_status(
    paths: WordIndexPaths,
    languages: Sequence[LanguageCode],
) -> dict[str, object] | None:
    if "grc" not in languages:
        return None
    return _duckdb_status("bailly", "grc", "bailly", paths.bailly, "entries")


def _strongs_greek_status(
    paths: WordIndexPaths,
    languages: Sequence[LanguageCode],
) -> dict[str, object] | None:
    if "grc" not in languages:
        return None
    status = _duckdb_status("strongs_greek", "grc", "strongs_greek", paths.strongs_greek, "entries")
    status["dictionary_genre"] = "religious"
    return status


def _diogenes_statuses(
    paths: WordIndexPaths,
    languages: Sequence[LanguageCode],
) -> list[dict[str, object]]:
    statuses: list[dict[str, object]] = []
    for language in languages:
        if language not in {"lat", "grc"}:
            continue
        path = paths.diogenes_grc if language == "grc" else paths.diogenes_lat
        statuses.append(
            _duckdb_status(
                "diogenes",
                language,
                "lsj" if language == "grc" else "lewis_short",
                path,
                "entries",
                f"language = '{language}'",
            )
        )
    return statuses


def _duckdb_status(  # noqa: PLR0913
    source: str,
    language: LanguageCode,
    dictionary: str,
    path: Path,
    table: str,
    where: str = "",
) -> dict[str, object]:
    payload: dict[str, object] = {
        "source": source,
        "language": language,
        "dictionary": dictionary,
        "available": path.exists(),
        "entry_count": 0,
        "path": str(path),
    }
    if not path.exists():
        payload["message"] = "index database is missing"
        return payload
    try:
        with connect_duckdb_ro(path) as conn:
            sql = f"SELECT COUNT(*) FROM {table}"
            if where:
                sql += f" WHERE {where}"
            row = conn.execute(sql).fetchone()
            payload["entry_count"] = int(row[0]) if row else 0
    except Exception as exc:  # noqa: BLE001
        payload["available"] = False
        payload["message"] = f"{type(exc).__name__}: {exc}"
    return payload


def _warn_missing(warnings: list[dict[str, str]], source: str, path: Path) -> None:
    warnings.append({"source": source, "message": f"word index database is missing: {path}"})


def _warn_error(warnings: list[dict[str, str]], source: str, path: Path, exc: Exception) -> None:
    warnings.append(
        {
            "source": source,
            "message": f"failed reading {path}: {type(exc).__name__}: {exc}",
        }
    )


def _cursor_offset(cursor: str | None) -> int:
    if not cursor:
        return 0
    with suppress(ValueError):
        return max(0, int(cursor))
    return 0


def _interleave(
    items: Sequence[dict[str, object]],
    *,
    limit: int,
    offset: int,
) -> list[dict[str, object]]:
    if limit <= 0:
        return list(items)
    buckets: dict[str, list[dict[str, object]]] = defaultdict(list)
    for item in items:
        buckets[str(item.get("language") or "")].append(item)
    ordered_languages = [language for language in ("san", "grc", "lat") if language in buckets]
    if len(ordered_languages) <= 1:
        return list(items[offset : offset + limit])
    out: list[dict[str, object]] = []
    positions = {language: 0 for language in ordered_languages}
    while len(out) < offset + limit:
        advanced = False
        for language in ordered_languages:
            pos = positions[language]
            bucket = buckets[language]
            if pos >= len(bucket):
                continue
            out.append(bucket[pos])
            positions[language] = pos + 1
            advanced = True
        if not advanced:
            break
    return out[offset : offset + limit]


def _interleave_wheel(
    items: Sequence[dict[str, object]],
    *,
    limit: int,
) -> list[dict[str, object]]:
    if limit <= 0:
        return list(items)
    language_buckets: dict[str, list[dict[str, object]]] = defaultdict(list)
    for item in items:
        language_buckets[str(item.get("language") or "")].append(item)
    language_streams = {
        language: _source_interleaved_stream(bucket)
        for language, bucket in language_buckets.items()
    }
    ordered_languages = [
        language for language in ("san", "grc", "lat") if language in language_streams
    ]
    out: list[dict[str, object]] = []
    positions = {language: 0 for language in ordered_languages}
    while len(out) < limit:
        advanced = False
        for language in ordered_languages:
            stream = language_streams[language]
            pos = positions[language]
            if pos >= len(stream):
                continue
            out.append(stream[pos])
            positions[language] = pos + 1
            advanced = True
            if len(out) >= limit:
                break
        if not advanced:
            break
    return out


def _source_interleaved_stream(items: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    buckets: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for item in items:
        key = (str(item.get("source") or ""), str(item.get("dictionary") or ""))
        buckets[key].append(item)
    ordered_keys = sorted(
        buckets,
        key=lambda key: (_SOURCE_ORDER.get(key[0], 9), key[1]),
    )
    out: list[dict[str, object]] = []
    positions = {key: 0 for key in ordered_keys}
    while True:
        advanced = False
        for key in ordered_keys:
            pos = positions[key]
            bucket = buckets[key]
            if pos >= len(bucket):
                continue
            out.append(bucket[pos])
            positions[key] = pos + 1
            advanced = True
        if not advanced:
            return out


def _wheel_lexeme_cards(items: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    order: list[str] = []
    for item in items:
        lexeme_id = str(item.get("lexeme_id") or "")
        if not lexeme_id:
            continue
        if lexeme_id not in grouped:
            grouped[lexeme_id] = []
            order.append(lexeme_id)
        grouped[lexeme_id].append(item)
    return [_wheel_lexeme_card(grouped[lexeme_id]) for lexeme_id in order]


def _wheel_lexeme_card(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    primary = dict(rows[0])
    source_entries = [_source_entry_summary(row) for row in sorted(rows, key=_source_entry_key)]
    native_order_keys = [
        str(row.get("native_order_key") or "") for row in rows if row.get("native_order_key")
    ]
    sources = [
        {"source": source, "dictionary": dictionary}
        for source, dictionary in dict.fromkeys(
            (str(row.get("source") or ""), str(row.get("dictionary") or "")) for row in rows
        )
    ]
    ids = dict(cast(Mapping[str, object], primary.get("ids") or {}))
    ids["source_entries"] = [entry["index_entry_id"] for entry in source_entries]
    primary["ids"] = ids
    primary["source_entries"] = source_entries
    primary["source_count"] = len(sources)
    primary["source_entry_count"] = len(source_entries)
    primary["sources"] = sources
    primary["native_order_key"] = min(native_order_keys) if native_order_keys else ""
    primary["order"] = _lexeme_card_order_metadata(primary)
    return primary


def _source_entry_summary(row: Mapping[str, object]) -> dict[str, object]:
    return {
        "index_entry_id": row.get("index_entry_id") or "",
        "source_order_id": row.get("source_order_id") or "",
        "wheel_id": row.get("wheel_id") or "",
        "wheel_order_key": row.get("wheel_order_key") or "",
        "lexeme_key": row.get("lexeme_key") or "",
        "source": row.get("source") or "",
        "dictionary": row.get("dictionary") or "",
        "source_name": row.get("source_name") or "",
        "source_display": row.get("source_name") or row.get("canonical_name") or "",
        "source_ref": row.get("source_ref") or "",
        "source_order_key": row.get("source_order_key") or "",
        "native_order_key": row.get("native_order_key") or "",
        "order": row.get("order") or {},
        "display": row.get("display") or {},
        "encounter": row.get("encounter") or {},
        "metadata": row.get("metadata") or {},
    }


def _source_entry_key(row: Mapping[str, object]) -> tuple[int, str, str]:
    return (
        _SOURCE_ORDER.get(str(row.get("source") or ""), 9),
        str(row.get("dictionary") or ""),
        str(row.get("source_order_id") or ""),
    )


def _strip_source_variant_label(value: str, *, fallback: str) -> str:
    stripped = re.sub(r"^\s*\d+\s+", "", value or "").strip()
    return stripped or fallback


def _collapse_list_lexemes(source: str) -> bool:
    return source.strip().lower() == "all"


def _canonical_item_order_key(item: Mapping[str, object]) -> tuple[str, int, str, str]:
    return (
        str(item.get("wheel_order_key") or ""),
        _SOURCE_ORDER.get(str(item.get("source") or ""), 9),
        str(item.get("dictionary") or ""),
        str(item.get("source_ref") or ""),
    )


def _language_native_card_order_key(item: Mapping[str, object]) -> tuple[int, str, str]:
    language = str(item.get("language") or "")
    canonical_key = str(item.get("canonical_key") or "")
    language_rank = _LANGUAGE_ORDER.get(cast(LanguageCode, language), 9)
    native_order_key = str(item.get("native_order_key") or "")
    if native_order_key:
        return (language_rank, native_order_key, canonical_key)
    if language == "san":
        return (language_rank, _sanskrit_native_card_order_key(item), canonical_key)
    return (language_rank, canonical_key, str(item.get("lexeme_id") or ""))


def _sanskrit_native_card_order_key(item: Mapping[str, object]) -> str:
    for value in _sanskrit_native_order_candidates(item):
        slp1 = _sanskrit_order_slp1(value)
        if slp1:
            return _sanskrit_native_order_key(slp1)
    return _sanskrit_native_order_key(str(item.get("canonical_key") or ""))


def _sanskrit_native_order_candidates(  # noqa: C901, PLR0912
    item: Mapping[str, object],
) -> list[str]:
    candidates: list[str] = []
    source_entries = item.get("source_entries")
    if isinstance(source_entries, Sequence) and not isinstance(source_entries, (str, bytes)):
        entries = [
            cast(Mapping[str, object], entry)
            for entry in source_entries
            if isinstance(entry, Mapping)
        ]
        for entry in entries:
            if entry.get("source") == "cdsl":
                source_name = str(entry.get("source_name") or "").strip()
                if source_name:
                    candidates.append(source_name)
        for entry in entries:
            display = entry.get("display")
            if isinstance(display, Mapping):
                display_map = cast(Mapping[str, object], display)
                transliteration = str(display_map.get("transliteration") or "").strip()
                if transliteration:
                    candidates.append(transliteration)
                source_key = str(display_map.get("source_key") or "").strip()
                if source_key:
                    candidates.append(source_key)
            source_name = str(entry.get("source_name") or "").strip()
            if source_name:
                candidates.append(source_name)
    display = item.get("display")
    if isinstance(display, Mapping):
        display_map = cast(Mapping[str, object], display)
        transliteration = str(display_map.get("transliteration") or "").strip()
        if transliteration:
            candidates.append(transliteration)
        source_key = str(display_map.get("source_key") or "").strip()
        if source_key:
            candidates.append(source_key)
    for field in ("source_name", "lookup", "canonical_name", "canonical_key"):
        value = str(item.get(field) or "").strip()
        if value:
            candidates.append(value)
    return list(dict.fromkeys(candidates))


def _sanskrit_order_slp1(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    plain = _plain_index_key(text)
    plain_single = _sanskrit_plain_single_slp1(text)
    if (
        text.isascii()
        and not any(marker in text for marker in (".", '"', "~"))
        and plain_single
        and any(marker in plain for marker in ("aa", "ii", "uu", "ai", "au", "rr", "ll", "sh"))
    ):
        return plain_single
    with suppress(Exception):
        converted = _to_slp1(text)
        if converted:
            return re.sub(r"[^A-Za-z]+", "", converted)
    return plain_single or re.sub(r"[^A-Za-z]+", "", text)


def _sanskrit_plain_single_slp1(value: str) -> str:
    slots = _sanskrit_plain_slp1_slots(_plain_index_key(value))
    if not slots:
        return ""
    return "".join(slot[0] for slot in slots)


def _sanskrit_native_order_key(slp1: str) -> str:
    clean = re.sub(r"[^A-Za-z]+", "", slp1)
    slots = _sanskrit_native_order_slots()
    out: list[str] = []
    index = 0
    while index < len(clean):
        matched = False
        for token, rank in slots:
            if clean.startswith(token, index):
                out.append(f"{rank:03d}")
                index += len(token)
                matched = True
                break
        if not matched:
            out.append(f"999{ord(clean[index]):04d}")
            index += 1
    return ".".join(out)


def _sanskrit_native_order_slots() -> list[tuple[str, int]]:
    tokens = [
        "a",
        "A",
        "i",
        "I",
        "u",
        "U",
        "f",
        "F",
        "x",
        "X",
        "e",
        "E",
        "o",
        "O",
        "M",
        "H",
        "k",
        "K",
        "g",
        "G",
        "N",
        "c",
        "C",
        "j",
        "J",
        "Y",
        "w",
        "W",
        "q",
        "Q",
        "R",
        "t",
        "T",
        "d",
        "D",
        "n",
        "p",
        "P",
        "b",
        "B",
        "m",
        "y",
        "r",
        "l",
        "v",
        "S",
        "z",
        "s",
        "h",
        "kz",
        "tr",
        "jY",
    ]
    ranks = {token: rank for rank, token in enumerate(tokens, start=1)}
    return sorted(ranks.items(), key=lambda item: (-len(item[0]), item[1]))


def _item_order_key(item: Mapping[str, object]) -> tuple[int, int, str, str]:
    return (
        _LANGUAGE_ORDER.get(str(item.get("language")), 9),
        _SOURCE_ORDER.get(str(item.get("source")), 9),
        str(item.get("wheel_order_key") or ""),
        str(item.get("source_ref") or ""),
    )


def _best_anchor(
    items: Sequence[dict[str, object]],
    query: str,
) -> dict[str, object] | None:
    best_item: dict[str, object] | None = None
    best_score = 0
    for item in items:
        score = _anchor_score(item, query)
        if score > best_score:
            best_item = item
            best_score = score
    return best_item


def _merged_lexeme_neighborhood(  # noqa: C901, PLR0913
    neighborhoods: Sequence[dict[str, object]],
    *,
    query: str,
    radius: int,
    languages: Sequence[LanguageCode],
    source: str,
    paths: WordIndexPaths,
    warnings: list[dict[str, str]],
) -> dict[str, object]:
    positioned_rows: list[tuple[str, dict[str, object]]] = []
    source_anchors: list[dict[str, object]] = []
    source_anchor_statuses: dict[str, str] = {}
    for neighborhood in neighborhoods:
        anchor = neighborhood.get("anchor")
        if isinstance(anchor, Mapping):
            anchor_row = dict(cast(Mapping[str, object], anchor))
            positioned_rows.append(("anchor", anchor_row))
            source_anchors.append(anchor_row)
            lexeme_id = str(anchor_row.get("lexeme_id") or "")
            if lexeme_id:
                source_anchor_statuses[lexeme_id] = _best_anchor_status(
                    source_anchor_statuses.get(lexeme_id),
                    str(neighborhood.get("anchor_status") or ""),
                )
        for position in ("before", "after"):
            values = neighborhood.get(position)
            if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
                continue
            for item in values:
                if isinstance(item, Mapping):
                    positioned_rows.append((position, dict(cast(Mapping[str, object], item))))

    anchor_row = _best_anchor(source_anchors, query) or (
        source_anchors[0] if source_anchors else None
    )
    anchor_lexeme_id = str(anchor_row.get("lexeme_id") or "") if anchor_row else ""
    grouped: dict[str, list[dict[str, object]]] = {}
    positions_by_lexeme: dict[str, set[str]] = defaultdict(set)
    for position, row in positioned_rows:
        lexeme_id = str(row.get("lexeme_id") or "")
        if not lexeme_id:
            continue
        grouped.setdefault(lexeme_id, []).append(row)
        positions_by_lexeme[lexeme_id].add(position)

    cards: list[dict[str, object]] = []
    for lexeme_id, rows in grouped.items():
        unique_rows = _unique_source_rows(rows)
        card = _wheel_lexeme_card(sorted(unique_rows, key=_source_entry_key))
        position = _merged_position(
            lexeme_id,
            anchor_lexeme_id=anchor_lexeme_id,
            positions=positions_by_lexeme[lexeme_id],
        )
        card["position"] = position
        card["match"] = position == "anchor"
        cards.append(card)
    cards.sort(key=_canonical_item_order_key)

    if anchor_lexeme_id:
        cards = [
            _hydrate_merged_anchor_card(
                card,
                languages=languages,
                source=source,
                paths=paths,
                warnings=warnings,
            )
            if str(card.get("lexeme_id") or "") == anchor_lexeme_id
            else card
            for card in cards
        ]

    selected = _select_merged_radius(cards, anchor_lexeme_id=anchor_lexeme_id, radius=radius)
    anchor_card = next(
        (card for card in selected if str(card.get("lexeme_id") or "") == anchor_lexeme_id),
        None,
    )
    if anchor_card is None and anchor_lexeme_id:
        anchor_card = next(
            (card for card in cards if str(card.get("lexeme_id") or "") == anchor_lexeme_id),
            None,
        )
    anchor_status = source_anchor_statuses.get(anchor_lexeme_id, "not_found")
    language_code = str(anchor_card.get("language", "") if anchor_card else "")
    return {
        "policy": "merged_lexeme",
        "language": language_code,
        "source": "all",
        "dictionary": "merged",
        "anchor": anchor_card,
        "items": selected,
        "groups": list(neighborhoods),
        "radius": radius,
        "neighborhood_kind": "merged_lexeme",
        "anchor_status": anchor_status,
        "order": _merged_neighborhood_order_metadata(
            language=language_code,
            query=query,
            anchor_status=anchor_status,
        ),
        "window": {
            "policy": "merged_lexeme_from_source_windows",
            "contiguous": False,
            "collapsed": True,
            "before_count": sum(1 for item in selected if item.get("position") == "before"),
            "after_count": sum(1 for item in selected if item.get("position") == "after"),
            "source_group_count": len(neighborhoods),
            "lexeme_count": len(selected),
        },
    }


def _integrated_language_native_neighborhood(  # noqa: PLR0913
    neighborhoods: Sequence[dict[str, object]],
    *,
    query: str,
    radius: int,
    languages: Sequence[LanguageCode],
    source: str,
    paths: WordIndexPaths,
    warnings: list[dict[str, str]],
) -> dict[str, object]:
    rows = _integrated_candidate_rows(
        neighborhoods,
        query=query,
        radius=radius,
        languages=languages,
        source=source,
        paths=paths,
        warnings=warnings,
    )
    cards = _wheel_lexeme_cards(rows)
    cards.sort(key=_language_native_card_order_key)
    anchor_card = _integrated_exact_source_anchor_card(cards, neighborhoods, query) or _best_anchor(
        cards, query
    )
    anchor_lexeme_id = str(anchor_card.get("lexeme_id") or "") if anchor_card else ""
    anchor_status = "exact" if anchor_card and _is_exact_anchor(anchor_card, query) else "nearest"
    if anchor_card is None:
        anchor_status = "not_found"
    selected = _select_merged_radius(cards, anchor_lexeme_id=anchor_lexeme_id, radius=radius)
    for card in selected:
        position = _integrated_position(
            str(card.get("lexeme_id") or ""),
            anchor_lexeme_id=anchor_lexeme_id,
            cards=cards,
        )
        card["position"] = position
        card["match"] = position == "anchor"
    selected_anchor = next(
        (card for card in selected if str(card.get("lexeme_id") or "") == anchor_lexeme_id),
        anchor_card,
    )
    language_code = str(selected_anchor.get("language", "") if selected_anchor else "")
    return {
        "policy": "integrated_language_native",
        "language": language_code,
        "source": "all",
        "dictionary": "integrated",
        "anchor": selected_anchor,
        "items": selected,
        "groups": list(neighborhoods),
        "radius": radius,
        "neighborhood_kind": "integrated_language_native",
        "anchor_status": anchor_status,
        "order": _integrated_language_native_order_metadata(
            language=language_code,
            query=query,
            anchor_status=anchor_status,
        ),
        "window": {
            "policy": "integrated_language_native",
            "contiguous": False,
            "collapsed": True,
            "before_count": sum(1 for item in selected if item.get("position") == "before"),
            "after_count": sum(1 for item in selected if item.get("position") == "after"),
            "source_group_count": len(neighborhoods),
            "lexeme_count": len(selected),
        },
    }


def _integrated_exact_source_anchor_card(
    cards: Sequence[dict[str, object]],
    neighborhoods: Sequence[dict[str, object]],
    query: str,
) -> dict[str, object] | None:
    exact_source_anchors = [
        dict(cast(Mapping[str, object], anchor))
        for neighborhood in neighborhoods
        if str(neighborhood.get("anchor_status") or "") == "exact"
        if isinstance((anchor := neighborhood.get("anchor")), Mapping)
    ]
    exact_anchor = _best_anchor(exact_source_anchors, query)
    if exact_anchor is None:
        return None

    exact_lexeme_id = str(exact_anchor.get("lexeme_id") or "")
    if not exact_lexeme_id:
        return None
    return next(
        (card for card in cards if str(card.get("lexeme_id") or "") == exact_lexeme_id),
        None,
    )


def _integrated_candidate_rows(  # noqa: PLR0913
    neighborhoods: Sequence[dict[str, object]],
    *,
    query: str,
    radius: int,
    languages: Sequence[LanguageCode],
    source: str,
    paths: WordIndexPaths,
    warnings: list[dict[str, str]],
) -> list[dict[str, object]]:
    rows = _neighborhood_source_rows(neighborhoods)
    limit = _integrated_candidate_prefix_limit(radius)
    for prefix in _integrated_candidate_prefixes(
        query=query,
        languages=languages,
        neighborhoods=neighborhoods,
    ):
        rows.extend(
            _collect_items(
                languages=languages,
                source=source,
                prefix=prefix,
                limit=limit,
                paths=paths,
                warnings=warnings,
            )
        )
    return _unique_source_rows(rows)


def _neighborhood_source_rows(
    neighborhoods: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for neighborhood in neighborhoods:
        for key in ("anchor",):
            value = neighborhood.get(key)
            if isinstance(value, Mapping):
                rows.append(dict(cast(Mapping[str, object], value)))
        for key in ("before", "after"):
            values = neighborhood.get(key)
            if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
                continue
            for value in values:
                if isinstance(value, Mapping):
                    rows.append(dict(cast(Mapping[str, object], value)))
    return rows


def _integrated_candidate_prefix_limit(radius: int) -> int:
    return max(50, min(500, (radius + 1) * 50))


def _integrated_candidate_prefixes(
    *,
    query: str,
    languages: Sequence[LanguageCode],
    neighborhoods: Sequence[dict[str, object]],
) -> list[str]:
    language = languages[0] if len(languages) == 1 else "all"
    anchor = _best_anchor(
        [
            cast(dict[str, object], neighborhood["anchor"])
            for neighborhood in neighborhoods
            if isinstance(neighborhood.get("anchor"), Mapping)
        ],
        query,
    )
    seed = _integrated_prefix_seed(query=query, language=language, anchor=anchor)
    if language == "san":
        return _sanskrit_integrated_prefixes(seed)
    if language == "grc":
        return _alphabetic_integrated_prefixes(seed, alphabet="abcdefghijklmnopqrstuvwxyz")
    if language == "lat":
        return _alphabetic_integrated_prefixes(seed, alphabet="abcdefghijklmnopqrstuvwxyz")
    return [seed] if seed else []


def _integrated_prefix_seed(
    *,
    query: str,
    language: LanguageCode | str,
    anchor: Mapping[str, object] | None,
) -> str:
    if anchor is not None:
        if language == "san":
            return _sanskrit_order_slp1(
                str(anchor.get("source_name") or "")
                if anchor.get("source") == "cdsl"
                else str(anchor.get("lookup") or anchor.get("canonical_key") or "")
            )
        return str(
            anchor.get("sort_key") or anchor.get("lookup") or anchor.get("canonical_key") or ""
        )
    if language == "san":
        return _sanskrit_order_slp1(query)
    if language == "grc":
        keys = sorted(_query_keys(query))
        return keys[0] if keys else _plain_index_key(query)
    return _plain_index_key(query)


def _alphabetic_integrated_prefixes(seed: str, *, alphabet: str) -> list[str]:
    if not seed:
        return []
    first = seed[:1].lower()
    if first not in alphabet:
        return [first]
    index = alphabet.index(first)
    prefixes = [alphabet[pos] for pos in (index - 1, index, index + 1) if 0 <= pos < len(alphabet)]
    return list(dict.fromkeys(prefixes))


def _sanskrit_integrated_prefixes(seed: str) -> list[str]:
    token = _sanskrit_initial_order_token(seed)
    if not token:
        return []
    order = _sanskrit_integrated_section_order()
    if token not in order:
        return _sanskrit_source_prefix_variants(token)
    index = order.index(token)
    prefixes: list[str] = []
    for pos in (index - 1, index, index + 1):
        if 0 <= pos < len(order):
            prefixes.extend(_sanskrit_source_prefix_variants(order[pos]))
    return list(dict.fromkeys(prefixes))


def _sanskrit_initial_order_token(seed: str) -> str:
    slp1 = _sanskrit_order_slp1(seed)
    for token, _rank in _sanskrit_native_order_slots():
        if slp1.startswith(token):
            return token
    return slp1[:1]


def _sanskrit_source_prefix_variants(token: str) -> list[str]:
    variants = [token]
    iast = _slp1_to_iast(token)
    if iast and iast != token:
        variants.append(iast)
        variants.append(_plain_index_key(iast))
    return [variant for variant in dict.fromkeys(variants) if variant]


def _sanskrit_integrated_section_order() -> list[str]:
    return [
        token for token, _rank in sorted(_sanskrit_native_order_slots(), key=lambda item: item[1])
    ]


def _hydrate_merged_anchor_card(
    card: dict[str, object],
    *,
    languages: Sequence[LanguageCode],
    source: str,
    paths: WordIndexPaths,
    warnings: list[dict[str, str]],
) -> dict[str, object]:
    lexeme_id = str(card.get("lexeme_id") or "")
    canonical_key = str(card.get("canonical_key") or "")
    if not lexeme_id or not canonical_key:
        return card

    rows = _collect_items(
        languages=languages,
        source=source,
        prefix=canonical_key,
        limit=ANCHOR_HYDRATION_LIMIT,
        paths=paths,
        warnings=warnings,
    )
    matching_rows = [row for row in rows if str(row.get("lexeme_id") or "") == lexeme_id]
    if not matching_rows:
        return card

    hydrated = _wheel_lexeme_card(sorted(matching_rows, key=_source_entry_key))
    hydrated["position"] = "anchor"
    hydrated["match"] = True
    return hydrated


def _best_anchor_status(current: str | None, candidate: str) -> str:
    order = {"exact": 0, "nearest": 1, "not_found": 2}
    current = current or "not_found"
    candidate = candidate or "not_found"
    return candidate if order.get(candidate, 9) < order.get(current, 9) else current


def _unique_source_rows(rows: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    unique: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = (str(row.get("index_entry_id") or ""), str(row.get("source_ref") or ""))
        if key in seen:
            continue
        seen.add(key)
        unique.append(dict(row))
    return unique


def _merged_position(
    lexeme_id: str,
    *,
    anchor_lexeme_id: str,
    positions: set[str],
) -> str:
    if lexeme_id == anchor_lexeme_id or "anchor" in positions:
        return "anchor"
    if "before" in positions and "after" in positions:
        return "nearby"
    if "before" in positions:
        return "before"
    if "after" in positions:
        return "after"
    return "nearby"


def _select_merged_radius(
    cards: Sequence[dict[str, object]],
    *,
    anchor_lexeme_id: str,
    radius: int,
) -> list[dict[str, object]]:
    if not anchor_lexeme_id:
        return list(cards)
    anchor_index = next(
        (
            index
            for index, card in enumerate(cards)
            if str(card.get("lexeme_id") or "") == anchor_lexeme_id
        ),
        -1,
    )
    if anchor_index < 0:
        return list(cards)
    start = max(0, anchor_index - radius)
    end = min(len(cards), anchor_index + radius + 1)
    return list(cards[start:end])


def _integrated_position(
    lexeme_id: str,
    *,
    anchor_lexeme_id: str,
    cards: Sequence[Mapping[str, object]],
) -> str:
    if lexeme_id == anchor_lexeme_id:
        return "anchor"
    positions = {str(card.get("lexeme_id") or ""): index for index, card in enumerate(cards)}
    current = positions.get(lexeme_id, -1)
    anchor = positions.get(anchor_lexeme_id, -1)
    if current < 0 or anchor < 0:
        return "nearby"
    return "before" if current < anchor else "after"


def _neighborhood(
    anchor: dict[str, object],
    *,
    before: list[dict[str, object]],
    after: list[dict[str, object]],
    radius: int,
    query: str,
) -> dict[str, object]:
    anchor_status = "exact" if _is_exact_anchor(anchor, query) else "nearest"
    return {
        "language": anchor["language"],
        "source": anchor["source"],
        "dictionary": anchor.get("dictionary", ""),
        "anchor": anchor,
        "before": before,
        "after": after,
        "radius": radius,
        "neighborhood_kind": "lexical_order",
        "anchor_status": anchor_status,
        "order": _neighborhood_order_metadata(anchor, anchor_status=anchor_status),
        "window": {
            "policy": "source_entry_contiguous",
            "contiguous": True,
            "collapsed": False,
            "before_count": len(before),
            "after_count": len(after),
            "source_entry_count": len(before) + 1 + len(after),
        },
    }


def _is_exact_anchor(item: Mapping[str, object], query: str) -> bool:
    query_norm = query.strip().lower()
    if not query_norm:
        return False
    query_plain = _plain_index_key(query_norm)
    query_keys = _match_keys(query_norm)
    canonical_key = str(item.get("canonical_key") or "").strip().lower()
    source_name = str(item.get("source_name") or "").strip().lower()
    if canonical_key and canonical_key in _exact_canonical_query_keys(
        query_norm, query_plain, query_keys
    ):
        return True
    return bool(
        source_name
        and not _contains_non_ascii(query_norm)
        and (source_name == query_norm or _plain_index_key(source_name) == query_plain)
    )


def _anchor_score(item: Mapping[str, object], query: str) -> int:
    query_raw = query.strip()
    query_norm = query_raw.lower()
    if not query_raw:
        return 0
    query_dico = normalize_dico_headword(query_norm)
    query_plain = _plain_index_key(query_norm)
    query_keys = _match_keys(query_norm)
    expanded_anchor_keys = set(_query_keys(query_norm))
    expanded_query_keys = _expanded_query_keys(query_norm)
    canonical_key = str(item.get("canonical_key") or "").strip().lower()
    source_name_raw = str(item.get("source_name") or "").strip()
    if source_name_raw == query_raw:
        return 130
    source_name = source_name_raw.lower()
    initial_score = _direct_anchor_score(
        canonical_key=canonical_key,
        source_name=source_name,
        query_norm=query_norm,
        query_plain=query_plain,
        query_keys=query_keys,
        expanded_query_keys=expanded_query_keys,
    )
    if initial_score:
        return initial_score

    item_values = _item_match_values(item)
    best = 0
    for value in item_values:
        value_norm = value.strip().lower()
        if not value_norm:
            continue
        best = max(
            best,
            _anchor_value_score(
                value_norm,
                query_norm=query_norm,
                query_plain=query_plain,
                query_dico=query_dico,
            ),
        )
    item_keys = set(_match_keys(*item_values))
    canonical_key = str(item.get("canonical_key") or "").strip().lower()
    if canonical_key and canonical_key in expanded_anchor_keys:
        best = max(best, 75)
    if expanded_anchor_keys & item_keys:
        best = max(best, 10)
    return best


def _anchor_value_score(
    value_norm: str,
    *,
    query_norm: str,
    query_plain: str,
    query_dico: str,
) -> int:
    if value_norm == query_norm:
        return 100
    if _plain_index_key(value_norm) == query_plain:
        return 85
    if normalize_dico_headword(value_norm) == query_dico:
        return 60
    return 0


def _direct_anchor_score(  # noqa: PLR0913
    *,
    canonical_key: str,
    source_name: str,
    query_norm: str,
    query_plain: str,
    query_keys: set[str],
    expanded_query_keys: set[str],
) -> int:
    if canonical_key and canonical_key in _exact_canonical_query_keys(
        query_norm, query_plain, query_keys
    ):
        return 120
    if source_name and (source_name == query_norm or _plain_index_key(source_name) == query_plain):
        return 115
    if canonical_key and canonical_key in expanded_query_keys:
        return 80
    return 0


def _exact_canonical_query_keys(
    query_norm: str,
    query_plain: str,
    _query_keys: set[str],
) -> set[str]:
    keys = {query_norm, query_plain}
    keys.update(_sanskrit_final_a_variants(query_norm))
    keys.update(_sanskrit_final_s_variants(query_norm))
    keys.update(_greek_latinized_query_keys(query_norm))
    if _contains_non_ascii(query_norm):
        keys.update(_native_canonical_keys(query_norm))
    return keys


def _contains_non_ascii(value: str) -> bool:
    return any(ord(char) >= NON_ASCII_CODEPOINT_MIN for char in value)


def _native_canonical_keys(query_norm: str) -> set[str]:
    keys: set[str] = set()
    with suppress(Exception):
        keys.add(_plain_index_key(to_heritage_velthuis(query_norm).lower()))
    greek_key = _greek_ascii_key(query_norm)
    if greek_key:
        keys.add(greek_key)
    return {key for key in keys if key}


def _expanded_query_keys(query_norm: str) -> set[str]:
    return {key for key in _sanskrit_unmarked_length_variants(_plain_index_key(query_norm)) if key}


def _sanskrit_unmarked_length_variants(value: str) -> set[str]:
    if not value or not value.isascii() or not value.isalpha():
        return set()
    variants: set[str] = set()
    for index, char in enumerate(value):
        if char in {"a", "i", "u"}:
            variants.add(f"{value[:index]}{char}{value[index:]}")
    return variants


def _item_match_values(item: Mapping[str, object]) -> list[str]:
    display = item.get("display")
    display_map = (
        cast(Mapping[str, object], display)
        if isinstance(display, Mapping)
        else cast(Mapping[str, object], {})
    )
    return [
        str(item.get("canonical_key") or ""),
        str(item.get("source_name") or ""),
        str(item.get("lookup") or ""),
        str(item.get("canonical_name") or ""),
        str(item.get("sort_key") or ""),
        str(display_map.get("source_key") or ""),
        str(display_map.get("transliteration") or ""),
    ]


def _match_keys(*values: str) -> set[str]:
    keys: set[str] = set()
    for value in values:
        normalized = value.strip().lower()
        if not normalized:
            continue
        keys.add(normalized)
        keys.add(normalize_dico_headword(normalized))
        keys.add(_plain_index_key(normalized))
        keys.add(normalize_gaffiot_headword(normalized))
        strongs_key = normalize_strongs_greek_key(normalized)
        if strongs_key:
            keys.add(strongs_key)
        with suppress(Exception):
            velthuis = to_heritage_velthuis(normalized).lower()
            if velthuis and velthuis != normalized:
                keys.add(velthuis)
                keys.add(_plain_index_key(velthuis))
                keys.add(_to_slp1(velthuis).lower())
        greek_key = _greek_ascii_key(normalized)
        if greek_key:
            keys.add(greek_key)
        keys.update(_greek_latinized_query_keys(normalized))
        with suppress(Exception):
            keys.add(_to_slp1(normalized).lower())
        with suppress(Exception):
            keys.add(_slp1_to_iast(normalized).lower())
    return {key for key in keys if key}


def _query_keys(query: str) -> list[str]:
    keys = set(_match_keys(query))
    pitchless = _strip_sanskrit_pitch_accents(query)
    if pitchless and pitchless != query:
        keys.update(_match_keys(pitchless))
    keys.update(_plain_index_key(key) for key in list(keys))
    keys.update(_expanded_query_keys(query))
    keys.update(_sanskrit_plain_slp1_keys(query))
    for final_s_variant in _sanskrit_final_s_variants(query):
        keys.update(_match_keys(final_s_variant))
        keys.update(_sanskrit_plain_slp1_keys(final_s_variant))
        keys.update(_sanskrit_final_a_variants(final_s_variant))
    for final_a_variant in _sanskrit_final_a_variants(query):
        keys.update(_match_keys(final_a_variant))
        keys.update(_sanskrit_plain_slp1_keys(final_a_variant))
    return sorted(key for key in keys if key)


def _sanskrit_final_a_variants(query: str) -> set[str]:
    plain = _plain_index_key(query)
    if not plain or not plain.isascii() or not plain.isalpha():
        return set()
    if len(plain) < SANSKRIT_FINAL_A_MIN_LENGTH or plain.endswith(("a", "i", "u", "e", "o")):
        return set()
    return {f"{plain}a"}


def _sanskrit_final_s_variants(query: str) -> set[str]:
    if not _has_sanskrit_final_s_stem_signal(_strip_sanskrit_pitch_accents(query)):
        return set()
    values = {_strip_sanskrit_pitch_accents(query), _plain_index_key(query)}
    variants: set[str] = set()
    for value in values:
        plain = _plain_index_key(value)
        if plain.isascii() and plain.isalpha() and plain.endswith("s"):
            variants.add(plain[:-1])
    return variants


def _has_sanskrit_final_s_stem_signal(value: str) -> bool:
    stripped = (value or "").strip()
    if not stripped.lower().endswith("s"):
        return False
    stem = stripped[:-1]
    return bool(stem) and any(char in _SANSKRIT_FINAL_S_STEM_MARKERS for char in stem)


def _sanskrit_section_source_prefix(query: str) -> str | None:
    value = query.strip()
    return value if value in _SANSKRIT_SECTION_SOURCE_PREFIXES else None


def _cdsl_prefix_predicate(prefix: str) -> tuple[str, list[object]]:
    return _cdsl_exact_prefix_predicate(prefix)


def _cdsl_exact_prefix_predicate(prefix: str) -> tuple[str, list[object]]:
    values = _cdsl_prefix_values(prefix)
    parts: list[str] = []
    params: list[object] = []
    if prefix in _SANSKRIT_SECTION_SOURCE_PREFIXES:
        for value in values:
            parts.append("substr(h.key, 1, ?) = ?")
            params.extend([len(value), value])
        return " OR ".join(parts), params

    for value in values:
        parts.append("h.key LIKE ?")
        params.append(f"{value}%")
    return " OR ".join(parts), params


def _cdsl_prefix_values(prefix: str) -> list[str]:
    if prefix in _SANSKRIT_SECTION_SOURCE_PREFIXES:
        return [prefix]

    values: list[str] = []

    def add(value: str) -> None:
        clean = value.strip()
        if clean and clean not in values:
            values.append(clean)

    add(prefix)
    with suppress(Exception):
        add(_to_slp1(prefix))
    return values


def _sanskrit_plain_slp1_keys(query: str, *, max_variants: int = 64) -> set[str]:
    plain = _plain_index_key(query)
    if not plain or not plain.isascii() or not plain.isalpha():
        return set()

    slots = _sanskrit_plain_slp1_slots(plain)
    if not slots:
        return set()

    variants = [""]
    for slot in slots:
        next_variants: list[str] = []
        for prefix in variants:
            for value in slot:
                next_variants.append(prefix + value)
                if len(next_variants) >= max_variants:
                    break
            if len(next_variants) >= max_variants:
                break
        variants = next_variants
        if len(variants) >= max_variants:
            break
    return {variant.lower() for variant in variants if variant}


def _sanskrit_plain_slp1_slots(plain: str) -> list[tuple[str, ...]]:  # noqa: C901, PLR0912
    if plain == "rr":
        return [("F",)]
    if plain == "ll":
        return [("X",)]

    slots: list[tuple[str, ...]] = []
    index = 0
    while index < len(plain):
        pair = plain[index : index + 2]
        if pair == "aa":
            slots.append(("A",))
            index += 2
            continue
        if pair == "ii":
            slots.append(("I",))
            index += 2
            continue
        if pair == "uu":
            slots.append(("U",))
            index += 2
            continue
        if pair == "ai":
            slots.append(("E",))
            index += 2
            continue
        if pair == "au":
            slots.append(("O",))
            index += 2
            continue
        if pair == "sh":
            slots.append(("S", "z"))
            index += 2
            continue

        char = plain[index]
        if char == "n":
            slots.append(("n", "R", "N"))
        elif char == "t":
            slots.append(("t", "w"))
        elif char == "d":
            slots.append(("d", "q"))
        elif char == "m":
            slots.append(("m", "M"))
        else:
            slots.append((char,))
        index += 1
    return slots


def _placeholders(values: Sequence[object]) -> str:
    return ", ".join("?" for _ in values) or "NULL"


def _as_int(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float | str):
        return int(value)
    return 0


def _as_float(value: object) -> float:
    if isinstance(value, int | float | str):
        return float(value)
    return 0.0


def _plain_index_key(value: str) -> str:
    text = (value or "").strip().lower().replace(".", "")
    replacements = {
        "ā": "aa",
        "ī": "ii",
        "ū": "uu",
        "ṛ": "r",
        "ṝ": "rr",
        "ḷ": "l",
        "ḹ": "ll",
        "ṃ": "m",
        "ṁ": "m",
        "ḥ": "h",
        "ṅ": "n",
        "ñ": "n",
        "ṭ": "t",
        "ḍ": "d",
        "ṇ": "n",
        "ś": "sh",
        "ṣ": "sh",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    normalized = normalize_dico_headword(text)
    return "".join(char for char in normalized if char.isalnum())


def _greek_ascii_key(value: str) -> str:
    if not any("\u0370" <= char <= "\u03ff" or "\u1f00" <= char <= "\u1fff" for char in value):
        return ""
    try:
        from betacode import conv as betacode_conv  # type: ignore[import-untyped]  # noqa: PLC0415

        beta = betacode_conv.uni_to_beta(value)
    except Exception:  # noqa: BLE001
        beta = value
    ascii_text = unicodedata.normalize("NFKD", beta).encode("ascii", "ignore").decode("ascii")
    ascii_text = ascii_text.lower().replace("w", "o")
    return re.sub(r"[^a-z]+", "", ascii_text)


def _greek_latinized_query_keys(value: str) -> set[str]:
    normalized = re.sub(r"[^a-z]+", "", value.strip().lower())
    if not normalized or not normalized.isascii():
        return set()
    keys = {normalized}
    base_forms = {normalized, normalized.replace("y", "u")}
    for base in base_forms:
        keys.add(base)
        keys.add(base.replace("x", "c"))
        transliterated = base
        for source, target in (
            ("rh", "r"),
            ("th", "q"),
            ("ph", "f"),
            ("ch", "x"),
        ):
            transliterated = transliterated.replace(source, target)
        keys.add(transliterated)
    return {key for key in keys if key}


def _diogenes_query_key(value: str) -> str:
    normalized = value.strip().lower()
    if not normalized:
        return ""
    keys = _match_keys(normalized)
    ordered_keys = list(keys)
    ordered_keys.sort(key=lambda key: len(key))
    return ordered_keys[0] if ordered_keys else normalized


def _greek_section_source_prefix(value: str) -> tuple[str, str] | None:
    return {
        "q": ("q", "θ"),
        "c": ("c", "ξ"),
        "f": ("f", "φ"),
        "x": ("x", "χ"),
        "y": ("y", "ψ"),
        "ō": ("o", "ω"),
        "ô": ("o", "ω"),
    }.get(value.strip().lower())


def _wheel_sort_key(item: Mapping[str, object], seed: str) -> str:
    material = "\x1f".join(
        [seed, str(item.get("language") or ""), str(item.get("source_ref") or "")]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _sanskrit_devanagari(text: str, scheme_name: str) -> str:
    if not text:
        return ""
    with suppress(Exception):
        sanscript = importlib.import_module("indic_transliteration.sanscript")
        scheme = getattr(sanscript, scheme_name)
        rendered = sanscript.transliterate(text, scheme, sanscript.DEVANAGARI)
        return rendered if rendered and rendered != text else ""
    return ""
