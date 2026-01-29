#!/usr/bin/env python3
"""
Test Heritage Platform with URL encoding and different approaches
"""

import sys
import os
import requests
from urllib.parse import urlencode

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def test_url_encoding():
    """Test with URL-encoded parameters"""
    print("Testing with URL encoding...")

    base_url = "http://localhost:48080/cgi-bin/skt/sktreader"

    # Test with URL encoding
    test_word = "आत्मा"
    params = {"text": test_word, "max": "3"}

    # Manual URL encoding
    encoded_params = urlencode(params, encoding="utf-8")
    full_url = f"{base_url}?{encoded_params}"

    print(f"URL: {full_url}")
    print(f"Encoded params: {encoded_params}")

    try:
        response = requests.get(full_url, timeout=10)
        print(f"Response status: {response.status_code}")
        print(f"Response length: {len(response.text)}")

        if "Wrong input" in response.text:
            print("❌ Still getting wrong input error")
        else:
            print("✅ No wrong input error")

    except Exception as e:
        print(f"❌ Error: {e}")


def test_simple_ascii():
    """Test with simple ASCII that might work"""
    print("\n" + "=" * 50)
    print("Testing with simple ASCII...")

    base_url = "http://localhost:48080/cgi-bin/skt/sktreader"

    # Try very simple words
    simple_words = [
        "a",
        "i",
        "u",
        "k",
        "g",
        "n",
    ]

    for word in simple_words:
        print(f"\nTesting: '{word}'")
        params = {"text": word, "max": "3"}

        try:
            response = requests.get(base_url, params=params, timeout=5)

            if "Stream error" in response.text:
                print("  ❌ Stream error")
            elif "Wrong input" in response.text:
                print("  ❌ Wrong input")
            elif len(response.text) > 500:
                print("  ✅ Success")
                # Look for meaningful content
                if "table" in response.text:
                    print("  📊 Contains tables")
            else:
                print("  📄 Short response")

        except Exception as e:
            print(f"  ❌ Error: {e}")


def test_cgi_script_directly():
    """Test calling the CGI script directly"""
    print("\n" + "=" * 50)
    print("Testing CGI script directly...")

    # Try to understand what the CGI script expects
    base_url = "http://localhost:48080/cgi-bin/skt/sktreader"

    # Test with no parameters
    print("\n1. No parameters:")
    try:
        response = requests.get(base_url, timeout=5)
        print(f"   Status: {response.status_code}")
        print(f"   Length: {len(response.text)}")
        if "form" in response.text.lower():
            print("   📝 Contains form")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test with help parameter
    print("\n2. Help parameter:")
    try:
        response = requests.get(base_url, params={"help": "1"}, timeout=5)
        print(f"   Status: {response.status_code}")
        print(f"   Length: {len(response.text)}")
    except Exception as e:
        print(f"   ❌ Error: {e}")


def examine_server_config():
    """Examine server configuration"""
    print("\n" + "=" * 50)
    print("Examining server configuration...")

    # Check server headers
    try:
        response = requests.get("http://localhost:48080", timeout=5)
        print("Server headers:")
        for key, value in response.headers.items():
            print(f"  {key}: {value}")
    except Exception as e:
        print(f"❌ Error getting server info: {e}")


if __name__ == "__main__":
    test_url_encoding()
    test_simple_ascii()
    test_cgi_script_directly()
    examine_server_config()
