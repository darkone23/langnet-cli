from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, cast

import orjson
from query_spec import ToolCallSpec

from langnet.clients.base import RawResponseEffect
from langnet.execution.effects import (
    ClaimEffect,
    DerivationEffect,
    ExtractionEffect,
    ProvenanceLink,
    stable_effect_id,
)
from langnet.execution.handlers.cltk import (  # Reuse Greek normalization helpers
    _form_anchor,
    _lex_anchor,
    _make_triple,
    _normalize_token,
)
from langnet.execution.versioning import versioned


@versioned("v1")
def extract_spacy(call: ToolCallSpec, raw: RawResponseEffect) -> ExtractionEffect:
    payload = {}
    HTTP_OK = 200
    canonical = None
    raw_json = raw.body.decode("utf-8", errors="ignore")
    if raw.status_code == HTTP_OK:
        try:
            payload = orjson.loads(raw.body)
            if isinstance(payload, Mapping):
                tokens = payload.get("tokens") or []
                if tokens and isinstance(tokens, Sequence) and isinstance(tokens[0], Mapping):
                    first = tokens[0]
                    canonical = first.get("lemma") or first.get("text")
        except Exception:
            payload = {}
    if isinstance(payload, Mapping):
        payload = {**payload, "raw_json": raw_json}
    return ExtractionEffect(
        extraction_id=stable_effect_id("spacy-ext", call.call_id, raw.response_id),
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        response_id=raw.response_id,
        kind="spacy.morph",
        canonical=canonical,
        payload=payload if isinstance(payload, Mapping) else {},
    )


@versioned("v1")
def derive_spacy(call: ToolCallSpec, extraction: ExtractionEffect) -> DerivationEffect:
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
        payload = dict(ext_payload)

        # Preserve raw_json if present
        if "raw_json" not in payload:
            raw_json = ext_payload.get("raw_json")
            if raw_json:
                payload["raw_json"] = raw_json

    return DerivationEffect(
        derivation_id=stable_effect_id("spacy-der", call.call_id, extraction.extraction_id),
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        extraction_id=extraction.extraction_id,
        kind="spacy.morph",
        canonical=canonical,
        payload=payload,
        provenance_chain=prov,
    )


def _pick_first(value: object) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Sequence) and value and isinstance(value[0], str):
        return value[0]
    return None


_FEATURE_PRED_MAP = {
    "Case": "has_case",
    "Number": "has_number",
    "Gender": "has_gender",
    "Tense": "has_tense",
    "Mood": "has_mood",
    "Person": "has_person",
    "Voice": "has_voice",
    "Degree": "has_degree",
}

_CASE_MAP = {
    "Nom": "nominative",
    "Acc": "accusative",
    "Gen": "genitive",
    "Dat": "dative",
    "Voc": "vocative",
    "Loc": "locative",
    "Abl": "ablative",
}
_NUMBER_MAP = {"Sing": "singular", "Plur": "plural", "Dual": "dual"}
_GENDER_MAP = {"Masc": "masculine", "Fem": "feminine", "Neut": "neuter", "Com": "common"}
_TENSE_MAP = {
    "Pres": "present",
    "Past": "past",
    "Fut": "future",
    "Imp": "imperfect",
    "Aor": "aorist",
    "Perf": "perfect",
    "Pqp": "pluperfect",
}
_MOOD_MAP = {
    "Ind": "indicative",
    "Sub": "subjunctive",
    "Imp": "imperative",
    "Inf": "infinitive",
    "Part": "participle",
    "Cnd": "conditional",
    "Opt": "optative",
}
_VOICE_MAP = {"Act": "active", "Mid": "middle", "Pass": "passive", "Mediopass": "mediopassive"}
_DEGREE_MAP = {"Pos": "positive", "Cmp": "comparative", "Sup": "superlative"}


def _map_feature(key: str, val: str) -> str:
    feature_maps = {
        "Case": _CASE_MAP,
        "Number": _NUMBER_MAP,
        "Gender": _GENDER_MAP,
        "Tense": _TENSE_MAP,
        "Mood": _MOOD_MAP,
        "Voice": _VOICE_MAP,
        "Degree": _DEGREE_MAP,
    }
    mapping = feature_maps.get(key)
    return mapping.get(val, val.lower()) if mapping else val.lower()


def _make_base_evidence(
    call: ToolCallSpec, derivation: DerivationEffect, claim_id: str
) -> Mapping[str, object]:
    return {
        "source_tool": "spacy",
        "call_id": call.call_id,
        "response_id": derivation.provenance_chain[0].metadata.get("response_id")
        if derivation.provenance_chain
        else None,
        "extraction_id": derivation.extraction_id,
        "derivation_id": derivation.derivation_id,
        "claim_id": claim_id,
        "raw_blob_ref": "raw_json",
    }


def _process_token_triples(
    tok: Mapping[str, object], base_evidence: Mapping[str, object]
) -> list[dict[str, object]]:
    """Process a single token and generate triples."""
    triples: list[dict[str, object]] = []

    # Extract and type text and lemma
    text_raw = tok.get("text")
    text: str | None = text_raw if isinstance(text_raw, str) else None

    lemma_raw = tok.get("lemma")
    lemma: str | None = lemma_raw if isinstance(lemma_raw, str) else None

    normalized_word = _normalize_token(text)
    normalized_lemma = _normalize_token(lemma)
    lex_anchor = _lex_anchor(normalized_lemma) if normalized_lemma else None
    form_anchor = _form_anchor(normalized_word) if normalized_word else None

    if not lex_anchor:
        return triples

    if form_anchor:
        if normalized_word and normalized_word != normalized_lemma:
            triples.append(_make_triple(form_anchor, "inflection_of", lex_anchor, base_evidence))
        if text:
            triples.append(_make_triple(form_anchor, "has_form", text, base_evidence))

    pos_val = tok.get("pos")
    if isinstance(pos_val, str):
        triples.append(_make_triple(lex_anchor, "has_pos", pos_val.lower(), base_evidence))

    morph_val = tok.get("morph")
    morph = cast(dict[str, object], morph_val) if isinstance(morph_val, Mapping) else {}
    for feature_key, pred in _FEATURE_PRED_MAP.items():
        val = _pick_first(morph.get(feature_key)) if morph else None
        if val:
            mapped = _map_feature(feature_key, str(val))
            triples.append(_make_triple(lex_anchor, pred, mapped, base_evidence))

    return triples


def _build_triples(
    payload: Mapping[str, object] | None, base_evidence: Mapping[str, object]
) -> list[dict[str, object]]:
    """Build RDF-style triples from spaCy token data."""
    if not isinstance(payload, Mapping):
        return []
    tokens = payload.get("tokens")
    if not isinstance(tokens, Sequence):
        return []

    triples: list[dict[str, object]] = []
    for tok in tokens:
        if isinstance(tok, Mapping):
            tok_typed = cast(Mapping[str, object], tok)
            triples.extend(_process_token_triples(tok_typed, base_evidence))
    return triples


@versioned("v1")
def claim_spacy(call: ToolCallSpec, derivation: DerivationEffect) -> ClaimEffect:
    prov = derivation.provenance_chain[:] if derivation.provenance_chain else []
    prov.append(
        ProvenanceLink(
            stage="derive",
            tool=derivation.tool,
            reference_id=derivation.derivation_id,
            metadata={"extraction_id": derivation.extraction_id},
        )
    )
    claim_id = stable_effect_id("spacy-clm", call.call_id, derivation.derivation_id)
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
