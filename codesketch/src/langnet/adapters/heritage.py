from __future__ import annotations

import structlog

from langnet.citation.cts_urn import CTSUrnMapper
from langnet.schema import DictionaryDefinition, DictionaryEntry, MorphologyInfo

from .base import BaseBackendAdapter

logger = structlog.get_logger(__name__)


class HeritageBackendAdapter(BaseBackendAdapter):
    """Adapter for Heritage Platform morphology/dictionary responses."""

    def __init__(self):
        self._cts_mapper = CTSUrnMapper()

    def adapt(self, data: dict, language: str, word: str) -> list[DictionaryEntry]:
        entries: list[DictionaryEntry] = []

        combined = (
            data.get("combined_analysis") or data.get("combined") or data.get("dictionary") or {}
        )
        dict_entries = combined.get("dictionary_entries") or combined.get("entries") or []
        canonical_payload = data.get("canonical") or {}
        lemmatize_payload = data.get("lemmatize") or {}

        morphology = self._build_morphology(data.get("morphology"), combined, word)
        definitions = self._build_definitions(dict_entries)

        if morphology or definitions:
            entry_metadata = {}
            if data.get("morphology"):
                entry_metadata["morphology_raw"] = data.get("morphology")
            if combined:
                entry_metadata["combined"] = combined

            entries.append(
                DictionaryEntry(
                    source="heritage",
                    language=language,
                    word=word,
                    definitions=definitions,
                    morphology=morphology,
                    metadata=entry_metadata,
                )
            )

        # Canonical-only or lemmatize-only responses should still produce an entry so callers
        # see the normalized form instead of an empty result.
        if not entries and (canonical_payload or lemmatize_payload):
            lemma = (
                lemmatize_payload.get("lemma")
                or canonical_payload.get("canonical_text")
                or canonical_payload.get("canonical_sanskrit")
                or word
            )
            metadata = {}
            if canonical_payload:
                metadata["canonical"] = canonical_payload
            if lemmatize_payload:
                metadata["lemmatize"] = lemmatize_payload

            entries.append(
                DictionaryEntry(
                    source="heritage",
                    language=language,
                    word=word,
                    definitions=[],
                    morphology=MorphologyInfo(
                        lemma=lemma,
                        pos=self._extract_pos_from_entry(lemmatize_payload.get("grammar", "")),
                        features={"analyses": lemmatize_payload.get("analyses") or []},
                    ),
                    metadata={
                        **metadata,
                        "canonical_form": lemma,
                        "input_form": word,
                    },
                )
            )

        return entries

    def _build_definitions(self, dict_entries: list[dict]) -> list[DictionaryDefinition]:
        definitions: list[DictionaryDefinition] = []
        for entry in dict_entries:
            definition_text = entry.get("meaning") or entry.get("analysis") or str(entry)
            definitions.append(
                DictionaryDefinition(
                    definition=str(definition_text),
                    pos=self._extract_pos_from_entry(entry.get("pos") or definition_text),
                    metadata={
                        "lemma": entry.get("headword") or entry.get("lemma"),
                        "dictionary": entry.get("dict_id") or entry.get("dictionary"),
                        "dict": entry.get("dict_id") or entry.get("dictionary"),
                        "grammar_tags": entry.get("grammar_tags"),
                        **self._build_reference_metadata(entry),
                    },
                )
            )
        return definitions

    def _build_morphology(
        self, morphology_data: dict | None, combined: dict, fallback_word: str
    ) -> MorphologyInfo | None:
        if isinstance(morphology_data, dict):
            solutions = morphology_data.get("solutions") or []
            analyses = []
            if solutions and isinstance(solutions[0], dict):
                analyses = solutions[0].get("analyses") or []
            if morphology_data.get("analyses"):  # legacy shape
                analyses = morphology_data.get("analyses")

            if analyses:
                first = analyses[0] if isinstance(analyses[0], dict) else {}
                lemma = first.get("lemma") or combined.get("lemma") or fallback_word
                pos_hint = (
                    first.get("pos")
                    or first.get("analysis")
                    or combined.get("pos")
                    or fallback_word
                )
                features = {"analyses": analyses}
                encoding = morphology_data.get("encoding")
                if encoding:
                    features["encoding"] = encoding
                foster_codes = first.get("foster_codes")
                return MorphologyInfo(
                    lemma=lemma,
                    pos=self._extract_pos_from_entry(pos_hint),
                    features=features,
                    foster_codes=foster_codes,
                )

        analyses = combined.get("morphology_analyses") if isinstance(combined, dict) else None
        if analyses:
            pos_hint = combined.get("pos") or ""
            lemma = combined.get("lemma") or fallback_word
            return MorphologyInfo(
                lemma=lemma,
                pos=self._extract_pos_from_entry(pos_hint),
                features={"analyses": analyses},
            )

        return None

    def _build_reference_metadata(self, entry: dict) -> dict:
        """Expand Heritage/CSDL-style reference abbreviations for clarity."""
        references = entry.get("references") or []
        if not references:
            return {}

        reference_details = []
        for ref in references:
            if not isinstance(ref, str):
                continue
            meta = self._cts_mapper.get_abbreviation_metadata(
                citation_id=ref, citation_text=ref, language="san"
            )
            if meta:
                reference_details.append({"abbreviation": ref, **meta})
            else:
                reference_details.append({"abbreviation": ref})

        metadata = {"references": references}
        if reference_details:
            metadata["reference_details"] = reference_details
        return metadata
