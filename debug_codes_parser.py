#!/usr/bin/env python3
"""Test script to understand codes parser behavior"""

import sys

sys.path.insert(0, ".")

from src.langnet.whitakers_words.lineparsers import CodesReducer

# Test cases
test_cases = [
    "Caesar, Caesaris  N (3rd) M   [XLXBO]",
    "Caesar, Caesaris  N  (3rd)  M  [XXXAO]",
    "mare  X   [XXXFO]    veryrare",
    "word1, word2, word3  N (3rd) M   [XXXAO]  note1 note2 note3",
]

for case in test_cases:
    print(f"Testing: '{case}'")
    try:
        result = CodesReducer.reduce(case)
        print(f"  Success: {result}")
    except Exception as e:
        print(f"  Error: {type(e).__name__}: {e}")
    print()
