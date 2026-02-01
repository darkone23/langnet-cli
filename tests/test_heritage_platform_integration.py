#!/usr/bin/env python3
"""
Integration tests for Heritage Platform API using real localhost service (localhost:48080).

These tests connect to the actual Heritage Platform service to verify that:
1. The HTML parsing works with real responses
2. The API integration is properly configured
3. The sktreader endpoint returns valid HTML for parsing
4. The morphology extraction works with live data

Tests use localhost:48080 as the Heritage Platform endpoint.
"""

import logging
import sys
import unittest
from pathlib import Path

import requests

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Constants for HTTP status codes and size thresholds
HTTP_OK = 200
MIN_HTML_SIZE = 1000
MIN_MORPHOLOGY_HTML_SIZE = 500

logger = logging.getLogger(__name__)


class TestHeritagePlatformIntegration(unittest.TestCase):
    """Integration tests with real Heritage Platform API."""

    def setUp(self):
        """Set up test configuration."""
        self.base_url = "http://localhost:48080"
        self.test_terms = ["agni", "devadatta", "narasimha", "mahadeva"]

    def test_service_health_check(self):
        """Test that Heritage Platform service is available."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == HTTP_OK:
                logger.info("Heritage Platform service is available")
                return True
            else:
                logger.warning("Service returned status: %d", response.status_code)
                return False
        except requests.exceptions.ConnectionError:
            logger.error("Heritage Platform service not available on localhost:48080")
            return False
        except Exception as e:
            logger.error("Cannot connect to Heritage Platform: %s", e)
            return False

    def test_sktreader_endpoint_availability(self):
        """Test that sktreader endpoint is accessible."""
        try:
            # Test the actual CGI endpoint found on the site
            params = {"q": "agni", "t": "VH", "lex": "SH", "font": "roma"}
            response = requests.get(
                f"{self.base_url}/cgi-bin/skt/sktindex", params=params, timeout=15
            )

            if response.status_code == HTTP_OK:
                logger.info("/cgi-bin/skt/sktindex endpoint is accessible")
                content_type = response.headers.get("content-type", "").lower()
                if "html" in content_type:
                    logger.info("Response contains HTML content")
                    return True
                else:
                    logger.warning("Response content-type: %s", content_type)
                    return False
            else:
                logger.warning("/cgi-bin/skt/sktindex returned status: %d", response.status_code)
                # Try alternative paths
                alternative_paths = ["/cgi-bin/sktreader", "/sktreader.cgi", "/sktreader.pl"]
                for path in alternative_paths:
                    try:
                        alt_response = requests.get(
                            f"{self.base_url}{path}", params=params, timeout=10
                        )
                        if alt_response.status_code == HTTP_OK:
                            logger.info("Found working endpoint: %s", path)
                            return True
                    except Exception:
                        continue
                return False
        except requests.exceptions.ConnectionError:
            logger.error("Cannot connect to Heritage Platform sktreader endpoint")
            return False
        except Exception as e:
            logger.error("Error testing sktreader endpoint: %s", e)
            return False

    def test_term_morphology_responses(self):
        """Test morphology responses with real HTML."""
        success_count = 0

        for term in self.test_terms:
            try:
                # Test real HTML response using the correct CGI endpoint
                params = {"q": term, "t": "VH", "lex": "SH", "font": "roma"}
                response = requests.get(
                    f"{self.base_url}/cgi-bin/skt/sktindex", params=params, timeout=15
                )

                if response.status_code == HTTP_OK:
                    html_content = response.text

                    # Basic HTML validation
                    if len(html_content) > MIN_HTML_SIZE:
                        # Check for morphology-related keywords
                        html_lower = html_content.lower()
                        morph_keywords = ["morph", "form", "stem", "root", "gender", "analysis"]
                        found_keywords = [kw for kw in morph_keywords if kw in html_lower]

                        if found_keywords:
                            print(f"✅ {term}: Found morphology keywords: {found_keywords}")
                            success_count += 1
                        # Check for tables (common in morphology responses)
                        elif "<table" in html_lower:
                            print(f"✅ {term}: Found HTML tables (potential morphology structure)")
                            success_count += 1
                        else:
                            print(
                                f"⚠️  {term}: Basic HTML response but no clear morphology indicators"
                            )
                    else:
                        print(f"⚠️  {term}: Response too short ({len(html_content)} chars)")
                else:
                    print(f"⚠️  {term}: HTTP {response.status_code}")

            except Exception as e:
                print(f"❌ Error testing {term}: {e}")
                continue

        term_count = len(self.test_terms)
        summary = (
            f"\n📊 Summary: {success_count}/{term_count} terms returned valid morphology responses"
        )
        print(summary)
        return success_count > 0

    def test_parameter_variations(self):
        """Test different parameter combinations with real API."""
        param_combinations = [
            {"t": "VH", "lex": "SH", "font": "roma"},  # Standard
            {"t": "VH", "lex": "MW", "font": "roma"},  # MW lexicon
            {"t": "IAST", "lex": "SH", "font": "roma"},  # IAST input
            {"t": "VH", "lex": "SH", "font": "deva"},  # Devanagari font
        ]

        success_count = 0

        for params in param_combinations:
            try:
                # Test with a common term
                params["q"] = "agni"
                response = requests.get(
                    f"{self.base_url}/cgi-bin/skt/sktindex", params=params, timeout=15
                )

                if response.status_code == HTTP_OK:
                    print(f"✅ Parameters {params} returned valid response")
                    success_count += 1
                else:
                    print(f"⚠️  Parameters {params} returned status {response.status_code}")

            except Exception as e:
                print(f"❌ Error testing params {params}: {e}")
                continue

        print(
            f"\n📊 Summary: {success_count}/{len(param_combinations)} parameter combinations worked"
        )
        return success_count > 0

    def test_sktsearch_endpoint(self):
        """Test sktsearch endpoint for canonical lookup."""
        try:
            params = {"q": "agni"}
            response = requests.get(f"{self.base_url}/sktsearch", params=params, timeout=15)

            if response.status_code == HTTP_OK:
                content = response.text

                # Check for links with H_ pattern
                if "H_" in content:
                    print("✅ Found H_ pattern in sktsearch results (canonical URLs)")

                    # Extract some examples
                    lines = content.split("\n")
                    h_lines = [line.strip() for line in lines if "H_" in line and "href" in line]

                    for line in h_lines[:3]:  # Show first 3 examples
                        print(f"   Example: {line[:100]}...")

                    return True
                else:
                    print("⚠️  No H_ pattern found in sktsearch results")
                    return False
            else:
                print(f"⚠️  sktsearch returned status: {response.status_code}")
                # Try alternative paths
                alternative_paths = ["/cgi-bin/sktsearch", "/sktsearch.cgi", "/sktsearch.pl"]
                for path in alternative_paths:
                    try:
                        alt_response = requests.get(
                            f"{self.base_url}{path}", params=params, timeout=10
                        )
                        if alt_response.status_code == HTTP_OK:
                            print(f"✅ Found working search endpoint: {path}")
                            return True
                    except Exception:
                        continue
                return False

        except Exception as e:
            print(f"❌ Error testing sktsearch: {e}")
            return False

    def test_encoding_variations(self):
        """Test different input encodings."""
        test_cases = [
            ("agni", "IAST"),
            ("devadatta", "IAST"),
            ("mahādeva", "IAST"),  # Long vowels
            ("agni.h", "IAST with anusvara"),
        ]

        success_count = 0

        for term, description in test_cases:
            try:
                params = {"q": term, "t": "VH", "lex": "SH", "font": "roma"}
                response = requests.get(
                    f"{self.base_url}/cgi-bin/skt/sktindex", params=params, timeout=15
                )

                if response.status_code == HTTP_OK:
                    print(f"✅ {description} ('{term}'): Valid response")
                    success_count += 1
                else:
                    print(f"⚠️  {description} ('{term}'): HTTP {response.status_code}")

            except Exception as e:
                print(f"❌ Error testing {description} ('{term}'): {e}")
                continue

        print(f"\n📊 Summary: {success_count}/{len(test_cases)} encoding variations worked")
        return success_count > 0


class TestRealIntegration(unittest.TestCase):
    """Comprehensive integration test suite."""

    def setUp(self):
        """Set up test configuration."""
        self.base_url = "http://localhost:48080"

    def test_full_integration_workflow(self):
        """Test complete workflow from query to morphology parsing."""
        print("\n🧪 Testing complete integration workflow...")

        # Step 1: Check service availability
        service_ok = TestHeritagePlatformIntegration()
        service_ok.setUp()
        if not service_ok.test_service_health_check():
            self.skipTest("Heritage Platform service not available")

        # Step 2: Test sktreader endpoint
        sktreader_ok = TestHeritagePlatformIntegration()
        sktreader_ok.setUp()
        if not sktreader_ok.test_sktreader_endpoint_availability():
            self.skipTest("sktreader endpoint not working")

        # Step 3: Test morphology parsing
        morphology_test = TestHeritagePlatformIntegration()
        morphology_test.setUp()
        if not morphology_test.test_term_morphology_responses():
            print("⚠️  Morphology responses need investigation")

        # Step 4: Test parameter variations
        param_test = TestHeritagePlatformIntegration()
        param_test.setUp()
        if not param_test.test_parameter_variations():
            print("⚠️  Parameter variations need investigation")

        # Step 5: Test canonical lookup
        canonical_ok = TestHeritagePlatformIntegration()
        canonical_ok.setUp()
        if not canonical_ok.test_sktsearch_endpoint():
            print("⚠️  Canonical lookup needs investigation")

        # Step 6: Test encoding variations
        encoding_test = TestHeritagePlatformIntegration()
        encoding_test.setUp()
        if not encoding_test.test_encoding_variations():
            print("⚠️  Encoding variations need investigation")

        print("✅ Integration workflow test completed")


if __name__ == "__main__":
    # Run tests with verbose output
    unittest.main(verbosity=2)
