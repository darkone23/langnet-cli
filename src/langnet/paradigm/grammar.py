from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

LANGNET_PARADIGM_RESOLUTION_SCHEMA_VERSION = "langnet.paradigm_resolution.v1"

LanguageCode = Literal["lat", "grc", "san"]
EntryType = Literal["root", "variant", "indeclinable", "compound_member", "unknown"]
ParadigmKind = Literal["declension", "conjugation", "none", "unknown"]
FetchableParadigmKind = Literal["declension", "conjugation"]
Confidence = Literal["high", "medium", "low"]
FunctionalRelation = Literal[
    "subject",
    "direct_object",
    "recipient_or_goal",
    "source_or_separation",
    "possession_or_association",
    "location",
    "instrument_or_means",
    "address",
    "predicate_relation",
    "unknown",
]
ParadigmSource = Literal["heritage:sktdeclin", "heritage:sktconjug", "diogenes:inflect"]

FeatureValue = str | int | float | bool | None


@dataclass(frozen=True)
class NativeAnalysis:
    language: LanguageCode
    features: dict[str, FeatureValue]
    source: str


@dataclass(frozen=True)
class FunctionalAnalysis:
    relation: FunctionalRelation
    native_feature: dict[str, FeatureValue]
    confidence: Confidence


@dataclass(frozen=True)
class ParadigmRequest:
    source: ParadigmSource
    language: LanguageCode
    lemma: str
    kind: FetchableParadigmKind
    options: dict[str, FeatureValue] = field(default_factory=dict)


@dataclass(frozen=True)
class GrammarEvidence:
    language: LanguageCode
    lemma: str
    part_of_speech: str
    features: dict[str, FeatureValue]
    analyses: list[dict[str, FeatureValue]] = field(default_factory=list)
    source: str = "unknown"
    confidence: Confidence = "low"


@dataclass(frozen=True)
class ParadigmResolutionCandidate:
    lemma: str
    entry_type: EntryType
    part_of_speech: str
    paradigm_kind: ParadigmKind
    observed_form: str | None = None
    slot_features: dict[str, FeatureValue] = field(default_factory=dict)
    foster_display: str = ""
    display_summary: str | None = None
    ranking_reasons: list[str] = field(default_factory=list)
    concept_ids: list[str] = field(default_factory=list)
    native_analyses: list[NativeAnalysis] = field(default_factory=list)
    functional_analyses: list[FunctionalAnalysis] = field(default_factory=list)
    paradigm_request: ParadigmRequest | None = None
    confidence: Confidence = "low"
    provenance: list[str] = field(default_factory=list)
    unresolved_reason: str | None = None


@dataclass(frozen=True)
class ParadigmResolutionPayload:
    searched_form: str
    normalized_form: str
    language: LanguageCode
    candidates: list[ParadigmResolutionCandidate] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    schema_version: str = LANGNET_PARADIGM_RESOLUTION_SCHEMA_VERSION
