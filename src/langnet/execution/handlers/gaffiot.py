from __future__ import annotations

import hashlib
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

import duckdb
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
from langnet.execution.handlers.local_raw import local_raw_response_id
from langnet.execution.source_text import display_text, source_segments_from_text, trim_empty
from langnet.normalizer.utils import strip_accents


def normalize_gaffiot_headword(raw: str) -> str:
    """Normalize a Latin headword for Gaffiot lookup."""
    stripped = (raw or "").strip()
    if "," in stripped:
        stripped = stripped.split(",", 1)[0]
    stripped = stripped.lstrip("0123456789. ").strip()
    ligature_expanded = (
        stripped.replace("æ", "ae").replace("Æ", "ae").replace("œ", "oe").replace("Œ", "oe")
    )
    return strip_accents(ligature_expanded.lower())


def lookup_gaffiot_entries(headword: str, db_path: Path | None = None) -> list[dict]:
    """Resolve a Latin headword from the local Gaffiot DuckDB index."""
    return lookup_gaffiot_entries_by_headword([headword], db_path)


def lookup_gaffiot_entries_by_headword(
    headwords: list[str], db_path: Path | None = None
) -> list[dict]:
    """Resolve local Gaffiot entries from ordered headword candidates."""
    keys: list[str] = []
    seen: set[str] = set()
    for headword in headwords:
        key = normalize_gaffiot_headword(headword)
        if key and key not in seen:
            seen.add(key)
            keys.append(key)
    if not keys:
        return []
    if db_path is None:
        from langnet.databuild.paths import default_gaffiot_path  # noqa: PLC0415

        db_path = default_gaffiot_path()
    if not db_path.exists():
        return []

    entries: list[dict] = []
    placeholders = ",".join(["?"] * len(keys))
    with duckdb.connect(str(db_path), read_only=True) as conn:
        rows = conn.execute(
            f"""
            SELECT
                entry_id,
                headword_raw,
                headword_norm,
                variant_num,
                plain_text,
                entry_hash
            FROM entries_fr
            WHERE headword_norm IN ({placeholders})
            ORDER BY variant_num NULLS FIRST, entry_id
            """,
            keys,
        ).fetchall()
        for row in rows:
            entries.append(
                {
                    "entry_id": row[0],
                    "headword_raw": row[1],
                    "headword_norm": row[2],
                    "variant_num": row[3],
                    "plain_text": row[4],
                    "entry_hash": row[5],
                }
            )
    return entries


def gaffiot_entry_triples(entry: dict) -> list[dict]:
    """Project a resolved Gaffiot entry into evidence-bearing triples."""
    headword = entry.get("headword_norm") or normalize_gaffiot_headword(
        str(entry.get("headword_raw") or "")
    )
    entry_id = entry.get("entry_id")
    variant_num = entry.get("variant_num")
    gloss = entry.get("plain_text") or ""
    if not isinstance(gloss, str):
        gloss = ""
    display_gloss = display_text(gloss)
    lex_anchor = f"lex:{headword}"
    source_ref = f"gaffiot:{entry_id}"
    digest_material = f"{source_ref}:{gloss}"
    digest = hashlib.sha256(digest_material.encode("utf-8")).hexdigest()[:8]
    sense_anchor = f"sense:{lex_anchor}#{digest}"
    evidence = {
        "source_tool": "gaffiot",
        "source_ref": source_ref,
        "raw_blob_ref": "tei_xml",
    }
    if variant_num is not None:
        evidence["variant_num"] = variant_num
    if entry.get("entry_hash"):
        evidence["entry_hash"] = entry["entry_hash"]
    source_entry = trim_empty(
        {
            "dict": "gaffiot",
            "source_ref": source_ref,
            "entry_id": entry_id,
            "headword_raw": entry.get("headword_raw"),
            "headword_norm": headword,
            "variant_num": variant_num,
            "entry_hash": entry.get("entry_hash"),
            "source_text": gloss,
        }
    )
    source_segments = source_segments_from_text(
        gloss,
        segment_type="definition_segment",
        labels=["definition"],
    )

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
            "metadata": {
                "evidence": evidence,
                "source_lang": "fr",
                "source_ref": source_ref,
                "display_gloss": display_gloss,
                "source_entry": source_entry,
                "source_segments": source_segments,
            },
        },
    ]


