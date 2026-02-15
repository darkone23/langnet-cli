# Semantic Reduction: Current Architecture Gap Analysis

**Date**: 2026-02-15  
**Status**: 🔍 ANALYSIS (In Progress)  
**Priority**: HIGH  
**Area**: infra/semantic-reduction

## Executive Summary

The semantic reduction pipeline design assumes a data structure that **does not match** the current implementation. We need to address these gaps before proceeding with implementation.

## Current Architecture vs Design Assumptions

### **Design Assumption (03-classifier-and-reducer.md)**
```json
{
  "source": "MW",
  "sense_ref": "217497",
  "gloss_raw": "auspicious; benign; favorable",
  "metadata": {
    "domain": [],
    "register": []
  }
}
```

### **Current Reality (src/langnet/schema.py)**
```python
@dataclass
class DictionaryDefinition:
    definition: str  # The dictionary definition text
    pos: str  # Part of speech
    gender: str | None = None
    etymology: str | None = None
    examples: list[str] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)
    metadata: JSONMapping = field(default_factory=dict)  # Backend-specific raw data
```

## Critical Gaps Identified

### **Gap 1: Missing Source References at Definition Level**
- **Design**: Each sense has `sense_ref` (e.g., "mw:217497")
- **Current**: `DictionaryDefinition` has no source reference field
- **Impact**: Cannot trace definitions back to original source

### **Gap 2: Sense Lines vs Definitions Mismatch**
- **CDSL Adapter**: Stores `sense_lines` in metadata, not as `DictionaryDefinition` objects
- **Example**: `"217497: auspicious; benign; favorable"` is a string in metadata
- **Impact**: Need to parse sense lines to create proper definitions

### **Gap 3: Granular Source Tracking**
- **Design**: Source tracking at sense level (`source: "MW"`)
- **Current**: Source tracking at entry level (`DictionaryEntry.source`)
- **Impact**: Cannot distinguish MW vs AP90 vs other sources within same entry

### **Gap 4: Metadata Structure**
- **Design**: Structured `metadata` with `domains` and `register` arrays
- **Current**: Flat `JSONMapping` without schema
- **Impact**: Cannot extract domains/register for similarity scoring

### **Gap 5: Citation vs Sense Separation**
- **Design**: Citations are separate from sense text
- **Current**: Citations embedded in definition text or in separate lists
- **Impact**: Need to extract citations from sense text

## Root Cause Analysis

### **Architecture Evolution**
The current schema evolved from a **backend aggregation** model rather than a **semantic reduction** model:

1. **Phase 1**: Aggregate outputs from different backends
2. **Phase 2**: Present aggregated results  
3. **Phase 3 (Current)**: Want semantic reduction but schema doesn't support it

### **Adapter Inconsistency**
Each adapter implements the schema differently:

| Adapter | Definition Storage | Source Tracking |
|---------|-------------------|-----------------|
| **CDSL** | `sense_lines` in metadata | Entry-level only |
| **Diogenes** | `dictionary_blocks` | Block-level with citations |
| **Whitakers** | `definitions` list | Entry-level |
| **Heritage** | Morphology only | Entry-level |

## Required Schema Changes

### **Minimum Viable Changes**
```python
@dataclass
class DictionaryDefinition:
    definition: str
    pos: str
    gender: str | None = None
    etymology: str | None = None
    examples: list[str] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)
    metadata: JSONMapping = field(default_factory=dict)
    
    # NEW FIELDS FOR SEMANTIC REDUCTION
    source_ref: str | None = None  # "mw:217497", "diogenes:lsj:1234"
    domains: list[str] = field(default_factory=list)  # ["religion", "mythology"]
    register: list[str] = field(default_factory=list)  # ["vedic", "epic"]
    confidence: float | None = None  # For stochastic sources
```

### **Alternative: WSU Layer on Top**
Instead of modifying `DictionaryDefinition`, create a parallel WSU structure:

```python
@dataclass
class WitnessSenseUnit:
    """Parallel structure for semantic reduction."""
    definition_id: str  # Reference to original DictionaryDefinition
    source: Source  # Enum from semantic structs
    sense_ref: str  # "mw:217497"
    gloss_raw: str  # Copy of definition text
    domains: list[str]
    register: list[str]
    
    # Link back to original
    original_definition: DictionaryDefinition
```

## Migration Strategies

### **Option A: Schema Evolution (Recommended)**
1. Add new fields to `DictionaryDefinition` (backward compatible)
2. Update adapters to populate new fields gradually
3. Build semantic reduction on enhanced schema

