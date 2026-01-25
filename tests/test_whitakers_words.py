import unittest
import time
import logging

from langnet.whitakers_words.core import (
    WhitakersWords,
    WhitakersWordsChunker,
    get_whitakers_proc,
)

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
        word_data = result.wordlist[0].model_dump()
        self.assertIn("terms", word_data)
        self.assertGreater(len(word_data["terms"]), 0)

    def test_verb_conjugation(self):
        result = WhitakersWords.words(["amo"])
        self.assertIsInstance(result, object)
        self.assertGreater(len(result.wordlist), 0)

    def test_adjective_comparison(self):
        result = WhitakersWords.words(["bonus"])
        self.assertIsInstance(result, object)
        self.assertGreater(len(result.wordlist), 0)

    def test_multiple_words_query(self):
        words = ["puella", "puer", "domus", "mensa"]
        result = WhitakersWords.words(words)
        self.assertGreater(len(result.wordlist), 3)

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
        word_data = result.wordlist[0].model_dump()
        terms = word_data.get("terms", [])
        self.assertGreater(len(terms), 0)
        first_term = terms[0]
        self.assertIn("declension", first_term)
        self.assertIn("part_of_speech", first_term)

    def test_codeline_parsing(self):
        result = WhitakersWords.words(["amo", "amare", "amavi", "amatus"])
        self.assertIsInstance(result, object)
        for word_data in result.wordlist:
            data = word_data.model_dump()
            if data.get("codeline") is not None:
                codeline = data["codeline"]
                self.assertIn("term", codeline)

    def test_senses_extraction(self):
        result = WhitakersWords.words(["lupus"])
        self.assertIsInstance(result, object)
        word_data = result.wordlist[0].model_dump()
        self.assertIn("senses", word_data)
        self.assertGreater(len(word_data["senses"]), 0)


if __name__ == "__main__":
    unittest.main()
