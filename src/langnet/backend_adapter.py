"""
Backend Adapters for Universal Schema

This module provides adapters that convert raw backend outputs
to standardized DictionaryEntry objects with proper citations.
"""

import structlog
from typing import Any, List

import cattrs

from langnet.schema import Citation, DictionaryEntry, MorphologyInfo, Sense

logger = structlog.get_logger(__name__)


def create_backend_converter() -> cattrs.Converter:
    """Create and configure a cattrs converter for backend data."""
    converter = cattrs.Converter(omit_if_default=True)
    return converter


class BaseBackendAdapter:
    """Base class for backend-specific adapters."""

    def adapt(self, data: dict, language: str, word: str) -> List[DictionaryEntry]:
        """Convert raw backend data to standardized DictionaryEntry objects."""
        raise NotImplementedError

    def _extract_pos_from_entry(self, entry_text: str) -> str:
        """Extract part of speech from entry text like 'lupus, i, m.' or 'λύκος [ῠ], ὁ'."""
        if not entry_text:
            return "unknown"

        # Look for POS indicators in entry text
        entry_text = entry_text.lower()

        # Noun indicators
        if any(
            indicator in entry_text for indicator in ["n", "noun", "m.", "f.", "n.", "substantive"]
        ):
            return "noun"
        # Verb indicators
        if any(indicator in entry_text for indicator in ["v", "verb", "ω"]):
            return "verb"
        # Adjective indicators
        if any(indicator in entry_text for indicator in ["adj", "adjective"]):
            return "adjective"
        # Pronoun indicators
        if any(indicator in entry_text for indicator in ["pron", "pronoun"]):
            return "pronoun"
        # Adverb indicators
        if any(indicator in entry_text for indicator in ["adv", "adverb"]):
            return "adverb"
        # Conjunction indicators
        if any(indicator in entry_text for indicator in ["conj", "conjunction"]):
            return "conjunction"
        # Preposition indicators
        if any(indicator in entry_text for indicator in ["prep", "preposition"]):
            return "preposition"

        return "unknown"

    def _create_citation_from_logeion(self, logeion_url: str) -> Citation:
        """Create a citation from a Diogenes Logeion URL."""
        # Extract citation info from Logeion format like:
        # https://logeion.uchicago.edu/lupus
        # or perseus references: perseus:abo:phi,0690,001:2:63
        if logeion_url.startswith("https://logeion.uchicago.edu/"):
            pass  # Could parse word-specific URL
        elif logeion_url.startswith("perseus:"):
            # Format: perseus:abo:phi,author_id,work:book:line
            parts = logeion_url.split(":")
            if len(parts) >= 3:
                return Citation(
                    url=logeion_url,
                    title=f"Perseus {parts[2]}",
                    page=parts[-1] if len(parts) > 3 else None,
                )

        return Citation(url=logeion_url)

    def _create_citation_from_perseus(self, perseus_ref: str) -> Citation:
        """Create a citation from Perseus reference format."""
        # Expected format: perseus:abo:phi,author_id,work:location
        return Citation(
            url=perseus_ref, title=perseus_ref.split(":")[-1] if ":" in perseus_ref else perseus_ref
        )


