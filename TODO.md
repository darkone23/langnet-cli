# TODO

## Current Roadmap

### Phase 1: API Completion (High Priority)

#### Complete asgi.py Implementation
The `langnet/asgi.py` is currently a stub returning "hello from langnet-api". It needs to:
- [x] Accept HTTP requests at `/api/q?l=<lang>&s=<word>`
- [x] Validate language parameter (lat, grc, san)
- [x] Validate word parameter (non-empty string)
- [x] Call `LanguageEngine.handle_query(lang, word)`
- [x] Return JSON response with proper error handling
- [x] Use `orjson` directly for JSON serialization (cattrs uses orjson for unstructured dataclasses)

#### Implement Query Endpoints by Language
- [x] **Latin**: Aggregate diogenes (lexicon) + whitakers (morphology) + CLTK (Lewis lexicon)
- [x] **Greek**: Return diogenes results (lexicon + morphology)

### Phase 2b: Reliability Improvements

### Phase 2: Code Style

#### Migrate from Pydantic to cattrs
Pydantic has been phased out in favor of Python's `dataclass` + `cattrs`:

- [x] Add `cattrs` to pyproject.toml dependencies
- [x] Audit all Pydantic models in:
  - `langnet/engine/core.py` - 1 model (LatinQueryResult)
  - `langnet/whitakers_words/core.py` - 6 models
  - `langnet/diogenes/core.py` - 9 models
  - `langnet/cologne/core.py` - 3 models
- [x] Migrate in dependency order (start with leaf models)
- [x] Run tests after each migration
- [x] Update AGENTS.md when complete

#### Model Refactoring Strategy
1. Replace `class X(BaseModel)` with `@dataclass class X`
2. Replace `Field(default=None)` with `field(default=None)`
3. Replace `model_dump()` with `cattrs.unstructure()`
4. Replace `model_validate()` with `cattrs.structure()`
5. Update `ORJsonResponse` in `asgi.py` with orjson options:
   - Add `default` callback for types orjson can't serialize (e.g., datetime)
   - Consider `OPT_SORT_KEYS` for consistent output
   - Consider `OPT_UTC_Z` if datetime serialization is needed

### Phase 2b: Reliability Improvements

### Language Coverage
- [ ] **Greek morphology** via CLTK/spacy (currently only diogenes)

### Developer Experience
- [ ] **CLI tool** with subcommands:
  - `langnet query lat benevolens`
  - `langnet langs` (list supported languages)
  - `langnet health` (check backend status)
- [ ] **Interactive mode** for exploring results
- [ ] **Configuration file** for backend URLs
  - [ ] python dotenv tool

### Structured Logging
- [ ] Add structured logging using structlog with logfmt output
- [ ] Restore useful log messages that were removed:
  - `get_whitakers_proc()`: log which whitakers binary is being used
  - `fixup()`: log wordlist transformation statistics
  - `WhitakersWordsChunker.smart_merge()`: log merge collisions (was `OH NO A COLLISION!`)
  - `DiogenesScraper`: log chunk classification, duplicate sense removal
- [ ] Define log levels:
  - DEBUG: parsing steps, chunk classification
  - INFO: backend selection, query initialization
  - WARN: missing optional data, merge conflicts
  - ERROR: failed queries, unavailable backends
- [ ] Add correlation IDs for tracing requests through multiple backends
- [x] Use `pamburus/hl` for colored logfmt output in development
- [ ] Log format example: `ts=2026-01-25T10:00:00Z level=INFO msg="using whitakers binary" path=/home/user/.local/bin/whitakers-words`

#### Diogenes Zombie Process Reaper
The Perl diogenes server leaks threads on certain queries. A sidecar process runs continuously:

- [x] `just sidecar` runs `langnet/diogenes/cli_util.py` in a loop
- [x] Checks every hour for zombie perl processes
- [x] Kills orphaned parent processes with SIGTERM
- [x] Document in README that sidecar should run alongside API server

#### Error Handling Improvements
- [ ] Add health check endpoint `/api/health`
- [ ] Check diogenes connectivity before querying
- [ ] Handle missing CLTK models gracefully
- [ ] Add circuit breaker for failing backends

### Phase 3: Sanskrit Integration

**Status**: Blocked. The `pycdsl` library depends on Cologne's assets which are no longer available.

#### Path Forward: Build Custom CDSL Parser

Once Greek/Latin functionality is complete, implement a native Python CDSL parser:

- [ ] Parse CDSL TEI XML files directly from `~/cdsl_data/`
- [ ] Support MW (Monier-Williams) and AP90 (Apte) dictionaries
- [ ] Implement entry grouping by headword ID
- [ ] Add transliteration support (IAST, HK, Devanagari)
- [ ] Wire to `SanskritCologneLexicon` and `LanguageEngine`
- [ ] Add Sanskrit query endpoint (`/api/q?l=san&s=<word>`)

This approach removes dependency on `pycdsl`.

### Latin Lewis Dictionary Parser

The CLTK `LatinLewisLexicon.lookup()` returns raw dictionary entry text. Parsing this into structured data is significant work:

- [ ] Analyze Lewis entry format: headword, part of speech, etymology, definitions, citations
- [ ] Create `LewisEntry` dataclass model
- [ ] Implement parser with robust handling of edge cases
- [ ] Wire parsed output to `LatinQueryResult` in `ClassicsToolkit.latin_query()`
- [ ] Add comprehensive test coverage for entry variations

## Future Ideas (Backlog)

### Local Data Storage Layer (Post-Implementation)

After core functionality is complete, add polars/duckdb for local knowledge base:

- [ ] **Store derived lexicon data** from CDSL, CLTK, Diogenes, Whitaker's
- [ ] **Schema design**:
  - `words`: term, language, headword, IPA, part_of_speech
  - `senses`: word_id, definition, citations, source_lemma
  - `morphology`: word_id, tags, stems, endings
  - `cognates`: word_id, related_word_id, relationship_type
- [ ] **Cached lookups**: Query local DB before hitting external services
- [ ] **Cross-lexicon queries**: Enable etymology research ("find Latin words with Greek cognates")
- [ ] **Precomputed indexes**: IPA, lemmas, morphological tags for fast search

**Technologies**: duckdb (OLAP queries on CDSL TEI XML, CLTK data), polars (data transformation)

### Performance
- [ ] **Response caching** for common queries
- [x] **Model warming** at startup (avoid cold downloads)
- [ ] **Async backends** for parallel lexicon queries

