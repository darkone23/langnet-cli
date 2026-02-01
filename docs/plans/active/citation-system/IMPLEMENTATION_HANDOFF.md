# Universal Citation Schema - Implementation Handoff Document

**Date**: February 1, 2026  
**Status**: Phase 1 - Core Foundation  
**Priority**: High (P1.5)  
**Assigned To**: *Next Developer*  

## Overview

This document provides comprehensive handoff information for implementing a universal citation schema across langnet-cli's language backends. The goal is to create a standardized system for representing citations and references that works consistently across Latin, Greek, and Sanskrit backends.

## Current State Analysis

### ✅ **Existing Citation Systems**
1. **Diogenes (Greek/Latin)**: 
   - Location: `/src/langnet/diogenes/core.py:293`
   - Format: `citations: dict[str, str]` in `DiogenesDefinitionBlock`
   - Extraction: `handle_references_citations()` extracts `.origjump` references
   - Example: `{"perseus": "Hom. Il. 1.1"}`

2. **CDSL (Sanskrit)**:
   - Location: `/src/langnet/cologne/parser.py:241`
   - Format: `references: list[dict]` in `SanskritDictionaryEntry`
   - Extraction: `_parse_references()` function
   - Example: `[{"source": "L.", "type": "lexicon"}]`

3. **Documentation**:
   - `/docs/plans/active/CITATION_SYSTEM.md` - Detailed 4-phase plan
   - `/docs/plans/active/CTS_URN_SYSTEM.md` - CTS URN integration plan
   - `/docs/CITATIONS.md` - Dependency and source documentation

### 🚫 **Missing Components**
- Universal schema/models for citations
- Standardized reference types (book vs line vs dictionary)
- Centralized citation processing
- Educational rendering system
- CLI commands for citation explanation

## Implementation Priority Sequence

### **PHASE 1: CORE FOUNDATION** (Week 1)

#### 1.1 Create Citation Models ✅ *[Started]*
**File**: `/src/langnet/citation/models.py`
**Status**: Basic structure exists, needs completion
**TODO**:
- Complete `CitationType` enum with all reference types
- Implement `TextReference.to_standardized_string()` method
- Add validation to `TextReference` fields
- Create factory methods for common citation patterns

**Key Models**:
```python
class CitationType(str, Enum):
    # Text references
    BOOK_REFERENCE = "book_reference"          # Whole book
    LINE_REFERENCE = "line_reference"          # Specific line
    # Dictionary references
    DICTIONARY_ABBREVIATION = "dictionary_abbreviation"
    # ... etc

@dataclass
class TextReference:
    type: CitationType
    text: str  # Original citation text
    # Hierarchical location
    work: Optional[str]  # "Iliad", "Aeneid"
    author: Optional[str]  # "Homer", "Vergil"
    book: Optional[str]  # "1"
    line: Optional[str]  # "23"
    page: Optional[str]  # "127"
    # Standardized formats
    cts_urn: Optional[str]  # Canonical Text Service URN
```

#### 1.2 Build Citation Extractors
**Directory**: `/src/langnet/citation/extractors/`
**Files to create**:
- `base.py` - `BaseCitationExtractor` abstract class
- `diogenes.py` - `DiogenesCitationExtractor`
- `cdsl.py` - `CDSLCitationExtractor`
- `heritage.py` - `HeritageCitationExtractor`
- `whitakers.py` - `WhitakersCitationExtractor`

**Each extractor should**:
1. Parse backend-specific response formats
2. Convert to standardized `Citation` objects
3. Handle edge cases (Unicode, multiple encodings)
4. Maintain backward compatibility

#### 1.3 Update Normalization Models
**File**: `/src/langnet/normalization/models.py`
**Modification**: Add citation support to `CanonicalQuery`
```python
class CanonicalQuery:
    # ... existing fields ...
    citations: List[Citation] = field(default_factory=list)
```

### **PHASE 2: INTEGRATION** (Week 2)

#### 2.1 Integrate with Existing Backends
**Diogenes Integration**:
- Update `DiogenesDefinitionBlock.citations` to use new model
- Add adapter: `dict[str, str]` → `List[Citation]`
- Ensure backward compatibility

