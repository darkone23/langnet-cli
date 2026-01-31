# Heritage Sanskrit Query Encoding Strategy Plan

## Status: IN PROGRESS - Smart Input Detection + sktsearch Integration

## Problem Summary

Fuzzing 149 Sanskrit words against Heritage API revealed **23.6% failure rate** (26/110 words returned 0 solutions):

### Failure Patterns

1. **Dot prefix (avagraha)** - 75% failure rate
   - `.agni` → 0 solutions
   - `.deva` → 1 solution (exception)
   - `.yoga` → 0 solutions

2. **Retroflex consonants (Velthuis R, T, D, N)** - 100% failure rate
   - `kRSNa` → 0 solutions
   - `viSNu` → 0 solutions
   - `maNi` → 0 solutions
   - `gaNesha` → 0 solutions

3. **Combined issues** - 100% failure rate
   - `.maatR` (dot + retroflex) → 0 solutions

### Comparison: Same words work without special chars

| Input | Result | Note |
|--------|---------|-------|
| `.agni` | 0 solutions | Failed |
| `agni` | 1 solution | ✓ Works |
| `maNi` | 0 solutions | Failed |
| `mani` | 1 solution | ✓ Works |
| `viSNu` | 0 solutions | Failed |
| `visnu` | 1 solution | ✓ Works |

## Root Cause Analysis

### The Pre-Encoding Problem

Current flow:
```
User Input → indic_transliteration → Velthuis → Heritage sktreader → 0 solutions
```

Issue: `indic_transliteration` produces **valid Velthuis** but Heritage's `sktreader` CGI can't parse certain Velthuis encodings:
1. Leading dots (avagraha) are mishandled
2. Retroflex consonants (R, T, D, N) in Velthuis produce invalid Devanagari when converted
3. Long vowels (ā, ī, ū) with retroflex fail

### The Double-Encoding Problem

When user provides Velthuis input (`.agni`, `kRSNa`), we:
1. "Helpfully" pre-convert it (breaking it further)
2. Send broken Velthuis to Heritage
3. Heritage receives garbage → 0 solutions

## Proposed Solution: Smart Input Detection + sktsearch

### New Architecture

```
User Input
    ↓
Smart Encoding Detection
    ↓
┌───────────┬───────────┬───────────┐
│ Devanagari │   IAST    │ Velthuis  │ Other
│    ↓       │     ↓      │    ↓      │    ↓
│   sktsearch │  sktsearch │ sktsearch │ sktsearch
│   (bare)  │   (bare)  │   (bare)  │   (bare)
│    ↓       │     ↓      │    ↓      │    ↓
└──────┬────┴──────┬────┴───────┘
       ↓             ↓            ↓
  Canonical Devanagari (from Heritage response)
       ↓
┌──────────┬──────────┬──────────┐
│  Morphology │  CDSL    │ Dictionary
│   (Velthuis)│  (SLP1)   │  (Devanagari)
└──────────┴──────────┴──────────┘
```

### Phase 1: Smart Encoding Detection

Detect what encoding the user provided:

```python
def detect_encoding(text: str) -> str:
    """Detect Sanskrit input encoding."""
    
    # 1. Check for Devanagari (Unicode range)
    if all('\u0900' <= c <= '\u097F' for c in text):
        return "devanagari"
    
    # 2. Check for IAST (with macrons)
    iast_chars = set("āīūṛṝḹḹṃḥṅñṭḍṇṣśḻḽ")
    if any(c in iast_chars for c in text):
        return "iast"
    
    # 3. Check for Velthuis (uppercase retroflex)
    velthuis_chars = set("RTDNS")
    if any(c in velthuis_chars for c in text):
        return "velthuis"
    
    # 4. Check for HK (common Sanskrit transcription)
    hk_chars = set("M N G J Y W Q Z L K S")
    if any(c in hk_chars for c in text):
        return "hk"
    
    # 5. Check for SLP1 (phonetic alphabet)
    slp1_chars = set("aAiIuUfFxXEeOoKkKGgGHhjJYcCwWqQrRNdzZbBpPmMtTdDsSnNlLvvyYsSz")
    if all(c in slp1_chars or c in "AIEOU" for c in text):
        return "slp1"
    
    # 6. Default: ASCII (bare Latin)
    return "ascii"
```

### Phase 2: sktsearch Canonical Lookup

Use Heritage's **sktsearch** CGI to get canonical Sanskrit form:

