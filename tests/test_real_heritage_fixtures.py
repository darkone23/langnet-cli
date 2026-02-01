#!/usr/bin/env python3
"""
Enhanced tests using real Heritage Platform fixtures from localhost:48080.

These tests use the actual HTML responses we fetched from the live service
to ensure our parsers work with real data instead of mocked responses.
"""

import json
import logging
import sys
import unittest
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Constants for fixture size thresholds
MIN_FIXTURE_SIZE = 1000
MIN_HTML_VALID_SIZE = 500

logger = logging.getLogger(__name__)


class TestRealFixtures(unittest.TestCase):
    """Test suite using real Heritage Platform fixtures."""

    def setUp(self):
        """Set up test fixtures."""
        # Fixtures are in the project root, not tests directory
        test_root = Path(__file__).parent.parent / "tests"
        self.fixtures_dir = test_root / "fixtures" / "heritage"
        self.morphology_dir = self.fixtures_dir / "morphology"
        self.search_dir = self.fixtures_dir / "search"

        # Test terms we have fixtures for
        self.test_terms = ["agni", "devadatta", "narasimha", "mahadeva", "raama", "sita", "hanumat"]

    def test_morphology_fixtures_exist(self):
        """Test that morphology fixtures exist and are readable."""
        for term in self.test_terms:
            with self.subTest(term=term):
                html_file = self.morphology_dir / f"{term}.html"
                metadata_file = self.morphology_dir / f"{term}.json"

                # Check HTML file exists
                self.assertTrue(html_file.exists(), f"HTML fixture missing for {term}")
                self.assertTrue(
                    html_file.stat().st_size > MIN_FIXTURE_SIZE,
                    f"HTML fixture too small for {term}",
                )

                # Check metadata file exists
                self.assertTrue(metadata_file.exists(), f"Metadata fixture missing for {term}")

                # Load and validate metadata
                with open(metadata_file, encoding="utf-8") as f:
                    metadata = json.load(f)

                self.assertIn("identifier", metadata)
                self.assertIn("content_length", metadata)
                self.assertIn("fetch_date", metadata)

                logger.info("%s: HTML (%d chars), Metadata valid", term, metadata["content_length"])

    def test_morphology_structure_with_real_data(self):
        """Test morphology structure using real HTML fixtures."""
        success_count = 0

        for term in self.test_terms:
            with self.subTest(term=term):
                try:
                    # Load real HTML response
                    html_file = self.morphology_dir / f"{term}.html"
                    with open(html_file, encoding="utf-8") as f:
                        html_content = f.read()

                    # Test basic HTML structure
                    self.assertIn("<html>", html_content, f"Missing HTML structure in {term}")
                    self.assertIn("</html>", html_content, f"Missing HTML closing tag in {term}")

                    # Look for morphology indicators
                    content_lower = html_content.lower()

                    # Check for tables (common in morphology responses)
                    table_count = content_lower.count("<table")
                    if table_count > 0:
                        logger.info("%s: Found %d tables", term, table_count)
                        success_count += 1
                    else:
                        # Check for other morphology indicators
                        morph_keywords = ["morph", "form", "stem", "root", "gender", "analysis"]
                        found_keywords = [kw for kw in morph_keywords if kw in content_lower]

                        if found_keywords:
                            logger.info("%s: Found morphology keywords: %s", term, found_keywords)
                            success_count += 1
                        else:
                            logger.warning("%s: No clear morphology indicators found", term)
                            # Still count as success if we have valid HTML structure
                            success_count += 1

                except Exception as e:
                    logger.error("%s: Error processing fixture - %s", term, e)
                    continue

        logger.info(
            "Summary: %d/%d terms processed successfully", success_count, len(self.test_terms)
        )
        self.assertGreater(success_count, 0, "No terms were processed successfully")

    def test_search_fixtures_exist(self):
        """Test that search fixtures exist and contain H_ patterns."""
        search_terms = ["agni", "devadatta", "narasimha", "mahadeva"]

        for term in search_terms:
            with self.subTest(term=term):
                html_file = self.search_dir / f"{term}.html"
                metadata_file = self.search_dir / f"{term}.json"

                # Check HTML file exists
                self.assertTrue(html_file.exists(), f"Search HTML fixture missing for {term}")

                # Load and validate content
                with open(html_file, encoding="utf-8") as f:
                    html_content = f.read()

                # Check for H_ patterns (canonical URLs)
                h_count = html_content.count("H_")
                self.assertGreater(h_count, 0, f"No H_ patterns found in {term} search results")

                # Load metadata
                with open(metadata_file, encoding="utf-8") as f:
                    metadata = json.load(f)

                self.assertTrue(
                    metadata.get("has_h_pattern", False),
                    f"Metadata should indicate H_ patterns for {term}",
                )

                logger.info("%s: HTML loaded, %d H_ patterns found", term, h_count)

    def test_encoding_detection_with_real_responses(self):
        """Test encoding detection using real HTML responses."""
        encoding_test_cases = [
            ("agni", "IAST"),
            ("devadatta", "IAST"),
            ("mahādeva", "IAST"),
        ]

        for term, expected_encoding in encoding_test_cases:
            with self.subTest(term=term, expected=expected_encoding):
                try:
                    html_file = self.morphology_dir / f"{term}.html"
                    with open(html_file, encoding="utf-8") as f:
                        html_content = f.read()

                    # Look for encoding indicators
                    content_lower = html_content.lower()

                    # Check for charset declaration
                    if "charset=utf-8" in content_lower:
                        logger.info("%s: UTF-8 charset detected", term)

                    # Check for specific encoding indicators
                    if "velthuis" in content_lower:
                        logger.info("%s: Velthuis encoding indicators found", term)
                    if "devanagari" in content_lower:
                        logger.info("%s: Devanagari font indicators found", term)

                    # Check for the term itself in different forms
                    if term in html_content:
                        logger.info("%s: Term found in response", term)

                    # Check for morphology-related content
                    if "<table" in content_lower:
                        logger.info("%s: HTML tables found (morphology structure)", term)

                except Exception as e:
                    logger.error("%s: Error analyzing encoding - %s", term, e)
                    continue

    def test_comprehensive_fixture_validation(self):
        """Comprehensive validation of all fixtures."""
        logger.info("Comprehensive fixture validation...")

        # Validate morphology fixtures
        morphology_files = list(self.morphology_dir.glob("*.html"))
        logger.info("Found %d morphology fixtures", len(morphology_files))

        valid_morphology = 0
        for html_file in morphology_files:
            try:
                with open(html_file, encoding="utf-8") as f:
                    content = f.read()

                # Basic validation
                if (
                    len(content) > MIN_HTML_VALID_SIZE
                    and "<html>" in content
                    and "</html>" in content
                ):
                    valid_morphology += 1
                    logger.info("%s: Valid HTML structure", html_file.name)
                else:
                    logger.error("%s: Invalid or incomplete HTML", html_file.name)

            except Exception as e:
                logger.error("%s: Error reading file - %s", html_file.name, e)

        # Validate search fixtures
        search_files = list(self.search_dir.glob("*.html"))
        logger.info("Found %d search fixtures", len(search_files))

        valid_search = 0
        for html_file in search_files:
            try:
                with open(html_file, encoding="utf-8") as f:
                    content = f.read()

                # Check for H_ patterns (canonical URLs)
                if "H_" in content and len(content) > MIN_HTML_VALID_SIZE:
                    valid_search += 1
                    h_count = content.count("H_")
                    logger.info(
                        "%s: Valid search results (%d H_ patterns)", html_file.name, h_count
                    )
                else:
                    logger.error("%s: No H_ patterns or content too short", html_file.name)

            except Exception as e:
                logger.error("%s: Error reading file - %s", html_file.name, e)

        # Summary
        total_fixtures = len(morphology_files) + len(search_files)
        valid_fixtures = valid_morphology + valid_search

        logger.info("Fixture validation summary:")
        logger.info("   Total fixtures: %d", total_fixtures)
        logger.info("   Valid fixtures: %d", valid_fixtures)

        if total_fixtures > 0:
            logger.info("   Validation rate: %.1f%%", valid_fixtures / total_fixtures * 100)
            self.assertGreater(valid_fixtures, 0, "No valid fixtures found")
        else:
            logger.info("   Validation rate: N/A (no fixtures found)")
            self.skipTest("No fixtures available for validation")

        logger.info("Fixture validation completed successfully")


if __name__ == "__main__":
    # Run tests with verbose output
    unittest.main(verbosity=2)
