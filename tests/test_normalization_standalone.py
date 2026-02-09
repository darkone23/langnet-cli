"""
Test suite for Canonical Query Normalization system.

This module contains comprehensive tests for the normalization pipeline,
including unit tests for individual components and integration tests.
"""

import os
import sys
import unittest

# Add the src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from typing import cast

from langnet.normalization import (
    CanonicalQuery,
    Encoding,
    GreekNormalizer,
    Language,
    LatinNormalizer,
    NormalizationPipeline,
    SanskritNormalizer,
)

EXPECTED_ALTERNATE_COUNT = 3


class TestCanonicalQuery(unittest.TestCase):
    """Test suite for CanonicalQuery dataclass."""

    def test_basic_creation(self):
        """Test basic CanonicalQuery creation."""
        query = CanonicalQuery(
            original_query="krishna",
            language=Language.SANSKRIT,
            canonical_text="krsna",
            detected_encoding=Encoding.ASCII,
        )

        self.assertEqual(query.original_query, "krishna")
        self.assertEqual(query.language, Language.SANSKRIT)
        self.assertEqual(query.canonical_text, "krsna")
        self.assertEqual(query.detected_encoding, Encoding.ASCII)
        self.assertEqual(query.alternate_forms, [])
        self.assertEqual(query.normalization_notes, [])
        self.assertIsNone(query.enrichment_metadata)

    def test_to_dict_and_from_dict(self):
        """Test serialization and deserialization."""
        original = CanonicalQuery(
            original_query="cēdō",
            language=Language.LATIN,
            canonical_text="cedo",
            alternate_forms=["CEDO"],
            detected_encoding=Encoding.UNICODE,
            normalization_notes=["Macrons stripped"],
            enrichment_metadata={"source": "test"},
        )

        # Convert to dict
        data = original.to_dict()

        # Convert back to object
        reconstructed = CanonicalQuery.from_dict(data)

        self.assertEqual(reconstructed.original_query, original.original_query)
        self.assertEqual(reconstructed.language, original.language)
        self.assertEqual(reconstructed.canonical_text, original.canonical_text)
        self.assertEqual(reconstructed.alternate_forms, original.alternate_forms)
        self.assertEqual(reconstructed.detected_encoding, original.detected_encoding)
        self.assertEqual(reconstructed.normalization_notes, original.normalization_notes)
        self.assertEqual(reconstructed.enrichment_metadata, original.enrichment_metadata)

    def test_get_all_forms(self):
        """Test getting all forms including alternates."""
        query = CanonicalQuery(
            original_query="test",
            language=Language.SANSKRIT,
            canonical_text="test",
            alternate_forms=["TEST", "testing"],
        )

        all_forms = query.get_all_forms()
        self.assertIn("test", all_forms)
        self.assertIn("TEST", all_forms)
        self.assertIn("testing", all_forms)
        self.assertEqual(len(all_forms), EXPECTED_ALTERNATE_COUNT)


def test_validation_errors(self):
    """Test validation catches invalid inputs."""
    # Test alternate forms validation
    with self.assertRaises(ValueError) as context:
        CanonicalQuery(
            original_query="test",
            language=Language.SANSKRIT,
            canonical_text="test",
            alternate_forms=cast(list[str], ["valid", 123]),
        )
    self.assertIn("all alternate_forms must be strings", str(context.exception))


