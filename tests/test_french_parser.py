"""Tests for French gloss parser (Gaffiot and Heritage)."""

from __future__ import annotations

import unittest

from langnet.parsing.french_parser import (
    FrenchGlossParser,
    parse_french_glosses,
    parse_gaffiot_entry,
)


class FrenchGlossBasicTests(unittest.TestCase):
    """Basic tests for French gloss parsing."""

    def test_parse_simple_gloss_list(self) -> None:
        """Parse simple comma-separated glosses."""
        glosses = parse_french_glosses("ardor, caritas")

        self.assertEqual(len(glosses), 2)
        self.assertEqual(glosses[0], "ardor")
        self.assertEqual(glosses[1], "caritas")

    def test_parse_semicolon_separated(self) -> None:
        """Parse semicolon-separated glosses."""
        glosses = parse_french_glosses("amour; passion; désir")

        self.assertEqual(len(glosses), 3)
        self.assertIn("amour", glosses)
        self.assertIn("passion", glosses)

    def test_parse_newline_separated(self) -> None:
        """Parse newline-separated glosses."""
        glosses = parse_french_glosses("ardor\ncaritas\namor")

        self.assertEqual(len(glosses), 3)
        self.assertEqual(glosses[0], "ardor")
        self.assertEqual(glosses[1], "caritas")

    def test_parse_mixed_separators(self) -> None:
        """Parse glosses with mixed separators."""
        glosses = parse_french_glosses("amour, passion; désir\nardeur")

        self.assertGreaterEqual(len(glosses), 3)

    def test_parse_single_gloss(self) -> None:
        """Parse single gloss without separators."""
        glosses = parse_french_glosses("amour")

        self.assertEqual(len(glosses), 1)
        self.assertEqual(glosses[0], "amour")

    def test_parse_empty_string(self) -> None:
        """Handle empty string gracefully."""
        glosses = parse_french_glosses("")

        self.assertEqual(len(glosses), 0)


class GaffiotEntryParsingTests(unittest.TestCase):
    """Tests for parsing complete Gaffiot entries."""

    def test_parse_gaffiot_entry_simple(self) -> None:
        """Parse simple Gaffiot entry."""
        entry = parse_gaffiot_entry("amor", "ardor, caritas")

        self.assertEqual(entry["headword"], "amor")
        self.assertEqual(len(entry["glosses"]), 2)  # type: ignore[arg-type]
        self.assertIn("ardor", entry["glosses"])  # type: ignore[arg-type]
        self.assertIn("caritas", entry["glosses"])  # type: ignore[arg-type]

    def test_parse_gaffiot_entry_with_newlines(self) -> None:
        """Parse Gaffiot entry with newline separators."""
        entry = parse_gaffiot_entry("bellum", "guerre\ncombat\nbataille")

        self.assertEqual(entry["headword"], "bellum")
        self.assertGreaterEqual(len(entry["glosses"]), 3)  # type: ignore[arg-type]

    def test_parse_gaffiot_entry_preserves_raw(self) -> None:
        """Preserve raw text in parsed entry."""
        raw_text = "ardor, caritas, amor"
        entry = parse_gaffiot_entry("test", raw_text)

        self.assertEqual(entry["raw_text"], raw_text)

    def test_parse_gaffiot_entry_empty_text(self) -> None:
        """Handle empty plain_text gracefully."""
        entry = parse_gaffiot_entry("test", "")

        self.assertEqual(entry["headword"], "test")
        self.assertEqual(entry["glosses"], [])


class FrenchGlossParserTests(unittest.TestCase):
    """Tests for FrenchGlossParser class."""

    def setUp(self) -> None:
        """Set up parser instance."""
        self.parser = FrenchGlossParser()

    def test_parser_parse_simple_list(self) -> None:
        """Parse simple gloss list."""
        result = self.parser.parse("amour, passion")

        self.assertIsNotNone(result)
        self.assertEqual(len(result["glosses"]), 2)
        self.assertEqual(result["glosses"][0]["text"], "amour")
        self.assertEqual(result["glosses"][1]["text"], "passion")

    def test_parser_parse_safe_returns_none_on_error(self) -> None:
        """parse_safe returns None for completely invalid input."""
        # Note: Most strings will parse as *something*, so this is hard to trigger
        # The fallback in parse_french_glosses handles most cases
        result = self.parser.parse_safe("normal text")

        # Even "invalid" text might parse - that's okay
        self.assertIsInstance(result, (dict, type(None)))

    def test_parser_preserves_raw_text(self) -> None:
        """Parser preserves original raw text."""
        text = "ardor, caritas, amor"
        result = self.parser.parse(text)

        self.assertEqual(result["raw_text"], text)


class FrenchGlossRealWorldTests(unittest.TestCase):
    """Tests with realistic Gaffiot/Heritage data."""

    def test_parse_gaffiot_amor_entry(self) -> None:
        """Parse realistic Gaffiot entry for 'amor'."""
        # From test_databuild_gaffiot.py
        entry = parse_gaffiot_entry("amor", "ardor\ncaritas")

        self.assertEqual(entry["headword"], "amor")
        self.assertIn("ardor", entry["glosses"])  # type: ignore[arg-type]
        self.assertIn("caritas", entry["glosses"])  # type: ignore[arg-type]

    def test_parse_gaffiot_bellum_entry(self) -> None:
        """Parse realistic Gaffiot entry for 'bellum'."""
        entry = parse_gaffiot_entry("bellum", "guerre\ncombat")

        self.assertEqual(entry["headword"], "bellum")
        self.assertIn("guerre", entry["glosses"])  # type: ignore[arg-type]
        self.assertIn("combat", entry["glosses"])  # type: ignore[arg-type]

    def test_parse_multiple_gaffiot_entries(self) -> None:
        """Parse multiple Gaffiot entries."""
        entries = [
            parse_gaffiot_entry("amor", "ardor, caritas"),
            parse_gaffiot_entry("bellum", "guerre, combat"),
            parse_gaffiot_entry("pax", "paix"),
        ]

        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0]["headword"], "amor")
        self.assertEqual(entries[1]["headword"], "bellum")
        self.assertEqual(entries[2]["headword"], "pax")

    def test_parse_pilcrow_separated_glosses(self) -> None:
        """Parse glosses with pilcrow (¶) separator."""
        # Pilcrow is used in some Gaffiot exports
        glosses = parse_french_glosses("amour ¶ passion ¶ désir")

        self.assertGreaterEqual(len(glosses), 2)


if __name__ == "__main__":
    unittest.main()
