# Sanskrit Tokenization with Compound Handling Implementation Plan
## Focus: Properly tokenizing "dhṛitarāśhtra uvācha dharma-kṣhetre kuru-kṣhetre"

**Feature Area**: Sanskrit Infrastructure  
**Status**: ⏳ PLANNING  
**Priority**: High  
**Estimated Effort**: 2-3 weeks  
**AI Personas**: @architect @coder @artisan  
**Target**: Bhagavad Gītā 1.1 tokenization for dictionary lookup

## 1. Problem Statement

Current Sanskrit processing in LangNet lacks proper tokenization for passage analysis. When students input "dhṛitarāśhtra uvācha dharma-kṣhetre kuru-kṣhetre", the system needs to:

1. **Split the passage into individual tokens**: `["dhṛitarāśhtra", "uvācha", "dharma-kṣhetre", "kuru-kṣhetre"]`
2. **Handle compound words**: Split hyphenated compounds into components for dictionary lookup
3. **Normalize encoding**: Convert various encodings (IAST, Devanagari, Velthuis, SLP1) to consistent forms
4. **Prepare for dictionary lookup**: Generate queries for Heritage Platform and CDSL dictionary
5. **Preserve context**: Maintain word order and sentence structure for educational analysis

**Current Limitations**:
- No passage-level tokenization for Sanskrit
- Hyphenated compounds not split into components
- No sandhi-aware tokenization
- No systematic handling of enclitics and particles

## 2. Example Analysis: Bhagavad Gītā 1.1

**Input**: `dhṛitarāśhtra uvācha dharma-kṣhetre kuru-kṣhetre`

**Expected Tokenization Pipeline**:
```
Input: "dhṛitarāśhtra uvācha dharma-kṣhetre kuru-kṣhetre"
↓ Encoding detection (IAST)
↓ Token splitting (whitespace + punctuation)
Tokens: ["dhṛitarāśhtra", "uvācha", "dharma-kṣhetre", "kuru-kṣhetre"]
↓ Compound detection (hyphenated terms)
Compounds: ["dharma-kṣhetre", "kuru-kṣhetre"]
↓ Compound splitting
Components: [("dharma", "kṣhetre"), ("kuru", "kṣhetre")]
↓ Normalization (to Velthuis for Heritage)
Normalized: ["dhRitarASTra", "uvAca", "dharmakSetre", "kurukSetre"]
↓ Dictionary query preparation
Queries: ["dhRitarASTra", "uvAca", "dharma", "kSetra", "kuru", "kSetra"]
```

**Final Output Structure**:
```json
{
  "original_text": "dhṛitarāśhtra uvācha dharma-kṣhetre kuru-kṣhetre",
  "language": "san",
  "tokens": [
    {
      "surface_form": "dhṛitarāśhtra",
      "normalized_form": "dhRitarASTra",
      "position": 0,
      "is_compound": false,
      "components": null
    },
    {
      "surface_form": "uvācha", 
      "normalized_form": "uvAca",
      "position": 1,
      "is_compound": false,
      "components": null
    },
    {
      "surface_form": "dharma-kṣhetre",
      "normalized_form": "dharmakSetre",
      "position": 2,
      "is_compound": true,
      "compound_type": "tatpuruṣa",
      "components": [
        {"surface": "dharma", "normalized": "dharma", "role": "initial"},
        {"surface": "kṣhetre", "normalized": "kSetra", "role": "final"}
      ]
    },
    {
      "surface_form": "kuru-kṣhetre",
      "normalized_form": "kurukSetre", 
      "position": 3,
      "is_compound": true,
      "compound_type": "tatpuruṣa",
      "components": [
        {"surface": "kuru", "normalized": "kuru", "role": "initial"},
        {"surface": "kṣhetre", "normalized": "kSetra", "role": "final"}
      ]
    }
  ]
}
```

## 3. Core Components Required

### 3.1 SanskritTokenizer Module
**Location**: `src/langnet/tokenization/sanskrit.py`