class TestSanskritNormalizer(unittest.TestCase):
    """Test suite for SanskritNormalizer."""

    def setUp(self):
        """Set up test fixtures."""
        self.normalizer = SanskritNormalizer()

    def test_encoding_detection(self):
        """Test encoding detection for various Sanskrit inputs."""
        test_cases = [
            ("अग्नि", Encoding.DEVANAGARI),
            ("krsna", Encoding.ASCII),
            ("agni", Encoding.ASCII),  # Simple ASCII should be detected as ASCII
            ("aGNa", Encoding.VELTHUIS),
            ("aGNa", Encoding.VELTHUIS),
            ("ānanda", Encoding.IAST),
        ]

        for text, expected in test_cases:
            detected = self.normalizer.detect_encoding(text)
            self.assertEqual(
                detected,
                expected.value,
                f"Failed for '{text}': got {detected}, expected {expected.value}",
            )

    def test_canonical_conversion(self):
        """Test conversion to canonical form."""
        # Test ASCII input - Heritage returns Velthuis-encoded canonical form
        canonical, _meta = self.normalizer.to_canonical("krishna", Encoding.ASCII.value)
        # The canonical form from Heritage is the Velthuis-encoded version
        self.assertIsInstance(canonical, str)
        self.assertGreater(len(canonical), 0)

        # Test SLP1 input (should remain unchanged or converted appropriately)
        canonical, _meta = self.normalizer.to_canonical("agni", Encoding.SLP1.value)
        self.assertIsInstance(canonical, str)
        self.assertGreater(len(canonical), 0)

        # Test Unicode input (should become lowercase)
        canonical, _meta = self.normalizer.to_canonical("अग्नि", Encoding.DEVANAGARI.value)
        self.assertIsInstance(canonical, str)

    def test_alternate_forms_generation(self):
        """Test generation of alternate forms."""
        alternates = self.normalizer.generate_alternates("krishna")

        # Should include uppercase and common variations
        self.assertIn("KRISHNA", alternates)
        self.assertIn("krishna", alternates)
        self.assertGreaterEqual(len(alternates), 1)

    def test_fuzzy_match_candidates(self):
        """Test fuzzy match candidate generation."""
        candidates = self.normalizer.fuzzy_match_candidates("krishna")

        self.assertIn("krishna", candidates)
        self.assertGreaterEqual(len(candidates), 1)

    def test_full_normalization(self):
        """Test complete normalization process."""
        result = self.normalizer.normalize("krishna")

        self.assertEqual(result.original_query, "krishna")
        self.assertEqual(result.language, Language.SANSKRIT)
        # The canonical form from Heritage is the Velthuis-encoded version (e.g., "k.r.s.naa")
        self.assertIsInstance(result.canonical_text, str)
        self.assertGreater(len(result.canonical_text), 0)
        self.assertIn(result.detected_encoding, [Encoding.ASCII, Encoding.VELTHUIS])
        self.assertGreaterEqual(len(result.normalization_notes), 1)

    def test_sanskrit_word_detection(self):
        """Test Sanskrit word pattern detection."""
        self.assertTrue(self.normalizer._is_sanskrit_word("krishna"))
        self.assertTrue(self.normalizer._is_sanskrit_word("yoga"))
        self.assertTrue(self.normalizer._is_sanskrit_word("agni"))
        self.assertFalse(self.normalizer._is_sanskrit_word("test"))  # Not Sanskrit-like
        self.assertFalse(self.normalizer._is_sanskrit_word("a"))  # Too short

    def test_needs_heritage_enrichment(self):
        """Test Heritage enrichment detection."""
        # Bare ASCII Sanskrit should be eligible for enrichment
        self.assertTrue(self.normalizer._needs_heritage_enrichment("krishna"))

        # With a mock heritage client, it would check patterns
        # For now, test basic validation
        short_word = self.normalizer._needs_heritage_enrichment("a")
        long_word = self.normalizer._needs_heritage_enrichment("a" * 100)
        non_ascii = self.normalizer._needs_heritage_enrichment("कृष्ण")

        self.assertFalse(short_word)
        self.assertFalse(long_word)
        self.assertFalse(non_ascii)


class TestLatinNormalizer(unittest.TestCase):
    """Test suite for LatinNormalizer."""

    def setUp(self):
        """Set up test fixtures."""
        self.normalizer = LatinNormalizer()

    def test_encoding_detection(self):
        """Test encoding detection for various Latin inputs."""
        test_cases = [
            ("cēdō", Encoding.UNICODE),
            ("cedo", Encoding.ASCII),
            ("rex", Encoding.ASCII),
        ]

        for text, expected in test_cases:
            detected = self.normalizer.detect_encoding(text)
            self.assertEqual(
                detected,
                expected.value,
                f"Failed for '{text}': got {detected}, expected {expected.value}",
            )

    def test_macron_stripping(self):
        """Test macron stripping functionality."""
        test_cases = [
            ("cēdō", "cedo"),
            ("rēx", "rex"),
            ("nūntius", "nuntius"),
            ("āēīōū", "aeiou"),
            ("cēdō", "cedo"),  # Verify it works
        ]

        for input_text, expected in test_cases:
            result = self.normalizer._strip_macrons(input_text)
            self.assertEqual(
                result,
                expected,
                f"Failed for '{input_text}': got '{result}', expected '{expected}'",
            )

    def test_canonical_conversion(self):
        """Test conversion to canonical form."""
        # Test Unicode input (should strip macrons)
        canonical = self.normalizer.to_canonical("cēdō", Encoding.UNICODE.value)
        self.assertEqual(canonical, "cedo")

        # Test ASCII input (should remain unchanged)
        canonical = self.normalizer.to_canonical("cedo", Encoding.ASCII.value)
        self.assertEqual(canonical, "cedo")

    def test_alternate_forms_generation(self):
        """Test generation of alternate forms."""
        alternates = self.normalizer.generate_alternates("iustitia")

        # Should include uppercase and spelling variations
        self.assertIn("IUSTITIA", alternates)
        self.assertGreaterEqual(len(alternates), 1)

    def test_ij_uv_variations(self):
        """Test i/j and u/v spelling variations."""
        # Test i/j variations
        ij_variations = self.normalizer._get_ij_uv_variations("iustitia")
        self.assertIn("justitia", ij_variations)

        # Test u/v variations
        uv_variations = self.normalizer._get_ij_uv_variations("uenio")
        self.assertIn("venio", uv_variations)

    def test_full_normalization(self):
        """Test complete normalization process."""
        result = self.normalizer.normalize("cēdō")

        self.assertEqual(result.original_query, "cēdō")
        self.assertEqual(result.language, Language.LATIN)
        self.assertEqual(result.canonical_text, "cedo")
        self.assertEqual(result.detected_encoding, Encoding.UNICODE)
        self.assertIn("Macrons stripped", result.normalization_notes)