**Pros**: Clean, maintains single source of truth  
**Cons**: Requires updating all adapters

### **Option B: Parallel WSU Extraction**
1. Keep current schema unchanged
2. Create WSU extraction from existing data
3. Build semantic reduction on WSU layer only

**Pros**: No adapter changes needed  
**Cons**: Duplicate data, synchronization issues

### **Option C: Hybrid Approach**
1. Add minimal source_ref field to schema
2. Extract WSUs with source_ref when available
3. Fall back to parsing when not available
4. Gradually enhance adapters

**Pros**: Incremental, practical  
**Cons**: Inconsistent data quality during transition

## Recommended Path Forward

### **Phase 0: Schema Enhancement (Immediate)**
1. Add `source_ref: str | None` to `DictionaryDefinition`
2. Add `domains: list[str]` and `register: list[str]` 
3. Update CDSL adapter to populate these fields
4. Test with Sanskrit data

### **Phase 1: WSU Extraction Foundation**
1. Create `WSUExtractor` that works with enhanced schema
2. Handle both new (with source_ref) and old data
3. Build normalization pipeline
4. Create test suite

### **Phase 2: Adapter Gradual Enhancement**
1. Update Diogenes adapter to populate source_ref
2. Update Whitakers adapter
3. Update Heritage adapter
4. Validate across all languages

### **Phase 3: Semantic Reduction Pipeline**
1. Build similarity scoring
2. Implement clustering
3. Add constant registry
4. Integrate with semantic converter

## Impact Assessment

### **Breaking Changes**
- Adding fields to `DictionaryDefinition`: **Non-breaking** (optional fields)
- Changing adapter outputs: **Non-breaking** (additional data only)
- API response format: **Non-breaking** (new format optional)

### **Performance Impact**
- Additional fields: Minimal memory increase
- WSU extraction: CPU overhead for parsing
- Similarity scoring: Most significant cost

### **Testing Impact**
- Need to test both old and new data paths
- Golden snapshot updates required
- Adapter regression testing needed

## Success Criteria for Gap Resolution

### **Schema Enhancement Complete**
- [ ] `DictionaryDefinition` has source_ref field
- [ ] CDSL adapter populates source_ref from sense_lines
- [ ] Sanskrit test data shows MW IDs in responses
- [ ] Backward compatibility maintained

### **WSU Extraction Working**
- [ ] WSUs extracted for CDSL entries with source_ref
- [ ] Fallback extraction for entries without source_ref
- [ ] No data loss in extraction
- [ ] Performance acceptable (< 20ms per entry)

### **Adapters Updated**
- [ ] CDSL: source_ref from sense_lines
- [ ] Diogenes: source_ref from dictionary blocks
- [ ] Whitakers: source_ref generated from output
- [ ] Heritage: source_ref for morphology analyses

## Questions Requiring Answers

### **Technical Questions**
1. Should `source_ref` be a simple string or structured object?
2. How to handle composite sources? (e.g., "MW via CDSL")
3. What format for Diogenes references? "diogenes:lsj:1234" vs "lsj:1234"
4. How to extract domains/register from raw definition text?

### **Architecture Questions**
1. Store domains/register in schema or extract on demand?
2. How to handle confidence scores from stochastic sources?
3. Should WSU extraction be lazy or eager?
4. Cache WSUs or regenerate each query?

### **Migration Questions**
1. Timeline for adapter updates?
2. How to handle mixed data during transition?
3. Fallback strategies for missing data?
4. Testing strategy for partial implementations?

## Next Immediate Actions

### **Action 1: Schema Update**
Update `src/langnet/schema.py` with new fields:
```python
source_ref: str | None = None
domains: list[str] = field(default_factory=list)
register: list[str] = field(default_factory=list)
confidence: float | None = None
```

### **Action 2: CDSL Adapter Enhancement**
Modify CDSL adapter to parse `sense_lines` into proper `DictionaryDefinition` objects with `source_ref`.

### **Action 3: Test Infrastructure**
Create tests for new schema fields and WSU extraction.

### **Action 4: Documentation Update**
Update design docs to reflect actual implementation path.

## Conclusion

The semantic reduction design is sound but built on assumptions that don't match current reality. We need **schema evolution** before pipeline implementation. Start with minimal enhancements to `DictionaryDefinition`, update CDSL adapter first, then proceed with WSU extraction.

**Recommendation**: Begin with Phase 0 (Schema Enhancement) immediately, as it's non-breaking and enables all future work.

---

*This gap analysis should be reviewed before starting semantic reduction implementation. Update design documents based on these findings.*