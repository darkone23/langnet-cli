# Project Plans Overview

This repository organises its design and implementation plans under `docs/plans/` using three clear lifecycle categories:

| Category | Directory | What it contains |
|----------|-----------|------------------|
| **Completed** | `docs/ARCHIVES/COMPLETED_PLANS/` | Plans whose work has been fully implemented and verified by tests. |
| **Active** | `docs/plans/active/` | Plans that are currently being worked on. They may have partially‑implemented code, ongoing tests, or upcoming milestones. |
| **Todo** | `docs/plans/todo/` | High‑level ideas, future work, or plans that have not yet started. |

**Archived Plans**: Historical and deprecated plans are kept in `docs/ARCHIVES/` for reference but are no longer active.

---

## ✅ Completed Plans (in `docs/ARCHIVES/COMPLETED_PLANS/`)

### Core Infrastructure (Fully Implemented)
- **whitakers_test_coverage.md** - Whitaker's Words parser testing
- **WHITAKERS_PARSER_TESTING_PLAN.md** - Whitaker's Words testing strategy
- **heritage_parser_migration.md** - Heritage Platform Lark parser migration
- **VELTHUIS_IMPLEMENTATION_SUMMARY.md** - Velthuis encoding system

### Sanskrit Integration (Fully Implemented)
- **sanskit_heritage_integration.md** - Complete Heritage Platform integration
- **sanskrit/normalization** - Sanskrit-specific normalization and encoding

### Educational Features (Fully Implemented)
- **Foster Functional Grammar** - All Latin, Greek, Sanskrit cases/tenses mapped to functions
- **Normalization Pipeline** - 381 tests passing, robust validation
- **Lemmatization** - Inflected forms → dictionary headwords

> **Cleanup Completed**: Archive directory created, duplicate files eliminated, structure simplified.

## 🚧 Active Plans (Status: In Progress)

### 1. Citation System (🔄 CRITICAL - API Integration Gap)
- **Files**: `docs/CITATION_SYSTEM.md`
- **Status**: 90% complete but critical API integration gap identified
- **Goal**: Foster's "see the word in the wild" approach with CTS URN support
- **Priority**: **HIGH** - 1-2 hours to fix API integration
- **Issue**: `/api/q` endpoint extracts citations but missing `cts_urn` field

### 2. CTS URN System (🔄 IN PROGRESS)
- **Files**: `docs/CTS_URN_SYSTEM.md`
- **Status**: Core functionality complete, API integration pending
- **Goal**: Canonical Text Standard reference system
- **Priority**: HIGH - Required for citation system completion

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
- **Citation Display**: Basic integration, needs enhancement (CRITICAL GAP)
- **Universal Schema**: Design complete, implementation pending

### ⏳ Not Started
- **Fuzzy Search**: Critical for user experience
- **DICO Integration**: French-Sanskrit dictionary
- **CTS URN System**: Scholarly text references (needs API fix)
- **Cross-Lexicon Etymology**: Advanced research feature

### 🚨 Critical Technical Issues
1. **Citation System API Gap** - MUST fix immediately (1-2 hours)
2. **Duplicate Fields in LanguageEngineConfig** - Must fix immediately
3. **Documentation Cleanup** - ✅ COMPLETED

### 🏗️ Core Dependencies
- **Sanskrit Heritage Platform**: Required dependency (localhost:48080)
- **Diogenes**: Required dependency (localhost:8888)
- **Whitaker's Words**: Required dependency (~/.local/bin/whitakers-words)
- **CLTK**: Automatic dependency (~500MB download)
- **CDSL**: Automatic dependency (~/cdsl_data/)

For detailed roadmap and current priorities, see [docs/ROADMAP.md](../ROADMAP.md).

### Maintenance Guidelines

1. **When a plan moves from active to completed** – move its markdown file to `docs/ARCHIVES/COMPLETED_PLANS/` and update this README.
2. **When a new high‑level idea appears** – add a markdown file under `docs/plans/todo/`.
3. **Avoid duplicate files** – each plan should live in only one of the three directories.
4. **Review implementation status** - Check if "active" plans are actually complete before updating.
5. **Keep structure clean** - Remove redundant files and directories, archive historical content.
6. **Archive deprecated plans** - Move to `docs/ARCHIVES/` rather than deleting.

### 📚 Related Documentation
- **[docs/CITATION_SYSTEM.md](../CITATION_SYSTEM.md)** - Comprehensive citation system documentation
- **[docs/CTS_URN_SYSTEM.md](../CTS_URN_SYSTEM.md)** - CTS URN system documentation
- **[docs/ROADMAP.md](../ROADMAP.md)** - Current roadmap and priorities (consolidated from TODO.md)
- **[docs/ACTIVE_WORK_SUMMARY.md](ACTIVE_WORK_SUMMARY.md)** - Detailed implementation status
- **[docs/ARCHIVES/](../ARCHIVES/)** - Historical and deprecated documentation

*Last Updated: February 2, 2026*
