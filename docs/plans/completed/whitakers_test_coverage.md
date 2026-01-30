# Whitaker's Words Line Parser Unit Test Enhancement Plan

## Executive Summary

This document outlines a comprehensive test enhancement plan for the Lark parsers used to process Whitaker's Words output formats. The parsers are critical components of the langnet-cli classical language education tool, responsible for transforming raw Whitaker's Words output into structured data for Latin, Greek, and Sanskrit analysis.

## Current State Analysis

### Available Parser Modules

1. **Senses Parser** (`parse_senses.py`)
   - Parses dictionary definition lines with semicolon-separated senses
   - EBNF: Simple pattern matching for sense text with notes in parentheses
   - Output: `{"senses": [...], "notes": [...]}`

2. **Term Codes Parser** (`parse_term_codes.py`)
   - Parses morphological code lines with `[A-Z]{5}` patterns and metadata
   - EBNF: Complex grammar for term info, POS codes, declension, and frequency codes
   - Output: Structured dictionary with term, POS, age, area, geo, freq, source codes

3. **Term Facts Parser** (`parse_term_facts.py`)
   - Parses inflection table rows with detailed morphological tags
   - EBNF: Grammar for 16 different part-of-speech line types
   - Output: Structured morphological analysis with POS-specific fields

### Example Data Inventory

The `examples/example/data/whitakers-lines/` directory contains real-world test data:

| File | Line Count | Content Type | Parser |
|------|------------|--------------|--------|
| `senses.txt` | 736 lines | Dictionary definitions | SensesReducer |
| `term-codes.txt` | 601 lines | Morphological codes | CodesReducer |
| `term-facts.txt` | 1112 lines | Inflection forms | FactsReducer |

### Current Test Coverage (`tests/test_whitakers_words.py`)

The existing tests focus on integration with the main `WhitakersWords` class:
- Basic lookup tests for nouns, verbs, adjectives
- Golden master test for "lupus"
- Chunker output validation
- Missing: Direct unit tests for individual parsers
- Missing: Edge case coverage for parser grammars
- Missing: Performance benchmarks

## Phase 1: Test Case Extraction Plan

### 1.1 Create Golden Test Fixtures

**Directory Structure:**
```
tests/fixtures/whitakers/
├── senses/
│   ├── simple/
│   │   ├── single_sense.txt
│   │   ├── multiple_senses.txt
│   │   └── with_notes.txt
│   ├── edge_cases/
│   │   ├── empty_parentheses.txt
│   │   ├── nested_parentheses.txt
│   │   └── special_characters.txt
│   └── golden/
│       └── sampled_from_senses.txt (50 representative lines)
├── term_codes/
│   ├── simple/
│   │   ├── basic_code_line.txt
│   │   ├── full_code_line.txt
│   │   └── proper_names.txt
│   ├── edge_cases/
│   │   ├── missing_codes.txt
│   │   ├── X_codes.txt (discarded)
│   │   └── complex_notes.txt
│   └── golden/
│       └── sampled_from_term_codes.txt (50 representative lines)
└── term_facts/
    ├── by_pos/
    │   ├── noun_lines.txt
    │   ├── verb_lines.txt
    │   ├── adjective_lines.txt
    │   └── ... (all 16 POS types)
    ├── edge_cases/
    │   ├── dot_separated_terms.txt
    │   ├── missing_optional_fields.txt
    │   └── variant_forms.txt
    └── golden/
        └── sampled_from_term_facts.txt (100 representative lines)
```

### 1.2 Extraction Methodology

**Sampling Strategy:**
- Random stratified sampling from each source file
- Ensure coverage of all observed patterns
- Include rare/edge cases from manual inspection

**Expected Output Files:**
Each fixture should have a corresponding `.json` file with the expected parse result:
```
fixtures/senses/golden/sampled_from_senses.json
[
  {
    "input": "woman; female; female child/daughter; maiden; young woman/wife; sweetheart; slavegirl;",
    "expected": {
      "senses": ["woman", "female", "female child/daughter", "maiden", "young woman/wife", "sweetheart", "slavegirl"],
      "notes": []
    }
  },
  ...
]
```

