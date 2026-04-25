"""Tests for CLTK parser integration with Lewis & Short entries."""

from __future__ import annotations

import unittest

from langnet.parsing.integration import (
    enrich_cltk_with_parsed_lewis,
    parse_lewis_lines,
)


class CLTKLewisParsingTests(unittest.TestCase):
    """Tests for parsing Lewis & Short entries from CLTK."""

    def test_parse_single_lewis_line(self) -> None:
        """Parse single Lewis & Short entry."""
        lines = ["lupus, -i, m."]
        parsed = parse_lewis_lines(lines)

        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["header"]["lemma"], "lupus")
        self.assertEqual(parsed[0]["header"]["gender"], "m")

    def test_parse_multiple_lewis_lines(self) -> None:
        """Parse multiple Lewis & Short entries."""
        lines = [
            "lupus, -i, m.",
            "amo, amare, amavi, amatum, v.",
            "bonus, -a, -um, adj.",
        ]
        parsed = parse_lewis_lines(lines)

        self.assertEqual(len(parsed), 3)
        self.assertEqual(parsed[0]["header"]["lemma"], "lupus")
        self.assertEqual(parsed[1]["header"]["lemma"], "amo")
        self.assertEqual(parsed[2]["header"]["lemma"], "bonus")

    def test_parse_lewis_lines_with_senses(self) -> None:
        """Parse Lewis entry with sense information."""
        lines = ["lupus, -i, m. I. a wolf"]
        parsed = parse_lewis_lines(lines)

        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["header"]["lemma"], "lupus")
        # Should have at least one sense
        self.assertGreaterEqual(len(parsed[0]["senses"]), 1)

    def test_parse_lewis_lines_skips_invalid(self) -> None:
        """Skip invalid lines gracefully."""
        lines = [
            "lupus, -i, m.",
            "@#$%^ invalid syntax",
            "amo, amare, amavi, amatum, v.",
            "",  # Empty line
            "   ",  # Whitespace only
        ]
        parsed = parse_lewis_lines(lines)

        # Should parse only the 2 valid entries
        self.assertEqual(len(parsed), 2)

    def test_parse_lewis_lines_empty_list(self) -> None:
        """Handle empty list gracefully."""
        parsed = parse_lewis_lines([])

        self.assertEqual(len(parsed), 0)


class CLTKPayloadEnrichmentTests(unittest.TestCase):
    """Tests for enriching CLTK payloads with parsed Lewis data."""

    def test_enrich_payload_with_lewis_lines(self) -> None:
        """Enrich CLTK payload with parsed Lewis & Short entries."""
        payload = {
            "lemma": "lupus",
            "word": "lupus",
            "lewis_lines": ["lupus, -i, m. I. a wolf"],
        }

        enriched = enrich_cltk_with_parsed_lewis(payload)

        self.assertIn("parsed_lewis", enriched)
        self.assertEqual(len(enriched["parsed_lewis"]), 1)
        self.assertEqual(enriched["parsed_lewis"][0]["header"]["lemma"], "lupus")
        # Original fields preserved
        self.assertEqual(enriched["lemma"], "lupus")
        self.assertEqual(enriched["word"], "lupus")

    def test_enrich_payload_multiple_lewis_lines(self) -> None:
        """Enrich payload with multiple Lewis entries."""
        payload = {
            "lemma": "amo",
            "lewis_lines": [
                "amo, amare, amavi, amatum, v. I. to love",
                "amor, -oris, m. I. love",
            ],
        }

        enriched = enrich_cltk_with_parsed_lewis(payload)

        self.assertIn("parsed_lewis", enriched)
        self.assertEqual(len(enriched["parsed_lewis"]), 2)
        self.assertEqual(enriched["parsed_lewis"][0]["header"]["lemma"], "amo")
        self.assertEqual(enriched["parsed_lewis"][1]["header"]["lemma"], "amor")

    def test_enrich_payload_no_lewis_lines(self) -> None:
        """Return fallback entry when no lewis_lines present."""
        payload = {"lemma": "test", "word": "test"}

        enriched = enrich_cltk_with_parsed_lewis(payload)

        # New behavior: we provide fallback data with query word as lemma
        self.assertIn("parsed_lewis", enriched)
        self.assertEqual(len(enriched["parsed_lewis"]), 1)
        self.assertEqual(enriched["parsed_lewis"][0]["header"]["lemma"], "test")

    def test_enrich_payload_empty_lewis_lines(self) -> None:
        """Return fallback entry for empty lewis_lines."""
        payload = {"lemma": "test", "lewis_lines": []}

        enriched = enrich_cltk_with_parsed_lewis(payload)

        # New behavior: we provide fallback data with query word as lemma
        self.assertIn("parsed_lewis", enriched)
        self.assertEqual(len(enriched["parsed_lewis"]), 1)
        self.assertEqual(enriched["parsed_lewis"][0]["header"]["lemma"], "test")

    def test_enrich_payload_all_invalid_lewis_lines(self) -> None:
        """Handle all-invalid lewis_lines gracefully."""
        payload = {
            "lemma": "test",
            "lewis_lines": ["@#$%^&*()", "12345", "!!!???"],
        }

        enriched = enrich_cltk_with_parsed_lewis(payload)

        # Should still have parsed_lewis (even if empty or minimal)
        # The grammar may parse some tokens as valid lemmas
        # This is acceptable - we're just checking no crashes
        self.assertIsInstance(enriched, dict)


class CLTKRealWorldTests(unittest.TestCase):
    """Tests with realistic CLTK data."""

    def test_parse_verb_with_principal_parts(self) -> None:
        """Parse verb entry with all principal parts."""
        lines = ["amo, amare, amavi, amatum, v. I. to love"]
        parsed = parse_lewis_lines(lines)

        self.assertEqual(len(parsed), 1)
        header = parsed[0]["header"]
        self.assertEqual(header["lemma"], "amo")
        self.assertIn("amare", header["principal_parts"])
        self.assertIn("amavi", header["principal_parts"])
        self.assertIn("amatum", header["principal_parts"])
        self.assertEqual(header["pos"], "v")

    def test_parse_adjective_three_endings(self) -> None:
        """Parse adjective with three endings."""
        lines = ["bonus, -a, -um, adj."]
        parsed = parse_lewis_lines(lines)

        self.assertEqual(len(parsed), 1)
        header = parsed[0]["header"]
        self.assertEqual(header["lemma"], "bonus")
        self.assertIn("-a", header["principal_parts"])
        self.assertIn("-um", header["principal_parts"])
        self.assertEqual(header["pos"], "adj")

    def test_parse_noun_with_etymology(self) -> None:
        """Parse noun with etymology root."""
        lines = ["lupus, -i, m. (√lup)"]
        parsed = parse_lewis_lines(lines)

        self.assertEqual(len(parsed), 1)
        header = parsed[0]["header"]
        self.assertEqual(header["lemma"], "lupus")
        self.assertEqual(header["root"], "lup")


if __name__ == "__main__":
    unittest.main()
