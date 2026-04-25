# Sanskrit Tokenization Implementation - Concrete Plan
## Focus: Immediate Implementation for "dhṛitarāśhtra uvācha dharma-kṣhetre kuru-kṣhetre"

**Feature Area**: Sanskrit Infrastructure  
**Status**: 🚀 ACTIVE IMPLEMENTATION  
**Priority**: High  
**Estimated Effort**: 3-5 days  
**AI Personas**: @coder @artisan  
**Target**: Functional tokenizer for Bhagavad Gītā 1.1 example

## 1. Immediate Goal
Build a functional Sanskrit tokenizer that can:
1. Split "dhṛitarāśhtra uvācha dharma-kṣhetre kuru-kṣhetre" into individual tokens
2. Handle hyphenated compounds by splitting them into components
3. Normalize tokens to Velthuis format for Heritage Platform queries
4. Prepare queries for dictionary lookup

## 2. Implementation Strategy: Custom Solution

**Decision**: Build custom tokenizer rather than using CLTK because:
- CLTK's Sanskrit support is limited and not well-maintained
- We need tight integration with Heritage Platform (requires Velthuis encoding)
- Need compound-aware processing for hyphenated terms
- Educational focus requires customizable output

**Core Components**:
1. **SanskritTokenizer** - Text splitting and basic tokenization
2. **CompoundSplitter** - Handle hyphenated compounds  
3. **Enhanced SanskritNormalizer** - Batch normalization for tokens
4. **TokenAnalysisService** - Orchestrate tokenization + dictionary lookup

## 3. Concrete Implementation Steps

### Day 1: Foundation & Data Models
1. **Create tokenization data models** (`src/langnet/tokenization/models.py`):
   ```python
   @dataclass
   class Token:
       surface_form: str
       normalized_form: str
       position: int
       encoding: str
       is_compound: bool = False
       compound_type: Optional[str] = None
       components: Optional[list[TokenComponent]] = None
       
   @dataclass
   class TokenComponent:
       surface: str
       normalized: str
       role: str  # "initial", "final"
   ```

2. **Create basic SanskritTokenizer** (`src/langnet/tokenization/sanskrit.py`):
   ```python
   class SanskritTokenizer:
       def tokenize(self, text: str) -> list[Token]:
           """Split Sanskrit text into tokens with whitespace/punctuation."""
   ```

3. **Write tests** for Gītā 1.1 example:
   ```python
   def test_bhagavad_gita_1_1_tokenization():
       tokenizer = SanskritTokenizer()
       tokens = tokenizer.tokenize("dhṛitarāśhtra uvācha dharma-kṣhetre kuru-kṣhetre")
       assert len(tokens) == 4
       assert tokens[0].surface_form == "dhṛitarāśhtra"
       assert tokens[2].surface_form == "dharma-kṣhetre"
   ```

### Day 2: Compound Handling
1. **Create CompoundSplitter** (`src/langnet/compounds/splitter.py`):
   ```python
   class CompoundSplitter:
       def split_hyphenated(self, token: Token) -> list[TokenComponent]:
           """Split hyphenated compounds like 'dharma-kṣhetre'."""
           
       def is_hyphenated_compound(self, text: str) -> bool:
           """Check if token contains hyphen indicating compound."""
   ```

2. **Integrate with SanskritTokenizer**:
   ```python
   class SanskritTokenizer:
       def tokenize(self, text: str) -> list[Token]:
           tokens = self._basic_tokenize(text)
           for token in tokens:
               if self.compound_splitter.is_hyphenated_compound(token.surface_form):
                   token.is_compound = True
                   token.components = self.compound_splitter.split_hyphenated(token)
   ```

3. **Add compound type detection** (basic: tatpuruṣa detection for hyphenated terms)

### Day 3: Normalization & Encoding
1. **Extend SanskritNormalizer** (`src/langnet/normalizer/sanskrit.py`):
   ```python
   class SanskritNormalizer(LanguageNormalizer):
       def normalize_token(self, token: Token) -> Token:
           """Normalize a single token to Velthuis format."""
           
       def normalize_tokens(self, tokens: list[Token]) -> list[Token]:
           """Batch normalize tokens efficiently."""
           
       def prepare_compound_query(self, components: list[str]) -> str:
           """Join compound components for Heritage Platform query."""
   ```

2. **Handle encoding detection per token**:
   - Use existing `_detect_encoding()` method from SanskritNormalizer
   - Apply per-token encoding detection

3. **Implement normalization pipeline**:
   ```
   Raw token → Detect encoding → Convert to Velthuis → Apply compound rules
   ```

### Day 4: Integration & CLI
1. **Create TokenAnalysisService** (`src/langnet/tokenization/service.py`):
   ```python
   class TokenAnalysisService:
       def analyze_passage(self, text: str) -> TokenizedPassage:
           """Full pipeline: tokenize → split compounds → normalize."""
   ```

2. **Add CLI command** (`src/langnet/cli.py`):
   ```python
   @cli.command(name="tokenize-san")
   @click.argument("text")
   def tokenize_sanskrit(text: str):
       """Tokenize Sanskrit text with compound analysis."""
   ```

3. **Test with Heritage Platform**:
   - Generate queries for joined compounds: `dharmakSetre`
   - Generate queries for components: `dharma`, `kSetra`