class DiogenesBackendAdapter(BaseBackendAdapter):
    """Adapter for Diogenes web scraper."""

    def adapt(self, data: dict, language: str, word: str) -> List[DictionaryEntry]:
        entries = []

        # Diogenes returns chunks with morphology and definitions
        if not data.get("dg_parsed"):
            return entries

        chunks = data.get("chunks", [])
        for chunk in chunks:
            definitions_blocks = chunk.get("definitions", {}).get("blocks", [])

            for block in definitions_blocks:
                # Headword and primary definition
                headword = block.get("entry", "")
                if not headword or "," not in headword:
                    continue

                # Parse definitions
                senses = []
                senses_list = block.get("senses", [])
                citations_list = block.get("citations", {})

                # Extract POS from entry text
                pos = self._extract_pos_from_entry(headword)

                # Assign citations to senses based on proximity in text
                # Citations are stored as {perseus_url: citation_text} mappings
                sense_citations = []
                for i, sense_text in enumerate(senses_list):
                    citations = []

                    # Try to find citations associated with this sense
                    # This is a heuristic approach - citations may not be perfectly mapped
                    for citation_ref, citation_text in citations_list.items():
                        # If citation contains words from this sense, associate it
                        if (
                            citation_text
                            and sense_text
                            and any(
                                word.lower() in citation_text.lower()
                                for word in sense_text.split()[:3]  # First few words
                            )
                        ):
                            citations.append(self._create_citation_from_logeion(citation_ref))

                    sense = Sense(
                        pos=pos,
                        definition=sense_text,
                        citations=citations,
                        examples=[],
                        metadata={"source_block": headword, "sense_index": i},
                    )
                    senses.append(sense)

                entry = DictionaryEntry(
                    word=word,
                    language=language,
                    senses=senses,
                    morphology=None,  # Morphology in separate chunks
                    source="diogenes",
                    metadata=block,
                )
                entries.append(entry)

        # Add morphology entries if we have morphology data
        for chunk in chunks:
            if "morphology" in chunk:
                # Extract lemma and POS from morphology
                morph_data = chunk.get("morphology", {})
                morphs = morph_data.get("morphs", [])
                for morph in morphs:
                    tags = morph.get("tags", [])
                    lemma = morph.get("stem", [""])[0] if morph.get("stem") else word

                    # Convert tags to POS with better mapping
                    pos = "noun"
                    if "V" in tags:
                        pos = "verb"
                    elif any(tag in tags for tag in ["ADJ", "ADJS", "ADJP"]):
                        pos = "adjective"
                    elif any(tag in tags for tag in ["ADV", "ADVB"]):
                        pos = "adverb"
                    elif any(tag in tags for tag in ["PRON", "PRN"]):
                        pos = "pronoun"
                    elif any(tag in tags for tag in ["CONJ", "CNJ"]):
                        pos = "conjunction"
                    elif any(tag in tags for tag in ["PREP", "PREP"]):
                        pos = "preposition"

                    morph_info = MorphologyInfo(
                        lemma=lemma, pos=pos, features={"tags": tags}, confidence=1.0
                    )

                    entry = DictionaryEntry(
                        word=word,
                        language=language,
                        senses=[],  # Morphology-only entry
                        morphology=morph_info,
                        source="diogenes",
                        metadata={"morphology": morph, "logeion": chunk.get("logeion")},
                    )
                    entries.append(entry)

        return entries


class WhitakersBackendAdapter(BaseBackendAdapter):
    """Adapter for Whitaker's Words."""

    def adapt(self, data: dict, language: str, word: str) -> List[DictionaryEntry]:
        entries = []

        # Whitaker's returns wordlist with terms and senses
        wordlist = data.get("wordlist", [])
        for word_data in wordlist:
            senses = []

            # Process senses
            senses_list = word_data.get("senses", [])
            for sense_text in senses_list:
                sense = Sense(
                    pos=word_data.get("part_of_speech", "unknown"),
                    definition=sense_text,
                    citations=[],  # Whitaker's doesn't provide citations
                    examples=[],
                    metadata=word_data,
                )
                senses.append(sense)

            # Extract morphology from terms
            terms = word_data.get("terms", [])
            for term in terms:
                morph_info = MorphologyInfo(
                    lemma=term.get("term_analysis", {}).get("stem", word),
                    pos=term.get("part_of_speech", "unknown"),
                    features={
                        "case": term.get("case"),
                        "number": term.get("number"),
                        "gender": term.get("gender"),
                        "variant": term.get("variant"),
                    },
                    confidence=1.0,
                )

                entry = DictionaryEntry(
                    word=word,
                    language=language,
                    senses=senses if senses else [],  # Attach senses to first morphology entry
                    morphology=morph_info if not senses else None,
                    source="whitakers",
                    metadata=term,
                )
                entries.append(entry)

                # Only attach senses once
                senses = []

        return entries


