from __future__ import annotations

from langnet.execution.effects import (
    ClaimEffect,
    DerivationEffect,
    ExtractionEffect,
    ProvenanceLink,
    stable_effect_id,
)


def stub_extract(call, raw) -> ExtractionEffect:
    """Fallback extract handler that records the raw response id."""
    return ExtractionEffect(
        extraction_id=stable_effect_id("ext", call.call_id, raw.response_id),
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        response_id=raw.response_id,
        kind=call.tool,
        canonical=None,
        payload={
            "stub": True,
            "call_id": call.call_id,
            "tool": call.tool,
            "note": "extract handler not yet implemented",
        },
    )


def stub_derive(call, extraction: ExtractionEffect) -> DerivationEffect:
    """Fallback derivation handler that carries extraction payload forward."""
    prov = [
        ProvenanceLink(stage="extract", tool=extraction.tool, reference_id=extraction.extraction_id)
    ]
    return DerivationEffect(
        derivation_id=stable_effect_id("drv", call.call_id, extraction.extraction_id),
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        extraction_id=extraction.extraction_id,
        kind=call.tool,
        canonical=extraction.canonical,
        payload={"stub": True, "upstream_payload": extraction.payload},
        provenance_chain=prov,
    )


def stub_claim(call, derivation: DerivationEffect) -> ClaimEffect:
    """Fallback claim handler that emits a placeholder claim."""
    prov = derivation.provenance_chain[:] if derivation.provenance_chain else []
    prov.append(
        ProvenanceLink(stage="derive", tool=derivation.tool, reference_id=derivation.derivation_id)
    )
    return ClaimEffect(
        claim_id=stable_effect_id("clm", call.call_id, derivation.derivation_id),
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        derivation_id=derivation.derivation_id,
        subject=derivation.canonical or call.call_id,
        predicate="stub:claim",
        value={"stub": True, "call_id": call.call_id},
        provenance_chain=prov,
    )
