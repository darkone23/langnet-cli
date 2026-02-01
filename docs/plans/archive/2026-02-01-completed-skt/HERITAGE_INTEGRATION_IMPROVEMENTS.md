# Heritage Integration Improvements Plan

## Current Issues Analysis

### 1. Velthuis Input Sensitivity Problem
**Observation**: Querying `agni` vs `agnii` produces dramatically different results:

- `agni` (single i): 1 solution with grey background (`{?}` unknown)
- `agnii` (double i): 2 solutions with proper analysis (`m. du. acc. | m. du. nom.` and `m. du. voc.`)

**Root Cause**: Heritage Platform's sktreader expects explicit long vowel marking in Velthuis:
- Short `i` → `i`
- Long `ī` → `ii`
- Short `a` → `a`
- Long `ā` → `aa`

Our current implementation doesn't handle this correctly in `encoding_service.py`.

### 2. Color Coding and Part-of-Speech Analysis
**Observation**: Different table background colors indicate different grammatical categories:

| Color Class | Background | Meaning |
|-------------|------------|---------|
| `grey_back` | Light grey | Unknown/unrecognized |
| `deep_sky_back` | Cyan | Substantives (Nouns, adjectives, pronouns) |
| `lawngreen_back` | Light green | Compounds (samāsa internal components) |
| `blue` | Blue | Finite verbs (tinnanta) |

**Analysis**: `sita` (short i, short a) shows `lawngreen_back` → compounds, while `siitaa` (long ii, long aa) shows `deep_sky_back` → substantive (noun).

### 3. Encoding Service Limitations
Current `detect_encoding()` in `encoding_service.py`:
- Doesn't properly detect Velthuis long vowel patterns (`aa`, `ii`, `uu`)
- Doesn't normalize ASCII to proper Velthuis
- Doesn't handle diacritics correctly for IAST detection

## Implementation Findings

### Current Architecture Review
1. **`HeritageHTTPClient`** (`src/langnet/heritage/client.py`): Handles CGI requests
2. **`EncodingService`** (`src/langnet/heritage/encoding_service.py`): Converts between encodings
3. **`SimpleHeritageParser`** (`src/langnet/heritage/parsers.py`): Parses HTML responses
4. **`MorphologyParser`**: Uses Lark-based parser for better analysis

### Key Code Locations:
- `fetch_canonical_sanskrit()`: Line 91 in `client.py`
- `to_velthuis()`: Line 124 in `encoding_service.py`
- `detect_encoding()`: Line 41 in `encoding_service.py`

## Actionable Recommendations

### Phase 1: Immediate Fixes (Priority)

#### 1.1 Enhance Encoding Detection
**File**: `src/langnet/heritage/encoding_service.py`
**Goal**: Improve detection of Velthuis long vowel patterns

```python
def detect_encoding(text: str) -> str:
    """Enhanced encoding detection with Velthuis long vowel awareness."""
    
    # Add Velthuis long vowel pattern detection
    velthuis_long_vowel_pattern = re.compile(r'[a-z][a-z]')  # aa, ii, uu, etc.
    if velthuis_long_vowel_pattern.search(text):
        # Check for Velthuis uppercase retroflex R, T, D, N, S
        if any(c in "RTDNS" for c in text):
            return "velthuis"
        # Check for mixed case with long vowels
        elif any(c.isupper() for c in text):
            return "velthuis"
    
    # Rest of existing detection logic...
```

#### 1.2 Add Velthuis Normalization
**File**: `src/langnet/heritage/encoding_service.py`
**Goal**: Normalize ASCII input to proper Velthuis

```python
def normalize_to_velthuis(text: str) -> str:
    """Convert ASCII Sanskrit to proper Velthuis encoding."""
    # Map ASCII approximations to Velthuis
    velthuis_map = {
        'aa': 'aa',
        'ii': 'ii',
        'uu': 'uu',
        'RR': 'RR',  # vowel
        'LL': 'LL',  # vowel
        'ai': 'ai',
        'au': 'au',
        'kh': 'kh',
        'gh': 'gh',
        'ch': 'ch',
        'jh': 'jh',
        'th': 'th',
        'dh': 'dh',
        'ph': 'ph',
        'bh': 'bh',
        'sh': 'z',
        'Sh': 'S',
        '.': '.',  # avagraha
    }
    
    # Simple conversion - enhance with proper Sanskrit rules
    for ascii_pattern, velthuis_pattern in velthuis_map.items():
        text = text.replace(ascii_pattern, velthuis_pattern)
    
    return text
```

