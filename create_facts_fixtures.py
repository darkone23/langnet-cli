#!/usr/bin/env python3
"""Create basic facts parser test fixtures manually"""

import json
from pathlib import Path

FIXTURE_DIR = Path("tests/fixtures/whitakers/term_facts")

# Create simple directory structure
(FIXTURE_DIR / "simple").mkdir(parents=True, exist_ok=True)
(FIXTURE_DIR / "edge_cases").mkdir(parents=True, exist_ok=True)
(FIXTURE_DIR / "golden").mkdir(parents=True, exist_ok=True)

# Simple test cases
simple_cases = {
    "noun_basic": "amor                 N      3 1 NOM S M",
    "verb_basic": "am.or                V      1 1 PRES PASSIVE IND 1 S",
    "adjective_basic": "femin.a              ADJ    1 1 NOM S F POS",
    "with_dot_separation": "femin.a              N      3 2 NOM P N",
}

# Edge cases
edge_cases = {
    "missing_mood": "verb_form            V      1 1 IND 1 S",
    "variant_forms": "word                 N      3 1 DAT P F",
}

# Write simple cases
for name, line in simple_cases.items():
    input_file = FIXTURE_DIR / "simple" / f"{name}.txt"
    input_file.write_text(line)

    # For now, let's create expected output manually based on observed behavior
    expected = {"term": line.split()[0], "pos_code": line.split()[1]}
    expected_file = FIXTURE_DIR / "simple" / f"{name}.json"
    expected_file.write_text(json.dumps(expected, indent=2))

# Write edge cases
for name, line in edge_cases.items():
    input_file = FIXTURE_DIR / "edge_cases" / f"{name}.txt"
    input_file.write_text(line)

    expected = {"term": line.split()[0], "pos_code": line.split()[1]}
    expected_file = FIXTURE_DIR / "edge_cases" / f"{name}.json"
    expected_file.write_text(json.dumps(expected, indent=2))

# Create golden master with a few lines
golden_fixtures = [
    {
        "input": "amor                 N      3 1 NOM S M",
        "expected": {"term": "amor", "pos_code": "N"},
    },
    {
        "input": "am.or                V      1 1 PRES PASSIVE IND 1 S",
        "expected": {"term": "am.or", "pos_code": "V"},
    },
    {
        "input": "femin.a              ADJ    1 1 NOM S F POS",
        "expected": {"term": "femin.a", "pos_code": "ADJ"},
    },
]

with open(FIXTURE_DIR / "golden" / "sampled_from_term_facts.json", "w") as f:
    json.dump(golden_fixtures, f, indent=2)

print("Created basic facts parser test fixtures")
