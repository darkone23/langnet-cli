from __future__ import annotations

import hashlib
import re
import time
from collections.abc import Mapping
from pathlib import Path
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
from langnet.execution.handlers.candidate_filters import close_fallback_candidates
from langnet.execution.handlers.local_raw import local_raw_response_id
from langnet.execution.source_text import (
    compact_source_gloss,
    display_text,
    learner_segments_from_text,
    source_segments_from_text,
    trim_empty,
)
from langnet.normalizer.utils import strip_accents
from langnet.storage.db import connect_duckdb_ro


def normalize_georges_1913_headword(raw: str) -> str:
    """Normalize a Latin headword for Georges 1913 lookup."""
    stripped = (raw or "").strip()
    if "," in stripped:
        stripped = stripped.split(",", 1)[0]
    stripped = stripped.strip("\"'`.,;:()[]{} ")
    stripped = re.sub(r"^\d+\.\s*", "", stripped)
    ligature_expanded = (
        stripped.replace("æ", "ae").replace("Æ", "ae").replace("œ", "oe").replace("Œ", "oe")
    )
    return strip_accents(ligature_expanded.lower())


def lookup_georges_1913_entries(headword: str, db_path: Path | None = None) -> list[dict]:
    """Resolve a Latin headword from the local Georges 1913 DuckDB index."""
    return lookup_georges_1913_entries_by_headword([headword], db_path)


