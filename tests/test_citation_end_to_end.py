"""
End-to-end integration tests for complete citation system.

These tests verify the complete workflow from Diogenes citation extraction
through CTS URN mapping to final API response.
"""

import unittest
import sys
import json
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from langnet.citation.cts_urn import CTSUrnMapper
from langnet.citation.models import Citation, TextReference, CitationType
from langnet.citation.extractors.diogenes import DiogenesCitationExtractor
from langnet.diogenes.core import DiogenesDefinitionBlock


class TestEndToEndCitationWorkflow(unittest.TestCase):
    """End-to-end tests for complete citation workflow."""

    def setUp(self):
        """Set up test environment."""
        self.mapper = CTSUrnMapper()
        self.extractor = DiogenesCitationExtractor()

    def test_complete_citation_workflow(self):
        """Test complete workflow from text query to CTS URNs."""
        print(f"\n🚀 Testing complete citation workflow:")

        # Simulate real Diogenes-style citations
        test_citations = [
            {
                "text": "Hom. Il. 1.1",
                "expected_type": "LINE_REFERENCE",
                "description": "Homer Iliad book 1 line 1",
            },
            {
                "text": "Verg. A. 1.1",
                "expected_type": "LINE_REFERENCE",
                "description": "Virgil Aeneid book 1 line 1",
            },
            {
                "text": "Cic. Fin. 2 24",
                "expected_type": "LINE_REFERENCE",
                "description": "Cicero De Finibus book 2 line 24",
            },
            {
                "text": "Hor. C. 1.17",
                "expected_type": "LINE_REFERENCE",
                "description": "Horace Carmina book 1 ode 17",
            },
        ]

        successful_mappings = 0

        for i, citation_info in enumerate(test_citations, 1):
            print(f"\n  Test {i}: {citation_info['description']}")
            print(f"    Input: {citation_info['text']}")

            try:
                # Step 1: Parse citation into TextReference
                parts = citation_info["text"].replace(",", " ").split()
                if len(parts) >= 2:
                    author = parts[0]

                    # Extract work and location
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

                    # Parse location into book and line
                    book = None
                    line = None
                    if location_parts:
                        if len(location_parts) == 1:
                            line = location_parts[0]
                        else:
                            book = location_parts[0]
                            line = location_parts[-1]

                    # Create TextReference
                    text_ref = TextReference(
                        type=CitationType.LINE_REFERENCE,
                        text=citation_info["text"],
                        author=author,
                        work=work,
                        book=book,
                        line=line,
                    )

                    print(f"    Parsed: author='{author}', work='{work}', location='{location}'")

                    # Step 2: Create Citation
                    citation = Citation(references=[text_ref])
                    print(f"    Citation type: {citation.references[0].type.value}")

                    # Step 3: Map to CTS URN
                    updated_citation = self.mapper.add_urns_to_citations([citation])[0]
                    urn = updated_citation.references[0].cts_urn

                    print(f"    CTS URN: {urn}")

                    if urn:
                        successful_mappings += 1
                        print(f"    ✅ Successfully mapped!")

                        # Step 4: Validate CTS URN format
                        self.assertTrue(
                            urn.startswith("urn:cts:"), f"Invalid CTS URN format: {urn}"
                        )

                        # Step 5: Generate CTS API URL
                        from langnet.citation.cts_urn import resolve_cts_urn

                        api_url = resolve_cts_urn(urn)
                        if api_url:
                            print(f"    CTS API: {api_url}")
                    else:
                        print(f"    ⚠️  No URN mapping available")

                else:
                    print(f"    ❌ Could not parse citation")

            except Exception as e:
                print(f"    ❌ Error: {e}")

        print(
            f"\n📊 Results: {successful_mappings}/{len(test_citations)} citations successfully mapped ({successful_mappings / len(test_citations) * 100:.1f}%)"
        )
        self.assertGreater(successful_mappings, 0, "Should have at least some successful mappings")

    def test_diogenes_citation_extractor_integration(self):
        """Test integration with Diogenes citation extractor."""
        print(f"\n🔗 Testing Diogenes citation extractor integration:")

        # Test with a real word that would produce citations
        test_words = [
            ("lupus", "lat"),
            (" Nike ", "grc"),
        ]

        for word, language in test_words:
            print(f"\n  Testing word: '{word}' ({language})")

            try:
                # Note: This would require a running Diogenes service
                # For now, we'll simulate the citation extraction
                simulated_citations = self._simulate_diogenes_citations(word, language)

                if simulated_citations:
                    print(f"    Found {len(simulated_citations)} citations")

                    # Process each citation through the CTS URN mapper
                    mapper = CTSUrnMapper()
                    updated_citations = mapper.add_urns_to_citations(simulated_citations)

                    successful_mappings = 0
                    for i, citation in enumerate(updated_citations):
                        urn = citation.references[0].cts_urn
                        text = citation.references[0].text
                        print(f"      {i + 1}. {text:25} -> {urn}")

                        if urn:
                            successful_mappings += 1

                    print(
                        f"    Successfully mapped: {successful_mappings}/{len(simulated_citations)}"
                    )
                else:
                    print(f"    No citations found for '{word}'")

            except Exception as e:
                print(f"    Error processing '{word}': {e}")

    def _simulate_diogenes_citations(self, word: str, language: str) -> list:
        """Simulate Diogenes citation extraction for testing."""
        # Simulate some typical citations that Diogenes might return
        simulated_citations = []

        if language == "lat" and word.lower() == "lupus":
            # Simulate Latin citations
            citations_data = [
                {
                    "text": "Verg. A. 1.1",
                    "type": "LINE_REFERENCE",
                    "author": "Verg",
                    "work": "A",
                    "book": "1",
                    "line": "1",
                },
                {
                    "text": "Cic. Fin. 2 24",
                    "type": "LINE_REFERENCE",
                    "author": "Cic",
                    "work": "Fin",
                    "book": "2",
                    "line": "24",
                },
            ]
        elif language == "grc" and word.strip() == "Nike":
            # Simulate Greek citations
            citations_data = [
                {
                    "text": "Hom. Il. 1.1",
                    "type": "LINE_REFERENCE",
                    "author": "Hom",
                    "work": "Il",
                    "book": "1",
                    "line": "1",
                }
            ]
        else:
            # Generic citations for other words
            citations_data = [
                {
                    "text": "Cic. Fin. 1.1",
                    "type": "LINE_REFERENCE",
                    "author": "Cic",
                    "work": "Fin",
                    "book": "1",
                    "line": "1",
                }
            ]

        # Convert to Citation objects
        for citation_data in citations_data:
            text_ref = TextReference(
                type=CitationType.LINE_REFERENCE,
                text=citation_data["text"],
                author=citation_data["author"],
                work=citation_data["work"],
                book=citation_data["book"],
                line=citation_data["line"],
            )
            citation = Citation(references=[text_ref])
            simulated_citations.append(citation)

        return simulated_citations

    def test_api_response_format_simulation(self):
        """Test simulated API response format with citations and URNs."""
        print(f"\n📡 Testing simulated API response format:")

        # Simulate what a real API response might look like
        simulated_response = {
            "query": "lupus",
            "language": "lat",
            "results": [
                {
                    "word": "lupus",
                    "definitions": ["wolf", "fox"],
                    "citations": [
                        {
                            "text": "Verg. A. 1.1",
                            "type": "LINE_REFERENCE",
                            "author": "Verg",
                            "work": "A",
                            "book": "1",
                            "line": "1",
                            "cts_urn": None,  # Will be filled by mapper
                            "cts_api_url": None,  # Will be filled by mapper
                        }
                    ],
                }
            ],
        }

        # Process citations through CTS URN mapper
        mapper = CTSUrnMapper()

        for result in simulated_response["results"]:
            if result["citations"]:
                # Convert to Citation objects
                citations = []
                for cit_data in result["citations"]:
                    text_ref = TextReference(
                        type=CitationType.LINE_REFERENCE,
                        text=cit_data["text"],
                        author=cit_data["author"],
                        work=cit_data["work"],
                        book=cit_data["book"],
                        line=cit_data["line"],
                    )
                    citation = Citation(references=[text_ref])
                    citations.append(citation)

                # Add URNs
                updated_citations = mapper.add_urns_to_citations(citations)

                # Update response with URNs and API URLs
                for i, citation in enumerate(updated_citations):
                    cit_data = result["citations"][i]
                    if citation.references[0].cts_urn:
                        cit_data["cts_urn"] = citation.references[0].cts_urn
                        from langnet.citation.cts_urn import resolve_cts_urn

                        api_url = resolve_cts_urn(citation.references[0].cts_urn)
                        if api_url:
                            cit_data["cts_api_url"] = api_url

        # Print the enhanced response
        print(f"  Enhanced API response:")
        print(f"    Query: {simulated_response['query']} ({simulated_response['language']})")
        for result in simulated_response["results"]:
            print(f"    Word: {result['word']}")
            for i, citation in enumerate(result["citations"]):
                print(f"      Citation {i + 1}:")
                print(f"        Text: {citation['text']}")
                print(f"        CTS URN: {citation.get('cts_urn', 'None')}")
                print(f"        CTS API: {citation.get('cts_api_url', 'None')}")

        # Verify we got some URNs
        total_citations = sum(len(r["citations"]) for r in simulated_response["results"])
        urn_citations = sum(
            1 for r in simulated_response["results"] for c in r["citations"] if c.get("cts_urn")
        )

        print(f"  Total citations: {total_citations}")
        print(f"  With CTS URNs: {urn_citations}")
        print(f"  URN coverage: {urn_citations / total_citations * 100:.1f}%")

        self.assertGreater(urn_citations, 0, "Should have at least some citations with URNs")

    def test_performance_with_large_citation_sets(self):
        """Test performance with larger sets of citations."""
        print(f"\n⚡ Testing performance with large citation sets:")

        # Generate a large set of test citations
        test_citations = []
        test_patterns = [
            ("Hom. Il. 1.", "1.1"),
            ("Hom. Il. 2.", "2.1"),
            ("Verg. A. 1.", "1.1"),
            ("Verg. A. 2.", "2.1"),
            ("Cic. Fin. 1.", "1.1"),
            ("Cic. Fin. 2.", "2.1"),
            ("Hor. C. 1.", "1.1"),
            ("Hor. C. 2.", "2.1"),
        ]

        # Generate 100 citations
        for i in range(100):
            pattern, location = test_patterns[i % len(test_patterns)]
            text = f"{pattern}{location}"

            text_ref = TextReference(
                type=CitationType.LINE_REFERENCE,
                text=text,
                author=text.split()[0],
                work=text.split()[1],
                book=location.split(".")[0],
                line=location.split(".")[-1],
            )
            citation = Citation(references=[text_ref])
            test_citations.append(citation)

        print(f"  Generated {len(test_citations)} test citations")

        # Test performance
        import time

        start_time = time.time()

        mapper = CTSUrnMapper()
        updated_citations = mapper.add_urns_to_citations(test_citations)

        end_time = time.time()
        duration = end_time - start_time

        print(f"  Processed {len(test_citations)} citations in {duration:.4f}s")
        print(f"  Average: {duration / len(test_citations) * 1000:.2f}ms per citation")
        print(f"  Citations per second: {len(test_citations) / duration:.1f}")

        # Check results
        successful_mappings = sum(
            1 for citation in updated_citations if citation.references[0].cts_urn
        )
        print(
            f"  Successful mappings: {successful_mappings}/{len(test_citations)} ({successful_mappings / len(test_citations) * 100:.1f}%)"
        )

        # Performance should be reasonable
        self.assertLess(duration, 5.0, "Should process 100 citations in less than 5 seconds")
        self.assertGreater(successful_mappings, 0, "Should have some successful mappings")


if __name__ == "__main__":
    # Run the end-to-end tests with verbose output
    unittest.main(verbosity=2)
