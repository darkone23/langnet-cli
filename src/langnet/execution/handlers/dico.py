from __future__ import annotations

import contextlib
import hashlib
import re
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast
from urllib.parse import unquote

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
from langnet.heritage.velthuis_converter import to_heritage_velthuis
from langnet.normalizer.utils import strip_accents

_DICO_URL_RE = re.compile(r"/DICO/(?P<page>[^/#?]+)\.html#(?P<entry>[^?]+)")


def normalize_dico_headword(raw: str) -> str:
    """Normalize a DICO lookup key."""
    return strip_accents((raw or "").strip()).lower()


def _strip_dico_anchor_variant(raw: str) -> str:
    """Drop Heritage/DICO numeric anchor suffixes such as ``#1`` for headword lookup."""
    return re.sub(r"#\d+$", "", raw or "")


def expand_dico_headword_candidates(headwords: list[str]) -> list[str]:
    """Build DICO lookup candidates from raw, normalized, and Velthuis forms."""
    candidates: list[str] = []
    seen: set[str] = set()

    def _add(value: str) -> None:
        key = normalize_dico_headword(value)
        if key and key not in seen:
            seen.add(key)
            candidates.append(key)

    for headword in headwords:
        if not headword:
            continue
        _add(headword)
        _add(_strip_dico_anchor_variant(headword))
        with contextlib.suppress(Exception):
            _add(to_heritage_velthuis(headword))
            _add(_strip_dico_anchor_variant(to_heritage_velthuis(headword)))
    return candidates


def extract_dico_refs_from_claims(claims) -> list[tuple[str, str]]:
    """Extract (source_page, entry_id) pairs from Heritage DICO dictionary URLs."""
    refs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for claim in claims:
        val = claim.value if isinstance(claim.value, dict) else {}
        triples = val.get("triples") if isinstance(val, dict) else None
        if not isinstance(triples, list):
            continue
        for triple in triples:
            if not isinstance(triple, dict):
                continue
            obj = triple.get("object")
            if not isinstance(obj, dict):
                continue
            dict_url = obj.get("dictionary_url")
            if not isinstance(dict_url, str):
                continue
            match = _DICO_URL_RE.search(dict_url)
            if match is None:
                continue
            ref = (unquote(match.group("page")), unquote(match.group("entry")))
            if ref not in seen:
                seen.add(ref)
                refs.append(ref)
    return refs


def lookup_dico_entries(refs: list[tuple[str, str]], db_path: Path | None = None) -> list[dict]:
    """Resolve DICO refs from the local DuckDB index."""
    if not refs:
        return []
    if db_path is None:
        from langnet.databuild.paths import default_dico_path  # noqa: PLC0415

        db_path = default_dico_path()
    if not db_path.exists():
        return []

    entries: list[dict] = []
    with duckdb.connect(str(db_path), read_only=True) as conn:
        for source_page, entry_id in refs:
            rows = conn.execute(
                """
                SELECT
                    entry_id,
                    occurrence,
                    headword_deva,
                    headword_roma,
                    headword_norm,
                    plain_text,
                    source_page
                FROM entries_fr
                WHERE source_page = ? AND entry_id = ?
                ORDER BY occurrence
                """,
                [source_page, entry_id],
            ).fetchall()
            for row in rows:
                entries.append(
                    {
                        "entry_id": row[0],
                        "occurrence": row[1],
                        "headword_deva": row[2],
                        "headword_roma": row[3],
                        "headword_norm": row[4],
                        "plain_text": row[5],
                        "source_page": row[6],
                    }
                )
    return entries


