#!/usr/bin/env python3
"""
Examine full HTML structure from Heritage Platform
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from langnet.heritage.client import HeritageHTTPClient
from langnet.heritage.parameters import HeritageParameterBuilder


def examine_full_html():
    """Examine the complete HTML response"""
    print("Examining complete HTML response...")

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

        print(f"Full HTML content ({len(html_content)} characters):")
        print("=" * 60)
        print(html_content)
        print("=" * 60)

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    examine_full_html()
