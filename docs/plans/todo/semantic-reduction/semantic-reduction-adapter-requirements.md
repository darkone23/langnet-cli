# Adapter WSU Extraction Requirements

**Date**: 2026-02-15  
**Status**: ⏳ PLANNING (Not Started)  
**Priority**: HIGH  
**Area**: infra/semantic-reduction  
**Related**: `semantic-reduction-roadmap.md` Phase 1

## Overview

This document defines the Witness Sense Unit (WSU) extraction requirements for each existing adapter. WSU extraction is **Phase 1** of the semantic reduction pipeline.

## Current Adapter Status

### Existing Adapters
1. **CDSL** (`src/langnet/adapters/cdsl.py`) - Sanskrit lexicon (MW/AP90)
2. **Diogenes** (`src/langnet/adapters/diogenes.py`) - Greek/Latin lexica
3. **Whitakers** (`src/langnet/adapters/whitakers.py`) - Latin morphology
4. **Heritage** (`src/langnet/adapters/heritage.py`) - Sanskrit morphology
5. **CLTK** (`src/langnet/adapters/cltk.py`) - Supplemental morphology/lexicon

## WSU Definition Reference

From `classifier-and-reducer.md`:
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

**Key Requirements**:
- Each WSU must include a stable locator (`sense_ref`)
- Gloss text must remain traceable to source
- No paraphrasing at this stage
- All WSUs must be preserved even if later hidden in UI

## Adapter-Specific Requirements

### 1. CDSL Adapter (Sanskrit Lexicon)

**Current Output**: `DictionaryEntry` with `sense_lines`, `headword`, `morphology_info`

**WSU Extraction Strategy**:
```python
def extract_wsu_cdsl(entry: DictionaryEntry) -> List[WitnessSenseUnit]:
    """
    Extract WSUs from CDSL DictionaryEntry.
    
    For each sense_line with MW ID:
    - source: SOURCE_MW (or SOURCE_AP90)
    - sense_ref: "mw:<MW_ID>" or "ap90:<AP90_ID>"
    - gloss_raw: The sense text (preserve punctuation)
    - metadata: Extract from sense_line tags if available
    """
```

**Example CDSL Sense Line**:
```
sense_lines: [
  "217497: auspicious; benign; favorable",
  "217498: Agni, the god of fire"
]

# Should produce:
WSU 1: source=SOURCE_MW, sense_ref="mw:217497", gloss_raw="auspicious; benign; favorable"
WSU 2: source=SOURCE_MW, sense_ref="mw:217498", gloss_raw="Agni, the god of fire"
```

**Challenges**:
- Some sense lines lack MW IDs
- AP90 vs MW distinction needed
- Domain/register metadata not always present

### 2. Diogenes Adapter (Greek/Latin Lexica)

**Current Output**: `DictionaryEntry` with parsed dictionary chunks

**WSU Extraction Strategy**:
```python
def extract_wsu_diogenes(entry: DictionaryEntry) -> List[WitnessSenseUnit]:
    """
    Extract WSUs from Diogenes DictionaryEntry.
    
    Strategy depends on lexicon type:
    - LSJ (Greek): Use numbered senses with stable references
    - Lewis & Short (Latin): Section-based referencing
    
    For each distinct sense chunk:
    - source: SOURCE_DIOGENES
    - sense_ref: "diogenes:<LEXICON>:<REFERENCE>"
    - gloss_raw: The sense text
    - metadata: Language-specific tags if available
    """
```

**Example Diogenes Structure**:
```
Dictionary chunks may contain:
- Numbered senses: "1. first meaning; 2. second meaning"
- Lettered subsenses: "a) specific case; b) other case"
- Citation references: "(Hom. Il. 1.1)"
```

**Challenges**:
- Inconsistent formatting across lexica
- Citation extraction vs sense extraction
- Stable reference generation

### 3. Whitakers Adapter (Latin Morphology)

