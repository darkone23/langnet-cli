# Future Work & Development Priorities

**Last Updated:** January 29, 2026  
**Priority Framework:** Based on pedagogical impact vs. implementation effort

## Current Status Summary

Core pedagogical features are **COMPLETE**:
- ✅ Foster functional grammar for all languages
- ✅ Sanskrit lemmatization and root display  
- ✅ Heritage Platform integration
- ✅ 151+ comprehensive tests passing

## Priority Matrix

| Priority | Feature | Effort | Pedagogical Impact | Status |
|----------|---------|--------|-------------------|--------|
| **P0** | Lemmatization | ✅ **COMPLETE** | **Huge** | ✅ All languages |
| **P0** | Foster Functional Grammar | ✅ **COMPLETE** | **Huge** | ✅ All languages |
| **P1** | Citation Display | Medium | **Huge** | 🔄 Partial (Diogenes) |
| **P1** | Fuzzy Searching | Low | High | ⏳ Not started |
| **P2** | CDSL Reference Enhancement | Low | High | ⏳ Not started |
| **P2** | Enhanced Citation Formatting | Low | Medium | ⏳ Not started |
| **P3** | Cross-Lexicon Etymology | High | Medium | ⏳ Not started |
| **P3** | Performance/Scaling | High | Low | ⏳ Not started |

## Phase 1: Citation Display & Context (P1 - High Priority)

### Goal: Foster's method — "See the word in the wild"

**Current:** Diogenes provides citations but they're displayed raw

**Implementation:**
1. **Citation formatter** for Diogenes results
   - Extract author/work/book/section/line from reference IDs
   - Format as "Cicero (Cic. Off. 1.2.5): '...in rerum gestarum...'"
   - File: `src/langnet/diogenes/citation_formatter.py`

2. **Snippet previews**
   - One-line context from parsed lexicon data
   - Highlight search term in context
   - Prioritize most pedagogically useful citations

3. **Morphology breakdown prominently displayed**
   - Show principal parts (Latin) or root/class (Sanskrit) at top
   - Connect morphology to citations

**Estimated Effort:** 3-4 days

## Phase 2: Fuzzy Searching & Typo Tolerance (P1 - High Priority)

### Goal: Help learners despite orthographic variations

**Current:** Exact match only for dictionary lookups

**Implementation:**
1. **Levenshtein distance fallback**
   - When direct lookup fails, find closest matches
   - Support orthographic variants (v/u, i/j, etc.)
   - File: `src/langnet/fuzzy/core.py`

2. **Backoff lemmatization chain**
   - Priority: Direct → Fuzzy → Lemmatized lookup
   - Track search method for transparency
   - Already implemented for Sanskrit; extend to Latin/Greek

**Estimated Effort:** 2-3 days

## Phase 3: CDSL Reference Enhancement (P2 - Medium Priority)

### Goal: Display CDSL `<ls>` tags (lexicon references)

**Current:** CDSL parser captures `<ls>` tags but doesn't display them

**Implementation:**
1. **Enhance CDSL entry formatter**
   - Parse and display lexicon references: "SEE ALSO: L., TS., Vop."
   - Group by reference type
   - File: `src/langnet/cologne/core.py`

2. **Cross-reference navigation**
   - Allow clicking/tab-completion to referenced entries
   - Show relationship types (synonyms, antonyms, derivatives)

**Estimated Effort:** 1-2 days

## Phase 4: Enhanced Citation Formatting (P2 - Medium Priority)

### Goal: Better display of existing citation data

**Current:** Raw citation IDs without formatting

**Implementation:**
1. **Parse Diogenes reference formats**
   - "perseus:abo:phi,1254,001:2:19:6" → Author, Work, Book, Section, Line
   - Support multiple reference formats
   - File: `src/langnet/diogenes/parser.py`

2. **Context extraction**
   - Show surrounding words for each citation
   - Highlight morphology in context
   - Group by work/author

