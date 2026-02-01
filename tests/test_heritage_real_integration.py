"""Integration tests for Heritage Platform - use real connection when available"""

import time
import unittest
from unittest.mock import Mock

import requests

from langnet.engine.core import LanguageEngine, LanguageEngineConfig
from langnet.heritage.config import HeritageConfig
from langnet.heritage.dictionary import HeritageDictionaryService
from langnet.heritage.morphology import HeritageMorphologyService


def heritage_available():
    """Check if Heritage Platform is available"""
    try:
        config = HeritageConfig()
        response = requests.get(f"{config.base_url}/cgi-bin/skt/sktreader", timeout=5)
        return response.status_code in [200, 404]  # Any response means service is up
    except Exception:
        return False


class TestHeritageRealConnection(unittest.TestCase):
    """Integration tests using real Heritage Platform connection"""

    @classmethod
    def setUpClass(cls):
        """Set up real Heritage services once for all tests"""
        if not heritage_available():
            raise unittest.SkipTest("Heritage Platform not available")

    def setUp(self):
        """Set up engine with real Heritage services"""
        config = HeritageConfig()
        heritage_morphology = HeritageMorphologyService(config)
        heritage_dictionary = HeritageDictionaryService()

        mock_scraper = Mock()
        mock_scraper.parse_word.return_value = None

        mock_whitakers = Mock()
        mock_whitakers.words.return_value = []

        mock_cltk = Mock()
        mock_cltk.latin_query.return_value = None
        mock_cltk.greek_morphology_query.return_value = None
        mock_cltk.spacy_is_available.return_value = False

        mock_cdsl = Mock()
        mock_cdsl.lookup_ascii.return_value = {"dictionaries": {}, "transliteration": {}}

        self.engine = LanguageEngine(
            LanguageEngineConfig(
                scraper=mock_scraper,  # type: ignore
                whitakers=mock_whitakers,  # type: ignore
                cltk=mock_cltk,  # type: ignore
                cdsl=mock_cdsl,  # type: ignore
                heritage_morphology=heritage_morphology,
                heritage_dictionary=heritage_dictionary,
            )
        )

    def test_heritage_morphology_analysis(self):
        """Test real Heritage morphology analysis for 'agni'"""
        result = self.engine._query_sanskrit("agni", self.engine._cattrs_converter)

        self.assertIn("heritage", result)
        heritage = result["heritage"]

        # Check morphology is present
        self.assertIn("morphology", heritage)
        morphology = heritage["morphology"]

        # Verify structure (morphology is a dict after conversion)
        self.assertIn("solutions", morphology)
        self.assertIn("total_solutions", morphology)
        self.assertGreater(morphology["total_solutions"], 0)

    def test_heritage_morphology_yoga(self):
        """Test real Heritage morphology analysis for 'yoga'"""
        result = self.engine._query_sanskrit("yoga", self.engine._cattrs_converter)

        self.assertIn("heritage", result)
        heritage = result["heritage"]
        self.assertIn("morphology", heritage)

        morphology = heritage["morphology"]
        self.assertIn("solutions", morphology)
        self.assertIn("total_solutions", morphology)

    def test_heritage_response_time(self):
        """Test that Heritage responses are returned in reasonable time"""
        start = time.time()
        result = self.engine._query_sanskrit("agni", self.engine._cattrs_converter)
        elapsed = time.time() - start

        # Should complete within 10 seconds
        self.assertLess(elapsed, 10.0)

        # Should have response
        self.assertIn("heritage", result)

    def test_heritage_error_handling_real(self):
        """Test error handling with real Heritage connection"""
        try:
            result = self.engine._query_sanskrit("agni", self.engine._cattrs_converter)
            # If we get here, the result should be a dict
            self.assertIsInstance(result, dict)
            self.assertIn("heritage", result)
        except Exception as e:
            # Connection errors should be handled, not crash
            self.fail(f"Heritage error handling failed: {e}")


class TestHeritageDictionaryRealConnection(unittest.TestCase):
    """Test Heritage dictionary service with real connection"""

    @classmethod
    def setUpClass(cls):
        """Set up real Heritage dictionary service"""
        if not heritage_available():
            raise unittest.SkipTest("Heritage Platform not available")

    def setUp(self):
        """Set up dictionary service"""
        self.dictionary = HeritageDictionaryService()

    def test_dictionary_lookup_agni(self):
        """Test dictionary lookup for 'agni' via Heritage + CDSL"""
        result = self.dictionary.lookup_word("agni")

        self.assertIn("word", result)
        self.assertEqual(result["word"], "agni")
        self.assertIn("entries", result)
        # CDSL should return entries
        self.assertIsInstance(result["entries"], list)

    def test_dictionary_lookup_yoga(self):
        """Test dictionary lookup for 'yoga' via Heritage + CDSL"""
        result = self.dictionary.lookup_word("yoga")

        self.assertIn("word", result)
        self.assertEqual(result["word"], "yoga")
        self.assertIn("entries", result)

    def test_dictionary_transliteration(self):
        """Test that transliteration is returned"""
        result = self.dictionary.lookup_word("agni")

        self.assertIn("transliteration", result)
        self.assertIsInstance(result["transliteration"], dict)


class TestHeritageMorphologyRealConnection(unittest.TestCase):
    """Test Heritage morphology service with real connection"""

    @classmethod
    def setUpClass(cls):
        """Set up real Heritage morphology service"""
        if not heritage_available():
            raise unittest.SkipTest("Heritage Platform not available")

    def setUp(self):
        """Set up morphology service"""
        config = HeritageConfig()
        self.morphology = HeritageMorphologyService(config)

    def test_morphology_analyze_agni(self):
        """Test morphology analysis for 'agni'"""
        result = self.morphology.analyze("agni")

        # Check basic structure (HeritageMorphologyResult is a dataclass)
        self.assertEqual(result.input_text, "agni")
        self.assertIsInstance(result.solutions, list)
        self.assertGreater(result.total_solutions, 0)

    def test_morphology_analyze_word_method(self):
        """Test analyze_word convenience method"""
        result = self.morphology.analyze_word("agni")

        self.assertEqual(result.input_text, "agni")
        self.assertIsInstance(result.solutions, list)

    def test_morphology_processing_time(self):
        """Test that morphology analysis completes in reasonable time"""
        start = time.time()
        result = self.morphology.analyze("agni")
        elapsed = time.time() - start

        # Should complete within 10 seconds
        self.assertLess(elapsed, 10.0)
        # processing_time can be 0.0 for very fast operations - that's OK
        self.assertGreaterEqual(result.processing_time, 0.0)


if __name__ == "__main__":
    unittest.main()
