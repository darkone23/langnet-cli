from __future__ import annotations

import structlog

from langnet.citation.cts_urn import CTSUrnMapper
from langnet.schema import DictionaryDefinition, DictionaryEntry, MorphologyInfo

from .base import BaseBackendAdapter

logger = structlog.get_logger(__name__)


class CDSLBackendAdapter(BaseBackendAdapter):
    """Adapter for CDSL dictionary responses."""

    def __init__(self):
        self._cts_mapper = CTSUrnMapper()

    def adapt(self, data: dict, language: str, word: str) -> list[DictionaryEntry]:
        entries: list[DictionaryEntry] = []
        dictionaries = data.get("dictionaries", {})

        for dict_name, dict_entries in dictionaries.items():
            if not dict_entries:
                continue

            definitions: list[DictionaryDefinition] = []
            all_references: list[str] = []
            lemma = word
            pos = "unknown"
            features: dict = {}

            for entry in dict_entries:
                definition_text = entry.get("meaning") or entry.get("data") or str(entry)
                entry_pos = self._extract_pos_from_entry(entry.get("pos") or definition_text)
                references = self._dedupe_preserve_order(
                    [r for r in entry.get("references") or [] if isinstance(r, str)]
                )
                reference_details = self._expand_references(references, language)
                all_references.extend(references)
                definitions.append(
                    DictionaryDefinition(
                        definition=str(definition_text),
                        pos=entry_pos,
                        metadata={
                            "dict": dict_name,
                            "id": entry.get("id"),
                            **({"references": references} if references else {}),
                            **(
                                {"reference_details": reference_details}
                                if reference_details
                                else {}
                            ),
                        },
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

            unique_references = self._dedupe_preserve_order(all_references)
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
                        **({"references": unique_references} if unique_references else {}),
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

    def _expand_references(
        self, references: list[str], language: str
    ) -> list[dict[str, str | None]]:
        """Expand Heritage-style abbreviations into richer metadata for display."""
        expanded: list[dict[str, str | None]] = []
        if not references:
            return expanded

        for ref in references:
            if not isinstance(ref, str):
                continue
            meta = self._cts_mapper.get_abbreviation_metadata(
                citation_id=ref, citation_text=ref, language=language
            )
            if meta:
                # Drop language marker to keep payload concise; language is on the entry.
                cleaned_meta = {k: v for k, v in meta.items() if k != "language"}
                expanded.append({"abbreviation": ref, **cleaned_meta})
            else:
                expanded.append({"abbreviation": ref})

        return expanded

    @staticmethod
    def _dedupe_preserve_order(items: list[str]) -> list[str]:
        """Remove duplicates while preserving original order."""
        seen = set()
        unique: list[str] = []
        for item in items:
            if item not in seen:
                seen.add(item)
                unique.append(item)
        return unique
