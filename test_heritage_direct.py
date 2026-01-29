#!/usr/bin/env python3
"""
Test Heritage Platform with minimal parameters
"""

import sys
import os
import requests

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from langnet.heritage.client import HeritageHTTPClient
from langnet.heritage.parameters import HeritageParameterBuilder


def test_minimal_params():
    """Test with minimal parameter combinations"""
    print("Testing minimal parameter combinations...")

    base_url = "http://localhost:48080/cgi-bin/skt/sktreader"

    # Different parameter combinations
    param_sets = [
        # Just the text
        {"text": "आत्मा"},
        # Text with max
        {"text": "आत्मा", "max": "3"},
        # Velthuis encoded text without encoding param
        {"text": "Atma"},
        # Velthuis encoded text with encoding param
        {"text": "Atma", "encoding": "velthuis"},
        # ITRANS encoded text
        {"text": "aatma"},
        # Empty params
        {},
    ]

    for i, params in enumerate(param_sets):
        print(f"\nTest {i + 1}: {params}")

        try:
            response = requests.get(base_url, params=params, timeout=10)

            if "Stream error" in response.text:
                print("  ❌ Stream error")
            elif "illegal begin" in response.text:
                print("  ❌ Illegal begin error")
            else:
                print("  ✅ Success")
                # Count tables
                table_count = response.text.count("<table")
                print(f"  📊 {table_count} tables found")

                if table_count > 0:
                    print("  📋 Extracting table data...")
                    # Look for table content
                    if "yellow_cent" in response.text:
                        print("  🎯 Found yellow_cent table (likely results)")

        except Exception as e:
            print(f"  ❌ Error: {e}")


def test_direct_calls():
    """Test direct calls to see what works"""
    print("\n" + "=" * 50)
    print("Testing direct calls...")

    base_url = "http://localhost:48080/cgi-bin/skt/sktreader"

    # Test what we know works
    print("\n1. Testing Devanagari text (known to work):")
    params = {"text": "आत्मा", "max": "3"}
    response = requests.get(base_url, params=params, timeout=10)

    if "Stream error" not in response.text:
        print("  ✅ No stream error")

        # Extract and examine the actual results
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(response.text, "html.parser")

        # Find all tables
        tables = soup.find_all("table")
        print(f"  📊 Found {len(tables)} tables")

        for i, table in enumerate(tables):
            print(f"\n  Table {i + 1}:")
            # Get table rows
            rows = table.find_all("tr")
            print(f"    Rows: {len(rows)}")

            for j, row in enumerate(rows[:3]):  # First 3 rows
                cells = row.find_all(["td", "th"])
                cell_texts = [cell.get_text(strip=True) for cell in cells]
                if any(cell_texts):  # Only show non-empty rows
                    print(f"    Row {j + 1}: {cell_texts}")
    else:
        print("  ❌ Stream error")


if __name__ == "__main__":
    test_minimal_params()
    test_direct_calls()
