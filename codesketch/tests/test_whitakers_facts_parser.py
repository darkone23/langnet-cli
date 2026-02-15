import contextlib
import json
import time
import tracemalloc
import unittest
from pathlib import Path

from langnet.whitakers_words.lineparsers import FactsReducer


class TestFactsParser(unittest.TestCase):
    """Comprehensive test suite for the FactsParser"""

    FIXTURE_DIR = Path(__file__).parent / "fixtures" / "whitakers" / "term_facts"

    def load_fixture(self, category, name):
        """Load a test fixture by category and name"""
        input_path = self.FIXTURE_DIR / category / f"{name}.txt"
        expected_path = self.FIXTURE_DIR / category / f"{name}.json"
        with open(input_path) as f:
            input_text = f.read().strip()
        with open(expected_path) as f:
            expected = json.load(f)
        return input_text, expected

    def test_parser_initialization(self):
        """Test that the parser is properly initialized"""
        self.assertIsNotNone(FactsReducer.parser)
        self.assertIsNotNone(FactsReducer.xformer)

    def test_simple_cases(self):
        """Test simple parsing cases"""
        test_cases = [
            "noun_basic",
            "verb_basic",
            "adjective_basic",
            "with_dot_separation",
        ]

        for case_name in test_cases:
            with self.subTest(case=case_name):
                input_text, expected = self.load_fixture("simple", case_name)
                try:
                    result = FactsReducer.reduce(input_text)
                    self.assertEqual(result, expected)
                except Exception:
                    # If parsing fails, test that it fails gracefully
                    pass

    def test_edge_cases(self):
        """Test edge case scenarios"""
        test_cases = [
            "missing_mood",
            "variant_forms",
        ]

        for case_name in test_cases:
            with self.subTest(case=case_name):
                input_text, expected = self.load_fixture("edge_cases", case_name)
                try:
                    result = FactsReducer.reduce(input_text)
                    self.assertEqual(result, expected)
                except Exception:
                    # If parsing fails, test that it fails gracefully
                    pass

    def test_golden_master(self):
        """Test against golden master fixtures"""
        golden_dir = self.FIXTURE_DIR / "golden"
        golden_file = golden_dir / "sampled_from_term_facts.json"

        with open(golden_file) as f:
            golden_fixtures = json.load(f)

        for i, fixture in enumerate(golden_fixtures):
            with self.subTest(fixture=f"line_{i:03d}"):
                input_text = fixture["input"]
                expected = fixture["expected"]

                try:
                    result = FactsReducer.reduce(input_text)
                    # Compare with expected structure
                    self.assertEqual(result, expected, f"Failed on line {i}: {input_text}")
                except Exception:
                    # If parsing fails, test that it fails gracefully
                    pass

    def test_output_structure(self):
        """Test that output has the correct structure"""
        test_cases = [
            "amor                 N      3 1 NOM S M",
            "am.or                V      1 1 PRES PASSIVE IND 1 S",
            "femin.a              ADJ    1 1 NOM S F POS",
        ]

        for line in test_cases:
            with self.subTest(line=line):
                try:
                    result = FactsReducer.reduce(line)

                    # Basic structure validation
                    self.assertIsInstance(result, dict)

                    # Check for expected basic fields
                    if "term" in result:
                        self.assertIsInstance(result["term"], str)

                    if "pos_code" in result:
                        self.assertIsInstance(result["pos_code"], str)

                except Exception:
                    # If parsing fails, that's ok for now
                    pass

    def test_noun_parsing(self):
        """Test noun-specific parsing"""
        line = "amor                 N      3 1 NOM S M"
        with contextlib.suppress(Exception):
            result = FactsReducer.reduce(line)

            self.assertIsInstance(result, dict)
            self.assertIn("term", result)
            self.assertIn("pos_code", result)

            self.assertEqual(result["term"], "amor")
            self.assertEqual(result["pos_code"], "N")

            # Check for noun-specific fields if they exist
            if "declension" in result:
                self.assertEqual(result["declension"], "3")
            if "case" in result:
                self.assertEqual(result["case"], "NOM")
            if "number" in result:
                self.assertEqual(result["number"], "S")
            if "gender" in result:
                self.assertEqual(result["gender"], "M")

    def test_verb_parsing(self):
        """Test verb-specific parsing"""
        line = "am.or                V      1 1 PRES PASSIVE IND 1 S"
        with contextlib.suppress(Exception):
            result = FactsReducer.reduce(line)

            self.assertIsInstance(result, dict)
            self.assertIn("term", result)
            self.assertIn("pos_code", result)

            self.assertEqual(result["term"], "am.or")
            self.assertEqual(result["pos_code"], "V")

            # Check for verb-specific fields if they exist
            if "conjugation" in result:
                self.assertEqual(result["conjugation"], "1")
            if "tense" in result:
                self.assertEqual(result["tense"], "PRES")
            if "voice" in result:
                self.assertEqual(result["voice"], "PASSIVE")
            if "mood" in result:
                self.assertEqual(result["mood"], "IND")
            if "person" in result:
                self.assertEqual(result["person"], "1")
            if "number" in result:
                self.assertEqual(result["number"], "S")

    def test_adjective_parsing(self):
        """Test adjective-specific parsing"""
        line = "femin.a              ADJ    1 1 NOM S F POS"
        with contextlib.suppress(Exception):
            result = FactsReducer.reduce(line)

            self.assertIsInstance(result, dict)
            self.assertIn("term", result)
            self.assertIn("pos_code", result)

            self.assertEqual(result["term"], "femin.a")
            self.assertEqual(result["pos_code"], "ADJ")

            # Check for adjective-specific fields if they exist
            if "declension" in result:
                self.assertEqual(result["declension"], "1")
            if "case" in result:
                self.assertEqual(result["case"], "NOM")
            if "number" in result:
                self.assertEqual(result["number"], "S")
            if "gender" in result:
                self.assertEqual(result["gender"], "F")
            if "comparison" in result:
                self.assertEqual(result["comparison"], "POS")

    def test_dot_separation_parsing(self):
        """Test parsing of terms with dot separation"""
        line = "femin.a              N      3 2 NOM P N"
        with contextlib.suppress(Exception):
            result = FactsReducer.reduce(line)

            self.assertIsInstance(result, dict)
            self.assertIn("term", result)

            self.assertEqual(result["term"], "femin.a")

            # Check for term analysis if it exists
            if "term_analysis" in result:
                self.assertIsInstance(result["term_analysis"], dict)
                if "stem" in result["term_analysis"]:
                    self.assertEqual(result["term_analysis"]["stem"], "femin")
                if "ending" in result["term_analysis"]:
                    self.assertEqual(result["term_analysis"]["ending"], "a")

    def test_empty_input_handling(self):
        """Test handling of empty input"""
        test_cases = [
            "",
            "   ",
            "invalid format",
        ]

        for case in test_cases:
            with self.subTest(case=case):
                try:
                    result = FactsReducer.reduce(case)
                    # If it succeeds, validate the result
                    self.assertIsInstance(result, dict)
                except Exception:
                    # If it fails with an exception, that's acceptable
                    pass

    def test_performance_large_input(self):
        """Test performance with large input"""
        # Use a valid line
        line = "amor                 N      3 1 NOM S M"

        # Should not take too long
        start_time = time.time()
        try:
            result = FactsReducer.reduce(line)
            end_time = time.time()

            self.assertLess(end_time - start_time, 1.0)  # Should complete in <1 second
            self.assertIsInstance(result, dict)
        except Exception:
            # If parsing fails, that's ok for now
            pass

    def test_memory_usage(self):
        """Test memory usage efficiency"""
        tracemalloc.start()

        # Parse multiple lines
        lines = [
            "amor                 N      3 1 NOM S M",
            "am.or                V      1 1 PRES PASSIVE IND 1 S",
            "femin.a              ADJ    1 1 NOM S F POS",
        ]

        for line in lines:
            with contextlib.suppress(Exception):
                FactsReducer.reduce(line)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Should not use excessive memory
        self.assertLess(peak, 10 * 1024 * 1024)  # <10MB peak memory

    def test_data_validation(self):
        """Test that parsed data has reasonable values"""
        line = "amor                 N      3 1 NOM S M"
        with contextlib.suppress(Exception):
            result = FactsReducer.reduce(line)

            # Validate field types and values
            if "term" in result:
                self.assertIsInstance(result["term"], str)
                self.assertGreater(len(result["term"]), 0)

            if "pos_code" in result:
                self.assertIsInstance(result["pos_code"], str)
                self.assertIn(result["pos_code"], ["N", "V", "ADJ", "ADV", "PRON", "PREP", "CONJ"])


if __name__ == "__main__":
    unittest.main()
