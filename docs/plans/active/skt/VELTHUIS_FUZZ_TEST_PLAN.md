# Velthuis Fuzz Testing and Integration Improvement Plan

## Overview

This plan addresses the critical Velthuis long vowel encoding issue through systematic fuzz testing and integration of the abbreviations documentation. The goal is to flatten existing documentation and create a unified approach for handling Velthuis input variations.

## Current Issues Summary

### Critical Issue: Velthuis Long Vowel Sensitivity
- `agni` (short i) → 1 solution with `grey_back` (`{?}` unknown)
- `agnii` (long ii) → 2 solutions with proper analysis (`m. du. acc. | m. du. nom.`)
- Heritage Platform requires explicit long vowel marking in Velthuis

### Related Issues:
1. **Encoding detection**: Doesn't recognize Velthuis long vowel patterns
2. **Normalization**: No automatic ASCII → Velthuis conversion
3. **Fallback**: No retry mechanism for short/long vowel variations
4. **Abbreviations**: French grammatical abbreviations not integrated

## Immediate Actions (First 24 Hours)

### 1. Fix Critical Parser Bug
**Location**: `src/langnet/heritage/parsers.py:181-182`

**Problem**: The parser has type errors accessing `.get()` on `Tree[Token]` objects.

**Fix**:
```python
# BEFORE (lines 181-182):
analyses = first.get("analyses", [])  # ERROR: Tree[Token] has no .get()
total_words = first.get("total_words", 1)  # ERROR

# AFTER:
if hasattr(first, 'data') and isinstance(first.data, dict):
    analyses = first.data.get("analyses", [])
    total_words = first.data.get("total_words", 1)
elif isinstance(first, dict):
    analyses = first.get("analyses", [])
    total_words = first.get("total_words", 1)
else:
    # Handle Lark parse tree structure
    analyses = self._extract_analyses_from_tree(first)
    total_words = len(analyses) if analyses else 1
```

### 2. Quick Validation Test
**Goal**: Confirm the Velthuis long vowel hypothesis before full implementation.

**Script**: `examples/debug/validate_velthuis_issue.py`
```python
import requests

def test_pair(short, long):
    base = "http://localhost:48080/cgi-bin/skt/sktreader"
    params = {"t": "VH", "lex": "SH", "font": "roma", "cache": "t"}
    
    short_r = requests.get(base, params={**params, "text": short})
    long_r = requests.get(base, params={**params, "text": long})
    
    short_unknown = "{?}" in short_r.text or "grey_back" in short_r.text
    long_unknown = "{?}" in long_r.text or "grey_back" in long_r.text
    
    return {
        "short": {"input": short, "unknown": short_unknown, "text": short_r.text[:200]},
        "long": {"input": long, "unknown": long_unknown, "text": long_r.text[:200]},
        "problem": short_unknown and not long_unknown
    }

# Test known problematic pairs
pairs = [("agni", "agnii"), ("sita", "siitaa"), ("deva", "devaa")]
results = [test_pair(*pair) for pair in pairs]
problematic = [r for r in results if r["problem"]]
print(f"Problematic pairs: {len(problematic)}/{len(pairs)}")
for r in problematic:
    print(f"  {r['short']['input']} → {r['long']['input']}: SHORT fails, LONG works")
```

### 3. Minimal Fallback Implementation
**Goal**: Provide immediate user benefit while full solution is being built.

**File**: `src/langnet/heritage/client.py`
```python
def fetch_morphology_with_simple_fallback(self, word: str, **kwargs):
    """Try common Velthuis variations when initial query fails."""
    # Try original query
    result = self.fetch_morphology(word, **kwargs)
    
    # Check if result is unknown/error
    if self._is_unknown_result(result):
        # Generate simple variations
        variations = []
        
        # Long vowel endings (most common issue)
        if word.endswith('i') and len(word) > 1:
            variations.append(word + 'i')  # agni → agnii
        if word.endswith('a') and len(word) > 1:
            variations.append(word + 'a')  # sita → siitaa
        if word.endswith('u') and len(word) > 1:
            variations.append(word + 'u')  # guru → guruu
            
        # Try each variation
        for variant in variations:
            try:
                fallback = self.fetch_morphology(variant, **kwargs)
                if not self._is_unknown_result(fallback):
                    fallback['fallback_used'] = True
                    fallback['original_input'] = word
                    fallback['suggested_input'] = variant
                    return fallback
            except Exception:
                continue
    
    return result

def _is_unknown_result(self, result):
    """Check if result indicates unknown analysis."""
    html = result.get("raw_html", "")
    return "{?}" in html or "grey_back" in html or "unknown" in html.lower()
```