**Responsibilities**:
- Split text into tokens (whitespace, punctuation)
- Detect and handle compounds (hyphenated, sandhi-joined)
- Identify enclitics (ca, vā, etc.)
- Handle punctuation and sentence boundaries

**Key Methods**:
```python
class SanskritTokenizer:
    def tokenize(self, text: str) -> list[Token]:
        """Split Sanskrit text into tokens."""
    
    def split_compounds(self, token: Token) -> list[Token]:
        """Split hyphenated or sandhi-joined compounds."""
    
    def normalize_token(self, token: Token) -> Token:
        """Normalize token encoding and prepare for lookup."""
```

### 3.2 CompoundSplitter Service
**Location**: `src/langnet/compounds/splitter.py`

**Responsibilities**:
- Identify compound boundaries
- Split hyphenated compounds (`dharma-kṣhetre` → `dharma`, `kṣhetre`)
- Detect potential sandhi-joined compounds (future enhancement)
- Assign compound roles (initial, medial, final)

**Key Methods**:
```python
class CompoundSplitter:
    def split_hyphenated(self, text: str) -> list[str]:
        """Split hyphenated Sanskrit compounds."""
    
    def identify_compound_type(self, components: list[str]) -> str:
        """Identify compound type: tatpuruṣa, bahuvrīhi, dvandva, etc."""
```

### 3.3 Enhanced SanskritNormalizer
**Location**: `src/langnet/normalizer/sanskrit.py` (extend existing)

**New Responsibilities**:
- Batch normalization of token lists
- Compound-aware normalization (join components for Heritage queries)
- Encoding consistency across tokens

**Key Enhancements**:
```python
class SanskritNormalizer(LanguageNormalizer):
    def normalize_tokens(self, tokens: list[str]) -> list[NormalizedToken]:
        """Normalize a list of tokens efficiently."""
    
    def prepare_compound_query(self, components: list[str]) -> str:
        """Join compound components for Heritage Platform query."""
```

### 3.4 Token Analysis Data Model
**Location**: `src/langnet/tokenization/models.py`

**Data Structures**:
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
    lemma: Optional[str] = None
    role: str  # "initial", "medial", "final"
    
@dataclass
class TokenizedPassage:
    original_text: str
    language: str
    tokens: list[Token]
    metadata: dict