**CDSL Integration**:
- Update `SanskritDictionaryEntry.references` to use new model
- Map existing `list[dict]` format to `List[Citation]`

#### 2.2 Create CLI Commands
**Directory**: `/src/langnet/citation/cli/`
**Commands to implement**:
1. `langnet-cli explain-citation <abbreviation>`
   - Explains dictionary abbreviations (L&S, GEL, MW, etc.)
   - Shows full name, date, description

2. `langnet-cli follow-citation <reference>`
   - Opens/resolves citations to external resources
   - Handles Perseus links, CTS URNs, dictionary pages

3. `langnet-cli list-citations <query>`
   - Shows all citations for a query
   - Groups by type (dictionary, text, cross-reference)

#### 2.3 Add to API Responses
**File**: `/src/langnet/asgi.py`
**Modification**: Include standardized citations in `/api/q` responses
```json
{
  "query": "amor",
  "results": [ ... ],
  "citations": [
    {
      "type": "dictionary_abbreviation",
      "abbreviation": "L&S",
      "full_name": "Lewis and Short Latin Dictionary",
      "date": "1879",
      "reference": {
        "text": "L&S 127.3",
        "page": "127"
      }
    }
  ]
}
```

### **PHASE 3: ADVANCED FEATURES** (Week 3)

#### 3.1 CTS URN Integration
Follow plan in `/docs/plans/active/CTS_URN_SYSTEM.md`
- Implement `CTSUrn` dataclass
- Map Perseus references → CTS URNs
- Add Sanskrit CTS support (`sanskritLit` collection)

#### 3.2 Educational Rendering
Integrate with Foster grammar system (`/src/langnet/foster/`)
- Create human-readable explanations for citations
- Add "why this matters" context for students
- Format citations for educational use

#### 3.3 Cross-Language Consistency
- Ensure all backends produce same citation format
- Add language-specific dictionaries registry
- Handle Unicode/transliteration differences

## File Structure to Create

```
src/langnet/citation/
├── __init__.py
├── models.py              # ✅ Started - needs completion
├── extractors/
│   ├── __init__.py
│   ├── base.py           # BaseCitationExtractor abstract class
│   ├── diogenes.py       # DiogenesCitationExtractor
│   ├── cdsl.py           # CDSLCitationExtractor
│   ├── heritage.py       # HeritageCitationExtractor
│   └── whitakers.py      # WhitakersCitationExtractor
├── parsers/
│   ├── __init__.py
│   ├── reference_parser.py   # Parse "Hom. Il. 1.1" → structured
│   ├── abbreviation_parser.py # Parse "cf. L&S" → structured
│   └── cts_parser.py     # Parse CTS URNs
├── registry/
│   ├── __init__.py
│   ├── dictionaries.py   # L&S, GEL, MW registry with metadata
│   ├── authors.py        # Author/work mappings for citations
│   └── cts_registry.py   # CTS collection mappings
└── cli/
    ├── __init__.py
    ├── commands.py       # CLI citation commands
    └── formatters.py     # Pretty-print citations
```

## Key Technical Decisions

### Schema Design Principles
1. **Hierarchical Structure**: References should capture book.chapter.section.line hierarchy
2. **Type Safety**: Use Enums for citation types and numbering systems
3. **Extensibility**: Easy to add new citation types or backends
4. **Backward Compatibility**: Support old formats during transition

### Backward Compatibility Strategy
- Keep existing `dict[str, str]` and `list[dict]` formats
- Add `@property` methods for gradual migration
- Use feature flag: `USE_NEW_CITATION_SYSTEM = True`
- Provide migration utilities

### Performance Considerations
1. **Caching**: Dictionary abbreviation lookups should be cached
2. **Lazy Loading**: CTS URN resolution should be lazy
3. **Parallel Processing**: Batch citation extraction where possible
4. **Memory**: Citations can be large; consider streaming for big responses

## Testing Strategy

### Unit Tests
**Location**: `/tests/test_citation_*.py`
**Coverage**:
- Each extractor with real backend responses
- Parsing edge cases (complex references, Unicode)
- Backward compatibility adapters
- Serialization/deserialization round-trip

### Integration Tests
- End-to-end: query → extraction → serialization → API response
- Cross-backend consistency checks
- CLI command output verification
- Performance benchmarks

