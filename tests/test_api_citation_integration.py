"""
Test API integration for citation system.

This module tests that citations are properly included in API responses.
"""

import unittest
from langnet.asgi import (
    _add_citations_to_response,
    _extract_citations_from_diogenes_result,
    _extract_citations_from_cdsl_result,
)


class TestDiogenesCitationExtraction(unittest.TestCase):
    """Tests for Diogenes citation extraction."""

    def test_extract_citations_from_diogenes_result(self):
        """Test extracting citations from Diogenes API result."""
        sample_result = {
            "chunks": [
                {
                    "definitions": {
                        "blocks": [
                            {
                                "citations": {
                                    "perseus:abo:phi,0119,006:985": "Plaut. Cas. 5, 4, 23 (985)",
                                    "perseus:abo:phi,0956,001:127": "Cic. Fin. 2, 24",
                                }
                            }
                        ]
                    }
                }
            ]
        }

        citations = _extract_citations_from_diogenes_result(sample_result)

        self.assertEqual(len(citations.citations), 2)
        self.assertEqual(citations.citations[0].references[0].text, "Plaut. Cas. 5, 4, 23 (985)")
        self.assertEqual(citations.citations[1].references[0].text, "Cic. Fin. 2, 24")

    def test_extract_citations_empty_result(self):
        """Test extracting citations from empty Diogenes result."""
        citations = _extract_citations_from_diogenes_result({})
        self.assertEqual(len(citations.citations), 0)

    def test_extract_citations_no_citations(self):
        """Test extracting citations when no citations are present."""
        sample_result = {"chunks": [{"definitions": {"blocks": [{"entry": "Test entry"}]}}]}

        citations = _extract_citations_from_diogenes_result(sample_result)
        self.assertEqual(len(citations.citations), 0)


class TestCDSLCitationExtraction(unittest.TestCase):
    """Tests for CDSL citation extraction."""

    def test_extract_citations_from_cdsl_result(self):
        """Test extracting citations from CDSL API result."""
        sample_result = {
            "dictionaries": {
                "MW": [
                    {
                        "references": [
                            {"source": "M-W 127", "dictionary": "MW"},
                            {"source": "Apte 89", "dictionary": "Apte"},
                        ]
                    }
                ]
            }
        }

        citations = _extract_citations_from_cdsl_result(sample_result)

        self.assertEqual(len(citations.citations), 2)
        self.assertEqual(citations.citations[0].references[0].text, "M-W 127")
        self.assertEqual(citations.citations[1].references[0].text, "Apte 89")

    def test_extract_citations_empty_result(self):
        """Test extracting citations from empty CDSL result."""
        citations = _extract_citations_from_cdsl_result({})
        self.assertEqual(len(citations.citations), 0)


class TestAPIResponseEnrichment(unittest.TestCase):
    """Tests for API response enrichment with citations."""

    def test_add_citations_to_response_latin(self):
        """Test adding citations to Latin API response."""
        sample_result = {
            "diogenes": {
                "chunks": [
                    {
                        "definitions": {
                            "blocks": [
                                {
                                    "citations": {
                                        "perseus:abo:phi,0119,006:985": "Plaut. Cas. 5, 4, 23 (985)"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        }

        enriched = _add_citations_to_response(sample_result, "lat")

        self.assertIn("citations", enriched)
        self.assertEqual(enriched["citations"]["total_count"], 1)
        self.assertEqual(enriched["citations"]["language"], "lat")
        self.assertEqual(enriched["citations"]["items"][0]["text"], "Plaut. Cas. 5, 4, 23 (985)")

    def test_add_citations_to_response_sanskrit(self):
        """Test adding citations to Sanskrit API response."""
        sample_result = {
            "cdsl": {
                "dictionaries": {
                    "MW": [{"references": [{"source": "M-W 127", "dictionary": "MW"}]}]
                }
            }
        }

        enriched = _add_citations_to_response(sample_result, "san")

        self.assertIn("citations", enriched)
        self.assertEqual(enriched["citations"]["total_count"], 1)
        self.assertEqual(enriched["citations"]["language"], "san")
        self.assertEqual(enriched["citations"]["items"][0]["text"], "M-W 127")

    def test_add_citations_no_citations(self):
        """Test adding citations when none are present."""
        sample_result = {"diogenes": {}, "whitakers": {}, "cltk": {}}

        enriched = _add_citations_to_response(sample_result, "lat")

        # Should not have citations key when no citations found
        self.assertNotIn("citations", enriched)

    def test_citation_response_structure(self):
        """Test that citation response has correct structure."""
        sample_result = {
            "diogenes": {
                "chunks": [
                    {
                        "definitions": {
                            "blocks": [
                                {
                                    "citations": {
                                        "perseus:abo:phi,0119,006:985": "Plaut. Cas. 5, 4, 23 (985)"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        }

        enriched = _add_citations_to_response(sample_result, "lat")
        citation_data = enriched["citations"]

        # Check structure
        self.assertIn("total_count", citation_data)
        self.assertIn("language", citation_data)
        self.assertIn("items", citation_data)

        # Check item structure
        item = citation_data["items"][0]
        self.assertIn("text", item)
        self.assertIn("type", item)
        self.assertIn("short_title", item)
        self.assertIn("full_name", item)
        self.assertIn("description", item)


if __name__ == "__main__":
    unittest.main()