#### 1.3 Update Query Flow
**File**: `src/langnet/heritage/client.py`
**Goal**: Apply normalization before sending to sktreader

```python
def fetch_morphology(self, word: str, lexicon: str = "SH", **kwargs) -> dict[str, Any]:
    """Fetch morphology with proper Velthuis encoding."""
    
    # Normalize to proper Velthuis
    normalized_word = self.normalize_to_velthuis(word)
    
    # Use canonical Sanskrit lookup first
    canonical = self.fetch_canonical_sanskrit(normalized_word, lexicon)
    if canonical.get("canonical_sanskrit"):
        # Use canonical form for better results
        velthuis_form = EncodingService.to_velthuis(canonical["canonical_sanskrit"])
    else:
        # Fallback to normalized input
        velthuis_form = normalized_word
    
    # Build parameters with proper encoding
    params = HeritageParameterBuilder.build_morph_params(
        text=velthuis_form,
        lexicon=lexicon,
        **kwargs
    )
    
    # Fetch from sktreader
    return self.fetch_cgi_script("sktreader", params)
```

### Phase 2: Enhanced Parsing

#### 2.1 Extract Color Coding Information
**File**: `src/langnet/heritage/parsers.py`
**Goal**: Parse background colors for grammatical analysis

```python
def _parse_solution_section(self, section_span, soup) -> dict[str, Any] | None:
    """Parse solution section including color coding."""
    
    # Existing parsing code...
    
    # Extract color information
    table = next_element.find("table")
    if table:
        color_class = table.get("class", [""])[0]
        grammatical_category = self._color_to_category(color_class)
        solution["grammatical_category"] = grammatical_category
```

#### 2.2 Map Colors to Grammatical Categories
**File**: `src/langnet/heritage/parsers.py`
**Goal**: Translate color codes to grammatical information

```python
def _color_to_category(self, color_class: str) -> str:
    """Map CSS color classes to grammatical categories."""
    color_map = {
        "grey_back": "unknown",
        "deep_sky_back": "substantive",  # Nouns, adjectives, pronouns
        "lawngreen_back": "compound",     # Samāsa components
        "blue": "finite_verb",           # Tinnanta
        "cyan": "indeclinable",          # Avyaya, particles
        "magenta": "compound_part",     # Compound segments
        "yellow": "kridanta",            # Participles, infinitives
        "orange": "kridanta",            # Verbal adjectives/nouns
        "red": "error",                  # Unrecognized
    }
    return color_map.get(color_class, "unknown")
```

### Phase 3: Testing and Validation

#### 3.1 Create Test Suite
**File**: `tests/test_heritage_encoding_improvements.py`
**Goal**: Test normalization and color parsing

```python
def test_velthuis_normalization():
    """Test ASCII to Velthuis conversion."""
    assert normalize_to_velthuis("agni") == "agni"
    assert normalize_to_velthuis("agnii") == "agnii"
    assert normalize_to_velthuis("sita") == "sita"
    assert normalize_to_velthilus("siitaa") == "siitaa"
    assert normalize_to_velthuis("kRSNa") == "kRSNa"
    assert normalize_to_velthuis(".agni") == ".agni"

def test_color_parsing():
    """Test color code to grammatical category mapping."""
    parser = SimpleHeritageParser()
    assert parser._color_to_category("deep_sky_back") == "substantive"
    assert parser._color_to_category("lawngreen_back") == "compound"
    assert parser._color_to_category("blue") == "finite_verb"
```

#### 3.2 Integration Tests
**Goal**: Test end-to-end queries

