# Comprehensive Citation System Integration

**Status**: 📋 TODO (Not Started)  
**Priority**: High (P1.5 - Between Citation Display and Enhanced Formatting)
**Dependencies**: Sanskrit Heritage Integration complete

## Overview

Create a unified citation system that:
1. **Extends existing Diogenes `.origjump` parsing** with structured data
2. **Adds CTS URN support** for canonical text references
3. **Explains dictionary abbreviations** (cf. L&S, see GEL, MW, etc.)
4. **Provides educational explanations** for scholarly citations
5. **Enables "follow the citation" navigation**

## Current State Analysis

### ✅ Already Working
- **Diogenes extracts `.origjump` references** as `citations` dict
- **Perseus reference parsing** via existing parser
- **Basic citation fields** in `DiogenesDefinitionBlock`

### 🚫 Missing Features
- **No structured citation model** - uses plain dict
- **No abbreviation explanations** - students see "cf. L&S" without explanation
- **No CTS URN support** - cannot handle canonical text references
- **No educational rendering** - citations appear as raw text
- **No cross-language consistency** - Sanskrit results lack citation support

## Architecture Design

### Core Data Models

```python
# src/langnet/citation/models.py
class CitationType(str, Enum):
    PERSEUS_REFERENCE = "perseus_reference"
    CTS_URN = "cts_urn"
    DICTIONARY_ABBREVIATION = "dictionary_abbreviation"
    CROSS_REFERENCE = "cross_reference"
    HERITAGE_REFERENCE = "heritage_reference"

@dataclass
class Citation:
    type: CitationType
    reference: str                    # Original citation text
    target: str | None = None         # Resolvable URL
    description: str | None = None    # Human explanation
    abbreviation: str | None = None   # For dictionary citations
    work_title: str | None = None     # Full work title
    author: str | None = None         # Author name
```

### Dictionary Abbreviation Registry

```python
DICTIONARY_ABBREVS = {
    "L&S": ("Lewis and Short", "Latin Dictionary (1879)"),
    "GEL": ("Liddell-Scott-Jones", "Greek-English Lexicon"),
    "MW": ("Monier-Williams", "Sanskrit-English Dictionary"),
    "DP": ("Dharmakīrti", "Pramāṇavārttika"),
    "cf.": ("compare", "Cross-reference marker"),
    "vid.": ("see", "Latin 'vide' abbreviation"),
    "G.": ("Greek", "Greek language marker"),
    "L.": ("Latin", "Latin language marker"),
    "S.": ("Sanskrit", "Sanskrit language marker"),
}
```

## Integration Points

### 1. Enhance Diogenes Parser
```python
# Current: extracts dict[str, str]
block["citations"] = refs  # {"perseus": "Hom. Il. 1.1"}

# Enhanced: extracts list[Citation]
from langnet.citation.extractor import CitationExtractor
citations = [
    CitationExtractor.extract_from_origjump(ref_txt, ref_id)
    for ref in soup.select(".origjump")
]
block["citations"] = citations
```

### 2. Add Sanskrit Citation Support
```python
# In src/langnet/heritage/models.py
class HeritageDictionaryEntry:
    # ... existing fields ...
    citations: list[Citation] = field(default_factory=list)
```

### 3. Create CTS URN Module
```python
# src/langnet/cts/models.py
@dataclass
class CTSUrn:
    """Canonical Text Service URN"""
    collection: str  # "greekLit", "latinLit", "sanskritLit"
    author: str      # "tlg0003"
    work: str        # "tlg001" 
    version: str     # "perseus-grc2"
    passage: str     # "5.84.1"
    
    def to_string(self) -> str:
        return f"urn:cts:{self.collection}:{self.author}.{self.work}.{self.version}:{self.passage}"
```

## Implementation Phases

### Phase 1: Core Models & Parser Updates (2-3 days)
1. **Create citation models** (`src/langnet/citation/`)
2. **Enhance Diogenes parser** to use new models
3. **Add abbreviation extractor** for dictionary citations
4. **Maintain backward compatibility** with existing API