**Current Output**: `DictionaryEntry` with morphological analyses

**WSU Extraction Strategy**:
```python
def extract_wsu_whitakers(entry: DictionaryEntry) -> List[WitnessSenseUnit]:
    """
    Extract WSUs from Whitaker's Words output.
    
    Whitaker's provides:
    1. Morphology analyses (primary)
    2. Brief sense hints (secondary, less reliable)
    
    For morphology:
    - source: SOURCE_WHITAKERS
    - sense_ref: "whitaker:morph:<RUN_HASH>:<ANALYSIS_INDEX>"
    - gloss_raw: Morphological description
    
    For sense hints (if present):
    - source: SOURCE_WHITAKERS  
    - sense_ref: "whitaker:sense:<LINE_NUMBER>"
    - gloss_raw: Sense hint text
    """
```

**Challenges**:
- Whitaker's sense hints are not lexicon-grade
- Morphology descriptions need standardization
- Run hash generation for stable references

### 4. Heritage Adapter (Sanskrit Morphology)

**Current Output**: `DictionaryEntry` with morphological features

**WSU Extraction Strategy**:
```python
def extract_wsu_heritage(entry: DictionaryEntry) -> List[WitnessSenseUnit]:
    """
    Extract WSUs from Heritage Platform output.
    
    Heritage provides:
    1. Morphological analyses (detailed)
    2. Lemma linkage (when available)
    3. Some lexical metadata
    
    For morphology:
    - source: SOURCE_HERITAGE
    - sense_ref: "heritage:morph:<KEY>"
    - gloss_raw: Morphological feature string
    
    For lexical hints:
    - source: SOURCE_HERITAGE
    - sense_ref: "heritage:lex:<REF>"
    - gloss_raw: Lexical hint text
    """
```

**Challenges**:
- Encoding/SLP1 issues in raw data
- Morphology vs lexicon boundary
- Stable key generation

### 5. CLTK Adapter (Supplemental)

**Current Output**: `DictionaryEntry` with supplemental data

**WSU Extraction Strategy**:
```python
def extract_wsu_cltk(entry: DictionaryEntry) -> List[WitnessSenseUnit]:
    """
    Extract WSUs from CLTK backend.
    
    CLTK provides:
    1. Morphology suggestions
    2. Lemma candidates
    3. Supplemental lexicon data
    
    For all outputs:
    - source: SOURCE_CLTK
    - sense_ref: "cltk:<MODEL_ID>:<RUN_HASH>:<ITEM_INDEX>"
    - gloss_raw: The suggested text
    - metadata: Include confidence score if available
    """
```

**Challenges**:
- CLTK outputs vary by language/model
- Confidence scores may be present
- Model version tracking

## Implementation Approach

### Option A: Adapter Modification
Modify each adapter to include WSU extraction method:
```python
# In each adapter class
def extract_witness_sense_units(self, entry: DictionaryEntry) -> List[WitnessSenseUnit]:
    """Extract WSUs from this adapter's output."""
```

**Pros**:
- Adapter-specific knowledge stays in adapter
- Can optimize for each source format
- Clear separation of concerns

**Cons**:
- Breaks adapter interface compatibility
- Requires changes to all adapters at once
- Risk of inconsistent implementations

### Option B: Post-Processor Layer
Create separate WSU extractor that processes `DictionaryEntry`:
```python
class WSUExtractor:
    def extract_from_entry(entry: DictionaryEntry) -> List[WitnessSenseUnit]:
        """Extract WSUs by analyzing entry structure and source."""
```

**Pros**:
- No adapter changes required
- Centralized logic
- Can handle mixed-source entries

**Cons**: 
- May not have adapter-specific knowledge
- More complex pattern matching
- Risk of missing adapter-specific nuances

### **Recommended Approach**: Hybrid
1. **Phase 1**: Create post-processor for immediate progress
2. **Phase 2**: Gradually add adapter-specific extraction methods
3. **Phase 3**: Migrate to adapter methods as they become available