### 4. Quick CLI Test
**Goal**: Verify current user experience.
```bash
# Test current behavior
devenv shell langnet-cli -- query skt agni --output json
devenv shell langnet-cli -- query skt agnii --output json

# Check for errors
tail -f /tmp/langnet.log 2>/dev/null | grep -E "(ERROR|WARNING|unknown)"
```

## Phase 1: Fuzz Testing Framework

### 1.1 Create Fuzz Test Corpus
**Location**: `examples/debug/velthuis_fuzz_corpus.txt`

```python
# Common Sanskrit words with vowel variations
test_cases = [
    # Basic long vowel pairs
    ("agni", "agnii"),
    ("sita", "siitaa"),
    ("deva", "devaa"),
    ("rama", "raama"),
    ("krishna", "kRSNa"),
    
    # Compound vowel patterns
    ("guru", "guruu"),
    ("shanti", "zanti", "zaanti"),
    ("yoga", "yogaa"),
    
    # Edge cases with diacritics
    ("a", "aa"),
    ("i", "ii"),
    ("u", "uu"),
    ("r", "RR"),
    ("l", "LL"),
    
    # Retroflex consonants
    ("t", "T"),  # dental vs retroflex
    ("d", "D"),
    ("n", "N"),
    ("s", "S"),
    ("sh", "z"),
    
    # Avagraha (apostrophe)
    ("agni", ".agni"),
    ("deva", ".deva"),
]
```

### 1.2 Fuzz Test Script
**Location**: `examples/debug/fuzz_velthuis.py`

```python
import requests
from concurrent.futures import ThreadPoolExecutor
import json
import re

BASE_URL = "http://localhost:48080/cgi-bin/skt/sktreader"

def test_velthuis_variant(word: str) -> dict:
    """Test a single Velthuis variant and return analysis."""
    params = {
        "t": "VH",
        "lex": "SH",
        "font": "roma",
        "cache": "t",
        "st": "t",
        "us": "f",
        "text": word,
        "topic": "",
        "abs": "f",
        "corpmode": "",
        "corpdir": "",
        "sentno": "",
        "mode": "p",
        "cpts": ""
    }
    
    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        html = response.text
        
        # Extract key metrics
        has_unknown = "{?}" in html
        has_solutions = "solution kept among" in html
        color_class = None
        
        # Extract color class
        color_match = re.search(r'class="([a-z_]+)_back"', html)
        if color_match:
            color_class = color_match.group(1)
        
        # Count solutions
        solution_match = re.search(r'(\d+)\s+solution[s]?\s+kept\s+among\s+(\d+)', html)
        solutions_kept = int(solution_match.group(1)) if solution_match else 0
        total_solutions = int(solution_match.group(2)) if solution_match else 0
        
        return {
            "word": word,
            "success": response.status_code == 200,
            "has_unknown": has_unknown,
            "has_solutions": has_solutions,
            "solutions_kept": solutions_kept,
            "total_solutions": total_solutions,
            "color_class": color_class,
            "status": "success"
        }
    except Exception as e:
        return {
            "word": word,
            "success": False,
            "error": str(e),
            "status": "error"
        }

def run_fuzz_test(corpus_file: str):
    """Run fuzz test on corpus and generate report."""
    with open(corpus_file, 'r') as f:
        test_cases = [line.strip() for line in f if line.strip()]
    
    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(test_velthuis_variant, word) for word in test_cases]
        for future in futures:
            results.append(future.result())
    
    # Generate analysis report
    generate_report(results)

def generate_report(results: list):
    """Generate comprehensive fuzz test report."""
    successful = [r for r in results if r["success"]]
    unknown_results = [r for r in successful if r["has_unknown"]]
    has_solutions = [r for r in successful if r["has_solutions"]]
    
    print(f"\n=== Velthuis Fuzz Test Report ===")
    print(f"Total tests: {len(results)}")
    print(f"Successful queries: {len(successful)}")
    print(f"Queries with unknown ({'{?}'}): {len(unknown_results)}")
    print(f"Queries with solutions: {len(has_solutions)}")
    
    # Color class analysis
    color_counts = {}
    for result in successful:
        color = result.get("color_class", "none")
        color_counts[color] = color_counts.get(color, 0) + 1
    
    print(f"\nColor Class Distribution:")
    for color, count in sorted(color_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {color}: {count}")
    
    # Identify problematic patterns
    print(f"\n=== Problematic Patterns ===")
    unknown_words = [r["word"] for r in unknown_results]
    print(f"Words with unknown analysis: {unknown_words[:20]}...")
    
    # Save detailed results
    with open("fuzz_results.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    run_fuzz_test("velthuis_fuzz_corpus.txt")
```

