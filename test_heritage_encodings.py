#!/usr/bin/env python3
"""
Test different encoding formats for Heritage Platform
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from langnet.heritage.client import HeritageHTTPClient
from langnet.heritage.parameters import HeritageParameterBuilder


def test_encodings():
    """Test different encoding approaches"""
    print("Testing different encoding approaches...")

    test_words = [
        # Original Devanagari
        ("आत्मा", "devanagari"),
        # Velthius encoding
        ("Atma", "velthuis"),
        # ITRANS encoding
        ("aatma", "itrans"),
        # SLP1 encoding
        ("Azm", "slp1"),
        # Try without encoding parameter
        ("Atma", None),
    ]

    for word, encoding in test_words:
        print(f"\nTesting: '{word}' (encoding: {encoding})")

        try:
            # Get the raw HTML content
            client = HeritageHTTPClient()
            client.__enter__()

            if encoding:
                params = HeritageParameterBuilder.build_morphology_params(
                    text=word,
                    encoding=encoding,
                    max_solutions=3,
                )
            else:
                # Try without encoding parameter
                params = {
                    "text": word,
                    "max": "3",
                }

            html_content = client.fetch_cgi_script("sktreader", params=params)
            client.__exit__(None, None, None)

            # Check for error messages
            if "Stream error" in html_content:
                print("  ❌ Stream error detected")
            elif "illegal begin" in html_content:
                print("  ❌ Illegal begin error detected")
            else:
                print("  ✅ No obvious errors")

                # Count solutions if no errors
                if "table" in html_content:
                    print(f"  📊 Contains tables")
                else:
                    print(f"  📊 No tables found")

        except Exception as e:
            print(f"  ❌ Error: {e}")


def try_direct_cgi_call():
    """Try calling CGI directly with curl-like approach"""
    print("\n" + "=" * 50)
    print("Trying direct CGI call...")

    import requests

    # Try the actual URL that should be called
    base_url = "http://localhost:48080/cgi-bin/skt/sktreader"

    # Parameters from the working example
    params = {"text": "Atma", "max": "3"}

    try:
        response = requests.get(base_url, params=params, timeout=10)
        print(f"Response status: {response.status_code}")
        print(f"Response length: {len(response.text)}")

        if "Stream error" in response.text:
            print("❌ Still getting stream error")
        else:
            print("✅ No stream error!")
            print("First 500 chars:")
            print(response.text[:500])

    except Exception as e:
        print(f"❌ Request failed: {e}")


if __name__ == "__main__":
    test_encodings()
    try_direct_cgi_call()
