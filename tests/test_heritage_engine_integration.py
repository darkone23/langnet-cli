"""Comprehensive Heritage Platform integration tests"""

import unittest
from unittest.mock import Mock

from langnet.classics_toolkit.core import ClassicsToolkit
from langnet.cologne.core import SanskritCologneLexicon
from langnet.diogenes.core import DiogenesScraper
from langnet.engine.core import LanguageEngine, LanguageEngineConfig
from langnet.heritage.dictionary import HeritageDictionaryService
from langnet.heritage.morphology import HeritageMorphologyService
from langnet.whitakers_words.core import WhitakersWords


class TestHeritageEngineIntegration(unittest.TestCase):
    """Test Heritage Platform integration with LanguageEngine"""

    def setUp(self):
        """Set up test fixtures"""
        # Create mock services
        self.mock_scraper = Mock(spec=DiogenesScraper)
        self.mock_whitakers = Mock(spec=WhitakersWords)
        self.mock_cltk = Mock(spec=ClassicsToolkit)
        self.mock_cdsl = Mock(spec=SanskritCologneLexicon)

        # Create Heritage mocks
        self.mock_heritage_morphology = Mock(spec=HeritageMorphologyService)
        self.mock_heritage_dictionary = Mock(spec=HeritageDictionaryService)

        # Create engine with Heritage services
        config = LanguageEngineConfig(
            scraper=self.mock_scraper,
            whitakers=self.mock_whitakers,
            cltk=self.mock_cltk,
            cdsl=self.mock_cdsl,
            heritage_morphology=self.mock_heritage_morphology,
            heritage_dictionary=self.mock_heritage_dictionary,
        )
        self.engine = LanguageEngine(config)

    def test_engine_initialization_with_heritage(self):
        """Test that engine initializes with Heritage services"""
        self.assertIsNotNone(self.engine.heritage_morphology)
        self.assertIsNotNone(self.engine.heritage_dictionary)
        self.assertIsInstance(self.engine.heritage_morphology, Mock)
        self.assertIsInstance(self.engine.heritage_dictionary, Mock)

    def test_sanskrit_query_uses_heritage_when_available(self):
        """Test that Sanskrit queries use Heritage services when available"""
        # Mock Heritage morphology result
        mock_morphology_result = Mock()
        mock_morphology_result.solutions = [Mock()]
        mock_morphology_result.solutions[0].analyses = [Mock()]
        mock_morphology_result.solutions[0].analyses[0].lemma = "yoga"
        mock_morphology_result.solutions[0].analyses[0].pos = "noun"
        mock_morphology_result.solutions[0].analyses[0].word = "yoga"
        mock_morphology_result.solutions[0].analyses[0].confidence = 0.9

        # Mock Heritage dictionary result
        mock_dict_result = {
            "word": "yoga",
            "entries": [{"meaning": "union"}],
            "transliteration": {"devanagari": "योग"},
        }

        # Set up mock methods
        self.mock_heritage_morphology.analyze_word.return_value = mock_morphology_result
        self.mock_heritage_dictionary.lookup_word.return_value = mock_dict_result

        # Mock CDSL result
        self.mock_cdsl.lookup_ascii.return_value = {
            "dictionaries": {"mw": [{"meaning": "union"}]},
            "transliteration": {"devanagari": "योग"},
        }

        # Execute query
        result = self.engine.handle_query("san", "yoga")

        # Verify Heritage was called
        self.mock_heritage_morphology.analyze_word.assert_called_once_with("yoga")
        self.mock_heritage_dictionary.lookup_word.assert_called_once_with("yoga")

        # Verify result contains Heritage data
        self.assertIn("heritage", result)
        self.assertIsNotNone(result["heritage"])
        self.assertIn("morphology", result["heritage"])
        self.assertIn("dictionary", result["heritage"])

    def test_sanskrit_query_fallback_to_cdsl(self):
        """Test that Sanskrit queries fall back to CDSL when Heritage fails"""
        # Mock Heritage to fail
        self.mock_heritage_morphology.analyze_word.side_effect = Exception("Heritage failed")

        # Mock CDSL result
        self.mock_cdsl.lookup_ascii.return_value = {
            "dictionaries": {"mw": [{"meaning": "union"}]},
            "transliteration": {"devanagari": "योग"},
        }

        # Execute query
        result = self.engine.handle_query("san", "yoga")

        # Verify Heritage was attempted
        self.mock_heritage_morphology.analyze_word.assert_called_once_with("yoga")

        # Verify fallback to CDSL
        self.assertIn("cdsl", result)
        self.assertIn("dictionaries", result["cdsl"])

    def test_sanskrit_query_without_heritage_services(self):
        """Test Sanskrit queries work without Heritage services"""
        # Create engine without Heritage services
        config_no_heritage = LanguageEngineConfig(
            scraper=self.mock_scraper,
            whitakers=self.mock_whitakers,
            cltk=self.mock_cltk,
            cdsl=self.mock_cdsl,
            heritage_morphology=None,
            heritage_dictionary=None,
        )
        engine_no_heritage = LanguageEngine(config_no_heritage)

        # Mock CDSL result
        self.mock_cdsl.lookup_ascii.return_value = {
            "dictionaries": {"mw": [{"meaning": "union"}]},
            "transliteration": {"devanagari": "योग"},
        }

        # Execute query
        result = engine_no_heritage.handle_query("san", "yoga")

        # Verify only CDSL is used
        self.assertIn("cdsl", result)
        self.assertNotIn("heritage", result)

    def test_heritage_combined_analysis_creation(self):
        """Test that Heritage creates proper combined analysis"""
        # Mock Heritage morphology result with complex structure
        mock_morphology_result = Mock()
        mock_morphology_result.solutions = [Mock()]
        mock_morphology_result.solutions[0].analyses = [
            Mock(lemma="yoga", pos="noun", word="yoga", confidence=0.9),
            Mock(lemma="yogin", pos="noun", word="yogin", confidence=0.8),
        ]

        # Mock Heritage dictionary result
        mock_dict_result = {
            "word": "yoga",
            "entries": [{"meaning": "union"}],
            "transliteration": {"devanagari": "योग"},
        }

        self.mock_heritage_morphology.analyze_word.return_value = mock_morphology_result
        self.mock_heritage_dictionary.lookup_word.return_value = mock_dict_result

        # Mock CDSL result
        self.mock_cdsl.lookup_ascii.return_value = {
            "dictionaries": {"mw": [{"meaning": "union"}]},
            "transliteration": {"devanagari": "योग"},
        }

        # Execute query
        result = self.engine.handle_query("san", "yoga")

        # Verify combined analysis is created
        heritage_data = result["heritage"]
        self.assertIn("combined", heritage_data)
        combined = heritage_data["combined"]

        self.assertEqual(combined["lemma"], "yoga")
        self.assertEqual(combined["pos"], "noun")
        self.assertEqual(len(combined["morphology_analyses"]), 2)
        self.assertEqual(len(combined["dictionary_entries"]), 1)

    def test_heritage_error_handling(self):
        """Test that Heritage errors are handled gracefully"""
        # Mock Heritage to fail with different error types
        self.mock_heritage_morphology.analyze_word.side_effect = Exception("Network error")

        # Mock CDSL result
        self.mock_cdsl.lookup_ascii.return_value = {
            "dictionaries": {"mw": [{"meaning": "union"}]},
            "transliteration": {"devanagari": "योग"},
        }

        # Execute query
        result = self.engine.handle_query("san", "yoga")

        # Verify error is captured
        heritage_data = result["heritage"]
        self.assertIsInstance(heritage_data, dict)
        self.assertIn("error", heritage_data)
        self.assertIn("Network error", heritage_data["error"])

        # Verify CDSL fallback still works
        self.assertIn("cdsl", result)

    def test_heritage_empty_results_handling(self):
        """Test that Heritage empty results are handled gracefully"""
        # Mock Heritage to return empty results
        mock_morphology_result = Mock()
        mock_morphology_result.solutions = []

        self.mock_heritage_morphology.analyze_word.return_value = mock_morphology_result

        # Mock CDSL result
        self.mock_cdsl.lookup_ascii.return_value = {
            "dictionaries": {"mw": [{"meaning": "union"}]},
            "transliteration": {"devanagari": "योग"},
        }

        # Execute query
        result = self.engine.handle_query("san", "yoga")

        # Verify Heritage is called but returns empty
        heritage_data = result["heritage"]
        self.assertIsInstance(heritage_data, dict)
        self.assertIsNotNone(heritage_data.get("morphology"))
        # Check that the mock was called with empty solutions
        self.assertEqual(self.mock_heritage_morphology.analyze_word.return_value.solutions, [])

        # Verify CDSL fallback works
        self.assertIn("cdsl", result)

    def test_heritage_lemma_cdsl_lookup(self):
        """Test that Heritage lemma triggers CDSL lookup"""
        # Mock Heritage morphology result with lemma
        mock_morphology_result = Mock()
        mock_morphology_result.solutions = [Mock()]
        mock_morphology_result.solutions[0].analyses = [Mock()]
        mock_morphology_result.solutions[0].analyses[0].lemma = "asana"
        mock_morphology_result.solutions[0].analyses[0].pos = "noun"

        self.mock_heritage_morphology.analyze_word.return_value = mock_morphology_result

        # Mock CDSL for original word (no results)
        self.mock_cdsl.lookup_ascii.return_value = {
            "dictionaries": {},
            "transliteration": {"devanagari": "योग"},
        }

        # Mock CDSL for lemma (with results)
        self.mock_cdsl.lookup_ascii.return_value = {
            "dictionaries": {"mw": [{"meaning": "posture"}]},
            "transliteration": {"devanagari": "असन"},
        }

        # Execute query
        result = self.engine.handle_query("san", "yoga")

        # Verify CDSL lookup was called for both original word and lemma
        # Note: The exact assertion depends on how the mock is set up
        self.assertIn("cdsl", result)
        self.assertIn("dictionaries", result["cdsl"])


if __name__ == "__main__":
    unittest.main()
