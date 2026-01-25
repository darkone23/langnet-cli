import unittest
import time
import logging

from langnet.whitakers_words.core import (
    WhitakersWords,
    WhitakersWordsChunker,
    WhitakersWordsT,
    get_whitakers_proc,
)
import cattrs

logging.getLogger("urllib3.connection").setLevel(logging.ERROR)


class WhitakersWiring:
    def __init__(self):
        self.start = time.monotonic()
        print("Setting up whitakers wiring...")
        self.ww_proc = get_whitakers_proc()
        print(f"Startup time took {time.monotonic() - self.start}s")


wiring = WhitakersWiring()


class TestWhitakersWords(unittest.TestCase):
    def test_single_noun_lookup(self):
        result = WhitakersWords.words(["lupus"])
        self.assertIsInstance(result, object)
        self.assertGreater(len(result.wordlist), 0)
        self.assertIsInstance(result.wordlist[0], WhitakersWordsT)
        word_data = cattrs.unstructure(result.wordlist[0])
        self.assertIn("terms", word_data)
        self.assertGreater(len(word_data["terms"]), 0)

    def test_verb_conjugation(self):
        result = WhitakersWords.words(["amo"])
        self.assertIsInstance(result, object)
        self.assertGreater(len(result.wordlist), 0)
        self.assertIsInstance(result.wordlist[0], WhitakersWordsT)

    def test_adjective_comparison(self):
        result = WhitakersWords.words(["bonus"])
        self.assertIsInstance(result, object)
        self.assertGreater(len(result.wordlist), 0)
        self.assertIsInstance(result.wordlist[0], WhitakersWordsT)

    def test_multiple_words_query(self):
        words = ["puella", "puer", "domus", "mensa"]
        result = WhitakersWords.words(words)
        self.assertGreater(len(result.wordlist), 3)
        for word in result.wordlist:
            self.assertIsInstance(word, WhitakersWordsT)

    def test_unknown_word_handling(self):
        result = WhitakersWords.words(["xyznonexistentword123"])
        self.assertIsInstance(result, object)

    def test_chunker_parses_output(self):
        chunker = WhitakersWordsChunker(["lupus"])
        chunks = chunker.get_word_chunks()
        self.assertIsInstance(chunks, list)
        self.assertGreater(len(chunks), 0)

    def test_whitakers_proc_is_available(self):
        proc = get_whitakers_proc()
        self.assertIsNotNone(proc)

    def test_word_has_morphological_data(self):
        result = WhitakersWords.words(["lupus"])
        self.assertIsInstance(result.wordlist[0], WhitakersWordsT)
        word_data = cattrs.unstructure(result.wordlist[0])
        terms = word_data.get("terms", [])
        self.assertGreater(len(terms), 0)
        first_term = terms[0]
        self.assertIn("declension", first_term)
        self.assertIn("part_of_speech", first_term)

    def test_codeline_parsing(self):
        result = WhitakersWords.words(["amo", "amare", "amavi", "amatus"])
        self.assertIsInstance(result, object)
        for word_data in result.wordlist:
            self.assertIsInstance(word_data, WhitakersWordsT)
            data = cattrs.unstructure(word_data)
            if data.get("codeline") is not None:
                codeline = data["codeline"]
                self.assertIn("term", codeline)

    def test_senses_extraction(self):
        result = WhitakersWords.words(["lupus"])
        self.assertIsInstance(result, object)
        self.assertIsInstance(result.wordlist[0], WhitakersWordsT)
        word_data = cattrs.unstructure(result.wordlist[0])
        self.assertIn("senses", word_data)
        self.assertGreater(len(word_data["senses"]), 0)

    def test_lupus_golden_master(self):
        result = WhitakersWords.words(["lupus"])
        self.assertEqual(len(result.wordlist), 1)
        word = result.wordlist[0]
        self.assertIsInstance(word, WhitakersWordsT)
        self.assertEqual(len(word.terms), 1)
        self.assertEqual(word.terms[0].term, "lup.us")
        self.assertEqual(word.terms[0].part_of_speech, "noun")
        self.assertIsNotNone(word.codeline)
        self.assertEqual(word.codeline.term, "lupus, lupi")
        self.assertEqual(word.senses, ["wolf", "grappling iron"])


if __name__ == "__main__":
    unittest.main()
