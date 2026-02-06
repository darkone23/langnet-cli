"""
Backend Adapters for Universal Schema

This module provides adapters that convert raw backend outputs
to standardized DictionaryEntry objects with proper citations.
"""

import cattrs
import structlog

from langnet.schema import Citation, DictionaryBlock, DictionaryEntry, MorphologyInfo, Sense

logger = structlog.get_logger(__name__)

# Constants for POS indicators
NOUN_INDICATORS = ["n", "noun", "m.", "f.", "n.", "substantive"]
VERB_INDICATORS = ["v", "verb", "ω"]
ADJECTIVE_INDICATORS = ["adj", "adjective"]
PRONOUN_INDICATORS = ["pron", "pronoun"]

# Constants for morphology POS mapping
MORPH_POS_MAPPING = {
    "V": "verb",
    "ADJ": "adjective",
    "ADJS": "adjective",
    "ADJP": "adjective",
    "ADV": "adverb",
    "ADVB": "adverb",
    "PRON": "pronoun",
    "PRN": "pronoun",
    "CONJ": "conjunction",
    "CNJ": "conjunction",
    "PREP": "preposition",
}

# Constants for URL parsing
MIN_URL_PARTS = 3


def create_backend_converter() -> cattrs.Converter:
    """Create and configure a cattrs converter for backend data."""
    converter = cattrs.Converter(omit_if_default=True)
    return converter