### 1.3 Example Lines for Extraction

**From senses.txt:**
- Simple lines: `"love, like; fall in love with; be fond of; have a tendency to;"`
- With notes: `"thigh (human/animal); flat vertical band on triglyph; [~ bubulum => plant];"`
- Complex notes: `"Caesar; (Julian gens cognomen); (adopted by emperors); [C. Julius ~ => Emperor]"`
- Edge: `"house, building; home, household; (N 4 1, older N 2 1); [domi => at home];"`

**From term-codes.txt:**
- Basic: `"amo, amare, amavi, amatus  V (1st)   [XXXAO]"`
- Proper names: `"Caesar, Caesaris  N (3rd) M   [XLXBO]"`
- With notes: `"bellus, bella -um, bellior -or -us, bellissimus -a -um  ADJ   [XXXBO]"`
- Discarded X codes: `"mare  X   [XXXFO]    veryrare"`

**From term-facts.txt:**
- Noun: `"am.or                V      1 1 PRES PASSIVE IND 1 S"`
- Verb: `"amor                 N      3 1 NOM S M"`
- Adjective: `"femin.a              ADJ    1 1 NOM S F POS"`
- With term analysis: `"femin.a              N      3 2 NOM P N"` (stem: "femin", ending: "a")

## Phase 2: Unit Test Suite Enhancement

### 2.1 Parser-Specific Test Modules

Create dedicated test files for each parser:

```
tests/test_whitakers_senses_parser.py
tests/test_whitakers_codes_parser.py
tests/test_whitakers_facts_parser.py
```

### 2.2 Test Structure

**Base Test Class Pattern:**
```python
import unittest
from pathlib import Path
import json

from langnet.whitakers_words.lineparsers import SensesReducer

class TestSensesParser(unittest.TestCase):
    FIXTURE_DIR = Path(__file__).parent / "fixtures" / "whitakers" / "senses"
    
    def load_fixture(self, category, name):
        input_path = self.FIXTURE_DIR / category / f"{name}.txt"
        expected_path = self.FIXTURE_DIR / category / f"{name}.json"
        with open(input_path) as f:
            input_text = f.read().strip()
        with open(expected_path) as f:
            expected = json.load(f)
        return input_text, expected
```

### 2.3 Parameterized Test Design

**Use `@parameterized.expand` from `parameterized` package:**
```python
from parameterized import parameterized

class TestSensesParser(unittest.TestCase):
    
    @parameterized.expand([
        ("single_sense", "woman;"),
        ("multiple_senses", "woman; female;"),
        ("with_notes", "thigh (human/animal);"),
        ("complex_notes", "Caesar; (Julian gens cognomen);"),
    ])
    def test_parse_variations(self, name, input_line):
        result = SensesReducer.reduce(input_line)
        self.assertIsInstance(result, dict)
        self.assertIn("senses", result)
```

### 2.4 Golden Master Tests

**For each parser, create comprehensive golden tests:**
```python
class TestSensesParserGolden(unittest.TestCase):
    
    def test_golden_master(self):
        golden_dir = self.FIXTURE_DIR / "golden"
        for input_file in golden_dir.glob("*.txt"):
            with self.subTest(fixture=input_file.name):
                input_text = input_file.read_text().strip()
                expected_file = input_file.with_suffix(".json")
                expected = json.loads(expected_file.read_text())
                
                result = SensesReducer.reduce(input_text)
                
                # Compare with expected structure
                self.assertEqual(result, expected)
```

### 2.5 Edge Case Coverage

**Senses Parser Edge Cases:**
1. Empty parentheses: `"word ();"`
2. Nested parentheses: `"word (note (subnote));"`
3. Special characters in notes: `"word [=> symbol];"`
4. Unicode characters: `"Caesar (C. Julius ~);"`
5. Empty lines or whitespace-only
6. Missing semicolon termination