def lookup_dico_entries_by_headword(
    headwords: list[str], db_path: Path | None = None
) -> list[dict]:
    """Resolve DICO entries by normalized headword candidates."""
    keys = expand_dico_headword_candidates(headwords)
    if not keys:
        return []
    if db_path is None:
        from langnet.databuild.paths import default_dico_path  # noqa: PLC0415

        db_path = default_dico_path()
    if not db_path.exists():
        return []

    placeholders = ",".join(["?"] * len(keys))
    with duckdb.connect(str(db_path), read_only=True) as conn:
        rows = conn.execute(
            f"""
            SELECT
                entry_id,
                occurrence,
                headword_deva,
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
            "headword_deva": row[2],
            "headword_roma": row[3],
            "headword_norm": row[4],
            "plain_text": row[5],
            "source_page": row[6],
        }
        for row in rows
    ]


def dico_entry_triples(entry: dict) -> list[dict]:
    """Project a resolved DICO entry into simple evidence-bearing triples."""
    headword = entry.get("headword_norm") or entry.get("entry_id")
    entry_id = entry.get("entry_id")
    occurrence = entry.get("occurrence")
    source_page = entry.get("source_page")
    gloss = entry.get("plain_text") or ""
    if not isinstance(gloss, str):
        gloss = ""
    display_gloss = display_text(gloss)
    lex_anchor = f"lex:{headword}"
    source_ref = f"dico:{source_page}.html#{entry_id}:{occurrence}"
    digest_material = f"{source_ref}:{gloss}"
    digest = hashlib.sha256(digest_material.encode("utf-8")).hexdigest()[:8]
    sense_anchor = f"sense:{lex_anchor}#{digest}"
    evidence = {
        "source_tool": "dico",
        "source_ref": source_ref,
        "raw_blob_ref": "body_html",
    }
    source_entry = trim_empty(
        {
            "dict": "dico",
            "source_ref": source_ref,
            "entry_id": entry_id,
            "occurrence": occurrence,
            "source_page": source_page,
            "headword_deva": entry.get("headword_deva"),
            "headword_roma": entry.get("headword_roma"),
            "headword_norm": headword,
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
            "object": gloss,
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


class DicoFetchClient:
    """DuckDB-backed fetcher for local DICO entries."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.tool = "fetch.dico"
        self.db_path = db_path

    def execute(
        self, call_id: str, endpoint: str, params: Mapping[str, str] | None = None
    ) -> RawResponseEffect:
        params = params or {}
        candidates = [
            params.get("headword") or "",
            params.get("lemma") or "",
            params.get("velthuis") or "",
            params.get("q") or "",
        ]
        start = time.perf_counter()
        entries = lookup_dico_entries_by_headword(candidates, self.db_path)
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


def extract_dico_json(call: ToolCallSpec, raw: RawResponseEffect) -> ExtractionEffect:
    """Extract local DICO lookup JSON."""
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
                        canonical = normalize_dico_headword(headword)
                        break
    except Exception:
        payload = {"entries": []}

    return ExtractionEffect(
        extraction_id=stable_effect_id("dico-ext", call.call_id, raw.response_id),
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        response_id=raw.response_id,
        kind="dico.entries",
        canonical=canonical,
        payload=payload,
    )


def derive_dico_entries(call: ToolCallSpec, extraction: ExtractionEffect) -> DerivationEffect:
    """Derive normalized DICO entries from extraction payload."""
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
        derivation_id=stable_effect_id("dico-der", call.call_id, extraction.extraction_id),
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        extraction_id=extraction.extraction_id,
        kind="dico.entries",
        canonical=extraction.canonical,
        payload=payload,
        provenance_chain=prov,
    )


def claim_dico_entries(call: ToolCallSpec, derivation: DerivationEffect) -> ClaimEffect:
    """Emit DICO sense/gloss triples as source-language French evidence."""
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
        triples.extend(dico_entry_triples(entry))

    subject = f"lex:{derivation.canonical}" if derivation.canonical else "lex:unknown"
    return ClaimEffect(
        claim_id=stable_effect_id("dico-clm", call.call_id, derivation.derivation_id),
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        derivation_id=derivation.derivation_id,
        subject=subject,
        predicate=predicates.HAS_SENSE,
        value={"entries": entries, "triples": triples},
        provenance_chain=prov,
    )
