from __future__ import annotations

import orjson
from typing import Mapping

from query_spec import ToolCallSpec

from langnet.clients.base import RawResponseEffect
from langnet.execution.effects import (
    ClaimEffect,
    DerivationEffect,
    ExtractionEffect,
    ProvenanceLink,
    stable_effect_id,
)


def extract_cltk(call: ToolCallSpec, raw: RawResponseEffect) -> ExtractionEffect:
    payload = {}
    canonical = None
    try:
        payload = orjson.loads(raw.body)
        if isinstance(payload, Mapping):
            canonical = payload.get("lemma") or payload.get("word")
            if payload.get("lemma"):
                payload = {**payload, "lemmas": [payload["lemma"]]}
    except Exception:
        payload = {}
    return ExtractionEffect(
        extraction_id=stable_effect_id("cltk-ext", call.call_id, raw.response_id),
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        response_id=raw.response_id,
        kind="cltk.lexicon",
        canonical=canonical,
        payload=payload if isinstance(payload, Mapping) else {},
    )


def derive_cltk(call: ToolCallSpec, extraction: ExtractionEffect) -> DerivationEffect:
    prov = [
        ProvenanceLink(
            stage="extract",
            tool=extraction.tool,
            reference_id=extraction.extraction_id,
            metadata={"response_id": extraction.response_id},
        )
    ]
    payload = extraction.payload if isinstance(extraction.payload, Mapping) else {}
    canonical = extraction.canonical or payload.get("lemma")
    if isinstance(payload, Mapping) and payload.get("lemma") and "lemmas" not in payload:
        payload = {**payload, "lemmas": [payload["lemma"]]}
    return DerivationEffect(
        derivation_id=stable_effect_id("cltk-der", call.call_id, extraction.extraction_id),
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        extraction_id=extraction.extraction_id,
        kind="cltk.ipa",
        canonical=canonical,
        payload=payload,
        provenance_chain=prov,
    )


def claim_cltk(call: ToolCallSpec, derivation: DerivationEffect) -> ClaimEffect:
    prov = derivation.provenance_chain[:] if derivation.provenance_chain else []
    prov.append(
        ProvenanceLink(
            stage="derive",
            tool=derivation.tool,
            reference_id=derivation.derivation_id,
            metadata={"extraction_id": derivation.extraction_id},
        )
    )
    subject = derivation.canonical or call.call_id
    value = derivation.payload if isinstance(derivation.payload, Mapping) else {}
    return ClaimEffect(
        claim_id=stable_effect_id("cltk-clm", call.call_id, derivation.derivation_id),
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        derivation_id=derivation.derivation_id,
        subject=subject,
        predicate="has_lemmas",
        value=value,
        provenance_chain=prov,
    )
