from __future__ import annotations

import hashlib
import time
from collections.abc import Mapping
from pathlib import Path
from typing import cast

import orjson
from query_spec import ToolCallSpec

from langnet.clients.base import RawResponseEffect
from langnet.databuild.lewis_1890 import (
    lookup_lewis_1890_entries_by_headword,
    normalize_lewis_1890_headword,
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


class Lewis1890FetchClient:
    """DuckDB-backed fetcher for local Lewis 1890 entries."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.tool = "fetch.lewis_1890"
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
        entries = lookup_lewis_1890_entries_by_headword(candidates, self.db_path)
        duration_ms = int((time.perf_counter() - start) * 1000)
        matched = entries[0].get("headword_norm") if entries else None
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


def lewis_1890_entry_triples(entry: Mapping[str, object]) -> list[dict[str, object]]:
    """Project a resolved Lewis 1890 entry into evidence-bearing triples."""
    headword = str(
        entry.get("headword_norm")
        or normalize_lewis_1890_headword(str(entry.get("headword_raw") or ""))
    )
    entry_id = str(entry.get("entry_id") or f"lewis-1890:{headword}")
    source_key = str(entry.get("source_key") or headword)
    gloss = entry.get("plain_text")
    gloss = gloss if isinstance(gloss, str) else ""
    display_gloss = display_text(gloss)
    lex_anchor = f"lex:{headword}"
    source_ref = f"lewis_1890:{source_key}"
    digest_material = f"{source_ref}:{gloss}"
    digest = hashlib.sha256(digest_material.encode("utf-8")).hexdigest()[:8]
    sense_anchor = f"sense:{lex_anchor}#{digest}"
    evidence = trim_empty(
        {
            "source_tool": "lewis_1890",
            "source_ref": source_ref,
            "raw_blob_ref": "cltk_lewis_yaml",
            "entry_hash": entry.get("entry_hash"),
        }
    )
    source_entry = trim_empty(
        {
            "dict": "lewis_1890",
            "source_ref": source_ref,
            "entry_id": entry_id,
            "headword_raw": entry.get("headword_raw"),
            "headword_norm": headword,
            "source_key": source_key,
            "source_text": gloss,
        }
    )
    source_segments = source_segments_from_text(
        gloss,
        segment_type="definition_segment",
        labels=["definition"],
    )
    learner_gloss = display_gloss
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
                    "learner_gloss": learner_gloss,
                    "learner_segments": learner_segments,
                    "source_entry": source_entry,
                    "source_segments": source_segments,
                }
            ),
        },
    ]


def extract_lewis_1890_json(call: ToolCallSpec, raw: RawResponseEffect) -> ExtractionEffect:
    """Extract local Lewis 1890 lookup JSON."""
    payload: dict[str, object] = {"entries": []}
    canonical = None
    try:
        loaded = orjson.loads(raw.body)
        if isinstance(loaded, dict):
            payload = loaded
            matched = loaded.get("matched_headword")
            if isinstance(matched, str) and matched:
                canonical = normalize_lewis_1890_headword(matched)
            if canonical is None:
                canonical = _canonical_from_entries(loaded.get("entries"))
            if canonical is None:
                headwords = loaded.get("headwords")
                if isinstance(headwords, list):
                    canonical = next(
                        (
                            normalize_lewis_1890_headword(headword)
                            for headword in headwords
                            if isinstance(headword, str) and headword
                        ),
                        None,
                    )
    except Exception:
        payload = {"entries": []}
    return ExtractionEffect(
        extraction_id=stable_effect_id("lewis-1890-ext", call.call_id, raw.response_id),
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        response_id=raw.response_id,
        kind="lewis_1890.entries",
        canonical=canonical,
        payload=payload,
    )


def derive_lewis_1890_entries(call: ToolCallSpec, extraction: ExtractionEffect) -> DerivationEffect:
    """Derive normalized Lewis 1890 entries from extraction payload."""
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
        derivation_id=stable_effect_id("lewis-1890-der", call.call_id, extraction.extraction_id),
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        extraction_id=extraction.extraction_id,
        kind="lewis_1890.entries",
        canonical=extraction.canonical,
        payload=payload,
        provenance_chain=prov,
    )


def claim_lewis_1890_entries(call: ToolCallSpec, derivation: DerivationEffect) -> ClaimEffect:
    """Produce source-backed Lewis 1890 dictionary claims."""
    prov = derivation.provenance_chain[:] if derivation.provenance_chain else []
    prov.append(
        ProvenanceLink(
            stage="derive",
            tool=derivation.tool,
            reference_id=derivation.derivation_id,
            metadata={"extraction_id": derivation.extraction_id},
        )
    )
    claim_id = stable_effect_id("lewis-1890-clm", call.call_id, derivation.derivation_id)
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
                triples.extend(lewis_1890_entry_triples(cast(Mapping[str, object], entry)))
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
        headword_norm = typed_entry.get("headword_norm")
        if isinstance(headword_norm, str) and headword_norm.strip():
            return normalize_lewis_1890_headword(headword_norm)
        headword_raw = typed_entry.get("headword_raw")
        if isinstance(headword_raw, str) and headword_raw.strip():
            return normalize_lewis_1890_headword(headword_raw)
    return None
