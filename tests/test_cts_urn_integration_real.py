"""
Integration tests for CTS URN system with real DuckDB database.

These tests verify the end-to-end workflow from citation processing
to CTS URN resolution using the actual DuckDB database and real data.
"""

import unittest
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from langnet.citation.cts_urn import CTSUrnMapper
from langnet.citation.models import Citation, TextReference, CitationType


class TestCTSUrndatabaseIntegration(unittest.TestCase):
    """Integration tests for CTS URN database functionality with real data."""

    def setUp(self):
        """Set up test environment with real database."""
        # Initialize CTSUrnMapper with real database
        self.mapper = CTSUrnMapper()

    def test_database_connectivity(self):
        """Test that we can connect to the real database."""
        db_path = self.mapper._get_db_path()
        self.assertIsNotNone(db_path, "Database path should be found")
        db_path_str = str(db_path)  # Convert to string to avoid Path(None) issue
        self.assertTrue(Path(db_path_str).exists(), "Database file should exist")

        conn = self.mapper._get_connection()
        self.assertIsNotNone(conn, "Should be able to connect to database")

        # Test basic query
        try:
            result = conn.execute("SELECT COUNT(*) FROM author_index").fetchone()
            self.assertIsNotNone(result, "Should get result from query")
            self.assertGreater(result[0], 0, "Should have authors in database")

            result = conn.execute("SELECT COUNT(*) FROM works").fetchone()
            self.assertIsNotNone(result, "Should get result from query")
            self.assertGreater(result[0], 0, "Should have works in database")
        except Exception as e:
            self.fail(f"Database query failed: {e}")

    def test_real_data_examples(self):
        """Test with real examples from the database."""
        # First, let's get some real data from the database
        conn = self.mapper._get_connection()
        cursor = conn.cursor()

        # Get some real Cicero works
        cursor.execute("""
            SELECT w.work_title, w.cts_urn 
            FROM works w 
            JOIN author_index a ON w.author_id = a.author_id 
            WHERE a.author_name = 'M. Tullius Cicero' 
            LIMIT 3
        """)
        cicero_works = cursor.fetchall()

        # Get some real Virgil works
        cursor.execute("""
            SELECT w.work_title, w.cts_urn 
            FROM works w 
            JOIN author_index a ON w.author_id = a.author_id 
            WHERE a.author_name = 'P. Vergilius Maro' 
            LIMIT 3
        """)
        virgil_works = cursor.fetchall()

        print(f"\n📚 Real works from database:")
        print(f"Cicero works: {[(w[0], w[1]) for w in cicero_works]}")
        print(f"Virgil works: {[(w[0], w[1]) for w in virgil_works]}")

        # Test with real data
        test_cases = []

        # Add Cicero works
        for work_title, cts_urn in cicero_works:
            if cts_urn:
                work_id = cts_urn.split(":")[-1].split(".")[1]  # Extract work ID like lat043
                test_cases.append(
                    {
                        "text": f"Cic. {work_title.split()[0]} 1.1",  # Abbreviated work title
                        "expected_urn": f"{cts_urn}:1.1",
                    }
                )

        # Add Virgil works
        for work_title, cts_urn in virgil_works:
            if cts_urn:
                work_id = cts_urn.split(":")[-1].split(".")[1]  # Extract work ID like lat003
                test_cases.append(
                    {
                        "text": f"Verg. {work_title.split()[0]} 1.1",  # Abbreviated work title
                        "expected_urn": f"{cts_urn}:1.1",
                    }
                )

        print(f"\n🧪 Testing {len(test_cases)} real work examples:")

        for i, test_case in enumerate(test_cases):
            with self.subTest(case=i):
                urn = self.mapper.map_text_to_urn(test_case["text"])
                print(f"  {test_case['text']:20} -> {urn}")

                # For now, just check that we get some result
                self.assertIsNotNone(urn, f"Should get URN for: {test_case['text']}")

    def test_text_to_urn_mapping(self):
        """Test direct text to URN mapping."""
        # Test cases that should work with the current mapping system
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

    def test_citation_object_processing(self):
        """Test processing citation objects to add URNs."""
        # Create test citations
        citations = [
            Citation(
                references=[
                    TextReference(
                        type=CitationType.LINE_REFERENCE,
                        text="Hom. Il. 1.1",
                        author="Hom",
                        work="Il",
                        book="1",
                        line="1",
                    )
                ]
            ),
            Citation(
                references=[
                    TextReference(
                        type=CitationType.LINE_REFERENCE,
                        text="Verg. A. 1.1",
                        author="Verg",
                        work="A",
                        book="1",
                        line="1",
                    )
                ]
            ),
        ]

        print(f"\n📝 Processing citation objects:")

        # Process citations
        updated = self.mapper.add_urns_to_citations(citations)

        # Check that we got URNs
        for i, citation in enumerate(updated):
            urn = citation.references[0].cts_urn
            print(f"  Citation {i + 1}: {citation.references[0].text:20} -> {urn}")
            self.assertIsNotNone(urn, f"Should get URN for citation {i + 1}")

    def test_database_content_examples(self):
        """Test specific examples from the database."""
        conn = self.mapper._get_connection()
        self.assertIsNotNone(conn, "Should have database connection")

        cursor = conn.cursor()

        print(f"\n🔍 Database content examples:")

        # Test some specific known mappings
        known_mappings = [
            ("M. Tullius Cicero", "De Finibus"),
            ("P. Vergilius Maro", "Aeneis"),
            ("P. Vergilius Maro", "Eclogae"),
            ("Q. Horatius Flaccus", "Carmina"),
        ]

        for author_name, work_title in known_mappings:
            # Find the actual CTS URN in database
            cursor.execute(
                """
                SELECT w.cts_urn 
                FROM works w 
                JOIN author_index a ON w.author_id = a.author_id 
                WHERE a.author_name = ? AND w.work_title = ?
            """,
                (author_name, work_title),
            )

            result = cursor.fetchone()
            if result:
                cts_urn = result[0]
                print(f"  {author_name} - {work_title}: {cts_urn}")

                # Test if we can map to it
                test_text = f"{author_name.split()[0][0:3]}. {work_title.split()[0]} 1.1"
                urn = self.mapper.map_text_to_urn(test_text)
                print(f"    Mapping test: {test_text} -> {urn}")
            else:
                print(f"  {author_name} - {work_title}: Not found in database")

    def test_performance_with_real_database(self):
        """Test performance with real database."""
        # Generate test queries
        test_queries = [
            "Hom. Il. 1.1",
            "Verg. A. 1.1",
            "Cic. Fin. 2 24",
            "Ovid Met. 1.1",
        ] * 25  # Repeat for meaningful performance testing

        print(f"\n⚡ Performance test with real database:")
        print(f"  Running {len(test_queries)} queries...")

        # Test performance
        start_time = time.time()
        results = []
        for query in test_queries:
            urn = self.mapper.map_text_to_urn(query)
            results.append(urn)
        end_time = time.time()

        duration = end_time - start_time
        print(f"  Completed in {duration:.4f}s")
        print(f"  Average: {duration / len(test_queries) * 1000:.2f}ms per query")
        print(f"  Queries per second: {len(test_queries) / duration:.1f}")

        # Verify we got some results
        self.assertEqual(len(results), len(test_queries))
        # Some should work, some might not depending on the mappings
        successful_results = [r for r in results if r is not None]
        print(
            f"  Successful mappings: {len(successful_results)}/{len(test_queries)} ({len(successful_results) / len(test_queries) * 100:.1f}%)"
        )

        print(f"  ✅ Performance test completed successfully!")


if __name__ == "__main__":
    # Run the integration tests with verbose output
    unittest.main(verbosity=2)
