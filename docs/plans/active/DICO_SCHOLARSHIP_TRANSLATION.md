# DICO French Scholarship Translation Pipeline

**Status**: 📋 TODO (Not Started)
**Priority**: Medium-High
**Dependencies**: Sanskrit Heritage Integration complete

## Overview

Leverage the French DICO dictionary's comprehensive Sanskrit scholarship by extracting French definitions and using LLM translation pipelines to make this valuable academic resource accessible to English-speaking learners. This creates an **academic-to-educational pipeline** that surfaces high-quality French Sanskrit scholarship for English audiences.

**Key Insight**: DICO represents decades of French Indological scholarship. By translating these definitions via LLM, we make this valuable academic corpus available to English-speaking Sanskrit students.

## Current Status Analysis

### ✅ COMPLETED PREREQUISITES
1. **Sanskrit Heritage Integration** - ✅ Complete with Lark parser
2. **Encoding Detection** - ✅ SmartVelthuisNormalizer working
3. **Canonical Query Lookup** - ✅ `fetch_canonical_sanskrit()` implemented
4. **URL Parsing** - ✅ Heritage Platform URL extraction available

### 🚫 CURRENT GAP
- No DICO implementation exists
- Only mentioned in plans and documentation
- French-to-English LLM translation pipeline not built

## Goals

1. **Extract DICO URLs from Heritage Platform**
   - Heritage's `sktreader` returns links in Velthuis encoding (e.g., `agnii` for agnī)
   - Parse and decode these URLs to build a DICO reference index

2. **Build DICO Dictionary Pipeline**
   - Import or scrape DICO dictionary data (French definitions)
   - Create LLM translation pipeline: French → English
   - Wire translated definitions to `LanguageEngine` alongside existing backends

3. **Academic-to-Educational Pipeline**
   - Surface French Indological scholarship to English learners
   - Add citation tracking for French academic sources
   - Create comparative definitions: English (MW/CDSL) vs French (DICO) scholarship

## Technical Architecture

### Data Flow
```
User Query → Normalization → DICO Backend → French Definitions → LLM Translation → English Definitions
             ↓
       Heritage/CDSL Backends → Sanskrit Analysis
             ↓
          Combined Results with Translated Scholarship
```

### Key Components
1. **DICO Client** (`src/langnet/dico/client.py`)
   - HTTP client for DICO dictionary API/scraping
   - Velthuis-to-Devanagari conversion for URLs

2. **DICO Parser** (`src/langnet/dico/parser.py`)
   - Parse DICO HTML/XML/JSON responses
   - Extract French definitions and academic metadata

3. **LLM Translation Pipeline** (`src/langnet/dico/llm_translator.py`)
   - French → English translation of definitions
   - Academic terminology preservation
   - Quality validation and confidence scoring

4. **Academic-to-Educational Engine** (`src/langnet/dico/engine.py`)
   - Surface French scholarship to English learners
   - Integration with existing Sanskrit analysis
   - Citation tracking for French academic sources

5. **Integration Layer** (`src/langnet/engine/core.py`)
   - Add DICO backend to query routing
   - Merge translated definitions with Heritage/CDSL results

## Implementation Phases

### Phase 1: URL Extraction & Data Collection (3-4 days)
1. **Extract DICO URLs** from Heritage sktreader responses
2. **Build URL index** mapping Sanskrit terms to DICO pages
3. **Create data collection pipeline** for DICO dictionary
4. **Store collected data** in structured format (JSON/Parquet)

**Deliverables**:
- `DICOUrlExtractor` class
- DICO URL index database
- Initial data collection script

### Phase 2: Backend Implementation (4-5 days)
1. **Create DICO client** for HTTP requests
2. **Implement parser** for DICO responses
3. **Build LLM translation pipeline** (French → English)
4. **Create academic-to-educational service** (`DICOScholarshipService`)

**Deliverables**:
- `DICOScholarshipService` class
- LLM translation pipeline with quality validation
- Translated definition dataclasses with confidence scoring

### Phase 3: Academic-to-Educational Features (3-4 days)
1. **Implement French scholarship surfacing**
2. **Add comparative definitions** (English vs French scholarship)
3. **Enhance UI/CLI** with translation metadata
4. **Create citation tracking** for French academic sources