### 1.3 Analysis Metrics
1. **Success Rate**: Percentage of queries returning HTTP 200
2. **Unknown Rate**: Percentage with `{?}` (grey_back)
3. **Solution Rate**: Percentage with >0 solutions
4. **Color Distribution**: Breakdown of grammatical categories
5. **Pattern Analysis**: Identify problematic input patterns

## Phase 2: Abbreviations Integration

### 2.1 Create Abbreviations Module
**Location**: `src/langnet/heritage/abbreviations.py`

```python
"""
French-to-English grammatical abbreviations for Heritage Platform.
Based on HERITAGE_ABBR.md documentation.
"""

GRAMMATICAL_ABBREVIATIONS = {
    # Case and number
    "abl.": "ablative",
    "abs.": "absolutive", 
    "acc.": "accusative",
    "dat.": "dative",
    "du.": "dual",
    "g.": "genitive",
    "i.": "instrumental",
    "loc.": "locative",
    "nom.": "nominative",
    "pl.": "plural",
    "sg.": "singular",
    "voc.": "vocative",
    
    # Gender
    "f.": "feminine",
    "m.": "masculine",
    "n.": "neuter",
    
    # Verb forms and moods
    "aor.": "aorist",
    "bén.": "benedictive",
    "cond.": "conditional",
    "dés.": "desiderative",
    "fut.": "future",
    "imp.": "imperative",
    "impers.": "impersonal",
    "impft.": "imperfect",
    "ind.": "indeclinable",
    "inf.": "infinitive",
    "inj.": "injunctive",
    "opt.": "optative",
    "pft.": "perfect",
    "pr.": "present",
    "subj.": "subjunctive",
    
    # Participles
    "pp.": "past passive participle",
    "ppa.": "past active participle",
    "ppft.": "perfect participle",
    "ppr.": "present participle",
    "pfut.": "future participle",
    "pfp.": "future passive participle",
    
    # Voice
    "ac.": "active",
    "mo.": "middle",
    "ps.": "passive",
    
    # Word classes
    "a.": "adjective",
    "adv.": "adverb",
    "comp.": "compound",
    "conj.": "conjunction",
    "interj.": "interjection",
    "num.": "numeral",
    "part.": "particle",
    "prép.": "preposition",
    "pron.": "pronoun",
    "S.": "substantive/noun",
    "V.": "verb",
    
    # Other grammatical terms
    "compar.": "comparative",
    "dém.": "demonstrative",
    "épith.": "epithet",
    "fb.": "weak",
    "gém.": "geminated",
    "hom.": "homonym",
    "intens.": "intensive",
    "interr.": "interrogative",
    "nég.": "negation",
    "obl.": "oblique",
    "ord.": "ordinal",
    "péj.": "pejorative",
    "poss.": "possessive",
    "priv.": "privative",
    "red.": "reduplication",
    "super.": "superlative",
    "suppl.": "suppletive",
    "syn.": "synonym",
    "var.": "variant",
    "vr.": "vṛddhi",
}

COMPOUND_INDICATORS = {
    "ic.": "in composition",
    "ifc.": "at the end of a compound",
    "iic.": "at the beginning of a compound",
    "iiv.": "at the beginning of a verb",
}

DOMAIN_ABBREVIATIONS = {
    "astr.": "astronomy",
    "bd.": "Buddhism",
    "bio.": "biology",
    "geo.": "geography",
    "hist.": "history",
    "jn.": "Jainism",
    "lex.": "lexicography",
    "lit.": "literature",
    "math.": "mathematics",
    "méd.": "medicine",
    "mus.": "music",
    "myth.": "mythology",
    "phil.": "philosophy",
    "phon.": "phonetics",
    "rit.": "ritual",
    "SOC.": "society",
    "ZOO.": "zoology",
}

LANGUAGE_ABBREVIATIONS = {
    "all.": "German",
    "ang.": "English",
    "fr.": "French",
    "gr.": "Greek",
    "hi.": "Hindi",
    "lat.": "Latin",
    "pt.": "Portuguese",
    "ru.": "Russian",
    "prk.": "Prakrit",
    "véd.": "Vedic",
}

def expand_abbreviation(abbr: str, context: str = "") -> str:
    """Expand a French abbreviation to English with optional context."""
    abbr = abbr.strip().lower()
    
    # Check all abbreviation dictionaries
    if abbr in GRAMMATICAL_ABBREVIATIONS:
        return GRAMMATICAL_ABBREVIATIONS[abbr]
    elif abbr in COMPOUND_INDICATORS:
        return COMPOUND_INDICATORS[abbr]
    elif abbr in DOMAIN_ABBREVIATIONS:
        return DOMAIN_ABBREVIATIONS[abbr]
    elif abbr in LANGUAGE_ABBREVIATIONS:
        return LANGUAGE_ABBREVIATIONS[abbr]
    
    # Return original if not found
    return abbr

def expand_morphology_string(morph_str: str) -> str:
    """Expand abbreviations in a morphology analysis string."""
    # Example: "m. sg. nom." → "masculine singular nominative"
    parts = morph_str.split()
    expanded_parts = [expand_abbreviation(part) for part in parts]
    return " ".join(expanded_parts)

def parse_grammatical_codes(code_str: str) -> dict:
    """Parse Heritage grammatical codes into structured data."""
    # Example: "m. du. acc." → {"gender": "masculine", "number": "dual", "case": "accusative"}
    parts = code_str.split()
    result = {}
    
    for part in parts:
        expanded = expand_abbreviation(part)
        
        # Categorize by type
        if expanded in ["masculine", "feminine", "neuter"]:
            result["gender"] = expanded
        elif expanded in ["singular", "dual", "plural"]:
            result["number"] = expanded
        elif expanded in ["nominative", "accusative", "instrumental", "dative", 
                         "ablative", "genitive", "locative", "vocative"]:
            result["case"] = expanded
        elif expanded in ["present", "imperfect", "perfect", "aorist", "future"]:
            result["tense"] = expanded
        elif expanded in ["active", "middle", "passive"]:
            result["voice"] = expanded
        elif expanded in ["indicative", "imperative", "optative", "subjunctive", "injunctive"]:
            result["mood"] = expanded
    
    return result
```

