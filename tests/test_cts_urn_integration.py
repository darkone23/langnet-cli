"""
Integration tests for CTS URN database system.

These tests verify the end-to-end workflow from database population
through citation processing to CTS URN resolution using real services
and actual data.
"""

import unittest
import tempfile
import os
import sys
import time
import duckdb
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from langnet.citation.cts_urn import CTSUrnMapper
from langnet.citation.models import Citation, TextReference, CitationType


class TestCTSUrndatabaseIntegration(unittest.TestCase):
    """Integration tests for CTS URN database functionality."""

    def setUp(self):
        """Set up test environment with real database."""
        # Create temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".duckdb")
        self.temp_db.close()

        # Initialize CTSUrnMapper
        self.mapper = CTSUrnMapper(self.temp_db.name)

        # Populate database with test data
        self._populate_test_database()

    def tearDown(self):
        """Clean up test environment."""
        os.unlink(self.temp_db.name)

    def _populate_test_database(self):
        """Populate test database with realistic classical data."""
        conn = duckdb.connect(self.temp_db.name)

        # Create tables matching the real DuckDB schema
        conn.execute("""
            CREATE TABLE author_index (
                author_id TEXT,
                author_name TEXT,
                language TEXT,
                namespace TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE works (
                author_id TEXT,
                work_title TEXT,
                work_reference TEXT,
                cts_urn TEXT
            )
        """)

        # Insert test authors with real CTS URN namespaces
        authors = [
            ("lat0194", "Livy", "lat", "phi"),
            ("lat0610", "Virgil", "lat", "phi"),
            ("lat0625", "Horace", "lat", "phi"),
            ("lat0630", "Ovid", "lat", "phi"),
            ("lat0843", "Quintilian", "lat", "phi"),
        ]

        conn.executemany(
            """
            INSERT INTO author_index VALUES (?, ?, ?, ?)
        """,
            authors,
        )

        # Insert test works with real CTS URNs
        works = [
            ("lat0194", "Ab Urbe Condita", "ab urbe condita", "urn:cts:latinLit:phi1291.phi001"),
            ("lat0610", "Aeneid", "aen", "urn:cts:latinLit:phi1290.phi004"),
            ("lat0625", "Odes", "c", "urn:cts:latinLit:phi1290.phi007"),
            ("lat0630", "Metamorphoses", "met", "urn:cts:latinLit:phi1290.phi002"),
            ("lat0843", "Institutio Oratoria", "inst", "urn:cts:latinLit:phi1290.phi003"),
        ]

        conn.executemany(
            """
            INSERT INTO works VALUES (?, ?, ?, ?)
        """,
            works,
        )

        conn.close()

    def test_database_population(self):
        """Test that database is properly populated with test data."""
        conn = duckdb.connect(self.temp_db.name)

        # Check authors
        result = conn.execute("SELECT COUNT(*) FROM author_index").fetchone()
        self.assertEqual(result[0], 5)

        result = conn.execute(
            "SELECT author_name FROM author_index WHERE author_id = 'lat0194'"
        ).fetchone()
        self.assertEqual(result[0], "Livy")

        # Check works
        result = conn.execute("SELECT COUNT(*) FROM works").fetchone()
        self.assertEqual(result[0], 5)

        result = conn.execute("SELECT work_title FROM works WHERE author_id = 'lat0610'").fetchone()
        self.assertEqual(result[0], "Aeneid")

        conn.close()

    def test_direct_text_mapping(self):
        """Test direct text to URN mapping."""
        # Test Livy
        urn = self.mapper.map_text_to_urn("Livy ab urbe condita 1.1")
        self.assertEqual(urn, "urn:cts:latinLit:phi1291.phi001:1.1")

        # Test Virgil
        urn = self.mapper.map_text_to_urn("Virgil Aeneid 1.1")
        self.assertEqual(urn, "urn:cts:latinLit:phi1290.phi004:1.1")

        # Test Horace
        urn = self.mapper.map_text_to_urn("Horace Odes 1.1")
        self.assertEqual(urn, "urn:cts:latinLit:phi1290.phi007:1.1")

        # Test Ovid
        urn = self.mapper.map_text_to_urn("Ovid Metamorphoses 1.1")
        self.assertEqual(urn, "urn:cts:latinLit:phi1290.phi002:1.1")

        # Test Quintilian
        urn = self.mapper.map_text_to_urn("Quintilian Institutio Oratoria 1.1")
        self.assertEqual(urn, "urn:cts:latinLit:phi1290.phi003:1.1")

    def test_citation_object_mapping(self):
        """Test mapping of citation objects to URNs."""
        # Create citation objects
        citations = [
            Citation(
                references=[
                    TextReference(
                        type=CitationType.LINE_REFERENCE,
                        text="Livy ab urbe condita 1 1",
                        author="Livy",
                        work="ab urbe condita",
                        book="1",
                        line="1",
                    )
                ]
            ),
            Citation(
                references=[
                    TextReference(
                        type=CitationType.LINE_REFERENCE,
                        text="Virgil Aeneid 1 1",
                        author="Virgil",
                        work="aen",
                        book="1",
                        line="1",
                    )
                ]
            ),
        ]

        # Test mapping
        updated = self.mapper.add_urns_to_citations(citations)
        self.assertEqual(updated[0].references[0].cts_urn, "urn:cts:latinLit:phi1291.phi001:1.1")
        self.assertEqual(updated[1].references[0].cts_urn, "urn:cts:latinLit:phi1290.phi004:1.1")

    def test_batch_citation_processing(self):
        """Test processing multiple citations in batch."""
        citations = []
        test_data = [
            ("Livy", "ab urbe condita", "1", "1"),
            ("Virgil", "aen", "1", "1"),
            ("Horace", "c", "1", "1"),
            ("Ovid", "met", "1", "1"),
        ]

        for author, work, book, line in test_data:
            text_ref = TextReference(
                type=CitationType.LINE_REFERENCE,
                text=f"{author} {work} {book} {line}",
                author=author,
                work=work,
                book=book,
                line=line,
            )
            citations.append(Citation(references=[text_ref]))

        # Process all citations
        updated = self.mapper.add_urns_to_citations(citations)
        expected_urns = [
            "urn:cts:latinLit:phi1291.phi001:1.1",
            "urn:cts:latinLit:phi1290.phi004:1.1",
            "urn:cts:latinLit:phi1290.phi007:1.1",
            "urn:cts:latinLit:phi1290.phi002:1.1",
        ]

        for i, citation in enumerate(updated):
            self.assertEqual(citation.references[0].cts_urn, expected_urns[i])

    def test_database_fallback_behavior(self):
        """Test that fallback hardcoded mappings work when database fails."""
        # Create mapper with non-existent database
        fallback_mapper = CTSUrnMapper("/non/existent.db")

        # This should use fallback mappings
        urn = fallback_mapper.map_text_to_urn("Hom. Il. 1.1")
        self.assertEqual(urn, "urn:cts:greekLit:tlg0012.tlg001:1.1")

        # Test with non-existent work
        urn = fallback_mapper.map_text_to_urn("NonExistent Author 1.1")
        self.assertIsNone(urn)

    def test_error_handling(self):
        """Test error handling for edge cases."""
        # Empty citation
        empty_citation = Citation(references=[])
        result = self.mapper.add_urns_to_citations([empty_citation])
        self.assertEqual(len(result[0].references), 0)

        # Invalid citation text
        invalid_citation = Citation(
            references=[
                TextReference(
                    type=CitationType.LINE_REFERENCE, text="invalid text", author=None, work=None
                )
            ]
        )
        result = self.mapper.add_urns_to_citations([invalid_citation])
        self.assertIsNone(result[0].references[0].cts_urn)

    def test_complex_citation_parsing(self):
        """Test parsing of complex citation formats."""
        # Test multi-word work titles
        urn = self.mapper.map_text_to_urn("Livy ab urbe condita 10.5")
        self.assertEqual(urn, "urn:cts:latinLit:phi1291.phi001:10.5")

        # Test book and line format
        urn = self.mapper.map_text_to_urn("Virgil Aeneid 2 24")
        self.assertEqual(urn, "urn:cts:latinLit:phi1290.phi004:2.24")

        # Test various spacing and punctuation
        urn = self.mapper.map_text_to_urn("Horace, Odes 1.17")
        self.assertEqual(urn, "urn:cts:latinLit:phi1290.phi007:1.17")


