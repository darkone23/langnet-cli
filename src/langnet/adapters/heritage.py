from __future__ import annotations

import structlog

from langnet.schema import DictionaryDefinition, DictionaryEntry, MorphologyInfo

from .base import BaseBackendAdapter

logger = structlog.get_logger(__name__)


class HeritageBackendAdapter(BaseBackendAdapter):
    """Adapter for Heritage Platform morphology/dictionary responses."""

    def adapt(self, data: dict, language: str, word: str) -> list[DictionaryEntry]:
        entries: list[DictionaryEntry] = []

        combined = data.get("combined_analysis") or data.get("dictionary") or {}
        dict_entries = combined.get("dictionary_entries") or combined.get("entries") or []

        morphology = None
        if combined:
            morph_pos = combined.get("pos")
            analyses = combined.get("morphology_analyses") or []
            if not morph_pos and analyses and isinstance(analyses[0], dict):
                morph_pos = analyses[0].get("analysis")
            lemma = combined.get("lemma") or word
            morph_features = {"analyses": analyses}
            morphology = MorphologyInfo(
                lemma=lemma,
                pos=self._extract_pos_from_entry(morph_pos or ""),
                features=morph_features,
            )

        definitions = []
        for entry in dict_entries:
            definition_text = entry.get("meaning") or entry.get("analysis") or str(entry)
            definitions.append(
                DictionaryDefinition(
                    definition=str(definition_text),
                    pos=self._extract_pos_from_entry(entry.get("pos") or definition_text),
                    metadata={
                        "lemma": entry.get("headword") or entry.get("lemma"),
                        "dictionary": entry.get("dict_id") or entry.get("dictionary"),
                        "grammar_tags": entry.get("grammar_tags"),
                    },
                )
            )

        morph = data.get("morphology") or combined.get("morphology_analyses")
        if isinstance(morph, dict) and morph.get("analyses"):
            entries.append(
                DictionaryEntry(
                    source="heritage",
                    language=language,
                    word=word,
                    definitions=definitions,
                    morphology=morphology,
                    metadata={"morphology": morph, "combined": combined},
                )
            )
        elif definitions:
            entries.append(
                DictionaryEntry(
                    source="heritage",
                    language=language,
                    word=word,
                    definitions=definitions,
                    morphology=morphology,
                    metadata={"combined": combined},
                )
            )

        return entries
