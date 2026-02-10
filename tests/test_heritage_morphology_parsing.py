#!/usr/bin/env python3
"""
Test suite for Heritage Platform morphology parsing
"""

import json
import unittest
from pathlib import Path

from langnet.heritage.html_extractor import HeritageHTMLExtractor
from langnet.heritage.lineparsers.parse_morphology import MorphologyReducer
from langnet.heritage.parsers import MorphologyParser


class TestHeritageMorphologyParser(unittest.TestCase):
    """Comprehensive test suite for Heritage morphology parser"""

    FIXTURE_DIR = Path(__file__).parent / "fixtures" / "heritage" / "morphology"

    def load_fixture(self, category, name):
        """Load a test fixture by category and name"""
        input_path = self.FIXTURE_DIR / category / f"{name}.txt"
        expected_path = self.FIXTURE_DIR / category / f"{name}.json"
        with open(input_path) as f:
            input_html = f.read()
        with open(expected_path) as f:
            expected = json.load(f)
        return input_html, expected

    def test_parser_initialization(self):
        """Test that the parser is properly initialized"""
        parser = MorphologyParser()
        self.assertIsNotNone(parser)
        self.assertTrue(parser.use_new_parser)

    def test_text_description_analysis(self):
        """Test parsing of text-based morphological descriptions"""
        input_html, expected = self.load_fixture("simple", "text_description")
        parser = MorphologyParser()
        result = parser.parse(input_html)

        self.assertEqual(result["total_solutions"], 1)
        self.assertEqual(len(result["solutions"]), 1)

        solution = result["solutions"][0]
        self.assertEqual(solution["total_words"], 1)  # type: ignore[index]

        analysis = solution["analyses"][0]  # type: ignore[index]
        self.assertEqual(analysis.word, "yoga")
        self.assertEqual(analysis.pos, "noun")
        self.assertEqual(analysis.gender, "masculine")
        self.assertEqual(analysis.number, "singular")
        self.assertEqual(analysis.case, "vocative")

    def test_unknown_analysis(self):
        """Test parsing of unknown analysis patterns"""
        input_html, expected = self.load_fixture("simple", "unknown_analysis")
        parser = MorphologyParser()
        result = parser.parse(input_html)

        self.assertEqual(result["total_solutions"], 1)
        solution = result["solutions"][0]
        analysis = solution["analyses"][0]  # type: ignore[index]

        self.assertEqual(analysis.word, "agni")
        self.assertEqual(analysis.pos, "unknown")
        self.assertIsNone(analysis.gender)
        self.assertIsNone(analysis.number)
        self.assertIsNone(analysis.case)

    def test_verb_form_analysis(self):
        """Test parsing of verb forms with person/tense/mood"""
        input_html, expected = self.load_fixture("simple", "verb_form")
        parser = MorphologyParser()
        result = parser.parse(input_html)

        self.assertEqual(result["total_solutions"], 1)
        solution = result["solutions"][0]
        analysis = solution["analyses"][0]  # type: ignore[index]

        self.assertEqual(analysis.word, "bhavati")
        self.assertEqual(analysis.pos, "verb")
        self.assertEqual(analysis.person, 3)
        self.assertEqual(analysis.number, "singular")
        self.assertEqual(analysis.tense, "present")
        self.assertEqual(analysis.voice, "active")
        self.assertEqual(analysis.mood, "indicative")

    def test_multiple_solution_sections(self):
        """Parser should respect multiple solution blocks in HTML"""
        fixture_path = self.FIXTURE_DIR / "agnii_morph.html"
        input_html = fixture_path.read_text()
        parser = MorphologyParser()

        result = parser.parse(input_html)

        self.assertEqual(result["total_solutions"], 2)
        self.assertEqual(len(result["solutions"]), 2)

        first_solution = result["solutions"][0]
        self.assertEqual(first_solution["solution_number"], 1)  # type: ignore[index]
        self.assertEqual(len(first_solution["analyses"]), 1)  # type: ignore[index]
        first_analysis = first_solution["analyses"][0]  # type: ignore[index]
        self.assertEqual(first_analysis.word, "agni")
        self.assertEqual(first_analysis.case, "accusative")
        self.assertEqual(first_analysis.gender, "masculine")
        self.assertEqual(first_analysis.number, "dual")

        second_solution = result["solutions"][1]
        self.assertEqual(second_solution["solution_number"], 2)  # type: ignore[index]
        self.assertEqual(len(second_solution["analyses"]), 1)  # type: ignore[index]
        second_analysis = second_solution["analyses"][0]  # type: ignore[index]
        self.assertEqual(second_analysis.case, "vocative")
        self.assertEqual(second_analysis.number, "dual")


class TestHeritageHTMLExtractor(unittest.TestCase):
    """Test suite for Heritage HTML extractor"""

    def test_extract_plain_text_lawngreen_back(self):
        """Test extraction from lawngreen_back table"""
        html = """<table class="lawngreen_back">
<tr><th><span class="latin12">[<a href="#">yoga</a>]{m. sg. voc.}</span></th></tr>
</table>"""
        extractor = HeritageHTMLExtractor()
        result = extractor.extract_plain_text(html)
        self.assertIn("[yoga]{m. sg. voc.}", result)

    def test_extract_plain_text_grey_back(self):
        """Test extraction from grey_back table"""
        html = """<table class="grey_back">
<tr><th><span class="latin12">[agni]{?}</span></th></tr>
</table>"""
        extractor = HeritageHTMLExtractor()
        result = extractor.extract_plain_text(html)
        self.assertIn("[agni]{?}", result)

    def test_extract_no_duplicates(self):
        """Test that patterns are not duplicated from nested tables"""
        html = """<table class="lawngreen_back">
<tr><th><span class="latin12"><table class="lawngreen_back">
<tr><th><span class="latin12">[yoga]{m. sg. voc.}</span></th></tr>
</table></th></span></th></tr>
</table>"""
        extractor = HeritageHTMLExtractor()
        result = extractor.extract_plain_text(html)
        # Should only appear once
        count = result.count("[yoga]{m. sg. voc.}")
        self.assertEqual(count, 1)


class TestMorphologyReducer(unittest.TestCase):
    """Test suite for the MorphologyReducer Lark parser"""

    def test_reducer_initialization(self):
        """Test reducer is properly initialized"""
        reducer = MorphologyReducer()
        self.assertIsNotNone(reducer.parser)

    def test_reduce_simple_pattern(self):
        """Test reducing a simple [word]{analysis} pattern"""
        reducer = MorphologyReducer()
        result = reducer.reduce("[yoga]{m. sg. voc.}")

        self.assertEqual(len(result), 1)
        solution = result[0]
        self.assertIsInstance(solution, dict)
        self.assertEqual(solution["total_words"], 1)  # type: ignore[index]
        analyses = solution["analyses"]  # type: ignore[index]
        self.assertEqual(len(analyses), 1)
        self.assertEqual(analyses[0].word, "yoga")


if __name__ == "__main__":
    unittest.main()
