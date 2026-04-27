from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from langnet.reduction.models import ReductionResult, SenseBucket, WitnessSenseUnit
from langnet.reduction.wsu import extract_witness_sense_units


def _bucket_id(language: str, normalized_gloss: str) -> str:
    digest = hashlib.sha256(f"{language}\x1f{normalized_gloss}".encode()).hexdigest()[:16]
    return f"bucket:{digest}"


def bucket_exact_glosses(witnesses: Sequence[WitnessSenseUnit], language: str) -> list[SenseBucket]:
    """Group WSUs by exact normalized gloss."""
    grouped: dict[str, list[WitnessSenseUnit]] = defaultdict(list)
    for witness in witnesses:
        grouped[witness.normalized_gloss].append(witness)

    buckets: list[SenseBucket] = []
    for normalized_gloss, bucket_witnesses in sorted(grouped.items()):
        display_gloss = bucket_witnesses[0].gloss
        confidence = "multi-witness" if len(bucket_witnesses) > 1 else "single-witness"
        notes = [] if len(bucket_witnesses) > 1 else ["provisional"]
        buckets.append(
            SenseBucket(
                bucket_id=_bucket_id(language, normalized_gloss),
                normalized_gloss=normalized_gloss,
                display_gloss=display_gloss,
                witnesses=list(bucket_witnesses),
                confidence_label=confidence,
                notes=notes,
            )
        )
    return buckets


def reduce_claims(
    *,
    query: str,
    language: str,
    claims: Sequence[Mapping[str, Any]],
) -> ReductionResult:
    witnesses = extract_witness_sense_units(claims)
    buckets = bucket_exact_glosses(witnesses, language)
    lexeme_anchors = sorted({witness.lexeme_anchor for witness in witnesses})
    warnings: list[str] = []
    if not witnesses:
        warnings.append("No has_sense/gloss witness units were extracted.")

    return ReductionResult(
        query=query,
        language=language,
        lexeme_anchors=lexeme_anchors,
        buckets=buckets,
        warnings=warnings,
    )
