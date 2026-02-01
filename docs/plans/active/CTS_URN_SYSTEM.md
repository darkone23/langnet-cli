# CTS URN System Integration

**Status**: 📋 TODO (Not Started)
**Priority**: Medium-High
**Dependencies**: Citation System partially complete

## Overview

Integrate Canonical Text Service URNs (CTS URNs) to provide standardized, hierarchical text references that work across the classical language ecosystem. CTS URNs enable:

1. **Standardized Text References**: Unambiguous passage identification
2. **Interoperability**: Works with Perseus, Scaife, and other digital classics platforms
3. **Text Navigation**: Direct links to specific passages
4. **Cross-Language Citation**: Consistent referencing across Greek, Latin, Sanskrit

## CTS URN Format

```
urn:cts:collection:author.work.version:passage
```

### Examples:
- **Greek**: `urn:cts:greekLit:tlg0003.tlg001.perseus-grc2:5.84.1` (Thucydides 5.84.1)
- **Latin**: `urn:cts:latinLit:phi1294.phi002.perseus-lat2:1.1` (Vergil Aeneid 1.1)
- **Sanskrit**: `urn:cts:sanskritLit:mbh.1.perseus-skt1:1.1.1` (Mahābhārata 1.1.1)

## Current State Analysis

### ✅ Existing Capabilities
- **Perseus Reference Extraction**: Diogenes extracts `.origjump` references
- **Text Structure Parsing**: Can handle hierarchical text divisions
- **Unicode Support**: Handles Greek, Latin, Sanskrit scripts
- **URL Construction**: Already builds URLs for external resources

### 🚫 Missing CTS Features
- **No CTS URN parsing/validation**
- **No Sanskrit collection** (`sanskritLit`) in CTS registry
- **No CTS ↔ Perseus mapping**
- **No CTS-aware navigation** in UI/CLI

## Architecture Design

### Core Data Models

```python
# src/langnet/cts/models.py
from dataclasses import dataclass
from enum import Enum

class CTSCollection(str, Enum):
    """CTS Collection identifiers"""
    GREEK_LITERATURE = "greekLit"
    LATIN_LITERATURE = "latinLit" 
    SANSKRIT_LITERATURE = "sanskritLit"  # NEW
    HEBREW_LITERATURE = "hebLit"
    COPTIC_LITERATURE = "copticLit"

@dataclass
class CTSUrn:
    """Canonical Text Service URN"""
    collection: CTSCollection
    author: str      # e.g., "tlg0003" (Thucydides)
    work: str        # e.g., "tlg001" (History)
    version: str     # e.g., "perseus-grc2"
    passage: str     # e.g., "5.84.1"
    
    def to_string(self) -> str:
        return f"urn:cts:{self.collection.value}:{self.author}.{self.work}.{self.version}:{self.passage}"
    
    @classmethod
    def from_string(cls, urn: str) -> "CTSUrn":
        # Parse urn:cts:collection:author.work.version:passage
        pass
    
    def to_url(self) -> str:
        """Convert to resolvable URL"""
        return f"https://cts.perseids.org/api/cts?request=GetPassage&urn={self.to_string()}"
```

### Sanskrit CTS Registry

```python
# src/langnet/cts/sanskrit_registry.py
SANSKRIT_AUTHORS = {
    "mbh": ("Mahābhārata", "Vyāsa", ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18"]),
    "ram": ("Rāmāyaṇa", "Vālmīki", ["1", "2", "3", "4", "5", "6", "7"]),
    "bg": ("Bhagavad Gītā", "Vyāsa", ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18"]),
    "kal": ("Kālidāsa", "Kālidāsa", ["sak", "kum", "rag", "megh", "rtu"]),
}

SANSKRIT_VERSIONS = {
    "perseus-skt1": ("Perseus Sanskrit", "Sanskrit texts from Perseus"),
    "gretil-skt1": ("GRETIL", "Göttingen Register of Electronic Texts in Indian Languages"),
    "mw-skt1": ("Monier-Williams", "MW Sanskrit-English Dictionary citations"),
}
```

## Implementation Phases

### Phase 1: Core CTS Module (2-3 days)
1. **Create CTS models** with parsing/validation
2. **Add Sanskrit collection** to CTS registry
3. **Create Perseus ↔ CTS mapping**
4. **Basic unit tests** for parsing/formatting

**Deliverables**:
- `CTSUrn` dataclass with full validation
- Sanskrit CTS registry
- Perseus-to-CTS conversion utilities

### Phase 2: Citation Integration (2-3 days)
5. **Integrate with Citation System** 
6. **Convert Diogenes `.origjump` → CTS URNs**
7. **Add CTS citations to API responses**
8. **Create CTS citation renderer**