def lookup_georges_1913_entries_by_headword(
    headwords: list[str], db_path: Path | None = None
) -> list[dict]:
    """Resolve local Georges entries from ordered headword candidates."""
    keys: list[str] = []
    seen: set[str] = set()
    for headword in headwords:
        key = normalize_georges_1913_headword(headword)
        if key and key not in seen:
            seen.add(key)
            keys.append(key)
    if not keys:
        return []
    if db_path is None:
        from langnet.databuild.paths import default_georges_1913_path  # noqa: PLC0415

        db_path = default_georges_1913_path()
    if not db_path.exists():
        return []

    placeholders = ",".join(["?"] * len(keys))
    with connect_duckdb_ro(db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT
                entry_id,
                occurrence,
                headword_roma,
                headword_norm,
                plain_text,
                source_page
            FROM entries_fr
            WHERE headword_norm IN ({placeholders})
            ORDER BY source_page, entry_id, occurrence
            """,
            keys,
        ).fetchall()
    return [
        {
            "entry_id": row[0],
            "occurrence": row[1],
            "headword_raw": row[2],
            "headword_norm": normalize_georges_1913_headword(row[3] or row[2] or row[0]),
            "plain_text": row[4],
            "source_page": row[5],
        }
        for row in rows
    ]


def georges_1913_entry_triples(entry: Mapping[str, object]) -> list[dict[str, object]]:
    """Project a resolved Georges entry into evidence-bearing triples."""
    headword = str(
        entry.get("headword_norm")
        or normalize_georges_1913_headword(str(entry.get("headword_raw") or ""))
    )
    entry_id = str(entry.get("entry_id") or headword)
    occurrence = entry.get("occurrence")
    source_page = str(entry.get("source_page") or "")
    gloss = entry.get("plain_text")
    gloss = gloss if isinstance(gloss, str) else ""
    display_gloss = display_text(gloss)
    lex_anchor = f"lex:{headword}"
    source_ref = f"georges_1913:{source_page}#{entry_id}:{occurrence or 0}"
    digest = hashlib.sha256(f"{source_ref}:{gloss}".encode("utf-8")).hexdigest()[:8]
    sense_anchor = f"sense:{lex_anchor}#{digest}"
    evidence = trim_empty(
        {
            "source_tool": "georges_1913",
            "source_ref": source_ref,
            "raw_blob_ref": "body_html",
            "occurrence": occurrence,
        }
    )
    source_entry = trim_empty(
        {
            "dict": "georges_1913",
            "source_ref": source_ref,
            "entry_id": entry_id,
            "occurrence": occurrence,
            "source_page": source_page,
            "headword_raw": entry.get("headword_raw"),
            "headword_norm": headword,
            "source_text": gloss,
        }
    )
    source_segments = source_segments_from_text(
        gloss,
        segment_type="definition_segment",
        labels=["definition"],
    )
    learner_gloss = compact_source_gloss(gloss)
    learner_segments = learner_segments_from_text(gloss, source_tool="georges_1913")
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
                    "source_lang": "de",
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


def _split_candidate_param(value: str | None) -> list[str]:
    if not value:
        return []
    return [candidate.strip() for candidate in value.split(";") if candidate.strip()]


class Georges1913FetchClient:
    """DuckDB-backed fetcher for local Georges 1913 entries."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.tool = "fetch.georges_1913"
        self.db_path = db_path

    def execute(
        self, call_id: str, endpoint: str, params: Mapping[str, str] | None = None
    ) -> RawResponseEffect:
        params = params or {}
        headword = params.get("headword") or ""
        lemma_candidates = close_fallback_candidates(
            headword,
            _split_candidate_param(params.get("lemma_candidates")),
            normalize=normalize_georges_1913_headword,
        )
        candidates = [
            headword,
            params.get("lemma") or "",
            params.get("q") or "",
            *lemma_candidates,
        ]
        start = time.perf_counter()
        entries = lookup_georges_1913_entries_by_headword(candidates, self.db_path)
        duration_ms = int((time.perf_counter() - start) * 1000)
        body = orjson.dumps({"headwords": candidates, "entries": entries})
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


def extract_georges_1913_json(call: ToolCallSpec, raw: RawResponseEffect) -> ExtractionEffect:
    """Extract local Georges lookup JSON."""
    payload: dict[str, object] = {"entries": []}
    canonical = None
    try:
        loaded = orjson.loads(raw.body)
        if isinstance(loaded, dict):
            payload = loaded
            headwords = loaded.get("headwords")
            if isinstance(headwords, list):
                canonical = next(
                    (
                        normalize_georges_1913_headword(headword)
                        for headword in headwords
                        if isinstance(headword, str) and headword
                    ),
                    None,
                )
    except Exception:
        payload = {"entries": []}
    return ExtractionEffect(
        extraction_id=stable_effect_id("georges-1913-ext", call.call_id, raw.response_id),
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        response_id=raw.response_id,
        kind="georges_1913.entries",
        canonical=canonical,
        payload=payload,
    )


def derive_georges_1913_entries(
    call: ToolCallSpec, extraction: ExtractionEffect
) -> DerivationEffect:
    """Derive normalized Georges entries from extraction payload."""
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
        derivation_id=stable_effect_id("georges-1913-der", call.call_id, extraction.extraction_id),
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        extraction_id=extraction.extraction_id,
        kind="georges_1913.entries",
        canonical=extraction.canonical,
        payload=payload,
        provenance_chain=prov,
    )


def claim_georges_1913_entries(call: ToolCallSpec, derivation: DerivationEffect) -> ClaimEffect:
    """Produce source-backed Georges dictionary claims."""
    prov = list(derivation.provenance_chain or [])
    prov.append(
        ProvenanceLink(
            stage="derive",
            tool=derivation.tool,
            reference_id=derivation.derivation_id,
            metadata={"extraction_id": derivation.extraction_id},
        )
    )
    payload = (
        cast(Mapping[str, object], derivation.payload)
        if isinstance(derivation.payload, Mapping)
        else {"entries": []}
    )
    raw_entries = payload.get("entries")
    entries = (
        [entry for entry in raw_entries if isinstance(entry, Mapping)]
        if isinstance(raw_entries, list)
        else []
    )
    triples: list[dict[str, object]] = []
    for entry in entries:
        triples.extend(georges_1913_entry_triples(cast(Mapping[str, object], entry)))
    subject = f"lex:{derivation.canonical}" if derivation.canonical else "lex:unknown"
    return ClaimEffect(
        claim_id=stable_effect_id("georges-1913-clm", call.call_id, derivation.derivation_id),
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        derivation_id=derivation.derivation_id,
        subject=subject,
        predicate=predicates.HAS_SENSE,
        value={"entries": entries, "triples": triples},
        provenance_chain=prov,
    )
