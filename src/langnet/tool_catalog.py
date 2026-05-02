from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

TOOL_CATALOG_SCHEMA_VERSION = "langnet.tools.v1"
LANGUAGE_CATALOG_SCHEMA_VERSION = "langnet.languages.v1"
LanguageCode = Literal["lat", "grc", "san"]


@dataclass(frozen=True, slots=True)
class ToolCatalogEntry:
    language: LanguageCode
    tool_filter: str
    label: str
    role: str
    source_tools: tuple[str, ...]
    plan_tools: tuple[str, ...]
    default_enabled: bool = True
    translation_capable: bool = False
    dictionaries: tuple[str, ...] = ()
    notes: str = ""


LANGUAGE_LABELS: dict[LanguageCode, str] = {
    "lat": "Latin",
    "grc": "Greek",
    "san": "Sanskrit",
}

LANGUAGE_ALIASES: dict[str, LanguageCode] = {
    "la": "lat",
    "lat": "lat",
    "el": "grc",
    "grc": "grc",
    "greek": "grc",
    "san": "san",
    "skt": "san",
    "sanskrit": "san",
}

_CATALOG: tuple[ToolCatalogEntry, ...] = (
    ToolCatalogEntry(
        language="lat",
        tool_filter="diogenes",
        label="Diogenes / Lewis and Short",
        role="dictionary and morphology",
        source_tools=("diogenes",),
        plan_tools=(
            "fetch.diogenes",
            "extract.diogenes.html",
            "derive.diogenes.morph",
            "claim.diogenes.morph",
        ),
        notes="Local Diogenes service; may require a running Diogenes endpoint.",
    ),
    ToolCatalogEntry(
        language="lat",
        tool_filter="whitakers",
        label="Whitaker's Words",
        role="morphology and compact lexical facts",
        source_tools=("whitaker", "whitakers"),
        plan_tools=(
            "fetch.whitakers",
            "extract.whitakers.lines",
            "derive.whitakers.facts",
            "claim.whitakers",
        ),
    ),
    ToolCatalogEntry(
        language="lat",
        tool_filter="cltk",
        label="CLTK Latin",
        role="supplemental lexicon and IPA",
        source_tools=("cltk",),
        plan_tools=(
            "fetch.cltk",
            "extract.cltk.lexicon",
            "derive.cltk.ipa",
            "claim.cltk.ipa",
        ),
        notes="Disabled by default for encounter unless --include-cltk is used.",
        default_enabled=False,
    ),
    ToolCatalogEntry(
        language="lat",
        tool_filter="gaffiot",
        label="Gaffiot",
        role="Latin-French dictionary entries",
        source_tools=("gaffiot",),
        plan_tools=(
            "fetch.gaffiot",
            "extract.gaffiot.json",
            "derive.gaffiot.entries",
            "claim.gaffiot.entries",
        ),
        translation_capable=True,
        notes="French source entries can be projected through the translation cache.",
    ),
    ToolCatalogEntry(
        language="grc",
        tool_filter="diogenes",
        label="Diogenes / LSJ",
        role="dictionary, morphology, and citation evidence",
        source_tools=("diogenes",),
        plan_tools=(
            "fetch.diogenes",
            "extract.diogenes.html",
            "derive.diogenes.morph",
            "derive.diogenes.citation",
            "claim.diogenes.morph",
            "claim.diogenes.citation",
        ),
        notes="Local Diogenes service; may require a running Diogenes endpoint.",
    ),
    ToolCatalogEntry(
        language="grc",
        tool_filter="cts_index",
        label="CTS index",
        role="citation hydration",
        source_tools=("cts_index",),
        plan_tools=(
            "fetch.cts_index",
            "extract.cts_index.json",
            "derive.cts_index.citation",
            "claim.cts_index",
        ),
    ),
    ToolCatalogEntry(
        language="grc",
        tool_filter="spacy",
        label="spaCy Greek",
        role="supplemental morphology",
        source_tools=("spacy",),
        plan_tools=(
            "fetch.spacy",
            "extract.spacy.json",
            "derive.spacy.morph",
            "claim.spacy.morph",
        ),
    ),
    ToolCatalogEntry(
        language="grc",
        tool_filter="cltk",
        label="CLTK Greek",
        role="supplemental lexicon and IPA",
        source_tools=("cltk",),
        plan_tools=(
            "fetch.cltk",
            "extract.cltk.lexicon",
            "derive.cltk.ipa",
            "claim.cltk.ipa",
        ),
        notes="Disabled by default for encounter unless --include-cltk is used.",
        default_enabled=False,
    ),
    ToolCatalogEntry(
        language="san",
        tool_filter="heritage",
        label="Sanskrit Heritage",
        role="morphology and segmentation",
        source_tools=("heritage",),
        plan_tools=(
            "fetch.heritage",
            "extract.heritage.html",
            "derive.heritage.morph",
            "claim.heritage.morph",
        ),
    ),
    ToolCatalogEntry(
        language="san",
        tool_filter="cdsl",
        label="CDSL",
        role="Sanskrit dictionary entries",
        source_tools=("cdsl",),
        plan_tools=(
            "fetch.cdsl",
            "extract.cdsl.xml",
            "derive.cdsl.sense",
            "claim.cdsl.sense",
        ),
        dictionaries=("mw", "ap90"),
        notes="Currently plans MW and AP90 dictionary rows.",
    ),
    ToolCatalogEntry(
        language="san",
        tool_filter="dico",
        label="DICO",
        role="Sanskrit-French dictionary entries",
        source_tools=("dico",),
        plan_tools=(
            "fetch.dico",
            "extract.dico.json",
            "derive.dico.entries",
            "claim.dico.entries",
        ),
        translation_capable=True,
        notes="French source entries can be projected through the translation cache.",
    ),
)