class CLTKBackendAdapter(BaseBackendAdapter):
    """Adapter for Classical Language Toolkit."""

    def adapt(self, data: dict, language: str, word: str) -> List[DictionaryEntry]:
        entries = []

        # Check if CLTK is enabled
        if data.get("error"):
            return entries

        # CLTK provides headword and lewis_1890_lines (dictionary)
        headword = data.get("headword", "")
        if not headword:
            return entries

        # Parse Lewis & Short lines (if present)
        lewis_lines = data.get("lewis_1890_lines", [])
        senses = []

        for line in lewis_lines:
            if ":" in line:
                definition = line.split(":", 1)[1].strip()
                sense = Sense(
                    pos="unknown",  # CLTK doesn't parse POS reliably
                    definition=definition,
                    citations=[],  # Could extract references from definitions
                    examples=[],
                    metadata={"lewis_line": line},
                )
                senses.append(sense)

        # If no dictionary data, still provide headword info
        if not senses:
            sense = Sense(
                pos="unknown",
                definition=f"Latin headword: {headword}",
                citations=[],
                examples=[],
                metadata=data,
            )
            senses.append(sense)

        entry = DictionaryEntry(
            word=headword,
            language=language,
            senses=senses,
            morphology=None,
            source="cltk",
            metadata=data,
        )
        entries.append(entry)

        return entries


class HeritageBackendAdapter(BaseBackendAdapter):
    """Adapter for Sanskrit Heritage Platform."""

    def adapt(self, data: dict, language: str, word: str) -> List[DictionaryEntry]:
        entries = []

        # Heritage returns morphology and dictionary separately
        morphology_data = data.get("morphology")

        # Convert morphologies to MorphologyInfo
        if morphology_data and "solutions" in morphology_data:
            for solution in morphology_data["solutions"]:
                for analysis in solution.get("analyses", []):
                    morph_info = MorphologyInfo(
                        lemma=analysis.get("lemma", ""),
                        pos=analysis.get("pos", ""),
                        features={},  # Heritage analysis features
                        confidence=analysis.get("confidence", 1.0),
                    )

                    # Combine with dictionary if available
                    senses = []
                    dict_data = data.get("combined", {}) if data.get("combined") else {}
                    if dict_data.get("dictionary_entries"):
                        for dict_entry in dict_data["dictionary_entries"]:
                            sense = Sense(
                                pos=dict_data.get("pos", "unknown"),
                                definition=str(dict_entry),
                                citations=[],  # Would need HTML parsing for citations
                                examples=[],
                                metadata=dict_entry,
                            )
                            senses.append(sense)

                    entry = DictionaryEntry(
                        word=word,
                        language=language,
                        senses=senses,
                        morphology=morph_info if not senses else morph_info,
                        source="heritage",
                        metadata={"analysis": analysis, "combined": dict_data},
                    )
                    entries.append(entry)

        # Convert dictionary entries (if separate)
        if not entries or not any(e.senses for e in entries):
            dictionary_data = data.get("dictionary")
            if dictionary_data and "entries" in dictionary_data:
                for dict_entry in dictionary_data["entries"]:
                    senses = []
                    if isinstance(dict_entry, dict):
                        # Convert dictionary entry to senses
                        if "definitions" in dict_entry:
                            for definition in dict_entry["definitions"]:
                                sense = Sense(
                                    pos=dict_entry.get("pos", "unknown"),
                                    definition=str(definition),
                                    citations=[],  # Extract from dictionary_data if possible
                                    examples=dict_entry.get("examples", []),
                                    metadata=dict_entry,
                                )
                                senses.append(sense)
                        else:
                            sense = Sense(
                                pos=dict_entry.get("pos", "unknown"),
                                definition=str(dict_entry.get("definition", "")),
                                citations=[],  # Extract from dictionary_data if possible
                                examples=dict_entry.get("examples", []),
                                metadata=dict_entry,
                            )
                            senses.append(sense)

                        entry = DictionaryEntry(
                            word=word,
                            language=language,
                            senses=senses,
                            morphology=None,
                            source="heritage",
                            metadata=dictionary_data,
                        )
                        entries.append(entry)

        return entries


