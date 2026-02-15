#!/usr/bin/env python3
"""
Test suite for POS parsing functionality
"""

import os
import sys
import unittest
from typing import cast

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from langnet.heritage.encoding_service import (
    HeritageCdslBridge,
    HeritagePOSResult,
)


class TestPosParsing(unittest.TestCase):
    """Test suite for POS parsing functionality"""

    def setUp(self):
        """Setup test fixtures"""
        self.bridge = HeritageCdslBridge()

    def test_heritage_pos_extraction_basic(self):
        """Test basic POS extraction from Heritage dictionary responses"""
        # Test the specific pattern: headword [ POS ] definition
        test_cases = [
            ("agni [ m. ] fire", ("agni", "m.")),
            ("jātu [ Ind. ]", ("jātu", "Ind.")),
            ("deva [ m. ] god", ("deva", "m.")),
        ]

        for response, expected in test_cases:
            with self.subTest(response=response):
                result = self.bridge.process_heritage_response_for_cdsl(response)
                self.assertNotIn("error", result)
                pos_result: HeritagePOSResult = result  # type: ignore[assignment]

                # Should extract headword and POS correctly
                self.assertIn("extracted_headwords_pos", pos_result)
                self.assertEqual(len(pos_result["extracted_headwords_pos"]), 1)
                headword, extracted_pos = pos_result["extracted_headwords_pos"][0]

                # Strip whitespace from extracted POS for comparison
                self.assertEqual(headword, expected[0])
                self.assertEqual(extracted_pos.strip(), expected[1])

    def test_pos_parsing_with_complex_definitions(self):
        """Test POS parsing with complex definitions"""
        test_cases = [
            "agni [ m. ] fire; god of fire",
            "deva [ m. ] god; deity",
            "mitra [ m. ] friend",
        ]

        for response in test_cases:
            with self.subTest(response=response):
                result = self.bridge.process_heritage_response_for_cdsl(response)
                self.assertNotIn("error", result)
                pos_result: HeritagePOSResult = result  # type: ignore[assignment]

                # Should extract headword and POS
                self.assertIn("extracted_headwords_pos", pos_result)
                self.assertTrue(len(pos_result["extracted_headwords_pos"]) > 0)

                headword, pos = pos_result["extracted_headwords_pos"][0]
                self.assertIsInstance(headword, str)
                self.assertIsInstance(pos, str)
                self.assertTrue(len(headword) > 0)
                self.assertTrue(len(pos) > 0)

    def test_multiple_headword_parsing(self):
        """Test parsing of responses with multiple headwords"""
        response = "agni [ m. ] fire deva [ m. ] god mitra [ m. ] friend"

        result = self.bridge.process_heritage_response_for_cdsl(response)
        self.assertNotIn("error", result)
        pos_result: HeritagePOSResult = result  # type: ignore[assignment]

        # Should extract all three entries
        self.assertEqual(len(pos_result["extracted_headwords_pos"]), 3)
        self.assertEqual(pos_result["headwords_only"], ["agni", "deva", "mitra"])

        # Should have POS info for each
        self.assertEqual(pos_result["pos_info"]["agni"], "m.")
        self.assertEqual(pos_result["pos_info"]["deva"], "m.")
        self.assertEqual(pos_result["pos_info"]["mitra"], "m.")

    def test_pos_code_variations(self):
        """Test various POS code formats"""
        pos_test_cases = ["m.", "f.", "n.", "Ind.", "N.", "adj.", "v."]

        for pos_code in pos_test_cases:
            with self.subTest(pos_code=pos_code):
                response = f"testword [ {pos_code} ] test definition"
                result = self.bridge.process_heritage_response_for_cdsl(response)
                self.assertNotIn("error", result)
                pos_result: HeritagePOSResult = result  # type: ignore[assignment]

                self.assertIn("extracted_headwords_pos", pos_result)
                self.assertEqual(len(pos_result["extracted_headwords_pos"]), 1)
                headword, extracted_pos = pos_result["extracted_headwords_pos"][0]
                self.assertEqual(extracted_pos.strip(), pos_code)

    def test_edge_cases_and_malformed_responses(self):
        """Test edge cases and malformed responses"""
        edge_cases = [
            # Headwords with numbers and hyphens
            "agni1 [ m. ] fire",
            "mahā-rāja [ m. ] great king",
            # Malformed responses
            "agni [ N. fire",  # Missing closing bracket
            "agni N. ] fire",  # Missing opening bracket
            "agni fire",  # No brackets at all
        ]

        for response in edge_cases:
            with self.subTest(response=response):
                result = self.bridge.process_heritage_response_for_cdsl(response)
                self.assertIsInstance(result, dict)
                combined_result = cast(dict[str, object], result)

                # For malformed cases, check if error exists
                if "error" in combined_result:
                    err = combined_result["error"]
                    self.assertIsInstance(err, str)
                    continue

    def test_pos_extraction_workflow(self):
        """Test POS extraction in the complete encoding bridge workflow"""
        test_cases = [
            ("agni", "agni [ m. ] fire"),
            ("deva", "deva [ m. ] god"),
            ("jātu", "jātu [ Ind. ] indeclinable"),
        ]

        for query, heritage_response in test_cases:
            with self.subTest(query=query):
                # Step 2: Process Heritage response
                processed = self.bridge.process_heritage_response_for_cdsl(heritage_response)
                self.assertIsInstance(processed, dict)
                pos_result = cast(HeritagePOSResult, processed)
                self.assertNotIn("error", pos_result)

                # Should have extracted headwords and POS
                self.assertIn("extracted_headwords_pos", pos_result)
                self.assertTrue(len(pos_result["extracted_headwords_pos"]) > 0)

                # Should have CDSL lookups
                self.assertIn("cdsl_lookups", pos_result)
                self.assertTrue(len(pos_result["cdsl_lookups"]) > 0)

                # Each lookup should have POS info
                for lookup in pos_result["cdsl_lookups"]:
                    self.assertIn("pos", lookup)
                    self.assertIsInstance(lookup["pos"], str)


if __name__ == "__main__":
    unittest.main()