def canonical_language(value: str) -> LanguageCode | None:
    return LANGUAGE_ALIASES.get(value.strip().lower())


def catalog_entries(language: str | None = None) -> list[ToolCatalogEntry]:
    canonical = canonical_language(language) if language else None
    return [entry for entry in _CATALOG if canonical is None or entry.language == canonical]


def _language_codes(language: str | None = None) -> list[LanguageCode]:
    canonical = canonical_language(language) if language else None
    return [canonical] if canonical is not None else list(LANGUAGE_LABELS)


def _aliases_for_language(code: LanguageCode) -> list[str]:
    return sorted(alias for alias, canonical in LANGUAGE_ALIASES.items() if canonical == code)


def language_payload(language: str | None = None) -> dict[str, object]:
    codes = _language_codes(language)
    return {
        "schema_version": LANGUAGE_CATALOG_SCHEMA_VERSION,
        "languages": [
            {
                "code": code,
                "label": LANGUAGE_LABELS[code],
                "aliases": _aliases_for_language(code),
                "default_tool_filter": "all",
                "tools_command": ["tools", code, "--output", "json"],
                "encounter_command": ["encounter", code, "<text>", "all", "--output", "json"],
            }
            for code in codes
        ],
    }


def catalog_payload(
    language: str | None = None, *, command: str = "encounter"
) -> dict[str, object]:
    entries = catalog_entries(language)
    languages = _language_codes(language)
    return {
        "schema_version": TOOL_CATALOG_SCHEMA_VERSION,
        "command": command,
        "languages": [
            {"code": code, "label": LANGUAGE_LABELS[code], "tool_filter": "all"}
            for code in languages
        ],
        "tools": [
            {
                **_entry_payload(entry),
                "accepted_filter": entry.tool_filter,
            }
            for entry in entries
        ],
        "pseudo_filters": [
            {
                "tool_filter": "all",
                "label": "All default tools for the language",
                "languages": languages,
            }
        ],
    }


def _entry_payload(entry: ToolCatalogEntry) -> dict[str, object]:
    payload = asdict(entry)
    payload["source_tools"] = list(entry.source_tools)
    payload["plan_tools"] = list(entry.plan_tools)
    payload["dictionaries"] = list(entry.dictionaries)
    return payload
