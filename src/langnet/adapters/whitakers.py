from __future__ import annotations

import structlog

from langnet.citation.cts_urn import CTSUrnMapper
from langnet.foster.latin import (
    FOSTER_LATIN_CASES,
    FOSTER_LATIN_GENDERS,
    FOSTER_LATIN_MISCELLANEOUS,
    FOSTER_LATIN_NUMBERS,
    FOSTER_LATIN_TENSES,
)
from langnet.schema import Citation, DictionaryDefinition, DictionaryEntry, MorphologyInfo

from .base import BaseBackendAdapter

logger = structlog.get_logger(__name__)


class WhitakersBackendAdapter(BaseBackendAdapter):
    """Adapter for Whitaker's Words backend."""

    def adapt(self, data: dict, language: str, word: str) -> list[DictionaryEntry]:
        entries: list[DictionaryEntry] = []
        results = data.get("results") or data.get("wordlist") or []

        for entry in results:
            if not entry:
                continue
            definitions = self._build_definitions(entry, word)
            morphology = self._build_morphology(entry, word)

            entries.append(
                DictionaryEntry(
                    source="whitakers",
                    language=language,
                    word=word,
                    definitions=definitions,
                    morphology=morphology,
                    metadata=entry,
                )
            )

        return entries

    def _build_definitions(self, entry: dict, word: str) -> list[DictionaryDefinition]:
        definitions: list[DictionaryDefinition] = []
        senses = entry.get("senses", []) or entry.get("meanings", [])

        # Turn each sense string into a DictionaryDefinition
        for sense in senses:
            definitions.append(
                DictionaryDefinition(
                    definition=str(sense).strip(),
                    pos=self._extract_pos_from_entry(entry.get("part_of_speech", sense)),
                    citations=self._convert_citations(entry),
                    metadata={"type": "sense"},
                )
            )

        # If no senses, fall back to codeline/terms as lightweight definitions
        if not definitions:
            codeline = entry.get("codeline") or {}
            if codeline:
                definition_text = codeline.get("term") or word
                definitions.append(
                    DictionaryDefinition(
                        definition=str(definition_text),
                        pos=self._extract_pos_from_entry(codeline.get("pos_code", "")),
                        citations=self._convert_citations(entry),
                        metadata={"type": "codeline"},
                    )
                )

        return definitions

    def _build_morphology(self, entry: dict, word: str):
        foster_codes = self._convert_foster_codes(entry)
        codeline = entry.get("codeline") or {}
        terms = entry.get("terms") or []

        lemma = (
            codeline.get("term")
            or (terms[0].get("term") if terms and isinstance(terms[0], dict) else None)
            or word
        )

        pos = (
            codeline.get("pos_code")
            or codeline.get("pos_form")
            or entry.get("part_of_speech")
            or self._extract_pos_from_entry(str(entry))
        )

        features = {}
        # Pull useful morphology features from term facts and codeline data
        for key in [
            "declension",
            "conjugation",
            "gender",
            "number",
            "case",
            "tense",
            "voice",
            "mood",
            "person",
            "comparison",
        ]:
            if key in codeline:
                features[key] = codeline[key]
        if terms:
            term_data = terms[0]
            if isinstance(term_data, dict):
                for key, value in term_data.items():
                    if key not in features and key != "term":
                        features[key] = value

        return MorphologyInfo(
            lemma=lemma,
            pos=self._extract_pos_from_entry(pos),
            features=features,
            foster_codes=foster_codes if foster_codes else None,
            declension=features.get("declension"),
            conjugation=features.get("conjugation"),
            tense=features.get("tense"),
            mood=features.get("mood"),
            voice=features.get("voice"),
            person=features.get("person"),
            number=features.get("number"),
            case=features.get("case"),
            gender=features.get("gender"),
        )

    def _convert_citations(self, entry: dict) -> list[Citation]:
        citations: list[Citation] = []
        cts_urns = entry.get("cts_urns", [])
        if cts_urns:
            mapper = CTSUrnMapper()
            for urn in cts_urns:
                citation = mapper.convert_to_citation(urn)
                if citation:
                    citations.append(citation)
        return citations

    def _convert_foster_codes(self, entry: dict) -> dict:
        foster_codes = {}
        declensions = entry.get("declension", [])
        if declensions:
            foster_codes["declension"] = self._map_declension_to_foster(declensions)

        verb_data = entry.get("verb_data", {})
        if verb_data:
            foster_codes["conjugation"] = verb_data.get("conjugation")
            foster_codes["tense"] = self._map_code(verb_data.get("tense"), FOSTER_LATIN_TENSES)
            foster_codes["voice"] = verb_data.get("voice")
            foster_codes["number"] = self._map_code(verb_data.get("number"), FOSTER_LATIN_NUMBERS)
            foster_codes["person"] = verb_data.get("person")
            foster_codes["mood"] = verb_data.get("mood")

        noun_data = entry.get("noun_data", {})
        if noun_data:
            foster_codes["gender"] = self._map_code(noun_data.get("gender"), FOSTER_LATIN_GENDERS)
            foster_codes["number"] = self._map_code(noun_data.get("number"), FOSTER_LATIN_NUMBERS)
            foster_codes["case"] = self._map_code(noun_data.get("case"), FOSTER_LATIN_CASES)

        if foster_codes:
            return foster_codes
        return {}

    def _map_declension_to_foster(self, declensions):
        mappings = {
            "1st": "I",
            "2nd": "II",
            "3rd": "III",
            "4th": "IV",
            "5th": "V",
        }
        return mappings.get(str(declensions[0]).strip(), declensions[0] if declensions else None)

    def _map_code(self, code, mapping):
        if code is None:
            return None
        code_str = str(code).strip().lower()
        return mapping.get(code_str, code)
