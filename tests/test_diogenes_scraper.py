import unittest
import time
import logging

from langnet.diogenes.core import DiogenesScraper, DiogenesChunkType, DiogenesLanguages

logging.getLogger("urllib3.connection").setLevel(logging.ERROR)


class DiogenesWiring:
    def __init__(self):
        self.start = time.monotonic()
        print("Setting up diogenes wiring...")
        self.scraper = DiogenesScraper()
        print(f"Startup time took {time.monotonic() - self.start}s")


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


if __name__ == "__main__":
    unittest.main()
