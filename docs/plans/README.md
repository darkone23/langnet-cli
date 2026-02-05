# Project Plans Overview

This repository organises its design and implementation plans under `docs/plans/` using clear lifecycle categories:

| Category | Directory | What it contains |
|----------|-----------|------------------|
| **Active** | `docs/plans/active/` | Plans that are currently being worked on. They may have partially‑implemented code, ongoing tests, or upcoming milestones. |
| **Todo** | `docs/plans/todo/` | High‑level ideas, future work, or plans that have not yet started. |
| **Completed** | `docs/plans/` | Plans whose work has been fully implemented and verified by tests. (Note: Currently implemented features are tracked in this README rather than separate files)

---

## ✅ Completed Features (Implemented & Tested)

### Core Infrastructure
- **Whitaker's Words Parser**: Complete line parsing for senses, codes, facts
- **Heritage Platform Integration**: Full Lark parser migration with encoding support
- **Velthuis Encoding System**: Comprehensive Sanskrit encoding support
- **Normalization Pipeline**: 381+ tests passing with robust validation

### Sanskrit Integration  
- **Sanskrit Heritage Platform**: Complete integration with Devanagari, IAST, Velthuis, SLP1, HK, ASCII support
- **CDSL Integration**: Cologne Digital Sanskrit Dictionary lookup
- **Encoding Bridge**: Multi-format conversion and normalization

### Educational Features
- **Foster Functional Grammar**: All Latin, Greek, Sanskrit cases/tenses mapped to functions
- **Lemmatization Pipeline**: Inflected forms → dictionary headwords
- **Citation System**: CTS URN support with "see the word in the wild" approach

## 🚧 Active Plans (Status: In Progress)

### 1. Citation System (✅ COMPLETE)
- **Status**: ✅ COMPLETE - Core functionality implemented
- **Goal**: Foster's "see the word in the wild" approach with CTS URN support
- **Implementation**: `src/langnet/citation/` with models, cts_urn parser, indexer
- **Tests**: `tests/test_cts_urn_basic.py` passes all tests
- **API**: Fully integrated with `/api/q` endpoint

### 3. DICO Scholarship Translation (⏳ PENDING)
- **Files**: `DICO_SCHOLARSHIP_TRANSLATION.md`
- **Status**: Plan exists, no implementation
- **Goal**: Scholarship translation features
- **Priority**: Medium - Specialized feature

### 4. Universal Schema (🔄 IN PROGRESS)
- **Files**: `UNIVERSAL_SCHEMA.md`
- **Status**: Design complete, implementation pending
- **Goal**: Cross-language data consistency
- **Priority**: Medium - Infrastructure improvement

## 📋 Todo Plans (Not Started)

### 1. DICO Integration (⏳ NOT STARTED)
- **Files**: `todo/dico/`
  - `DICO_INTEGRATION_PLAN.md`
  - `DICO_IMPLEMENTATION_GUIDE.md`
  - `DICO_BILINGUAL_PIPELINE.md`
- **Goal**: French-Sanskrit bilingual dictionary support
- **Priority**: Medium - Enhances Sanskrit learning

### 2. Normalization Enhancements (⏳ PENDING)
- **Files**: `todo/normalization/CANONICAL_QUERY_NORMALIZATION_TODO.md`
- **Goal**: Additional normalization features
- **Priority**: Medium - Quality improvement

### 3. Future Pedagogical Features (⏳ PENDING)
- **Files**: Various pedagogical enhancement plans
- **Goal**: Enhanced educational features
- **Priority**: Medium - User experience

---

## 🎯 Current Implementation Status

### ✅ Fully Implemented & Working (~75% Complete)
- **Core Query Engine**: Multi-language routing and aggregation
- **All Language Backends**: Diogenes, Whitaker's, CLTK, CDSL, Heritage
- **Foster Functional Grammar**: All three languages complete
- **Normalization Pipeline**: 381 tests passing, robust validation
- **Response Caching**: DuckDB-based caching system
- **AI-Assisted Development**: Multi-model persona system
- **Sanskrit Heritage Platform**: Full integration with Lark parser

### 🔄 Partially Implemented
- **ASCII Enrichment**: Sanskrit only, Latin/Greek pending
- **Universal Schema**: Design complete, implementation pending

### ⏳ Not Started
- **Fuzzy Search**: Critical for user experience
- **DICO Integration**: French-Sanskrit dictionary
- **Cross-Lexicon Etymology**: Advanced research feature

### 🚨 Critical Technical Issues
1. **Documentation Cleanup** - ✅ COMPLETED

### 🏗️ Core Dependencies
- **Sanskrit Heritage Platform**: Required dependency (localhost:48080)
- **Diogenes**: Required dependency (localhost:8888)
- **Whitaker's Words**: Required dependency (~/.local/bin/whitakers-words)
- **CLTK**: Automatic dependency (~500MB download)
- **CDSL**: Automatic dependency (~/cdsl_data/)

For detailed roadmap and current priorities, see [docs/ROADMAP.md](../ROADMAP.md).

### Maintenance Guidelines

1. **When a plan moves from active to completed** – move its markdown file to `docs/plans/completed/` and update this README.
2. **When a new high‑level idea appears** – add a markdown file under `docs/plans/todo/`.
3. **Avoid duplicate files** – each plan should live in only one of the three directories.
4. **Review implementation status** - Check if "active" plans are actually complete before updating.
5. **Keep structure clean** - Remove redundant files and directories.
6. **Track progress** - Update status markers (✅ COMPLETE, 🔄 IN PROGRESS, ⏳ PENDING) as work progresses.

### 📚 Related Documentation
- **[docs/ROADMAP.md](../ROADMAP.md)** - Current roadmap and priorities
- **[docs/DEVELOPER.md](../DEVELOPER.md)** - Development workflow and AI integration

*Last Updated: February 2, 2026*
