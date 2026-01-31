import unittest
from typing import cast

import cattrs

from langnet.cache.core import NoOpCache
from langnet.classics_toolkit.core import (
    ClassicsToolkit,
    SanskritMorphologyResult,
)
from langnet.cologne.core import SanskritCologneLexicon
from langnet.engine.core import LanguageEngine, LanguageEngineConfig


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
                cache=NoOpCache(),
            )
        )

    def test_direct_lookup_sets_search_method(self):
        result = self.engine.handle_query("san", "agni")
        # Since no Heritage services, result should be from CDSL
        self.assertIn("cdsl", result)
        cdsl_result = result["cdsl"]
        self.assertEqual(cdsl_result.get("_search_method"), "direct")

    def test_direct_lookup_has_root(self):
        result = self.engine.handle_query("san", "agni")
        # Since no Heritage services, result should be from CDSL
        self.assertIn("cdsl", result)
        cdsl_result = result["cdsl"]
        self.assertIn("root", cdsl_result)
        self.assertEqual(cdsl_result["root"]["root"], "ag")

    def test_direct_lookup_includes_lemmatized_fields(self):
        result = self.engine.handle_query("san", "agni")
        # Since no Heritage services, result should be from CDSL
        self.assertIn("cdsl", result)
        cdsl_result = result["cdsl"]
        self.assertIn("_search_method", cdsl_result)

    def test_result_structure_has_transliteration(self):
        result = self.engine.handle_query("san", "agni")
        # Since no Heritage services, result should be from CDSL
        self.assertIn("cdsl", result)
        cdsl_result = result["cdsl"]
        self.assertIn("transliteration", cdsl_result)
        self.assertIn("dictionaries", cdsl_result)

    def test_engine_uses_cdsl_for_sanskrit(self):
        result = self.engine._query_sanskrit("agni", self.engine._cattrs_converter)
        # This should return CDSL results in the cdsl key
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
                cache=NoOpCache(),
            )
        )

    def test_agni_full_result_structure(self):
        result = self.engine.handle_query("san", "agni")
        # Check if we have Heritage results
        if "heritage" in result:
            # For Heritage results, check the structure
            heritage_result = result["heritage"]
            self.assertIn("morphology", heritage_result)
            self.assertIn("dictionary", heritage_result)
        else:
            # For CDSL-only results, check the structure
            cdsl_result = result["cdsl"]
            required_keys = ["transliteration", "dictionaries", "root", "_search_method"]
            for key in required_keys:
                with self.subTest(key=key):
                    self.assertIn(key, cdsl_result)


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
                cache=NoOpCache(),
            )
        )

    def test_agni_transliteration_fields(self):
        result = self.engine.handle_query("san", "agni")
        # Check both Heritage and CDSL results
        trans = None
        if "heritage" in result and result["heritage"].get("dictionary"):
            # Heritage results have transliteration in the dictionary section
            heritage_dict = result["heritage"]["dictionary"]
            trans = heritage_dict.get("transliteration")
        elif "cdsl" in result:
            # CDSL results have transliteration at the top level of cdsl
            trans = result["cdsl"].get("transliteration")

        self.assertIsNotNone(trans)
        self.assertIsInstance(trans, dict)
        trans = cast(dict, trans)
        self.assertIn("iast", trans)
        self.assertIn("devanagari", trans)
        self.assertEqual(trans["iast"], "agni")
        self.assertEqual(trans["devanagari"], "अग्नि")

    def test_agni_mw_dictionary_has_entries(self):
        result = self.engine.handle_query("san", "agni")
        # Check both Heritage and CDSL results
        mw_entries = None
        if "heritage" in result and result["heritage"].get("dictionary"):
            # Heritage results have entries in the dictionary section
            heritage_dict = result["heritage"]["dictionary"]
            mw_entries = heritage_dict.get("entries")
        elif "cdsl" in result:
            # CDSL results have dictionaries in the cdsl section
            cdsl_result = result["cdsl"]
            mw_entries = cdsl_result.get("dictionaries", {}).get("mw")

        self.assertIsNotNone(mw_entries)
        self.assertIsInstance(mw_entries, list)
        mw_entries = cast(list, mw_entries)
        self.assertTrue(len(mw_entries) > 0)
        first_entry = mw_entries[0]
        self.assertIsInstance(first_entry, dict)
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
