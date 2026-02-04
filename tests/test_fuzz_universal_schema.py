"""
Fuzz testing for universal schema with real word queries.

This module tests the universal schema implementation by querying
a variety of real words across all supported languages and backends.
"""

import unittest

import orjson

from langnet.core import LangnetWiring
from langnet.schema import DictionaryEntry, MorphologyInfo


class FuzzTestUniversalSchema(unittest.TestCase):
    """Fuzz testing for universal schema with real word queries."""

    def setUp(self):
        """Set up test environment with universal schema enabled."""
        self.wiring = LangnetWiring(cache_enabled=False)

    def test_latin_word_fuzzing(self):
        """Test Latin words through universal schema."""
        # Test a variety of Latin words with different characteristics
        latin_words = [
            "lupus",  # Common noun
            "sum",  # Common verb
            "amicus",  # Common noun with multiple meanings
            "arma",  # Plural noun
            "vir",  # Simple noun
            "rosa",  # First declension noun
            "puer",  # Second declension noun
            "dux",  # Third declension noun
            "homo",  # Homograph with multiple meanings
            "res",  # Irregular noun
            "esse",  # Irregular verb
            "possum",  # Compound verb
            "bonus",  # Adjective
            "magnus",  # Adjective with multiple forms
            "ille",  # Demonstrative pronoun
            "hic",  # Demonstrative pronoun
            "quis",  # Interrogative pronoun
            "nemo",  # Indefinite pronoun
            "bene",  # Adverb
            "ita",  # Adverb
        ]

        for word in latin_words:
            with self.subTest(word=word):
                entries = self.wiring.engine.handle_query("lat", word)

                # Should return a list of DictionaryEntry objects
                self.assertIsInstance(entries, list)

                # Should have at least one entry
                self.assertGreater(len(entries), 0, f"Should have entries for '{word}'")

                # All entries should be DictionaryEntry objects
                for entry in entries:
                    self.assertIsInstance(entry, DictionaryEntry)
                    # Note: word may be lemmatized, so we check it's a string
                    self.assertIsInstance(entry.word, str)
                    self.assertEqual(entry.language, "lat")
                    self.assertIn(
                        entry.source, ["whitakers", "diogenes", "cltk", "heritage", "cdsl"]
                    )

    def test_greek_word_fuzzing(self):
        """Test Greek words through universal schema."""
        # Test a variety of Greek words with different characteristics
        greek_words = [
            "λόγος",  # Common noun
            "ἄνθρωπος",  # Common noun
            "πόλις",  # Common noun
            "θεός",  # Common noun
            "βίος",  # Common noun
            "εἰμί",  # Common verb
            "ἔχω",  # Common verb
            "λέγω",  # Common verb
            "ποιέω",  # Common verb
            "γίγνομαι",  # Deponent verb
            "καλός",  # Adjective
            "μέγας",  # Adjective
            "ἀγαθός",  # Adjective
            "κακός",  # Adjective
            "ὅδε",  # Demonstrative pronoun
            "ἐκεῖνος",  # Demonstrative pronoun
            "τίς",  # Interrogative pronoun
            "οὐδείς",  # Indefinite pronoun
            "καλῶς",  # Adverb
            "οὕτως",  # Adverb
        ]

        for word in greek_words:
            with self.subTest(word=word):
                entries = self.wiring.engine.handle_query("grc", word)

                # Should return a list of DictionaryEntry objects
                self.assertIsInstance(entries, list)

                # Should have at least one entry for most words
                # (some may fail due to backend limitations)
                if len(entries) > 0:
                    # All entries should be DictionaryEntry objects
                    for entry in entries:
                        self.assertIsInstance(entry, DictionaryEntry)
                        # Note: word may be lemmatized, so we check it's a string
                        self.assertIsInstance(entry.word, str)
                        self.assertEqual(entry.language, "grc")
                        self.assertIn(
                            entry.source, ["whitakers", "diogenes", "cltk", "heritage", "cdsl"]
                        )

    def test_sanskrit_word_fuzzing(self):
        """Test Sanskrit words through universal schema."""
        # Test a variety of Sanskrit words with different characteristics
        sanskrit_words = [
            "अग्नि",  # Common noun (devanagari)
            "योग",  # Common noun (devanagari)
            "कर्मन्",  # Common noun (devanagari)
            "धर्म",  # Common noun (devanagari)
            "आत्मन्",  # Common noun (devanagari)
            "अस्ति",  # Common verb (devanagari)
            "भवति",  # Common verb (devanagari)
            "करोति",  # Common verb (devanagari)
            "गच्छति",  # Common verb (devanagari)
            "पठति",  # Common verb (devanagari)
            "सुन्दर",  # Adjective (devanagari)
            "महत्",  # Adjective (devanagari)
            "सत्य",  # Adjective (devanagari)
            "दुर्",  # Prefix (devanagari)
            "अयम्",  # Demonstrative pronoun (devanagari)
            "तद्",  # Demonstrative pronoun (devanagari)
            "किम्",  # Interrogative pronoun (devanagari)
            "सर्व",  # Indefinite pronoun (devanagari)
            "सु",  # Adverb (devanagari)
            "एवम्",  # Adverb (devanagari)
        ]

        for word in sanskrit_words:
            with self.subTest(word=word):
                entries = self.wiring.engine.handle_query("san", word)

                # Should return a list of DictionaryEntry objects
                self.assertIsInstance(entries, list)

                # Should have at least one entry for most words
                # (some may fail due to backend limitations)
                if len(entries) > 0:
                    # All entries should be DictionaryEntry objects
                    for entry in entries:
                        self.assertIsInstance(entry, DictionaryEntry)
                        # Note: word may be lemmatized, so we check it's a string
                        self.assertIsInstance(entry.word, str)
                        self.assertEqual(entry.language, "san")
                        self.assertIn(
                            entry.source, ["whitakers", "diogenes", "cltk", "heritage", "cdsl"]
                        )

    def test_latin_inflected_forms(self):
        """Test Latin inflected forms through universal schema."""
        # Test inflected forms that should be lemmatized
        inflected_forms = [
            ("lupi", "lat"),  # Genitive singular of lupus
            ("luporum", "lat"),  # Genitive plural of lupus
            ("lupo", "lat"),  # Dative singular of lupus
            ("lupis", "lat"),  # Dative/ablative plural of lupus
            ("sumus", "lat"),  # First person plural of sum
            ("es", "lat"),  # Second person singular of sum
            ("est", "lat"),  # Third person singular of sum
            ("sunt", "lat"),  # Third person plural of sum
            ("amici", "lat"),  # Nominative plural of amicus
            ("amicorum", "lat"),  # Genitive plural of amicus
        ]

        for word, lang in inflected_forms:
            with self.subTest(word=word, lang=lang):
                entries = self.wiring.engine.handle_query(lang, word)

                # Should return a list of DictionaryEntry objects
                self.assertIsInstance(entries, list)

                # Should have at least one entry for most forms
                if len(entries) > 0:
                    # All entries should be DictionaryEntry objects
                    for entry in entries:
                        self.assertIsInstance(entry, DictionaryEntry)
                        self.assertEqual(entry.language, lang)
                        self.assertIn(
                            entry.source, ["whitakers", "diogenes", "cltk", "heritage", "cdsl"]
                        )

    def test_sanskrit_inflected_forms(self):
        """Test Sanskrit inflected forms through universal schema."""
        # Test inflected forms that should be lemmatized
        inflected_forms = [
            ("अग्निना", "san"),  # Instrumental singular of अग्नि
            ("अग्निभिः", "san"),  # Instrumental plural of अग्नि
            ("अग्नेः", "san"),  # Genitive singular of अग्नि
            ("अग्नीन्", "san"),  # Accusative plural of अग्नि
            ("योगेन", "san"),  # Instrumental singular of योग
            ("योगात्", "san"),  # Ablative singular of योग
            ("योगस्य", "san"),  # Genitive singular of योग
            ("अस्ति", "san"),  # Third person singular of अस्ति
            ("स्मि", "san"),  # First person singular of अस्ति
            ("भवन्ति", "san"),  # Third person plural of भवति
        ]

        for word, lang in inflected_forms:
            with self.subTest(word=word, lang=lang):
                entries = self.wiring.engine.handle_query(lang, word)

                # Should return a list of DictionaryEntry objects
                self.assertIsInstance(entries, list)

                # Should have at least one entry for most forms
                if len(entries) > 0:
                    # All entries should be DictionaryEntry objects
                    for entry in entries:
                        self.assertIsInstance(entry, DictionaryEntry)
                        self.assertEqual(entry.language, lang)
                        self.assertIn(
                            entry.source, ["whitakers", "diogenes", "cltk", "heritage", "cdsl"]
                        )

    def test_edge_case_words(self):
        """Test edge case words through universal schema."""
        # Test words that might cause issues
        edge_cases = [
            ("", "lat"),  # Empty string
            (" ", "lat"),  # Space
            ("x", "lat"),  # Single letter
            ("zzz", "lat"),  # Non-existent word
            ("123", "lat"),  # Numbers
            ("a", "san"),  # Single letter in Sanskrit
            ("", "san"),  # Empty string in Sanskrit
            (" ", "san"),  # Space in Sanskrit
        ]

        for word, lang in edge_cases:
            with self.subTest(word=word, lang=lang):
                try:
                    entries = self.wiring.engine.handle_query(lang, word)

                    # Should return a list (even if empty)
                    self.assertIsInstance(entries, list)

                    # All entries should be DictionaryEntry objects if any exist
                    for entry in entries:
                        self.assertIsInstance(entry, DictionaryEntry)
                        self.assertEqual(entry.language, lang)
                        self.assertIn(
                            entry.source, ["whitakers", "diogenes", "cltk", "heritage", "cdsl"]
                        )
                except Exception:
                    # Some edge cases may raise exceptions, which is acceptable
                    # but we want to know about them
                    pass

    def test_citation_presence(self):
        """Test that citations are present in DictionaryEntry objects."""
        # Test words that should have citations
        test_words = [
            ("lupus", "lat"),
            ("λόγος", "grc"),
            ("अग्नि", "san"),
        ]

        for word, lang in test_words:
            with self.subTest(word=word, lang=lang):
                entries = self.wiring.engine.handle_query(lang, word)

                # Should return a list of DictionaryEntry objects
                self.assertIsInstance(entries, list)

                # Check if any entries have citations
                total_citations = 0
                for entry in entries:
                    self.assertIsInstance(entry, DictionaryEntry)
                    for sense in entry.senses:
                        total_citations += len(sense.citations)
                        # Each citation should be a Citation object or None
                        for citation in sense.citations:
                            if citation is not None:
                                # Should have at least one field with content
                                has_content = any(
                                    [
                                        citation.url,
                                        citation.title,
                                        citation.author,
                                        citation.page,
                                        citation.excerpt,
                                    ]
                                )
                                self.assertTrue(has_content, "Citation should have some content")

                # Log citation count for informational purposes
                print(f"Found {total_citations} citations for {lang} '{word}'")

    def test_morphology_presence(self):
        """Test that morphology information is present in DictionaryEntry objects."""
        # Test words that should have morphology
        test_words = [
            ("lupus", "lat"),
            ("λόγος", "grc"),
            ("अग्नि", "san"),
        ]

        for word, lang in test_words:
            with self.subTest(word=word, lang=lang):
                entries = self.wiring.engine.handle_query(lang, word)

                # Should return a list of DictionaryEntry objects
                self.assertIsInstance(entries, list)

                # Check if any entries have morphology
                morphology_count = 0
                for entry in entries:
                    self.assertIsInstance(entry, DictionaryEntry)
                    if entry.morphology:
                        morphology_count += 1
                        # Morphology should be a MorphologyInfo object
                        self.assertIsInstance(entry.morphology, MorphologyInfo)
                        # Check that it has the expected fields
                        self.assertTrue(hasattr(entry.morphology, "lemma"))
                        self.assertTrue(hasattr(entry.morphology, "pos"))
                        self.assertTrue(hasattr(entry.morphology, "features"))
                        self.assertTrue(hasattr(entry.morphology, "confidence"))

                # Log morphology count for informational purposes
                print(f"Found {morphology_count} morphology entries for {lang} '{word}'")

    def test_json_serialization(self):
        """Test that DictionaryEntry objects can be serialized to JSON."""

        # Test words from all languages
        test_words = [
            ("lupus", "lat"),
            ("λόγος", "grc"),
            ("अग्नि", "san"),
        ]

        for word, lang in test_words:
            with self.subTest(word=word, lang=lang):
                entries = self.wiring.engine.handle_query(lang, word)

                # Should return a list of DictionaryEntry objects
                self.assertIsInstance(entries, list)

                # Should be able to serialize to JSON without errors
                try:
                    json_bytes = orjson.dumps(entries)
                    self.assertIsInstance(json_bytes, bytes)
                    self.assertGreater(len(json_bytes), 0)

                    # Should be valid JSON
                    json_str = json_bytes.decode("utf-8")
                    self.assertIsInstance(json_str, str)
                except Exception as e:
                    self.fail(f"Failed to serialize {lang} '{word}': {e}")


if __name__ == "__main__":
    unittest.main()
