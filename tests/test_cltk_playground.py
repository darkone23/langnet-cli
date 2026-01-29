import logging
import textwrap
import unittest

from langnet.classics_toolkit.core import ClassicsToolkit
from langnet.cologne.core import SanskritCologneLexicon

cltk_logger = logging.getLogger("CLTK")
cltk_logger.setLevel(logging.CRITICAL)
cltk_logger.propagate = False


class TestLatinExamples(unittest.TestCase):
    def setUp(self):
        self.cltk = ClassicsToolkit()

    def test_replacer(self):
        self.assertTrue(hasattr(self.cltk, "jvsub"))
        replaced = self.cltk.jvsub.replace("justiciar")
        self.assertEqual(replaced, "iusticiar")

    def test_transcriber(self):
        self.assertTrue(hasattr(self.cltk, "latxform"))
        transcribed = self.cltk.latxform.transcribe("iusticiar")
        self.assertEqual(transcribed, "[jʊs.'t̪ɪ.kɪ̣.jar]")

    def test_lemmatizer(self):
        self.assertTrue(hasattr(self.cltk, "latlemma"))
        lupus = ["lupi", "luporum", "lupis", "lupos", "lupi", "lupis"]
        lemmas = self.cltk.latlemma.lemmatize(lupus)

        expected = [
            ("lupi", "lupus"),
            ("luporum", "lupus1"),
            ("lupis", "lupus1"),
            ("lupos", "lupus1"),
            ("lupi", "lupus"),
            ("lupis", "lupus1"),
        ]
        self.assertEqual(lemmas, expected)

    def test_lexicon(self):
        self.assertTrue(hasattr(self.cltk, "latdict"))
        result = self.cltk.latdict.lookup("saga")

        somestr = """\
        sāga


         ae, 
        f

        sagus, prophetic; SAG-, 
        a wisewoman, fortune-teller, sooth-sayer, witch
        , H., O."""

        self.assertEqual(result, textwrap.dedent(somestr))


class TestGreekSpacyMorphology(unittest.TestCase):
    def setUp(self):
        self.cltk = ClassicsToolkit()

    def test_spacy_is_available(self):
        self.assertIsInstance(self.cltk.spacy_is_available(), bool)

    def test_greek_morphology_query(self):
        result = self.cltk.greek_morphology_query("λόγος")

        self.assertIsInstance(result.text, str)
        self.assertIsInstance(result.lemma, str)
        self.assertIsInstance(result.pos, str)
        self.assertIsInstance(result.morphological_features, dict)

    def test_greek_morphology_returns_valid_result(self):
        result = self.cltk.greek_morphology_query("λόγος")

        self.assertEqual(result.text, "λόγος")
        self.assertEqual(result.lemma, "λόγος")
        self.assertEqual(result.pos, "NOUN")
        self.assertIn("Case", result.morphological_features)
        self.assertIn("Gender", result.morphological_features)


# class TestCologneDigitalSanskritLexicon(unittest.TestCase):

#     def test_basic_dictionary(self):
#         results = wiring.cologne_dict.mw.search("राम")
#         meaning = (
#             "राम mf(आ/)n. (prob. 'causing rest', and in most meanings fr. √ रम्) "
#             "dark, dark-coloured, black (cf. रात्रि), AV.; TĀr. (रामः शकुनिः. a black "
#             "bird, crow, KāṭhGṛ.; Viṣṇ.)"
#         )
#         self.assertEqual(results[0].meaning(), meaning)


if __name__ == "__main__":
    unittest.main()