**Deliverables**:
- `Citation` dataclass with rich metadata
- `CitationExtractor` for parsing multiple formats
- Updated Diogenes parser with new citation model

### Phase 2: CTS URN Integration (2-3 days)
5. **Create CTS URN module** with Sanskrit support
6. **Map Perseus references → CTS URNs**
7. **Add Sanskrit collection** (`sanskritLit`)
8. **Test with real texts** (Iliad, Aeneid, Bhagavad Gita)

**Deliverables**:
- `CTSUrn` dataclass with parsing/validation
- Perseus-to-CTS mapping utilities
- Sanskrit CTS examples and tests

### Phase 3: Educational Rendering (1-2 days)
9. **Create Foster citation renderer**
10. **Add CLI explanation commands**
11. **Enhance API response formatting**

**Deliverables**:
- `CitationRenderer` for educational display
- `explain-citation` CLI command
- Enhanced API citation formatting

### Phase 4: Cross-Language Support (2-3 days)
12. **Add citations to Heritage results**
13. **Add citations to CDSL results**
14. **Create citation helper for all languages**
15. **Comprehensive testing**

**Deliverables**:
- Citation support for all backends
- Unified citation display across languages
- Complete test coverage

## Educational Value

### For Students:
1. **Understand Abbreviations**: "cf. L&S" → "Lewis and Short Latin Dictionary"
2. **Follow Citations**: Clickable links to referenced texts
3. **Learn Scholarly Conventions**: Understand standard citation formats
4. **Cross-Reference**: Connect definitions across dictionaries

### Example Workflow:
```
Student query: "amor"
Result includes: "cf. L&S 127.3"
Student action: langnet-cli explain-citation "L&S"
Response: "Lewis and Short Latin Dictionary (1879)"
Student action: langnet-cli follow-citation "L&S 127.3"
Result: Opens Perseus/CTS reference
```

## Technical Considerations

### Backward Compatibility
- Existing `citations` dict preserved during transition
- Feature flag for new citation format
- Migration path for API consumers

### Performance Impact
- Minimal overhead for citation extraction
- Caching for abbreviation lookups
- Lazy loading for CTS URN resolution

### Unicode Support
- Handle Sanskrit/Hebrew/Greek in citations
- Proper encoding for CTS URNs
- Diacritic preservation in dictionary titles

## Risk Assessment

### Low Risk
- Model design (clear requirements)
- Abbreviation mapping (static data)
- Educational rendering (display only)

### Medium Risk
- CTS URN parsing complexity
- Perseus reference mapping accuracy
- Cross-language consistency

### High Risk
- Performance with many citations
- Unicode edge cases
- Integration with existing API consumers

## Success Criteria

1. **Functionality**: All citation types extracted and explained
2. **Performance**: < 10ms overhead for citation processing
3. **Accuracy**: > 95% correct abbreviation identification
4. **Usability**: Clear educational value for students
5. **Integration**: Works with all language backends

## Timeline

**Total**: 7-11 days
```
Phase 1 (2-3 days): Core Models & Parser Updates
Phase 2 (2-3 days): CTS URN Integration  
Phase 3 (1-2 days): Educational Rendering
Phase 4 (2-3 days): Cross-Language Support
```

## Dependencies

1. **Sanskrit Heritage Integration** - ✅ COMPLETED
2. **Existing Diogenes Parser** - ✅ COMPLETED
3. **Foster Renderer Infrastructure** - ✅ COMPLETED
4. **CLI Framework** - ✅ COMPLETED

## Next Steps

1. **Create citation module structure**
2. **Prototype abbreviation extraction**
3. **Test with real Diogenes responses**
4. **Design educational rendering format**
5. **Implement gradual rollout plan**

## Impact Assessment

This system transforms langnet-cli from a **lookup tool** into a **citation-aware research assistant**, significantly enhancing its educational value for classical language students and researchers.