### Educational Value Tests
- Verify explanations are helpful for students
- Test CLI commands produce educational output
- Ensure "follow citation" works correctly
- Check Unicode rendering in terminal

## Success Metrics

1. **Functionality**: 95%+ of existing citations convert correctly to new format
2. **Performance**: < 10ms overhead per citation processed
3. **Educational Value**: Clear explanations for all common abbreviations
4. **Interoperability**: Works with all language backends (Latin, Greek, Sanskrit)
5. **Adoption**: Smooth transition for existing API consumers

## Common Pitfalls & Solutions

### Diogenes Betacode Conversion
**Problem**: Diogenes uses Greek betacode; citations may be in betacode
**Solution**: Use `betacode.conv.beta_to_uni()` in `DiogenesLanguages` class

### Sanskrit Encoding Schemes
**Problem**: Sanskrit references use multiple encodings (Devanagari, IAST, SLP1, HK)
**Solution**: Use `indic-transliteration` library via existing encoding service

### Whitaker's Words Custom Syntax
**Problem**: Whitaker's Words has custom reference syntax (`[~ reference]`)
**Solution**: Create specialized parser in `whitakers.py` extractor

### Performance Bottlenecks
**Problem**: Citation extraction blocking main query
**Solution**: Use async/await patterns, batch processing

## Immediate Next Steps

1. **Complete `models.py`**
   ```bash
   cd /home/nixos/langnet-tools/langnet-cli
   # Finish the TODOs in src/langnet/citation/models.py
   ```

2. **Create Diogenes extractor as POC**
   ```bash
   # Create extractors/diogenes.py first
   # Test with existing Diogenes fixtures
   ```

3. **Test with real responses**
   ```bash
   # Use existing test fixtures
   # Run: python -m pytest tests/test_diogenes_scraper.py -v
   ```

## Key Files to Examine

### Code Files
- `/src/langnet/diogenes/core.py:293` - Current citation handling in Diogenes
- `/src/langnet/cologne/parser.py:241` - CDSL reference parsing
- `/src/langnet/cologne/models.py:63` - Sanskrit dictionary models
- `/src/langnet/normalization/models.py` - CanonicalQuery model

### Test Fixtures
- `/tests/fixtures/whitakers/senses/simple/with_references.txt` - Whitaker's references
- `/tests/fixtures/heritage/search/agni.json` - Sanskrit references
- `/tests/test_diogenes_scraper.py` - Diogenes tests with citations

### Documentation
- `/docs/plans/active/CITATION_SYSTEM.md` - Original comprehensive plan
- `/docs/plans/active/CTS_URN_SYSTEM.md` - CTS integration details
- `/docs/CITATIONS.md` - Source and dependency info
- `AGENTS.md` - Multi-model AI development workflow

## Who to Ask / Reference

### AI Personas (see AGENTS.md)
- `@architect` - Schema design, complex logic
- `@coder` - Implementation details, testing
- `@auditor` - Security review, edge cases
- `@artisan` - Code optimization, style
- `@scribe` - Documentation, comments
- `@sleuth` - Debugging complex issues

### Key Patterns to Follow
1. **Dataclass + cattrs**: Used throughout for serialization
2. **Enum for types**: Consistent with existing codebase
3. **Feature flags**: For gradual rollout
4. **CLI integration**: Follow existing Click patterns

## Timeline Estimate

**Total**: 2-3 weeks for full implementation
- **Week 1**: Core models + extractors (Phase 1)
- **Week 2**: Integration + CLI (Phase 2)  
- **Week 3**: Advanced features + testing (Phase 3)

## Impact Statement

This implementation will transform langnet-cli from a **lookup tool** into a **citation-aware research assistant**. Students will be able to:

1. **Understand abbreviations**: "cf. L&S" → "Lewis and Short Latin Dictionary (1879)"
2. **Follow citations**: Clickable links to referenced texts
3. **Learn scholarly conventions**: Standard citation formats explained
4. **Navigate texts**: Direct access to specific passages
5. **Cross-reference**: Connect definitions across dictionaries

This significantly enhances the educational value for classical language students and researchers.

---

*Last Updated: February 1, 2026*  
*Handoff prepared by: opencode*  
*Next Review: When Phase 1 is completed*