### Day 5: Testing & Polish
1. **Comprehensive test suite**:
   - Test all 4 tokens from Gītā 1.1
   - Test compound splitting accuracy
   - Test normalization correctness
   - Test encoding detection

2. **Performance optimization**:
   - Batch processing for efficiency
   - Caching of encoding detection
   - Memory-efficient token storage

3. **Documentation**:
   - Update README with new command
   - Add usage examples
   - Document output format

## 4. Key Implementation Details

### Tokenization Rules:
```python
def _basic_tokenize(text: str) -> list[str]:
    # Split on whitespace
    tokens = re.split(r'\s+', text.strip())
    # Keep hyphenated compounds as single tokens initially
    return [t for t in tokens if t]
```

### Compound Splitting Logic:
```python
def split_hyphenated(self, text: str) -> list[str]:
    # "dharma-kṣhetre" → ["dharma", "kṣhetre"]
    parts = text.split('-')
    if len(parts) == 2:
        return parts
    return [text]
```

### Normalization Pipeline:
```python
def normalize_token(token: Token) -> Token:
    # Detect encoding (IAST, Devanagari, etc.)
    encoding = self._detect_encoding(token.surface_form)
    
    # Convert to Velthuis (Heritage format)
    if encoding == "iast":
        velthuis = self._iast_to_velthuis(token.surface_form)
    elif encoding == "devanagari":
        velthuis = self._devanagari_to_velthuis(token.surface_form)
    else:
        velthuis = token.surface_form  # Assume already Velthuis
    
    token.normalized_form = velthuis
    token.encoding = "velthuis"
    return token
```

### Output Format for CLI:
```json
{
  "original_text": "dhṛitarāśhtra uvācha dharma-kṣhetre kuru-kṣhetre",
  "tokens": [
    {
      "surface": "dhṛitarāśhtra",
      "normalized": "dhRitarASTra", 
      "position": 0,
      "encoding": "velthuis",
      "is_compound": false
    },
    {
      "surface": "dharma-kṣhetre",
      "normalized": "dharmakSetre",
      "position": 2,
      "encoding": "velthuis",
      "is_compound": true,
      "compound_type": "tatpuruṣa",
      "components": [
        {"surface": "dharma", "normalized": "dharma", "role": "initial"},
        {"surface": "kṣhetre", "normalized": "kSetra", "role": "final"}
      ]
    }
  ],
  "dictionary_queries": {
    "compound_forms": ["dhRitarASTra", "uvAca", "dharmakSetre", "kurukSetre"],
    "component_forms": ["dhRitarASTra", "uvAca", "dharma", "kSetra", "kuru", "kSetra"]
  }
}
```

## 5. Integration Points

### With Existing SanskritNormalizer:
- Reuse `_detect_encoding()` method
- Reuse `_to_velthuis()` conversion logic
- Reuse Heritage query preparation

### With Heritage Platform:
- Compound forms: Query `dharmakSetre` for full analysis
- Component forms: Query `dharma` and `kSetra` separately
- Parse Heritage color coding for compound confirmation

### With CDSL Dictionary:
- Query components in SLP1: `kSetra` → CDSL lookup
- Use existing CDSL handler integration

## 6. Success Criteria

### Minimal Viable Product (Days 1-3):
- [ ] Tokenize Gītā 1.1 into 4 tokens
- [ ] Split hyphenated compounds into components
- [ ] Normalize all tokens to Velthuis format
- [ ] Generate correct dictionary queries

### Full Implementation (Days 4-5):
- [ ] CLI command functional with JSON output
- [ ] Integration tests with Heritage Platform
- [ ] Performance: < 50ms for 10-word passage
- [ ] Comprehensive test suite passing

## 7. Immediate Action Items

1. **Create directory structure**:
   ```
   mkdir -p src/langnet/tokenization
   mkdir -p src/langnet/compounds
   mkdir -p tests/tokenization
   ```

2. **Start with data models** (`models.py`)
3. **Implement basic tokenizer** (`sanskrit.py`)
4. **Add compound splitter** (`splitter.py`)
5. **Extend normalizer** with batch methods
6. **Create service orchestrator**
7. **Add CLI integration**

## 8. Testing Strategy

### Unit Tests:
```python
# tests/tokenization/test_sanskrit_tokenizer.py
def test_hyphenated_compound_splitting():
    splitter = CompoundSplitter()
    components = splitter.split_hyphenated("dharma-kṣhetre")
    assert components == ["dharma", "kṣhetre"]
    
def test_normalization_pipeline():
    normalizer = SanskritNormalizer()
    token = Token(surface_form="dhṛitarāśhtra", position=0)
    normalized = normalizer.normalize_token(token)
    assert normalized.normalized_form == "dhRitarASTra"
```

### Integration Test:
```python
def test_full_pipeline_gita_1_1():
    service = TokenAnalysisService()
    result = service.analyze_passage(
        "dhṛitarāśhtra uvācha dharma-kṣhetre kuru-kṣhetre"
    )
    assert len(result.tokens) == 4
    assert result.tokens[2].is_compound == True
```

## 9. Next Steps After MVP

1. **Sandhi-aware tokenization** (Phase 2)
2. **Enclitic detection** (ca, vā, eva)
3. **Educational explanations** for compounds
4. **Batch processing** for longer texts
5. **Caching** for performance

---

**Implementation Team**: @coder @artisan  
**Start Date**: 2026-04-12  
**Target Completion**: 2026-04-17