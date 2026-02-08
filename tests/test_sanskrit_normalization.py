"""
Unit tests for Sanskrit normalization functionality using unittest.
"""

import unittest

from langnet.heritage.encoding_service import SmartVelthuisNormalizer
from langnet.normalization.models import Language
from langnet.normalization.sanskrit import MAX_SIMPLE_WORD_LENGTH, SanskritNormalizer


class TestSmartVelthuisNormalizer(unittest.TestCase):
    """Test cases for SmartVelthuisNormalizer class"""

    def test_normalize_basic(self):
        """Test basic normalization functionality."""
        normalizer = SmartVelthuisNormalizer

        # Test basic normalization
        result = normalizer.normalize("agni")
        self.assertIsInstance(result, list)
        self.assertIn("agni", result)

    def test_normalize_with_aggressive(self):
        """Test normalization with aggressive mode."""
        normalizer = SmartVelthuisNormalizer

        # Test aggressive normalization
        result = normalizer.normalize("agni", aggressive=True)
        self.assertIsInstance(result, list)
        self.assertGreaterEqual(len(result), 1)

    def test_apply_common_corrections(self):
        """Test common corrections functionality."""
        normalizer = SmartVelthuisNormalizer

        # Test sh -> z correction
        result = normalizer._apply_common_corrections("shiva")
        self.assertIn("ziva", result)

        # Test Sh -> S correction
        result = normalizer._apply_common_corrections("Shiva")
        self.assertIn("Siva", result)

    def test_generate_long_vowel_variants(self):
        """Test long vowel variant generation."""
        normalizer = SmartVelthuisNormalizer

        # Test long vowel generation - check that we get variants
        result = normalizer._generate_long_vowel_variants("rama")
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)


class TestSanskritNormalizer(unittest.TestCase):
    """Test cases for SanskritNormalizer class using real backend"""

    def test_max_simple_word_length(self):
        """Test that MAX_SIMPLE_WORD_LENGTH is properly set"""
        self.assertEqual(MAX_SIMPLE_WORD_LENGTH, 6)

    def test_normalize_krishna_real(self):
        """Test real normalization of 'krishna' using Heritage backend"""
        normalizer = SanskritNormalizer()

        result = normalizer.normalize("krishna")

        self.assertEqual(result.original_query, "krishna")
        self.assertEqual(result.language, Language.SANSKRIT)
        self.assertEqual(result.detected_encoding.value, "ascii")

    def test_normalize_agni_real(self):
        """Test real normalization of 'agni'"""
        normalizer = SanskritNormalizer()

        result = normalizer.normalize("agni")

        self.assertEqual(result.original_query, "agni")
        self.assertEqual(result.language, Language.SANSKRIT)

    def test_normalize_devanagari(self):
        """Test real normalization of Devanagari text"""
        normalizer = SanskritNormalizer()

        result = normalizer.normalize("कृष्ण")

        self.assertEqual(result.original_query, "कृष्ण")
        self.assertEqual(result.language, Language.SANSKRIT)
        self.assertEqual(result.detected_encoding.value, "devanagari")

    def test_canonical_conversion(self):
        """Test canonical form conversion"""
        normalizer = SanskritNormalizer()

        # Test basic conversion
        result = normalizer.to_canonical("krishna", "ascii")

        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_full_normalization(self):
        """Test complete normalization workflow"""
        normalizer = SanskritNormalizer()

        result = normalizer.normalize("agni")

        # Verify complete result structure
        self.assertEqual(result.original_query, "agni")
        self.assertEqual(result.language, Language.SANSKRIT)
        self.assertIsInstance(result.canonical_text, str)
        self.assertIsInstance(result.detected_encoding.value, str)
        self.assertIsInstance(result.alternate_forms, list)


if __name__ == "__main__":
    unittest.main()
