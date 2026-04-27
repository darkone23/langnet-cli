from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from typing import Any, cast

import orjson
from query_spec import ToolCallSpec

from langnet.clients.base import RawResponseEffect
from langnet.execution import predicates
from langnet.execution.effects import (
    ClaimEffect,
    DerivationEffect,
    ExtractionEffect,
    ProvenanceLink,
    stable_effect_id,
)
from langnet.execution.source_text import display_text, source_segments_from_text, trim_empty
from langnet.execution.versioning import versioned
from langnet.normalizer.utils import contains_greek, normalize_greekish_token, strip_accents
from langnet.parsing.integration import enrich_cltk_with_parsed_lewis


@versioned("v2")
def extract_cltk(call: ToolCallSpec, raw: RawResponseEffect) -> ExtractionEffect:
    """
    Extract CLTK lexicon data from JSON response.

    Version 2: Adds grammar-based parsing of lewis_lines (Lewis & Short entries).
    """
    payload = {}
    canonical = None
    raw_json = raw.body.decode("utf-8", errors="ignore")
    try:
        payload = orjson.loads(raw.body)
        if isinstance(payload, Mapping):
            canonical = payload.get("lemma") or payload.get("word")
            if payload.get("lemma"):
                payload = {**payload, "lemmas": [payload["lemma"]]}
    except Exception:
        payload = {}
    if isinstance(payload, Mapping):
        payload = {**payload, "raw_json": raw_json}

        # Enrich with parsed Lewis & Short entries (v2 improvement)
        payload = enrich_cltk_with_parsed_lewis(payload)

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


@versioned("v1")
def derive_cltk(call: ToolCallSpec, extraction: ExtractionEffect) -> DerivationEffect:
    prov = [
        ProvenanceLink(
            stage="extract",
            tool=extraction.tool,
            reference_id=extraction.extraction_id,
            metadata={"response_id": extraction.response_id},
        )
    ]
    payload: dict[str, object] = {}
    canonical = extraction.canonical

    if isinstance(extraction.payload, Mapping):
        ext_payload = cast(dict[str, Any], extraction.payload)
        lemma = ext_payload.get("lemma")
        lemmas = ext_payload.get("lemmas")
        raw_json = ext_payload.get("raw_json")

        payload = dict(ext_payload)

        # Add lemmas list if we have a lemma but no lemmas list
        if lemma and not lemmas:
            payload["lemmas"] = [lemma]

        # Preserve raw_json if present
        if raw_json and "raw_json" not in payload:
            payload["raw_json"] = raw_json

        # Set canonical from lemma if not already set
        if not canonical and isinstance(lemma, str):
            canonical = lemma

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


def _trim_evidence(evidence: Mapping[str, object]) -> dict[str, object]:
    return {k: v for k, v in evidence.items() if v is not None}


def _normalize_token(text: str | None) -> str | None:
    """
    Normalize CLTK lemmas/forms for anchor minting.

    - Greek: use shared Greek-aware normalizer to converge betacode/Unicode forms.
    - Otherwise: legacy ASCII collapse.
    """
    if not text:
        return None
    greekish = normalize_greekish_token(text)
    if greekish:
        return greekish
    normalized = strip_accents(text).lower()
    if contains_greek(normalized):
        normalized = normalized.replace("ς", "σ")
    normalized = "".join(ch for ch in normalized if ch.isalnum() or ch == "_")
    normalized = normalized.replace(" ", "_").strip("_")
    return normalized or None


def _lex_anchor(lemma: str) -> str:
    return f"lex:{lemma}"


def _form_anchor(form: str) -> str:
    return f"form:{form}"


def _sense_anchor(lex_anchor: str, gloss: str) -> str:
    digest = hashlib.sha256(gloss.strip().encode("utf-8")).hexdigest()[:8]
    return f"sense:{lex_anchor}#{digest}"


def _make_triple(
    subject: str,
    predicate: str,
    obj: object,
    base_evidence: Mapping[str, object],
    metadata: Mapping[str, object] | None = None,
) -> dict[str, object]:
    triple_metadata = {"evidence": _trim_evidence(dict(base_evidence))}
    if metadata:
        triple_metadata.update(trim_empty(metadata))
    return {
        "subject": subject,
        "predicate": predicate,
        "object": obj,
        "metadata": triple_metadata,
    }


