# Similarity Scoring Algorithm Specification

**Date**: 2026-02-15  
**Status**: ⏳ PLANNING (Not Started)  
**Priority**: MEDIUM  
**Area**: infra/semantic-reduction  
**Related**: `semantic-reduction-roadmap.md` Phase 2

## Overview

This document specifies the similarity scoring algorithm for comparing Witness Sense Units (WSUs). This is **Phase 2** of the semantic reduction pipeline, following WSU extraction.

Based on `classifier-and-reducer.md` Section 5: "Similarity Graph Construction"

## Algorithm Requirements

### **Design Goals**
1. **Deterministic**: Same inputs → same similarity scores
2. **Fast**: < 10ms per WSU pair comparison
3. **Interpretable**: Scores should make semantic sense
4. **Configurable**: Mode-dependent thresholds
5. **Multilingual**: Works for Latin, Greek, Sanskrit

### **Inputs**
```python
class SimilarityInput:
    wsu1: WitnessSenseUnit
    wsu2: WitnessSenseUnit
    mode: Mode = Mode.OPEN  # OPEN or SKEPTIC
```

### **Output**
```python
class SimilarityOutput:
    score: float  # 0.0 - 1.0
    components: Dict[str, float]  # Breakdown of score components
    explanation: Optional[str]  # Human-readable explanation
```

## Similarity Signals

From design doc Section 5.2:

### **1. Token Overlap (Primary Signal)**
Compare normalized gloss tokens using Jaccard similarity.

```python
def token_overlap_similarity(gloss1: str, gloss2: str) -> float:
    """
    Jaccard similarity between token sets.
    
    Jaccard(A, B) = |A ∩ B| / |A ∪ B|
    
    Where tokens are:
    - Lowercased
    - Stop words removed (optional)
    - Stemmed (optional, language-dependent)
    """
```

**Tokenization Rules**:
- Split on whitespace and punctuation
- Remove empty tokens
- Language-specific tokenization for Sanskrit compounds

**Example**:
```
gloss1: "auspicious; benign; favorable"
gloss2: "auspicious; lucky; propitious"

Tokens1: {"auspicious", "benign", "favorable"}
Tokens2: {"auspicious", "lucky", "propitious"}
Intersection: {"auspicious"}
Union: {"auspicious", "benign", "favorable", "lucky", "propitious"}
Jaccard: 1/5 = 0.20
```

### **2. Shared Metadata Signals**
Compare domain and register metadata.

```python
def metadata_similarity(metadata1: Dict, metadata2: Dict) -> float:
    """
    Compare domain and register metadata.
    
    Scoring:
    - Shared domain: +0.2 per matching domain
    - Shared register: +0.15 per matching register
    - Max metadata contribution: 0.4
    """
```

**Metadata Structure**:
```json
{
  "domains": ["religion", "mythology"],
  "register": ["vedic", "epic"]
}
```

### **3. Entity-Type Indicators**
Detect and match entity types in glosses.

```python
def entity_type_similarity(gloss1: str, gloss2: str) -> float:
    """
    Detect entity types and compare.
    
    Entity types:
    - PERSON/GOD: "Zeus", "Agni", "god", "deity"
    - PLACE: "city", "river", "mountain"
    - ABSTRACT: "virtue", "law", "concept"
    - OBJECT: "sword", "shield", "vessel"
    
    Scoring:
    - Same entity type: +0.3
    - Different entity type: -0.1 penalty
    """
```

**Entity Detection Rules**:
- Capitalized proper nouns
- Known deity names (from lexicon)
- Semantic markers: "god of", "person who", "place where"

### **4. Primary Lexicon Agreement Boost**
Boost similarity if both WSUs are from primary lexica.

```python
def primary_lexicon_boost(source1: Source, source2: Source) -> float:
    """
    Boost similarity for primary lexicon agreement.
    
    Primary lexica:
    - SOURCE_MW (Sanskrit)
    - SOURCE_DIOGENES (Greek/Latin - LSJ, Lewis & Short)
    
    Scoring:
    - Both primary: +0.25 boost
    - One primary, one secondary: +0.1 boost
    - Both secondary: no boost
    """
```

**Source Priority**:
1. **Primary**: MW, Diogenes (LSJ/Lewis & Short)
2. **Secondary**: AP90, Heritage, Whitakers
3. **Tertiary**: CLTK, supplemental sources

### **5. Negation Penalty**
Penalize similarity when glosses contain negations.

```python
def negation_penalty(gloss1: str, gloss2: str) -> float:
    """
    Detect negation markers and apply penalty.
    
    Negation markers:
    - "not", "non-", "un-", "in-", "im-"
    - "without", "lack of", "absence of"
    
    Scoring:
    - One gloss negated, other not: -0.4 penalty
    - Both negated: no penalty (they might be similar)
    """
```

