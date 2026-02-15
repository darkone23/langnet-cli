#!/usr/bin/env python3
"""
Test script to demonstrate semantic structs schema integration.

This shows how the new semantic structs schema can be used with the
existing LangNet infrastructure.
"""

import sys
import json

# Add paths for imports
sys.path.insert(0, "src")
sys.path.insert(0, "vendor/langnet-spec/generated/python")


def test_semantic_converter():
    """Test the semantic converter module."""
    print("=== Testing Semantic Converter ===")

    try:
        from langnet.semantic_converter import convert_dictionary_entry
        from langnet.schema import DictionaryEntry, DictionaryDefinition, MorphologyInfo

        # Create a mock DictionaryEntry
        entry = DictionaryEntry(
            word="agni",
            language="san",
            definitions=[
                DictionaryDefinition(
                    definition="fire, sacrificial fire",
                    pos="noun",
                    gender="masculine",
                    metadata={"id": "217497", "source": "MW"},
                )
            ],
            morphology=MorphologyInfo(
                lemma="agni",
                pos="noun",
                features={"gender": ["masculine"]},
                gender="masculine",
                case="nominative",
                number="singular",
            ),
            source="cdsl",
        )

        # Convert to semantic structs
        response = convert_dictionary_entry(entry)

        print(f"Successfully converted DictionaryEntry to QueryResponse")
        print(f"Schema version: {response.schema_version}")
        if response.query:
            print(f"Query surface: {response.query.surface}")
        else:
            print("Query: None")
        print(f"Number of lemmas: {len(response.lemmas)}")
        print(f"Number of senses: {len(response.senses)}")
        print(f"Number of analyses: {len(response.analyses)}")

        # Show JSON output
        json_str = response.to_json(indent=2)
        print(f"\nJSON output (first 500 chars):")
        print(json_str[:500] + "..." if len(json_str) > 500 else json_str)

        return True

    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure to run 'just codegen' first")
        return False
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_direct_schema_usage():
    """Test direct usage of the generated schema classes."""
    print("\n\n=== Testing Direct Schema Usage ===")

    try:
        from langnet_spec import SimpleSearchQuery, SimpleSearchResult, Language

        # Create a simple search query
        query = SimpleSearchQuery(
            query="lupus",
            language=Language.LAT,
            max_results=10,
            include_morphology=True,
            include_definitions=True,
        )

        print(f"Created SimpleSearchQuery: {query.query}")
        print(f"Language: {query.language.name}")

        # Convert to JSON
        json_str = query.to_json(indent=2)
        print(f"\nSimpleSearchQuery JSON:\n{json_str}")

        # Create a search result
        result = SimpleSearchResult(
            word="lupus",
            lemma="lupus",
            language="lat",
            part_of_speech="noun",
            definition="wolf",
            morphology="nominative singular masculine",
            relevance_score=0.95,
            sources=["Lewis & Short", "Whitaker's"],
        )

        json_str = result.to_json(indent=2)
        print(f"\nSimpleSearchResult JSON:\n{json_str}")

        return True

    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure to run 'just codegen' first")
        return False
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_api_integration_scenario():
    """Test a scenario showing how the schema integrates with the API."""
    print("\n\n=== Testing API Integration Scenario ===")

    print("Scenario: CLI command with --output semantic")
    print("1. User runs: langnet-cli query san agni --output semantic")
    print("2. CLI calls API to get data")
    print("3. API returns DictionaryEntry objects")
    print("4. CLI uses semantic_converter to convert to QueryResponse")
    print("5. CLI outputs QueryResponse as JSON")
    print("\nThis enables:")
    print("  - Stable, versioned output schema")
    print("  - Semantic constants for concept identity")
    print("  - Witness traceability")
    print("  - Epistemic modes (open/skeptic)")
    print("  - UI hints for presentation")

    return True


def main():
    """Run all tests."""
    print("LangNet Semantic Structs Integration Test")
    print("=" * 50)

    success = True

    # Test 1: Semantic converter
    if not test_semantic_converter():
        success = False

    # Test 2: Direct schema usage
    if not test_direct_schema_usage():
        success = False

    # Test 3: API integration scenario
    test_api_integration_scenario()

    print("\n" + "=" * 50)
    if success:
        print("✓ All tests completed successfully!")
        print("\nNext steps:")
        print("1. Update CLI to add --output semantic option")
        print("2. Add schema validation tests")
        print("3. Create migration guide for consumers")
    else:
        print("✗ Some tests failed")
        print("\nTroubleshooting:")
        print("1. Run 'just codegen' to generate schema classes")
        print("2. Check imports in semantic_converter.py")
        print("3. Verify generated schema files exist")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
