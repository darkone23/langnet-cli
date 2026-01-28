import unittest

import cattrs

from langnet.cache.core import NoOpCache
from langnet.classics_toolkit.core import (
    ClassicsToolkit,
    SanskritMorphologyResult,
)
from langnet.cologne.core import SanskritCologneLexicon
from langnet.engine.core import LanguageEngine


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
        root = result.get("root")
        self.assertIsNotNone(root)
        assert root is not None
        self.assertEqual(root.get("type"), "verb_root")
        self.assertEqual(root.get("root"), "ag")

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
            scraper=None,  # type: ignore
            whitakers=None,  # type: ignore
            cltk=self.cltk,
            cdsl=self.cdsl,
            cache=NoOpCache(),
        )

    def test_direct_lookup_sets_search_method(self):
        result = self.engine.handle_query("san", "agni")
        self.assertEqual(result.get("_search_method"), "direct")

    def test_direct_lookup_has_root(self):
        result = self.engine.handle_query("san", "agni")
        self.assertIn("root", result)
        self.assertEqual(result["root"]["root"], "ag")

    def test_direct_lookup_includes_lemmatized_fields(self):
        result = self.engine.handle_query("san", "agni")
        self.assertIn("_search_method", result)

    def test_result_structure_has_transliteration(self):
        result = self.engine.handle_query("san", "agni")
        self.assertIn("transliteration", result)
        self.assertIn("dictionaries", result)

    def test_engine_uses_cdsl_for_sanskrit(self):
        result = self.engine._query_sanskrit("agni", self.engine._cattrs_converter)
        self.assertIn("dictionaries", result)
        self.assertIn("mw", result["dictionaries"])


class TestSanskritIntegration(unittest.TestCase):
    def setUp(self):
        self.cltk = ClassicsToolkit()
        self.cdsl = SanskritCologneLexicon()
        self.engine = LanguageEngine(
            scraper=None,  # type: ignore
            whitakers=None,  # type: ignore
            cltk=self.cltk,
            cdsl=self.cdsl,
            cache=NoOpCache(),
        )

    def test_agni_full_result_structure(self):
        result = self.engine.handle_query("san", "agni")
        required_keys = ["transliteration", "dictionaries", "root", "_search_method"]
        for key in required_keys:
            with self.subTest(key=key):
                self.assertIn(key, result)

    def test_agni_transliteration_fields(self):
        result = self.engine.handle_query("san", "agni")
        trans = result["transliteration"]
        self.assertIn("iast", trans)
        self.assertIn("devanagari", trans)
        self.assertEqual(trans["iast"], "agni")
        self.assertEqual(trans["devanagari"], "अग्नि")

    def test_agni_mw_dictionary_has_entries(self):
        result = self.engine.handle_query("san", "agni")
        mw_entries = result["dictionaries"]["mw"]
        self.assertTrue(len(mw_entries) > 0)
        first_entry = mw_entries[0]
        self.assertIn("meaning", first_entry)
        self.assertIn("pos", first_entry)


class TestSanskritMorphologyFeatures(unittest.TestCase):
    def setUp(self):
        self.toolkit = ClassicsToolkit()

    def test_morphology_result_has_morphological_features_dict(self):
        result = self.toolkit.sanskrit_morphology_query("agni")
        self.assertIsInstance(result.morphological_features, dict)


if __name__ == "__main__":
    unittest.main()