class BaseBackendAdapter:
    """Base class for backend-specific adapters."""

    def adapt(self, data: dict, language: str, word: str) -> list[DictionaryEntry]:
        """Convert raw backend data to standardized DictionaryEntry objects."""
        raise NotImplementedError

    def _extract_pos_from_entry(self, entry_text: str) -> str:
        """Extract part of speech from entry text like 'lupus, i, m.' or 'λύκος [ῠ], ὁ'."""
        if not entry_text:
            return "unknown"

        entry_text = entry_text.lower()

        # Define POS indicators
        pos_indicators = {
            "noun": NOUN_INDICATORS,
            "verb": VERB_INDICATORS,
            "adjective": ADJECTIVE_INDICATORS,
            "pronoun": PRONOUN_INDICATORS,
            "adverb": ["adv", "adverb"],
            "conjunction": ["conj", "conjunction"],
            "preposition": ["prep", "preposition"],
        }

        # Check each POS category
        for pos, indicators in pos_indicators.items():
            if any(indicator in entry_text for indicator in indicators):
                return pos

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
            if len(parts) >= MIN_URL_PARTS:
                return Citation(
                    url=logeion_url,
                    title=f"Perseus {parts[2]}",
                    page=parts[-1] if len(parts) > MIN_URL_PARTS else None,
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

    def _has_valid_data(self, chunks: list) -> bool:
        """Check if any chunks contain valid data."""
        for chunk in chunks:
            definitions_blocks = chunk.get("definitions", {}).get("blocks", [])
            if definitions_blocks and len(definitions_blocks) > 0:
                return True
            if "morphology" in chunk:
                morphs = chunk.get("morphology", {}).get("morphs", [])
                if morphs and len(morphs) > 0:
                    return True
        return False

    def _extract_dictionary_blocks(self, chunks: list) -> list[DictionaryBlock]:
        """Extract dictionary blocks from chunks."""
        blocks = []
        for chunk in chunks:
            if "definitions" in chunk:
                definitions_blocks = chunk.get("definitions", {}).get("blocks", [])
                for block in definitions_blocks:
                    blocks.append(
                        DictionaryBlock(
                            entry=block.get("entry", ""),
                            entryid=block.get("entryid", ""),
                            citations=block.get("citations", {}),
                        )
                    )
        return blocks

    def _extract_morphology(self, chunks: list, word: str) -> MorphologyInfo | None:
        """Extract morphology from chunks if present."""
        for chunk in chunks:
            if "morphology" in chunk:
                morph_data = chunk.get("morphology", {})
                morphs = morph_data.get("morphs", [])
                if morphs:
                    morph = morphs[0]
                    tags = morph.get("tags", [])
                    lemma = morph.get("stem", [word])[0] if morph.get("stem") else word
                    pos = self._map_morph_tags_to_pos(tags)
                    return MorphologyInfo(
                        lemma=lemma, pos=pos, features={"tags": tags}, confidence=1.0
                    )
        return None

    def _map_morph_tags_to_pos(self, tags: list) -> str:
        """Map morphology tags to POS."""
        for tag in tags:
            if tag in MORPH_POS_MAPPING:
                return MORPH_POS_MAPPING[tag]
        return "noun"

    def adapt(self, data: dict, language: str, word: str) -> list[DictionaryEntry]:
        """Convert Diogenes data to a single DictionaryEntry with dictionary blocks."""
        if data is None:
            return []

        chunks = data.get("chunks", [])
        if not self._has_valid_data(chunks):
            return []

        # Extract dictionary blocks and morphology
        dictionary_blocks = self._extract_dictionary_blocks(chunks)
        morphology = self._extract_morphology(chunks, word)

        # Create single unified entry
        entry = DictionaryEntry(
            word=word,
            language=language,
            senses=[],  # No sense extraction - use dictionary_blocks instead
            morphology=morphology,
            source="diogenes",
            dictionary_blocks=dictionary_blocks,
            metadata={
                "chunk_types": data.get("chunk_types", []),
                "dg_parsed": data.get("dg_parsed", False),
            },
        )

        return [entry]


class WhitakersBackendAdapter(BaseBackendAdapter):
    """Adapter for Whitaker's Words."""

    def adapt(self, data: dict, language: str, word: str) -> list[DictionaryEntry]:
        entries = []

        # Handle None or invalid input
        if data is None:
            return entries

        # Whitaker's returns wordlist with terms and senses
        wordlist = data.get("wordlist", [])
        for word_data in wordlist:
            # Process senses - deduplicate by definition text
            senses = []
            seen_definitions = set()
            senses_list = word_data.get("senses", [])
            for sense_text in senses_list:
                if sense_text not in seen_definitions:
                    sense = Sense(
                        pos=word_data.get("part_of_speech", "unknown"),
                        definition=sense_text,
                        citations=[],  # Whitaker's doesn't provide citations
                        examples=[],
                        metadata=word_data,
                    )
                    senses.append(sense)
                    seen_definitions.add(sense_text)

            # Extract primary morphology (first term) or None if no terms
            terms = word_data.get("terms", [])
            morphology = None
            if terms:
                first_term = terms[0]
                morphology = MorphologyInfo(
                    lemma=first_term.get("term_analysis", {}).get("stem", word),
                    pos=first_term.get("part_of_speech", "unknown"),
                    features={
                        "case": first_term.get("case"),
                        "number": first_term.get("number"),
                        "gender": first_term.get("gender"),
                        "variant": first_term.get("variant"),
                    },
                    confidence=1.0,
                )

            # Create ONE entry per word_data with all terms in metadata
            entry = DictionaryEntry(
                word=word,
                language=language,
                senses=senses,
                morphology=morphology,
                source="whitakers",
                metadata={
                    "word_data": word_data,  # Include all original data
                    "terms": terms,  # Keep all terms accessible
                },
            )
            entries.append(entry)

        return entries

        # Whitaker's returns wordlist with terms and senses
        wordlist = data.get("wordlist", [])
        for word_data in wordlist:
            # Process senses
            senses = []
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

            # Extract primary morphology (first term) or None if no terms
            terms = word_data.get("terms", [])
            morphology = None
            if terms:
                first_term = terms[0]
                morphology = MorphologyInfo(
                    lemma=first_term.get("term_analysis", {}).get("stem", word),
                    pos=first_term.get("part_of_speech", "unknown"),
                    features={
                        "case": first_term.get("case"),
                        "number": first_term.get("number"),
                        "gender": first_term.get("gender"),
                        "variant": first_term.get("variant"),
                    },
                    confidence=1.0,
                )

            # Create ONE entry per word_data with all terms in metadata
            entry = DictionaryEntry(
                word=word,
                language=language,
                senses=senses,
                morphology=morphology,
                source="whitakers",
                metadata={
                    "word_data": word_data,  # Include all original data
                    "terms": terms,  # Keep all terms accessible
                },
            )
            entries.append(entry)

        return entries


class CLTKBackendAdapter(BaseBackendAdapter):
    """Adapter for Classical Language Toolkit."""

    def adapt(self, data: dict, language: str, word: str) -> list[DictionaryEntry]:
        entries = []

        # Handle None or invalid input
        if data is None:
            return entries

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

    def _has_morphology_data(self, data: dict) -> bool:
        """Check if morphology data exists."""
        if not data:
            return False
        morphology_data = data.get("morphology")
        if not morphology_data:
            return False
        return "solutions" in morphology_data

    def _process_morphology_solutions(
        self, data: dict, language: str, word: str
    ) -> list[DictionaryEntry]:
        """Process morphology solutions and create entries."""
        entries = []
        morphology_data = data.get("morphology")

        if not morphology_data:
            return entries

        # Collect all morphology analyses
        all_analyses = []
        for solution in morphology_data.get("solutions", []):
            for analysis in solution.get("analyses", []):
                all_analyses.append(analysis)

        # Extract senses from combined dictionary data
        senses = self._extract_senses_from_combined(data)

        # Create ONE entry with primary morphology (first analysis) or None
        morphology = None
        if all_analyses:
            first_analysis = all_analyses[0]
            morphology = MorphologyInfo(
                lemma=first_analysis.get("lemma", ""),
                pos=first_analysis.get("pos", ""),
                features={},
                confidence=first_analysis.get("confidence", 1.0),
            )

        entry = DictionaryEntry(
            word=word,
            language=language,
            senses=senses,
            morphology=morphology,
            source="heritage",
            metadata={
                "all_analyses": all_analyses,
                "combined": data.get("combined", {}),
            },
        )
        entries.append(entry)

        return entries

    def _extract_senses_from_combined(self, data: dict) -> list:
        """Extract senses from combined dictionary data."""
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

        return senses

    def _process_dictionary_entries(
        self, data: dict, language: str, word: str
    ) -> list[DictionaryEntry]:
        """Process separate dictionary entries."""
        entries = []
        dictionary_data = data.get("dictionary")

        if dictionary_data and "entries" in dictionary_data:
            for dict_entry in dictionary_data["entries"]:
                senses = self._create_senses_from_entry(dict_entry)
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

    def _create_senses_from_entry(self, dict_entry: dict) -> list:
        """Create senses from a dictionary entry."""
        senses = []

        if isinstance(dict_entry, dict):
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

        return senses

    def adapt(self, data: dict, language: str, word: str) -> list[DictionaryEntry]:
        """Convert Heritage Platform data to DictionaryEntry objects."""
        # Handle None or invalid input
        if data is None:
            return []

        entries = []

        # Process morphology solutions if available
        if self._has_morphology_data(data):
            entries.extend(self._process_morphology_solutions(data, language, word))

        # If no entries with senses, try dictionary entries
        if not entries or not any(e.senses for e in entries):
            entries.extend(self._process_dictionary_entries(data, language, word))

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

    def adapt(self, data: dict, language: str, word: str) -> list[DictionaryEntry]:
        """Convert CDSL data to DictionaryEntry objects."""
        # Handle None or invalid input
        if data is None:
            return []

        entries = []

        # Process dictionary entries
        dictionaries = data.get("dictionaries", {})
        for dict_name, dict_data in dictionaries.items():
            if dict_data:
                entries.extend(
                    self._process_dictionary_entries(dict_data, dict_name, word, language)
                )

        # If no structured data, create fallback entry
        if not entries:
            entries.append(self._create_fallback_entry(data, word, language))

        return entries

    def _process_dictionary_entries(
        self, dict_data: list, dict_name: str, word: str, language: str
    ) -> list[DictionaryEntry]:
        """Process entries from a specific dictionary."""
        entries = []

        # Group entries by dictionary to avoid explosion
        if dict_name in ["mw", "ap90", "apte"]:  # Sanskrit dictionaries that can have many entries
            senses = []
            original_entries = []

            for entry_data in dict_data:
                if isinstance(entry_data, dict):
                    citations = self._extract_citations_from_references(
                        entry_data.get("references", [])
                    )

                    sense = Sense(
                        pos=entry_data.get("pos", "unknown"),
                        definition=entry_data.get("meaning", ""),
                        citations=citations,
                        examples=entry_data.get("examples", []),
                        metadata=entry_data,
                    )
                    senses.append(sense)
                    original_entries.append(
                        {
                            "id": entry_data.get("id"),
                            "meaning": entry_data.get("meaning", ""),
                            "page_ref": entry_data.get("page_ref"),
                        }
                    )

            if senses:
                entry = DictionaryEntry(
                    word=word,
                    language=language,
                    senses=senses,
                    morphology=None,
                    source="cdsl",
                    metadata={
                        "dictionary": dict_name,
                        "original_entry_count": len(original_entries),
                        "original_entries": original_entries,
                    },
                )
                entries.append(entry)
        else:
            # Process other dictionaries normally
            for entry_data in dict_data:
                if isinstance(entry_data, dict):
                    senses = []
                    citations = self._extract_citations_from_references(
                        entry_data.get("references", [])
                    )

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

        return entries

    def _extract_citations_from_references(self, references: list) -> list:
        """Extract citations from reference list."""
        citations = []

        for ref in references:
            if isinstance(ref, dict):
                citations.extend(self._process_dict_reference(ref))
            elif isinstance(ref, str):
                citations.append(Citation(title=str(ref), excerpt=f"Reference: {ref}"))

        return citations

    def _process_dict_reference(self, ref: dict) -> list:
        """Process a dictionary reference and return citations."""
        citations = []
        source = ref.get("source")
        page_ref = ref.get("page_ref")

        # Handle nested citations
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
            citations.append(Citation(title=source, page=page_ref, excerpt=ref.get("type", "")))

        return citations

    def _create_fallback_entry(self, data: dict, word: str, language: str) -> DictionaryEntry:
        """Create a fallback entry when no structured data is available."""
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

        return DictionaryEntry(
            word=word,
            language=language,
            senses=[sense],
            morphology=None,
            source="cdsl",
            metadata=data,
        )


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

    def adapt(self, raw_backends_result: dict, language: str, word: str) -> list[DictionaryEntry]:
        """Compose results from multiple backends into unified DictionaryEntry objects."""
        raise NotImplementedError


class GreekAdapter(BaseLanguageAdapter):
    """Greek language adapter combining Diogenes and CLTK (spacy)."""

    def adapt(self, raw_backends_result: dict, language: str, word: str) -> list[DictionaryEntry]:
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

    def adapt(self, raw_backends_result: dict, language: str, word: str) -> list[DictionaryEntry]:
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

    def adapt(self, raw_backends_result: dict, language: str, word: str) -> list[DictionaryEntry]:
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
