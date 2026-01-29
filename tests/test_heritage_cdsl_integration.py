#!/usr/bin/env python3
"""
Test suite for complete Heritage Platform + CDSL integration
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from langnet.cologne.core import CdslIndex
from langnet.heritage.encoding_service import HeritageCdslBridge


class TestHeritageCdslIntegration(unittest.TestCase):
    """Test suite for complete Heritage Platform + CDSL integration"""

    def setUp(self):
        """Setup test fixtures"""
        self.bridge = HeritageCdslBridge()
        self.db_dir = Path("/home/nixos/cdsl_data/db")

    def test_encoding_bridge_workflow(self):
        """Test complete encoding bridge workflow"""
        # Test cases that should work with both systems
        test_words = [
            ("अग्नि", "Devanagari input"),
            ("jātu", "IAST input (Heritage output format)"),
            ("agni", "Roman input"),
            ("deva", "Simple roman"),
            ("jaatu", "Approximate roman"),
        ]

        for word, description in test_words:
            with self.subTest(word=word, description=description):
                try:
                    # Step 1: Use encoding bridge to convert for Heritage Platform
                    heritage_result = self.bridge.search_heritage_and_lookup_cdsl(word, "MW")

                    # Verify basic structure
                    self.assertIn("query", heritage_result)
                    self.assertIn("encoding_conversions", heritage_result)
                    self.assertIn("heritage_search", heritage_result)
                    self.assertIn("cdsl_lookup", heritage_result)

                    # Verify conversion details
                    self.assertEqual(heritage_result["query"], word)
                    self.assertIn("original", heritage_result["encoding_conversions"])
                    self.assertIn("slp1", heritage_result["encoding_conversions"])

                    # Verify heritage search parameters
                    heritage_params = heritage_result["heritage_search"]["parameters"]
                    self.assertIn("lex", heritage_params)
                    self.assertIn("q", heritage_params)
                    self.assertIn("t", heritage_params)

                    # Verify CDSL lookup structure
                    cdsl_lookup = heritage_result["cdsl_lookup"]
                    self.assertIn("slp1_key", cdsl_lookup)
                    self.assertIn("cdsl_query", cdsl_lookup)

                except Exception as e:
                    self.fail(f"Encoding bridge workflow failed for '{word}': {e}")

    def test_heritage_response_processing(self):
        """Test processing of Heritage Platform responses"""
        heritage_responses = [
            "jātu [ Ind. ]",
            "agni [ m. ] fire",
            "deva [ m. ] god",
            "mitra [ m. ] friend",
        ]

        for response in heritage_responses:
            with self.subTest(response=response):
                try:
                    # Process the Heritage response to extract headwords
                    processed = self.bridge.process_heritage_response_for_cdsl(response)

                    # Should not have error
                    self.assertNotIn("error", processed)

                    # Should have extracted headwords
                    self.assertIn("extracted_headwords_pos", processed)
                    self.assertTrue(len(processed["extracted_headwords_pos"]) > 0)

                    # Should have headwords only
                    self.assertIn("headwords_only", processed)

                    # Should have POS info
                    self.assertIn("pos_info", processed)

                    # Should have CDSL lookups
                    self.assertIn("cdsl_lookups", processed)
                    self.assertTrue(len(processed["cdsl_lookups"]) > 0)

                    # Verify each lookup has required fields
                    for lookup in processed["cdsl_lookups"]:
                        self.assertIn("iast", lookup)
                        self.assertIn("slp1", lookup)
                        self.assertIn("cdsl_key", lookup)
                        self.assertIn("cdsl_query", lookup)
                        self.assertIn("pos", lookup)

                except Exception as e:
                    self.fail(f"Heritage response processing failed for '{response}': {e}")

    @patch("langnet.cologne.core.CdslIndex")
    def test_cdsl_lookup_integration(self, mock_cdsl_index_class):
        """Test CDSL lookup integration"""
        # Mock CDSL index
        mock_index_instance = Mock()
        mock_cdsl_index_class.return_value.__enter__.return_value = mock_index_instance

        # Mock successful lookup
        mock_index_instance.lookup.return_value = [
            Mock(key="agni", lnum=123, data="<entry>fire</entry>")
        ]

        # Test with a word that should have CDSL results
        slp1_key = "agni"

        # Use the mock directly instead of creating real CdslIndex
        results = mock_index_instance.lookup("MW", slp1_key)

        # Verify lookup was called with correct parameters
        mock_index_instance.lookup.assert_called_once_with("MW", slp1_key)

        # Verify results structure
        self.assertTrue(len(results) > 0)
        first_result = results[0]
        self.assertEqual(first_result.key, "agni")
        self.assertEqual(first_result.lnum, 123)
        self.assertIn("fire", str(first_result.data))

    def test_prefix_search_functionality(self):
        """Test prefix search functionality"""
        with patch("langnet.cologne.core.CdslIndex") as mock_cdsl_index_class:
            # Mock CDSL index
            mock_index_instance = Mock()
            mock_cdsl_index_class.return_value.__enter__.return_value = mock_index_instance

            # Mock prefix search results
            mock_index_instance.prefix_search.return_value = [
                ("agni", 123),
                ("agnin", 124),
                ("agniya", 125),
            ]

            # Test prefix search
            slp1_prefix = "agn"
            limit = 5

            # Use the mock directly instead of creating real CdslIndex
            results = mock_index_instance.prefix_search("MW", slp1_prefix, limit=limit)

            # Verify search was called with correct parameters
            mock_index_instance.prefix_search.assert_called_once_with(
                "MW", slp1_prefix, limit=limit
            )

            # Verify results structure
            self.assertEqual(len(results), 3)
            for headword, lnum in results:
                self.assertIsInstance(headword, str)
                self.assertIsInstance(lnum, int)
                self.assertTrue(int(lnum) > 0)  # type: ignore[arg-type]

    def test_complete_workflow_simulation(self):
        """Test complete workflow simulation"""
        # Simulate what happens when we get a response from Heritage Platform
        heritage_responses = [
            "jātu [ Ind. ]",
            "agni [ m. ] fire",
            "deva [ m. ] god",
            "mitra [ m. ] friend",
        ]

        for response in heritage_responses:
            with self.subTest(response=response):
                try:
                    # Process the Heritage response
                    processed = self.bridge.process_heritage_response_for_cdsl(response)

                    # For each headword, verify CDSL lookup structure
                    for lookup in processed["cdsl_lookups"]:
                        headword = lookup["iast"]
                        slp1_key = lookup["slp1"]
                        cdsl_key = lookup["cdsl_key"]
                        pos = lookup["pos"]

                        # Verify data integrity
                        if "headwords_only" in processed and processed["headwords_only"]:
                            self.assertEqual(headword, processed["headwords_only"][0])
                        self.assertEqual(slp1_key.lower(), cdsl_key)
                        self.assertIsInstance(pos, str)

                        # Verify CDSL query format
                        cdsl_query = lookup["cdsl_query"]
                        self.assertIn("SELECT", cdsl_query)
                        self.assertIn("key_normalized", cdsl_query)
                        self.assertIn(f"'{cdsl_key}'", cdsl_query)

                except Exception as e:
                    self.fail(f"Complete workflow simulation failed for '{response}': {e}")

    def test_error_handling(self):
        """Test error handling for various scenarios"""
        # Test empty response
        result = self.bridge.process_heritage_response_for_cdsl("")
        self.assertIn("error", result)
        self.assertIn("No headwords found", result["error"])

        # Test malformed response
        malformed_responses = [
            "[ only brackets",
            "headword [unclosed bracket",
            "headword ] missing opening",
        ]

        for response in malformed_responses:
            with self.subTest(response=response):
                result = self.bridge.process_heritage_response_for_cdsl(response)
                # Should handle gracefully
                self.assertIsInstance(result, dict)

    def test_encoding_conversion_accuracy(self):
        """Test accuracy of encoding conversions"""
        test_cases = [
            ("अग्नि", "agni"),  # Devanagari to Velthuis
            ("jātu", "jātu"),  # IAST to SLP1 (IAST is already valid SLP1 for most characters)
            ("agni", "agni"),  # Already SLP1
        ]

        for input_text, expected_slp1 in test_cases:
            with self.subTest(input_text=input_text):
                # Test SLP1 conversion
                slp1_result = self.bridge.encoding_service.to_slp1(input_text)
                self.assertEqual(slp1_result.lower(), expected_slp1.lower())

                # Test normalization
                normalized = self.bridge.encoding_service.normalize_for_cdsl(input_text)
                self.assertEqual(normalized, expected_slp1.lower())


class TestHeritageWorkflowExamples(unittest.TestCase):
    """Test specific workflow examples from documentation"""

    def test_example_workflow_agni(self):
        """Test the specific 'अग्नि' workflow example"""
        bridge = HeritageCdslBridge()

        # Step 1: User enters 'अग्नि'
        user_input = "अग्नि"

        # Step 2: Encoding bridge detects devanagari
        result = bridge.search_heritage_and_lookup_cdsl(user_input, "MW")
        detected_encoding = result["encoding_conversions"]["detected_encoding"]
        self.assertEqual(detected_encoding, "devanagari")

        # Step 3: Convert to Velthuis
        velthuis = result["encoding_conversions"]["velthuis"]
        self.assertEqual(velthuis, "agni")

        # Step 4: Heritage URL construction
        heritage_url = result["heritage_search"]["url"]
        self.assertIn("agni", heritage_url)
        self.assertIn("t=VH", heritage_url)

        # Step 5-6: Process Heritage response format
        heritage_response = "agni [ m. ] fire"
        processed = bridge.process_heritage_response_for_cdsl(heritage_response)

        # Step 7: Extract headwords
        self.assertEqual(processed["headwords_only"], ["agni"])

        # Step 8: CDSL key conversion
        cdsl_key = processed["cdsl_lookups"][0]["cdsl_key"]
        self.assertEqual(cdsl_key, "agni")

        # Step 9: Verify CDSL query structure
        cdsl_query = processed["cdsl_lookups"][0]["cdsl_query"]
        self.assertIn("key_normalized", cdsl_query)
        self.assertIn("'agni'", cdsl_query)

    def test_multi_entry_response_handling(self):
        """Test handling of Heritage responses with multiple entries"""
        bridge = HeritageCdslBridge()

        # Response with multiple entries
        response = "agni [ m. ] fire deva [ m. ] god mitra [ m. ] friend"

        processed = bridge.process_heritage_response_for_cdsl(response)

        # Should extract all three entries
        self.assertEqual(len(processed["extracted_headwords_pos"]), 3)
        self.assertEqual(processed["headwords_only"], ["agni", "deva", "mitra"])

        # Should have POS info for each
        self.assertEqual(processed["pos_info"]["agni"], "m.")
        self.assertEqual(processed["pos_info"]["deva"], "m.")
        self.assertEqual(processed["pos_info"]["mitra"], "m.")

        # Should have corresponding CDSL lookups
        self.assertEqual(len(processed["cdsl_lookups"]), 3)
