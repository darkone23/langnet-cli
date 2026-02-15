# Semantic Reduction Pipeline Roadmap

**Date**: 2026-02-15  
**Status**: ⏳ PLANNING (Not Started)  
**Priority**: HIGH  
**Area**: infra/semantic-reduction

## Overview

This plan outlines the implementation of the semantic reduction pipeline as defined in:
1. `docs/technical/design/semantic-structs.md` - Schema definition
2. `docs/technical/design/witness-contracts.md` - Source contracts  
3. `docs/technical/design/classifier-and-reducer.md` - 4-stage pipeline design

**Current Status**: We have completed the **schema infrastructure** but need to build the actual **semantic reduction engine**.

## 📋 Current Implementation Status

### ✅ **Completed (Schema Layer)**
- [x] Semantic structs schema (proto v0.0.1)
- [x] API format parameter support (`?format=semantic`)
- [x] CLI semantic command (`langnet semantic`)
- [x] Basic converter (DictionaryEntry → QueryResponse)
- [x] Design documentation (01, 02, 03)

### ❌ **Missing (Reduction Engine)**
From the 4-stage pipeline design:
1. **Stage 1**: WSU extraction from adapters
2. **Stage 2**: Gloss normalization for comparison
3. **Stage 3**: Similarity graph construction  
4. **Stage 4**: Sense bucketing/clustering
5. **Stage 5**: Semantic constant assignment

## 🎯 Phase 1: WSU Extraction Layer

### **Goal**: Extract Witness Sense Units from existing adapters

### **Required Components**

#### 1.1 WSU Type Definition
```python
# New type in semantic structs schema
class WitnessSenseUnit:
    source: Source  # SOURCE_MW, SOURCE_DIOGENES, etc.
    sense_ref: str  # Stable locator (mw:217497, diogenes:lsj:1234)
    gloss_raw: str  # Raw gloss text from source
    metadata: Optional[Dict[str, List[str]]]  # domains, register, etc.
    ordering: Optional[int]  # Original ordering in source
```

#### 1.2 Adapter WSU Extraction
Update each adapter to provide WSU extraction methods:

| Adapter | WSU Extraction Strategy |
|---------|-------------------------|
| **CDSL** | Extract from `sense_lines` with MW IDs |
| **Diogenes** | Parse dictionary chunks with stable refs |
| **Whitakers** | Extract from parsed output lines |
| **Heritage** | Extract morphological feature sets |
| **CLTK** | Extract lemma suggestions with confidence |

#### 1.3 WSU Collection Interface
```python
def extract_wsu_from_dictionary_entry(entry: DictionaryEntry) -> List[WitnessSenseUnit]:
    """Extract WSUs from a DictionaryEntry based on source."""
```

### **Success Criteria**
- [ ] WSU type defined in schema
- [ ] All major adapters can extract WSUs
- [ ] Tests with 20+ entries per language
- [ ] Stable locators preserved for all WSUs

## 🎯 Phase 2: Normalization & Similarity Engine

### **Goal**: Compare and score similarity between WSUs

### **Required Components**

#### 2.1 Gloss Normalizer
```python
class GlossNormalizer:
    def normalize_for_comparison(gloss: str) -> str:
        """Apply allowed transformations only for comparison."""
        # 1. Lowercase
        # 2. Unicode normalization  
        # 3. Whitespace normalization
        # 4. Abbreviation expansion (via AbbrevMap)
        # 5. Tokenization (stop word removal optional)
```

**Allowed transformations** (per design doc):
- Lowercasing
- Unicode normalization  
- Whitespace normalization
- Abbreviation expansion
- Tokenization

**Prohibited**:
- Paraphrasing
- Translation  
- Semantic summarization

#### 2.2 Similarity Scoring
```python
class SimilarityScorer:
    def calculate_similarity(wsu1: WitnessSenseUnit, wsu2: WitnessSenseUnit) -> float:
        """Return similarity score 0.0-1.0 based on design signals."""
        
        # Signals (from design doc):
        # 1. Token overlap (Jaccard or cosine)
        # 2. Shared domain/register metadata
        # 3. Shared entity-type indicators  
        # 4. Primary lexicon agreement boost
        # 5. Negation penalty
```

