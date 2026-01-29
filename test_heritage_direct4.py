#!/usr/bin/env python3
"""
Test Heritage Platform with correct encoding parameters
"""

import sys
import os
import requests

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from langnet.heritage.parameters import HeritageParameterBuilder


def test_correct_parameters():
    """Test with correct CGI parameter format"""
    print("Testing Heritage Platform with correct parameters...")

    # Test parameter building
    print("\n1. Testing parameter building:")

    # Test morphology parameters
    params = HeritageParameterBuilder.build_morphology_params(
        text="आत्मा", encoding="velthuis", max_solutions=3
    )
    print(f"Morphology params: {params}")

    # Test search parameters
    search_params = HeritageParameterBuilder.build_search_params(
        query="yoga", lexicon="MW", encoding="velthuis", max_results=10
    )
    print(f"Search params: {search_params}")

    # Test encoding mapping
    print(f"\n2. Testing encoding mapping:")
    for encoding in ["velthuis", "itrans", "slp1", "devanagari"]:
        cgi_code = HeritageParameterBuilder.get_cgi_encoding_param(encoding)
        print(f"  {encoding} -> {cgi_code}")

    # Test direct CGI calls
    print(f"\n3. Testing direct CGI calls:")

    base_url = "http://localhost:48080/cgi-bin/skt/"

    # Test sktreader with correct parameters
    print("\n  Testing sktreader:")
    params = {"text": "आत्मा", "t": "VH", "max": "3"}
    url = base_url + "sktreader?" + "&".join([f"{k}={v}" for k, v in params.items()])

    try:
        response = requests.get(url, timeout=10)
        print(f"    Status: {response.status_code}")
        print(f"    Length: {len(response.text)}")

        if "Stream error" in response.text:
            print("    ❌ Still stream error")
        elif "Wrong input" in response.text:
            print("    ❌ Still wrong input")
        else:
            print("    ✅ Success!")

            # Check for tables
            if "table" in response.text:
                print("    📊 Contains tables")

    except Exception as e:
        print(f"    ❌ Error: {e}")

    # Test sktindex with example from documentation
    print("\n  Testing sktindex (using example from docs):")
    params = {"lex": "MW", "q": "yoga", "t": "VH"}
    url = base_url + "sktindex?" + "&".join([f"{k}={v}" for k, v in params.items()])

    try:
        response = requests.get(url, timeout=10)
        print(f"    Status: {response.status_code}")
        print(f"    Length: {len(response.text)}")

        if "Stream error" in response.text:
            print("    ❌ Stream error")
        elif len(response.text) > 1000:
            print("    ✅ Large response - likely successful!")

            # Look for dictionary entries
            if "entry" in response.text.lower() or "definition" in response.text.lower():
                print("    📚 Contains dictionary content")

    except Exception as e:
        print(f"    ❌ Error: {e}")


if __name__ == "__main__":
    test_correct_parameters()
