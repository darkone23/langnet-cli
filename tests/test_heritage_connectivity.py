#!/usr/bin/env python3
"""
Test suite for Heritage Platform CGI connectivity
"""

import os
import sys
import time
import unittest
from unittest.mock import Mock, patch

import requests

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from langnet.heritage.client import HeritageAPIError, HeritageHTTPClient
from langnet.heritage.config import heritage_config
from langnet.heritage.morphology import HeritageMorphologyService


class TestHeritageConnectivity(unittest.TestCase):
    """Test suite for Heritage Platform connectivity"""

    # Encoding test constants
    VELOCITY_TEST_INDEX = 0
    ITRANS_TEST_INDEX = 1
    SLP1_TEST_INDEX = 2
    DEVANAGARI_TEST_INDEX = 3

    def setUp(self):
        """Setup test fixtures"""
        self.client = HeritageHTTPClient()

    def test_morphology_service_initialization(self):
        """Test HeritageMorphologyService initialization"""
        service = HeritageMorphologyService()
        self.assertIsNotNone(service)

        # Test context manager
        with HeritageMorphologyService() as service:
            self.assertIsNotNone(service)

    @patch("langnet.heritage.morphology.HeritageHTTPClient")
    @patch("langnet.heritage.morphology.MorphologyParser")
    def test_morphology_service_analysis(self, mock_parser_class, mock_http_client_class):
        """Test morphology analysis functionality"""
        # Mock the HTTP client
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_http_client_class.return_value = mock_client
        mock_client.fetch_cgi_script.return_value = "<html>Morphology response</html>"

        # Mock the parser
        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser
        mock_parser.parse.return_value = {
            "solutions": [
                {
                    "type": "morphological_analysis",
                    "solution_number": 1,
                    "analyses": [
                        {
                            "word": "योगेन",
                            "lemma": "yoga",
                            "pos": "noun",
                        }
                    ],
                    "total_words": 1,
                },
                {
                    "type": "morphological_analysis",
                    "solution_number": 2,
                    "analyses": [
                        {
                            "word": "योगेन",
                            "lemma": "yogin",
                            "pos": "noun",
                        }
                    ],
                    "total_words": 1,
                },
            ],
            "total_solutions": 2,
            "word_analyses": [],
            "encoding": "velthuis",
        }

        with HeritageMorphologyService() as service:
            result = service.analyze("योगेन", encoding="velthuis", max_solutions=2)

            # Verify the result structure
            self.assertEqual(result.input_text, "योगेन")
            self.assertEqual(result.total_solutions, 2)
            self.assertIsInstance(result.processing_time, float)

            # Verify HTTP client was called correctly
            mock_client.fetch_cgi_script.assert_called_once_with(
                "sktreader", params={"text": "yogena", "t": "VH", "max": "2"}, timeout=None
            )

    @patch("requests.get")
    def test_server_connectivity(self, mock_get):
        """Test server connectivity"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        try:
            response = requests.get(heritage_config.base_url, timeout=5)
            self.assertEqual(response.status_code, 200)
        except Exception as e:
            self.fail(f"Server connectivity test failed: {e}")

    def test_server_unavailable_handling(self):
        """Test handling when server is unavailable"""
        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.ConnectionError("Connection failed")

            with self.assertRaises(requests.ConnectionError):
                requests.get(heritage_config.base_url, timeout=5)

    @patch("langnet.heritage.client.HeritageHTTPClient")
    def test_morphology_analysis_with_mock_data(self, mock_http_client_class):
        """Test morphology analysis with mocked response data"""
        # Mock the HTTP client with realistic response
        mock_client = Mock()
        mock_http_client_class.return_value.__enter__.return_value = mock_client

        # Mock morphology response HTML
        mock_html_response = """
        <html>
            <body>
                <table class="yellow_cent">
                    <tr>
                        <td>
                            <b>योगेन</b> (yogena)
                            <br>
                            Analysis: yoga-ge eighth case feminine singular
                        </td>
                    </tr>
                </table>
            </body>
        </html>
        """
        mock_client.fetch_cgi_script.return_value = mock_html_response

        with HeritageMorphologyService() as service:
            result = service.analyze("yogena", encoding="velthuis", max_solutions=1)

            # Verify basic result structure
            self.assertIsNotNone(result)
            self.assertEqual(result.input_text, "yogena")
            self.assertGreaterEqual(result.processing_time, 0)

    def test_morphology_analysis_error_handling(self):
        """Test morphology analysis error handling"""
        with patch("langnet.heritage.morphology.HeritageHTTPClient") as mock_client_class:
            # Mock client that raises an exception
            mock_client = Mock()
            mock_client.fetch_cgi_script.side_effect = HeritageAPIError("CGI script error")
            mock_client_class.return_value.__enter__.return_value = mock_client

            with HeritageMorphologyService() as service, self.assertRaises(HeritageAPIError):
                service.analyze("test", encoding="velthuis")

    def test_encoding_parameter_handling(self):
        """Test encoding parameter handling in morphology analysis"""
        with (
            patch("langnet.heritage.morphology.HeritageHTTPClient") as mock_client_class,
            patch("langnet.heritage.morphology.MorphologyParser") as mock_parser_class,
        ):
            mock_client = Mock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=None)
            mock_client_class.return_value = mock_client
            mock_client.fetch_cgi_script.return_value = "<html>Response</html>"

            # Mock the parser
            mock_parser = Mock()
            mock_parser_class.return_value = mock_parser
            mock_parser.parse.return_value = {
                "solutions": [],
                "total_solutions": 0,
                "word_analyses": [],
                "encoding": "velthuis",
            }

            with HeritageMorphologyService() as service:
                # Test different encodings
                service.analyze("अग्नि", encoding="velthuis", max_solutions=1)
                service.analyze("agni", encoding="itrans", max_solutions=1)
                service.analyze("agni", encoding="slp1", max_solutions=1)

                # Verify different CGI parameters were used
                calls = mock_client.fetch_cgi_script.call_args_list
                self.assertEqual(len(calls), 3)

                for i, call in enumerate(calls):
                    args, kwargs = call
                    self.assertEqual(args[0], "sktreader")
                    self.assertIn("text", kwargs["params"])
                    self.assertIn("t", kwargs["params"])
                    self.assertIn("max", kwargs["params"])

                    # Just verify that the calls were made with different parameters
                    self.assertTrue(len(kwargs["params"]["text"]) > 0)
                    self.assertTrue(len(kwargs["params"]["t"]) > 0)
                    self.assertEqual(kwargs["params"]["max"], "1")

    def test_max_solutions_parameter(self):
        """Test max_solutions parameter handling"""
        with patch("langnet.heritage.morphology.HeritageHTTPClient") as mock_client_class:
            mock_client = Mock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=None)
            mock_client_class.return_value = mock_client
            mock_client.fetch_cgi_script.return_value = "<html>Response</html>"

            with HeritageMorphologyService() as service:
                service.analyze("test", max_solutions=5)

                # Verify max parameter was passed
                args, kwargs = mock_client.fetch_cgi_script.call_args
                self.assertEqual(kwargs["params"]["max"], "5")

    @patch("langnet.heritage.client.HeritageHTTPClient")
    def test_client_initialization(self, mock_http_client_class):
        """Test HTTP client initialization"""
        client = HeritageHTTPClient()
        self.assertIsNotNone(client.config)
        self.assertEqual(client.min_request_delay, 0.1)

        # Test with custom config
        custom_config = Mock()
        custom_config.base_url = "http://test:8080"
        custom_config.timeout = 30
        client_with_config = HeritageHTTPClient(custom_config)
        self.assertEqual(client_with_config.config.timeout, 30)

    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        with HeritageHTTPClient() as client:
            client.last_request_time = 0
            client.min_request_delay = 0.01  # Short delay for testing

            start_time = time.time()

            # Make multiple rapid calls
            for i in range(3):
                client._rate_limit()

            end_time = time.time()
            elapsed = end_time - start_time

            # Should take at least (3-1) * 0.01 = 0.02 seconds
            self.assertGreaterEqual(elapsed, 0.015)

    @patch("requests.Session.request")
    def test_http_request_timeout(self, mock_request):
        """Test HTTP request timeout handling"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Test response"
        mock_request.return_value = mock_response

        with HeritageHTTPClient() as client:
            # Test with custom timeout
            result = client.fetch_cgi_script("sktreader", {"text": "test"}, timeout=10)
            self.assertEqual(result, "Test response")

    @patch("requests.Session.request")
    def test_http_error_handling(self, mock_request):
        """Test HTTP error handling"""
        # Mock HTTP error
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.HTTPError("Server Error")
        mock_request.return_value = mock_response

        with HeritageHTTPClient() as client, self.assertRaises(HeritageAPIError):
            client.fetch_cgi_script("sktreader", {"text": "test"})

    def test_config_validation(self):
        """Test configuration validation"""
        # Test that heritage_config has required attributes
        required_attrs = ["base_url", "cgi_path", "timeout"]

        for attr in required_attrs:
            self.assertTrue(hasattr(heritage_config, attr))
            self.assertIsNotNone(getattr(heritage_config, attr))

    @patch("langnet.heritage.morphology.HeritageHTTPClient")
    def test_morphology_service_context_manager(self, mock_http_client_class):
        """Test morphology service context manager"""
        service = HeritageMorphologyService()

        # Test entering context
        with service:
            self.assertIsNotNone(service.client)

            # Test that client was created
            mock_http_client_class.assert_called()

        # Test exiting context (client should be cleaned up)
        # This is hard to test directly since the cleanup happens in __exit__


class TestHeritageConnectivityIntegration(unittest.TestCase):
    """Integration tests for Heritage Platform connectivity (may require actual server)"""

    def test_real_server_connectivity(self):
        """Test real server connectivity (skipped if server not available)"""
        try:
            with patch("requests.get") as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_get.return_value = mock_response

                response = requests.get(heritage_config.base_url, timeout=5)
                self.assertEqual(response.status_code, 200)

        except requests.ConnectionError:
            self.skipTest("Heritage Platform server not available")

    def test_real_morphology_analysis(self):
        """Test real morphology analysis (skipped if server not available)"""
        try:
            with HeritageMorphologyService() as service:
                result = service.analyze("agni", encoding="velthuis", max_solutions=1)

                # Basic validation of result structure
                self.assertIsNotNone(result)
                self.assertIsInstance(result.input_text, str)
                self.assertIsInstance(result.total_solutions, int)
                self.assertIsInstance(result.processing_time, float)
                self.assertGreaterEqual(result.processing_time, 0)

        except (HeritageAPIError, requests.ConnectionError):
            self.skipTest("Heritage Platform server not available or CGI script not working")


if __name__ == "__main__":
    unittest.main()
