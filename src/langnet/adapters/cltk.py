from __future__ import annotations

import structlog

from langnet.schema import Citation, DictionaryDefinition, DictionaryEntry, MorphologyInfo

from .base import BaseBackendAdapter, DiogenesLanguages

logger = structlog.get_logger(__name__)


class CLTKBackendAdapter(BaseBackendAdapter):
    """Adapter for CLTK morphology and dictionary outputs."""

    def adapt(self, data: dict, language: str, word: str) -> list[DictionaryEntry]:
        entries: list[DictionaryEntry] = []
        if not isinstance(data, dict):
            return entries

        # 1) Sanskrit/other CLTK pipelines may return a "results" list of morphology dicts
        if isinstance(data.get("results"), list):
            for res in data["results"]:
                entries.append(self._adapt_generic_result(res, language, word))
            return [e for e in entries if e]

        # 2) Latin Lewis & Short lookup (headword + dictionary lines)
        if "lewis_1890_lines" in data:
            lines = data.get("lewis_1890_lines") or []
            headword = data.get("headword") or word
            definitions = [
                DictionaryDefinition(
                    definition=line,
                    pos=self._extract_pos_from_entry(line),
                    metadata={"source": "lewis_1890"},
                )
                for line in lines
            ]
            morph_features = {"ipa": data.get("ipa")} if data.get("ipa") else {}
            morphology = MorphologyInfo(
                lemma=headword,
                pos="unknown",
                features=morph_features,
            )
            entries.append(
                DictionaryEntry(
                    source="cltk",
                    language=language,
                    word=word,
                    definitions=definitions,
                    morphology=morphology,
                    metadata=data,
                )
            )
            return entries

        # 3) Greek spaCy morphology result (or similar morphology-only payload)
        if {"lemma", "pos", "morphological_features"} <= data.keys():
            morphology = MorphologyInfo(
                lemma=data.get("lemma") or word,
                pos=data.get("pos") or "unknown",
                features=data.get("morphological_features") or {},
            )
            entries.append(
                DictionaryEntry(
                    source=data.get("source") or ("spacy" if language in {"grc", "grk"} else "cltk"),
                    language=language,
                    word=word,
                    definitions=[],
                    morphology=morphology,
                    metadata=data,
                )
            )
            return entries

        return entries

    def _adapt_generic_result(self, res: dict, language: str, word: str) -> DictionaryEntry:
        headword = res.get("headword") or res.get("canonical_form") or word
        morphology = res.get("morphology") or {}
        morph_info = None
        if isinstance(morphology, dict):
            morph_info = MorphologyInfo(
                lemma=headword,
                pos=morphology.get("pos") or "unknown",
                features=morphology,
            )

        definitions: list[DictionaryDefinition] = []
        for line in res.get("definitions", []):
            definitions.append(
                DictionaryDefinition(
                    definition=line,
                    pos=self._extract_pos_from_entry(line),
                    metadata={"source": "cltk"},
                )
            )

        return DictionaryEntry(
            source="cltk",
            language=language,
            word=word,
            definitions=definitions,
            morphology=morph_info,
            metadata=res,
        )
