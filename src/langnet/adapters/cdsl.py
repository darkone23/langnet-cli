from __future__ import annotations

from typing import cast

import structlog

from langnet.citation.cts_urn import CTSUrnMapper
from langnet.schema import DictionaryDefinition, DictionaryEntry, MorphologyInfo
from langnet.types import JSONValue

from .base import BaseBackendAdapter

logger = structlog.get_logger(__name__)

# Maximum length for tokens considered abbreviations
MAX_ABBREVIATION_LENGTH = 4


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

            definitions, morphology = self._process_dictionary_entries(
                dict_entries, dict_name, language, word
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
            entries.append(self._build_fallback_entry(data, language, word, dictionaries))

        return entries

    def _process_dictionary_entries(
        self,
        dict_entries: list[dict],
        dict_name: str,
        language: str,
        word: str,
    ) -> tuple[list[DictionaryDefinition], MorphologyInfo]:
        """Process all entries for a single dictionary and return definitions and morphology."""
        definitions: list[DictionaryDefinition] = []
        lemma = word
        pos = "unknown"
        features: dict = {}
        foster_codes: dict | list[str] | None = None
        last_reference: dict[str, str] | None = None

        for entry in dict_entries:
            definition_text = entry.get("meaning") or entry.get("data") or str(entry)
            entry_pos = self._extract_pos_from_entry(entry.get("pos") or definition_text)
            references_raw = [r for r in entry.get("references") or [] if isinstance(r, str)]
            reference_details, notes, last_reference = self._parse_references(
                references_raw, language, last_reference
            )
            if not reference_details and last_reference and self._contains_ibid(definition_text):
                # Fallback: detect ibid in definition text even when references are absent.
                resolved = {
                    "abbreviation": "ib.",
                    "display": last_reference.get("display")
                    or last_reference.get("abbreviation")
                    or "ib.",
                }
                reference_details = [resolved]

            definitions.append(
                DictionaryDefinition(
                    definition=str(definition_text),
                    pos=entry_pos,
                    source_ref=self._build_source_ref(dict_name, entry.get("id")),
                    metadata={
                        "dict": dict_name,
                        "id": entry.get("id"),
                        **(
                            {"reference_details": cast(JSONValue, reference_details)}
                            if reference_details
                            else {}
                        ),
                        **({"notes": cast(JSONValue, notes)} if notes else {}),
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
            if entry.get("foster_codes") and foster_codes is None:
                foster_codes = entry.get("foster_codes")

        morphology = MorphologyInfo(
            lemma=lemma,
            pos=pos,
            features=features or {},
            gender=features.get("gender"),
            foster_codes=foster_codes,
        )

        return definitions, morphology

    def _build_fallback_entry(
        self, data: dict, language: str, word: str, dictionaries: dict
    ) -> DictionaryEntry:
        """Build a fallback entry when no dictionary entries are found."""
        canonical_form = data.get("canonical_form") or word
        transliteration = data.get("transliteration")
        return DictionaryEntry(
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

    def _parse_references(
        self, references: list[str], language: str, last_concrete: dict[str, str] | None
    ) -> tuple[list[dict[str, str]], list[str], dict[str, str] | None]:
        """
        Parse reference strings into structured details.

        Returns reference_details, passthrough notes (for plain names), and last_concrete.
        """
        reference_details: list[dict[str, str]] = []
        notes: list[str] = []
        seen_keys: set[tuple[str | None, str | None]] = set()

        for ref in references:
            detail, last_concrete = self._parse_single_reference(ref, last_concrete, language)
            if detail is None:
                if ref:
                    notes.append(ref)
                continue

            key = (detail.get("abbreviation"), detail.get("locator"))
            if key in seen_keys:
                continue
            seen_keys.add(key)
            reference_details.append(detail)

        return reference_details, notes, last_concrete

    def _parse_single_reference(
        self, ref: str, last_concrete: dict[str, str] | None, language: str
    ) -> tuple[dict[str, str] | None, dict[str, str] | None]:
        """Expand a single reference with ibid resolution and AP90-style locator parsing."""
        if not ref or not isinstance(ref, str):
            return None, last_concrete

        text = ref.strip()
        if not text:
            return None, last_concrete

        normalized_ibid = text.lower().replace(".", "").strip()
        if normalized_ibid.startswith("ib"):
            return self._try_resolve_ibid(text, last_concrete)

        source, locator = self._split_source_locator(text)
        meta = self._lookup_reference_metadata(source, text, language)

        if not locator and not meta and not self._looks_like_abbreviation(text):
            # Treat unrecognized names without locators as notes, not references.
            return None, last_concrete

        detail = self._build_reference_detail(source, text, locator, meta)

        # Update ibid anchor when locator present or metadata clearly identifies a source.
        if locator or meta or self._looks_like_abbreviation(text):
            last_concrete = detail

        return detail, last_concrete

    def _try_resolve_ibid(
        self, text: str, last_concrete: dict[str, str] | None
    ) -> tuple[dict[str, str] | None, dict[str, str] | None]:
        """Attempt to resolve an ibid reference to the last concrete reference."""
        _, ibid_locator = self._split_source_locator(text)
        # Resolve ibid to the last concrete reference; drop if none.
        if last_concrete:
            resolved = {**last_concrete}
            # Preserve ibid token as abbreviation, carry display from anchor.
            resolved["abbreviation"] = "ib."
            display_val = last_concrete.get("display") or last_concrete.get("abbreviation")
            if display_val:
                resolved["display"] = display_val
            if ibid_locator:
                resolved["locator"] = ibid_locator
            return resolved, last_concrete
        return None, last_concrete

    def _lookup_reference_metadata(
        self, source: str | None, text: str, language: str
    ) -> dict[str, str] | None:
        """Lookup metadata for a reference if it looks like an abbreviation or has a source."""
        if source or self._looks_like_abbreviation(text):
            return self._cts_mapper.get_abbreviation_metadata(
                citation_id=source or text, citation_text=source or text, language=language
            )
        return None

    def _build_reference_detail(
        self,
        source: str | None,
        text: str,
        locator: str | None,
        meta: dict[str, str] | None,
    ) -> dict[str, str] | None:
        """Build the reference detail dictionary from parsed components.

        Returns None if the reference appears to be a grammatical annotation
        rather than a source citation (e.g., clipped French words like "variante (").
        """
        detail: dict[str, str] = {}
        detail["abbreviation"] = source if source else text

        if locator:
            detail["locator"] = locator

        if meta:
            # Check if long_name looks like a clipped French word (ends with "(", incomplete)
            long_name = meta.get("long_name", "")
            if long_name and (long_name.endswith("(") or long_name.endswith(" ")):
                # This looks like a grammatical annotation, not a source
                return None

            # Add metadata fields except language and long_name (which we handle separately)
            detail.update({k: v for k, v in meta.items() if k not in ("language", "long_name")})
            # Only set display if we have valid metadata with a proper long_name
            # that is different from the abbreviation (i.e., an actual expansion)
            if long_name and long_name != detail["abbreviation"]:
                detail["display"] = long_name
            # Note: long_name is only included when it differs from display
            # This avoids redundancy in the output

        return detail

    @staticmethod
    def _split_source_locator(ref: str) -> tuple[str | None, str | None]:
        """Split a reference string into source abbreviation and locator."""
        cleaned = ref.strip().strip(";")
        if not cleaned:
            return None, None

        digit_match = None
        for idx, char in enumerate(cleaned):
            if char.isdigit():
                digit_match = idx
                break

        if digit_match is None:
            return cleaned.strip(), None

        source = cleaned[:digit_match].rstrip(" ,;")
        locator = cleaned[digit_match:].strip(" .;,")
        locator = locator.replace(" ", "")
        return (source or None), (locator or None)

    @staticmethod
    def _looks_like_abbreviation(text: str) -> bool:
        """Heuristic to detect abbreviation-like tokens."""
        return bool(text and (text.endswith(".") or len(text) <= MAX_ABBREVIATION_LENGTH))

    @staticmethod
    def _looks_like_reference(text: str) -> bool:
        """Heuristic to decide if text could be a reference.

        Checks for digits or abbreviation punctuation like periods or colons.
        """
        return any(ch.isdigit() for ch in text) or "." in text or ":" in text

    @staticmethod
    def _contains_ibid(text: str | None) -> bool:
        if not text:
            return False
        lowered = text.lower()
        return " ib." in lowered or lowered.endswith("ib.") or " ibid" in lowered

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

    @staticmethod
    def _build_source_ref(dict_name: str, entry_id: str | None) -> str | None:
        """Build a stable source reference from dictionary name and entry ID.

        Args:
            dict_name: Dictionary identifier (e.g., "mw", "ap90", "MW", "AP90")
            entry_id: Entry ID from the dictionary (e.g., "890")

        Returns:
            Source reference string (e.g., "mw:890", "ap90:123") or None if entry_id is missing
        """
        if not entry_id:
            return None
        normalized_dict = dict_name.lower()
        return f"{normalized_dict}:{entry_id}"