## Combined Similarity Formula

### **Weighted Combination**
```python
def calculate_similarity(wsu1, wsu2, mode) -> float:
    """
    Calculate final similarity score 0.0-1.0.
    
    Formula:
    score = (
        w1 * token_similarity +
        w2 * metadata_similarity + 
        w3 * entity_similarity +
        w4 * primary_boost +
        w5 * negation_penalty
    )
    
    Clamped to [0.0, 1.0]
    """
```

### **Mode-Dependent Weights**

**OPEN Mode** (learner-friendly consolidation):
```python
OPEN_WEIGHTS = {
    "token": 0.60,      # Emphasize gloss similarity
    "metadata": 0.20,   # Consider domains/register
    "entity": 0.10,     # Light entity matching
    "primary_boost": 0.10,  # Minor lexicon preference
    "negation_penalty": -0.40  # Strong negation avoidance
}
```

**SKEPTIC Mode** (evidence-first grouping):
```python
SKEPTIC_WEIGHTS = {
    "token": 0.40,      # Less weight on gloss alone
    "metadata": 0.30,   # More weight on metadata
    "entity": 0.20,     # Strong entity matching
    "primary_boost": 0.20,  # Strong lexicon preference  
    "negation_penalty": -0.60  # Very strong negation avoidance
}
```

## Implementation Details

### **Tokenization Module**
```python
class GlossTokenizer:
    """Tokenize gloss text for comparison."""
    
    def __init__(self, language: str):
        self.language = language
        self.stop_words = self.load_stop_words(language)
        
    def tokenize(self, gloss: str) -> Set[str]:
        """
        Tokenize gloss into comparison tokens.
        
        Steps:
        1. Normalize Unicode
        2. Lowercase
        3. Split on whitespace/punctuation
        4. Remove stop words
        5. Apply language-specific stemming
        6. Remove duplicates
        """
```

### **Similarity Calculator**
```python
class SimilarityCalculator:
    """Calculate similarity between WSUs."""
    
    def __init__(self, mode: Mode = Mode.OPEN):
        self.mode = mode
        self.weights = self.get_weights_for_mode(mode)
        
    def calculate(self, wsu1: WitnessSenseUnit, wsu2: WitnessSenseUnit) -> SimilarityOutput:
        """Calculate comprehensive similarity."""
        
        # Calculate component scores
        token_score = self.token_similarity(wsu1.gloss_raw, wsu2.gloss_raw)
        metadata_score = self.metadata_similarity(wsu1.metadata, wsu2.metadata)
        entity_score = self.entity_similarity(wsu1.gloss_raw, wsu2.gloss_raw)
        primary_boost = self.primary_lexicon_boost(wsu1.source, wsu2.source)
        negation_penalty = self.negation_penalty(wsu1.gloss_raw, wsu2.gloss_raw)
        
        # Combine with weights
        combined = (
            self.weights["token"] * token_score +
            self.weights["metadata"] * metadata_score +
            self.weights["entity"] * entity_score +
            self.weights["primary_boost"] * primary_boost +
            negation_penalty  # Already weighted in calculation
        )
        
        # Clamp to [0, 1]
        final_score = max(0.0, min(1.0, combined))
        
        return SimilarityOutput(
            score=final_score,
            components={
                "token": token_score,
                "metadata": metadata_score,
                "entity": entity_score,
                "primary_boost": primary_boost,
                "negation_penalty": negation_penalty
            }
        )
```

## Similarity Graph Construction

### **Graph Structure**
```python
class SimilarityGraph:
    """Pairwise similarity matrix for WSUs."""
    
    def __init__(self, wsu_list: List[WitnessSenseUnit]):
        self.wsu_list = wsu_list
        self.matrix = self.build_similarity_matrix()
        
    def build_similarity_matrix(self) -> np.ndarray:
        """
        Build N x N similarity matrix.
        
        Returns symmetric matrix where:
        matrix[i][j] = similarity(wsu_i, wsu_j)
        """
```

### **Optimization Strategies**

**Strategy 1: Full Matrix** (for small N)
- Calculate all N*(N-1)/2 pairs
- Simple but O(N²)
- Good for N < 100

**Strategy 2: Pruned Calculation** (for large N)
- Skip pairs with obviously different metadata
- Use locality-sensitive hashing
- Good for N > 100

**Strategy 3: Cached Calculation**
- Cache similarity scores by (source1, ref1, source2, ref2)
- Useful for repeated comparisons
- Requires stable WSU references

## Performance Requirements

### **Latency Targets**
- **Tokenization**: < 1ms per gloss
- **Pairwise similarity**: < 5ms per pair
- **Full graph (50 WSUs)**: < 500ms
- **Full graph (10 WSUs)**: < 50ms