def _extract_response_id(provenance: list[ProvenanceLink] | None) -> str | None:
    if not provenance:
        return None
    for link in provenance:
        if link.stage == "extract" and link.metadata:
            rid = link.metadata.get("response_id")
            if isinstance(rid, str):
                return rid
    return None


def _make_base_evidence(
    call: ToolCallSpec, derivation: DerivationEffect, claim_id: str
) -> Mapping[str, object]:
    return _trim_evidence(
        {
            "source_tool": "cltk",
            "call_id": call.call_id,
            "response_id": _extract_response_id(derivation.provenance_chain),
            "extraction_id": derivation.extraction_id,
            "derivation_id": derivation.derivation_id,
            "claim_id": claim_id,
            "raw_blob_ref": "raw_json",
        }
    )


def _extract_ipa_value(ipa_raw: object) -> str | None:
    """Extract IPA value from raw payload field (can be str or list)."""
    if isinstance(ipa_raw, str):
        return ipa_raw
    if isinstance(ipa_raw, Sequence) and ipa_raw:
        first = ipa_raw[0]
        if isinstance(first, str):
            return first
    return None


def _build_triples(
    payload: Mapping[str, object] | None, base_evidence: Mapping[str, object]
) -> list[dict[str, object]]:
    if not isinstance(payload, Mapping):
        return []
    triples: list[dict[str, object]] = []

    # Extract and type lemma
    payload_dict = cast(dict[str, object], payload)
    lemma_raw = payload_dict.get("lemma")
    lemma: str | None = lemma_raw if isinstance(lemma_raw, str) else None
    normalized_lemma = _normalize_token(lemma)
    lex_anchor = _lex_anchor(normalized_lemma) if normalized_lemma else None

    # Extract and type word
    word_raw = payload_dict.get("word")
    word: str | None = word_raw if isinstance(word_raw, str) else None
    normalized_word = _normalize_token(word)
    ipa_value = _extract_ipa_value(payload_dict.get("ipa"))
    lewis_lines_val = payload_dict.get("lewis_lines")
    if isinstance(lewis_lines_val, Sequence):
        lewis_lines = [line for line in lewis_lines_val if isinstance(line, str)]
    else:
        lewis_lines = []

    if lex_anchor and normalized_word and normalized_word != normalized_lemma:
        triples.append(
            _make_triple(_form_anchor(normalized_word), "inflection_of", lex_anchor, base_evidence)
        )
        triples.append(
            _make_triple(
                _form_anchor(normalized_word), "has_form", word or normalized_word, base_evidence
            )
        )
    if lex_anchor and ipa_value:
        triples.append(_make_triple(lex_anchor, "has_pronunciation", ipa_value, base_evidence))
    if lex_anchor:
        for line_index, line in enumerate(lewis_lines):
            gloss = line.strip()
            if not gloss:
                continue
            sense_anchor = _sense_anchor(lex_anchor, gloss)
            source_ref = f"cltk:lewis_lines:{normalized_lemma}:{line_index}"
            source_entry = trim_empty(
                {
                    "dict": "lewis_short_cltk",
                    "source_ref": source_ref,
                    "line_index": line_index,
                    "lemma": normalized_lemma,
                    "source_text": line,
                }
            )
            source_segments = source_segments_from_text(
                line,
                segment_type="dictionary_line",
                labels=["dictionary_entry"],
            )
            triples.append(
                _make_triple(lex_anchor, predicates.HAS_SENSE, sense_anchor, base_evidence)
            )
            triples.append(
                _make_triple(
                    sense_anchor,
                    predicates.GLOSS,
                    gloss,
                    base_evidence,
                    {
                        "source_ref": source_ref,
                        "display_gloss": display_text(gloss),
                        "source_entry": source_entry,
                        "source_segments": source_segments,
                    },
                )
            )
    return triples


@versioned("v1")
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
    claim_id = stable_effect_id("cltk-clm", call.call_id, derivation.derivation_id)
    subject = derivation.canonical or call.call_id
    value_raw = derivation.payload if isinstance(derivation.payload, Mapping) else {}
    value_typed = cast(Mapping[str, object], value_raw) if isinstance(value_raw, Mapping) else None
    base_evidence = _make_base_evidence(call, derivation, claim_id)
    triples = _build_triples(value_typed, base_evidence)
    value = {**value_typed, "triples": triples} if value_typed else {"triples": triples}
    return ClaimEffect(
        claim_id=claim_id,
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        derivation_id=derivation.derivation_id,
        subject=subject,
        predicate="has_lemmas",
        value=value,
        provenance_chain=prov,
    )
