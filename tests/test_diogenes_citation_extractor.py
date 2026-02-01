"""
Test for Diogenes citation extractor.
"""

import sys
import os

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from langnet.citation.extractors.diogenes import DiogenesCitationExtractor
from langnet.citation.models import CitationCollection


def test_diogenes_extractor():
    """Test the Diogenes citation extractor with sample data."""

    # Create extractor
    extractor = DiogenesCitationExtractor()

    # Test data similar to what Diogenes would return
    test_data = {
        "term": "philosophos",
        "citations": {
            "perseus": "Hom. Il. 1.1",
            "tlg": "Arist. Eth. Nic. 1.1",
            "stoa": "Plato. Rep. 7.1",
        },
    }

    # Test can_extract
    assert extractor.can_extract(test_data), "Should recognize Diogenes data"
    print("✓ can_extract test passed")

    # Test extraction
    collection = extractor.extract(test_data)

    # Verify collection structure
    assert isinstance(collection, CitationCollection), "Should return CitationCollection"
    assert collection.source == "diogenes", "Should have correct source"
    assert collection.query == "unknown", "Should have default query for dict data"
    assert len(collection.citations) == 3, (
        f"Should extract 3 citations, got {len(collection.citations)}"
    )

    print(f"✓ Extracted {len(collection.citations)} citations")

    # Test individual citations
    citations = collection.citations

    # Test first citation (Hom. Il. 1.1)
    first_citation = citations[0]
    assert first_citation.abbreviation == "Perseus"
    assert first_citation.full_name == "Perseus Digital Library"
    assert len(first_citation.references) == 1

    first_ref = first_citation.references[0]
    assert first_ref.text == "Hom. Il. 1.1"
    assert first_ref.work == "Il."
    assert first_ref.author == "Hom."
    assert first_ref.book == "1"
    assert first_ref.line == "1"
    assert first_ref.type.value == "line_reference"

    print("✓ First citation parsed correctly")

    # Test second citation (Arist. Eth. Nic. 1.1)
    second_citation = citations[1]
    second_ref = second_citation.references[0]
    assert second_ref.text == "Arist. Eth. Nic. 1.1"
    assert second_ref.author == "Arist."
    assert second_ref.work == "Eth. Nic."

    print("✓ Second citation parsed correctly")

    # Test third citation (Plato. Rep. 7.1)
    third_citation = citations[2]
    third_ref = third_citation.references[0]
    print(
        f"Debug: Third citation - text: '{third_ref.text}', author: '{third_ref.author}', work: '{third_ref.work}'"
    )
    assert third_ref.text == "Plato. Rep. 7.1"
    assert third_ref.author == "Plato."
    assert third_ref.work == "Rep."

    print("✓ Third citation parsed correctly")

    print("\n🎉 All Diogenes extractor tests passed!")
    return True


if __name__ == "__main__":
    test_diogenes_extractor()
