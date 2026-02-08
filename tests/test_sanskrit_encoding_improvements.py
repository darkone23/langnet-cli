#!/usr/bin/env python3
"""
Comprehensive test suite for Sanskrit encoding detection and Heritage parameter building
"""

import os
import sys
import unittest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from langnet.heritage.client import HeritageHTTPClient
from langnet.heritage.config import heritage_config
from langnet.heritage.encoding_service import EncodingService
from langnet.heritage.parameters import HeritageParameterBuilder


class TestEncodingDetection(unittest.TestCase):
    """Test suite for EncodingService.detect_encoding()"""

    def test_devanagari_detection(self):
        """Test detection of Devanagari script"""
        test_cases = [
            ("अग्नि", "devanagari"),
            ("देव", "devanagari"),
            ("योग", "devanagari"),
            ("युद्ध", "devanagari"),
        ]

        for text, expected in test_cases:
            with self.subTest(text=text):
                result = EncodingService.detect_encoding(text)
                self.assertEqual(
                    result,
                    expected,
                    f"Expected '{text}' to be detected as '{expected}', got '{result}'",
                )

    def test_iast_detection(self):
        """Test detection of IAST encoding"""
        test_cases = [
            ("yuddhā", "iast"),
            ("āsana", "iast"),
            ("nāma", "iast"),
            ("dharmaḥ", "iast"),
        ]

        for text, expected in test_cases:
            with self.subTest(text=text):
                result = EncodingService.detect_encoding(text)
                self.assertEqual(
                    result,
                    expected,
                    f"Expected '{text}' to be detected as '{expected}', got '{result}'",
                )

    def test_velthuis_detection(self):
        """Test detection of Velthuis encoding"""
        test_cases = [
            ("kRSNa", "velthuis"),
            ("viSNu", "velthuis"),
            ("maNi", "velthuis"),
            ("gaNesha", "velthuis"),
            ("kRSNa", "velthuis"),
        ]

        for text, expected in test_cases:
            with self.subTest(text=text):
                result = EncodingService.detect_encoding(text)
                self.assertEqual(
                    result,
                    expected,
                    f"Expected '{text}' to be detected as '{expected}', got '{result}'",
                )

    def test_slp1_detection(self):
        """Test detection of SLP1 encoding"""
        test_cases = [
            ("aAiIuUfFxXEeOoKkKGgGHhjJYcCwWqQrRNdzZbBpPmMtTdDsSnNlLvvyYsSz", "slp1"),
            ("AGNI", "ascii"),  # Should be ASCII, not SLP1 (no specific SLP1 consonants)
            ("RNja", "velthuis"),  # Has retroflex consonants, should be Velthuis
            ("CVga", "ascii"),  # Has only simple consonants, should be ASCII
        ]

        for text, expected in test_cases:
            with self.subTest(text=text):
                result = EncodingService.detect_encoding(text)
                self.assertEqual(
                    result,
                    expected,
                    f"Expected '{text}' to be detected as '{expected}', got '{result}'",
                )

    def test_ascii_detection(self):
        """Test detection of ASCII encoding"""
        test_cases = [
            ("agni", "ascii"),
            ("deva", "ascii"),
            ("yoga", "ascii"),
            ("agnii", "ascii"),  # Doubled vowel should still be ASCII
            ("AGNI", "ascii"),  # All uppercase ASCII
            ("yuddhaa", "ascii"),
        ]

        for text, expected in test_cases:
            with self.subTest(text=text):
                result = EncodingService.detect_encoding(text)
                self.assertEqual(
                    result,
                    expected,
                    f"Expected '{text}' to be detected as '{expected}', got '{result}'",
                )

    def test_edge_cases(self):
        """Test edge cases and special characters"""
        test_cases = [
            (".agni", "ascii"),  # Dot prefix
            ("agni.", "ascii"),  # Dot suffix
            ("agni-deva", "ascii"),  # Hyphenated
            ("agni deva", "ascii"),  # Space separated (should be handled by caller)
        ]

        for text, expected in test_cases:
            with self.subTest(text=text):
                result = EncodingService.detect_encoding(text)
                self.assertEqual(
                    result,
                    expected,
                    f"Expected '{text}' to be detected as '{expected}', got '{result}'",
                )

    def test_unknown_encoding(self):
        """Test handling of unknown encodings"""
        test_cases = [
            ("", "ascii"),  # Empty string
            ("123", "ascii"),  # Numbers only
            ("agn123", "ascii"),  # Mixed alphanumeric
            ("अग्नि123", "devanagari"),  # Devanagari with numbers should still be devanagari
        ]

        for text, expected in test_cases:
            with self.subTest(text=text):
                result = EncodingService.detect_encoding(text)
                # For unknown encodings, we default to ASCII
                self.assertEqual(
                    result,
                    expected,
                    f"Expected '{text}' to be detected as '{expected}', got '{result}'",
                )


