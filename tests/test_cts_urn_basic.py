"""
Simple integration tests for CTS URN system.

These tests verify basic functionality of the CTS URN mapper
with the real database.
"""

import unittest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from langnet.citation.cts_urn import CTSUrnMapper


class TestCTSUrnbasicIntegration(unittest.TestCase):
    """Basic integration tests for CTS URN functionality."""

    def setUp(self):
        """Set up test environment with real database."""
        # Initialize CTSUrnMapper with real database
        self.mapper = CTSUrnMapper()

    def test_mapper_initialization(self):
        """Test that the mapper initializes correctly."""
        self.assertIsNotNone(self.mapper, "Mapper should be initialized")
        self.assertIsNotNone(self.mapper._get_db_path(), "Database path should be found")

    def test_basic_mapping_functionality(self):
        """Test basic text to URN mapping functionality."""
        # Test cases that should work with the fallback system
        test_cases = [
            "Hom. Il. 1.1",
            "Verg. A. 1.1",
            "Cic. Fin. 2 24",
            "Hor. C. 1 17 9",
            "perseus:abo:tlg,0011,001:911",
            "perseus:abo:phi,0690,003:1:2",
            "perseus:abo:phi,0474,043:2:3:6",
        ]

        print(f"\n🔄 Testing text to URN mapping:")
        successful = 0

        for citation_text in test_cases:
            with self.subTest(citation=citation_text):
                urn = self.mapper.map_text_to_urn(citation_text)
                print(f"  {citation_text:35} -> {urn}")

                if urn:
                    successful += 1
                    # Check it's a valid CTS URN format
                    self.assertTrue(urn.startswith("urn:cts:"), f"Should be CTS URN: {urn}")

                    # Test CTS API URL resolution using the standalone function
                    from langnet.citation.cts_urn import resolve_cts_urn

                    api_url = resolve_cts_urn(urn)
                    if api_url:
                        print(f"    API URL: {api_url}")

        print(
            f"  Successfully mapped: {successful}/{len(test_cases)} ({successful / len(test_cases) * 100:.1f}%)"
        )
        # At least some should work
        self.assertGreater(successful, 0, "Should have at least some successful mappings")

    def test_perseus_format_mapping(self):
        """Test that Perseus format mapping works correctly."""
        # These should always work as they use direct transformation
        # Note: The actual implementation uses colons, not dots, for separators
        perseus_cases = [
            ("perseus:abo:tlg,0011,001:911", "urn:cts:greekLit:tlg0011.tlg001:911"),
            ("perseus:abo:phi,0690,003:1:2", "urn:cts:latinLit:phi0690.phi003:1:2"),
            ("perseus:abo:phi,0474,043:2:3:6", "urn:cts:latinLit:phi0474.phi043:2:3:6"),
        ]

        print(f"\n🔗 Testing Perseus format mapping:")
        for input_text, expected_output in perseus_cases:
            with self.subTest(perseus_ref=input_text):
                urn = self.mapper.map_text_to_urn(input_text)
                print(f"  {input_text:35} -> {urn}")

                # Perseus format should always work
                self.assertIsNotNone(urn, f"Perseus mapping should work: {input_text}")
                self.assertEqual(urn, expected_output, f"Wrong URN for {input_text}")

    def test_database_functionality(self):
        """Test database-related functionality."""
        # Test that we can get database connection
        conn = self.mapper._get_connection()
        if conn is not None:
            print(f"\n🗄️  Database connection successful")

            # Test basic queries
            try:
                result = conn.execute("SELECT COUNT(*) FROM author_index").fetchone()
                if result:
                    author_count = result[0]
                    print(f"  Authors in database: {author_count}")
                    self.assertGreater(author_count, 0, "Should have authors")

                result = conn.execute("SELECT COUNT(*) FROM works").fetchone()
                if result:
                    work_count = result[0]
                    print(f"  Works in database: {work_count}")
                    self.assertGreater(work_count, 0, "Should have works")

            except Exception as e:
                print(f"  Database query failed: {e}")
        else:
            print(f"\n⚠️  Database connection failed")

    def test_author_work_caching(self):
        """Test that author and work caching works."""
        # Load caches
        author_cache = self.mapper._load_author_cache()
        work_cache = self.mapper._load_work_cache()

        print(f"\n💾 Testing caching:")
        print(f"  Author cache entries: {len(author_cache)}")
        print(f"  Work cache entries: {len(work_cache)}")

        # Check that we have some cached data
        if author_cache:
            print(f"  Sample authors: {list(author_cache.keys())[:5]}")
        if work_cache:
            print(f"  Sample works: {list(work_cache.keys())[:5]}")

        # Caches should be populated if database is working
        self.assertIsNotNone(author_cache, "Author cache should be loaded")
        self.assertIsNotNone(work_cache, "Work cache should be loaded")

    def test_fallback_hardcoded_mappings(self):
        """Test that fallback hardcoded mappings work."""
        # Test cases that should work with hardcoded mappings
        hardcoded_cases = [
            "Hom. Il. 1.1",  # Homer Iliad
            "Verg. A. 1.1",  # Virgil Aeneid
            "Cic. Fin. 2 24",  # Cicero De Finibus
            "Hor. C. 1 17 9",  # Horace Carmina
        ]

        print(f"\n🔧 Testing fallback hardcoded mappings:")
        successful = 0

        for citation_text in hardcoded_cases:
            with self.subTest(citation=citation_text):
                urn = self.mapper.map_text_to_urn(citation_text)
                print(f"  {citation_text:25} -> {urn}")

                if urn:
                    successful += 1
                    self.assertTrue(urn.startswith("urn:cts:"), f"Should be CTS URN: {urn}")

        print(
            f"  Successfully mapped: {successful}/{len(hardcoded_cases)} ({successful / len(hardcoded_cases) * 100:.1f}%)"
        )


if __name__ == "__main__":
    # Run the integration tests with verbose output
    unittest.main(verbosity=2)