### **Memory Targets**
- **Similarity matrix (100 WSUs)**: < 80KB (100x100 float32)
- **Token cache**: < 10MB for 10,000 glosses
- **Entity detection models**: < 5MB

## Testing Strategy

### **Unit Tests**
```python
def test_token_similarity():
    """Test Jaccard similarity calculations."""
    assert similarity("fire", "fire") == 1.0
    assert similarity("fire", "water") == 0.0
    assert similarity("auspicious favorable", "auspicious lucky") == 0.5

def test_metadata_similarity():
    """Test domain/register matching."""
    metadata1 = {"domains": ["religion"], "register": ["vedic"]}
    metadata2 = {"domains": ["religion"], "register": ["classical"]}
    assert similarity(metadata1, metadata2) > 0.2  # Shared domain

def test_entity_detection():
    """Test entity type recognition."""
    assert get_entity_type("god Agni") == "PERSON/GOD"
    assert get_entity_type("river Ganges") == "PLACE"
    assert get_entity_type("moral law") == "ABSTRACT"
```

### **Integration Tests**
```python
def test_full_similarity_pipeline():
    """Test end-to-end similarity calculation."""
    wsu1 = WitnessSenseUnit(source=SOURCE_MW, sense_ref="mw:217497", 
                           gloss_raw="auspicious; benign; favorable")
    wsu2 = WitnessSenseUnit(source=SOURCE_MW, sense_ref="mw:217498",
                           gloss_raw="Agni, the god of fire")
    
    calculator = SimilarityCalculator(mode=Mode.OPEN)
    result = calculator.calculate(wsu1, wsu2)
    
    assert 0.0 <= result.score <= 1.0
    assert "token" in result.components
    assert "metadata" in result.components
```

### **Benchmark Tests**
```python
def benchmark_similarity_calculation():
    """Performance benchmark."""
    # Generate 100 random WSUs
    # Time full matrix calculation
    # Assert < 500ms
```

## Edge Cases & Special Handling

### **Multi-Word Glosses**
```python
# Example: "auspicious; benign; favorable"
# Should be treated as single gloss with multiple alternatives
# Tokenization: union of all alternative tokens
```

### **Language-Specific Handling**
```python
# Sanskrit: Compound word splitting
# Greek: Diacritic normalization
# Latin: Abbreviation expansion
```

### **Empty/Missing Data**
```python
# Handle missing metadata gracefully
# Empty gloss should have 0 similarity with everything
# Single-word glosses need special handling
```

### **Very Similar but Different**
```python
# "fire (element)" vs "fire (destructive force)"
# Should have high token similarity but entity difference
# Result: moderate similarity (0.6-0.7)
```

## Configuration & Tuning

### **Configurable Parameters**
```yaml
similarity:
  mode_weights:
    open:
      token: 0.60
      metadata: 0.20
      entity: 0.10
      primary_boost: 0.10
    skeptic:
      token: 0.40
      metadata: 0.30
      entity: 0.20
      primary_boost: 0.20
  
  thresholds:
    clustering_open: 0.62
    clustering_skeptic: 0.78
    constant_assignment: 0.85
  
  tokenization:
    remove_stop_words: true
    stem_words: false
    language_specific_rules: true
```

### **Tuning Process**
1. **Collect gold standard**: Human-labeled similar/dissimilar pairs
2. **Calculate metrics**: Precision, recall, F1-score
3. **Adjust weights**: Optimize for target F1-score
4. **Validate**: Test on held-out data

## Questions & Decisions Needed

### **Technical Decisions**
1. **Tokenization library**: Use NLTK/spaCy or custom implementation?
2. **Stemming/lemmatization**: Needed for accuracy, but adds complexity
3. **Stop word list**: Language-specific or universal?
4. **Entity detection**: Rule-based or ML-based?

### **Algorithm Decisions**
1. **Jaccard vs Cosine similarity**: Which works better for short texts?
2. **Weight tuning**: Initial weights vs learned weights?
3. **Negation handling**: Simple rule-based or semantic analysis?
4. **Metadata extraction**: How deep to extract from raw glosses?

### **Performance Decisions**
1. **Caching strategy**: Cache at token level or similarity level?
2. **Parallelization**: Calculate pairs in parallel?
3. **Approximation**: Accept approximate similarity for speed?

## Success Criteria

### **Phase 2 Complete**
- [ ] Tokenization working for all languages
- [ ] All 5 similarity signals implemented
- [ ] Mode-dependent weighting operational
- [ ] Performance: < 50ms for 10 WSU graph
- [ ] Deterministic: Same inputs → same scores
- [ ] Test suite: 100+ test cases passing
- [ ] Documentation: Algorithm explained in code

---

*This specification will guide Phase 2 implementation. Start with token overlap similarity, then add other signals incrementally.*