#### 2.3 Similarity Graph Builder
```python
class SimilarityGraph:
    def build_graph(wsu_list: List[WitnessSenseUnit]) -> SimilarityMatrix:
        """Build pairwise similarity matrix."""
```

### **Success Criteria**
- [ ] Deterministic normalization
- [ ] Jaccard similarity implementation
- [ ] Metadata signal integration
- [ ] Graph construction for 50+ WSUs
- [ ] Performance: < 100ms for typical queries

## 🎯 Phase 3: Clustering Engine

### **Goal**: Cluster WSUs into semantic buckets

### **Required Components**

#### 3.1 Greedy Agglomerative Clustering
```python
class SenseBucketer:
    def cluster_wsu(
        wsu_list: List[WitnessSenseUnit], 
        mode: Mode = Mode.OPEN
    ) -> List[SenseBucket]:
        """Implement deterministic clustering per design doc."""
        
        # Algorithm (from design doc):
        # 1. Sort WSUs by source priority, stable sense_ref
        # 2. Start new bucket with next unused WSU
        # 3. Add WSUs with similarity ≥ threshold
        # 4. Repeat until exhausted
```

#### 3.2 Mode-Dependent Thresholds
```python
class ModeThresholds:
    OPEN = 0.62    # Lower threshold for learner-friendly consolidation
    SKEPTIC = 0.78 # Higher threshold for evidence-first grouping
```

#### 3.3 Bucket Structure
```python
class SenseBucket:
    sense_id: str           # Deterministic "B1", "B2", etc.
    semantic_constant: Optional[str]  # Assigned constant (or null)
    display_gloss: str      # Human-readable from centroid
    confidence: float       # 0.0-1.0 bucket coherence
    witnesses: List[WitnessSenseUnit]  # Original WSUs
    metadata: Dict[str, Any]  # Aggregated domains, register, etc.
```

### **Success Criteria**
- [ ] Deterministic clustering (same input → same buckets)
- [ ] Mode-specific threshold behavior
- [ ] No overlapping witnesses between buckets
- [ ] Confidence calculation implemented
- [ ] Bucket ranking by source count/importance

## 🎯 Phase 4: Semantic Constant Registry

### **Goal**: Assign stable semantic identifiers to buckets

### **Required Components**

#### 4.1 Constant Registry Storage
```python
class SemanticConstantRegistry:
    """Store and lookup semantic constants."""
    
    # Storage options:
    # Option A: JSON file in project data/
    # Option B: DuckDB table in langnet_data/
    # Option C: In-memory with persistence
    
    def find_matching_constant(bucket: SenseBucket) -> Optional[str]:
        """Find existing constant with similarity ≥ threshold."""
    
    def create_provisional_constant(bucket: SenseBucket) -> str:
        """Generate new constant ID from centroid gloss."""
        # Format: UPPERCASE_SNAKE_CASE
        # Example: "moral law; righteous conduct" → MORAL_LAW
```

#### 4.2 Constant Structure
```json
{
  "constant_id": "AUSPICIOUSNESS",
  "canonical_label": "auspiciousness", 
  "description": "state or quality of being favorable or blessed",
  "domains": ["religion"],
  "status": "provisional | curated",
  "created_from": ["mw:217497", "diogenes:lsj:1234"],
  "created_at": "2026-02-15T10:30:00Z",
  "curated_at": null
}
```

#### 4.3 Assignment Policy
```python
class ConstantAssigner:
    def assign_constants(buckets: List[SenseBucket]) -> List[SenseBucket]:
        """Apply constant assignment per design doc."""
        
        # Step 1: Attempt match against registry
        # Step 2: If no match, create provisional constant
        # Step 3: Add to registry with provisional status
```

### **Success Criteria**
- [ ] Registry storage implemented
- [ ] Match + introduce policy operational
- [ ] Deterministic constant ID generation
- [ ] Provisional vs curated status tracking
- [ ] Human review interface planned

## 🎯 Phase 5: Integration & Polish

### **Goal**: Integrate pipeline and add polish features

### **Required Components**

