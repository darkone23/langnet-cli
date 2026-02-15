import json
import time
import tracemalloc
import unittest
from pathlib import Path

from langnet.whitakers_words.lineparsers import CodesReducer


class TestCodesParser(unittest.TestCase):
    """Comprehensive test suite for the CodesParser"""

    FIXTURE_DIR = Path(__file__).parent / "fixtures" / "whitakers" / "term_codes"

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
        self.assertIsNotNone(CodesReducer.parser)
        self.assertIsNotNone(CodesReducer.xformer)

    def test_simple_cases(self):
        """Test simple parsing cases"""
        test_cases = [
            "basic_code_line",
            "proper_names",
            "with_notes",
            "full_indeclinable",
        ]

        for case_name in test_cases:
            with self.subTest(case=case_name):
                input_text, expected = self.load_fixture("simple", case_name)
                result = CodesReducer.reduce(input_text)
                self.assertEqual(result, expected)

    def test_edge_cases(self):
        """Test edge case scenarios"""
        test_cases = [
            "x_codes_discarded",
            "missing_codes",
            "complex_notes",
            "whitespace_variations",
        ]

        for case_name in test_cases:
            with self.subTest(case=case_name):
                input_text, expected = self.load_fixture("edge_cases", case_name)
                result = CodesReducer.reduce(input_text)
                self.assertEqual(result, expected)

    def test_golden_master(self):
        """Test against golden master fixtures"""
        golden_dir = self.FIXTURE_DIR / "golden"
        golden_file = golden_dir / "sampled_from_term_codes.json"

        with open(golden_file) as f:
            golden_fixtures = json.load(f)

        for i, fixture in enumerate(golden_fixtures):
            with self.subTest(fixture=f"line_{i:03d}"):
                input_text = fixture["input"]
                expected = fixture["expected"]

                result = CodesReducer.reduce(input_text)

                # Compare with expected structure
                self.assertEqual(result, expected, f"Failed on line {i}: {input_text}")

    def test_output_structure(self):
        """Test that output has the correct structure"""
        test_cases = [
            "amo, amare, amavi, amatus  V (1st)   [XXXAO]",
            "Caesar, Caesaris  N (3rd) M   [XLXBO]",
            "bellus, bella -um, bellior -or -us, bellissimus -a -um  ADJ   [XXXBO]",
        ]

        for line in test_cases:
            with self.subTest(line=line):
                result = CodesReducer.reduce(line)

                # Basic structure validation
                self.assertIsInstance(result, dict)

                # Check for expected fields
                if "term" in result:
                    self.assertIsInstance(result["term"], str)

                if "pos_code" in result:
                    self.assertIsInstance(result["pos_code"], str)

                if "declension" in result:
                    self.assertIsInstance(result["declension"], str)

                if "names" in result:
                    self.assertIsInstance(result["names"], list)

                if "notes" in result:
                    self.assertIsInstance(result["notes"], list)

    def test_x_codes_discarded(self):
        """Test that X codes are properly handled"""
        line = "mare  X   [XXXFO]    veryrare"
        result = CodesReducer.reduce(line)

        # X codes are not discarded, they're still parsed
        self.assertIsInstance(result, dict)
        self.assertIn("term", result)
        self.assertIn("pos_code", result)
        self.assertEqual(result["term"], "mare")
        self.assertEqual(result["pos_code"], "X")

    def test_proper_names_parsing(self):
        """Test proper names parsing"""
        line = "Caesar, Caesaris  N (3rd) M   [XLXBO]"
        result = CodesReducer.reduce(line)

        self.assertIsInstance(result, dict)
        self.assertIn("names", result)
        self.assertIn("pos_code", result)
        self.assertIn("declension", result)

        self.assertEqual(result["names"], ["Caesar", "Caesaris"])
        self.assertEqual(result["pos_code"], "N")
        self.assertEqual(result["declension"], "3rd")

    def test_codes_parsing(self):
        """Test code parsing (age, area, geo, freq, source)"""
        line = "Caesar, Caesaris  N (3rd) M   [XLXBO]"
        result = CodesReducer.reduce(line)

        self.assertIsInstance(result, dict)

        # Check that codes are parsed
        expected_codes = ["L", "B", "O"]  # area, freq, source (age/geo not present)
        code_fields = ["area", "freq", "source"]

        for field, expected_code in zip(code_fields, expected_codes):
            self.assertIn(field, result)
            self.assertEqual(result[field], expected_code)

    def test_missing_fields_handling(self):
        """Test handling of missing optional fields"""
        line = "word  N (3rd)    [XXXAO]"  # Missing some codes
        result = CodesReducer.reduce(line)

        self.assertIsInstance(result, dict)
        # Should still parse what it can
        self.assertIn("term", result)
        self.assertIn("pos_code", result)

    def test_whitespace_variations(self):
        """Test handling of different whitespace patterns"""
        line = "Caesar, Caesaris  N  (3rd)  M  [XXXAO]"
        result = CodesReducer.reduce(line)

        self.assertIsInstance(result, dict)
        # Should parse correctly despite extra whitespace
        self.assertIn("names", result)
        self.assertIn("pos_code", result)
        self.assertIn("declension", result)
        self.assertIn("pos_form", result)

    def test_notes_parsing(self):
        """Test notes parsing"""
        line = "bellus, bella -um, bellior -or -us, bellissimus -a -um  ADJ   [XXXBO]  note1 note2"
        result = CodesReducer.reduce(line)

        self.assertIsInstance(result, dict)
        self.assertIn("notes", result)
        self.assertIsInstance(result["notes"], list)
        self.assertEqual(len(result["notes"]), 2)
        self.assertIn("note1", result["notes"])
        self.assertIn("note2", result["notes"])

    def test_indeclinable_words(self):
        """Test parsing of indeclinable words"""
        line = "ne, non  ADV   [XXXAO]  neg"
        result = CodesReducer.reduce(line)

        self.assertIsInstance(result, dict)
        self.assertIn("term", result)
        self.assertIn("pos_code", result)
        self.assertEqual(result["term"], "ne, non")
        self.assertEqual(result["pos_code"], "ADV")

    def test_empty_input_handling(self):
        """Test handling of empty input"""
        # Empty string
        with self.assertRaises(Exception):
            CodesReducer.reduce("")

        # Invalid format
        with self.assertRaises(Exception):
            CodesReducer.reduce("invalid format")

    def test_performance_large_input(self):
        """Test performance with large input"""
        # Use a valid complex line
        line = (
            "bellus, bella -um, bellior -or -us, bellissimus -a -um  ADJ   [XXXBO]  "
            "note1 note2 note3"
        )

        # Should not take too long
        start_time = time.time()
        result = CodesReducer.reduce(line)
        end_time = time.time()

        self.assertLess(end_time - start_time, 1.0)  # Should complete in <1 second
        self.assertIsInstance(result, dict)

    def test_memory_usage(self):
        """Test memory usage efficiency"""
        tracemalloc.start()

        # Parse multiple lines
        lines = [
            "amo, amare, amavi, amatus  V (1st)   [XXXAO]",
            "Caesar, Caesaris  N (3rd) M   [XLXBO]",
            "bellus, bella -um, bellior -or -us, bellissimus -a -um  ADJ   [XXXBO]",
        ]

        for line in lines:
            CodesReducer.reduce(line)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Should not use excessive memory
        self.assertLess(peak, 10 * 1024 * 1024)  # <10MB peak memory

    def test_data_validation(self):
        """Test that parsed data has reasonable values"""
        line = "Caesar, Caesaris  N (3rd) M   [XLXBO]"
        result = CodesReducer.reduce(line)

        # Validate field types and values
        if "term" in result:
            self.assertIsInstance(result["term"], str)
            self.assertGreater(len(result["term"]), 0)

        if "pos_code" in result:
            self.assertIsInstance(result["pos_code"], str)
            self.assertIn(result["pos_code"], ["N", "V", "ADJ", "ADV", "PRON", "PREP", "CONJ"])

        if "declension" in result:
            self.assertIsInstance(result["declension"], str)
            self.assertRegex(result["declension"], r"\d+[sthnrd]{2}")

        if "names" in result:
            self.assertIsInstance(result["names"], list)
            for name in result["names"]:
                self.assertIsInstance(name, str)
                self.assertGreater(len(name), 0)


if __name__ == "__main__":
    unittest.main()