class TestRealDatabaseIntegration(unittest.TestCase):
    """Integration tests with the real existing database."""

    def setUp(self):
        """Set up with real database."""
        self.mapper = CTSUrnMapper("/tmp/classical_refs_new.db")

    def test_real_database_functionality(self):
        """Test with the real populated database."""
        # Test all major authors from real database
        test_cases = [
            ("Livy", "ab urbe condita", "1.1", "urn:cts:latinLit:phi1291.phi001:1.1"),
            ("Virgil", "aen", "1.1", "urn:cts:latinLit:phi1290.phi004:1.1"),
            ("Horace", "c", "1.1", "urn:cts:latinLit:phi1290.phi007:1.1"),
            ("Ovid", "met", "1.1", "urn:cts:latinLit:phi1290.phi002:1.1"),
            ("Quintilian", "inst", "1.1", "urn:cts:latinLit:phi1290.phi003:1.1"),
            ("Martial", "epigr", "1.1", "urn:cts:latinLit:phi1290.phi001:1.1"),
            ("Statius", "ach", "1.1", "urn:cts:latinLit:phi1290.phi002:1.1"),
            ("Suetonius", "vit", "1.1", "urn:cts:latinLit:phi1290.phi004:1.1"),
        ]

        for author, work, location, expected_urn in test_cases:
            # Create citation object
            text_ref = TextReference(
                type=CitationType.LINE_REFERENCE,
                text=f"{author} {work} {location}",
                author=author,
                work=work,
                book=location.split(".")[0] if "." in location else None,
                line=location.split(".")[-1] if "." in location else None,
            )
            citation = Citation(references=[text_ref])

            # Map to URN
            updated = self.mapper.add_urns_to_citations([citation])[0]
            urn = updated.references[0].cts_urn

            self.assertEqual(urn, expected_urn, f"Failed for {author} {work} {location}")

    def test_end_to_end_workflow_simulation(self):
        """Simulate the complete workflow from text query to CTS URN resolution."""
        print(f"\n🚀 Simulating end-to-end workflow with real database:")

        # Test cases representing real user queries
        test_queries = [
            {
                "query": "Livy ab urbe condita 1.1",
                "expected_author": "Livy",
                "expected_work": "ab urbe condita",
                "expected_urn": "urn:cts:latinLit:phi1291.phi001:1.1",
            },
            {
                "query": "Virgil Aeneid 1.1",
                "expected_author": "Virgil",
                "expected_work": "Aeneid",
                "expected_urn": "urn:cts:latinLit:phi1290.phi004:1.1",
            },
            {
                "query": "Horace Odes 1.1",
                "expected_author": "Horace",
                "expected_work": "Odes",
                "expected_urn": "urn:cts:latinLit:phi1290.phi007:1.1",
            },
            {
                "query": "Ovid Metamorphoses 1.1",
                "expected_author": "Ovid",
                "expected_work": "Metamorphoses",
                "expected_urn": "urn:cts:latinLit:phi1290.phi002:1.1",
            },
        ]

        for i, test_case in enumerate(test_queries, 1):
            print(f"\n  Test {i}: {test_case['query']}")

            # Step 1: Parse query into citation
            parts = test_case["query"].replace(",", " ").split()
            author = parts[0]
            work_parts = []
            location_parts = []

            for j, part in enumerate(parts[1:], 1):
                if part.isdigit() or (part.replace(".", "", 1).isdigit() and "." in part):
                    location_parts = parts[j:]
                    work_parts = parts[1:j]
                    break
            else:
                work_parts = parts[1:]
                location_parts = []

            work = " ".join(work_parts)
            location = ".".join(location_parts) if location_parts else ""

            # Create citation object
            # Parse location into book and line properly
            book = None
            line = None
            if location_parts:
                if len(location_parts) == 1:
                    # Single number - treat as line number
                    line = location_parts[0]
                else:
                    # Multiple numbers - treat as book.line
                    book = location_parts[0]
                    line = location_parts[-1]

            text_ref = TextReference(
                type=CitationType.LINE_REFERENCE,
                text=test_case["query"],
                author=author,
                work=work,
                book=book,
                line=line,
            )
            citation = Citation(references=[text_ref])

            print(f"    Parsed: author='{author}', work='{work}', location='{location}'")

            # Step 2: Resolve CTS URN
            updated_citation = self.mapper.add_urns_to_citations([citation])[0]
            urn = updated_citation.references[0].cts_urn

            print(f"    CTS URN: {urn}")

            # Step 3: Verify results
            self.assertEqual(author, test_case["expected_author"])
            self.assertEqual(work, test_case["expected_work"])
            self.assertEqual(urn, test_case["expected_urn"])

            print(f"    ✅ Test {i} passed!")

        print(f"\n🎉 All {len(test_queries)} workflow tests completed successfully!")