```

## 4. Implementation Phases

### Phase 1: Foundation Tokenization (Week 1)
**Goal**: Basic text splitting and compound detection

**Tasks**:
1. Create `SanskritTokenizer` with whitespace/punctuation splitting
2. Implement hyphenated compound detection
3. Add basic encoding detection per token
4. Create `Token` data model
5. Write tests for Gītā 1.1 example

**Deliverables**:
- `src/langnet/tokenization/sanskrit.py`
- `src/langnet/tokenization/models.py`
- Tests: `test_sanskrit_tokenization.py`

### Phase 2: Compound Handling & Normalization (Week 1-2)
**Goal**: Proper compound splitting and normalization

**Tasks**:
1. Implement `CompoundSplitter` for hyphenated compounds
2. Enhance `SanskritNormalizer` to handle token lists
3. Add compound query preparation (join components for Heritage)
4. Implement batch normalization for efficiency
5. Add compound type detection (basic: tatpuruṣa vs. other)

**Deliverables**:
- `src/langnet/compounds/splitter.py`
- Enhanced `src/langnet/normalizer/sanskrit.py`
- Tests for compound splitting and normalization

### Phase 3: Integration with Existing Pipeline (Week 2)
**Goal**: Connect tokenization to Heritage Platform and CDSL

**Tasks**:
1. Create `TokenAnalysisService` orchestrating tokenization + lookup
2. Integrate with `HeritageHandler` for morphology queries
3. Integrate with `CDSLHandler` for dictionary lookups
4. Add caching for tokenization results
5. Create CLI command for testing

**Deliverables**:
- `src/langnet/tokenization/service.py`
- CLI command: `langnet-cli tokenize-san "dhṛitarāśhtra uvācha..."`
- Integration tests with Heritage/CDSL

### Phase 4: Advanced Features (Week 3)
**Goal**: Sandhi-aware tokenization and educational enhancements

**Tasks**:
1. Implement basic sandhi splitting (external-vowel sandhi)
2. Add enclitic detection (ca, vā, eva, etc.)
3. Create educational explanations for compounds
4. Add difficulty scoring for tokens
5. Performance optimization for long texts

**Deliverables**:
- Sandhi splitting module
- Educational annotation system
- Performance benchmarks

## 5. Technical Specifications

### 5.1 Tokenization Rules

**Basic Splitting**:
- Split on whitespace (`\s+`)
- Split on punctuation (`,;:.!?`)
- Preserve hyphens within compounds
- Handle common Sanskrit punctuation (`॥`, `।`)

**Compound Detection**:
- Hyphenated terms: `dharma-kṣhetre`
- Potential sandhi joins: `dharmakṣhetre` (future)
- Compound markers in Heritage analysis (`iic.`, `ifc.`)

**Encoding Support**:
- IAST: `dhṛitarāśhtra`
- Devanagari: `धृतराष्ट्र`
- Velthuis: `dhRitarASTra` (Heritage format)
- SLP1: `DftarAzwa` (CDSL format)

### 5.2 Normalization Pipeline

```
Raw Token → Encoding Detection → Normalize to Velthuis → 
↓ (for compounds)
Split Components → Normalize Each → Join for Heritage Query
```

**Example**:
- Input: `dharma-kṣhetre` (IAST)
- Detect: IAST encoding
- Normalize: `dharma-kSetre` (Velthuis)
- Split: `["dharma", "kSetre"]`
- Heritage Query: `dharmakSetre`
- Component Queries: `["dharma", "kSetra"]`

### 5.3 Integration Points

**With Heritage Platform**:
- Use joined form for morphology analysis: `dharmakSetre`
- Parse Heritage response for compound confirmation
- Extract component analysis from color coding

**With CDSL Dictionary**:
- Query each component separately: `dharma`, `kSetra`
- Merge senses for compound understanding
- Use SLP1 encoding for CDSL queries

## 6. API Design

### 6.1 Python API
```python
from langnet.tokenization import SanskritTokenizer

tokenizer = SanskritTokenizer()
result = tokenizer.analyze_passage(
    "dhṛitarāśhtra uvācha dharma-kṣhetre kuru-kṣhetre",
    detail_level="full"
)

# Returns TokenizedPassage with tokens, compounds, normalization
```

### 6.2 CLI Command
```bash
# Basic tokenization
langnet-cli tokenize-san "dhṛitarāśhtra uvācha dharma-kṣhetre kuru-kṣhetre"

# With compound analysis
langnet-cli tokenize-san --analyze-compounds "dharma-kṣhetre"

# With dictionary lookup
langnet-cli tokenize-san --lookup "dhṛitarāśhtra uvācha..."