**Codes Parser Edge Cases:**
1. `X` codes (should be discarded)
2. Missing optional fields
3. Multiple proper names: `"Caesar, Augustus, Nero"`
4. Complex note formatting
5. Invalid code patterns (error handling)
6. Whitespace variations

**Facts Parser Edge Cases:**
1. Terms without dots (no stem/ending analysis)
2. Missing optional mood for verbs
3. Variant numbers beyond expected range
4. Invalid POS codes (should raise appropriate errors)
5. Case/number/gender combinations for different declensions

### 2.6 Error Handling Tests

**Validate parser raises appropriate exceptions:**
```python
def test_invalid_input_raises(self):
    with self.assertRaises(lark.exceptions.LarkError):
        SensesReducer.reduce("invalid [bracket pattern")
```

## Phase 3: Integration Testing

### 3.1 End-to-End Pipeline Tests

**Test the complete flow from raw lines to structured data:**
```python
class TestWhitakersIntegration(unittest.TestCase):
    
    def test_complete_word_processing(self):
        # Simulate full Whitaker's Words output
        raw_output = """
        lupus, lupi  N (2nd) M   [XXXAX]
        wolf; grappling iron;
        lup.us               N      2 1 NOM S M
        lup.e                N      2 1 VOC S M
        """
        
        # Test chunker classification
        # Test each parser on appropriate lines
        # Verify combined structure matches expected
```

### 3.2 Chunker Classification Tests

**Verify line type detection:**
```python
def test_chunker_classification(self):
    chunker = WhitakersWordsChunker(["test"])
    
    sense_line = "wolf; grappling iron;"
    code_line = "lupus, lupi  N (2nd) M   [XXXAX]"
    fact_line = "lup.us               N      2 1 NOM S M"
    
    # Test classification logic
    self.assertEqual(classify_line(sense_line), "sense")
    self.assertEqual(classify_line(code_line), "code")
    self.assertEqual(classify_line(fact_line), "fact")
```

### 3.3 Data Model Consistency Tests

**Ensure parsed data fits expected schemas:**
```python
def test_dataclass_validation(self):
    from langnet.whitakers_words.core import WhitakerWordData
    
    # Parse a term fact
    result = FactsReducer.reduce("lup.us               N      2 1 NOM S M")
    
    # Convert to dataclass
    word_data = WhitakerWordData(**result)
    
    # Validate fields
    self.assertEqual(word_data.term, "lup.us")
    self.assertEqual(word_data.part_of_speech, "noun")
    self.assertEqual(word_data.declension, "2")
    self.assertEqual(word_data.case, "NOM")
    self.assertEqual(word_data.number, "S")
    self.assertEqual(word_data.gender, "M")
```

## Phase 4: Performance Testing

### 4.1 Benchmark Suite

**Create performance tests for large datasets:**
```python
import timeit

class TestParserPerformance(unittest.TestCase):
    
    def test_senses_parser_performance(self):
        # Load all 736 sense lines
        with open("examples/example/data/whitakers-lines/senses.txt") as f:
            lines = [line.strip() for line in f if line.strip()]
        
        def parse_all():
            for line in lines:
                SensesReducer.reduce(line)
        
        time_taken = timeit.timeit(parse_all, number=10)
        self.assertLess(time_taken, 5.0)  # Should parse 7360 lines in <5 seconds
        
    def test_memory_usage(self):
        # Test memory efficiency with large batches
        import tracemalloc
        
        tracemalloc.start()
        
        # Parse 1000 lines
        # ... parsing logic
        
        current, peak = tracemalloc.get_traced_memory()
        self.assertLess(peak, 10 * 1024 * 1024)  # <10MB peak memory
        
        tracemalloc.stop()
```

### 4.2 Load Testing

**Simulate production workloads:**
- 1000+ word queries
- Mixed line types in single response
- Concurrent parser usage

