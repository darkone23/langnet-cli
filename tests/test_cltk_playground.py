import unittest
import time
import textwrap

from langnet.cologne.core import SanskritCologneLexicon
from langnet.classics_toolkit.core import ClassicsToolkit


class ClassicsWiring:

    def __init__(self):
        self.start = time.monotonic()
        print("Setting up classics wiring...")

        # print(self.lat_corpus.all_corpora_for_lang)
        self.cologne_dict = SanskritCologneLexicon()
        self.cltk = ClassicsToolkit()
        print(f"Startup time took {time.monotonic() - self.start}s")


wiring = (
    ClassicsWiring()
)  # this will prompt downloading language data from universities


class TestLatinExamples(unittest.TestCase):

    # import basic latin corpus

    def test_replacer(self):
        replaced = wiring.cltk.jvsub.replace("justiciar")
        self.assertEqual(replaced, "iusticiar")

    def test_transcriber(self):
        transcribed = wiring.cltk.latxform.transcribe("iusticiar")
        self.assertEqual(transcribed, "[jʊs.'t̪ɪ.kɪ̣.jar]")

    def test_lemmatizer(self):
        lupus = ["lupi", "luporum", "lupis", "lupos", "lupi", "lupis"]
        lemmas = wiring.cltk.latlemma.lemmatize(lupus)

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
        result = wiring.cltk.latdict.lookup("saga")

        somestr = """\
        sāga


         ae, 
        f

        sagus, prophetic; SAG-, 
        a wisewoman, fortune-teller, sooth-sayer, witch
        , H., O."""

        self.assertEqual(result, textwrap.dedent(somestr))

        # self.assertExpectedInline(somestr, """""")


# class TestCologneDigitalSanskritLexicon(unittest.TestCase):

#     def test_basic_dictionary(self):
#         results = wiring.cologne_dict.mw.search("राम")
#         meaning = "राम mf(आ/)n. (prob. ‘causing rest’, and in most meanings fr. √ रम्) dark, dark-coloured, black (cf. रात्रि), AV.; TĀr. (रामः शकुनिः. a black bird, crow, KāṭhGṛ.; Viṣṇ.)"
#         self.assertEqual(results[0].meaning(), meaning)


if __name__ == "__main__":
    unittest.main()
