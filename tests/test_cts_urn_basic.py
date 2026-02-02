"""
Simplified integration tests for CTS URN system.

These tests verify basic functionality of CTS URN mapper
with real database, focusing on database connectivity and caching.
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
        self.mapper = CTSUrnMapper()

    def test_mapper_initialization(self):
        """Test that mapper initializes correctly."""
        self.assertIsNotNone(self.mapper, "Mapper should be initialized")
        self.assertIsNotNone(self.mapper._get_db_path(), "Database path should be found")

    def test_database_functionality(self):
        """Test database-related functionality."""
        conn = self.mapper._get_connection()
        self.assertIsNotNone(conn, "Should have database connection")

        result = conn.execute("SELECT COUNT(*) FROM author_index").fetchone()
        author_count = result[0]
        self.assertGreater(author_count, 0, "Should have authors")

        result = conn.execute("SELECT COUNT(*) FROM works").fetchone()
        work_count = result[0]
        self.assertGreater(work_count, 0, "Should have works")

    def test_author_work_caching(self):
        """Test that author and work caching works."""
        author_cache = self.mapper._load_author_cache()
        work_cache = self.mapper._load_work_cache()

        self.assertIsNotNone(author_cache, "Author cache should be loaded")
        self.assertIsNotNone(work_cache, "Work cache should be loaded")


if __name__ == "__main__":
    unittest.main(verbosity=2)
