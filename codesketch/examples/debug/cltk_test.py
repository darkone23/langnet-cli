#!/usr/bin/env python3
import json
from langnet.classics_toolkit.core import ClassicsToolkit


def test_cltk_lookup():
    cltk = ClassicsToolkit()

    # Test direct lookup
    print("Testing CLTK latin_query for 'sedat':")
    result = cltk.latin_query("sedat")
    print(f"Result: {result}")
    print(f"lewis_1890_lines: {result.lewis_1890_lines}")
    print(f"Type of lewis_1890_lines: {type(result.lewis_1890_lines)}")
    print(f"Length: {len(result.lewis_1890_lines)}")
    print(
        f"First element: {repr(result.lewis_1890_lines[0]) if result.lewis_1890_lines else 'Empty'}"
    )

    print("\nTesting CLTK latin_query for 'lupus':")
    result2 = cltk.latin_query("lupus")
    print(f"Result: {result2}")
    print(f"lewis_1890_lines: {result2.lewis_1890_lines}")
    print(f"Length: {len(result2.lewis_1890_lines)}")

    print("\nTesting CLTK latin_query for 'sedo':")
    result3 = cltk.latin_query("sedo")
    print(f"Result: {result3}")
    print(f"lewis_1890_lines: {result3.lewis_1890_lines}")
    print(f"Length: {len(result3.lewis_1890_lines)}")


if __name__ == "__main__":
    test_cltk_lookup()