### 2.2 Integrate with Morphology Parser
**File**: `src/langnet/heritage/parsers.py`

```python
from .abbreviations import expand_morphology_string, parse_grammatical_codes

class SimpleHeritageParser:
    # ... existing code ...
    
    def _parse_analysis_table(self, table) -> dict[str, Any] | None:
        """Parse analysis table with abbreviation expansion."""
        analysis = {
            "word": "",
            "lemma": "",
            "root": "",
            "pos": "",
            "grammatical_codes": "",
            "grammatical_details": {},
            "case": None,
            "gender": None,
            "number": None,
            "person": None,
            "tense": None,
            "voice": None,
            "mood": None,
            "stem": "",
            "meaning": [],
            "lexicon_refs": [],
            "confidence": 0.0,
        }
        
        # Extract the pattern like [agni]{m. du. acc. | m. du. nom.}
        table_text = table.get_text(strip=True)
        pattern_match = re.search(r"\[([^\]]+)\]\{([^}]+)\}", table_text)
        
        if pattern_match:
            analysis["word"] = pattern_match.group(1)
            grammatical_codes = pattern_match.group(2)
            analysis["grammatical_codes"] = grammatical_codes
            
            # Expand abbreviations
            expanded_codes = expand_morphology_string(grammatical_codes)
            analysis["grammatical_details"] = parse_grammatical_codes(grammatical_codes)
            
            # Extract individual fields
            details = analysis["grammatical_details"]
            analysis.update({
                "case": details.get("case"),
                "gender": details.get("gender"),
                "number": details.get("number"),
                "tense": details.get("tense"),
                "voice": details.get("voice"),
                "mood": details.get("mood"),
            })
            
            # Determine POS from grammatical codes
            if "participle" in expanded_codes:
                analysis["pos"] = "participle"
            elif "verb" in expanded_codes or any(x in expanded_codes for x in ["present", "future", "aorist"]):
                analysis["pos"] = "verb"
            elif any(x in expanded_codes for x in ["nominative", "accusative", "genitive"]):
                analysis["pos"] = "noun"
            elif "adjective" in expanded_codes:
                analysis["pos"] = "adjective"
        
        return analysis if analysis["word"] else None
```

