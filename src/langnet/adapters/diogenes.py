from __future__ import annotations

import structlog

from langnet.schema import DictionaryBlock, DictionaryDefinition, DictionaryEntry, MorphologyInfo

from .base import BaseBackendAdapter, DiogenesLanguages

logger = structlog.get_logger(__name__)


class DiogenesBackendAdapter(BaseBackendAdapter):
    """Adapter for Diogenes backend results."""

    def adapt(self, data: dict, language: str, word: str) -> list[DictionaryEntry]:
        entries: list[DictionaryEntry] = []
        morphology = self._extract_perseus_morphology(data, word)

        for chunk in data.get("chunks", []):
            chunk_type = (
                chunk.get("chunk_type")
                or ("PerseusAnalysisHeader" if chunk.get("morphology") else None)
                or ("DiogenesMatchingReference" if chunk.get("definitions") else None)
            )
            if chunk_type in {"DiogenesMatchingReference", "DiogenesFuzzyReference"}:
                entries.extend(
                    self._adapt_definition_chunk(chunk, language, word, morphology, chunk_type)
                )
            elif chunk_type == "PerseusAnalysisHeader":
                # Preserve morphology-only chunks for completeness
                entries.append(
                    DictionaryEntry(
                        source="diogenes",
                        language=language,
                        word=word,
                        definitions=[],
                        morphology=morphology,
                        metadata={"chunk_type": chunk_type},
                    )
                )
            else:
                # Skip unknown/empty chunks to avoid placeholder entries
                continue

        return entries

    def _extract_perseus_morphology(self, data: dict, fallback_word: str) -> MorphologyInfo | None:
        chunks = data.get("chunks", [])
        for chunk in chunks:
            if chunk.get("chunk_type") == "PerseusAnalysisHeader":
                morph = chunk.get("morphology", {})
                if "morphs" in morph and morph["morphs"]:
                    first = morph["morphs"][0]
                    tags = first.get("tags", [])
                    lemma = first.get("stem", [fallback_word])
                    lemma_text = lemma[0] if isinstance(lemma, list) and lemma else fallback_word
                    return MorphologyInfo(
                        lemma=lemma_text,
                        pos=tags[0] if tags else "unknown",
                        features={"tags": tags},
                    )
        return None

    def _adapt_definition_chunk(
        self,
        chunk: dict,
        language: str,
        word: str,
        morphology: MorphologyInfo | None,
        chunk_type: str | None,
    ) -> list[DictionaryEntry]:
        entries: list[DictionaryEntry] = []

        diogenes_definitions = chunk.get("definitions") or {}
        term = diogenes_definitions.get("term") or word
        blocks_data = diogenes_definitions.get("blocks") or []

        blocks: list[DictionaryBlock] = []
        definitions: list[DictionaryDefinition] = []

        for block in blocks_data:
            entry_text = block.get("entry") or term
            entry_id = str(block.get("entryid") or "")
            citations = block.get("citations") or {}
            block_metadata = {}
            if block.get("heading"):
                block_metadata["heading"] = block["heading"]
            if block.get("diogenes_warning"):
                block_metadata["diogenes_warning"] = block["diogenes_warning"]

            blocks.append(
                DictionaryBlock(
                    entry=entry_text,
                    entryid=entry_id,
                    citations=citations or {},
                    original_citations=citations or {},
                    metadata=block_metadata,
                )
            )
            definitions.append(
                DictionaryDefinition(
                    definition=entry_text,
                    pos=self._extract_pos_from_entry(entry_text),
                    metadata={"entryid": entry_id},
                )
            )

        entries.append(
            DictionaryEntry(
                source="diogenes",
                language=language,
                word=word,
                definitions=definitions,
                morphology=morphology,
                metadata={"chunk_type": chunk_type or chunk.get("chunk_type"), "term": term},
                dictionary_blocks=blocks,
            )
        )

        return entries
