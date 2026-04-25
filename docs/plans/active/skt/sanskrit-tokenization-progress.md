# Sanskrit Tokenization Implementation - Progress Report
## Status Update for "dhṛitarāśhtra uvācha dharma-kṣhetre kuru-kṣhetre"

**Feature Area**: Sanskrit Infrastructure  
**Status**: 🚧 IN PROGRESS (Phase 1 Complete)  
**Last Updated**: 2026-04-12  
**Current Phase**: Foundation Complete, Normalization Pending

## 1. What Has Been Implemented

### ✅ Phase 1: Foundation Tokenization - COMPLETE

**Files Created**:
1. `src/langnet/tokenization/__init__.py` - Package initialization
2. `src/langnet/tokenization/models.py` - Data models (Token, TokenComponent, TokenizedPassage)
3. `src/langnet/tokenization/sanskrit.py` - Main SanskritTokenizer with compound handling
4. `src/langnet/tokenization/service.py` - TokenAnalysisService (needs integration)
5. `src/langnet/compounds/__init__.py` - Package initialization  
6. `src/langnet/compounds/splitter.py` - CompoundSplitter logic

**Core Functionality Working**:
- ✅ Text splitting on whitespace
- ✅ Hyphenated compound detection (`dharma-kṣhetre`)
- ✅ Compound splitting into components with roles (initial/final/medial)
- ✅ Compound type identification (tatpuruṣa for 2-part compounds)
- ✅ Dictionary query generation (compound + component forms)
- ✅ Data model serialization to dict/JSON

**Test Results for Gītā 1.1**:
```
Input: "dhṛitarāśhtra uvācha dharma-kṣhetre kuru-kṣhetre"
Tokens: 4
Compounds detected: 2 (dharma-kṣhetre, kuru-kṣhetre)
Compound types: tatpuruṣa (both)
Components correctly split: ✅
Query generation working: ✅
```

## 2. Current Implementation Details

### Tokenization Pipeline:
```python
# Current working implementation
tokenizer = SanskritTokenizer()
passage = tokenizer.tokenize("dhṛitarāśhtra uvācha dharma-kṣhetre kuru-kṣhetre")

# Returns:
# - Token 0: "dhṛitarāśhtra" (non-compound)
# - Token 1: "uvācha" (non-compound)  
# - Token 2: "dharma-kṣhetre" (compound, tatpuruṣa)
#   - Components: ["dharma" (initial), "kṣhetre" (final)]
# - Token 3: "kuru-kṣhetre" (compound, tatpuruṣa)
#   - Components: ["kuru" (initial), "kṣhetre" (final)]
```

### Query Generation:
```python
compound_queries, component_queries = tokenizer.get_compound_queries(passage)
# compound_queries: ['dhṛitarāśhtra', 'uvācha', 'dharma-kṣhetre', 'dharmakṣhetre', ...]
# component_queries: ['dhṛitarāśhtra', 'uvācha', 'dharma', 'kṣhetre', 'kuru']
```

## 3. What Remains to be Implemented

### 🔄 Phase 2: Normalization & Encoding - IN PROGRESS

**Missing Components**:
1. **Encoding detection per token** - Integrate with SanskritNormalizer's `_detect_encoding()`
2. **IAST → Velthuis conversion** - Proper normalization for Heritage Platform
3. **Batch normalization** - Process token lists efficiently
4. **Integration with existing SanskritNormalizer** - Reuse conversion logic

**Required Integration**:
- Connect `SanskritTokenizer` with `SanskritNormalizer._to_velthuis()`
- Use `indic-transliteration.sanscript` for accurate conversions
- Handle multiple encodings: IAST, Devanagari, SLP1, HK, ASCII

### 🔄 Phase 3: CLI & Integration - NOT STARTED

**Tasks**:
1. Add CLI command: `langnet-cli tokenize-san "text"`
2. Integration with Heritage Platform queries
3. Integration with CDSL dictionary lookups
4. Caching implementation for performance

### 🔄 Phase 4: Advanced Features - FUTURE

**Future Enhancements**:
1. Sandhi-aware tokenization
2. Enclitic detection (ca, vā, eva)
3. Educational explanations for compounds
4. Performance optimization for long texts

## 4. Technical Debt & Issues

### Current Limitations:
1. **No proper normalization** - Tokens remain in input encoding
2. **Basic IAST→Velthuis conversion needed** - Hardcoded mapping required
3. **No integration with existing SanskritNormalizer** - Duplicates functionality
4. **No CLI interface** - Only programmatic API available
5. **No tests** - Need comprehensive test suite

