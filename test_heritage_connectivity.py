#!/usr/bin/env python3
"""
Test script for Heritage Platform CGI connectivity
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from langnet.heritage.morphology import HeritageMorphologyService
from langnet.heritage.config import heritage_config


def test_morphology_connectivity():
    """Test connectivity to morphology analysis endpoint"""
    print("Testing morphology analysis connectivity...")

    try:
        with HeritageMorphologyService() as service:
            # Test with a simple Sanskrit word
            test_word = "योगेन"
            print(f"Testing word: '{test_word}'")

            result = service.analyze(test_word, encoding="velthuis", max_solutions=2)

            print(f"✓ Analysis successful")
            print(f"  Input: {result.input_text}")
            print(f"  Total solutions: {result.total_solutions}")
            print(f"  Processing time: {result.processing_time:.3f}s")

            if result.solutions:
                print(f"  First solution type: {result.solutions[0].type}")
                if result.solutions[0].analyses:
                    print(
                        f"  First analysis: {result.solutions[0].analyses[0].word} -> {result.solutions[0].analyses[0].lemma}"
                    )

            return True

    except Exception as e:
        print(f"✗ Morphology test failed: {e}")
        print("  This may be expected if the Heritage Platform server is not running")
        return False


def test_endpoint_availability():
    """Test if endpoints are available"""
    print("\nTesting endpoint availability...")

    try:
        from langnet.heritage.client import HeritageHTTPClient

        client = HeritageHTTPClient()

        # Test if server is responding
        try:
            import requests

            response = requests.get(heritage_config.base_url, timeout=5)
            print(f"✓ Server responded with status: {response.status_code}")
            return True
        except Exception as e:
            print(f"✗ Server not accessible: {e}")
            print(f"  Expected server at: {heritage_config.base_url}")
            return False

    except Exception as e:
        print(f"✗ Endpoint availability test failed: {e}")
        return False


def main():
    """Run connectivity tests"""
    print("Heritage Platform CGI Connectivity Test")
    print("=" * 50)

    tests = [
        test_endpoint_availability,
        test_morphology_connectivity,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1

    print("\n" + "=" * 50)
    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("✓ All connectivity tests passed!")
        return True
    else:
        print("✗ Some connectivity tests failed.")
        print("  Make sure Heritage Platform is running at localhost:48080")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