class CDSLBackendAdapter(BaseBackendAdapter):
    """Adapter for Sanskrit Cologne Digital Lexicon (MW/Apte dictionaries)."""

    def _convert_citation_collection_to_schema(self, citation_collection) -> list[Citation]:
        """Convert CitationCollection to schema.Citation objects."""
        if not citation_collection:
            return []

        citations = []
        for citation in citation_collection.citations:
            primary_ref = citation.get_primary_reference()
            if primary_ref:
                schema_citation = Citation(
                    url=primary_ref.url,
                    title=citation.abbreviation or primary_ref.work or primary_ref.text,
                    author=citation.author,
                    page=primary_ref.page,
                    excerpt=primary_ref.text,
                )
                citations.append(schema_citation)
        return citations

    def adapt(self, data: dict, language: str, word: str) -> List[DictionaryEntry]:
        entries = []

        # CDSL returns dictionaries MW and Apte
        dictionaries = data.get("dictionaries", {})
        for dict_name, dict_data in dictionaries.items():
            if not dict_data:
                continue

            # Each dictionary has entries with definitions
            for entry_data in dict_data:
                if isinstance(entry_data, dict):
                    senses = []

                    # Extract citations from references if available
                    citations = []
                    references = entry_data.get("references", [])
                    for ref in references:
                        if isinstance(ref, dict):
                            # Handle structured references
                            source = ref.get("source")
                            page_ref = ref.get("page_ref")

                            # If we have nested citations (like from CDSL), extract from the nested structure
                            if "citations" in ref and ref["citations"]:
                                for citation_data in ref["citations"]:
                                    if citation_data.get("references"):
                                        for nested_ref in citation_data["references"]:
                                            citations.append(
                                                Citation(
                                                    title=nested_ref.get("work", source),
                                                    page=page_ref,
                                                    excerpt=nested_ref.get("text", ""),
                                                )
                                            )
                            else:
                                # Handle simple references
                                citations.append(
                                    Citation(
                                        title=source, page=page_ref, excerpt=ref.get("type", "")
                                    )
                                )
                        elif isinstance(ref, str):
                            # Handle string references like "Sūryas."
                            citations.append(Citation(title=str(ref), excerpt=f"Reference: {ref}"))

                    # Create a sense with the entry data
                    sense = Sense(
                        pos=entry_data.get("pos", "unknown"),
                        definition=entry_data.get("meaning", ""),
                        citations=citations,
                        examples=entry_data.get("examples", []),
                        metadata=entry_data,
                    )
                    senses.append(sense)

                    if senses:
                        entry = DictionaryEntry(
                            word=word,
                            language=language,
                            senses=senses,
                            morphology=None,
                            source="cdsl",
                            metadata={"dictionary": dict_name},
                        )
                        entries.append(entry)

        # If no structured data, check for search method info
        if not entries:
            if data.get("error"):
                sense = Sense(
                    pos="unknown",
                    definition=f"Error: {data['error']}",
                    citations=[],
                    examples=[],
                    metadata=data,
                )
            else:
                sense = Sense(
                    pos="unknown",
                    definition=data.get("warning", "No specific entries found"),
                    citations=[],
                    examples=[],
                    metadata=data,
                )

            entry = DictionaryEntry(
                word=word,
                language=language,
                senses=[sense],
                morphology=None,
                source="cdsl",
                metadata=data,
            )
            entries.append(entry)

        return entries


class LanguageAdapterRegistry:
    """Registry of language-specific adapters that compose multiple backends."""

    def __init__(self):
        self.adapters = {
            "grc": GreekAdapter(),
            "lat": LatinAdapter(),
            "san": SanskritAdapter(),
        }

    def get_adapter(self, language: str) -> "BaseLanguageAdapter":
        """Get language adapter for a given language code."""
        if language not in self.adapters:
            raise ValueError(f"No adapter registered for language: {language}")
        return self.adapters[language]


class BaseLanguageAdapter:
    """Base class for language-specific adapters that compose multiple backends."""

    def __init__(self):
        self.backend_adapters = {
            "diogenes": DiogenesBackendAdapter(),
            "whitakers": WhitakersBackendAdapter(),
            "cltk": CLTKBackendAdapter(),
            "heritage": HeritageBackendAdapter(),
            "cdsl": CDSLBackendAdapter(),
        }

    def adapt(self, raw_backends_result: dict, language: str, word: str) -> List[DictionaryEntry]:
        """Compose results from multiple backends into unified DictionaryEntry objects."""
        raise NotImplementedError


