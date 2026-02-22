from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import orjson


def stable_effect_id(prefix: str, *materials: object) -> str:
    """
    Deterministic ID builder for non-raw effects.

    Use stable hashing so the same inputs (payload + source) yield the same
    effect identifiers across executions. Falls back to a random UUID when
    hashing fails to keep the executor resilient during early bring-up.
    """
    try:
        material = orjson.dumps(materials, option=orjson.OPT_SORT_KEYS)
        digest = hashlib.sha256(material).hexdigest()[:16]
        return f"{prefix}-{digest}"
    except Exception:
        return f"{prefix}-{uuid.uuid4()}"


@dataclass(slots=True)
class ProvenanceLink:
    stage: str
    tool: str
    reference_id: str | None
    metadata: Mapping[str, Any] | None = None


ProvenanceChain = list[ProvenanceLink]


@dataclass(slots=True)
class ExtractionEffect:
    extraction_id: str
    tool: str
    call_id: str
    source_call_id: str
    response_id: str
    kind: str
    canonical: str | None
    payload: Mapping[str, Any] | Sequence[Any] | None
    load_duration_ms: int = 0
    created_at: float = field(default_factory=time.time)


@dataclass(slots=True)
class DerivationEffect:
    derivation_id: str
    tool: str
    call_id: str
    source_call_id: str
    extraction_id: str
    kind: str
    canonical: str | None
    payload: Mapping[str, Any] | Sequence[Any] | None
    derive_duration_ms: int = 0
    provenance_chain: ProvenanceChain | None = None
    created_at: float = field(default_factory=time.time)


@dataclass(slots=True)
class ClaimEffect:
    claim_id: str
    tool: str
    call_id: str
    source_call_id: str
    derivation_id: str
    subject: str
    predicate: str
    value: Mapping[str, Any] | Sequence[Any] | None
    provenance_chain: ProvenanceChain
    load_duration_ms: int = 0
    created_at: float = field(default_factory=time.time)
