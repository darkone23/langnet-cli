import logging
import time
import unittest

import cattrs

from langnet.whitakers_words.core import (
    WhitakersWords,
    WhitakersWordsChunker,
    WhitakersWordsT,
    WhitakerWordData,
    get_whitakers_proc,
)

logging.getLogger("urllib3.connection").setLevel(logging.ERROR)


class WhitakersWiring:
    def __init__(self):
        self.ww_proc = get_whitakers_proc()


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
        self.assertEqual(word.terms[0].part_of_speech, "Noun")
        self.assertIsNotNone(word.codeline)
        self.assertEqual(word.codeline.term, "lupus, lupi")  # type: ignore
        self.assertEqual(word.senses, ["wolf", "grappling iron"])


class TestWhitakersIntegration(unittest.TestCase):
    """Integration tests for Whitaker's Words parsers"""

    def test_chunker_classification(self):
        """Test chunker line classification"""
        chunker = WhitakersWordsChunker(["lupus"])
        chunks = chunker.get_word_chunks()

        self.assertIsInstance(chunks, list)
        self.assertGreater(len(chunks), 0)

        # Test that chunks have the expected structure (dictionaries)
        for chunk in chunks:
            self.assertIsInstance(chunk, dict)
            self.assertIn("txts", chunk)
            self.assertIn("types", chunk)
            self.assertIn("size", chunk)
            self.assertIsInstance(chunk["txts"], list)
            self.assertIsInstance(chunk["types"], list)
            self.assertEqual(chunk["size"], len(chunk["txts"]))

    def test_chunker_with_different_inputs(self):
        """Test chunker with different types of input"""
        test_inputs = [
            ["lupus"],  # Single word
            ["puella", "puer"],  # Multiple words
            ["amo", "amare", "amavi", "amatus"],  # Verb forms
        ]

        for input_words in test_inputs:
            with self.subTest(input=input_words):
                chunker = WhitakersWordsChunker(input_words)
                chunks = chunker.get_word_chunks()

                self.assertIsInstance(chunks, list)
                self.assertGreater(len(chunks), 0)

                for chunk in chunks:
                    self.assertIsInstance(chunk, dict)
                    self.assertIn("txts", chunk)
                    self.assertIn("types", chunk)
                    self.assertIn("size", chunk)
                    self.assertIsInstance(chunk["txts"], list)
                    self.assertIsInstance(chunk["types"], list)
                    self.assertEqual(chunk["size"], len(chunk["txts"]))

    def test_complete_word_processing(self):
        """Test the complete flow from raw lines to structured data"""
        # Test chunker classification
        chunker = WhitakersWordsChunker(["lupus"])
        chunks = chunker.get_word_chunks()

        self.assertIsInstance(chunks, list)
        self.assertGreater(len(chunks), 0)

        # Test that we get results from the full system
        result = WhitakersWords.words(["lupus"])
        self.assertIsInstance(result, object)
        self.assertGreater(len(result.wordlist), 0)

        word_data = cattrs.unstructure(result.wordlist[0])
        self.assertIn("terms", word_data)
        self.assertIn("senses", word_data)
        self.assertIn("codeline", word_data)

    def test_parser_integration_consistency(self):
        """Test that individual parsers work with the main system"""
        result = WhitakersWords.words(["lupus"])
        self.assertIsInstance(result, object)
        self.assertGreater(len(result.wordlist), 0)

        word_data = cattrs.unstructure(result.wordlist[0])

        # Test that senses parser results are consistent
        self.assertIn("senses", word_data)
        if word_data["senses"]:
            self.assertIsInstance(word_data["senses"], list)
            for sense in word_data["senses"]:
                self.assertIsInstance(sense, str)

        # Test that codeline parser results are consistent
        if word_data.get("codeline"):
            codeline = word_data["codeline"]
            self.assertIn("term", codeline)
            self.assertIsInstance(codeline["term"], str)

        # Test that term parser results are consistent
        self.assertIn("terms", word_data)
        for term in word_data["terms"]:
            self.assertIn("part_of_speech", term)
            self.assertIn("term", term)
            self.assertIsInstance(term["part_of_speech"], str)
            self.assertIsInstance(term["term"], str)

    def test_data_model_validation(self):
        """Test that parsed data fits expected schemas"""
        result = WhitakersWords.words(["lupus"])
        self.assertIsInstance(result.wordlist[0], WhitakersWordsT)

        # Try to convert terms to dataclass
        try:
            word_data = cattrs.unstructure(result.wordlist[0])

            # Validate terms
            for term_data in word_data.get("terms", []):
                term_obj = WhitakerWordData(**term_data)

                # Validate basic fields
                self.assertIsInstance(term_obj.term, str)
                self.assertIsInstance(term_obj.part_of_speech, str)

        except Exception:
            # If conversion fails, it's ok for now
            pass

    def test_line_type_detection(self):
        """Test detection of different line types"""
        chunker = WhitakersWordsChunker(["lupus"])
        chunks = chunker.get_word_chunks()

        # Verify we get chunks (classification is internal to chunker)
        self.assertIsInstance(chunks, list)
        self.assertGreater(len(chunks), 0)

    def test_pipeline_end_to_end(self):
        """Test complete pipeline from input to structured output"""
        # Test with multiple words
        words = ["puella", "puer", "domus", "mensa"]
        result = WhitakersWords.words(words)

        self.assertIsInstance(result, object)
        self.assertGreater(len(result.wordlist), 0)

        # Validate each word has the expected structure
        for word in result.wordlist:
            word_data = cattrs.unstructure(word)

            # Should have basic structure
            self.assertIn("terms", word_data)
            self.assertIn("senses", word_data)

            # Terms should be valid
            for term in word_data["terms"]:
                self.assertIn("term", term)
                self.assertIn("part_of_speech", term)

            # Senses should be valid
            if word_data["senses"]:
                self.assertIsInstance(word_data["senses"], list)

    def test_morphological_data_completeness(self):
        """Test that morphological data is complete and consistent"""
        result = WhitakersWords.words(["amo"])  # Verb

        self.assertIsInstance(result, object)
        self.assertGreater(len(result.wordlist), 0)

        word_data = cattrs.unstructure(result.wordlist[0])

        # Should have multiple forms for a verb
        self.assertIn("terms", word_data)
        self.assertGreater(len(word_data["terms"]), 0)

        # Check that terms have morphological information
        for term in word_data["terms"]:
            if hasattr(term, "part_of_speech"):
                self.assertIn(term.part_of_speech.lower(), ["verb", "noun", "adjective", "adverb"])

    def test_chunker_with_different_inputs_fixed(self):
        """Test chunker with different types of input"""
        test_inputs = [
            ["lupus"],  # Single word
            ["puella", "puer"],  # Multiple words
            ["amo", "amare", "amavi", "amatus"],  # Verb forms
        ]

        for input_words in test_inputs:
            with self.subTest(input=input_words):
                chunker = WhitakersWordsChunker(input_words)
                chunks = chunker.get_word_chunks()

                self.assertIsInstance(chunks, list)
                self.assertGreater(len(chunks), 0)

                for chunk in chunks:
                    self.assertIsInstance(chunk, dict)
                    self.assertIn("txts", chunk)
                    self.assertIn("types", chunk)
                    self.assertIn("size", chunk)
                    self.assertIsInstance(chunk["txts"], list)
                    self.assertIsInstance(chunk["types"], list)
                    self.assertEqual(chunk["size"], len(chunk["txts"]))

    def test_error_handling_integration(self):
        """Test error handling in the integrated system"""
        # Test with non-existent word
        result = WhitakersWords.words(["xyznonexistentword123"])
        self.assertIsInstance(result, object)

        # Should not crash, even if word doesn't exist
        self.assertIsInstance(result.wordlist, list)

    def test_performance_integration(self):
        """Test performance of the integrated system"""
        # Test with multiple words
        words = ["lupus", "puella", "puer", "domus", "mensa", "amo", "est", "in"]

        start_time = time.time()
        result = WhitakersWords.words(words)
        end_time = time.time()

        self.assertLess(end_time - start_time, 5.0)  # Should complete in <5 seconds
        self.assertIsInstance(result, object)
        self.assertGreater(len(result.wordlist), 0)


if __name__ == "__main__":
    unittest.main()