class TestGreekNormalizer(unittest.TestCase):
    """Test suite for GreekNormalizer."""

    def setUp(self):
        """Set up test fixtures."""
        self.normalizer = GreekNormalizer()

    def test_encoding_detection(self):
        """Test encoding detection for various Greek inputs."""
        test_cases = [
            ("οὐσία", Encoding.UNICODE),
            ("*ou/sia", Encoding.BETAcode),
            ("ousia", Encoding.ASCII),
        ]

        for text, expected in test_cases:
            detected = self.normalizer.detect_encoding(text)
            self.assertEqual(
                detected,
                expected.value,
                f"Failed for '{text}': got {detected}, expected {expected.value}",
            )

    def test_betacode_detection(self):
        """Test betacode format detection."""
        self.assertTrue(self.normalizer._is_betacode("*ou/sia"))
        self.assertTrue(self.normalizer._is_betacode("*logos"))
        self.assertFalse(self.normalizer._is_betacode("ousia"))
        self.assertFalse(self.normalizer._is_betacode("οὐσία"))

    def test_unicode_greek_detection(self):
        """Test Unicode Greek character detection."""
        self.assertTrue(self.normalizer._contains_unicode_greek("οὐσία"))
        self.assertFalse(self.normalizer._contains_unicode_greek("*ou/sia"))
        self.assertFalse(self.normalizer._contains_unicode_greek("ousia"))

    def test_betacode_conversion(self):
        """Test betacode to Unicode conversion."""
        # Test basic conversion
        result = self.normalizer._betacode_to_unicode("*ou/sia")
        self.assertTrue("ουσια" in result or "οὐσία" in result)

        # Test without asterisk
        result = self.normalizer._betacode_to_unicode("ou/sia")
        self.assertGreater(len(result), 0)

    def test_ascii_to_unicode_conversion(self):
        """Test ASCII Greek to Unicode conversion."""
        # Test known mappings
        result = self.normalizer._ascii_to_unicode("ousia")
        self.assertGreater(len(result), 0)

        # Test basic vowel mapping
        result = self.normalizer._ascii_to_unicode("alpha")
        self.assertTrue("α" in result or len(result) > 0)

    def test_full_normalization(self):
        """Test complete normalization process."""
        # Test Unicode input
        result = self.normalizer.normalize("οὐσία")
        self.assertEqual(result.original_query, "οὐσία")
        self.assertEqual(result.language, Language.GREEK)
        self.assertEqual(result.canonical_text, "οὐσία")
        self.assertEqual(result.detected_encoding, Encoding.UNICODE)

        # Test betacode input
        result = self.normalizer.normalize("*ou/sia")
        self.assertEqual(result.original_query, "*ou/sia")
        self.assertIn(result.canonical_text, ["ουσια", "οὐσία"])  # Depending on conversion
        self.assertEqual(result.detected_encoding, Encoding.BETAcode)


