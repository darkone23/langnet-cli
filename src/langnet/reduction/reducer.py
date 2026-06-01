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


def merge_translated_source_buckets(buckets: Sequence[SenseBucket]) -> list[SenseBucket]:
    """Attach translated source witnesses to the translated bucket and hide duplicates.

    Translation projection deliberately keeps the original source witness so the
    UI can still expose source text beside Reader English. Without this merge,
    exact-gloss reduction emits a second French-only bucket for the same sense.
    """
    translated_by_source_sense: dict[str, SenseBucket] = {}
    for bucket in buckets:
        for witness in bucket.witnesses:
            if not _is_translation_witness(witness):
                continue
            derived_from_sense = _string_evidence(witness, "derived_from_sense")
            if derived_from_sense:
                translated_by_source_sense[derived_from_sense] = bucket

    if not translated_by_source_sense:
        return list(buckets)

    merged: list[SenseBucket] = []
    for bucket in buckets:
        if any(_is_translation_witness(witness) for witness in bucket.witnesses):
            merged.append(bucket)
            continue

        target_buckets = [
            translated_by_source_sense.get(witness.sense_anchor) for witness in bucket.witnesses
        ]
        if (
            target_buckets
            and all(target_buckets)
            and len({id(target) for target in target_buckets}) == 1
        ):
            target = target_buckets[0]
            assert target is not None
            target.witnesses.extend(bucket.witnesses)
            target.confidence_label = "multi-witness"
            target.notes = [
                *[note for note in target.notes if note != "provisional"],
                "source witness merged behind translation",
            ]
            continue

        merged.append(bucket)
    return merged


def _is_translation_witness(witness: WitnessSenseUnit) -> bool:
    return (
        witness.source_tool == "translation"
        or witness.evidence.get("source_tool") == "translation"
        or bool(witness.evidence.get("translation_id"))
    )


def _string_evidence(witness: WitnessSenseUnit, key: str) -> str:
    value = witness.evidence.get(key)
    return value if isinstance(value, str) else ""


def reduce_claims(
    *,
    query: str,
    language: str,
    claims: Sequence[Mapping[str, Any]],
) -> ReductionResult:
    witnesses = extract_witness_sense_units(claims)
    buckets = merge_translated_source_buckets(bucket_exact_glosses(witnesses, language))
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
