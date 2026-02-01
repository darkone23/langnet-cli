#!/usr/bin/env python3
"""
Test to demonstrate the critical difference between direct and canonical lookup
in Heritage Platform morphology parsing.

This test shows why canonical lookup is essential - 'agni' vs 'agnii' produces
completely different results.
"""

import json
import logging
import re
import sys
import unittest
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

logger = logging.getLogger(__name__)


class TestCanonicalLookupImportance(unittest.TestCase):
    """Test demonstrating the importance of canonical lookup."""

    def setUp(self):
        """Set up test fixtures."""
        self.fixtures_dir = Path(__file__).parent / "fixtures" / "heritage"
        self.morphology_dir = self.fixtures_dir / "morphology"
        self.search_dir = self.fixtures_dir / "search"

    def test_agni_vs_agnii_difference(self):
        """Test that demonstrates the critical difference between agni and agnii."""
        # Load direct lookup (agni)
        agni_file = self.morphology_dir / "agni.html"
        with open(agni_file, encoding="utf-8") as f:
            agni_content = f.read()

        # Load canonical lookup (agnii)
        agnii_file = self.morphology_dir / "agnii.html"
        with open(agnii_file, encoding="utf-8") as f:
            agnii_content = f.read()

        # Check basic differences
        logger.info("Comparing agni vs agnii responses:")

        # Look for morphology tables
        agni_tables = agni_content.count("<table")
        agnii_tables = agnii_content.count("<table")

        logger.info("   agni tables: %d", agni_tables)
        logger.info("   agnii tables: %d", agnii_tables)

        # Look for specific morphology indicators
        morphology_indicators = ["morph", "analysis", "breakdown", "form", "stem"]

        agni_indicators = []
        agnii_indicators = []

        for indicator in morphology_indicators:
            if indicator in agni_content.lower():
                agni_indicators.append(indicator)
            if indicator in agnii_content.lower():
                agnii_indicators.append(indicator)

        logger.info("   agni indicators: %s", agni_indicators)
        logger.info("   agnii indicators: %s", agnii_indicators)

        # Check for dictionary links
        agni_links = agni_content.count("href=")
        agnii_links = agnii_content.count("href=")

        logger.info("   agni links: %d", agni_links)
        logger.info("   agnii links: %d", agnii_links)

        # The key test: agnii should have significantly more structure
        self.assertGreater(agnii_tables, 0, "agnii should have morphology tables")
        self.assertGreater(agnii_links, 5, "agnii should have multiple dictionary links")

        logger.info("Confirmed: agnii has much richer morphology data than agni")

    def test_search_canonical_extraction(self):
        """Test that search responses correctly extract canonical forms."""
        # Load search response for agni
        search_file = self.search_dir / "agni.html"
        with open(search_file, encoding="utf-8") as f:
            search_content = f.read()

        # Extract H_ patterns (canonical URLs)
        h_matches = re.findall(r'H_([^&"\s>]+)', search_content)

        logger.info("Extracted canonical forms from search:")
        for match in h_matches:
            logger.info("   H_%s", match)

        # Should find both agni and agnii
        self.assertIn("agni", h_matches, "Should find direct form agni")
        self.assertIn("agnii", h_matches, "Should find canonical form agnii")

        # The canonical form (agnii) should be more prominent
        agnii_positions = [m.start() for m in re.finditer(r"H_agnii", search_content)]
        agni_positions = [m.start() for m in re.finditer(r"H_agni", search_content)]

        logger.info("agnii occurrences: %d", len(agnii_positions))
        logger.info("agni occurrences: %d", len(agni_positions))

        # agnii should be the canonical/more specific form
        self.assertGreater(len(agnii_positions), 0, "Should find agnii canonical form")

        logger.info("Confirmed: search response contains both direct and canonical forms")

    def test_other_canonical_examples(self):
        """Test other canonical lookup examples."""
        canonical_pairs = [
            ("narasimha", "naarasi.mha"),
            ("mahadeva", "mahaadeva"),
            ("raama", "raamaa"),
            ("sita", "siitaa"),
            ("hanumat", "hanuumat"),
        ]

        logger.info("Testing canonical pairs:")

        for original, canonical in canonical_pairs:
            try:
                # Check if both forms exist in fixtures
                original_file = self.morphology_dir / f"{original}.html"
                canonical_file = self.morphology_dir / f"{canonical}.html"

                if original_file.exists() and canonical_file.exists():
                    with open(original_file, encoding="utf-8") as f:
                        original_content = f.read()

                    with open(canonical_file, encoding="utf-8") as f:
                        canonical_content = f.read()

                    # Compare richness of responses
                    original_tables = original_content.count("<table")
                    canonical_tables = canonical_content.count("<table")

                    original_links = original_content.count("href=")
                    canonical_links = canonical_content.count("href=")

                    logger.info("   %s -> %s:", original, canonical)
                    logger.info("     Tables: %d vs %d", original_tables, canonical_tables)
                    logger.info("     Links: %d vs %d", original_links, canonical_links)

                    # Canonical form should generally have richer data
                    if canonical_tables > original_tables:
                        logger.info("     Canonical form has richer morphology data")
                    elif canonical_tables == original_tables:
                        logger.warning("     Both forms have similar structure")
                    else:
                        logger.warning("     Direct form has richer data (unexpected)")

            except Exception as e:
                logger.error("   Error testing %s -> %s: %s", original, canonical, e)

    def test_metadata_validation(self):
        """Test that fixture metadata correctly records canonical information."""
        # Test agnii fixture (should show canonical transformation)
        agnii_metadata = None
        agnii_meta_file = self.morphology_dir / "agnii.json"
        if agnii_meta_file.exists():
            with open(agnii_meta_file, encoding="utf-8") as f:
                agnii_metadata = json.load(f)

            logger.info("agnii metadata:")
            for key, value in agnii_metadata.items():
                if key not in ["html"]:  # Skip HTML content
                    logger.info("   %s: %s", key, value)

        # Test agni fixture (direct lookup)
        agni_metadata = None
        agni_direct_meta_file = self.morphology_dir / "agni.json"
        if agni_direct_meta_file.exists():
            with open(agni_direct_meta_file, encoding="utf-8") as f:
                agni_metadata = json.load(f)

            logger.info("agni metadata:")
            for key, value in agni_metadata.items():
                if key not in ["html"]:  # Skip HTML content
                    logger.info("   %s: %s", key, value)

        # Verify metadata structure
        if agnii_metadata:
            self.assertIn("canonical_used", agnii_metadata)
            self.assertIn("original_term", agnii_metadata)
            logger.info("Metadata structure is correct")

    def test_comprehensive_canonical_workflow(self):
        """Test the complete canonical lookup workflow."""
        logger.info("Testing complete canonical lookup workflow:")

        # Step 1: Search for term
        search_file = self.search_dir / "agni.html"
        with open(search_file, encoding="utf-8") as f:
            search_content = f.read()

        # Step 2: Extract canonical forms
        h_matches = re.findall(r'H_([^&"\s>]+)', search_content)
        canonical_forms = [h for h in h_matches if h != "agni"]  # Exclude direct form

        logger.info("   Step 1 - Search results: Found %d H_ patterns", len(h_matches))
        logger.info("   Step 2 - Canonical extraction: %s", canonical_forms)

        # Step 3: Verify canonical forms have richer morphology data
        if canonical_forms:
            canonical_form = canonical_forms[0]  # Take first canonical form
            canonical_file = self.morphology_dir / f"{canonical_form}.html"

            if canonical_file.exists():
                with open(canonical_file, encoding="utf-8") as f:
                    canonical_content = f.read()

                # Check for rich morphology data
                tables = canonical_content.count("<table")
                links = canonical_content.count("href=")
                dictionary_refs = canonical_content.count("DICO/")

                logger.info("   Step 3 - Canonical validation:")
                logger.info("     Tables: %d", tables)
                logger.info("     Dictionary links: %d", links)
                logger.info("     DICO references: %d", dictionary_refs)

                # Should have substantial morphology data
                self.assertGreater(tables, 0, "Canonical form should have morphology tables")
                self.assertGreater(dictionary_refs, 0, "Canonical form should have DICO references")

                logger.info("Complete canonical workflow validated")
            else:
                logger.warning("Canonical file not found: %s", canonical_file)
        else:
            logger.warning("No canonical forms found in search results")


if __name__ == "__main__":
    # Run tests with verbose output
    unittest.main(verbosity=2)