**Estimated Effort:** 2-3 days

## Phase 5: Local Data Storage Layer (P3 - Low Priority)

### Goal: Build language-neutral knowledge base for derived lexicon data

**Schema Design:**
```sql
CREATE TABLE words (
    id INTEGER PRIMARY KEY,
    term VARCHAR NOT NULL,
    language VARCHAR NOT NULL,
    headword VARCHAR,
    ipa VARCHAR,
    part_of_speech VARCHAR
);

CREATE TABLE senses (
    id INTEGER PRIMARY KEY,
    word_id INTEGER,
    definition VARCHAR,
    citations VARCHAR,
    source_lemma VARCHAR,
    FOREIGN KEY (word_id) REFERENCES words(id)
);

CREATE TABLE morphology (
    id INTEGER PRIMARY KEY,
    word_id INTEGER,
    tags VARCHAR,
    stems VARCHAR,
    endings VARCHAR,
    FOREIGN KEY (word_id) REFERENCES words(id)
);

CREATE TABLE cognates (
    id INTEGER PRIMARY KEY,
    word_id INTEGER,
    related_word_id INTEGER,
    relationship_type VARCHAR,
    related_word_language VARCHAR,
    FOREIGN KEY (word_id) REFERENCES words(id),
    FOREIGN KEY (related_word_id) REFERENCES words(id)
);
```

**Future Features:**
- Phonetic search by 'sounds-like'
- Precomputed indexes for fast search
- Cross-lexicon etymology research
- Automated etymology linking

**Estimated Effort:** 5-7 days

## Phase 6: Advanced Features (P3 - Low Priority)

### CLTK Enhancements
- Latin stemmer/lemmatizer for faster lookups
- Greek prosody and meter information
- Vedic Sanskrit variant support

### Performance Optimization
- Async multi-search (query Lewis, Diogenes, CDSL in parallel)
- Connection pooling for Heritage CGI calls
- DuckDB caching layer

### Observability
- Distributed tracing with correlation IDs
- Query profiling by backend service

### Export Features
- Anki flashcards export (word + definition + one citation)
- CSV/JSON export for research

## Heritage Platform Integration (Remaining)

**Current:** Morphology and dictionary lookup complete

**Remaining Phases from HERITAGE_PLAN.md:**
- Phase 4: Grammar & Sandhi Services (sktdeclin, sktconjug, sktsandhier)
- Phase 5: Advanced Parsing Services (sktparser, sktgraph)
- Phase 6: API Enhancement & Optimization

**Priority:** Medium (only needed for advanced Sanskrit features)

## DICO Bilingual Pipeline

**Status:** Conceptual/planning phase only

**Considerations:**
- Requires OpenAI API integration
- Heavy on data processing (15,000+ entries)
- Separate from core pedagogical mission
- **Recommendation:** Postpone or implement as separate project

## Implementation Guidelines

### Pedagogical Focus
All features should be evaluated by:
1. Does this help learners understand word function?
2. Does this make classical languages more accessible?
3. Does this support Foster's "see the word in the wild" philosophy?

### Technical Standards
- Use existing patterns from completed implementations
- Follow dataclass + cattrs serialization
- Add comprehensive tests
- Document pedagogical rationale
- Consider performance impact

### Testing Requirements
- Unit tests for all new functionality
- Integration tests with real backends
- Performance benchmarks for new features
- Edge case handling (missing data, errors, timeouts)

## Getting Started

For each phase:
1. Create detailed implementation plan (like PHASE1_DETAILED_PLAN.md)
2. Implement core functionality
3. Add tests
4. Integrate with existing codebase
5. Update documentation

**Start with:** Phase 1 (Citation Display) - highest pedagogical impact for remaining work

---

*Future work should focus on features that directly enhance the learning experience. Citations, fuzzy search, and enhanced displays will have the greatest impact for learners.*