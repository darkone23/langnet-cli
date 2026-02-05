# Pedagogical TODO Analysis & Roadmap
**Generated**: 2025-02-05  
**Based on**: `docs/TODO.md` vs `docs/PEDAGOGICAL_PHILOSOPHY.md` vs Current Codebase

## Executive Summary

This roadmap prioritizes TODO items based on **pedagogical impact** vs **implementation complexity**, aligning with the Foster functional grammar philosophy outlined in `docs/PEDAGOGICAL_PHILOSOPHY.md`. The analysis identifies **CTS URN citations** and **Sanskrit canonical forms** as P0 priorities.

## Priority Matrix

| Priority | Issue | Pedagogical Impact | Implementation Complexity | Status | Affected Modules |
|----------|-------|-------------------|--------------------------|--------|------------------|
| **P0** | **CTS URN Citation System** | **Huge** - Core to "see the word in the wild" learning | Medium - citation parsing/enrichment | Broken | `src/langnet/citation/models.py`, `src/langnet/diogenes/core.py:300-323` |
| **P0** | **Sanskrit Canonical Form Integration** | **Huge** - Essential for Sanskrit learners using inflected forms | Medium - wire sktsearch into pipeline | Partial | `src/langnet/normalization/core.py`, `src/langnet/engine/core_normalized.py` |
| **P1** | **Diogenes Sense Extraction Fix** | High - affects Latin/Greek dictionary accuracy | Low-Medium - parser logic improvements | Broken | `src/langnet/diogenes/core.py:274-297` |
| **P1** | **Heritage Citation Abbreviations** | High - citations lack proper corpus abbreviations | Low - integrate existing abbreviation list | Partial | `docs/upstream-docs/skt-heritage/ABBR.md`, `src/langnet/heritage/*` |
| **P2** | **CDSL SLP1 Encoding Fix** | Medium - affects Sanskrit dictionary readability | High - automated transliteration pipeline | Problematic | `src/langnet/cologne/transcoder.py`, `src/langnet/normalization/sanskrit.py` |
| **P2** | **Universal Schema Improvements** | Medium - affects cross-tool consistency | Medium - refactoring & standardization | Partial | `src/langnet/schema.py` |
| **P3** | **Tool Debug Improvements** | Low-Medium - development/debugging | Low - API standardization | Missing | CLI tools, `src/langnet/cli.py` |
| **P3** | **Functional Grammar Mapping** | Medium - pedagogical presentation | Medium - comprehensive mapping | Partial | `src/langnet/foster/` |
| **P4** | **DICO Dictionary Integration** | Medium - expands learning resources | High - new service integration | Missing | `docs/plans/todo/dico/` (plans exist) |
| **P4** | **Web UI Development** | High - improves manual fuzzing & UX | High - full web application | Missing | New component needed |

## Detailed Analysis

### P0: Critical Educational Functionality

#### 1. CTS URN Citation System (`docs/TODO.md:7-8`)
- **Problem**: Citations should return proper CTS URNs; CTS URN enrichment currently not working
- **Pedagogical Impact**: Core to Foster's "see the word in the wild" approach
- **Current Implementation**: Citations parsed but not enriched to CTS URNs in `src/langnet/diogenes/core.py:300-323`
- **Solution Path**: Enhance citation parsing to convert references to proper CTS URNs

#### 2. Sanskrit Canonical Form Integration (`docs/TODO.md:12-14`)
- **Problem**: Sanskrit terms often need canonical form via sktsearch; all san tools should use canonical form; sktsearch not wired into tools
- **Pedagogical Impact**: Critical for Sanskrit learners using inflected forms (e.g., `योगेन` → `yoga`)
- **Current Implementation**: Normalization pipeline exists (`src/langnet/normalization/core.py`) but sktsearch integration missing
- **Solution Path**: Wire sktsearch into normalization pipeline for Sanskrit queries

### P1: High-Impact Data Quality Issues

#### 3. Diogenes Sense Extraction Fix (`docs/TODO.md:5-6`)
- **Problem**: Sense extraction from diogenes often results in broken senses (usually 'dictionary sense' and a bunch of 'about this usage')
- **Pedagogical Impact**: Directly affects dictionary accuracy for Latin/Greek
- **Current Implementation**: Sense collection logic in `src/langnet/diogenes/core.py:274-297`
- **Related Plan**: `docs/plans/todo/diogenes/REMOVE_UNRELIABLE_SENSES.md`

#### 4. Heritage Platform Citation Abbreviations (`docs/TODO.md:15-16`)
- **Problem**: Citation abbreviations not including corpus abbr.; saved real abbr list exists at `./upstream-docs/skt-heritage/ABBR.md`
- **Pedagogical Impact**: Improves citation readability and scholarly accuracy
- **Solution Path**: Integrate abbreviation list into heritage citation formatting

### P2: Cross-Dictionary Enhancements

