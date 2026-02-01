# Project Plans Overview

This repository organises its design and implementation plans under `docs/plans/` using three clear categories:

| Category | Directory | What it contains |
|----------|-----------|------------------|
| **Completed** | `docs/plans/completed/` | Plans whose work has been fully implemented and verified by tests. |
| **Active** | `docs/plans/active/` | Plans that are currently being worked on. They may have partially‑implemented code, ongoing tests, or upcoming milestones. |
| **Todo** | `docs/plans/todo/` | High‑level ideas, future work, or plans that have not yet started. |

---

## ✅ Completed Plans

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

> **Cleanup Completed**: Archive directory removed, duplicate files eliminated, structure simplified.

## 🚧 Active Plans (Status: In Progress)

### 1. Citation System (🔄 PARTIAL)
- **Files**: `CITATION_SYSTEM.md`
- **Status**: Basic integration exists, needs enhancement
- **Goal**: Foster's "see the word in the wild" approach
- **Priority**: High - Huge pedagogical impact

### 2. CTS URN System (⏳ PENDING)
- **Files**: `CTS_URN_SYSTEM.md`
- **Status**: Plan exists, no implementation
- **Goal**: Canonical Text Standard reference system
- **Priority**: Low - Scholarly feature

### 3. DICO Scholarship Translation (⏳ PENDING)
- **Files**: `DICO_SCHOLARSHIP_TRANSLATION.md`
- **Status**: Plan exists, no implementation
- **Goal**: Scholarship translation features
- **Priority**: Low - Specialized feature

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
- **Citation Display**: Basic integration, needs enhancement
- **Universal Schema**: Design complete, implementation pending

### ⏳ Not Started
- **Fuzzy Search**: Critical for user experience
- **DICO Integration**: French-Sanskrit dictionary
- **CTS URN System**: Scholarly text references
- **Cross-Lexicon Etymology**: Advanced research feature

### 🚨 Critical Technical Issues
1. **Duplicate Fields in LanguageEngineConfig** - Must fix immediately
2. **Documentation Cleanup** - ✅ COMPLETED

### 🏗️ Core Dependencies
- **Sanskrit Heritage Platform**: Required dependency (localhost:48080)
- **Diogenes**: Required dependency (localhost:8888)
- **Whitaker's Words**: Required dependency (~/.local/bin/whitakers-words)
- **CLTK**: Automatic dependency (~500MB download)
- **CDSL**: Automatic dependency (~/cdsl_data/)

For detailed roadmap and current priorities, see [docs/TODO.md](../TODO.md).

### Maintenance Guidelines

1. **When a plan moves from active to completed** – move its markdown file to `docs/plans/completed/` and update this README.
2. **When a new high‑level idea appears** – add a markdown file under `docs/plans/todo/`.
3. **Avoid duplicate files** – each plan should live in only one of the three directories.
4. **Review implementation status** - Check if "active" plans are actually complete before updating.
5. **Keep structure clean** - Remove redundant files and directories.

Feel free to add or edit the entries above as the project evolves.

*Last Updated: February 1, 2026*

### 📚 Related Documentation
- **[docs/CITATIONS.md](../CITATIONS.md)** - Complete dependency documentation
- **[docs/TODO.md](../TODO.md)** - Current roadmap and priorities
- **[docs/ACTIVE_WORK_SUMMARY.md](ACTIVE_WORK_SUMMARY.md)** - Detailed implementation status
