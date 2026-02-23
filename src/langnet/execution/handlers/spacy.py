from __future__ import annotations

from typing import Mapping, Sequence

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


def extract_spacy(call: ToolCallSpec, raw: RawResponseEffect) -> ExtractionEffect:
    payload = {}
    canonical = None
    raw_json = raw.body.decode("utf-8", errors="ignore")
    if raw.status_code == 200:
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


def derive_spacy(call: ToolCallSpec, extraction: ExtractionEffect) -> DerivationEffect:
    prov = [
        ProvenanceLink(
            stage="extract",
            tool=extraction.tool,
            reference_id=extraction.extraction_id,
            metadata={"response_id": extraction.response_id},
        )
    ]
    payload = extraction.payload if isinstance(extraction.payload, Mapping) else {}
    canonical = extraction.canonical
    if isinstance(payload, Mapping) and "raw_json" not in payload and extraction.payload.get("raw_json"):
        payload = {**payload, "raw_json": extraction.payload.get("raw_json")}
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
    if key == "Case":
        return _CASE_MAP.get(val, val.lower())
    if key == "Number":
        return _NUMBER_MAP.get(val, val.lower())
    if key == "Gender":
        return _GENDER_MAP.get(val, val.lower())
    if key == "Tense":
        return _TENSE_MAP.get(val, val.lower())
    if key == "Mood":
        return _MOOD_MAP.get(val, val.lower())
    if key == "Voice":
        return _VOICE_MAP.get(val, val.lower())
    if key == "Degree":
        return _DEGREE_MAP.get(val, val.lower())
    return val.lower()


def _make_base_evidence(
    call: ToolCallSpec, derivation: DerivationEffect, claim_id: str
) -> Mapping[str, object]:
    return {
        "source_tool": "spacy",
        "call_id": call.call_id,
        "response_id": derivation.provenance_chain[0].metadata.get("response_id") if derivation.provenance_chain else None,
        "extraction_id": derivation.extraction_id,
        "derivation_id": derivation.derivation_id,
        "claim_id": claim_id,
        "raw_blob_ref": "raw_json",
    }


def _build_triples(payload: Mapping[str, object] | None, base_evidence: Mapping[str, object]) -> list[dict[str, object]]:
    if not isinstance(payload, Mapping):
        return []
    tokens = payload.get("tokens")
    if not isinstance(tokens, Sequence):
        return []
    triples: list[dict[str, object]] = []
    for tok in tokens:
        if not isinstance(tok, Mapping):
            continue
        text = tok.get("text") if isinstance(tok.get("text"), str) else None
        lemma = tok.get("lemma") if isinstance(tok.get("lemma"), str) else None
        normalized_word = _normalize_token(text)
        normalized_lemma = _normalize_token(lemma)
        lex_anchor = _lex_anchor(normalized_lemma) if normalized_lemma else None
        form_anchor = _form_anchor(normalized_word) if normalized_word else None

        if lex_anchor:
            if form_anchor:
                if normalized_word and normalized_word != normalized_lemma:
                    triples.append(_make_triple(form_anchor, "inflection_of", lex_anchor, base_evidence))
                if text:
                    triples.append(_make_triple(form_anchor, "has_form", text, base_evidence))
            pos = tok.get("pos") if isinstance(tok.get("pos"), str) else None
            if pos:
                triples.append(_make_triple(lex_anchor, "has_pos", pos.lower(), base_evidence))
            morph = tok.get("morph") if isinstance(tok.get("morph"), Mapping) else {}
            for feature_key, pred in _FEATURE_PRED_MAP.items():
                val = _pick_first(morph.get(feature_key)) if isinstance(morph, Mapping) else None
                if val:
                    mapped = _map_feature(feature_key, str(val))
                    triples.append(_make_triple(lex_anchor, pred, mapped, base_evidence))
    return triples


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
    value = derivation.payload if isinstance(derivation.payload, Mapping) else {}
    base_evidence = _make_base_evidence(call, derivation, claim_id)
    triples = _build_triples(value, base_evidence) if isinstance(value, Mapping) else []
    if isinstance(value, Mapping):
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
