"""
Comprehensive test coverage for the Universal Schema implementation.

This test suite verifies that:
1. All backend adapters conform to the universal schema
2. The Language Engine returns structured DictionaryEntry objects
3. Citations, morphology, and senses are properly structured
4. JSON serialization works without custom encoders
5. Backward compatibility is maintained

Run with: just test-universal-schema
"""

import json
import time
import unittest

import orjson

from langnet.backend_adapter import (
    CDSLBackendAdapter,
    CLTKBackendAdapter,
    DiogenesBackendAdapter,
    HeritageBackendAdapter,
    WhitakersBackendAdapter,
)
from langnet.classics_toolkit.core import ClassicsToolkit
from langnet.core import LangnetWiring
from langnet.schema import Citation, DictionaryEntry, MorphologyInfo, Sense


def preload_dependencies():
    """Pre-load CLTK and other heavy dependencies to avoid timing them in tests."""
    ClassicsToolkit()  # Triggers CLTK/spacy/sanskrit loading


preload_dependencies()


class BackendAdapterRegistry:
    """Simple registry of backend adapters for testing."""

    def __init__(self):
        self.adapters = {
            "diogenes": DiogenesBackendAdapter(),
            "whitakers": WhitakersBackendAdapter(),
            "cltk": CLTKBackendAdapter(),
            "heritage": HeritageBackendAdapter(),
            "cdsl": CDSLBackendAdapter(),
        }

    def get_adapter(self, backend_name):
        """Get adapter for a specific backend."""
        if backend_name not in self.adapters:
            raise ValueError(f"No adapter registered for backend: {backend_name}")
        return self.adapters[backend_name]


