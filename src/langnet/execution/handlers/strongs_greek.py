from __future__ import annotations

import hashlib
import time
from collections.abc import Mapping
from pathlib import Path
from typing import cast

import orjson
from query_spec import ToolCallSpec

from langnet.clients.base import RawResponseEffect
from langnet.databuild.strongs_greek import (
    lookup_strongs_greek_entries_by_headword,
    normalize_strongs_greek_key,
)
from langnet.execution import predicates
from langnet.execution.effects import (
    ClaimEffect,
    DerivationEffect,
    ExtractionEffect,
    ProvenanceLink,
    stable_effect_id,
)
from langnet.execution.handlers.local_raw import local_raw_response_id
from langnet.execution.source_text import (
    display_text,
    learner_segments_from_text,
    source_segments_from_text,
    trim_empty,
)


def _split_candidate_param(value: str | None) -> list[str]:
    if not value:
        return []
    return [candidate.strip() for candidate in value.split(";") if candidate.strip()]


def _dedupe_candidates(candidates: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate and candidate not in seen:
            seen.add(candidate)
            ordered.append(candidate)
    return ordered


class StrongsGreekFetchClient:
    """DuckDB-backed fetcher for local Strong's Greek entries."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.tool = "fetch.strongs_greek"
        self.db_path = db_path

    def execute(
        self, call_id: str, endpoint: str, params: Mapping[str, str] | None = None
    ) -> RawResponseEffect:
        params = params or {}
        candidates = _dedupe_candidates(
            [
                params.get("headword") or "",
                params.get("lemma") or "",
                params.get("q") or "",
                *_split_candidate_param(params.get("lemma_candidates")),
            ]
        )
        start = time.perf_counter()
        entries = lookup_strongs_greek_entries_by_headword(candidates, self.db_path)
        duration_ms = int((time.perf_counter() - start) * 1000)
        matched = entries[0].get("matched_alias_display") if entries else None
        body = orjson.dumps(
            {"headwords": candidates, "matched_headword": matched, "entries": entries}
        )
        return RawResponseEffect(
            response_id=local_raw_response_id(self.tool, endpoint, body),
            tool=self.tool,
            call_id=call_id,
            endpoint=endpoint,
            status_code=200,
            content_type="application/json",
            headers={},
            body=body,
            fetch_duration_ms=duration_ms,
        )


def strongs_greek_entry_triples(entry: Mapping[str, object]) -> list[dict[str, object]]:
    """Project a resolved Strong's Greek entry into evidence-bearing triples."""
    lemma = str(entry.get("lemma_unicode") or "")
    lemma_norm = normalize_strongs_greek_key(lemma)
    strongs_number = str(entry.get("strongs_number") or "")
    entry_id = str(entry.get("entry_id") or f"strongs-greek:{strongs_number}")
    gloss = str(entry.get("display_gloss") or entry.get("definition") or "")
    display_gloss = display_text(gloss)
    lex_anchor = f"lex:{lemma_norm}" if lemma_norm else entry_id
    source_ref = f"strongs_greek:{strongs_number}" if strongs_number else entry_id
    digest_material = f"{source_ref}:{gloss}"
    digest = hashlib.sha256(digest_material.encode("utf-8")).hexdigest()[:8]
    sense_anchor = f"sense:{lex_anchor}#{digest}"
    evidence = trim_empty(
        {
            "source_tool": "strongs_greek",
            "source_ref": source_ref,
            "raw_blob_ref": "strongs_greek_xml",
            "entry_hash": entry.get("entry_hash"),
        }
    )
    source_entry = trim_empty(
        {
            "dict": "strongs_greek",
            "source_ref": source_ref,
            "entry_id": entry_id,
            "strongs_number": strongs_number,
            "lemma_unicode": lemma,
            "lemma_beta": entry.get("lemma_beta"),
            "lemma_translit": entry.get("lemma_translit"),
            "pronunciation": entry.get("pronunciation"),
            "matched_alias_display": entry.get("matched_alias_display"),
            "matched_alias_kind": entry.get("matched_alias_kind"),
            "derivation": entry.get("derivation"),
            "definition": entry.get("definition"),
            "kjv_definition": entry.get("kjv_definition"),
            "source_text": gloss,
        }
    )
    source_segments = source_segments_from_text(
        gloss,
        segment_type="definition_segment",
        labels=["definition"],
    )
    learner_segments = learner_segments_from_text(gloss)
    return [
        {
            "subject": lex_anchor,
            "predicate": predicates.HAS_SENSE,
            "object": sense_anchor,
            "metadata": {"evidence": evidence},
        },
        {
            "subject": sense_anchor,
            "predicate": predicates.GLOSS,
            "object": display_gloss,
            "metadata": trim_empty(
                {
                    "evidence": evidence,
                    "source_lang": "en",
                    "source_ref": source_ref,
                    "display_gloss": display_gloss,
                    "learner_gloss": display_gloss,
                    "learner_segments": learner_segments,
                    "source_entry": source_entry,
                    "source_segments": source_segments,
                }
            ),
        },
    ]


def extract_strongs_greek_json(call: ToolCallSpec, raw: RawResponseEffect) -> ExtractionEffect:
    """Extract local Strong's Greek lookup JSON."""
    payload: dict[str, object] = {"entries": []}
    canonical = None
    try:
        loaded = orjson.loads(raw.body)
        if isinstance(loaded, dict):
            payload = loaded
            canonical = _canonical_from_entries(loaded.get("entries"))
            if canonical is None:
                headwords = loaded.get("headwords")
                if isinstance(headwords, list):
                    canonical = next(
                        (
                            normalize_strongs_greek_key(headword)
                            for headword in headwords
                            if isinstance(headword, str) and headword
                        ),
                        None,
                    )
    except Exception:
        payload = {"entries": []}
    return ExtractionEffect(
        extraction_id=stable_effect_id("strongs-greek-ext", call.call_id, raw.response_id),
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        response_id=raw.response_id,
        kind="strongs_greek.entries",
        canonical=canonical,
        payload=payload,
    )


def derive_strongs_greek_entries(
    call: ToolCallSpec, extraction: ExtractionEffect
) -> DerivationEffect:
    """Derive normalized Strong's Greek entries from extraction payload."""
    prov = [
        ProvenanceLink(
            stage="extract",
            tool=extraction.tool,
            reference_id=extraction.extraction_id,
            metadata={"response_id": extraction.response_id},
        )
    ]
    payload = (
        cast(Mapping[str, object], extraction.payload)
        if isinstance(extraction.payload, Mapping)
        else {"entries": []}
    )
    return DerivationEffect(
        derivation_id=stable_effect_id("strongs-greek-der", call.call_id, extraction.extraction_id),
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        extraction_id=extraction.extraction_id,
        kind="strongs_greek.entries",
        canonical=extraction.canonical,
        payload=payload,
        provenance_chain=prov,
    )


def claim_strongs_greek_entries(call: ToolCallSpec, derivation: DerivationEffect) -> ClaimEffect:
    """Produce source-backed Strong's Greek dictionary claims."""
    prov = derivation.provenance_chain[:] if derivation.provenance_chain else []
    prov.append(
        ProvenanceLink(
            stage="derive",
            tool=derivation.tool,
            reference_id=derivation.derivation_id,
            metadata={"extraction_id": derivation.extraction_id},
        )
    )
    claim_id = stable_effect_id("strongs-greek-clm", call.call_id, derivation.derivation_id)
    payload = (
        cast(Mapping[str, object], derivation.payload)
        if isinstance(derivation.payload, Mapping)
        else {"entries": []}
    )
    entries = payload.get("entries")
    triples: list[dict[str, object]] = []
    if isinstance(entries, list):
        for entry in entries:
            if isinstance(entry, Mapping):
                triples.extend(strongs_greek_entry_triples(cast(Mapping[str, object], entry)))
    canonical = derivation.canonical or _canonical_from_entries(entries)
    value = dict(payload)
    value["triples"] = triples
    return ClaimEffect(
        claim_id=claim_id,
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        derivation_id=derivation.derivation_id,
        subject=f"lex:{canonical}" if canonical else call.call_id,
        predicate="has_dictionary_entries",
        value=value,
        provenance_chain=prov,
    )


def _canonical_from_entries(entries: object) -> str | None:
    if not isinstance(entries, list):
        return None
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        typed_entry = cast(Mapping[str, object], entry)
        lemma = typed_entry.get("lemma_unicode")
        if isinstance(lemma, str) and lemma.strip():
            return normalize_strongs_greek_key(lemma)
    return None
