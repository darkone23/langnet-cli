"""Tests for parser integration with existing handlers."""

from __future__ import annotations

import unittest

from langnet.parsing.integration import (
    enrich_extraction_with_parsed_header,
    extract_diogenes_header_from_html,
)


class DiogenesIntegrationTests(unittest.TestCase):
    """Integration tests for Diogenes parser with HTML extraction."""

    def test_extract_header_from_h2_span(self) -> None:
        """Extract header from <h2><span> pattern."""
        html = """
        <html>
            <body>
                <h2><span>lupus, -i, m.</span></h2>
                <div>Wolf definition...</div>
            </body>
        </html>
        """

        header = extract_diogenes_header_from_html(html)

        self.assertIsNotNone(header)
        if header:
            self.assertEqual(header["lemma"], "lupus")
            self.assertIn("-i", header["principal_parts"])
            self.assertEqual(header["gender"], "m")
            self.assertTrue(header["parse_success"])

    def test_extract_header_from_h2_direct(self) -> None:
        """Extract header from direct <h2> text."""
        html = "<h2>amo, amare, amavi, amatum, v.</h2>"

        header = extract_diogenes_header_from_html(html)

        self.assertIsNotNone(header)
        if header:
            self.assertEqual(header["lemma"], "amo")
            self.assertIn("amare", header["principal_parts"])
            self.assertEqual(header["pos"], "v")

    def test_extract_header_with_etymology(self) -> None:
        """Extract header with etymology root."""
        html = "<h2><span>lupus, -i, m. (√lup)</span></h2>"

        header = extract_diogenes_header_from_html(html)

        self.assertIsNotNone(header)
        if header:
            self.assertEqual(header["lemma"], "lupus")
            self.assertEqual(header["root"], "lup")

    def test_extract_header_returns_none_for_invalid(self) -> None:
        """Return None for HTML without recognizable header."""
        html = "<div>No header here</div>"

        header = extract_diogenes_header_from_html(html)

        self.assertIsNone(header)

    def test_extract_header_returns_none_for_unparseable(self) -> None:
        """Return None for header text that can't be parsed."""
        html = "<h2>@#$%^& invalid syntax !!!</h2>"

        header = extract_diogenes_header_from_html(html)

        self.assertIsNone(header)

    def test_enrich_payload_with_parsed_header(self) -> None:
        """Enrich extraction payload with parsed header."""
        payload = {
            "lemmas": ["lupus"],
            "parsed": {"chunks": []},
        }

        html = "<h2><span>lupus, -i, m.</span></h2>"

        enriched = enrich_extraction_with_parsed_header(payload, html)

        self.assertIn("parsed_header", enriched)
        self.assertEqual(enriched["parsed_header"]["lemma"], "lupus")
        self.assertEqual(enriched["lemmas"], ["lupus"])  # Original data preserved

    def test_enrich_payload_preserves_original_on_failure(self) -> None:
        """Preserve original payload if header parsing fails."""
        payload = {"lemmas": ["test"]}
        html = "<div>No header</div>"

        enriched = enrich_extraction_with_parsed_header(payload, html)

        self.assertNotIn("parsed_header", enriched)
        self.assertEqual(enriched, payload)


class RealWorldDiogenesTests(unittest.TestCase):
    """Tests with realistic Diogenes HTML patterns."""

    def test_extract_from_lewis_short_format(self) -> None:
        """Extract from Lewis & Short dictionary format."""
        html = """
        <div class="diogenes-result">
            <h2>
                <span class="lemma">lupus, -i, m.</span>
            </h2>
            <div id="sense">
                <div style="padding-left: 0px;">
                    I. a wolf
                </div>
                <div style="padding-left: 20px;">
                    A. lit., Cic.; Verg.
                </div>
            </div>
        </div>
        """

        header = extract_diogenes_header_from_html(html)

        self.assertIsNotNone(header)
        if header:
            self.assertEqual(header["lemma"], "lupus")
            self.assertEqual(header["gender"], "m")

    def test_extract_from_lsj_greek_format(self) -> None:
        """Extract from LSJ Greek dictionary format."""
        html = """
        <h2><span>λόγος, -ου, m.</span></h2>
        """

        header = extract_diogenes_header_from_html(html)

        self.assertIsNotNone(header)
        if header:
            self.assertIn("λόγος", header["lemma"])
            self.assertIn("-ου", header["principal_parts"])


if __name__ == "__main__":
    unittest.main()
