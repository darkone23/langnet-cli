import unittest
from typing import cast

import cattrs

from langnet.classics_toolkit.core import (
    ClassicsToolkit,
    SanskritMorphologyResult,
)
from langnet.cologne.core import SanskritCologneLexicon
from langnet.engine.core import LanguageEngine, LanguageEngineConfig


def find_entries_by_source(entries, source):
    """Helper to find all entries from a specific source."""
    return [e for e in entries if e.source == source]


def get_first_entry_by_source(entries, source):
    """Helper to get first entry from a specific source."""
    for entry in entries:
        if entry.source == source:
            return entry
    return None


class TestSanskritMorphologyResult(unittest.TestCase):
    def test_dataclass_creation(self):
        result = SanskritMorphologyResult(
            lemma="yoga",
            pos="NOUN",
            morphological_features={"Case": "Nom", "Number": "Sing"},
        )
        self.assertEqual(result.lemma, "yoga")
        self.assertEqual(result.pos, "NOUN")
        self.assertEqual(result.morphological_features["Case"], "Nom")

    def test_cattrs_serialization(self):
        converter = cattrs.Converter(omit_if_default=True)
        result = SanskritMorphologyResult(
            lemma="agni",
            pos="NOUN",
            morphological_features={},
        )
        serialized = converter.unstructure(result)
        self.assertEqual(serialized["lemma"], "agni")
        self.assertEqual(serialized["pos"], "NOUN")
        self.assertIsInstance(serialized, dict)


class TestClassicsToolkitSanskrit(unittest.TestCase):
    def setUp(self):
        self.toolkit = ClassicsToolkit()

    def test_sanskrit_morphology_query_returns_result(self):
        result = self.toolkit.sanskrit_morphology_query("agni")
        self.assertIsInstance(result, SanskritMorphologyResult)
        self.assertIn(result.lemma, ("agni", "error", "cltk_unavailable"))

    def test_sanskrit_morphology_query_empty_input(self):
        result = self.toolkit.sanskrit_morphology_query("")
        self.assertIsInstance(result, SanskritMorphologyResult)

    def test_sanskrit_morphology_query_devanagari(self):
        result = self.toolkit.sanskrit_morphology_query("अग्नि")
        self.assertIsInstance(result, SanskritMorphologyResult)


class TestSanskritCologneRootExtraction(unittest.TestCase):
    def setUp(self):
        self.lexicon = SanskritCologneLexicon()

    def test_lookup_ascii_returns_root_field(self):
        result = self.lexicon.lookup_ascii("agni")
        self.assertIn("root", result)

    def test_agni_has_verb_root(self):
        result = self.lexicon.lookup_ascii("agni")
        self.assertIn("root", result)
        root = result["root"]
        self.assertEqual(root["type"], "verb_root")
        self.assertEqual(root["root"], "ag")

    def test_lookup_ascii_returns_transliteration(self):
        result = self.lexicon.lookup_ascii("agni")
        self.assertIn("transliteration", result)
        transliteration = result["transliteration"]
        self.assertIn("devanagari", transliteration)
        self.assertEqual(transliteration["devanagari"], "अग्नि")

    def test_lookup_ascii_returns_dictionaries(self):
        result = self.lexicon.lookup_ascii("agni")
        self.assertIn("dictionaries", result)
        self.assertIn("mw", result["dictionaries"])
        self.assertIn("ap90", result["dictionaries"])


class TestSanskritEngineLemmatizationFallback(unittest.TestCase):
    def setUp(self):
        self.cltk = ClassicsToolkit()
        self.cdsl = SanskritCologneLexicon()
        self.engine = LanguageEngine(
            LanguageEngineConfig(
                scraper=None,  # type: ignore
                whitakers=None,  # type: ignore
                cltk=self.cltk,
                cdsl=self.cdsl,
            )
        )

    def test_direct_lookup_returns_entries(self):
        entries = self.engine.handle_query("san", "agni")
        self.assertIsInstance(entries, list)
        self.assertGreater(len(entries), 0, "Should have at least one entry for agni")

        cdsl_entry = get_first_entry_by_source(entries, "cdsl")
        self.assertIsNotNone(cdsl_entry, "Should have cdsl entry")

    def test_direct_lookup_has_dictionary_info(self):
        entries = self.engine.handle_query("san", "agni")
        cdsl_entry = get_first_entry_by_source(entries, "cdsl")
        self.assertIsNotNone(cdsl_entry, "Should have cdsl entry")
        if cdsl_entry:
            cdsl_result = cdsl_entry.metadata
            self.assertIn("dictionary", cdsl_result)

    def test_engine_uses_cdsl_for_sanskrit(self):
        result = self.engine._query_sanskrit("agni", self.engine._cattrs_converter)
        self.assertIn("cdsl", result)
        cdsl_result = result["cdsl"]
        self.assertIn("dictionaries", cdsl_result)
        self.assertIn("mw", cdsl_result["dictionaries"])


class TestSanskritIntegration(unittest.TestCase):
    def setUp(self):
        self.cltk = ClassicsToolkit()
        self.cdsl = SanskritCologneLexicon()
        self.engine = LanguageEngine(
            LanguageEngineConfig(
                scraper=None,  # type: ignore
                whitakers=None,  # type: ignore
                cltk=self.cltk,
                cdsl=self.cdsl,
            )
        )

    def test_agni_full_result_structure(self):
        entries = self.engine.handle_query("san", "agni")
        self.assertIsInstance(entries, list)
        self.assertGreater(len(entries), 0, "Should have entries for agni")

        sources = [e.source for e in entries]
        if "heritage" in sources:
            heritage_entry = get_first_entry_by_source(entries, "heritage")
            if heritage_entry:
                heritage_result = heritage_entry.metadata
                self.assertIn("morphology", heritage_result)
                self.assertIn("dictionary", heritage_result)
        else:
            cdsl_entry = get_first_entry_by_source(entries, "cdsl")
            self.assertIsNotNone(cdsl_entry, "Should have cdsl entry")
            if cdsl_entry:
                cdsl_result = cdsl_entry.metadata
                self.assertIn("dictionary", cdsl_result)


class TestSanskritStandaloneFunctions(unittest.TestCase):
    def setUp(self):
        self.cltk = ClassicsToolkit()
        self.cdsl = SanskritCologneLexicon()
        self.engine = LanguageEngine(
            LanguageEngineConfig(
                scraper=None,  # type: ignore
                whitakers=None,  # type: ignore
                cltk=self.cltk,
                cdsl=self.cdsl,
            )
        )

    def test_agni_has_entries(self):
        entries = self.engine.handle_query("san", "agni")
        self.assertIsInstance(entries, list)
        self.assertGreater(len(entries), 0, "Should have entries for agni")

    def test_agni_has_cdsl_dictionary(self):
        entries = self.engine.handle_query("san", "agni")
        cdsl_entry = get_first_entry_by_source(entries, "cdsl")
        self.assertIsNotNone(cdsl_entry, "Should have cdsl entry")
        if cdsl_entry:
            cdsl_result = cdsl_entry.metadata
            self.assertIn("dictionary", cdsl_result)


class TestSanskritMorphologyFeatures(unittest.TestCase):
    def setUp(self):
        self.toolkit = ClassicsToolkit()

    def test_morphology_result_has_morphological_features_dict(self):
        result = self.toolkit.sanskrit_morphology_query("agni")
        self.assertIsInstance(result.morphological_features, dict)


if __name__ == "__main__":
    unittest.main()
