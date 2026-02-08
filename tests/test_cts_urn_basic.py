"""
Simplified integration tests for CTS URN system.

These tests verify basic functionality of CTS URN mapper
with real database, focusing on database connectivity and caching.
"""

import sys
import unittest
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

    def test_phi_urn_metadata_fallback(self):
        """Latin PHI URNs should resolve with current Perseus-derived index."""
        urn = "urn:cts:latinLit:phi0893.phi004:1:4:95"
        meta = self.mapper.get_urn_metadata(urn)
        self.assertIsNotNone(meta, "phi-prefixed URNs should map to metadata via fallback")
        self.assertIn("Hor", meta.get("author", ""))
        self.assertIn(meta.get("work"), {"Satires", "Sermones"})

    def test_phi_urn_hint_overrides_mismatched_work(self):
        """When phi→lat lookup yields a mismatched work title, prefer the citation hint."""
        urn = "urn:cts:latinLit:phi0474.phi040:48:160"
        meta = self.mapper.get_urn_metadata(urn, citation_text="Cic. Or. 48, 160")
        self.assertIsNotNone(meta, "phi URN with hint should resolve")
        self.assertIn("Cicero", meta.get("author", ""))
        self.assertEqual(meta.get("work"), "Orator")

    def test_greek_tlg_lookup(self):
        """Greek TLG URN should resolve to author/work."""
        urn = "urn:cts:greekLit:tlg0012.tlg001:1.1"
        meta = self.mapper.get_urn_metadata(urn, citation_text="Hom. Il. 1.1")
        self.assertIsNotNone(meta)
        self.assertIn("Homer", meta.get("author", ""))
        self.assertEqual(meta.get("work"), "Iliad")

    def test_stoa_lookup_from_legacy_gap(self):
        """Non-Perseus stoa URN should be available via legacy supplement."""
        urn = "urn:cts:latinLit:stoa0023.stoa001:25:1:5"
        meta = self.mapper.get_urn_metadata(urn, citation_text="Amm. 25, 1, 5")
        self.assertIsNotNone(meta)
        self.assertIn("Ammianus", meta.get("author", ""))
        self.assertEqual(meta.get("work"), "Res Gestae")


if __name__ == "__main__":
    unittest.main(verbosity=2)
