from __future__ import annotations

import hashlib
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

import orjson
from query_spec import ToolCallSpec

from langnet.clients.base import RawResponseEffect
from langnet.databuild.bailly import lookup_bailly_entries
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
    compact_source_gloss,
    display_text,
    learner_segments_from_text,
    source_segments_from_text,
    trim_empty,
)
from langnet.normalizer.utils import normalize_greekish_token


def normalize_bailly_headword(raw: str) -> str:
    """Normalize a Greek headword for Bailly lookup."""
    return normalize_greekish_token(raw) or raw.strip().lower()


def _split_candidate_param(value: str | None) -> list[str]:
    if not value:
        return []
    return [candidate.strip() for candidate in value.split(";") if candidate.strip()]


def _dedupe_candidates(candidates: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = normalize_bailly_headword(candidate)
        if key and key not in seen:
            seen.add(key)
            ordered.append(candidate)
    return ordered


class BaillyFetchClient:
    """DuckDB-backed fetcher for local Bailly entries."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.tool = "fetch.bailly"
        self.db_path = db_path

    def execute(
        self, call_id: str, endpoint: str, params: Mapping[str, str] | None = None
    ) -> RawResponseEffect:
        params = params or {}
        candidates = [
            params.get("headword") or "",
            params.get("lemma") or "",
            params.get("q") or "",
            *_split_candidate_param(params.get("lemma_candidates")),
        ]
        start = time.perf_counter()
        entries: list[dict[str, Any]] = []
        matched_headword = None
        for candidate in _dedupe_candidates(candidates):
            entries = lookup_bailly_entries(candidate, self.db_path)
            if entries:
                matched_headword = candidate
                break
        duration_ms = int((time.perf_counter() - start) * 1000)
        resolved_canonical = _canonical_from_entries(entries)
        body = orjson.dumps(
            {
                "headwords": candidates,
                "matched_headword": matched_headword,
                "resolved_canonical": resolved_canonical,
                "entries": entries,
            }
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


def _safe_block_ordinal(block: Mapping[str, Any], fallback: int) -> int:
    ordinal = block.get("ordinal")
    if ordinal is None:
        return fallback
    try:
        return int(cast(Any, ordinal))
    except (TypeError, ValueError):
        return fallback


def _bailly_source_text(entry: Mapping[str, Any]) -> str:
    blocks = entry.get("blocks")
    if isinstance(blocks, list):
        ordered_blocks = [block for block in blocks if isinstance(block, Mapping)]
        ordered_blocks = [
            block
            for _, block in sorted(
                enumerate(ordered_blocks),
                key=lambda item: (_safe_block_ordinal(item[1], item[0]), item[0]),
            )
        ]
        parts = []
        for block in ordered_blocks:
            marker = str(block.get("marker") or "").strip().lower()
            text = block.get("text")
            if marker != "head" and isinstance(text, str) and text.strip():
                parts.append(text.strip())
        if parts:
            return " ".join(parts)
    raw_text = entry.get("raw_text")
    return raw_text if isinstance(raw_text, str) else ""


def _ordered_bailly_blocks(entry: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    blocks = entry.get("blocks")
    if not isinstance(blocks, list):
        return []
    ordered_blocks = [block for block in blocks if isinstance(block, Mapping)]
    return [
        block
        for _, block in sorted(
            enumerate(ordered_blocks),
            key=lambda item: (_safe_block_ordinal(item[1], item[0]), item[0]),
        )
    ]


def _bailly_block_ref(source_ref: str, path: str) -> str:
    return f"{source_ref}:{path}"


def _bailly_block_parent_path(path: str) -> str | None:
    if ":" not in path:
        return None
    parent = path.rsplit(":", 1)[0].strip()
    return parent or None


def _bailly_block_level(path: str, marker: str) -> int:
    if marker.strip().lower() == "head":
        return 0
    return path.count(":") + 1 if path else 1


def _bailly_source_blocks(entry: Mapping[str, Any], source_ref: str) -> list[dict[str, Any]]:
    source_blocks: list[dict[str, Any]] = []
    for fallback, block in enumerate(_ordered_bailly_blocks(entry)):
        text = block.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        marker = str(block.get("marker") or "").strip()
        path = str(block.get("path") or f"{fallback:02d}").strip()
        layout = block.get("layout")
        source_blocks.append(
            trim_empty(
                {
                    "path": path,
                    "parent_path": _bailly_block_parent_path(path),
                    "level": _bailly_block_level(path, marker),
                    "marker": marker,
                    "kind": "head" if marker.lower() == "head" else "sense",
                    "ordinal": _safe_block_ordinal(block, fallback),
                    "text": text.strip(),
                    "source_ref": _bailly_block_ref(source_ref, path),
                    "layout": dict(layout) if isinstance(layout, Mapping) else None,
                }
            )
        )
    return source_blocks


def _bailly_body_source_blocks(
    source_blocks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [block for block in source_blocks if block.get("kind") != "head"]


def _bailly_source_segments_from_blocks(
    source_blocks: list[dict[str, Any]],
) -> list[dict[str, object]]:
    segments: list[dict[str, object]] = []
    for block in _bailly_body_source_blocks(source_blocks):
        text = str(block.get("text") or "").strip()
        if not text:
            continue
        segment = {
            "index": len(segments),
            "raw_text": text,
            "display_text": display_text(text),
            "segment_type": "definition_segment",
            "labels": ["definition"],
            "source_ref": block.get("source_ref"),
            "source_path": block.get("path"),
            "source_marker": block.get("marker"),
            "source_level": block.get("level"),
            "parent_path": block.get("parent_path"),
        }
        segments.append(trim_empty(segment))
    return segments


def _canonical_from_entry(entry: Mapping[str, Any]) -> str | None:
    lemma_norm = entry.get("lemma_norm")
    if isinstance(lemma_norm, str) and lemma_norm.strip():
        return normalize_bailly_headword(lemma_norm)
    lemma = entry.get("lemma")
    if isinstance(lemma, str) and lemma.strip():
        return normalize_bailly_headword(lemma)
    return None


def _canonical_from_entries(entries: object) -> str | None:
    if not isinstance(entries, list):
        return None
    for entry in entries:
        if isinstance(entry, Mapping):
            canonical = _canonical_from_entry(cast(Mapping[str, Any], entry))
            if canonical:
                return canonical
    return None


def _source_ref_for_entry(entry: Mapping[str, Any], source_text: str) -> str:
    entry_id = entry.get("entry_id")
    if isinstance(entry_id, str) and entry_id.strip():
        return f"bailly:{entry_id}"
    digest_material = {
        "lemma": entry.get("lemma"),
        "lemma_norm": entry.get("lemma_norm"),
        "page_start": entry.get("page_start"),
        "page_end": entry.get("page_end"),
        "source_text": source_text,
    }
    digest = hashlib.sha256(orjson.dumps(digest_material, option=orjson.OPT_SORT_KEYS)).hexdigest()[
        :12
    ]
    return f"bailly:generated:{digest}"


def bailly_entry_triples(entry: dict) -> list[dict]:
    """Project a resolved Bailly entry into evidence-bearing triples."""
    headword = entry.get("lemma_norm") or normalize_bailly_headword(str(entry.get("lemma") or ""))
    entry_id = entry.get("entry_id")
    page_start = entry.get("page_start")
    page_end = entry.get("page_end")
    source_text = _bailly_source_text(entry)
    display_gloss = display_text(source_text)
    lex_anchor = f"lex:{headword}"
    source_ref = _source_ref_for_entry(entry, source_text)
    source_blocks = _bailly_source_blocks(entry, source_ref)
    digest_material = f"{source_ref}:{source_text}"
    digest = hashlib.sha256(digest_material.encode("utf-8")).hexdigest()[:8]
    sense_anchor = f"sense:{lex_anchor}#{digest}"
    evidence = trim_empty(
        {
            "source_tool": "bailly",
            "source_ref": source_ref,
            "raw_blob_ref": "pdf_structural_jsonl",
            "page_start": page_start,
            "page_end": page_end,
        }
    )
    source_entry = trim_empty(
        {
            "dict": "bailly",
            "source_ref": source_ref,
            "entry_id": entry_id,
            "lemma": entry.get("lemma"),
            "lemma_norm": headword,
            "page_start": page_start,
            "page_end": page_end,
            "source_text": source_text,
            "blocks": source_blocks,
        }
    )
    source_segments = _bailly_source_segments_from_blocks(source_blocks)
    if not source_segments:
        source_segments = source_segments_from_text(
            source_text,
            segment_type="definition_segment",
            labels=["definition"],
        )
    learner_gloss = compact_source_gloss(source_text)
    learner_segments = learner_segments_from_text(source_text)

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
                    "source_lang": "fr",
                    "source_ref": source_ref,
                    "display_gloss": display_gloss,
                    "learner_gloss": learner_gloss,
                    "learner_segments": learner_segments,
                    "source_entry": source_entry,
                    "source_blocks": source_blocks,
                    "source_segments": source_segments,
                }
            ),
        },
    ]


def extract_bailly_json(call: ToolCallSpec, raw: RawResponseEffect) -> ExtractionEffect:
    """Extract local Bailly lookup JSON."""
    payload: dict[str, object] = {}
    canonical = None
    try:
        loaded = orjson.loads(raw.body)
        if isinstance(loaded, dict):
            payload = loaded
            canonical = _canonical_from_entries(loaded.get("entries"))
            resolved_canonical = loaded.get("resolved_canonical")
            if canonical is None and isinstance(resolved_canonical, str):
                canonical = normalize_bailly_headword(resolved_canonical)
            matched_headword = loaded.get("matched_headword")
            if canonical is None and isinstance(matched_headword, str):
                canonical = normalize_bailly_headword(matched_headword)
            headwords = loaded.get("headwords")
            if canonical is None and isinstance(headwords, list):
                for headword in headwords:
                    if isinstance(headword, str) and headword:
                        canonical = normalize_bailly_headword(headword)
                        break
            if canonical is None:
                headword = loaded.get("headword")
                canonical = (
                    normalize_bailly_headword(headword) if isinstance(headword, str) else None
                )
    except Exception:
        payload = {"entries": []}

    return ExtractionEffect(
        extraction_id=stable_effect_id("bailly-ext", call.call_id, raw.response_id),
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        response_id=raw.response_id,
        kind="bailly.entries",
        canonical=canonical,
        payload=payload,
    )


def derive_bailly_entries(call: ToolCallSpec, extraction: ExtractionEffect) -> DerivationEffect:
    """Derive normalized Bailly entries from extraction payload."""
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
        derivation_id=stable_effect_id("bailly-der", call.call_id, extraction.extraction_id),
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        extraction_id=extraction.extraction_id,
        kind="bailly.entries",
        canonical=extraction.canonical,
        payload=payload,
        provenance_chain=prov,
    )


def claim_bailly_entries(call: ToolCallSpec, derivation: DerivationEffect) -> ClaimEffect:
    """Emit Bailly sense/gloss triples as source-language French evidence."""
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
        triples.extend(bailly_entry_triples(entry))

    subject = f"lex:{derivation.canonical}" if derivation.canonical else "lex:unknown"
    return ClaimEffect(
        claim_id=stable_effect_id("bailly-clm", call.call_id, derivation.derivation_id),
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        derivation_id=derivation.derivation_id,
        subject=subject,
        predicate=predicates.HAS_SENSE,
        value={"entries": entries, "triples": triples},
        provenance_chain=prov,
    )