### Integration Points Needed:
1. **With SanskritNormalizer** (`src/langnet/normalizer/sanskrit.py`):
   - Reuse `_detect_encoding()` method
   - Reuse `_to_velthuis()` conversion logic
   - Reuse Heritage query preparation

2. **With Heritage Platform**:
   - Generate proper Velthuis queries
   - Parse Heritage response for compound confirmation
   - Extract component analysis from color coding

3. **With CDSL Dictionary**:
   - Query components in SLP1 encoding
   - Use existing CDSL handler integration

## 5. Immediate Next Steps (Priority Order)

### 1. Add Basic Normalization (Day 1)
```python
# Extend SanskritTokenizer with normalization
def normalize_tokens(self, passage: TokenizedPassage) -> None:
    # Use existing SanskritNormalizer or implement basic conversion
    # IAST → Velthuis: "dhṛitarāśhtra" → "dhRitarASTra"
    # IAST → Velthuis: "kṣhetre" → "kSetre"
```

### 2. Create Simple CLI Command (Day 1)
```python
# Add to src/langnet/cli.py
@main.command()
@click.argument("text")
def tokenize_sanskrit(text: str):
    """Tokenize Sanskrit text with compound analysis."""
```

### 3. Write Tests (Day 2)
- Unit tests for tokenization
- Integration tests with normalization
- Test Gītā 1.1 end-to-end

### 4. Integrate with SanskritNormalizer (Day 2-3)
- Refactor to use existing encoding detection
- Reuse Velthuis conversion logic
- Add batch processing methods

## 6. Code Examples Needed

### Normalization Implementation:
```python
# In SanskritTokenizer or new NormalizationService
def _normalize_token(self, token: Token) -> Token:
    encoding = self._detect_encoding(token.surface_form)
    if encoding == "iast":
        token.normalized_form = self._iast_to_velthuis(token.surface_form)
    elif encoding == "devanagari":
        token.normalized_form = self._devanagari_to_velthuis(token.surface_form)
    token.encoding = "velthuis"
    return token
```

### CLI Integration:
```python
# In src/langnet/cli.py
from langnet.tokenization.service import TokenAnalysisService

@main.command(name="tokenize-san")
@click.argument("text")
@click.option("--output", type=click.Choice(["text", "json"]), default="text")
def tokenize_sanskrit(text: str, output: str):
    service = TokenAnalysisService()
    result = service.analyze_passage(text)
    
    if output == "json":
        click.echo(service.to_json(text))
    else:
        # Pretty text output
        click.echo(f"Tokens: {len(result['tokens'])}")
        for token in result["tokens"]:
            click.echo(f"  {token['surface']} → {token['normalized']}")
```

## 7. Success Metrics Achieved

### ✅ Phase 1 Success Criteria Met:
- [x] Tokenize Gītā 1.1 into correct word list (4 tokens)
- [x] Detect hyphenated compounds (2 compounds)
- [x] Split compounds into components (dharma + kṣhetre, kuru + kṣhetre)
- [x] Generate dictionary queries

### 🔄 Phase 2 Pending:
- [ ] Normalize tokens to Velthuis format
- [ ] Integrate with SanskritNormalizer
- [ ] CLI command functional
- [ ] Basic tests passing

## 8. Recommendations for Completion

### Short-term (1-2 days):
1. Implement basic IAST→Velthuis normalization
2. Add simple CLI command
3. Write basic unit tests

### Medium-term (3-5 days):
1. Integrate with existing SanskritNormalizer
2. Add encoding detection per token
3. Implement batch processing
4. Add integration tests

### Long-term (1-2 weeks):
1. Sandhi splitting module
2. Educational explanations
3. Performance optimization
4. Full Heritage/CDSL integration

## 9. Current Code Location

**Working Implementation**: `src/langnet/tokenization/sanskrit.py`
**Data Models**: `src/langnet/tokenization/models.py`
**Compound Logic**: `src/langnet/compounds/splitter.py`
**Demo Script**: `examples/debug/sanskrit_tokenization_demo.py`

**Test Command** (run from project root):
```bash
cd /home/nixos/langnet-tools/langnet-cli
python3 -c "
import sys
sys.path.insert(0, 'src')
from langnet.tokenization.sanskrit import SanskritTokenizer
tokenizer = SanskritTokenizer()
passage = tokenizer.tokenize('dhṛitarāśhtra uvācha dharma-kṣhetre kuru-kṣhetre')
print(f'Tokens: {len(passage.tokens)}')
for t in passage.tokens:
    print(f'{t.surface_form} (compound: {t.is_compound})')
"
```

---

**Implementation Team**: @coder @artisan  
**Current Status**: Foundation complete, normalization pending  
**Estimated Completion**: 2-3 days remaining