**Deliverables**:
- Comparative definition display
- Academic citation tracking
- Translation quality indicators

### Phase 4: Integration & Testing (2-3 days)
1. **Integrate with `LanguageEngine`**
2. **Add to API endpoints** (`/api/q`)
3. **Create comprehensive tests**
4. **Performance benchmarking**

**Deliverables**:
- Full integration with existing system
- Test suite covering all features
- Performance benchmarks

## Technical Considerations

### Data Format Challenges
- **DICO data format** unknown (XML, JSON, HTML scrape?)
- **Encoding issues** with French diacritics
- **Velthuis decoding** for URL parsing

### Schema Design
- Need translated academic entry structure:
```python
@dataclass
class TranslatedAcademicEntry:
    sanskrit_term: str
    french_original: str                    # Original French definition
    english_translation: str               # LLM-translated English version
    translation_confidence: float           # LLM confidence score
    academic_metadata: dict[str, str]       # Source, author, date, etc.
    citations: list[Citation]               # Academic citations
    comparative_notes: str | None = None    # Comparison with MW/CDSL definitions
```

### Caching Strategy
- **Local cache** for DICO lookups
- **Index preloading** for common terms
- **Incremental updates** as new URLs discovered

### Integration Points
- Add to `LanguageEngineConfig`
- Wire into Sanskrit query flow
- Support both standalone and combined queries

## Dependencies

1. **Sanskrit Heritage Integration** - ✅ COMPLETED
   - URL extraction from sktreader
   - Velthuis encoding support
   - Canonical form lookup

2. **Normalization Pipeline** - ✅ COMPLETED
   - Encoding detection
   - Canonical query handling

3. **Existing Infrastructure** - ✅ COMPLETED
   - Caching system
   - API framework
   - Testing infrastructure

## Risk Assessment

### High Risk
- **DICO data availability** - Unknown if easily accessible
- **LLM translation quality** - Academic terminology accuracy
- **Performance impact** - LLM API calls add latency

### Medium Risk  
- **URL parsing reliability** - Heritage Platform changes
- **Translation consistency** - LLM output variability
- **Integration complexity** - Multiple backend coordination

### Low Risk
- **Schema design** - Clear academic translation model
- **Testing** - Can mock LLM responses
- **Fallback options** - Can degrade gracefully without translation

## Mitigation Strategies

1. **Start with URL extraction only** - Validate data availability first
2. **Use cached translations** - Reduce LLM API calls
3. **Feature flags** - Gradual rollout with ability to disable translation
4. **Quality validation** - Human review samples of LLM translations

## Success Criteria

1. **Functionality**: Translated French scholarship available for Sanskrit queries
2. **Performance**: < 200ms additional latency for translated lookups (cached)
3. **Translation Quality**: > 85% accurate academic terminology translation
4. **Integration**: Seamless with existing Sanskrit analysis
5. **Educational Value**: Access to French Indological scholarship for English learners

## Testing Strategy

### Unit Tests
- DICO URL extraction
- French definition parsing
- LLM translation quality validation
- Academic metadata extraction

### Integration Tests
- End-to-end French scholarship translation pipeline
- Combined results with Heritage/CDSL
- Error handling for missing DICO data or LLM failures

### Performance Tests
- LLM translation latency measurements
- Translation cache effectiveness
- Memory usage with academic term index

## Timeline

**Total**: 12-16 days
```
Phase 1 (3-4 days): URL Extraction & Data Collection
Phase 2 (4-5 days): Backend Implementation  
Phase 3 (3-4 days): Bilingual Features
Phase 4 (2-3 days): Integration & Testing
```

## Next Immediate Steps

1. **Investigate DICO data availability** - Check if accessible via API/scraping
2. **Prototype URL extraction** - Test with real Heritage responses
3. **Design data models** - Based on available DICO format
4. **Create minimal implementation** - Basic lookup without full integration

## Educational Value

This integration provides:
- **English-speaking learners** - Access to French Indological scholarship via translation
- **Comparative scholarship** - English (MW/CDSL) vs French (DICO) academic perspectives
- **Vocabulary enrichment** - Additional definitions from French academic tradition
- **Research tool** - Cross-cultural academic analysis of Sanskrit terms