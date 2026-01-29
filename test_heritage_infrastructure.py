#!/usr/bin/env python3
"""
Test script for Heritage Platform backend infrastructure
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def test_imports():
    """Test basic imports"""
    print("Testing imports...")

    try:
        from langnet.heritage.config import heritage_config

        print("✓ Config import successful")
        print(f"  Base URL: {heritage_config.base_url}")
        print(f"  CGI Path: {heritage_config.cgi_path}")
    except Exception as e:
        print(f"✗ Config import failed: {e}")
        return False

    try:
        from langnet.heritage.parameters import HeritageParameterBuilder

        print("✓ Parameter builder import successful")
    except Exception as e:
        print(f"✗ Parameter builder import failed: {e}")
        return False

    try:
        from langnet.heritage.models import (
            HeritageMorphologyResult,
            HeritageDictionaryEntry,
            HeritageSearchResult,
        )

        print("✓ Models import successful")
    except Exception as e:
        print(f"✗ Models import failed: {e}")
        return False

    try:
        from langnet.heritage.client import HeritageHTTPClient

        print("✓ HTTP client import successful")
    except Exception as e:
        print(f"✗ HTTP client import failed: {e}")
        return False

    return True


def test_parameter_builder():
    """Test parameter builder functionality"""
    print("\nTesting parameter builder...")

    try:
        from langnet.heritage.parameters import HeritageParameterBuilder

        # Test text encoding
        test_word = "योगेन"
        velthuis = HeritageParameterBuilder.encode_text(test_word, "velthuis")
        print(f"✓ Text encoding: '{test_word}' -> '{velthuis}'")

        # Test parameter building
        params = HeritageParameterBuilder.build_morphology_params(
            test_word, encoding="velthuis", max_solutions=5
        )
        print(f"✓ Morphology params: {params}")

        # Test search params
        search_params = HeritageParameterBuilder.build_search_params(
            "yoga", lexicon="MW", max_results=10
        )
        print(f"✓ Search params: {search_params}")

        return True

    except Exception as e:
        print(f"✗ Parameter builder test failed: {e}")
        return False


def test_models():
    """Test data models"""
    print("\nTesting data models...")

    try:
        from langnet.heritage.models import (
            HeritageWordAnalysis,
            HeritageSolution,
            HeritageDictionaryEntry,
            HeritageSearchResult,
        )

        # Test word analysis
        analysis = HeritageWordAnalysis(
            word="योगेन",
            lemma="योग",
            root="युज्",
            pos="noun",
            case="3",
            gender="m",
            number="s",
            meaning=["yoga", "union"],
        )
        print(f"✓ Word analysis: {analysis.word} -> {analysis.lemma}")

        # Test solution
        solution = HeritageSolution(
            type="morphological", analyses=[analysis], total_words=1, score=0.95
        )
        print(f"✓ Solution: {solution.type} with {len(solution.analyses)} analyses")

        # Test dictionary entry
        entry = HeritageDictionaryEntry(
            headword="योगः",
            lemma="योग",
            definitions=["yoga", "union", "connection"],
            pos="noun",
            gender="m",
            number="s",
            case="1",
        )
        print(f"✓ Dictionary entry: {entry.headword}")

        # Test search result
        search_result = HeritageSearchResult(
            query="yoga", lexicon="MW", entries=[entry], total_results=1
        )
        print(f"✓ Search result: {search_result.query} -> {search_result.total_results} entries")

        return True

    except Exception as e:
        print(f"✗ Models test failed: {e}")
        return False


def test_http_client():
    """Test HTTP client basic functionality"""
    print("\nTesting HTTP client...")

    try:
        from langnet.heritage.client import HeritageHTTPClient

        # Test URL building
        client = HeritageHTTPClient()
        url = client.build_cgi_url("sktreader", {"text": "test"})
        print(f"✓ URL building: {url}")

        # Test that client can be initialized
        with HeritageHTTPClient() as http_client:
            print("✓ HTTP client context manager works")

        return True

    except Exception as e:
        print(f"✗ HTTP client test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("Heritage Platform Backend Infrastructure Test")
    print("=" * 50)

    tests = [
        test_imports,
        test_parameter_builder,
        test_models,
        test_http_client,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1

    print("\n" + "=" * 50)
    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("✓ All tests passed! Infrastructure is ready.")
        return True
    else:
        print("✗ Some tests failed. Check the output above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
