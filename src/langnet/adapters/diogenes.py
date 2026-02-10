from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TypedDict, cast

import structlog

from langnet.citation.cts_urn import CTSUrnMapper
from langnet.schema import DictionaryBlock, DictionaryDefinition, DictionaryEntry, MorphologyInfo
from langnet.types import JSONMapping, JSONValue

from .base import BaseBackendAdapter

logger = structlog.get_logger(__name__)


class _MergedAggregate(TypedDict):
    definitions: list[DictionaryDefinition]
    blocks: list[DictionaryBlock]
    norm_index: dict[str, int]
    chunk_types: set[str]
    terms: set[str]


@dataclass
class _CollectionContext:
    language: str
    word: str
    aggregated: dict[str, _MergedAggregate]
    seen_blocks: set[tuple[str, str, str]]


@dataclass
class _BlockBuildContext:
    entry_text: str
    entry_id: str
    citations: dict[str, str]
    original_citations: dict[str, str]
    citation_details: dict[str, dict[str, str]] | None
    block_metadata: JSONMapping


class DiogenesBackendAdapter(BaseBackendAdapter):
    """Adapter for Diogenes backend results."""

    def __init__(self):
        self._cts_mapper = CTSUrnMapper()

    def adapt(
        self,
        data: dict[str, object],
        language: str,
        word: str,
        timings: dict[str, float] | None = None,
    ) -> list[DictionaryEntry]:
        overall_start = time.perf_counter() if timings is not None else None
        entries: list[DictionaryEntry] = []
        morphology = self._time_section(
            "adapt_diogenes_morphology_extract",
            timings,
            lambda: self._extract_perseus_morphology(data, word),
        )
        merged: _MergedAggregate = {
            "definitions": [],
            "blocks": [],
            "norm_index": {},
            "chunk_types": set(),
            "terms": set(),
        }
        aggregated: dict[str, _MergedAggregate] = {"merged": merged}
        seen_blocks: set[tuple[str, str, str]] = set()
        if morphology:
            aggregated["merged"]["chunk_types"].add("PerseusAnalysisHeader")

        context = _CollectionContext(
            language=language,
            word=word,
            aggregated=aggregated,
            seen_blocks=seen_blocks,
        )

        chunks = self._normalize_chunks(data.get("chunks"))
        if not chunks:
            return entries

        self._process_chunks(chunks, context, timings)

        payload = aggregated["merged"]
        metadata = {
            "chunk_types": self._ordered_chunk_types(payload["chunk_types"]),
            "terms": sorted(payload["terms"]) if payload["terms"] else None,
        }

        if payload["blocks"] or morphology:
            self._prune_morphology_duplicates(morphology)
            entries.append(
                DictionaryEntry(
                    source="diogenes",
                    language=language,
                    word=word,
                    definitions=[],  # Don't duplicate block content in definitions
                    morphology=morphology,
                    metadata=metadata,
                    dictionary_blocks=payload["blocks"],
                )
            )

        if overall_start is not None and timings is not None:
            timings["adapt_diogenes_internal"] = (time.perf_counter() - overall_start) * 1000
            diogenes_timings = {k: v for k, v in timings.items() if k.startswith("adapt_diogenes")}
            diogenes_timings["chunk_count"] = len(chunks)
            logger.info(
                "diogenes_adapter_timings",
                word=word,
                language=language,
                timings=diogenes_timings,
            )
        return entries

    @staticmethod
    def _time_section(name: str, timings: dict[str, float] | None, func):
        if timings is None:
            return func()
        start = time.perf_counter()
        try:
            return func()
        finally:
            timings[name] = timings.get(name, 0.0) + (time.perf_counter() - start) * 1000

    def _extract_perseus_morphology(
        self, data: dict[str, object], fallback_word: str
    ) -> MorphologyInfo | None:
        chunks_raw = data.get("chunks")
        if not isinstance(chunks_raw, list):
            return None
        chunks: list[dict[str, object]] = [
            cast(dict[str, object], c) for c in chunks_raw if isinstance(c, dict)
        ]
        for chunk in chunks:
            has_morph = bool(chunk.get("morphology"))
            if chunk.get("chunk_type") == "PerseusAnalysisHeader" or has_morph:
                morph_data = chunk.get("morphology", {})
                if not isinstance(morph_data, dict):
                    continue
                morph: dict[str, object] = cast(dict[str, object], morph_data)
                morphs_raw = morph.get("morphs")
                morphs: list[dict[str, object]] = (
                    [cast(dict[str, object], m) for m in morphs_raw if isinstance(m, dict)]
                    if isinstance(morphs_raw, list)
                    else []
                )
                if morphs:
                    first = morphs[0]
                    tags_raw = first.get("tags")
                    tags = [str(tag) for tag in tags_raw] if isinstance(tags_raw, list) else []
                    lemma_raw = first.get("stem")
                    lemma_candidates = lemma_raw if isinstance(lemma_raw, list) else None
                    lemma_text = lemma_candidates[0] if lemma_candidates else fallback_word
                    foster_codes = first.get("foster_codes")
                    foster_clean: list[str] | dict[str, str] | None = None
                    if isinstance(foster_codes, list):
                        foster_clean = [str(code) for code in foster_codes]
                    elif isinstance(foster_codes, dict):
                        foster_clean = {str(k): str(v) for k, v in foster_codes.items()}
                    return MorphologyInfo(
                        lemma=lemma_text,
                        pos=tags[0] if tags else "unknown",
                        features={
                            "tags": tags,
                            "raw": [self._normalize_morph_entry(m) for m in morphs],
                        },
                        foster_codes=foster_clean,
                    )
        return None

    def _collect_definition_chunk(
        self,
        chunk: dict[str, object],
        chunk_type: str | None,
        context: _CollectionContext,
        timings: dict[str, float] | None = None,
    ) -> None:
        diogenes_definitions_raw = chunk.get("definitions") or {}
        if not isinstance(diogenes_definitions_raw, dict):
            return
        diogenes_definitions: dict[str, object] = cast(dict[str, object], diogenes_definitions_raw)
        term_val = diogenes_definitions.get("term")
        term = term_val if isinstance(term_val, str) else context.word
        blocks_data_raw = diogenes_definitions.get("blocks") or []
        if not isinstance(blocks_data_raw, list):
            return
        blocks_data: list[dict[str, object]] = [
            cast(dict[str, object], block) for block in blocks_data_raw if isinstance(block, dict)
        ]

        merged = context.aggregated["merged"]
        norm_index: dict[str, int] = merged.get("norm_index", {})

        for block in blocks_data:
            entry_val = block.get("entry")
            entry_text = entry_val if isinstance(entry_val, str) else term
            entry_id = str(block.get("entryid") or entry_text)
            block_key = (term, entry_id, entry_text)
            if self._already_seen_block(block_key, context.seen_blocks):
                continue
            normalized_entry = " ".join(entry_text.split())
            existing_idx = norm_index.get(normalized_entry)

            citations_raw = block.get("citations") or {}
            citations = (
                {str(k): str(v) for k, v in citations_raw.items()}
                if isinstance(citations_raw, dict)
                else {}
            )
            original_citations_raw = block.get("original_citations") or {}
            original_citations = (
                {str(k): str(v) for k, v in original_citations_raw.items()}
                if isinstance(original_citations_raw, dict)
                else {}
            )
            original_citations = self._strip_duplicate_originals(citations, original_citations)
            citation_details = self._time_section(
                "adapt_diogenes_enrich_citations",
                timings,
                lambda: self._enrich_citations(citations, context.language),
            )
            block_metadata = self._build_block_metadata(block)
            block_ctx = _BlockBuildContext(
                entry_text=entry_text,
                entry_id=entry_id,
                citations=citations,
                original_citations=original_citations,
                citation_details=citation_details,
                block_metadata=block_metadata,
            )

            if existing_idx is not None:
                self._time_section(
                    "adapt_diogenes_merge_block",
                    timings,
                    lambda: self._merge_existing_block(merged, existing_idx, block_ctx),
                )
                continue

            block_obj = self._time_section(
                "adapt_diogenes_create_block",
                timings,
                lambda: self._create_block(block_ctx),
            )
            # Append directly to the merged list so norm_index stays in lockstep with the
            # real block positions; staging in a temp list made merge-by-index brittle.
            merged["blocks"].append(block_obj)
            norm_index[normalized_entry] = len(merged["blocks"]) - 1

        merged.setdefault("norm_index", {})
        if chunk_type:
            merged["chunk_types"].add(chunk_type)
        term_value = term or context.word
        if term_value:
            merged["terms"].add(term_value)

    def _process_chunks(
        self,
        chunks: list[dict[str, object]],
        context: _CollectionContext,
        timings: dict[str, float] | None,
    ) -> None:
        for chunk in chunks:
            chunk_type = self._detect_chunk_type(chunk)
            if chunk_type in {"DiogenesMatchingReference", "DiogenesFuzzyReference"}:
                self._time_section(
                    "adapt_diogenes_chunk",
                    timings,
                    lambda c=chunk, ct=chunk_type: self._collect_definition_chunk(
                        c, ct, context, timings
                    ),
                )
            elif chunk.get("morphology"):
                context.aggregated["merged"]["chunk_types"].add("PerseusAnalysisHeader")

    def _ordered_chunk_types(self, chunk_types: set[str]) -> list[str]:
        ordered: list[str] = []
        for kind in (
            "PerseusAnalysisHeader",
            "DiogenesMatchingReference",
            "DiogenesFuzzyReference",
        ):
            if kind in chunk_types:
                ordered.append(kind)
        return ordered

    @staticmethod
    def _detect_chunk_type(chunk: dict[str, object]) -> str | None:
        chunk_type_val = chunk.get("chunk_type")
        chunk_type: str | None = chunk_type_val if isinstance(chunk_type_val, str) else None
        if chunk_type:
            return chunk_type
        if chunk.get("morphology"):
            return "PerseusAnalysisHeader"
        if chunk.get("definitions"):
            return "DiogenesMatchingReference"
        return None

    @staticmethod
    def _normalize_chunks(chunks_raw: object) -> list[dict[str, object]]:
        if not isinstance(chunks_raw, list):
            return []
        return [cast(dict[str, object], c) for c in chunks_raw if isinstance(c, dict)]

    @staticmethod
    def _already_seen_block(
        block_key: tuple[str, str, str],
        seen_blocks: set[tuple[str, str, str]],
    ) -> bool:
        if block_key in seen_blocks:
            return True
        seen_blocks.add(block_key)
        return False

    @staticmethod
    def _strip_duplicate_originals(
        citations: dict[str, str], original_citations: dict[str, str]
    ) -> dict[str, str]:
        if original_citations == citations:
            return {}
        return original_citations

    @staticmethod
    def _build_block_metadata(
        block: dict[str, object],
    ) -> JSONMapping:
        block_metadata: JSONMapping = {}
        heading = block.get("heading")
        if heading:
            block_metadata["heading"] = str(heading)
        diogenes_warning = block.get("diogenes_warning")
        if diogenes_warning:
            block_metadata["diogenes_warning"] = str(diogenes_warning)
        # Avoid duplicating morphology payload (tags/foster_codes) in metadata; morphology lives on
        # the entry. Keep only lightweight block descriptors.
        for meta_key in ("pos", "source"):
            if meta_key in block:
                block_metadata[meta_key] = DiogenesBackendAdapter._json_value(block.get(meta_key))
        metadata_raw = block.get("metadata")
        if isinstance(metadata_raw, dict):
            for key, value in metadata_raw.items():
                if str(key) in {"tags", "foster_codes", "morphology", "morphs"}:
                    continue
                block_metadata[str(key)] = DiogenesBackendAdapter._json_value(value)
        return block_metadata

    @staticmethod
    def _json_value(value: object) -> JSONValue:
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if isinstance(value, list):
            return [DiogenesBackendAdapter._json_value(item) for item in value]
        if isinstance(value, dict):
            return {str(k): DiogenesBackendAdapter._json_value(v) for k, v in value.items()}
        return str(value)

    @staticmethod
    def _normalize_morph_entry(entry: dict[str, object]) -> dict[str, str | list[str] | None]:
        normalized: dict[str, str | list[str] | None] = {}
        for key, value in entry.items():
            if key in {"tags", "foster_codes"}:
                continue
            if isinstance(value, list):
                normalized[key] = [str(v) for v in value]
            elif isinstance(value, dict):
                normalized[key] = [f"{k}:{v}" for k, v in value.items()]
            elif value is None:
                normalized[key] = None
            else:
                normalized[key] = str(value)
        return normalized

    @staticmethod
    def _prune_morphology_duplicates(morphology: MorphologyInfo | None) -> None:
        """Drop duplicate tag/foster fields from raw morphology."""
        if not morphology:
            return

        raw = morphology.features.get("raw")
        if not isinstance(raw, list):
            return

        cleaned_raw: list[dict[str, object]] = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            cleaned_raw.append(
                {k: v for k, v in entry.items() if k not in {"tags", "foster_codes"}}
            )
        cleaned_typed = cast(list[dict[str, str | list[str] | None]], cleaned_raw)
        morphology.features["raw"] = cleaned_typed

    def _create_block(self, block_ctx: _BlockBuildContext) -> DictionaryBlock:
        block_obj = DictionaryBlock(
            entry=block_ctx.entry_text,
            entryid=block_ctx.entry_id,
            citations=block_ctx.citations,
            original_citations=block_ctx.original_citations,
            citation_details=block_ctx.citation_details or {},
            metadata=block_ctx.block_metadata,
        )
        return block_obj

    def _merge_existing_block(
        self,
        merged: _MergedAggregate,
        existing_idx: int,
        block_ctx: _BlockBuildContext,
    ) -> None:
        existing_block = merged["blocks"][existing_idx]
        existing_block.citations = {**(existing_block.citations or {}), **block_ctx.citations}
        existing_block.original_citations = {
            **(existing_block.original_citations or {}),
            **block_ctx.original_citations,
        }
        existing_block.citation_details = {
            **(existing_block.citation_details or {}),
            **(block_ctx.citation_details or {}),
        }
        if block_ctx.block_metadata:
            existing_block.metadata = {
                **(existing_block.metadata or {}),
                **block_ctx.block_metadata,
            }

        # No need to update definitions since we're not creating them

    def _enrich_citations(self, citations: dict, language: str) -> dict[str, dict[str, str]]:
        """Add author/work metadata for CTS URNs and known abbreviations."""
        if not citations:
            return {}

        cts_urns = {
            urn: citation_text
            for urn, citation_text in citations.items()
            if urn.startswith("urn:cts")
        }
        cts_metadata = self._cts_mapper.get_urn_metadata_bulk(cts_urns) if cts_urns else {}

        details: dict[str, dict[str, str]] = {}
        for urn, citation_text in citations.items():
            info: dict[str, str] | None = None
            if urn.startswith("urn:cts"):
                info = cts_metadata.get(urn)
                if info:
                    info = {**info, "kind": "cts"}
            if not info:
                info = self._cts_mapper.get_abbreviation_metadata(
                    citation_id=urn, citation_text=citation_text, language=language
                )

            if not info:
                details[urn] = {"text": citation_text}
                continue

            display = self._build_display(info, citation_text, urn)
            details[urn] = {
                "text": citation_text,
                "author": info.get("author") or "",
                "work": info.get("work") or "",
                "display": display,
                "kind": info.get("kind")
                or ("cts" if urn.startswith("urn:cts") else "abbreviation"),
            }
        return details

    @staticmethod
    def _build_display(info: dict[str, str], citation_text: str, urn: str) -> str:
        display = info.get("display") or ""
        if display:
            return display

        author = info.get("author") or ""
        work = info.get("work") or ""
        if author and work:
            return f"{author} - {work}"
        if author:
            return author
        if work:
            return work
        if urn.startswith("urn:cts"):
            return citation_text
        return citation_text
