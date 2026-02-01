"""
Test for CDSL citation extractor.
"""

import sys
import os

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from langnet.citation.extractors.cdsl import CDSLCitationExtractor
from langnet.citation.models import CitationCollection


def test_cdsl_extractor():
    """Test the CDSL citation extractor with sample data."""

    # Create extractor
    extractor = CDSLCitationExtractor()

    # Test data similar to what CDSL would return
    test_data = {
        "term": "agni",
        "iast": "agni",
        "references": [
            {"source": "L.", "type": "lexicon"},
            {"source": "MW 127", "type": "lexicon"},
            {"source": "cf. fire", "type": "cross_reference"},
            {"source": "Böhtlingk", "type": "lexicon"},
        ],
    }

    # Test can_extract
    assert extractor.can_extract(test_data), "Should recognize CDSL data"
    print("✓ can_extract test passed")

    # Debug: Check what attributes are available
    print(f"Debug: Data attributes: {dir(test_data) if hasattr(test_data, '__dict__') else 'dict'}")
    print(f"Debug: Data keys: {test_data.keys() if isinstance(test_data, dict) else 'not a dict'}")

    # Test extraction
    collection = extractor.extract(test_data)

    # Verify collection structure
    assert isinstance(collection, CitationCollection), "Should return CitationCollection"
    assert collection.source == "cdsl", "Should have correct source"
    assert collection.query == "agni", f"Should have correct query, got: {collection.query}"
    assert len(collection.citations) == 4, (
        f"Should extract 4 citations, got {len(collection.citations)}"
    )

    print(f"✓ Extracted {len(collection.citations)} citations")

    # Test individual citations
    citations = collection.citations

    # Test first citation (L.)
    first_citation = citations[0]
    assert first_citation.abbreviation == "L."
    assert first_citation.full_name == "Monier-Williams Sanskrit-English Dictionary"
    assert len(first_citation.references) == 1

    first_ref = first_citation.references[0]
    assert first_ref.text == "L."
    assert first_ref.work == "L."
    assert first_ref.page is None
    assert first_ref.type.value == "dictionary_abbreviation"

    print("✓ First lexicon citation parsed correctly")

    # Test second citation (MW 127)
    second_citation = citations[1]
    second_ref = second_citation.references[0]
    assert second_ref.text == "MW 127"
    assert second_ref.work == "MW"
    assert second_ref.page == "127"

    print("✓ Second lexicon citation with page parsed correctly")

    # Test third citation (cf. fire)
    third_citation = citations[2]
    third_ref = third_citation.references[0]
    assert third_ref.text == "cf. fire"
    assert third_ref.work == "fire"
    assert third_ref.type.value == "cross_reference"

    print("✓ Cross-reference citation parsed correctly")

    # Test fourth citation (Böhtlingk)
    fourth_citation = citations[3]
    fourth_ref = fourth_citation.references[0]
    assert fourth_ref.text == "Böhtlingk"
    assert fourth_ref.work == "Böhtlingk"

    print("✓ Fourth lexicon citation parsed correctly")

    print("\n🎉 All CDSL extractor tests passed!")
    return True


if __name__ == "__main__":
    test_cdsl_extractor()
