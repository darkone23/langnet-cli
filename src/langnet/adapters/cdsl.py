from __future__ import annotations

import structlog

from langnet.schema import DictionaryDefinition, DictionaryEntry, MorphologyInfo

from .base import BaseBackendAdapter

logger = structlog.get_logger(__name__)


class CDSLBackendAdapter(BaseBackendAdapter):
    """Adapter for CDSL dictionary responses."""

    def adapt(self, data: dict, language: str, word: str) -> list[DictionaryEntry]:
        entries: list[DictionaryEntry] = []
        dictionaries = data.get("dictionaries", {})

        for dict_name, dict_entries in dictionaries.items():
            if not dict_entries:
                continue

            definitions: list[DictionaryDefinition] = []
            lemma = word
            pos = "unknown"
            features: dict = {}

            for entry in dict_entries:
                definition_text = entry.get("meaning") or entry.get("data") or str(entry)
                entry_pos = self._extract_pos_from_entry(entry.get("pos") or definition_text)
                definitions.append(
                    DictionaryDefinition(
                        definition=str(definition_text),
                        pos=entry_pos,
                        metadata={"dict": dict_name, "id": entry.get("id")},
                    )
                )
                if entry.get("sanskrit_form"):
                    lemma = entry["sanskrit_form"]
                if entry.get("pos"):
                    pos = entry_pos
                grammar = entry.get("grammar_tags") or {}
                if grammar:
                    features.update(grammar)
                if entry.get("gender"):
                    features["gender"] = entry["gender"]

            morphology = MorphologyInfo(
                lemma=lemma,
                pos=pos,
                features=features or {},
                gender=features.get("gender"),
            )

            entries.append(
                DictionaryEntry(
                    source="cdsl",
                    language=language,
                    word=word,
                    definitions=definitions,
                    morphology=morphology,
                    metadata={
                        "dict": dict_name,
                        "dictionary": dict_name,
                        "count": len(dict_entries),
                    },
                )
            )

        # Preserve source visibility even when no entries matched
        # to avoid losing CDSL in unified output
        if not entries:
            canonical_form = data.get("canonical_form") or word
            transliteration = data.get("transliteration")
            entries.append(
                DictionaryEntry(
                    source="cdsl",
                    language=language,
                    word=word,
                    definitions=[
                        DictionaryDefinition(
                            definition="No specific entries found",
                            pos="unknown",
                            metadata={
                                "input_form": data.get("input_form", word),
                                "canonical_form": canonical_form,
                                "dictionaries": dictionaries,
                            },
                        )
                    ],
                    morphology=MorphologyInfo(
                        lemma=canonical_form,
                        pos="unknown",
                        features={},
                    ),
                    metadata={
                        "input_form": data.get("input_form", word),
                        "canonical_form": canonical_form,
                        "dictionaries": dictionaries,
                        **({"transliteration": transliteration} if transliteration else {}),
                    },
                )
            )

        return entries