**Deliverables**:
- Automatic CTS citation generation
- Enhanced API responses with CTS URNs
- Educational rendering of CTS references

### Phase 3: Navigation Features (2-3 days)
9. **Create CTS navigation commands**
10. **Add `--cts` flag to CLI queries**
11. **Implement passage range support** (e.g., `1.1-1.10`)
12. **Add text metadata lookup**

**Deliverables**:
- `follow-cts` CLI command
- Text metadata queries (author, work, version info)
- Passage range navigation

### Phase 4: Sanskrit-Specific Features (3-4 days)
13. **Map Heritage Platform results → CTS URNs**
14. **Add CDSL dictionary citations → CTS URNs**
15. **Create Sanskrit text hierarchy database**
16. **Test with major Sanskrit texts**

**Deliverables**:
- Sanskrit text CTS coverage
- Heritage/CDSL citation mapping
- Comprehensive Sanskrit test suite

## Educational Value

### For Students:
1. **Learn Standard Citations**: Understand CTS format for scholarly work
2. **Navigate Digital Editions**: Direct links to passages in context
3. **Compare Translations**: Same passage across languages/translations
4. **Text Structure Understanding**: Visualize hierarchical text organization

### Example Workflow:
```
Student query: "Iliad 1.1"
Result: "μῆνιν ἄειδε θεὰ..." with CTS URN
Student action: langnet-cli follow-cts "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1.1"
Result: Opens Iliad 1.1 in Perseus reader
```

## Technical Challenges

### Sanskrit-Specific Issues:
1. **Text Hierarchy**: Sanskrit texts have complex nested structures
2. **Edition Variants**: Multiple recensions and versions
3. **Transliteration**: CTS URNs use ASCII, need Devanagari/IAST mapping
4. **Authority Files**: Need Sanskrit author/work identifiers

### Cross-Platform Compatibility:
5. **Perseus CTS API**: Rate limits, response formats
6. **Local Caching**: Store text metadata and passages
7. **Offline Support**: Handle API unavailability gracefully

## Integration Points

### With Existing Systems:
1. **Diogenes Parser**: Convert `.origjump` → CTS URNs
2. **Citation System**: CTS as a citation type
3. **Foster Renderer**: Display CTS references educationally
4. **CLI Framework**: Add CTS navigation commands
5. **API Endpoints**: Include CTS URNs in responses

### Example Integration:
```python
# In Diogenes parser
if citation.type == CitationType.PERSEUS_REFERENCE:
    cts_urn = PerseusToCTSConverter.convert(citation.reference)
    citation.cts_urn = cts_urn
    citation.target = cts_urn.to_url()
```

## Success Criteria

1. **Coverage**: CTS URNs for major Greek, Latin, Sanskrit texts
2. **Accuracy**: > 95% correct Perseus → CTS mapping
3. **Performance**: < 50ms CTS URN parsing/generation
4. **Usability**: Clear educational benefits for students
5. **Interoperability**: Works with external CTS services

## Timeline

**Total**: 9-13 days
```
Phase 1 (2-3 days): Core CTS Module
Phase 2 (2-3 days): Citation Integration  
Phase 3 (2-3 days): Navigation Features
Phase 4 (3-4 days): Sanskrit-Specific Features
```

## Dependencies

1. **Citation System** - 📋 IN PROGRESS (Phase 1 needed first)
2. **Sanskrit Heritage Integration** - ✅ COMPLETED
3. **Diogenes Parser** - ✅ COMPLETED
4. **CLI Framework** - ✅ COMPLETED

## Risk Assessment

### Low Risk
- Model design (well-specified standard)
- Greek/Latin CTS (established mappings)
- Basic parsing/validation (regex-based)

### Medium Risk
- Sanskrit text hierarchy mapping
- Perseus API reliability/rate limits
- Performance with many CTS conversions

### High Risk
- Sanskrit authority file completeness
- Complex passage range handling
- Unicode/transliteration edge cases

## Next Steps

1. **Create CTS module skeleton**
2. **Implement basic CTSUrn parsing**
3. **Test with known Greek/Latin URNs**
4. **Design Sanskrit CTS registry structure**
5. **Prototype Perseus → CTS conversion**

## Impact

CTS URN integration transforms langnet-cli into a **canonical text-aware research platform**, enabling:
- **Seamless navigation** between dictionary entries and original texts
- **Standardized citations** for student papers and research
- **Cross-platform compatibility** with the digital classics ecosystem
- **Enhanced educational value** through text context and navigation