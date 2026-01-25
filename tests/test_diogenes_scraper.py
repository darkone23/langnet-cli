import unittest
import time
import logging

from langnet.diogenes.core import (
    DiogenesScraper,
    DiogenesChunkType,
    DiogenesLanguages,
    PerseusMorphology,
    DiogenesDefinitionEntry,
)

logging.getLogger("urllib3.connection").setLevel(logging.ERROR)


class DiogenesWiring:
    def __init__(self):
        self.scraper = DiogenesScraper()


wiring = DiogenesWiring()


class TestDiogenesScraper(unittest.TestCase):
    def test_latin_word_parsing(self):
        result = wiring.scraper.parse_word("lupus", DiogenesLanguages.LATIN)
        self.assertTrue(result.dg_parsed)
        self.assertGreater(len(result.chunks), 0)

    def test_latin_word_returns_matching_reference(self):
        result = wiring.scraper.parse_word("lupus", DiogenesLanguages.LATIN)
        chunk_types = [chunk.chunk_type for chunk in result.chunks]
        self.assertIn(DiogenesChunkType.DiogenesMatchingReference, chunk_types)

    def test_greek_word_parsing(self):
        result = wiring.scraper.parse_word("λόγος", DiogenesLanguages.GREEK)
        self.assertTrue(result.dg_parsed)
        self.assertGreater(len(result.chunks), 0)

    def test_invalid_language_raises_assertion(self):
        with self.assertRaises(AssertionError):
            wiring.scraper.parse_word("test", "invalid_lang")

    def test_latin_word_no_match_header(self):
        result = wiring.scraper.parse_word(
            "xyznonexistentword123", DiogenesLanguages.LATIN
        )
        chunk_types = [chunk.chunk_type for chunk in result.chunks]
        self.assertIn(DiogenesChunkType.NoMatchFoundHeader, chunk_types)

    def test_perseus_header_has_morphology_instance(self):
        result = wiring.scraper.parse_word("lupus", DiogenesLanguages.LATIN)
        header = None
        for chunk in result.chunks:
            if chunk.chunk_type == DiogenesChunkType.PerseusAnalysisHeader:
                header = chunk
                break
        self.assertIsNotNone(header, "Should have a PerseusAnalysisHeader chunk")
        self.assertIsInstance(header.morphology, PerseusMorphology)

    def test_matching_reference_has_definition_instance(self):
        result = wiring.scraper.parse_word("lupus", DiogenesLanguages.LATIN)
        match = None
        for chunk in result.chunks:
            if chunk.chunk_type == DiogenesChunkType.DiogenesMatchingReference:
                match = chunk
                break
        self.assertIsNotNone(match, "Should have a DiogenesMatchingReference chunk")
        self.assertIsInstance(match.definitions, DiogenesDefinitionEntry)
        self.assertIsNotNone(match.reference_id)
        self.assertTrue(match.reference_id.isdigit())

    def test_lupus_has_known_sense(self):
        result = wiring.scraper.parse_word("lupus", DiogenesLanguages.LATIN)
        match = None
        for chunk in result.chunks:
            if chunk.chunk_type == DiogenesChunkType.DiogenesMatchingReference:
                match = chunk
                break
        self.assertIsNotNone(match)
        definitions = match.definitions
        self.assertTrue(len(definitions.blocks) > 0)
        senses = definitions.blocks[0].senses
        self.assertIsNotNone(senses)
        self.assertTrue(len(senses) > 0)
        self.assertTrue(any("wolf" in s.lower() for s in senses))

    def test_perseus_morphology_has_stems(self):
        result = wiring.scraper.parse_word("lupus", DiogenesLanguages.LATIN)
        header = None
        for chunk in result.chunks:
            if chunk.chunk_type == DiogenesChunkType.PerseusAnalysisHeader:
                header = chunk
                break
        self.assertIsNotNone(header)
        self.assertIsInstance(header.morphology, PerseusMorphology)
        self.assertTrue(len(header.morphology.morphs) > 0)
        self.assertTrue(len(header.morphology.morphs[0].stem) > 0)
        self.assertTrue(len(header.morphology.morphs[0].tags) > 0)

    def test_lupus_golden_master(self):
        result = wiring.scraper.parse_word("lupus", DiogenesLanguages.LATIN)
        self.assertTrue(result.dg_parsed)
        self.assertEqual(len(result.chunks), 2)
        header = [
            c
            for c in result.chunks
            if c.chunk_type == DiogenesChunkType.PerseusAnalysisHeader
        ][0]
        self.assertEqual(header.logeion, "https://logeion.uchicago.edu/lupus")
        self.assertIsInstance(header.morphology, PerseusMorphology)
        self.assertEqual(len(header.morphology.morphs), 1)
        self.assertEqual(header.morphology.morphs[0].stem, ["lupus"])
        match = [
            c
            for c in result.chunks
            if c.chunk_type == DiogenesChunkType.DiogenesMatchingReference
        ][0]
        self.assertEqual(match.reference_id, "42690320")
        self.assertEqual(match.definitions.term, "lŭpus")
        self.assertEqual(len(match.definitions.blocks), 16)


if __name__ == "__main__":
    unittest.main()
