import unittest
import time
import textwrap
import logging

cltk_logger = logging.getLogger("CLTK")
cltk_logger.setLevel(logging.CRITICAL)
cltk_logger.propagate = False

from langnet.cologne.core import SanskritCologneLexicon
from langnet.classics_toolkit.core import ClassicsToolkit


class ClassicsWiring:
    def __init__(self):
        self.cologne_dict = SanskritCologneLexicon()
        self.cltk = ClassicsToolkit()


wiring = (
    ClassicsWiring()
)  # this will prompt downloading language data from universities


class TestLatinExamples(unittest.TestCase):
    # import basic latin corpus

    def test_replacer(self):
        replaced = wiring.cltk.jvsub.replace("justiciar")
        self.assertEqual(replaced, "iusticiar")

    def test_transcriber(self):
        transcribed = wiring.cltk.latxform.transcribe("iusticiar")  # type: ignore
        self.assertEqual(transcribed, "[jʊs.'t̪ɪ.kɪ̣.jar]")

    def test_lemmatizer(self):
        lupus = ["lupi", "luporum", "lupis", "lupos", "lupi", "lupis"]
        lemmas = wiring.cltk.latlemma.lemmatize(lupus)  # type: ignore

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
        result = wiring.cltk.latdict.lookup("saga")  # type: ignore

        somestr = """\
        sāga


         ae, 
        f

        sagus, prophetic; SAG-, 
        a wisewoman, fortune-teller, sooth-sayer, witch
        , H., O."""

        self.assertEqual(result, textwrap.dedent(somestr))

        # self.assertExpectedInline(somestr, """"")


class TestGreekSpacyMorphology(unittest.TestCase):
    def test_spacy_is_available(self):
        self.assertIsInstance(wiring.cltk.spacy_is_available(), bool)

    def test_greek_morphology_query(self):
        result = wiring.cltk.greek_morphology_query("λόγος")

        self.assertIsInstance(result.text, str)
        self.assertIsInstance(result.lemma, str)
        self.assertIsInstance(result.pos, str)
        self.assertIsInstance(result.morphological_features, dict)

    def test_greek_morphology_returns_valid_result(self):
        result = wiring.cltk.greek_morphology_query("λόγος")

        self.assertEqual(result.text, "λόγος")
        self.assertEqual(result.lemma, "λόγος")
        self.assertEqual(result.pos, "NOUN")
        self.assertIn("Case", result.morphological_features)
        self.assertIn("Gender", result.morphological_features)


# class TestCologneDigitalSanskritLexicon(unittest.TestCase):

#     def test_basic_dictionary(self):
#         results = wiring.cologne_dict.mw.search("राम")
#         meaning = "राम mf(आ/)n. (prob. ‘causing rest’, and in most meanings fr. √ रम्) dark, dark-coloured, black (cf. रात्रि), AV.; TĀr. (रामः शकुनिः. a black bird, crow, KāṭhGṛ.; Viṣṇ.)"
#         self.assertEqual(results[0].meaning(), meaning)


if __name__ == "__main__":
    unittest.main()