#### 5.1 Pipeline Integration
```python
class SemanticReducer:
    """Main pipeline orchestrator."""
    
    def reduce_to_semantic_structs(
        dictionary_entries: List[DictionaryEntry],
        mode: Mode = Mode.OPEN
    ) -> QueryResponse:
        """Full pipeline from raw entries to semantic structs."""
        
        # 1. Extract WSUs
        # 2. Normalize glosses  
        # 3. Build similarity graph
        # 4. Cluster into buckets
        # 5. Assign semantic constants
        # 6. Build QueryResponse
```

#### 5.2 Evidence Inspection
```python
# CLI command for debugging
@main.command(name="evidence")
def show_evidence():
    """Show WSU extraction and clustering details."""
```

#### 5.3 Mode Switching
```python
# API and CLI support
@app.get("/api/q")
async def query_word(request: Request, mode: str = "open"):
    """Support ?mode=open|skeptic parameter."""
```

### **Success Criteria**
- [ ] End-to-end pipeline integration
- [ ] Performance acceptable (< 500ms total)
- [ ] Evidence inspection CLI command
- [ ] Mode parameter fully supported
- [ ] Comprehensive test suite

## 📊 Testing Strategy

### **Golden Snapshot Tests**
```python
# Store expected outputs for key test cases
TEST_CASES = [
    ("san", "agni", "expected_buckets_agni.json"),
    ("lat", "lupus", "expected_buckets_lupus.json"),
    ("grc", "λόγος", "expected_buckets_logos.json"),
]
```

### **Determinism Tests**
```python
def test_deterministic_clustering():
    """Same input must produce same buckets across runs."""
```

### **Fuzz Testing**
```python
def test_encoding_variants():
    """Test IAST/SLP1/Devanagari variants produce same buckets."""
```

### **Performance Benchmarks**
```python
def benchmark_pipeline():
    """Measure latency for various input sizes."""
```

## 📅 Implementation Timeline

### **Week 1: Foundation**
- Define WSU types in schema
- Create WSU extraction from CDSL adapter
- Build basic test harness

### **Week 2: Comparison Engine**  
- Implement gloss normalizer
- Build Jaccard similarity scorer
- Create similarity graph builder

### **Week 3: Clustering Core**
- Implement greedy agglomerative clustering
- Add mode threshold support
- Build bucket confidence calculation

### **Week 4: Constants & Integration**
- Create semantic constant registry
- Implement assignment policy
- Integrate full pipeline

### **Week 5: Polish & Testing**
- Add evidence inspection CLI
- Implement mode switching
- Create golden snapshot tests
- Performance optimization

## 🚨 Risks & Mitigations

### **Risk 1: Performance degradation**
- **Mitigation**: Profile early, add caching, consider async processing
- **Fallback**: Keep legacy format as default for speed-critical use

### **Risk 2: Non-deterministic clustering**  
- **Mitigation**: Strict sorting rules, seed control, extensive testing
- **Fallback**: Document as non-deterministic feature

### **Risk 3: Constant registry bloat**
- **Mitigation**: Automatic merging of similar constants
- **Fallback**: Manual curation workflow

### **Risk 4: Adapter compatibility breaks**
- **Mitigation**: Keep WSU extraction optional, fallback to raw data
- **Fallback**: Progressive enhancement model

## 🤝 Handoff Notes

### **Start Here**
1. Review `src/langnet/adapters/` to understand current data structures
2. Examine `src/langnet/semantic_converter.py` for mapping patterns
3. Run `examples/semantic_structs_example.py` to see schema usage

### **Key Design Decisions Already Made**
- Confidence only on Sense (bucket coherence), not Lemma/Analysis
- Sources use Source enum, not freeform strings  
- Separate display vs canonical identifiers
- Semantic constants for stable concept identity

### **Questions to Answer During Implementation**
1. Should we cache similarity calculations?
2. How to handle multi-word glosses vs single-word?
3. What similarity threshold provides best UX?
4. How to present "provisional" constants to users?

## 📞 Contact & Context

**Based on**: `docs/technical/design/semantic-structs.md`, `witness-contracts.md`, `classifier-and-reducer.md`  
**Educational Focus**: Classical language education tool for Latin, Greek, Sanskrit  
**Session Goal**: Build semantic reduction pipeline to move from raw evidence to structured semantic output

**Next Session**: Start Phase 1 (WSU Extraction Layer)

---
*This roadmap will be moved to `docs/plans/active/` once implementation begins.*