# Output formats
langnet-cli tokenize-san --output json "dhṛitarāśhtra uvācha..."
langnet-cli tokenize-san --output text "dhṛitarāśhtra uvācha..."
```

### 6.3 HTTP API (Future)
```python
POST /api/v1/tokenize/sanskrit
{
  "text": "dhṛitarāśhtra uvācha dharma-kṣhetre kuru-kṣhetre",
  "options": {
    "split_compounds": true,
    "normalize": true,
    "lookup_dictionary": false
  }
}
```

## 7. Testing Strategy

### 7.1 Test Corpus
- **Bhagavad Gītā 1.1-10**: Various compounds and syntax
- **Rāmāyaṇa excerpts**: Longer sentences, proper nouns
- **Sanskrit textbook examples**: Pedagogical focus
- **Edge cases**: Single words, punctuation, mixed encoding

### 7.2 Validation Metrics
- **Token accuracy**: 95% correct token boundaries
- **Compound detection**: 90% of hyphenated compounds correctly split
- **Normalization**: 99% encoding conversion accuracy
- **Performance**: < 100ms for 50-word passage

### 7.3 Test Files
- `tests/tokenization/test_sanskrit_tokenizer.py`
- `tests/tokenization/test_compound_splitter.py`
- `tests/integration/test_tokenization_pipeline.py`
- Fixtures: `tests/fixtures/sanskrit_passages.json`

## 8. Dependencies & Integration

### 8.1 Existing Components to Use
1. **SanskritNormalizer** (`src/langnet/normalizer/sanskrit.py`)
   - Encoding detection
   - Velthuis conversion
   - Heritage query preparation

2. **HeritageHandler** (`src/langnet/execution/handlers/heritage.py`)
   - Morphology analysis
   - Compound confirmation via color coding
   - Dictionary URL extraction

3. **CDSLHandler** (`src/langnet/execution/handlers/cdsl.py`)
   - Dictionary sense lookup
   - SLP1 encoding support

### 8.2 New Dependencies
- None beyond existing indic-transliteration

## 9. Success Criteria

### Phase 1 Complete
- [ ] Tokenize Gītā 1.1 into correct word list
- [ ] Detect hyphenated compounds
- [ ] Basic normalization to Velthuis
- [ ] CLI command functional

### Phase 2 Complete  
- [ ] Split compounds into components
- [ ] Batch normalization of token lists
- [ ] Compound type detection (basic)
- [ ] Integration tests passing

### Phase 3 Complete
- [ ] Heritage Platform queries for compounds
- [ ] CDSL lookup for components
- [ ] Caching implementation
- [ ] Full pipeline working

### Phase 4 Complete
- [ ] Basic sandhi splitting
- [ ] Enclitic detection
- [ ] Educational explanations
- [ ] Performance optimization

## 10. Risks & Mitigations

### 10.1 Heritage Platform Reliability
- **Risk**: Heritage may not analyze all compound forms
- **Mitigation**: Fallback to heuristic analysis, use CDSL data

### 10.2 Encoding Complexity
- **Risk**: Mixed or incorrect encoding detection
- **Mitigation**: Conservative detection with user override option

### 10.3 Performance with Long Texts
- **Risk**: Tokenizing long passages may be slow
- **Mitigation**: Implement streaming tokenization, incremental processing

### 10.4 Sandhi Ambiguity
- **Risk**: Sandhi splitting has multiple valid solutions
- **Mitigation**: Present alternatives with confidence scores

## 11. Next Steps

### Immediate (Start Now)
1. **@architect**: Review and refine technical design
2. **@coder**: Create tokenization module structure
3. **@artisan**: Establish code patterns and tests

### Week 1
1. Implement basic tokenizer with compound detection
2. Write comprehensive tests for Gītā 1.1
3. Get feedback from Sanskrit scholars

### Week 2
1. Implement compound splitting and normalization
2. Integrate with Heritage and CDSL
3. Performance testing and optimization

### Week 3
1. Add advanced features (sandhi, enclitics)
2. Create educational explanations
3. Final integration and documentation

## 12. References

### Technical Documentation
- [Sanskrit Normalizer](/home/nixos/langnet-tools/langnet-cli/src/langnet/normalizer/sanskrit.py)
- [Heritage Handler](/home/nixos/langnet-tools/langnet-cli/src/langnet/execution/handlers/heritage.py)
- [CDSL Handler](/home/nixos/langnet-tools/langnet-cli/src/langnet/execution/handlers/cdsl.py)
- [Compound Term Lookup Plan](/home/nixos/langnet-tools/langnet-cli/docs/plans/active/pedagogy/compound-term-lookup.md)

### Sanskrit Resources
- Heritage Platform: https://sanskrit.inria.fr/
- Sanskrit compound grammar references
- Bhagavad Gītā critical edition

### Educational Context
- [LangNet Educational Philosophy](/home/nixos/langnet-tools/langnet-cli/docs/GOALS.md)
- [Foster Grammar Framework](/home/nixos/langnet-tools/langnet-cli/docs/technical/design/foster_grammar.md)

---

**Maintained by**: @architect @coder @artisan  
**Created**: 2026-04-12  
**Target Completion**: 2026-05-03