class GaffiotFetchClient:
    """DuckDB-backed fetcher for local Gaffiot entries."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.tool = "fetch.gaffiot"
        self.db_path = db_path

    def execute(
        self, call_id: str, endpoint: str, params: Mapping[str, str] | None = None
    ) -> RawResponseEffect:
        params = params or {}
        candidates = [
            params.get("headword") or "",
            params.get("lemma") or "",
            params.get("q") or "",
        ]
        start = time.perf_counter()
        entries = lookup_gaffiot_entries_by_headword(candidates, self.db_path)
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


def extract_gaffiot_json(call: ToolCallSpec, raw: RawResponseEffect) -> ExtractionEffect:
    """Extract local Gaffiot lookup JSON."""
    payload: dict[str, object] = {}
    canonical = None
    try:
        loaded = orjson.loads(raw.body)
        if isinstance(loaded, dict):
            payload = loaded
            headwords = loaded.get("headwords")
            if isinstance(headwords, list):
                for headword in headwords:
                    if isinstance(headword, str) and headword:
                        canonical = normalize_gaffiot_headword(headword)
                        break
            if canonical is None:
                headword = loaded.get("headword")
                canonical = (
                    normalize_gaffiot_headword(headword) if isinstance(headword, str) else None
                )
    except Exception:
        payload = {"entries": []}

    return ExtractionEffect(
        extraction_id=stable_effect_id("gaffiot-ext", call.call_id, raw.response_id),
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        response_id=raw.response_id,
        kind="gaffiot.entries",
        canonical=canonical,
        payload=payload,
    )


def derive_gaffiot_entries(call: ToolCallSpec, extraction: ExtractionEffect) -> DerivationEffect:
    """Derive normalized Gaffiot entries from extraction payload."""
    prov = [
        ProvenanceLink(
            stage="extract",
            tool=extraction.tool,
            reference_id=extraction.extraction_id,
            metadata={"response_id": extraction.response_id},
        )
    ]
    payload = extraction.payload if isinstance(extraction.payload, Mapping) else {"entries": []}
    return DerivationEffect(
        derivation_id=stable_effect_id("gaffiot-der", call.call_id, extraction.extraction_id),
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        extraction_id=extraction.extraction_id,
        kind="gaffiot.entries",
        canonical=extraction.canonical,
        payload=payload,
        provenance_chain=prov,
    )


def claim_gaffiot_entries(call: ToolCallSpec, derivation: DerivationEffect) -> ClaimEffect:
    """Emit Gaffiot sense/gloss triples as source-language French evidence."""
    prov = list(derivation.provenance_chain or [])
    prov.append(
        ProvenanceLink(
            stage="derive",
            tool=derivation.tool,
            reference_id=derivation.derivation_id,
            metadata={"extraction_id": derivation.extraction_id},
        )
    )
    entries: list[dict] = []
    if isinstance(derivation.payload, Mapping):
        payload = cast(Mapping[str, Any], derivation.payload)
        raw_entries = payload.get("entries")
        if isinstance(raw_entries, list):
            entries = [entry for entry in raw_entries if isinstance(entry, dict)]
    triples: list[dict] = []
    for entry in entries:
        triples.extend(gaffiot_entry_triples(entry))

    subject = f"lex:{derivation.canonical}" if derivation.canonical else "lex:unknown"
    return ClaimEffect(
        claim_id=stable_effect_id("gaffiot-clm", call.call_id, derivation.derivation_id),
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        derivation_id=derivation.derivation_id,
        subject=subject,
        predicate=predicates.HAS_SENSE,
        value={"entries": entries, "triples": triples},
        provenance_chain=prov,
    )
