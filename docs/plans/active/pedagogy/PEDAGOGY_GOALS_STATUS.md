# langnet-cli Implementation Status

**Last Updated:** January 29, 2026  
**Current Status:** Core pedagogical transformation underway - Foster functional grammar now active

## Project Overview

langnet-cli is a classical language education tool providing instant access to dictionary definitions, morphological parsing, and grammatical information for **Latin, Greek, and Sanskrit**.

**Educational Philosophy:** Foster functional grammar approach - always show what words *do* in sentences, not just technical categories.

## Current Implementation Status

### ✅ CORE PEDAGOGICAL FEATURES ACTIVE

| Component | Status | Progress | Notes |
|-----------|--------|----------|-------|
| **Heritage Platform Foundation** | ✅ ACTIVE | Essential for Sanskrit | HTTP client, CGI parameter builder, HTML parser |
| **Heritage Parser Migration** | 📋 PLANNED | Regex → Lark migration | See `HERITAGE_PARSER_LARK_MIGRATION_PLAN.md` |
| **Heritage Morphology Analysis** | ✅ ACTIVE | Sanskrit morphology operational | sktreader integration, morphology result parsing |
| **Heritage Dictionary/Lemmatizer** | ✅ ACTIVE | Sanskrit lemmatization working | sktindex/sktsearch integration, lemmatization |
| **Foster Functional Grammar** | ✅ ACTIVE | **North Star achieved** | All languages (Latin, Greek, Sanskrit) |
| **Encoding Bridge (Heritage+CDSL)** | ✅ ACTIVE | Combined results working | POS extraction, pedagogical display formatting |
| **Sanskrit Foundation** | ✅ ACTIVE | Learner access enabled | CLTK morphology, lemmatization fallback, root display |
| **Test Coverage** | ✅ ROBUST | 151+ comprehensive tests | Quality foundation for further development |

### 📊 Feature Coverage by Language

| Feature | Latin | Greek | Sanskrit |
|---------|-------|-------|----------|
| Dictionary lookup | ✅ Lewis via Diogenes | ✅ Diogenes | ✅ CDSL |
| Morphological analysis | ✅ Whitaker's/Dio | ✅ spaCy/Diogenes | ✅ CLTK + Heritage |
| Lemmatization | ✅ CLTK | ✅ spaCy | ✅ CLTK + Heritage |
| Foster grammar display | ✅ COMPLETE | ✅ COMPLETE | ✅ COMPLETE |
| Citation display | ✅ Diogenes | ✅ Diogenes | ✅ CDSL |
| Root display | N/A | N/A | ✅ CDSL etymology |

## Technical Architecture

### Backend Services
- **CDSL Sanskrit Dictionary**: Local SQLite database with ~180,000 entries
- **Heritage Platform**: CGI server at `localhost:48080` for Sanskrit morphology
- **Diogenes**: Greek/Latin dictionary and morphology via scraper
- **CLTK**: Classical Language Toolkit for Latin/Greek/Sanskrit morphology
- **Whitaker's Words**: Latin morphological analyzer

### Data Flow
1. Query routed by language to appropriate backend(s)
2. Sanskrit: Heritage lemmatizer → CDSL lookup → Foster grammar display
3. Latin/Greek: Diogenes/CLTK → Foster grammar display
4. Results combined and formatted with Foster functional terminology

### Key Files
- `src/langnet/engine/core.py` - Main query router and result assembler
- `src/langnet/heritage/` - Heritage Platform integration (complete)
- `src/langnet/foster/` - Foster grammar mappings and application
- `src/langnet/cologne/` - CDSL Sanskrit dictionary interface
- `src/langnet/diogenes/` - Greek/Latin dictionary interface

## Pedagogical Features Active

### Foster Functional Grammar - Now Active
**Display Format:** Technical Term + Foster Function (e.g., "Nominative (Naming Function)")

**Languages Supported:**
- **Latin**: All cases, tenses, genders, numbers, voices
- **Greek**: All cases, tenses, genders, numbers, moods, voices  
- **Sanskrit**: All cases (1-8), genders, numbers

**Example Output:**
```
Morphology:
  - Future (Time-Later Function)
  - Participle (Participle Function)
  - Active (Doing Function)
  - Masculine (Male Function)
  - Nominative (Naming Function)
  - Plural (Group Function)
```

**Impact:** This transforms langnet-cli from a data browser into a pedagogical engine.

### Sanskrit-Specific Features
- **Lemmatization fallback**: Inflected forms (योगेन) → lemma (yoga) → CDSL lookup
- **Root display**: Verb/noun roots shown prominently: `√ag (to move, go)`
- **Encoding support**: Devanagari, IAST, SLP1, Velthuis
- **Heritage+CDSL integration**: Combined morphology + dictionary results

## Testing Status

**Current Test Suite:** 151 tests passing

**Key Test Categories:**
- Heritage Platform connectivity and integration
- Foster grammar mappings and rendering
- CDSL Sanskrit dictionary functionality
- Diogenes Greek/Latin parsing
- API integration and caching
- Sanskrit lemmatization and morphology

**Test Command:** `just test` or `nose2 -s tests --config tests/nose2.cfg`

## Usage Examples

### CLI
```bash
# Sanskrit with lemmatization
devenv shell langnet-cli -- query san योगेन

# Latin with Foster grammar
devenv shell langnet-cli -- query lat sumpturi

# Greek
devenv shell langnet-cli -- query grc λόγος
```

### API
```bash
# Sanskrit query
curl -s -X POST "http://localhost:8000/api/q" -d "l=san&s=agni"

# Latin query with Foster grammar
curl -s -X POST "http://localhost:8000/api/q" -d "l=lat&s=sumpturi"
```

## Environment Requirements

- Python 3.8+
- Heritage Platform running at `localhost:48080` (for Sanskrit morphology)
- CDSL Sanskrit database loaded
- Diogenes accessible for Greek/Latin
- All dependencies installed via poetry

## Known Issues & Limitations

1. **Heritage Platform dependency**: Requires local CGI server for Sanskrit morphology
2. **CLTK cold download**: ~500MB Sanskrit model download on first query
3. **Diogenes zombie threads**: Run `langnet-dg-reaper` if needed
4. **Process restart**: Server caches Python modules - restart after code changes

## Recent Updates (January 2026)

- ✅ **Heritage Platform integration completed**
- ✅ **Foster grammar implementation completed for all languages**
- ✅ **Sanskrit lemmatization and root display implemented**
- ✅ **Comprehensive test suite (151 tests)**
- ✅ **Documentation cleanup and consolidation**

## Next Steps

See [FUTURE_WORK.md](FUTURE_WORK.md) for prioritized future development plans.

---

*This status reflects the implementation as of January 29, 2026. The core pedagogical features (Foster grammar, Sanskrit lemmatization, Heritage integration) are complete and production-ready.*