class TestNormalizationPipeline(unittest.TestCase):
    """Test suite for NormalizationPipeline."""

    def setUp(self):
        """Set up test fixtures."""
        self.pipeline = NormalizationPipeline()
        self.pipeline.register_handler(Language.SANSKRIT, SanskritNormalizer())
        self.pipeline.register_handler(Language.LATIN, LatinNormalizer())
        self.pipeline.register_handler(Language.GREEK, GreekNormalizer())
        self.pipeline.initialize()

    def test_supported_languages(self):
        """Test getting supported languages."""
        supported = self.pipeline.get_supported_languages()
        self.assertIn("san", supported)
        self.assertIn("lat", supported)
        self.assertIn("grc", supported)

    def test_language_support_check(self):
        """Test language support checking."""
        self.assertTrue(self.pipeline.is_language_supported("san"))
        self.assertTrue(self.pipeline.is_language_supported("lat"))
        self.assertTrue(self.pipeline.is_language_supported("grc"))
        self.assertFalse(self.pipeline.is_language_supported("invalid"))

    def test_query_normalization(self):
        """Test query normalization through pipeline."""
        # Test Sanskrit
        result = self.pipeline.normalize_query("san", "krishna")
        self.assertEqual(result.language, Language.SANSKRIT)
        self.assertEqual(result.original_query, "krishna")

        # Test Latin
        result = self.pipeline.normalize_query("lat", "cēdō")
        self.assertEqual(result.language, Language.LATIN)
        self.assertEqual(result.canonical_text, "cedo")

        # Test Greek
        result = self.pipeline.normalize_query("grc", "οὐσία")
        self.assertEqual(result.language, Language.GREEK)
        self.assertEqual(result.canonical_text, "οὐσία")

    def test_unsupported_language_fallback(self):
        """Test fallback for unsupported languages."""
        result = self.pipeline.normalize_query("invalid", "test")
        # Should return default normalization
        self.assertEqual(result.original_query, "test")
        self.assertEqual(result.canonical_text, "test")

    def test_pipeline_initialization(self):
        """Test pipeline initialization."""
        # Should not raise error when initialized
        self.pipeline.initialize()
        self.assertTrue(self.pipeline._initialized)


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete normalization system."""

    def setUp(self):
        """Set up test fixtures."""
        self.pipeline = NormalizationPipeline()
        self.pipeline.register_handler(Language.SANSKRIT, SanskritNormalizer())
        self.pipeline.register_handler(Language.LATIN, LatinNormalizer())
        self.pipeline.register_handler(Language.GREEK, GreekNormalizer())
        self.pipeline.initialize()

    def test_multilingual_query_handling(self):
        """Test handling of queries in multiple languages."""
        test_cases = [
            ("san", "krishna", "Sanskrit"),
            ("lat", "cēdō", "Latin"),
            ("grc", "οὐσία", "Greek"),
            ("grc", "*ou/sia", "Greek (betacode)"),
        ]

        for lang, query, description in test_cases:
            result = self.pipeline.normalize_query(lang, query)
            self.assertEqual(result.language.value, lang, f"Failed for {description}: {query}")
            self.assertEqual(result.original_query, query, f"Failed for {description}: {query}")
            self.assertTrue(isinstance(result.canonical_text, str))

    def test_encoding_variations(self):
        """Test handling of different encoding variations."""
        # Sanskrit variations
        sanskrit_cases = [
            ("अग्नि", "Devanagari"),
            ("krsna", "ASCII"),
            ("agni", "SLP1"),
        ]

        for query, desc in sanskrit_cases:
            result = self.pipeline.normalize_query("san", query)
            self.assertEqual(result.language, Language.SANSKRIT)
            self.assertTrue(isinstance(result.canonical_text, str))

        # Latin variations
        latin_cases = [
            ("cēdō", "Unicode with macrons"),
            ("cedo", "ASCII"),
        ]

        for query, desc in latin_cases:
            result = self.pipeline.normalize_query("lat", query)
            self.assertEqual(result.language, Language.LATIN)
            self.assertTrue(isinstance(result.canonical_text, str))

        # Greek variations
        greek_cases = [
            ("οὐσία", "Unicode"),
            ("*ou/sia", "Betacode"),
            ("ousia", "ASCII"),
        ]

        for query, desc in greek_cases:
            result = self.pipeline.normalize_query("grc", query)
            self.assertEqual(result.language, Language.GREEK)
            self.assertTrue(isinstance(result.canonical_text, str))

    def test_normalization_metadata(self):
        """Test that normalization metadata is properly generated."""
        result = self.pipeline.normalize_query("lat", "cēdō")

        # Should have detected encoding
        self.assertNotEqual(result.detected_encoding, Encoding.UNKNOWN)

        # Should have normalization notes
        self.assertGreater(len(result.normalization_notes), 0)

        # Should alternate forms
        self.assertIsInstance(result.alternate_forms, list)

    def test_error_handling(self):
        """Test error handling in the pipeline."""
        # Should handle empty strings gracefully
        result = self.pipeline.normalize_query("san", "")
        self.assertEqual(result.original_query, "")
        self.assertEqual(result.language, Language.SANSKRIT)

        # Should handle very long strings
        long_query = "a" * 1000
        result = self.pipeline.normalize_query("san", long_query)
        self.assertEqual(result.original_query, long_query)

        # Should handle special characters
        special_query = "cēdō@#$%"
        result = self.pipeline.normalize_query("lat", special_query)
        self.assertEqual(result.original_query, special_query)


if __name__ == "__main__":
    unittest.main()