```python
def fetch_canonical_sanskrit(query: str, encoding: str) -> dict:
    """Get canonical Sanskrit from Heritage sktsearch."""
    
    # sktsearch wants lowercase alpha-only
    bare_query = re.sub(r"[^a-z]", "", query.lower())
    
    params = {
        "q": bare_query,
        "lex": "MW",
        "t": "VH",
    }
    
    # Query sktsearch
    html = fetch_cgi_script("sktsearch", params)
    soup = BeautifulSoup(html, "html.parser")
    
    # Extract Devanagari from response
    for link in soup.find_all("a", href=True):
        if "/skt/MW/" in link.get("href"):
            # Convert IAST in link text to Devanagari
            iast_text = link.get_text(strip=True)
            devanagari = transliterate(iast_text, ITRANS, DEVANAGARI)
            return {
                "original_query": query,
                "detected_encoding": encoding,
                "canonical_sanskrit": devanagari,
                "match_method": "sktsearch",
            }
    
    return {"canonical_sanskrit": None, "match_method": "not_found"}
```

### Phase 3: Downstream Operations

Use canonical Devanagari for all Heritage queries:

1. **Morphology Analysis** (sktreader)
   - Input: Canonical Devanagari
   - Convert to Velthuis: `transliterate(devanagari, DEVANAGARI, VELTHUIS)`
   - Send to sktreader with `t=VH`

2. **CDSL Lookup**
   - Input: Canonical Devanagari
   - Convert to SLP1: `transliterate(devanagari, DEVANAGARI, SLP1)`
   - Query CDSL index

3. **Dictionary Search**
   - Input: Canonical Devanagari
   - Send to sktsearch/sktindex directly

## Implementation Progress

### ✅ Completed

1. **Added `fetch_canonical_sanskrit()` method** to `HeritageHTTPClient`
   - Strips non-alpha characters
   - Lowercases query
   - Queries sktsearch CGI
   - Extracts Devanagari from response
   - Uses `indic_transliteration` for IAST → Devanagari conversion

2. **Tests show sktsearch works**
   - `yuddhaa` → `युद्ध्ā` (IAST) → `युद्धा` (Devanagari) ✓

### 🚧 In Progress

3. **Smart Encoding Detection**
   - Need to implement `detect_encoding()` function
   - Check for Devanagari, IAST, Velthuis, HK, SLP1, ASCII
   - Return appropriate encoding tag

4. **Update Query Flow**
   - Integrate smart detection into `LanguageEngine.handle_query()`
   - Call `fetch_canonical_sanskrit()` for all Sanskrit queries
   - Use canonical Devanagari for morphology, CDSL, dictionary

### ⏳ To Do

5. **Fix Devanagari → Velthuis conversion**
   - Current `encode_text()` produces invalid Velthuis for some Devanagari
   - Issue with retroflex vowels (ृ, ॄ) and consonants (ट, ठ, ड, ढ, ण)
   - Need to verify `indic_transliteration` output for canonical Devanagari

6. **Update Morphology Parser**
   - Lark parser needs to handle Velthuis encoding properly
   - Test with canonical Devanagari → Velthuis → Heritage
   - Ensure solutions extracted correctly

7. **Add Tests**
   - Test smart encoding detection with all input types
   - Verify canonical Sanskrit lookup works for edge cases
   - Ensure morphology returns solutions with canonical input

8. **Update Documentation**
   - Document supported encodings
   - Add examples for each encoding type
   - Explain fallback behavior

## Test Cases

| Input | Detected | Canonical | Expected Result |
|-------|-----------|------------|-----------------|
| `.agni` | velthuis | `अग्निः` | >0 morphology solutions |
| `agni` | ascii | `अग्नि` | >0 morphology solutions |
| `kRSNa` | velthuis | `कृष्ण` | >0 morphology solutions |
| `अग्नि` | devanagari | `अग्नि` | >0 morphology solutions |
| `yuddhā` | iast | `युद्धा` | >0 morphology solutions |
| `yuddhaa` | ascii | `युद्धा` | >0 morphology solutions |

## Benefits

1. **Robust encoding handling** - Let Heritage's guesser handle ASCII inputs
2. **Canonical forms** - Always use Heritage's canonical Devanagari for consistency
3. **No double-encoding** - Avoid indic_transliteration → Velthuis issues
4. **Better edge case handling** - Support dot prefix, retroflex, long vowels correctly
5. **Backward compatible** - Still support all existing input encodings

## Risks

1. **sktsearch availability** - Relies on sktsearch CGI being available and responsive
2. **Devanagari → Velthuis bugs** - Still need to fix conversion issues
3. **Detection edge cases** - May misclassify ambiguous inputs (e.g., `a` could be ascii or velthuis)

## References

- Fuzzing results: `examples/debug/fuzz_outputs/`
- Implementation: `src/langnet/heritage/client.py::fetch_canonical_sanskrit()`
- Test scripts: `examples/debug/analyze_zero_solutions.py`, `examples/debug/test_hypothesis.py`