## WSU Extraction Interface

### Proposed Interface
```python
# In src/langnet/semantic_reducer/wsu_extractor.py
class WSUExtractor:
    """Extract Witness Sense Units from DictionaryEntry objects."""
    
    def extract_wsu_from_entry(entry: DictionaryEntry) -> List[WitnessSenseUnit]:
        """
        Extract WSUs based on entry source and structure.
        
        This is a temporary implementation that will be replaced by
        adapter-specific methods as they become available.
        """
        
        # Determine source from entry metadata
        # Apply source-specific extraction logic
        # Return list of WSUs
```

### Source Detection
```python
def detect_source_from_entry(entry: DictionaryEntry) -> Source:
    """
    Detect primary source from DictionaryEntry structure.
    
    Heuristics:
    - CDSL: has 'sense_lines' with MW/AP90 IDs
    - Diogenes: has 'dictionary_chunks' with lexicon markers
    - Whitakers: has 'morphology_analyses' with Whitaker's format
    - Heritage: has 'morphology_info' with Heritage structure
    - CLTK: has 'cltk_data' or similar marker
    """
```

## Success Criteria for Phase 1

### **Minimum Viable Phase 1**
- [ ] WSU type defined in semantic schema
- [ ] Basic WSU extractor for CDSL entries
- [ ] Stable MW ID references preserved
- [ ] Tests with 10+ Sanskrit words (agni, śiva, etc.)

### **Phase 1 Complete**
- [ ] WSU extraction for all major adapters (CDSL, Diogenes, Whitakers)
- [ ] Stable locators for all WSUs
- [ ] No data loss in extraction
- [ ] Comprehensive test suite
- [ ] Performance: < 50ms per entry

## Testing Strategy

### **Test Data Sources**
```python
TEST_ENTRIES = [
    # Sanskrit (CDSL)
    ("san", "agni", "CDSL with MW IDs"),
    ("san", "śiva", "CDSL with multiple senses"),
    
    # Latin (Diogenes + Whitakers)
    ("lat", "lupus", "Diogenes + Whitakers combination"),
    ("lat", "amor", "Multiple lexicon sources"),
    
    # Greek (Diogenes)
    ("grc", "λόγος", "LSJ lexicon structure"),
    ("grc", "ἄνθρωπος", "Simple word with clear senses"),
]
```

### **Validation Checks**
```python
def validate_wsu_extraction(entry: DictionaryEntry, wsu_list: List[WitnessSenseUnit]):
    """
    Validate WSU extraction quality.
    
    1. No data loss: All sense information preserved
    2. Stable references: Each WSU has unique, reproducible sense_ref
    3. Source accuracy: Correct Source enum for each WSU
    4. Ordering preserved: WSUs in same order as original
    5. No duplication: No identical WSUs extracted
    """
```

## Next Steps After Phase 1

Once WSU extraction is complete:
1. **Move to Phase 2**: Gloss normalization
2. **Update adapters**: Add native WSU extraction methods
3. **Performance optimization**: Cache extraction results
4. **Documentation**: Update adapter documentation with WSU examples

## Questions to Resolve

1. **How to handle multi-source entries?** (e.g., Diogenes + Whitakers)
   - Option: Separate WSU lists per source
   - Option: Combined list with source field

2. **What about citations vs senses?**
   - Should citation references be separate WSUs?
   - Or should they be metadata on sense WSUs?

3. **Ordering preservation across sources?**
   - How to order WSUs from multiple adapters?
   - Source priority: CDSL > Diogenes > Whitakers > CLTK?

4. **Metadata extraction depth?**
   - Should we try to extract domains/register from raw text?
   - Or leave metadata empty for Phase 1?

---

*This requirements doc will guide Phase 1 implementation. Start with CDSL adapter as it has the clearest structure, then expand to others.*