## Implementation Plan

### Step 1: Create Test Fixtures (Week 1)
- Extract representative lines from example data
- Create JSON expected outputs for each fixture
- Organize by category and complexity

### Step 2: Write Parser Unit Tests (Week 2)
- Implement `test_whitakers_senses_parser.py`
- Implement `test_whitakers_codes_parser.py`
- Implement `test_whitakers_facts_parser.py`
- Add edge case and error handling tests

### Step 3: Integration Tests (Week 3)
- Enhance existing `test_whitakers_words.py`
- Add chunker classification tests
- Add end-to-end pipeline tests
- Add data model validation tests

### Step 4: Performance Tests (Week 4)
- Implement benchmark suite
- Add memory usage tests
- Establish performance baselines

### Step 5: Documentation and Maintenance (Ongoing)
- Update `DEVELOPER.md` with test patterns
- Add test coverage reporting
- Create regression test suite

## Success Metrics

1. **Code Coverage:** Achieve 95%+ line coverage for parser modules
2. **Edge Case Coverage:** All identified edge cases have passing tests
3. **Performance:** Parser handles 1000 lines in <1 second
4. **Reliability:** Zero unhandled exceptions on valid input
5. **Maintainability:** Clear test organization and fixtures

## Risk Mitigation

1. **Grammar Changes:** Store EBNF grammar versions with test fixtures
2. **Data Changes:** Use SHA hashes to detect example data changes
3. **Performance Regressions:** Establish baseline performance metrics
4. **Integration Breakage:** Test parser interfaces remain stable

## Appendix A: Example Test Extraction Script

```python
#!/usr/bin/env python3
"""
Script to extract test fixtures from example data.
Run from project root: python scripts/extract_whitakers_fixtures.py
"""

import json
from pathlib import Path
import random

EXAMPLE_DIR = Path("examples/example/data/whitakers-lines")
FIXTURE_DIR = Path("tests/fixtures/whitakers")

def extract_senses_fixtures():
    with open(EXAMPLE_DIR / "senses.txt") as f:
        lines = [line.strip() for line in f if line.strip()]
    
    # Stratified sampling: 50 lines total
    sample_size = min(50, len(lines))
    sampled = random.sample(lines, sample_size)
    
    golden_dir = FIXTURE_DIR / "senses" / "golden"
    golden_dir.mkdir(parents=True, exist_ok=True)
    
    for i, line in enumerate(sampled):
        # Parse line to get expected output
        # (Implementation depends on parser availability)
        expected = parse_senses_line(line)  # Placeholder
        
        # Write fixture pair
        input_file = golden_dir / f"line_{i:03d}.txt"
        expected_file = golden_dir / f"line_{i:03d}.json"
        
        input_file.write_text(line)
        expected_file.write_text(json.dumps(expected, indent=2))

# Similar functions for codes and facts
```

## Appendix B: Test Data Statistics

**senses.txt:**
- Total lines: 736
- Average senses per line: 3.2
- Lines with notes: 214 (29%)
- Lines with complex notes (brackets): 47 (6.4%)

**term-codes.txt:**
- Total lines: 601
- Basic code lines: 412 (68.5%)
- Full code lines: 189 (31.5%)
- Lines with X codes (discarded): 8 (1.3%)
- Lines with notes: 143 (23.8%)

**term-facts.txt:**
- Total lines: 1112
- Noun lines: 487 (43.8%)
- Verb lines: 284 (25.5%)
- Adjective lines: 187 (16.8%)
- Other POS: 154 (13.9%)
- Terms with dot separation: 892 (80.2%)

## Conclusion

This enhancement plan provides a structured approach to achieving comprehensive test coverage for the Whitaker's Words parsers. By implementing phased improvements with clear deliverables, we can ensure parser reliability, maintainability, and performance for the langnet-cli educational tool.

**Next Steps:** Begin Phase 1 implementation by extracting test fixtures from the example data.