import unittest
import json
import logging

logging.getLogger("urllib3.connection").setLevel(logging.ERROR)

from langnet.core import LangnetWiring
from langnet.engine.core import LanguageEngine
from langnet.diogenes.core import DiogenesScraper, DiogenesLanguages
from langnet.whitakers_words.core import WhitakersWords
from langnet.classics_toolkit.core import ClassicsToolkit
from langnet.cologne.core import SanskritCologneLexicon


class TestGreekSpacyIntegration(unittest.TestCase):
    def setUp(self):
        self.wiring = LangnetWiring()

    def test_greek_query_includes_spacy_response(self):
        result = self.wiring.engine.handle_query("grc", "λόγος")

        self.assertIn("diogenes", result)
        self.assertIn("spacy", result)

        spacy_result = result["spacy"]
        self.assertIsInstance(spacy_result, dict)
        self.assertEqual(spacy_result["text"], "λόγος")
        self.assertIsInstance(spacy_result["lemma"], str)
        self.assertIsInstance(spacy_result["pos"], str)
        self.assertIsInstance(spacy_result["morphological_features"], dict)

    def test_greek_query_spacy_morphology_features(self):
        result = self.wiring.engine.handle_query("grc", "οὐσία")

        self.assertIn("spacy", result)
        spacy_result = result["spacy"]

        self.assertEqual(spacy_result["text"], "οὐσία")
        self.assertIn("Case", spacy_result["morphological_features"])
        self.assertIn("Gender", spacy_result["morphological_features"])


class TestLatinQueryIntegration(unittest.TestCase):
    def setUp(self):
        self.wiring = LangnetWiring()

    def test_latin_query_aggregates_sources(self):
        result = self.wiring.engine.handle_query("lat", "lupus")

        self.assertIn("diogenes", result)
        self.assertIn("whitakers", result)
        self.assertIn("cltk", result)

    def test_latin_query_cltk_has_headword(self):
        result = self.wiring.engine.handle_query("lat", "lupus")

        cltk_result = result["cltk"]
        self.assertIsInstance(cltk_result, dict)
        self.assertIn("headword", cltk_result)


if __name__ == "__main__":
    unittest.main()
