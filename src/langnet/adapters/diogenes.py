from __future__ import annotations

import structlog

from langnet.citation.cts_urn import CTSUrnMapper
from langnet.schema import DictionaryBlock, DictionaryDefinition, DictionaryEntry, MorphologyInfo

from .base import BaseBackendAdapter, DiogenesLanguages

logger = structlog.get_logger(__name__)


class DiogenesBackendAdapter(BaseBackendAdapter):
    """Adapter for Diogenes backend results."""

    def __init__(self):
        self._cts_mapper = CTSUrnMapper()

    def adapt(self, data: dict, language: str, word: str) -> list[DictionaryEntry]:
        entries: list[DictionaryEntry] = []
        morphology = self._extract_perseus_morphology(data, word)
        aggregated: dict[str, dict] = {
            "merged": {
                "definitions": [],
                "blocks": [],
                "norm_index": {},
                "chunk_types": set(),
                "terms": set(),
            }
        }
        seen_blocks: set[tuple[str, str, str]] = set()
        if morphology:
            aggregated["merged"]["chunk_types"].add("PerseusAnalysisHeader")

        for chunk in data.get("chunks", []):
            chunk_type = (
                chunk.get("chunk_type")
                or ("PerseusAnalysisHeader" if chunk.get("morphology") else None)
                or ("DiogenesMatchingReference" if chunk.get("definitions") else None)
            )
            if chunk_type in {"DiogenesMatchingReference", "DiogenesFuzzyReference"}:
                self._collect_definition_chunk(
                    chunk,
                    language,
                    word,
                    morphology,
                    chunk_type,
                    aggregated,
                    seen_blocks,
                )
            else:
                # Skip unknown/empty chunks to avoid placeholder entries
                continue

        payload = aggregated["merged"]
        metadata = {
            "chunk_types": sorted(payload["chunk_types"]),
            "terms": sorted(payload["terms"]) if payload["terms"] else None,
        }

        if payload["definitions"] or payload["blocks"] or morphology:
            entries.append(
                DictionaryEntry(
                    source="diogenes",
                    language=language,
                    word=word,
                    definitions=payload["definitions"],
                    morphology=morphology,
                    metadata=metadata,
                    dictionary_blocks=payload["blocks"],
                )
            )

        return entries

    def _extract_perseus_morphology(self, data: dict, fallback_word: str) -> MorphologyInfo | None:
        chunks = data.get("chunks", [])
        for chunk in chunks:
            has_morph = bool(chunk.get("morphology"))
            if chunk.get("chunk_type") == "PerseusAnalysisHeader" or has_morph:
                morph = chunk.get("morphology", {})
                morphs = morph.get("morphs") or []
                if morphs:
                    first = morphs[0]
                    tags = first.get("tags", [])
                    lemma = first.get("stem", [fallback_word])
                    lemma_text = lemma[0] if isinstance(lemma, list) and lemma else fallback_word
                    return MorphologyInfo(
                        lemma=lemma_text,
                        pos=tags[0] if tags else "unknown",
                        features={"tags": tags, "raw": morphs},
                        foster_codes=first.get("foster_codes"),
                    )
        return None

    def _collect_definition_chunk(
        self,
        chunk: dict,
        language: str,
        word: str,
        morphology: MorphologyInfo | None,
        chunk_type: str | None,
        aggregated: dict[str, dict],
        seen_blocks: set[tuple[str, str, str]],
    ) -> None:
        diogenes_definitions = chunk.get("definitions") or {}
        term = diogenes_definitions.get("term") or word
        blocks_data = diogenes_definitions.get("blocks") or []

        blocks: list[DictionaryBlock] = []
        definitions: list[DictionaryDefinition] = []
        merged = aggregated.get("merged")
        norm_index: dict[str, int] = merged.get("norm_index", {})

        for block in blocks_data:
            entry_text = block.get("entry") or term
            entry_id = str(block.get("entryid") or entry_text)
            block_key = (term, entry_id, entry_text)
            if block_key in seen_blocks:
                continue
            seen_blocks.add(block_key)
            normalized_entry = " ".join(entry_text.split())
            existing_idx = norm_index.get(normalized_entry)
            citations = block.get("citations") or {}
            original_citations = block.get("original_citations") or {}
            citation_details = self._enrich_citations(citations, language)
            if original_citations == citations:
                original_citations = {}
            block_metadata = {}
            if block.get("heading"):
                block_metadata["heading"] = block["heading"]
            if block.get("diogenes_warning"):
                block_metadata["diogenes_warning"] = block["diogenes_warning"]
            for meta_key in ("pos", "foster_codes", "source"):
                if block.get(meta_key):
                    block_metadata[meta_key] = block[meta_key]
            if block.get("metadata"):
                block_metadata.update(block["metadata"])

            if existing_idx is not None:
                # Merge citations/metadata into existing block/definition to avoid duplicates.
                existing_block = merged["blocks"][existing_idx]
                existing_block.citations = {**(existing_block.citations or {}), **citations}
                existing_block.original_citations = {
                    **(existing_block.original_citations or {}),
                    **original_citations,
                }
                existing_block.citation_details = {
                    **(existing_block.citation_details or {}),
                    **(citation_details or {}),
                }
                if block_metadata:
                    existing_block.metadata = {**(existing_block.metadata or {}), **block_metadata}

                existing_def = merged["definitions"][existing_idx]
                if isinstance(existing_def.metadata, dict):
                    merged_md = existing_def.metadata
                    merged_md["citations"] = {**(merged_md.get("citations") or {}), **citations}
                    merged_md["citation_details"] = {
                        **(merged_md.get("citation_details") or {}),
                        **(citation_details or {}),
                    }
                    if block_metadata:
                        merged_md["block_metadata"] = {
                            **(merged_md.get("block_metadata") or {}),
                            **block_metadata,
                        }
                    existing_def.metadata = merged_md
                continue

            blocks.append(
                DictionaryBlock(
                    entry=entry_text,
                    entryid=entry_id,
                    citations=citations,
                    original_citations=original_citations,
                    citation_details=citation_details or {},
                    metadata=block_metadata,
                )
            )
            definitions.append(
                DictionaryDefinition(
                    definition=entry_text,
                    pos=self._extract_pos_from_entry(entry_text),
                    metadata={
                        "entryid": entry_id,
                        "citations": citations or {},
                        "citation_details": citation_details or {},
                        "block_metadata": block_metadata or {},
                    },
                )
            )
            norm_index[normalized_entry] = len(merged["blocks"]) + len(blocks) - 1

        merged.setdefault("norm_index", {})
        merged["definitions"].extend(definitions)
        merged["blocks"].extend(blocks)
        if chunk_type:
            merged["chunk_types"].add(chunk_type)
        term_value = term or word
        if term_value:
            merged["terms"].add(term_value)

    def _enrich_citations(self, citations: dict, language: str) -> dict[str, dict[str, str]]:
        """Add author/work metadata for CTS URNs and known abbreviations."""
        if not citations:
            return {}

        details: dict[str, dict[str, str]] = {}
        for urn, citation_text in citations.items():
            info: dict[str, str] | None = None
            if urn.startswith("urn:cts"):
                info = self._cts_mapper.get_urn_metadata(urn, citation_text)
                if info:
                    info = {**info, "kind": "cts"}
            if not info:
                info = self._cts_mapper.get_abbreviation_metadata(
                    citation_id=urn, citation_text=citation_text, language=language
                )

            if not info:
                details[urn] = {"text": citation_text}
                continue

            display = info.get("display") or ""
            if not display:
                author = info.get("author")
                work = info.get("work")
                if author and work:
                    display = f"{author} - {work}"
                elif author:
                    display = author
                elif work:
                    display = work
                else:
                    display = citation_text

            details[urn] = {
                "text": citation_text,
                "author": info.get("author"),
                "work": info.get("work"),
                "display": display,
                "kind": info.get("kind") or ("cts" if urn.startswith("urn:cts") else "abbreviation"),
            }
        return details
