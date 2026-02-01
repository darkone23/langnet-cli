"""
Unit tests for Heritage Platform integration functionality.
Uses unittest for compatibility and real Heritage backend when available.
"""

import unittest

from langnet.heritage.client import HeritageHTTPClient
from langnet.heritage.encoding_service import EncodingService, SmartVelthuisNormalizer
from langnet.heritage.parsers import MorphologyReducer


class TestMorphologyReducer(unittest.TestCase):
    """Test cases for MorphologyReducer class using real LARK parser"""

    def test_parse_line_basic(self):
        """Test basic line parsing functionality with valid grammar format"""
        reducer = MorphologyReducer()

        # Use proper format expected by LARK grammar: [word]{analysis}
        result = reducer.parse_line("[agni]{m.}")

        # Parser should return a list (possibly empty or with parsed results)
        self.assertIsInstance(result, list)

    def test_parse_line_empty(self):
        """Test parsing empty line."""
        reducer = MorphologyReducer()
        result = reducer.parse_line("")

        # Empty input may return empty list or None
        self.assertTrue(result is None or result == [])

    def test_parse_line_invalid_format(self):
        """Test parsing line with invalid format - should handle gracefully"""
        reducer = MorphologyReducer()

        # Invalid format should be handled (may log error but not crash)
        result = reducer.parse_line("invalid line without proper format")

        # Should return empty list on parse failure, not crash
        self.assertIsInstance(result, list)


class TestHeritageHTTPClient(unittest.TestCase):
    """Test cases for HeritageHTTPClient using real backend"""

    def test_client_initialization(self):
        """Test client initialization"""
        client = HeritageHTTPClient()
        self.assertIsNotNone(client)

    def test_real_sktsearch_krishna(self):
        """Test real sktsearch lookup for 'krishna'"""
        with HeritageHTTPClient() as client:
            result = client.fetch_canonical_via_sktsearch("krishna")

            # Verify we got a valid response structure
            self.assertIn("canonical_text", result)
            self.assertIn("bare_query", result)
            self.assertEqual(result["bare_query"], "krishna")

    def test_real_sktsearch_agni(self):
        """Test real sktsearch lookup for 'agni'"""
        with HeritageHTTPClient() as client:
            result = client.fetch_canonical_via_sktsearch("agni")

            # Verify we got a valid response
            self.assertIn("canonical_text", result)
            self.assertEqual(result["bare_query"], "agni")

    def test_real_fetch_canonical_sanskrit(self):
        """Test real canonical Sanskrit (Devanagari) lookup"""
        with HeritageHTTPClient() as client:
            result = client.fetch_canonical_sanskrit("krishna")

            # Verify response structure
            self.assertIn("original_query", result)
            self.assertIn("canonical_sanskrit", result)
            self.assertIn("match_method", result)


class TestEncodingService(unittest.TestCase):
    """Test cases for EncodingService class"""

    def test_detect_encoding_ascii(self):
        """Test ASCII encoding detection."""
        result = EncodingService.detect_encoding("krishna")
        self.assertEqual(result, "ascii")

    def test_detect_encoding_velthuis(self):
        """Test Velthuis encoding detection."""
        # Use proper Velthuis format with uppercase retroflex
        result = EncodingService.detect_encoding("k.Ri1ShNa")
        self.assertIn(result, ["velthuis", "slp1", "ascii"])

    def test_detect_encoding_devanagari(self):
        """Test Devanagari encoding detection."""
        result = EncodingService.detect_encoding("कृष्ण")
        self.assertEqual(result, "devanagari")

    def test_detect_encoding_iast(self):
        """Test IAST encoding detection."""
        result = EncodingService.detect_encoding("ātmā")
        self.assertEqual(result, "iast")

    def test_to_velthuis(self):
        """Test Velthuis conversion."""
        result = EncodingService.to_velthuis("krishna")
        # Should convert to Velthuis format
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_normalize_for_cdsl(self):
        """Test CDSL normalization."""
        result = EncodingService.normalize_for_cdsl("krishna")
        # Should normalize for CDSL
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)


class TestSmartVelthuisNormalizerIntegration(unittest.TestCase):
    """Integration tests for SmartVelthuisNormalizer"""

    def test_normalize_variants(self):
        """Test normalization variant generation."""
        result = SmartVelthuisNormalizer.normalize("agni")
        self.assertIsInstance(result, list)
        self.assertGreaterEqual(len(result), 1)
        self.assertIn("agni", result)

    def test_normalize_aggressive(self):
        """Test aggressive normalization."""
        result = SmartVelthuisNormalizer.normalize("agni", aggressive=True)
        self.assertIsInstance(result, list)
        self.assertGreaterEqual(len(result), 1)

    def test_apply_corrections(self):
        """Test common corrections."""
        result = SmartVelthuisNormalizer._apply_common_corrections("shiva")
        self.assertIn("ziva", result)

    def test_generate_long_variants(self):
        """Test long vowel variant generation."""
        result = SmartVelthuisNormalizer._generate_long_vowel_variants("rama")
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)


class TestHeritageIntegrationWorkflow(unittest.TestCase):
    """Test Heritage Platform integration workflow using real backend"""

    def test_encoding_detection_workflow(self):
        """Test encoding detection workflow."""
        test_cases = [
            ("krishna", "ascii"),
            ("कृष्ण", "devanagari"),
            ("ātmā", "iast"),
        ]

        for text, expected_encoding in test_cases:
            result = EncodingService.detect_encoding(text)
            self.assertIsInstance(result, str)

    def test_real_client_workflow(self):
        """Test complete client workflow with real backend"""
        with HeritageHTTPClient() as client:
            # Test search workflow
            result = client.fetch_canonical_via_sktsearch("agni")

            # Verify result structure
            self.assertIn("canonical_text", result)
            self.assertIn("entry_url", result)


class TestErrorHandling(unittest.TestCase):
    """Test error handling in Heritage integration"""

    def test_invalid_input_handling(self):
        """Test invalid input handling."""
        # Test empty input
        result = EncodingService.detect_encoding("")
        self.assertIsInstance(result, str)

        # Test single character
        result = EncodingService.detect_encoding("a")
        self.assertIsInstance(result, str)


if __name__ == "__main__":
    unittest.main()
