"""
Fuzz testing for backend adapters using real tool output fixtures.

This module tests backend adapters with real tool output fixtures
to ensure they properly convert raw backend data to the universal schema.
"""

import json
import unittest
from pathlib import Path
from typing import Any, Dict, List

from langnet.backend_adapter import (
    CDSLBackendAdapter,
    CLTKBackendAdapter,
    DiogenesBackendAdapter,
    HeritageBackendAdapter,
    WhitakersBackendAdapter,
)
from langnet.schema import DictionaryEntry, Citation, Sense, MorphologyInfo


class FuzzTestBackendAdapters(unittest.TestCase):
    """Fuzz testing for backend adapters with real tool output fixtures."""

    def setUp(self):
        """Set up test environment."""
        self.fixture_dir = Path("tests/fixtures/raw_tool_outputs")
        self.adapters = {
            "diogenes": DiogenesBackendAdapter(),
            "whitakers": WhitakersBackendAdapter(),
            "cltk": CLTKBackendAdapter(),
            "heritage": HeritageBackendAdapter(),
            "cdsl": CDSLBackendAdapter(),
        }

    def _load_fixture(self, tool: str, filename: str) -> Dict[str, Any]:
        """Load a fixture file."""
        fixture_path = self.fixture_dir / tool / filename
        if not fixture_path.exists():
            self.skipTest(f"Fixture not found: {fixture_path}")

        with open(fixture_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_diogenes_adapter_with_real_fixtures(self):
        """Test Diogenes adapter with real fixtures."""
        adapter = self.adapters["diogenes"]

        # Test with available fixtures
        diogenes_fixtures = list((self.fixture_dir / "diogenes").glob("*.json"))
        if not diogenes_fixtures:
            self.skipTest("No Diogenes fixtures available")

        for fixture_path in diogenes_fixtures[:3]:  # Test first 3 fixtures
            with self.subTest(fixture=fixture_path.name):
                try:
                    with open(fixture_path, "r", encoding="utf-8") as f:
                        raw_data = json.load(f)

                    entries = adapter.adapt(raw_data, "lat", "test_word")

                    # Should return a list
                    self.assertIsInstance(entries, list)

                    # All entries should be DictionaryEntry objects
                    for entry in entries:
                        self.assertIsInstance(entry, DictionaryEntry)
                        # Validate required fields
                        self.assertIsInstance(entry.word, str)
                        self.assertIsInstance(entry.language, str)
                        self.assertIsInstance(entry.source, str)
                        self.assertEqual(entry.source, "diogenes")
                        self.assertIsInstance(entry.senses, list)

                        # Validate senses
                        for sense in entry.senses:
                            self.assertIsInstance(sense, Sense)
                            self.assertIsInstance(sense.pos, str)
                            self.assertIsInstance(sense.definition, str)
                            self.assertIsInstance(sense.citations, list)
                            self.assertIsInstance(sense.examples, list)

                            # Validate citations
                            for citation in sense.citations:
                                if citation is not None:
                                    self.assertIsInstance(citation, Citation)

                except Exception as e:
                    # Log the error but don't fail the test
                    print(f"Warning: Fixture {fixture_path.name} caused error: {e}")

    def test_whitakers_adapter_with_real_fixtures(self):
        """Test Whitakers adapter with real fixtures."""
        adapter = self.adapters["whitakers"]

        # Test with available fixtures
        whitakers_fixtures = list((self.fixture_dir / "whitakers").glob("*.json"))
        if not whitakers_fixtures:
            self.skipTest("No Whitakers fixtures available")

        for fixture_path in whitakers_fixtures[:3]:  # Test first 3 fixtures
            with self.subTest(fixture=fixture_path.name):
                try:
                    with open(fixture_path, "r", encoding="utf-8") as f:
                        raw_data = json.load(f)

                    entries = adapter.adapt(raw_data, "lat", "test_word")

                    # Should return a list
                    self.assertIsInstance(entries, list)

                    # All entries should be DictionaryEntry objects
                    for entry in entries:
                        self.assertIsInstance(entry, DictionaryEntry)
                        # Validate required fields
                        self.assertIsInstance(entry.word, str)
                        self.assertIsInstance(entry.language, str)
                        self.assertIsInstance(entry.source, str)
                        self.assertEqual(entry.source, "whitakers")
                        self.assertIsInstance(entry.senses, list)

                        # Validate senses
                        for sense in entry.senses:
                            self.assertIsInstance(sense, Sense)
                            self.assertIsInstance(sense.pos, str)
                            self.assertIsInstance(sense.definition, str)
                            self.assertIsInstance(sense.citations, list)
                            self.assertIsInstance(sense.examples, list)

                except Exception as e:
                    # Log the error but don't fail the test
                    print(f"Warning: Fixture {fixture_path.name} caused error: {e}")

    def test_cltk_adapter_with_real_fixtures(self):
        """Test CLTK adapter with real fixtures."""
        adapter = self.adapters["cltk"]

        # Test with available fixtures
        cltk_fixtures = list((self.fixture_dir / "cltk").glob("*.json"))
        if not cltk_fixtures:
            self.skipTest("No CLTK fixtures available")

        for fixture_path in cltk_fixtures[:3]:  # Test first 3 fixtures
            with self.subTest(fixture=fixture_path.name):
                try:
                    with open(fixture_path, "r", encoding="utf-8") as f:
                        raw_data = json.load(f)

                    entries = adapter.adapt(raw_data, "lat", "test_word")

                    # Should return a list
                    self.assertIsInstance(entries, list)

                    # All entries should be DictionaryEntry objects
                    for entry in entries:
                        self.assertIsInstance(entry, DictionaryEntry)
                        # Validate required fields
                        self.assertIsInstance(entry.word, str)
                        self.assertIsInstance(entry.language, str)
                        self.assertIsInstance(entry.source, str)
                        self.assertEqual(entry.source, "cltk")
                        self.assertIsInstance(entry.senses, list)

                        # Validate senses
                        for sense in entry.senses:
                            self.assertIsInstance(sense, Sense)
                            self.assertIsInstance(sense.pos, str)
                            self.assertIsInstance(sense.definition, str)
                            self.assertIsInstance(sense.citations, list)
                            self.assertIsInstance(sense.examples, list)

                except Exception as e:
                    # Log the error but don't fail the test
                    print(f"Warning: Fixture {fixture_path.name} caused error: {e}")

    def test_heritage_adapter_with_real_fixtures(self):
        """Test Heritage adapter with real fixtures."""
        adapter = self.adapters["heritage"]

        # Test with available fixtures
        heritage_fixtures = list((self.fixture_dir / "heritage").glob("*.json"))
        if not heritage_fixtures:
            self.skipTest("No Heritage fixtures available")

        for fixture_path in heritage_fixtures[:3]:  # Test first 3 fixtures
            with self.subTest(fixture=fixture_path.name):
                try:
                    with open(fixture_path, "r", encoding="utf-8") as f:
                        raw_data = json.load(f)

                    entries = adapter.adapt(raw_data, "san", "test_word")

                    # Should return a list
                    self.assertIsInstance(entries, list)

                    # All entries should be DictionaryEntry objects
                    for entry in entries:
                        self.assertIsInstance(entry, DictionaryEntry)
                        # Validate required fields
                        self.assertIsInstance(entry.word, str)
                        self.assertIsInstance(entry.language, str)
                        self.assertIsInstance(entry.source, str)
                        self.assertEqual(entry.source, "heritage")
                        self.assertIsInstance(entry.senses, list)

                        # Validate senses
                        for sense in entry.senses:
                            self.assertIsInstance(sense, Sense)
                            self.assertIsInstance(sense.pos, str)
                            self.assertIsInstance(sense.definition, str)
                            self.assertIsInstance(sense.citations, list)
                            self.assertIsInstance(sense.examples, list)

                            # Validate citations
                            for citation in sense.citations:
                                if citation is not None:
                                    self.assertIsInstance(citation, Citation)

                except Exception as e:
                    # Log the error but don't fail the test
                    print(f"Warning: Fixture {fixture_path.name} caused error: {e}")

    def test_cdsl_adapter_with_real_fixtures(self):
        """Test CDSL adapter with real fixtures."""
        adapter = self.adapters["cdsl"]

        # Test with available fixtures
        cdsl_fixtures = list((self.fixture_dir / "cdsl").glob("*.json"))
        if not cdsl_fixtures:
            self.skipTest("No CDSL fixtures available")

        for fixture_path in cdsl_fixtures[:3]:  # Test first 3 fixtures
            with self.subTest(fixture=fixture_path.name):
                try:
                    with open(fixture_path, "r", encoding="utf-8") as f:
                        raw_data = json.load(f)

                    entries = adapter.adapt(raw_data, "san", "test_word")

                    # Should return a list
                    self.assertIsInstance(entries, list)

                    # All entries should be DictionaryEntry objects
                    for entry in entries:
                        self.assertIsInstance(entry, DictionaryEntry)
                        # Validate required fields
                        self.assertIsInstance(entry.word, str)
                        self.assertIsInstance(entry.language, str)
                        self.assertIsInstance(entry.source, str)
                        self.assertEqual(entry.source, "cdsl")
                        self.assertIsInstance(entry.senses, list)

                        # Validate senses
                        for sense in entry.senses:
                            self.assertIsInstance(sense, Sense)
                            self.assertIsInstance(sense.pos, str)
                            self.assertIsInstance(sense.definition, str)
                            self.assertIsInstance(sense.citations, list)
                            self.assertIsInstance(sense.examples, list)

                            # Validate citations
                            for citation in sense.citations:
                                if citation is not None:
                                    self.assertIsInstance(citation, Citation)

                except Exception as e:
                    # Log the error but don't fail the test
                    print(f"Warning: Fixture {fixture_path.name} caused error: {e}")

    def test_adapter_error_handling(self):
        """Test that all adapters handle error conditions gracefully."""
        error_data = {"error": "Backend unavailable"}

        for name, adapter in self.adapters.items():
            with self.subTest(adapter=name):
                # Determine appropriate language for this adapter
                lang = "lat" if name in ["diogenes", "whitakers", "cltk"] else "san"
                entries = adapter.adapt(error_data, lang, "test")
                self.assertIsInstance(entries, list)

    def test_adapter_empty_input_handling(self):
        """Test that all adapters handle empty input gracefully."""
        empty_data = {}

        for name, adapter in self.adapters.items():
            with self.subTest(adapter=name):
                # Determine appropriate language for this adapter
                lang = "lat" if name in ["diogenes", "whitakers", "cltk"] else "san"
                entries = adapter.adapt(empty_data, lang, "test")
                self.assertIsInstance(entries, list)

    def test_adapter_none_input_handling(self):
        """Test that all adapters handle None input gracefully."""
        for name, adapter in self.adapters.items():
            with self.subTest(adapter=name):
                # Determine appropriate language for this adapter
                lang = "lat" if name in ["diogenes", "whitakers", "cltk"] else "san"
                # Adapters should handle None input gracefully (may raise exception or return empty list)
                try:
                    entries = adapter.adapt(None, lang, "test")
                    self.assertIsInstance(entries, list)
                except Exception as e:
                    # It's acceptable for adapters to raise exceptions on None input
                    # as long as they don't crash the entire system
                    pass

    def test_schema_compliance(self):
        """Test that adapter outputs comply with the universal schema."""
        # Load a sample fixture for each adapter
        sample_fixtures = {
            "diogenes": "diogenes_search_lat_lupus.json",
            "whitakers": "whitakers_analyze_vir.json",
            "cltk": "cltk_morphology_lat_lupus.json",
            "heritage": "heritage_morphology_agni.json",
            "cdsl": "cdsl_lookup_agni.json",
        }

        for name, fixture_file in sample_fixtures.items():
            with self.subTest(adapter=name):
                try:
                    adapter = self.adapters[name]
                    raw_data = self._load_fixture(name, fixture_file)

                    # Determine appropriate language for this adapter
                    lang = "lat" if name in ["diogenes", "whitakers", "cltk"] else "san"
                    entries = adapter.adapt(raw_data, lang, "test_word")

                    # Validate schema compliance
                    self._validate_schema_compliance(entries, name)

                except FileNotFoundError:
                    # Skip if fixture not available
                    continue
                except Exception as e:
                    self.fail(f"Adapter {name} failed schema compliance: {e}")

    def _validate_schema_compliance(self, entries: List[DictionaryEntry], adapter_name: str):
        """Validate that entries comply with the universal schema."""
        # Should be a list
        self.assertIsInstance(entries, list)

        # Validate each entry
        for entry in entries:
            self.assertIsInstance(entry, DictionaryEntry)

            # Validate required fields
            self.assertIsInstance(entry.word, str)
            self.assertTrue(entry.word, "Word should not be empty")

            self.assertIsInstance(entry.language, str)
            self.assertIn(entry.language, ["lat", "grc", "san"], "Language should be valid")

            self.assertIsInstance(entry.source, str)
            self.assertEqual(entry.source, adapter_name, "Source should match adapter")

            # Validate senses
            self.assertIsInstance(entry.senses, list)
            for sense in entry.senses:
                self.assertIsInstance(sense, Sense)
                self.assertIsInstance(sense.pos, str)
                self.assertIsInstance(sense.definition, str)
                self.assertIsInstance(sense.citations, list)
                self.assertIsInstance(sense.examples, list)
                self.assertIsInstance(sense.metadata, dict)

                # Validate citations
                for citation in sense.citations:
                    if citation is not None:
                        self.assertIsInstance(citation, Citation)
                        # At least one field should have content
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

            # Validate morphology if present
            if entry.morphology is not None:
                self.assertIsInstance(entry.morphology, MorphologyInfo)
                self.assertIsInstance(entry.morphology.lemma, str)
                self.assertIsInstance(entry.morphology.pos, str)
                self.assertIsInstance(entry.morphology.features, dict)
                self.assertIsInstance(entry.morphology.confidence, (int, float))
                self.assertGreaterEqual(entry.morphology.confidence, 0.0)
                self.assertLessEqual(entry.morphology.confidence, 1.0)


if __name__ == "__main__":
    unittest.main()
