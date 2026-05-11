from __future__ import annotations

from dataclasses import dataclass, field

from langnet.paradigm.grammar import (
    FeatureValue,
    FetchableParadigmKind,
    LanguageCode,
    ParadigmSource,
)

LANGNET_PARADIGM_SCHEMA_VERSION = "langnet.paradigm.v1"


@dataclass(frozen=True)
class ParadigmForm:
    text: str
    normalized: str
    source_key: str


@dataclass(frozen=True)
class ParadigmSlot:
    features: dict[str, FeatureValue]
    forms: list[ParadigmForm]
    source_label: str
    is_ambiguous: bool = False


@dataclass(frozen=True)
class ParadigmBlock:
    label: str
    dimensions: list[str]
    slots: list[ParadigmSlot]


@dataclass(frozen=True)
class ParadigmPayload:
    language: LanguageCode
    lemma: str
    kind: FetchableParadigmKind
    source: ParadigmSource
    source_request: dict[str, object]
    paradigms: list[ParadigmBlock] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    schema_version: str = LANGNET_PARADIGM_SCHEMA_VERSION
