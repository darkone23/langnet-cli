#!/usr/bin/env python3
"""
Test script for Heritage Platform with common Sanskrit words
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from langnet.heritage.morphology import HeritageMorphologyService


def test_common_words():
    """Test with common Sanskrit words"""
    print("Testing with common Sanskrit words...")

    common_words = [
        ("नमः", "velthuis"),  # namah
        ("सत्यम्", "velthuis"),  # satyam
        ("धर्मः", "velthuis"),  # dharmaḥ
        ("योगः", "velthuis"),  # yogaḥ
        ("आत्मा", "velthuis"),  # ātman
    ]

    with HeritageMorphologyService() as service:
        for word, encoding in common_words:
            print(f"\nTesting: '{word}' ({encoding})")
            try:
                result = service.analyze(word, encoding=encoding, max_solutions=3)
                print(f"  Solutions: {result.total_solutions}")
                print(f"  Time: {result.processing_time:.3f}s")

                if result.solutions:
                    for i, solution in enumerate(result.solutions[:2]):
                        print(f"  Solution {i + 1}: {solution.type}")
                        if solution.analyses:
                            for analysis in solution.analyses[:1]:
                                print(f"    {analysis.word} -> {analysis.lemma} ({analysis.pos})")
                else:
                    print("  No solutions found")

            except Exception as e:
                print(f"  Error: {e}")


def test_different_encodings():
    """Test different text encodings"""
    print("\n" + "=" * 50)
    print("Testing different text encodings...")

    word = "yoga"
    encodings = ["velthuis", "itrans", "slp1"]

    with HeritageMorphologyService() as service:
        for encoding in encodings:
            print(f"\nTesting encoding: {encoding}")
            try:
                result = service.analyze(word, encoding=encoding, max_solutions=2)
                print(f"  Solutions: {result.total_solutions}")
                print(f"  Time: {result.processing_time:.3f}s")

            except Exception as e:
                print(f"  Error: {e}")


if __name__ == "__main__":
    test_common_words()
    test_different_encodings()
