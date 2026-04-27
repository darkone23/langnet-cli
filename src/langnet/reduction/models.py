from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

JSONMapping = dict[str, Any]


@dataclass(slots=True)
class WitnessSenseUnit:
    """One source-backed gloss witness extracted from claim triples."""

    wsu_id: str
    lexeme_anchor: str
    sense_anchor: str
    gloss: str
    normalized_gloss: str
    source_tool: str
    claim_id: str
    source_triple_subject: str
    evidence: JSONMapping = field(default_factory=dict)


@dataclass(slots=True)
class SenseBucket:
    """Deterministic group of related witness sense units."""

    bucket_id: str
    normalized_gloss: str
    display_gloss: str
    witnesses: list[WitnessSenseUnit] = field(default_factory=list)
    confidence_label: str = "unreviewed"
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ReductionResult:
    """Semantic reduction result for one lookup target."""

    query: str
    language: str
    lexeme_anchors: list[str] = field(default_factory=list)
    buckets: list[SenseBucket] = field(default_factory=list)
    unbucketed_witnesses: list[WitnessSenseUnit] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