## Phase 3: Smart Velthuis Normalization

### 3.1 Enhanced Encoding Service
**File**: `src/langnet/heritage/encoding_service.py`

```python
class SmartVelthuisNormalizer:
    """Smart normalization for Velthuis input variations."""
    
    # Common Sanskrit vowel patterns
    VOWEL_PATTERNS = {
        r'\ba([^a]|$)': 'a',    # Short a at word beginning or before consonant
        r'aa\b': 'aa',          # Long aa at word end
        r'\bi([^i]|$)': 'i',    # Short i
        r'ii\b': 'ii',          # Long ii at word end
        r'\bu([^u]|$)': 'u',    # Short u
        r'uu\b': 'uu',          # Long uu at word end
    }
    
    # Common word endings that should be long
    LONG_ENDING_PATTERNS = [
        ('a$', 'aa'),    # Final a often should be aa
        ('i$', 'ii'),    # Final i often should be ii  
        ('u$', 'uu'),    # Final u often should be uu
    ]
    
    @classmethod
    def normalize(cls, text: str, aggressive: bool = False) -> list[str]:
        """Generate normalized Velthuis variants for a given input.
        
        Returns list of variants to try, ordered by likelihood.
        """
        variants = [text]  # Original first
        
        # Apply common corrections
        corrected = cls._apply_common_corrections(text)
        if corrected != text:
            variants.append(corrected)
        
        # Try long vowel variants for word endings
        if aggressive:
            long_variants = cls._generate_long_vowel_variants(text)
            variants.extend(long_variants)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_variants = []
        for v in variants:
            if v not in seen:
                seen.add(v)
                unique_variants.append(v)
        
        return unique_variants
    
    @classmethod
    def _apply_common_corrections(cls, text: str) -> str:
        """Apply common Velthuis corrections."""
        corrections = [
            ('sh', 'z'),      # sha → za
            ('Sh', 'S'),      # Sha → Sa (retroflex)
            ('.a', '.a'),     # Preserve avagraha
            ('RR', 'RR'),     # Preserve vowel r
            ('LL', 'LL'),     # Preserve vowel l
        ]
        
        result = text
        for wrong, right in corrections:
            result = result.replace(wrong, right)
        
        return result
    
    @classmethod
    def _generate_long_vowel_variants(cls, text: str) -> list[str]:
        """Generate variants with long vowel endings."""
        variants = []
        
        for pattern, replacement in cls.LONG_ENDING_PATTERNS:
            if re.search(pattern, text):
                long_version = re.sub(pattern, replacement, text)
                variants.append(long_version)
        
        # Also try adding H (visarga) for nouns
        if text and text[-1].isalpha():
            variants.append(text + 'H')
        
        return variants
```

### 3.2 Integration with HTTP Client
**File**: `src/langnet/heritage/client.py`

