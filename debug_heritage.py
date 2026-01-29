#!/usr/bin/env python3
"""
Debug script to examine raw HTML responses from Heritage Platform
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from langnet.heritage.morphology import HeritageMorphologyService
from langnet.heritage.parsers import MorphologyParser
from langnet.heritage.client import HeritageHTTPClient
from langnet.heritage.parameters import HeritageParameterBuilder


def debug_html_response():
    """Debug the raw HTML response"""
    print("Debugging raw HTML responses...")

    # Test with the word that worked
    test_word = "आत्मा"
    print(f"Testing word: '{test_word}'")

    try:
        # Get the raw HTML content
        client = HeritageHTTPClient()
        client.__enter__()

        params = HeritageParameterBuilder.build_morphology_params(
            text=test_word,
            encoding="velthuis",
            max_solutions=3,
        )

        html_content = client.fetch_cgi_script("sktreader", params=params)
        client.__exit__(None, None, None)

        print(f"Raw HTML content length: {len(html_content)}")
        print("First 1000 characters:")
        print(html_content[:1000])
        print("\n" + "=" * 50)

        # Try to parse it
        parser = MorphologyParser()
        parsed_data = parser.parse(html_content)

        print("Parsed data structure:")
        for key, value in parsed_data.items():
            if isinstance(value, list):
                print(f"  {key}: {len(value)} items")
                if len(value) > 0 and isinstance(value[0], dict):
                    print(f"    Sample: {str(value[0])[:100]}...")
            else:
                print(f"  {key}: {str(value)[:100]}...")

    except Exception as e:
        print(f"Error: {e}")


def debug_encoding():
    """Check text encoding"""
    print("\n" + "=" * 50)
    print("Debugging text encoding...")

    # Test different encodings
    test_words = [
        ("आत्मा", "velthuis"),
        ("aatma", "itrans"),
        ("Aatma", "velthuis"),
    ]

    for word, encoding in test_words:
        encoded = HeritageParameterBuilder.encode_text(word, encoding)
        print(f"'{word}' ({encoding}) -> '{encoded}'")


if __name__ == "__main__":
    debug_html_response()
    debug_encoding()