#### 5. CDSL SLP1 Encoding Fix (`docs/TODO.md:22-29`)
- **Problem**: Often SLP1 encoded text in definitions; requires automated pipeline to fix (tokenize → transliterate → lookup → replace if valid Sanskrit term)
- **Pedagogical Impact**: Affects Sanskrit dictionary readability
- **Complexity**: High - requires comprehensive transliteration pipeline
- **Example**: `vf/kA` → `vṛ̍kā`

#### 6. Universal Schema Improvements (`docs/TODO.md:32-35`)
- **Problems**: `created_at` in CDSL citation seems pointless; mapping to universal schema often broken; needs better hierarchical organization for related/grouped terms
- **Pedagogical Impact**: Affects cross-tool consistency and data organization
- **Current Implementation**: `src/langnet/schema.py`
- **Solution Path**: Refactor schema for better hierarchical organization

### P3: Developer Experience & Tooling

#### 7. Tool Debug Improvements (`docs/TODO.md:36-38`)
- **Problems**: Tool output should just be passthrough JSON; tool should have standard 'verbs'
- **Impact**: Low-Medium - affects development/debugging efficiency
- **Solution**: Standardize CLI/API interfaces

#### 8. Functional Grammar Mapping (`docs/TODO.md:39`)
- **Problem**: Functional grammar mapping often not present
- **Current Status**: Foster grammar exists (`src/langnet/foster/`) but mapping incomplete
- **Pedagogical Impact**: Affects quality of functional grammar presentation
- **Solution**: Complete Foster grammar mapping across all languages

### P4: Infrastructure & UI

#### 9. DICO Dictionary Integration (`docs/TODO.md:18`)
- **Problem**: No DICO dictionary integration yet
- **Existing Plans**: `docs/plans/todo/dico/` contains implementation guides
- **Impact**: Expands bilingual dictionary coverage
- **Complexity**: High - new service integration

#### 10. Web UI Development (`docs/TODO.md:41-44`)
- **Problem**: Data accuracy bugs often easier to spot via manual fuzzing; needs web UI
- **Impact**: High - improves user experience and debugging
- **Complexity**: High - requires full web application development

## Implementation Priority Order

1. **Fix CTS URN Citation System** - Core pedagogical feature for "see the word in the wild"
2. **Integrate Sanskrit Canonical Forms** - Essential for Sanskrit learners using inflected forms
3. **Fix Diogenes Sense Extraction** - Improves Latin/Greek dictionary accuracy
4. **Integrate Citation Abbreviations** - Enhances citation readability
5. **Refactor Universal Schema** - Foundation for other improvements
6. **Address CDSL SLP1 Encoding** - Complex but important Sanskrit fix
7. **Standardize Tool Debug Interface** - Improves developer experience
8. **Complete Functional Grammar Mapping** - Finishes Foster implementation
9. **Integrate DICO Dictionary** - Expands bilingual coverage
10. **Develop Web UI** - Long-term usability enhancement

## Pedagogical Alignment

### Foster Functional Grammar Principles
- **Currently Active**: ✅ Lemmatization, ✅ Foster Functional Grammar
- **Partially Active**: 🔄 Citation Display (needs CTS URN fix)
- **Pending**: ⏳ Fuzzy Searching, CDSL Reference Enhancement, Enhanced Citation Formatting

### Sanskrit Pedagogy Features
- ✅ Root-Focused Learning (`√ag (to move, go)`)
- ✅ Lemmatization for Inflected Forms (`योगेन` → `yoga`)
- ✅ Multiple Encoding Support (Devanagari, IAST, SLP1, Velthuis)
- 🔄 Canonical Form Integration (needs sktsearch wiring)

## Actionable Next Steps

### Immediate (P0):
1. **@coder**: Fix CTS URN citation parsing in `src/langnet/diogenes/core.py:300-323`
2. **@coder**: Wire sktsearch into normalization pipeline (`src/langnet/normalization/core.py`)

### Short-term (P1):
3. **@sleuth**: Debug diogenes sense extraction (`src/langnet/diogenes/core.py:274-297`)
4. **@coder**: Integrate abbreviation list from `docs/upstream-docs/skt-heritage/ABBR.md`

### Medium-term (P2):
5. **@architect**: Design automated SLP1 transliteration pipeline
6. **@artisan**: Refactor universal schema for hierarchical organization

## Related Existing Plans
- `docs/plans/todo/diogenes/REMOVE_UNRELIABLE_SENSES.md`
- `docs/plans/todo/normalization/CANONICAL_QUERY_NORMALIZATION_TODO.md`
- `docs/plans/todo/dico/DICO_INTEGRATION_PLAN.md`

## Success Metrics
- **Educational**: Citations show proper CTS URNs, Sanskrit inflected forms resolve to lemmas
- **Technical**: Sense extraction reliability > 95%, schema consistency across tools
- **User Experience**: CLI tools provide consistent JSON output, web UI enables manual fuzzing