```python
from .encoding_service import SmartVelthuisNormalizer

class HeritageHTTPClient:
    # ... existing code ...
    
    def fetch_morphology_with_fallback(self, word: str, **kwargs) -> dict[str, Any]:
        """Fetch morphology with automatic Velthuis normalization fallback."""
        
        # Generate normalization variants
        variants = SmartVelthuisNormalizer.normalize(word, aggressive=True)
        
        results = []
        for variant in variants:
            try:
                result = self.fetch_morphology(variant, **kwargs)
                
                # Check if result is valid (not unknown/grey_back)
                if self._is_valid_result(result):
                    result["used_variant"] = variant
                    result["tried_variants"] = variants
                    return result
                
                results.append({
                    "variant": variant,
                    "result": result,
                    "valid": self._is_valid_result(result)
                })
                
            except Exception as e:
                results.append({
                    "variant": variant,
                    "error": str(e),
                    "valid": False
                })
        
        # If no variant worked, return the best we have
        best_result = self._select_best_result(results)
        if best_result:
            best_result["used_variant"] = best_result["variant"]
            best_result["tried_variants"] = variants
            best_result["fallback_used"] = True
            return best_result["result"]
        
        # Return error if all failed
        return {
            "error": "All Velthuis variants failed",
            "tried_variants": variants,
            "results": results
        }
    
    def _is_valid_result(self, result: dict) -> bool:
        """Check if morphology result is valid (not unknown)."""
        html = result.get("raw_html", "")
        # Check for unknown marker or grey background
        return "{?}" not in html and "grey_back" not in html
    
    def _select_best_result(self, results: list) -> dict:
        """Select the best result from multiple variants."""
        valid_results = [r for r in results if r.get("valid")]
        if not valid_results:
            return None
        
        # Prefer results with more solutions
        def score_result(r):
            result = r.get("result", {})
            html = result.get("raw_html", "")
            
            # Extract solution count
            match = re.search(r'(\d+)\s+solution[s]?\s+kept', html)
            solutions = int(match.group(1)) if match else 0
            
            # Prefer substantive (deep_sky_back) over compounds
            if "deep_sky_back" in html:
                solutions += 10
            
            return solutions
        
        return max(valid_results, key=score_result)
```

## Phase 4: Documentation Consolidation

### 4.1 Create Unified Documentation
**File**: `docs/heritage_integration_guide.md`

```markdown
# Heritage Platform Integration Guide

## Velthuis Encoding Requirements

### Long Vowel Marking
Heritage Platform requires explicit long vowel marking:
- Short `a` → `a`
- Long `ā` → `aa`
- Short `i` → `i`
- Long `ī` → `ii`
- Short `u` → `u`
- Long `ū` → `uu`

### Examples:
| Input | Correct Velthuis | Result |
|-------|------------------|---------|
| `agni` | `agni` | Unknown ({?}) |
| `agnī` | `agnii` | Proper analysis |
| `sita` | `sita` | Compound analysis |
| `sītā` | `siitaa` | Noun analysis |

### Common Patterns:
1. **Word-final vowels often long**: `deva` → try `devaa`
2. **Nouns often need visarga**: `deva` → try `devaH`
3. **Retroflex consonants**: `t` → `T`, `d` → `D`, `n` → `N`

## Abbreviations Reference

### Grammatical Abbreviations (French → English)
| Abbr | English | Category |
|------|---------|----------|
| `m.` | masculine | Gender |
| `f.` | feminine | Gender |
| `n.` | neuter | Gender |
| `sg.` | singular | Number |
| `du.` | dual | Number |
| `pl.` | plural | Number |
| `nom.` | nominative | Case |
| `acc.` | accusative | Case |
| `voc.` | vocative | Case |

[Complete list in abbreviations.py]

## Color Coding Guide

Heritage Platform uses background colors to indicate grammatical categories:

| Color | CSS Class | Meaning | Example |
|-------|-----------|---------|---------|
| Cyan | `deep_sky_back` | Substantives (nouns, adjectives) | `agnii` |
| Green | `lawngreen_back` | Compounds | `sita` |
| Blue | `blue` | Finite verbs | `bhavati` |
| Grey | `grey_back` | Unknown/Error | `agni` |

## API Usage Examples

### Basic Morphology Query
```python
from langnet.heritage import HeritageHTTPClient

client = HeritageHTTPClient()
result = client.fetch_morphology_with_fallback("agni")
print(result["solutions"])
```

### With Manual Velthuis
```python
# Always use proper Velthuis encoding
result = client.fetch_morphology("agnii")  # Correct
result = client.fetch_morphology("siitaa")  # Correct
```

### Accessing Abbreviations
```python
from langnet.heritage.abbreviations import expand_morphology_string