class TestPerformance(unittest.TestCase):
    """Performance tests."""

    def test_real_database_performance(self):
        """Test performance with real database."""
        mapper = CTSUrnMapper("/tmp/classical_refs_new.db")

        # Generate test queries
        test_queries = [
            "Livy ab urbe condita 1.1",
            "Virgil Aeneid 1.1",
            "Horace Odes 1.1",
            "Ovid Metamorphoses 1.1",
            "Quintilian Institutio Oratoria 1.1",
        ] * 50  # Repeat for meaningful performance testing

        print(f"\n⚡ Performance test with real database:")
        print(f"  Running {len(test_queries)} queries...")

        # Test performance
        start_time = time.time()
        results = []
        for query in test_queries:
            urn = mapper.map_text_to_urn(query)
            results.append(urn)
        end_time = time.time()

        duration = end_time - start_time
        print(f"  Completed in {duration:.4f}s")
        print(f"  Average: {duration / len(test_queries) * 1000:.2f}ms per query")
        print(f"  Queries per second: {len(test_queries) / duration:.1f}")

        # Verify we got results
        self.assertEqual(len(results), len(test_queries))
        self.assertTrue(all(results))  # All should return URNs

        print(f"  ✅ Performance test completed successfully!")


if __name__ == "__main__":
    # Run the integration tests with verbose output
    unittest.main(verbosity=2)
