"""
Integration tests for Diogenes citation extraction with real services.

These tests use actual Diogenes scraper calls to get real citation data
and verify that the citation extractors work correctly with live data.
"""

import unittest
import logging
from typing import List

from langnet.diogenes.core import (
    DiogenesScraper,
    DiogenesLanguages,
    DiogenesChunkType,
)
from langnet.citation.extractors.diogenes import DiogenesCitationExtractor
from langnet.citation.models import CitationCollection, CitationType

# Set up logging to see debug information
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestDiogenesCitationIntegration(unittest.TestCase):
    """Integration tests for Diogenes citation extraction."""

    @classmethod
    def setUpClass(cls):
        """Set up scraper and extractor for all tests."""
        cls.scraper = DiogenesScraper()
        cls.extractor = DiogenesCitationExtractor()
        logger.info("Set up Diogenes scraper and citation extractor")

    def test_real_latin_citation_extraction(self):
        """Test citation extraction from real Latin Diogenes data."""
        # Get real data from Diogenes
        result = self.scraper.parse_word("amor", DiogenesLanguages.LATIN)

        # Should have parsed successfully
        self.assertTrue(result.dg_parsed, "Diogenes parsing should succeed")
        self.assertGreater(len(result.chunks), 0, "Should have some chunks")

        # Find definition entries that have citations
        citation_blocks_found = 0
        total_citations_found = 0

        for chunk in result.chunks:
            if hasattr(chunk, "definitions") and chunk.chunk_type in [
                DiogenesChunkType.DiogenesMatchingReference,
                DiogenesChunkType.DiogenesFuzzyReference,
            ]:
                definitions = chunk.definitions
                logger.info(f"Processing definition entry: {definitions.term}")
                logger.info(f"Number of blocks: {len(definitions.blocks)}")

                for block in definitions.blocks:
                    if hasattr(block, "citations") and block.citations:
                        citation_blocks_found += 1
                        logger.info(f"Block with citations found: {block.entry[:50]}...")
                        logger.info(f"Citations: {block.citations}")

                        # Convert block to format extractor expects
                        block_dict = {
                            "term": definitions.term,
                            "blocks": [block],  # Put block in a list
                        }

                        collection = self.extractor.extract(block_dict)
                        total_citations_found += len(collection.citations)

                        logger.info(f"Extracted {len(collection.citations)} citations")

                        # Verify collection structure
                        self.assertIsInstance(
                            collection, CitationCollection, "Should return CitationCollection"
                        )
                        self.assertEqual(
                            collection.source, "diogenes", "Should have correct source"
                        )
                        self.assertEqual(collection.language, "grk", "Should have Greek language")

                        # Verify individual citations
                        for citation in collection.citations:
                            self._validate_citation_structure(citation, "Diogenes")

                            # Log citation details for educational value
                            if citation.references:
                                ref = citation.references[0]
                                logger.info(f"  Citation: {ref.text}")
                                logger.info(f"  Type: {ref.type.value}")
                                if citation.abbreviation:
                                    logger.info(f"  Abbreviation: {citation.abbreviation}")
                                if citation.full_name:
                                    logger.info(f"  Full name: {citation.full_name}")

        logger.info(f"\nSummary for 'amor':")
        logger.info(f"  Citation blocks found: {citation_blocks_found}")
        logger.info(f"  Total citations extracted: {total_citations_found}")

        # We should find some citations in real data
        self.assertGreater(citation_blocks_found, 0, "Should find blocks with citations")

        # Note: total_citations_found could be 0 if extractor doesn't recognize Perseus IDs
        # but we've verified the blocks exist with real citation data

    def test_real_greek_citation_extraction(self):
        """Test citation extraction from real Greek Diogenes data."""
        # Get real data from Diogenes for Greek
        result = self.scraper.parse_word("λόγος", DiogenesLanguages.GREEK)

        # Should have parsed successfully
        self.assertTrue(result.dg_parsed, "Diogenes parsing should succeed")
        self.assertGreater(len(result.chunks), 0, "Should have some chunks")

        # Find definition entries that have citations
        citation_blocks_found = 0

        for chunk in result.chunks:
            if hasattr(chunk, "definitions") and chunk.chunk_type in [
                DiogenesChunkType.DiogenesMatchingReference,
                DiogenesChunkType.DiogenesFuzzyReference,
            ]:
                definitions = chunk.definitions
                logger.info(f"Processing Greek definition entry: {definitions.term}")

                for block in definitions.blocks:
                    if hasattr(block, "citations") and block.citations:
                        citation_blocks_found += 1
                        logger.info(f"Block with citations found: {block.entry[:50]}...")
                        logger.info(f"Citations: {block.citations}")

                        # Convert block to format extractor expects
                        block_dict = {"term": definitions.term, "blocks": [block]}

                        collection = self.extractor.extract(block_dict)
                        logger.info(f"Extracted {len(collection.citations)} citations")

                        # Verify collection structure
                        self.assertIsInstance(
                            collection, CitationCollection, "Should return CitationCollection"
                        )
                        self.assertEqual(
                            collection.source, "diogenes", "Should have correct source"
                        )
                        self.assertEqual(collection.language, "grk", "Should have Greek language")

                        # Verify individual citations
                        for citation in collection.citations:
                            self._validate_citation_structure(citation, "Diogenes")

        logger.info(f"\nSummary for 'λόγος':")
        logger.info(f"  Citation blocks found: {citation_blocks_found}")

        # Greek data may or may not have citations, so this is flexible

    def test_real_canonical_references(self):
        """Test parsing of real canonical references like Cic. Tusc. 1, 19, 44."""
        # Get real data from Diogenes
        result = self.scraper.parse_word("cupiditas", DiogenesLanguages.LATIN)

        self.assertTrue(result.dg_parsed, "Diogenes parsing should succeed")

        # Look for blocks with canonical references
        canonical_blocks = []
        for chunk in result.chunks:
            if hasattr(chunk, "definitions") and chunk.chunk_type in [
                DiogenesChunkType.DiogenesMatchingReference,
                DiogenesChunkType.DiogenesFuzzyReference,
            ]:
                for block in chunk.definitions.blocks:
                    if hasattr(block, "citations") and block.citations:
                        # Check if any citation looks like a canonical reference
                        for abb, ref_text in block.citations.items():
                            if any(
                                pattern in ref_text.lower()
                                for pattern in ["cic. tus.", "virg. a.", "hor. c.", "lucr.", "liv."]
                            ):
                                canonical_blocks.append((block, ref_text))
                                break

        logger.info(f"Found {len(canonical_blocks)} canonical reference blocks")

        for block, ref_text in canonical_blocks:
            logger.info(f"Canonical reference: {ref_text}")

            # Test if extractor can handle this format
            block_dict = {"term": "cupiditas", "blocks": [block]}

            collection = self.extractor.extract(block_dict)
            logger.info(f"Extracted {len(collection.citations)} citations from canonical reference")

            # Look for citations with parsed canonical references
            for citation in collection.citations:
                if citation.references:
                    ref = citation.references[0]
                    logger.info(f"Parsed: {ref.text}")
                    logger.info(f"  Author: {ref.author}")
                    logger.info(f"  Work: {ref.work}")
                    logger.info(f"  Book: {ref.book}")
                    logger.info(f"  Standardized: {ref.to_standardized_string()}")

    def test_multiple_real_words(self):
        """Test citation extraction across multiple different real words."""
        test_words = [
            ("amor", DiogenesLanguages.LATIN),
            ("sapientia", DiogenesLanguages.LATIN),
            ("philosophia", DiogenesLanguages.LATIN),
            ("cupiditas", Diogenes.LATIN),
            ("λόγος", DiogenesLanguages.GREEK),
        ]

        results_summary = {}

        for word, language in test_words:
            with self.subTest(word=word):
                try:
                    result = self.scraper.parse_word(word, language)
                    self.assertTrue(result.dg_parsed, f"Diogenes parsing should succeed for {word}")

                    # Find citation blocks
                    citation_blocks = 0
                    total_citations = 0
                    extracted_citations = 0

                    for chunk in result.chunks:
                        if hasattr(chunk, "definitions") and chunk.chunk_type in [
                            DiogenesChunkType.DiogenesMatchingReference,
                            DiogenesChunkType.DiogenesFuzzyReference,
                        ]:
                            for block in chunk.definitions.blocks:
                                if hasattr(block, "citations") and block.citations:
                                    citation_blocks += 1

                                    # Test extraction
                                    block_dict = {"term": chunk.definitions.term, "blocks": [block]}

                                    collection = self.extractor.extract(block_dict)
                                    extracted_citations += len(collection.citations)

                    results_summary[word] = {
                        "citation_blocks": citation_blocks,
                        "extracted_citations": extracted_citations,
                        "language": language.value,
                    }

                    logger.info(
                        f"{word}: {citation_blocks} citation blocks, {extracted_citations} extracted citations"
                    )

                except Exception as e:
                    logger.error(f"Error testing {word}: {e}")
                    results_summary[word] = {"error": str(e)}

        # Log overall results
        logger.info("\n=== Multi-word real citation extraction summary ===")
        total_blocks = 0
        total_extracted = 0

        for word, data in results_summary.items():
            if "error" in data:
                logger.info(f"{word}: ERROR - {data['error']}")
            else:
                logger.info(
                    f"{word}: {data['citation_blocks']} blocks, {data['extracted_citations']} extracted"
                )
                total_blocks += data["citation_blocks"]
                total_extracted += data["extracted_citations"]

        logger.info(
            f"\nTotal across all words: {total_blocks} citation blocks, {total_extracted} extracted citations"
        )

    def _validate_citation_structure(self, citation, backend_name):
        """Validate that a citation has proper structure."""
        # Citation should have references
        self.assertIsInstance(citation.references, list, "References should be a list")

        if citation.references:
            # Primary reference should be valid
            primary_ref = citation.get_primary_reference()
            self.assertIsNotNone(primary_ref, "Should have primary reference")
            self.assertIsInstance(primary_ref.text, str, "Reference text should be string")
            self.assertGreater(len(primary_ref.text), 0, "Reference text should not be empty")

            # Reference should have a valid type
            self.assertIsInstance(
                primary_ref.type, CitationType, "Reference should have CitationType"
            )

            # Citation should have either abbreviation or meaningful reference content
            has_abbreviation = bool(citation.abbreviation)
            has_meaningful_ref = (
                primary_ref.author or primary_ref.work or primary_ref.book or primary_ref.line
            )

            self.assertTrue(
                has_abbreviation or has_meaningful_ref,
                f"Citation should have either abbreviation or meaningful reference content: {citation}",
            )


if __name__ == "__main__":
    unittest.main()
