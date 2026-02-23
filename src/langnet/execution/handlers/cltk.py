from __future__ import annotations

import orjson
import hashlib
from typing import Mapping, Sequence

from query_spec import ToolCallSpec

from langnet.clients.base import RawResponseEffect
from langnet.execution.effects import (
    ClaimEffect,
    DerivationEffect,
    ExtractionEffect,
    ProvenanceLink,
    stable_effect_id,
)
from langnet.normalizer.utils import normalize_greekish_token, strip_accents, contains_greek


def extract_cltk(call: ToolCallSpec, raw: RawResponseEffect) -> ExtractionEffect:
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
    if isinstance(payload, Mapping) and "raw_json" not in payload and extraction.payload.get("raw_json"):
        payload = {**payload, "raw_json": extraction.payload.get("raw_json")}
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
    subject: str, predicate: str, obj: object, base_evidence: Mapping[str, object]
) -> dict[str, object]:
    return {
        "subject": subject,
        "predicate": predicate,
        "object": obj,
        "metadata": {"evidence": _trim_evidence(dict(base_evidence))},
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


def _build_triples(payload: Mapping[str, object] | None, base_evidence: Mapping[str, object]) -> list[dict[str, object]]:
    if not isinstance(payload, Mapping):
        return []
    triples: list[dict[str, object]] = []
    lemma = payload.get("lemma") if isinstance(payload.get("lemma"), str) else None
    normalized_lemma = _normalize_token(lemma)
    lex_anchor = _lex_anchor(normalized_lemma) if normalized_lemma else None
    word = payload.get("word") if isinstance(payload.get("word"), str) else None
    normalized_word = _normalize_token(word)
    ipa_list = payload.get("ipa")
    ipa_value: str | None = None
    if isinstance(ipa_list, str):
        ipa_value = ipa_list
    elif isinstance(ipa_list, Sequence) and ipa_list:
        first = ipa_list[0]
        if isinstance(first, str):
            ipa_value = first
    lewis_lines = [line for line in payload.get("lewis_lines", []) or [] if isinstance(line, str)]

    if lex_anchor and normalized_word and normalized_word != normalized_lemma:
        triples.append(_make_triple(_form_anchor(normalized_word), "inflection_of", lex_anchor, base_evidence))
        triples.append(_make_triple(_form_anchor(normalized_word), "has_form", word or normalized_word, base_evidence))
    if lex_anchor and ipa_value:
        triples.append(_make_triple(lex_anchor, "has_pronunciation", ipa_value, base_evidence))
    if lex_anchor:
        for line in lewis_lines:
            gloss = line.strip()
            if not gloss:
                continue
            sense_anchor = _sense_anchor(lex_anchor, gloss)
            triples.append(_make_triple(lex_anchor, "has_sense", sense_anchor, base_evidence))
            triples.append(_make_triple(sense_anchor, "gloss", gloss, base_evidence))
    return triples


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
    value = derivation.payload if isinstance(derivation.payload, Mapping) else {}
    base_evidence = _make_base_evidence(call, derivation, claim_id)
    if isinstance(value, Mapping):
        triples = _build_triples(value, base_evidence)
        value = {**value, "triples": triples}
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
