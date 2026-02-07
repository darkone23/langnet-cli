"""Comprehensive Heritage Platform integration tests"""

import unittest
from unittest.mock import Mock

from langnet.heritage.dictionary import HeritageDictionaryService

from langnet.classics_toolkit.core import ClassicsToolkit
from langnet.cologne.core import SanskritCologneLexicon
from langnet.diogenes.core import DiogenesScraper
from langnet.engine.core import LanguageEngine, LanguageEngineConfig
from langnet.heritage.morphology import HeritageMorphologyService
from langnet.whitakers_words.core import WhitakersWords


def find_entries_by_source(entries, source):
    """Helper to find all entries from a specific source."""
    return [e for e in entries if e.source == source]


def get_first_entry_by_source(entries, source):
    """Helper to get first entry from a specific source."""
    for entry in entries:
        if entry.source == source:
            return entry
    return None


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
        mock_morphology_result = Mock()
        mock_morphology_result.solutions = [Mock()]
        mock_morphology_result.solutions[0].analyses = [Mock()]
        mock_morphology_result.solutions[0].analyses[0].lemma = "yoga"
        mock_morphology_result.solutions[0].analyses[0].pos = "noun"
        mock_morphology_result.solutions[0].analyses[0].word = "yoga"

        mock_dict_result = {
            "word": "yoga",
            "entries": [{"meaning": "union"}],
            "transliteration": {"devanagari": "योग"},
        }

        self.mock_heritage_morphology.analyze_word.return_value = mock_morphology_result
        self.mock_heritage_dictionary.lookup_word.return_value = mock_dict_result

        self.mock_cdsl.lookup_ascii.return_value = {
            "dictionary": "mw",
            "dictionaries": {"mw": [{"meaning": "union"}]},
            "transliteration": {"devanagari": "योग"},
        }

        entries = self.engine.handle_query("san", "yoga")

        self.mock_heritage_morphology.analyze_word.assert_called_once_with("yoga")
        self.mock_heritage_dictionary.lookup_word.assert_called_once_with("yoga")

        self.assertIsInstance(entries, list)
        self.assertGreater(len(entries), 0, "Should have entries")

    def test_sanskrit_query_fallback_to_cdsl(self):
        """Test that Sanskrit queries fall back to CDSL when Heritage fails"""
        self.mock_heritage_morphology.analyze_word.side_effect = Exception("Heritage failed")

        self.mock_cdsl.lookup_ascii.return_value = {
            "dictionary": "mw",
            "dictionaries": {"mw": [{"meaning": "union"}]},
            "transliteration": {"devanagari": "योग"},
        }

        entries = self.engine.handle_query("san", "yoga")

        self.mock_heritage_morphology.analyze_word.assert_called_once_with("yoga")

        sources = [e.source for e in entries]
        self.assertIn("cdsl", sources, "Should have cdsl entries for fallback")

        cdsl_entry = get_first_entry_by_source(entries, "cdsl")
        self.assertIsNotNone(cdsl_entry, "Should have cdsl entry")

    def test_sanskrit_query_without_heritage_services(self):
        """Test Sanskrit queries work without Heritage services"""
        config_no_heritage = LanguageEngineConfig(
            scraper=self.mock_scraper,
            whitakers=self.mock_whitakers,
            cltk=self.mock_cltk,
            cdsl=self.mock_cdsl,
            heritage_morphology=None,
            heritage_dictionary=None,
        )
        engine_no_heritage = LanguageEngine(config_no_heritage)

        self.mock_cdsl.lookup_ascii.return_value = {
            "dictionaries": {"mw": [{"meaning": "union"}]},
            "transliteration": {"devanagari": "योग"},
        }

        entries = engine_no_heritage.handle_query("san", "yoga")

        sources = [e.source for e in entries]
        self.assertIn("cdsl", sources, "Should have cdsl entries")
        self.assertNotIn("heritage", sources, "Should not have heritage entries")

    def test_heritage_combined_analysis_creation(self):
        """Test that Heritage creates proper combined analysis"""
        mock_morphology_result = Mock()
        mock_morphology_result.solutions = [Mock()]
        mock_morphology_result.solutions[0].analyses = [
            Mock(lemma="yoga", pos="noun", word="yoga"),
            Mock(lemma="yogin", pos="noun", word="yogin"),
        ]

        mock_dict_result = {
            "word": "yoga",
            "entries": [{"meaning": "union"}],
            "transliteration": {"devanagari": "योग"},
        }

        self.mock_heritage_morphology.analyze_word.return_value = mock_morphology_result
        self.mock_heritage_dictionary.lookup_word.return_value = mock_dict_result

        self.mock_cdsl.lookup_ascii.return_value = {
            "dictionary": "mw",
            "dictionaries": {"mw": [{"meaning": "union"}]},
            "transliteration": {"devanagari": "योग"},
        }

        entries = self.engine.handle_query("san", "yoga")

        self.assertIsInstance(entries, list)
        self.assertGreater(len(entries), 0, "Should have entries")

    def test_heritage_error_handling(self):
        """Test that Heritage errors are handled gracefully"""
        self.mock_heritage_morphology.analyze_word.side_effect = Exception("Network error")

        self.mock_cdsl.lookup_ascii.return_value = {
            "dictionaries": {"mw": [{"meaning": "union"}]},
            "transliteration": {"devanagari": "योग"},
        }

        entries = self.engine.handle_query("san", "yoga")

        heritage_entry = get_first_entry_by_source(entries, "heritage")
        if heritage_entry:
            heritage_data = heritage_entry.metadata
            self.assertIsInstance(heritage_data, dict)
            self.assertIn("error", heritage_data)
            self.assertIn("Network error", heritage_data["error"])

        sources = [e.source for e in entries]
        self.assertIn("cdsl", sources, "CDSL fallback should work")

    def test_heritage_empty_results_handling(self):
        """Test that Heritage empty results are handled gracefully"""
        mock_morphology_result = Mock()
        mock_morphology_result.solutions = []

        self.mock_heritage_morphology.analyze_word.return_value = mock_morphology_result

        self.mock_cdsl.lookup_ascii.return_value = {
            "dictionaries": {"mw": [{"meaning": "union"}]},
            "transliteration": {"devanagari": "योग"},
        }

        entries = self.engine.handle_query("san", "yoga")

        heritage_entry = get_first_entry_by_source(entries, "heritage")
        if heritage_entry:
            heritage_data = heritage_entry.metadata
            self.assertIsInstance(heritage_data, dict)
            self.assertIsNotNone(heritage_data.get("morphology"))

        self.assertEqual(self.mock_heritage_morphology.analyze_word.return_value.solutions, [])

        sources = [e.source for e in entries]
        self.assertIn("cdsl", sources, "CDSL fallback should work")

    def test_heritage_lemma_cdsl_lookup(self):
        """Test that Heritage lemma triggers CDSL lookup"""
        mock_morphology_result = Mock()
        mock_morphology_result.solutions = [Mock()]
        mock_morphology_result.solutions[0].analyses = [Mock()]
        mock_morphology_result.solutions[0].analyses[0].lemma = "asana"
        mock_morphology_result.solutions[0].analyses[0].pos = "noun"

        self.mock_heritage_morphology.analyze_word.return_value = mock_morphology_result

        self.mock_cdsl.lookup_ascii.return_value = {
            "dictionary": "mw",
            "dictionaries": {"mw": [{"meaning": "posture"}]},
            "transliteration": {"devanagari": "असन"},
        }

        entries = self.engine.handle_query("san", "yoga")

        sources = [e.source for e in entries]
        self.assertIn("cdsl", sources, "Should have cdsl entries")

        cdsl_entry = get_first_entry_by_source(entries, "cdsl")
        self.assertIsNotNone(cdsl_entry, "Should have cdsl entry")


if __name__ == "__main__":
    unittest.main()
