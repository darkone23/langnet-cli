import logging
import unittest

from langnet.classics_toolkit.core import ClassicsToolkit, LatinQueryResult

logging.getLogger("urllib3.connection").setLevel(logging.ERROR)


class ClassicsToolkitWiring:
    def __init__(self):
        self.cltk = ClassicsToolkit()


wiring = ClassicsToolkitWiring()


class TestClassicsToolkitIntegration(unittest.TestCase):
    def test_is_available_reflects_cltk_status(self):
        self.assertIsInstance(wiring.cltk.is_available(), bool)

    def test_latin_query_returns_latin_query_result(self):
        result = wiring.cltk.latin_query("lupus")
        self.assertIsInstance(result, LatinQueryResult)

    def test_latin_query_has_required_fields(self):
        result = wiring.cltk.latin_query("lupus")
        self.assertIsInstance(result.headword, str)
        self.assertIsInstance(result.ipa, str)
        self.assertIsInstance(result.lewis_1890_lines, list)

    def test_latin_query_returns_headword_for_known_word(self):
        result = wiring.cltk.latin_query("lupus")
        self.assertNotEqual(result.headword, "")
        self.assertNotEqual(result.headword, "error")

    def test_latin_query_unknown_word_still_returns_result(self):
        result = wiring.cltk.latin_query("xyznonexistentword123")
        self.assertIsInstance(result, LatinQueryResult)
        self.assertIn(result.headword, ["error", "xyznonexistentword123"])

    def test_latin_query_multiple_forms(self):
        forms = ["lupus", "lupi", "lupum", "lupo"]
        for form in forms:
            with self.subTest(form=form):
                result = wiring.cltk.latin_query(form)
                self.assertIsInstance(result, LatinQueryResult)


class TestClassicsToolkitProperties(unittest.TestCase):
    def test_latdict_property_exists(self):
        self.assertTrue(hasattr(wiring.cltk, "latdict"))

    def test_latlemma_property_exists(self):
        self.assertTrue(hasattr(wiring.cltk, "latlemma"))

    def test_latxform_property_exists(self):
        self.assertTrue(hasattr(wiring.cltk, "latxform"))

    def test_jvsub_property_exists(self):
        self.assertTrue(hasattr(wiring.cltk, "jvsub"))


if __name__ == "__main__":
    unittest.main()