code = "m. sg. nom."
expanded = expand_morphology_string(code)  # "masculine singular nominative"
```

## Troubleshooting

### Common Issues:
1. **No solutions returned**: Try long vowel variant (`agni` → `agnii`)
2. **Unknown analysis (`{?}`)**: Check Velthuis encoding
3. **Wrong part of speech**: Check color class for grammatical category

### Debug Mode:
```bash
export HERITAGE_VERBOSE=true
python -m langnet.cli query skt agni --output detailed
```

## References
- Heritage Platform: http://localhost:48080
- Manual: http://localhost:48080/manual.html
- Source: `src/langnet/heritage/`
```

### 4.2 Archive Old Documents
Move to `docs/plans/completed/skt/`:
- `HERITAGE_ABBR.md` → Integrated into code
- `VELTHUIS_INPUT_TIPS.md` → Consolidated into guide
- `HERITAGE_ENCODING_STRATEGY.md` → Implemented/consolidated

## Phase 5: Implementation Timeline

### Week 1: Fuzz Testing & Analysis
1. Create fuzz test corpus (`examples/debug/`)
2. Run comprehensive fuzz tests
3. Analyze patterns and failure rates
4. Generate baseline metrics

### Week 2: Core Implementation
1. Implement `SmartVelthuisNormalizer`
2. Create `abbreviations.py` module
3. Update `parsers.py` with abbreviation expansion
4. Add fallback logic to `client.py`

### Week 3: Integration & Testing
1. Update `LanguageEngine` to use new methods
2. Create integration tests
3. Test with real user queries
4. Performance benchmarking

### Week 4: Documentation & Polish
1. Create unified documentation
2. Archive old documents
3. Update README and API docs
4. Create user examples

## Success Criteria

1. **Fuzz Test Coverage**: 95% of test corpus returns valid results
2. **Unknown Rate Reduction**: <10% unknown (`{?}`) results
3. **Performance**: <100ms additional latency for fallback
4. **User Experience**: Clear error messages with suggestions
5. **Documentation**: Complete guide with examples

## Prioritization and Timeline

### Day 1 (Immediate)
1. **Fix parser bug** in `src/langnet/heritage/parsers.py` - Critical blocker
2. **Run validation test** - Confirm the hypothesis
3. **Implement minimal fallback** - Immediate user benefit
4. **Test current CLI** - Understand user experience

### Day 2-3 (Short-term)
1. **Create fuzz test corpus** - Quantify the problem
2. **Run comprehensive fuzz tests** - Gather data
3. **Analyze patterns** - Identify most common issues
4. **Implement SmartVelthuisNormalizer** - Based on test results

### Day 4-5 (Medium-term)
1. **Create abbreviations module** - French-to-English translations
2. **Integrate abbreviation expansion** - Better parsing
3. **Update parsers with color analysis** - Extract grammatical info
4. **Add user suggestions** - "Did you mean 'agnii'?"

### Week 2 (Long-term)
1. **Full documentation consolidation** - Unified guide
2. **Performance optimization** - Caching, batch processing
3. **Edge case handling** - Rare encoding issues
4. **User feedback integration** - Real-world testing

## Why This Order?
1. **Parser bug must be fixed first** - Existing code is broken
2. **Validation before implementation** - Confirm we're solving the right problem
3. **Quick wins for users** - Simple fallback provides immediate value
4. **Data-driven development** - Fuzz tests guide intelligent solutions
5. **Documentation consolidation** - Prevent knowledge fragmentation

## Next Steps

1. **@coder**: Fix parser bug in `parsers.py:181-182`
2. **@coder**: Create validation test script
3. **@sleuth**: Run validation and analyze results
4. **@coder**: Implement minimal fallback in `client.py`
5. **@coder**: Create fuzz test framework
6. **@sleuth**: Run fuzz tests and identify patterns
7. **@coder**: Build `SmartVelthuisNormalizer` based on patterns
8. **@coder**: Create `abbreviations.py` module
9. **@artisan**: Integrate everything with performance optimizations
10. **@scribe**: Create unified documentation and archive old docs

**Immediate Action**: Fix the parser bug and validate the hypothesis. This ensures we're building on stable ground.