# Sanskrit Heritage Backend Implementation Plan

## Overview
Create a new backend service that leverages the Sanskrit Heritage Platform CGI functions running at `localhost:48080`. This service will provide structured API access to Sanskrit morphological analysis, parsing, and dictionary lookup capabilities.

## Current State Analysis

### Existing Infrastructure
- **Heritage Platform**: Running at `localhost:48080` with CGI scripts in `/cgi-bin/skt/`
- **Available CGI Scripts**:
  - `sktreader` - Morphological analyzer
  - `sktparser` - Sentence parser
  - `sktdeclin` - Declension generator
  - `sktconjug` - Conjugation generator
  - `sktsandhier` - Sandhi processor
  - `sktlemmatizer` - Lemma finder
  - `sktindex`/`sktsearch` - Dictionary search
  - `sktgraph`/`sktgraph2` - Graph-based analysis

### Reference Implementation (`./tmp/heritage/` project)
- Python wrapper with web/shell modes
- BeautifulSoup parsing of HTML output
- SQLite caching layer (not needed)
- Supports Monier-Williams and Sanskrit Heritage dictionaries (not needed)

## Implementation Phases

### Phase 1: Foundation & Core API (Week 1-2)
**Goal**: Basic HTTP client with structured response parsing

**Checklist**:
- [ ] Create HTTP client for `localhost:48080` CGI calls
- [ ] Implement request parameter builder (text encoding, options)
- [ ] Create base HTML parser for common response patterns
- [ ] Add configuration for local vs. remote endpoint
- [ ] Set up logging and error handling

### Phase 2: Morphological Analysis Service (Week 3-4)
**Goal**: Full-featured morphological analyzer API

**Checklist**:
- [ ] Implement `sktreader` client (morphological analysis)
- [ ] Create structured response format (JSON)
- [ ] Parse solution tables with word-by-word analysis
- [ ] Extract roots, analyses, and lexicon references
- [ ] Handle multiple solutions/ambiguities
- [ ] Add caching layer for frequent queries
- [ ] Implement text segmentation support

### Phase 3: Dictionary & Lemma Services (Week 5-6)
**Goal**: Dictionary lookup and lemma finding capabilities

**Checklist**:
- [ ] Implement `sktindex`/`sktsearch` clients
- [ ] Create `sktlemmatizer` client for inflected forms
- [ ] Build lexicon entry parser (Monier-Williams, Heritage Dictionary)
- [ ] Extract headwords, definitions, grammatical information
- [ ] Handle alternative forms and cross-references
- [ ] fuzzy search feature (search simple ascii / fallback)
  - localhost:48080/cgi-bin/skt/sktsearch?lex=MW&q=kriya

### Phase 4: Grammar & Sandhi Services (Week 7-8)
**Goal**: Grammatical form generation and sandhi processing

**Checklist**:
- [ ] Implement `sktdeclin` client (noun declensions)
- [ ] Implement `sktconjug` client (verb conjugations)
- [ ] Create `sktsandhier` client (sandhi formation)
- [ ] Parse grammatical tables into structured data
- [ ] Support different grammatical parameters (gender, case, number)
- [ ] Add validation for input parameters

<!-- ### Phase 5: Advanced Parsing Services (Week 9-10) -->
<!-- **Goal**: Sentence parsing and semantic role labeling -->

<!-- **Checklist**: -->
<!-- - [ ] Implement `sktparser` client (sentence parsing) -->
<!-- - [ ] Parse semantic role information -->
<!-- - [ ] Extract dependency relations -->
<!-- - [ ] Handle compound analysis -->
<!-- - [ ] Implement `sktgraph`/`sktgraph2` clients -->
<!-- - [ ] Parse graph-based analysis outputs -->

<!-- ### Phase 6: API Enhancement & Optimization (Week 11-12) -->
<!-- **Goal**: Production-ready service with performance improvements -->

<!-- **Checklist**: -->
<!-- - [ ] Add rate limiting and request throttling -->
<!-- - [ ] Implement request batching for multiple words -->
<!-- - [ ] Add health checks and monitoring endpoints -->
<!-- - [ ] Optimize HTML parsing performance -->
<!-- - [ ] Implement connection pooling -->
<!-- - [ ] Add comprehensive test suite -->
<!-- - [ ] Create API documentation (OpenAPI/Swagger) -->

## Technical Architecture

### Components
1. **HTTP Client Layer**: CGI request/response handling
2. **HTML Parser Layer**: BeautifulSoup-based response parsing
3. **Data Model Layer**: Structured Python dataclasses
4. Implemented into the langnet-cli search tools
<!-- 4. **Cache Layer**: SQLite/Redis for performance -->
<!-- 5. **API Layer**: REST/GraphQL endpoints -->

### Key Design Decisions
- Use **async/await** for HTTP requests
- Implement **request/response models** with cattrs / dataclsses
- Create **modular parser classes** for each CGI script type
- Support json output (parse html)
- Include **fallback mechanisms** for CGI script failures

## Development Guidelines for Junior Engineers

### Getting Started
1. Study the existing `./tmp/heritage/heritage.py` for parsing patterns
2. Test CGI endpoints manually with curl to understand parameters
3. Create small, focused modules for each CGI script

### Code Patterns to Follow
- Use dataclasses for structured data
- Implement consistent error handling
- Write comprehensive tests for edge cases
- Document all CGI parameters and response formats

### Common Pitfalls to Avoid
- HTML structure may vary between CGI scripts
- Text encoding issues (Devanagari → Velthuis)
- CGI scripts may return multiple solution formats
- Some endpoints require specific parameter combinations

## Success Metrics
- Comprehensive test coverage (>80%)
- Clear, consistent API documentation
- Support for all major Heritage Platform features

## Next Steps
1. Start with Phase 1 implementation
2. Create spike prototypes for key CGI scripts
3. Establish development environment with local CGI access

---

*Note: This plan assumes familiarity with Python, HTTP clients, HTML parsing, and Sanskrit computational linguistics concepts. Regular coordination with domain experts is recommended for accurate implementation.*