class GreekAdapter(BaseLanguageAdapter):
    """Greek language adapter combining Diogenes and CLTK (spacy)."""

    def adapt(self, raw_backends_result: dict, language: str, word: str) -> List[DictionaryEntry]:
        all_entries = []

        # Process Diogenes (primary dictionary source)
        diogenes_data = raw_backends_result.get("diogenes", {})
        if diogenes_data and not diogenes_data.get("error"):
            try:
                diogenes_entries = self.backend_adapters["diogenes"].adapt(
                    diogenes_data, language, word
                )
                all_entries.extend(diogenes_entries)
            except Exception as e:
                logger.warning("diogenes_adaptation_failed", word=word, error=str(e))

        # Process CLTK/spacy (morphology)
        spacy_data = raw_backends_result.get("spacy", {})
        if spacy_data and not spacy_data.get("error"):
            try:
                # Adapt spacy data through CLTK adapter
                cltk_data = {"text": word, **spacy_data}  # CLTK format
                spacy_entries = self.backend_adapters["cltk"].adapt(cltk_data, language, word)
                all_entries.extend(spacy_entries)
            except Exception as e:
                logger.warning("cltk_spacy_adaptation_failed", word=word, error=str(e))

        return all_entries


class LatinAdapter(BaseLanguageAdapter):
    """Latin language adapter combining Diogenes, Whitaker's, and CLTK."""

    def adapt(self, raw_backends_result: dict, language: str, word: str) -> List[DictionaryEntry]:
        all_entries = []

        # Process Whitaker's Words (primary morphological analyzer)
        whitakers_data = raw_backends_result.get("whitakers", {})
        if whitakers_data and not whitakers_data.get("error"):
            try:
                whitakers_entries = self.backend_adapters["whitakers"].adapt(
                    whitakers_data, language, word
                )
                all_entries.extend(whitakers_entries)
            except Exception as e:
                logger.warning("whitakers_adaptation_failed", word=word, error=str(e))

        # Process Diogenes (rich dictionary and citations)
        diogenes_data = raw_backends_result.get("diogenes", {})
        if diogenes_data and not diogenes_data.get("error"):
            try:
                diogenes_entries = self.backend_adapters["diogenes"].adapt(
                    diogenes_data, language, word
                )
                all_entries.extend(diogenes_entries)
            except Exception as e:
                logger.warning("diogenes_adaptation_failed", word=word, error=str(e))

        # Process CLTK (Lewis & Short dictionary)
        cltk_data = raw_backends_result.get("cltk", {})
        if cltk_data and not cltk_data.get("error"):
            try:
                cltk_entries = self.backend_adapters["cltk"].adapt(cltk_data, language, word)
                all_entries.extend(cltk_entries)
            except Exception as e:
                logger.warning("cltk_adaptation_failed", word=word, error=str(e))

        return all_entries


class SanskritAdapter(BaseLanguageAdapter):
    """Sanskrit language adapter combining Heritage Platform and CDSL."""

    def adapt(self, raw_backends_result: dict, language: str, word: str) -> List[DictionaryEntry]:
        all_entries = []

        # Process CDSL dictionaries (Monier-Williams, Apte)
        cdsl_data = raw_backends_result.get("cdsl", {})
        if cdsl_data and not cdsl_data.get("error"):
            try:
                cdsl_entries = self.backend_adapters["cdsl"].adapt(cdsl_data, language, word)
                all_entries.extend(cdsl_entries)
            except Exception as e:
                logger.warning("cdsl_adaptation_failed", word=word, error=str(e))

        # Process Heritage Platform (morphology and dictionary)
        heritage_data = raw_backends_result.get("heritage", {})
        if heritage_data and not heritage_data.get("error"):
            try:
                heritage_entries = self.backend_adapters["heritage"].adapt(
                    heritage_data, language, word
                )
                all_entries.extend(heritage_entries)
            except Exception as e:
                logger.warning("heritage_adaptation_failed", word=word, error=str(e))

        return all_entries