```bash
# Test cases with expected results
curl "http://localhost:48080/cgi-bin/skt/sktreader?t=VH;lex=SH;font=roma;cache=t;st=t;us=f;text=agnii"
curl "http://localhost:48080/cgi-bin/skt/sktreader?t=VH;lex=SH;font=roma;cache=t;st=t;us=f;text=siitaa"
```

### Phase 4: Documentation and API Updates

#### 4.1 Update API Documentation
**File**: `README.md` and `REFERENCE.md`
**Goal**: Document Velthuis requirements and color coding

Add section:
```markdown
## Velthuis Encoding Requirements

The Heritage Platform expects proper Velthuis encoding:
- Long vowels must be doubled: `ā` → `aa`, `ī` → `ii`, `ū` → `uu`
- Retroflex consonants: `ṭ` → `T`, `ḍ` → `D`, `ṇ` → `N`, `ṣ` → `S`
- Avagraha (apostrophe): `.` (dot prefix)
- Visarga: `H`

Examples:
- `agni` (short) → `agni`
- `agnī` (long) → `agnii`
- `kṛṣṇa` → `kRSNa`
- `.agni` → `.agni`
```

#### 4.2 Color Code Documentation
**Goal**: Document grammatical category colors

| Color | CSS Class | Grammatical Category | Examples |
|-------|-----------|---------------------|----------|
| Cyan | `deep_sky_back` | Substantives | Nouns, adjectives, pronouns |
| Green | `lawngreen_back` | Compounds | Internal components of samāsa |
| Blue | `blue` | Finite verbs | Conjugated verb forms |
| Light Blue | `cyan` | Indeclinables | Adverbs, particles, preverbs |
| Magenta | `magenta` | Compound parts | Samāsa segments |
| Yellow/Orange | `yellow`/`orange` | Kridantas | Participles, infinitives |
| Red | `red` | Errors | Unrecognized forms |

## Implementation Priority

### High Priority (Week 1)
1. Fix `normalize_to_velthuis()` function
2. Update `detect_encoding()` for long vowel patterns
3. Integrate normalization in `fetch_morphology()`
4. Basic tests for `agni`/`agnii`, `sita`/`siitaa`

### Medium Priority (Week 2)
1. Add color parsing to morphology results
2. Update `SimpleHeritageParser` to extract grammatical categories
3. Enhance `MorphologyParser` with color information
4. Create comprehensive test suite

### Low Priority (Week 3)
1. Update API documentation
2. Add examples to README
3. Create user guide for Velthuis input
4. Performance optimization for repeated queries

## Expected Outcomes

1. **Improved Accuracy**: `agnii` queries should return proper morphological analysis
2. **Better POS Detection**: Color coding provides grammatical category hints
3. **Enhanced User Experience**: Proper guidance on Velthuis encoding
4. **Consistent Results**: Canonical Sanskrit forms for all queries

## Risks and Mitigation

### Risks:
1. **Breaking existing queries**: Normalization may change input behavior
2. **Performance impact**: Additional encoding checks
3. **False positives**: Incorrect encoding detection

### Mitigation:
1. **Backward compatibility**: Keep ASCII fallback
2. **Caching**: Cache encoding detection results
3. **Validation**: Test with known Sanskrit corpora
4. **Fallback**: Graceful degradation on detection failure

## Success Metrics

1. **Test Coverage**: 90% of Sanskrit words return >0 solutions
2. **Accuracy Improvement**: 50% reduction in "unknown" (`grey_back`) results
3. **User Feedback**: Positive feedback on improved results
4. **Integration**: Seamless with existing CDSL and dictionary lookups

## Next Steps

1. **@coder**: Implement Phase 1 improvements in `encoding_service.py`
2. **@coder**: Update `client.py` to use normalized Velthuis
3. **@sleuth**: Test with fuzzing suite from `examples/debug/`
4. **@artisan**: Optimize performance and add caching
5. **@scribe**: Update documentation and user guides

## References

1. `docs/plans/active/skt/VELTHUIS_INPUT_TIPS.md`
2. `docs/plans/active/skt/HERITAGE_ENCODING_STRATEGY.md`
3. `src/langnet/heritage/encoding_service.py`
4. `src/langnet/heritage/client.py`
5. Heritage Platform manual: `http://localhost:48080/manual.html`