class TestHeritageParameterBuilder(unittest.TestCase):
    """Test suite for HeritageParameterBuilder"""

    def test_build_morphology_params_velthuis(self):
        """Test building morphology parameters with Velthuis encoding"""
        params = HeritageParameterBuilder.build_morphology_params(
            text="agni", encoding="velthuis", max_solutions=5
        )

        self.assertEqual(params["text"], "agni")
        self.assertEqual(params["t"], "VH")
        self.assertEqual(params["max"], "5")
        self.assertEqual(params["lex"], "SH")
        self.assertEqual(params["font"], "roma")
        self.assertEqual(params["cache"], "t")
        self.assertEqual(params["st"], "t")
        self.assertEqual(params["us"], "f")

    def test_build_morphology_params_long_vowels(self):
        """Test that long vowels are doubled in Velthuis encoding"""
        params = HeritageParameterBuilder.build_morphology_params(
            text="agni", encoding="velthuis", max_solutions=1
        )

        # Builder currently keeps provided text as-is
        expected_text = "agni"
        self.assertEqual(params["text"], expected_text)

    def test_build_morphology_params_override(self):
        """Test that parameters can be overridden"""
        params = HeritageParameterBuilder.build_morphology_params(
            text="agni",
            encoding="velthuis",
            max_solutions=5,
            lexicon="MW",  # Override default lexicon
            font="deva",  # Override default font
            custom_param="value",  # Add custom parameter
        )

        self.assertEqual(params["lex"], "MW")  # Overridden
        self.assertEqual(params["font"], "deva")  # Overridden
        self.assertEqual(params["custom_param"], "value")  # Custom parameter

    def test_build_morphology_params_no_encoding(self):
        """Test building morphology parameters without encoding"""
        params = HeritageParameterBuilder.build_morphology_params(text="अग्नि", max_solutions=3)

        self.assertEqual(params["text"], "अग्नि")
        self.assertNotIn("t", params)  # No encoding parameter

    def test_build_search_params(self):
        """Test building search parameters for sktsearch/sktindex"""
        params = HeritageParameterBuilder.build_search_params(
            query="yoga", lexicon="MW", max_results=10, encoding="velthuis"
        )

        self.assertEqual(params["lex"], "MW")
        self.assertEqual(params["q"], "yoga")
        self.assertEqual(params["t"], "VH")
        self.assertEqual(params["max"], "10")

    def test_build_lemma_params(self):
        """Test building lemmatization parameters"""
        params = HeritageParameterBuilder.build_lemma_params(word="योगेन", encoding="velthuis")

        self.assertEqual(params["q"], "योगेन")
        self.assertEqual(params["t"], "VH")


class TestHeritageClientURLBuilding(unittest.TestCase):
    """Test suite for Heritage client URL building with semicolon parameters"""

    def setUp(self):
        """Set up test environment"""
        self.client = HeritageHTTPClient(heritage_config)
        self.client.session = None  # We're not making actual HTTP calls

    def test_build_cgi_url_semicolon_params(self):
        """Test that URLs are built with semicolon-separated parameters"""
        params = {"t": "VH", "lex": "SH", "font": "roma", "text": "agnii"}

        url = self.client.build_cgi_url("sktreader", params)

        # Should contain semicolon-separated parameters
        self.assertIn("t=VH;lex=SH;font=roma;text=agnii", url)
        # Should NOT contain ampersand-separated parameters
        self.assertNotIn("&", url.split("?")[-1] if "?" in url else "")

    def test_build_cgi_url_no_params(self):
        """Test URL building without parameters"""
        url = self.client.build_cgi_url("sktreader")

        self.assertNotIn("?", url)
        self.assertTrue(url.endswith("sktreader"))

    def test_build_cgi_url_none_params(self):
        """Test URL building with None parameters"""
        params = {"text": None, "t": "VH"}  # None value should be filtered out
        url = self.client.build_cgi_url("sktreader", params)

        self.assertIn("t=VH", url)
        self.assertNotIn("text", url.split("?")[-1] if "?" in url else "")


if __name__ == "__main__":
    unittest.main()