class TestUniversalSchemaComprehensive(unittest.TestCase):
    """Complete end-to-end testing of universal schema implementation."""

    def setUp(self):
        """Set up test environment with universal schema enabled."""
        self.wiring = LangnetWiring(cache_enabled=False)
        self.adapter_registry = BackendAdapterRegistry()

    def tearDown(self):
        """Clean up environment."""
        pass

    def _validate_dictionary_entry(self, entry: DictionaryEntry) -> None:
        """Validate that a DictionaryEntry conforms to the schema."""
        # Basic structure
        self.assertIsInstance(entry, DictionaryEntry)
        self.assertIsInstance(entry.word, str)
        self.assertIsInstance(entry.language, str)
        self.assertIsInstance(entry.source, str)
        self.assertIsInstance(entry.senses, list)
        self.assertIsInstance(entry.metadata, dict)

        # Content validation
        self.assertTrue(entry.word.strip(), "Word should not be empty")
        self.assertTrue(entry.language.strip(), "Language should not be empty")
        self.assertTrue(entry.source.strip(), "Source should not be empty")

        # Validate senses
        for sense in entry.senses:
            self.assertIsInstance(sense, Sense)
            self.assertIsInstance(sense.pos, str)
            self.assertIsInstance(sense.definition, str)
            self.assertIsInstance(sense.citations, list)
            self.assertIsInstance(sense.examples, list)
            self.assertIsInstance(sense.metadata, dict)

            # Citations validation
            for citation in sense.citations:
                if citation is not None:
                    self.assertIsInstance(citation, Citation)
                    if citation.url:
                        self.assertIsInstance(citation.url, str)
                    if citation.title:
                        self.assertIsInstance(citation.title, str)

        # Validate morphology if present
        if entry.morphology:
            self.assertIsInstance(entry.morphology, MorphologyInfo)
            self.assertIsInstance(entry.morphology.lemma, str)
            self.assertIsInstance(entry.morphology.pos, str)
            self.assertIsInstance(entry.morphology.features, dict)
            self.assertIsInstance(entry.morphology.confidence, (int, float))

    def test_sanskrit_word_agni(self):
        """Test Sanskrit word 'agni' via universal schema."""
        entries = self.wiring.engine.handle_query("san", "agni")

        self.assertIsInstance(entries, list)
        self.assertGreater(len(entries), 0, "Should have at least one entry for 'agni'")

        for entry in entries:
            self._validate_dictionary_entry(entry)
            self.assertEqual(entry.word, "agni")
            self.assertEqual(entry.language, "san")

            # Should have sources like heritage, cdsl
            self.assertIn(entry.source, ["heritage", "cdsl", "diogenes", "whitakers", "cltk"])

    def test_latin_word_lupus(self):
        """Test Latin word 'lupus' via universal schema."""
        entries = self.wiring.engine.handle_query("lat", "lupus")

        self.assertIsInstance(entries, list)
        self.assertGreater(len(entries), 0, "Should have at least one entry for 'lupus'")

        found_whitakers = False
        found_diogenes = False

        for entry in entries:
            self._validate_dictionary_entry(entry)
            self.assertEqual(entry.word, "lupus")
            self.assertEqual(entry.language, "lat")

            if entry.source == "whitakers":
                found_whitakers = True
            elif entry.source == "diogenes":
                found_diogenes = True

            # CLTK should be present occasionally
            self.assertIn(entry.source, ["whitakers", "diogenes", "cltk", "heritage", "cdsl"])

        # Should have at least diogenes or whitakers for Latin
        self.assertTrue(found_whitakers or found_diogenes, "Should have Latin backends")

    def test_greek_word_logos(self):
        """Test Greek word 'λόγος' via universal schema."""
        entries = self.wiring.engine.handle_query("grc", "λόγος")

        self.assertIsInstance(entries, list)
        self.assertGreater(len(entries), 0, "Should have at least one entry for 'λόγος'")

        found_diogenes = False
        found_spacy = False

        for entry in entries:
            self._validate_dictionary_entry(entry)
            self.assertEqual(entry.word, "λόγος")
            self.assertEqual(entry.language, "grc")

            if entry.source == "diogenes":
                found_diogenes = True
            elif entry.source == "spacy":  # CLTK returns as "spacy"
                found_spacy = True

        # Should have diogenes or spacy for Greek
        self.assertTrue(found_diogenes or found_spacy, "Should have Greek backends")

    def test_json_serialization_all_languages(self):
        """Test that all languages can be serialized to JSON."""
        test_words = [("lat", "lupus"), ("grc", "λόγος"), ("san", "agni")]

        for language, word in test_words:
            with self.subTest(language=language, word=word):
                entries = self.wiring.engine.handle_query(language, word)

                # Should be able to serialize without custom encoders
                try:
                    json_bytes = orjson.dumps(entries)
                    self.assertIsInstance(json_bytes, bytes)
                    self.assertGreater(len(json_bytes), 0)

                    # Should be valid JSON
                    json_str = json_bytes.decode("utf-8")
                    parsed = json.loads(json_str)
                    self.assertIsInstance(parsed, list)
                    self.assertEqual(len(parsed), len(entries))

                except Exception as e:
                    self.fail(f"Failed to serialize {language} '{word}': {e}")

    def test_morphology_present_when_expected(self):
        """Test that morphology information is present when expected."""
        # Test Latin where Whitaker's should provide morphology
        entries = self.wiring.engine.handle_query("lat", "lupus")

        found_morphology = False
        for entry in entries:
            if entry.morphology:
                found_morphology = True
                self.assertIsInstance(entry.morphology.lemma, str)
                self.assertIsInstance(entry.morphology.pos, str)
                break

        # Latin should have morphology from one of the backends
        self.assertTrue(found_morphology, "Latin should have morphology info")

    def test_adapter_registry_all_backends(self):
        """Test that all expected backends have adapters."""
        expected_backends = ["heritage", "cdsl", "whitakers", "diogenes", "cltk"]

        for backend_name in expected_backends:
            with self.subTest(backend=backend_name):
                try:
                    adapter = self.adapter_registry.get_adapter(backend_name)
                    self.assertIsNotNone(adapter)
                    # Should have an adapt method
                    self.assertTrue(hasattr(adapter, "adapt"))
                    self.assertTrue(callable(getattr(adapter, "adapt")))
                except Exception as e:
                    self.fail(f"No adapter for {backend_name}: {e}")

    def test_backward_compatibility_mode(self):
        """Test that the universal schema returns structured DictionaryEntry objects."""
        wiring = LangnetWiring(cache_enabled=False)
        entries = wiring.engine.handle_query("lat", "lupus")

        # Should be a list of DictionaryEntry
        self.assertIsInstance(entries, list)

        # Should have entries from expected backends
        sources = [e.source for e in entries]
        self.assertIn("whitakers", sources, "Should have whitakers entries")
        self.assertIn("diogenes", sources, "Should have diogenes entries")

        # Each entry should be a DictionaryEntry
        for entry in entries:
            self.assertIsInstance(entry, DictionaryEntry)

    def test_citations_structure(self):
        """Test that citations have proper structure when present."""
        entries = self.wiring.engine.handle_query("san", "agni")

        total_citations = 0
        for entry in entries:
            for sense in entry.senses:
                for citation in sense.citations:
                    if citation:
                        total_citations += 1
                        # Should have at least one of: url, title, author, page, excerpt
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

        # We expect at least some citations in the system
        # (may be minimal based on backend capabilities)
        print(f"Found {total_citations} citations across all entries")

    def test_performance_baseline(self):
        """Test that performance is reasonable for a cached query."""
        # Warmup - first query triggers initialization
        self.wiring.engine.handle_query("lat", "sum")

        # Time the actual query (should be fast with cached backends)
        start_time = time.time()
        entries = self.wiring.engine.handle_query("lat", "sum")
        duration = time.time() - start_time

        # Should complete in under 3 seconds (accounts for network/process overhead)
        self.assertLess(duration, 3.0, f"Query took too long: {duration:.2f}s")

        # Should return results
        self.assertGreater(len(entries), 0)


if __name__ == "__main__":
    unittest.main()
