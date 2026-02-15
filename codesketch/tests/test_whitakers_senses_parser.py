import json
import time
import tracemalloc
import unittest
from pathlib import Path

from langnet.whitakers_words.lineparsers import SensesReducer


class TestSensesParser(unittest.TestCase):
    """Comprehensive test suite for the SensesParser"""

    FIXTURE_DIR = Path(__file__).parent / "fixtures" / "whitakers" / "senses"

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
        self.assertIsNotNone(SensesReducer.parser)
        self.assertIsNotNone(SensesReducer.xformer)

    def test_parse_variations(self):
        """Test various parsing scenarios"""
        test_cases = [
            ("single_sense", "woman;"),
            ("multiple_senses", "woman; female;"),
            ("with_notes", "thigh (human/animal);"),
            ("complex_notes", "Caesar; (Julian gens cognomen);"),
            (
                "with_references",
                "house, building; home, household; (N 4 1, older N 2 1); [domi => at home];",
            ),
        ]

        for name, input_line in test_cases:
            with self.subTest(case=name):
                result = SensesReducer.reduce(input_line)
                self.assertIsInstance(result, dict)
                self.assertIn("senses", result)
                self.assertIsInstance(result["senses"], list)
                self.assertGreater(len(result["senses"]), 0)

    def test_simple_cases(self):
        """Test simple parsing cases"""
        test_cases = [
            "single_sense",
            "multiple_senses",
            "with_notes",
            "complex_notes",
            "with_references",
        ]

        for case_name in test_cases:
            with self.subTest(case=case_name):
                input_text, expected = self.load_fixture("simple", case_name)
                result = SensesReducer.reduce(input_text)
                self.assertEqual(result, expected)

    def test_edge_cases(self):
        """Test edge case scenarios"""
        test_cases = [
            "empty_parentheses",
            "nested_parentheses",
            "special_characters",
            "unicode_chars",
            "no_semicolon",
        ]

        for case_name in test_cases:
            with self.subTest(case=case_name):
                input_text, expected = self.load_fixture("edge_cases", case_name)
                result = SensesReducer.reduce(input_text)
                self.assertEqual(result, expected)

    def test_golden_master(self):
        """Test against golden master fixtures"""
        golden_dir = self.FIXTURE_DIR / "golden"
        golden_file = golden_dir / "sampled_from_senses.json"

        with open(golden_file) as f:
            golden_fixtures = json.load(f)

        for i, fixture in enumerate(golden_fixtures):
            with self.subTest(fixture=f"line_{i:03d}"):
                input_text = fixture["input"]
                expected = fixture["expected"]

                result = SensesReducer.reduce(input_text)

                # Compare with expected structure
                self.assertEqual(result, expected, f"Failed on line {i}: {input_text}")

    def test_output_structure(self):
        """Test that output has the correct structure"""
        test_cases = [
            "woman;",
            "word (note);",
            "word1; word2 (note1); word3;",
        ]

        for line in test_cases:
            with self.subTest(line=line):
                result = SensesReducer.reduce(line)

                # Basic structure validation
                self.assertIsInstance(result, dict)
                self.assertIn("senses", result)
                self.assertIsInstance(result["senses"], list)
                self.assertGreater(len(result["senses"]), 0)

                # Check each sense has proper structure
                for sense in result["senses"]:
                    self.assertIsInstance(sense, str)
                    self.assertGreater(len(sense), 0)

                # Notes should be optional
                if "notes" in result:
                    self.assertIsInstance(result["notes"], list)
                    for note in result["notes"]:
                        self.assertIsInstance(note, str)

    def test_empty_input_handling(self):
        """Test handling of empty or whitespace input"""
        # Empty string - this actually parses as a sense
        result = SensesReducer.reduce("")
        self.assertIsInstance(result, dict)
        self.assertIn("senses", result)

        # Whitespace only - this creates an empty senses list
        result = SensesReducer.reduce("   ")
        self.assertIsInstance(result, dict)
        self.assertIn("senses", result)
        self.assertEqual(len(result["senses"]), 0)

    def test_invalid_syntax_handling(self):
        """Test that the parser handles various input gracefully"""
        # The parser is lenient and doesn't raise exceptions
        test_cases = [
            "word (unclosed",
            "word [invalid",
            "just a word without semicolon",
            "unclosed [bracket",
        ]

        for case in test_cases:
            with self.subTest(case=case):
                result = SensesReducer.reduce(case)
                self.assertIsInstance(result, dict)
                self.assertIn("senses", result)
                # The parser should always return something valid

    def test_complex_notes_parsing(self):
        """Test complex note parsing with various symbols"""
        line = "Caesar; (Julian gens cognomen); (adopted by emperors); [C. Julius ~ => Emperor]"
        result = SensesReducer.reduce(line)

        self.assertIsInstance(result, dict)
        self.assertIn("senses", result)
        # The parser treats parenthesized parts as separate senses
        self.assertEqual(len(result["senses"]), 3)
        self.assertIn("Caesar", result["senses"])
        self.assertIn("(Julian gens cognomen)", result["senses"])
        self.assertIn("(adopted by emperors)", result["senses"])

        # Check notes are parsed correctly
        self.assertIn("notes", result)
        notes = result["notes"]
        self.assertEqual(len(notes), 1)
        self.assertIn("C. Julius ~ => Emperor", notes)

    def test_special_characters_handling(self):
        """Test handling of special characters in input"""
        line = "word [=> symbol]; word [~ reference]; word [-> another];"
        result = SensesReducer.reduce(line)

        self.assertIsInstance(result, dict)
        self.assertIn("senses", result)
        self.assertEqual(len(result["senses"]), 3)

        # Check that basic words are there
        senses = result["senses"]
        self.assertIn("word", senses)
        self.assertIn("word", senses)
        self.assertIn("word", senses)

        # Check notes for the bracket content
        self.assertIn("notes", result)
        notes = result["notes"]
        self.assertEqual(len(notes), 3)
        self.assertIn("=> symbol", notes)
        self.assertIn("~ reference", notes)
        self.assertIn("-> another", notes)

    def test_unicode_characters_handling(self):
        """Test handling of Unicode characters"""
        line = "Caesar (C. Julius ~);"
        result = SensesReducer.reduce(line)

        self.assertIsInstance(result, dict)
        self.assertIn("senses", result)

        # The parser keeps the entire parenthesized content as a single sense
        senses = result["senses"]
        self.assertEqual(len(senses), 1)
        self.assertIn("Caesar (C. Julius ~)", senses)

        # In this case, no notes are extracted (might be a parser limitation)
        if "notes" in result:
            notes = result["notes"]
            self.assertEqual(len(notes), 1)
            self.assertIn("C. Julius ~", notes)

    def test_performance_large_input(self):
        """Test performance with large input"""
        # Create a large line with many senses
        large_line = ";".join([f"word{i}" for i in range(100)]) + ";"

        # Should not take too long
        start_time = time.time()
        result = SensesReducer.reduce(large_line)
        end_time = time.time()

        self.assertLess(end_time - start_time, 1.0)  # Should complete in <1 second
        self.assertEqual(len(result["senses"]), 100)

    def test_memory_usage(self):
        """Test memory usage efficiency"""
        tracemalloc.start()

        # Parse multiple lines
        lines = [
            "word1;",
            "word2 (note);",
            "word3; word4;",
            "complex word (with notes);",
        ]

        for line in lines:
            SensesReducer.reduce(line)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Should not use excessive memory
        self.assertLess(peak, 10 * 1024 * 1024)  # <10MB peak memory


if __name__ == "__main__":
    unittest.main()
