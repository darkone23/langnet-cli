from __future__ import annotations

import structlog
from langnet.schema import DictionaryDefinition, DictionaryEntry, MorphFeatures, MorphologyInfo

from .base import BaseBackendAdapter

logger = structlog.get_logger(__name__)


class CLTKBackendAdapter(BaseBackendAdapter):
    """Adapter for CLTK morphology and dictionary outputs."""

    def adapt(self, data: dict, language: str, word: str) -> list[DictionaryEntry]:
        entries: list[DictionaryEntry] = []
        if not isinstance(data, dict):
            return entries

        if isinstance(data.get("results"), list):
            entries.extend(
                [
                    entry
                    for entry in (
                        self._adapt_generic_result(res, language, word) for res in data["results"]
                    )
                    if entry
                ]
            )
        elif "lewis_1890_lines" in data:
            lines = data.get("lewis_1890_lines") or []
            unique_lines: list[str] = []
            seen_lines: set[str] = set()
            for line in lines:
                normalized = " ".join(str(line).split())
                if not normalized or normalized in seen_lines:
                    continue
                seen_lines.add(normalized)
                unique_lines.append(line)
            headword = data.get("headword") or word
            definitions = [
                DictionaryDefinition(
                    definition=line,
                    pos=self._extract_pos_from_entry(line),
                    metadata={"source": "lewis_1890"},
                )
                for line in unique_lines
            ]
            morph_features: MorphFeatures = (
                {"ipa": str(data.get("ipa"))} if data.get("ipa") is not None else {}
            )
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
                    metadata={k: v for k, v in data.items() if k != "lewis_1890_lines"},
                )
            )
        elif {"lemma", "pos", "morphological_features"} <= data.keys():
            features = data.get("morphological_features") or {}
            if not features and not (data.get("lemma") or data.get("pos")):
                return entries
            if self._is_plausible_spacy_payload(data, features):
                morphology = MorphologyInfo(
                    lemma=data.get("lemma") or word,
                    pos=data.get("pos") or "unknown",
                    features=features,
                )
                entries.append(
                    DictionaryEntry(
                        source=data.get("source")
                        or ("spacy" if language in {"grc", "grk"} else "cltk"),
                        language=language,
                        word=word,
                        definitions=[],
                        morphology=morphology,
                        metadata=dict(data),
                    )
                )

        return entries

    def _adapt_generic_result(self, res: dict, language: str, word: str) -> DictionaryEntry:
        headword = res.get("headword") or res.get("canonical_form") or word
        morphology_raw = res.get("morphology") or {}
        morph_info = None
        if isinstance(morphology_raw, dict):
            morph_info = MorphologyInfo(
                lemma=headword,
                pos=morphology_raw.get("pos") or "unknown",
                features=self._stringify_features(morphology_raw),
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

    @staticmethod
    def _is_plausible_spacy_payload(data: dict, features: dict) -> bool:
        """Filter obviously noisy spaCy payloads."""
        pos = (data.get("pos") or "").upper()
        if pos in {"X", "PUNCT", "SYM"}:
            return False
        if pos in {"VERB", "AUX"}:
            return any(key in features for key in ("VerbForm", "Mood", "Tense", "Voice"))
        if pos in {"NOUN", "PROPN", "ADJ"}:
            return any(key in features for key in ("Case", "Gender", "Number"))
        # Default: keep if there is at least some morphological signal
        return bool(features)

    @staticmethod
    def _stringify_features(features: dict) -> MorphFeatures:
        clean: MorphFeatures = {}
        for key, value in features.items():
            if value is None:
                continue
            clean[str(key)] = str(value)
        return clean
