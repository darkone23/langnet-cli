#!/usr/bin/env python3
"""
Test Heritage Platform with better encoding handling
"""

import sys
import os
import requests

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def test_encoding_variations():
    """Test different encoding variations"""
    print("Testing different encoding variations...")

    base_url = "http://localhost:48080/cgi-bin/skt/sktreader"

    # Test common Sanskrit words with proper Devanagari
    test_words = [
        "नमः",  # namah
        "सत्यम्",  # satyam
        "धर्मः",  # dharmaḥ
        "योगः",  # yogaḥ
        "आत्मा",  # ātman
        "अहं",  # aham
        "त्वम्",  # tvam
        "सः",  # saḥ
    ]

    successful_words = []

    for word in test_words:
        print(f"\nTesting: '{word}'")

        params = {"text": word, "max": "5"}
        try:
            response = requests.get(base_url, params=params, timeout=10)

            if "Stream error" in response.text:
                print("  ❌ Stream error")
            elif "Wrong input" in response.text:
                print("  ❌ Wrong input error")
            else:
                print("  ✅ Success")
                successful_words.append(word)

                # Extract table data
                from bs4 import BeautifulSoup

                soup = BeautifulSoup(response.text, "html.parser")
                tables = soup.find_all("table", class_="yellow_cent")

                if tables:
                    main_table = tables[0]
                    rows = main_table.find_all("tr")
                    data_rows = [row for row in rows if row.find_all("td")]

                    print(f"  📊 Found {len(data_rows)} data rows")

                    # Show first few rows of data
                    for i, row in enumerate(data_rows[:3]):
                        cells = row.find_all("td")
                        cell_texts = [cell.get_text(strip=True) for cell in cells]
                        if any(cell_texts):
                            print(f"    Row {i + 1}: {cell_texts}")

        except Exception as e:
            print(f"  ❌ Error: {e}")

    print(f"\nSuccessful words: {len(successful_words)}/{len(test_words)}")
    print(f"Working words: {successful_words}")


def try_different_cgi_scripts():
    """Try different CGI scripts"""
    print("\n" + "=" * 50)
    print("Testing different CGI scripts...")

    base_url = "http://localhost:48080/cgi-bin/skt/"
    scripts = ["sktreader", "sktsearch", "sktindex", "sktlemmatizer"]

    test_word = "आत्मा"

    for script in scripts:
        print(f"\nTesting: {script}")

        url = base_url + script
        params = {"text": test_word, "max": "3"}

        try:
            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                print("  ✅ Script accessible")

                if "Stream error" in response.text:
                    print("  ❌ Stream error")
                elif len(response.text) > 100:
                    print(f"  📄 Response length: {len(response.text)}")

                    # Check for meaningful content
                    if any(
                        word in response.text.lower()
                        for word in ["table", "result", "analysis", "word"]
                    ):
                        print("  🎯 Contains potentially useful content")
                    else:
                        print("  📄 Basic HTML response")
                else:
                    print("  📄 Short response")
            else:
                print(f"  ❌ HTTP {response.status_code}")

        except Exception as e:
            print(f"  ❌ Error: {e}")


if __name__ == "__main__":
    test_encoding_variations()
    try_different_cgi_scripts()
