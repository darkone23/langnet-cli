"""
Unit tests for morphology parser functionality using unittest.
"""

import unittest

from langnet.heritage.parsers import MorphologyReducer


class TestMorphologyParser(unittest.TestCase):
    """Test cases for morphology parser functionality"""

    def test_parse_line_basic(self):
        """Test basic line parsing functionality"""
        reducer = MorphologyReducer()

        # Test with proper LARK grammar format
        result = reducer.parse_line("[agni]{m.}")

        # Should return a list
        self.assertIsInstance(result, list)

    def test_parse_line_empty(self):
        """Test parsing empty line"""
        reducer = MorphologyReducer()
        result = reducer.parse_line("")

        # Should return empty or None
        self.assertTrue(result is None or result == [])

    def test_parse_line_invalid_format(self):
        """Test parsing line with invalid format - should not crash"""
        reducer = MorphologyReducer()

        # Invalid format should be handled gracefully
        result = reducer.parse_line("invalid input format")

        # Should return a list (possibly empty) without crashing
        self.assertIsInstance(result, list)


if __name__ == "__main__":
    unittest.main()
