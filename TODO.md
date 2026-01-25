# TODO

## Current Roadmap

### Phase 1: API Completion (High Priority)

#### Complete asgi.py Implementation
The `langnet/asgi.py` is currently a stub returning "hello from langnet-api". It needs to:
- [ ] Accept HTTP requests at `/api/q?l=<lang>&s=<word>`
- [ ] Validate language parameter (lat, grc, san)
- [ ] Validate word parameter (non-empty string)
- [ ] Call `LanguageEngine.handle_query(lang, word)`
- [ ] Return JSON response with proper error handling
- [ ] Use `ORJSONResponse` for efficient JSON serialization

#### Implement Query Endpoints by Language
- [ ] **Latin**: Aggregate diogenes (lexicon) + whitakers (morphology) + CLTK (Lewis lexicon)
- [ ] **Greek**: Return diogenes results (lexicon + morphology)
- [ ] **Sanskrit**: Return CDSL results (currently returns placeholders)

### Phase 2: Code Style

#### Migrate from Pydantic to cattrs
Pydantic is being phased out in favor of Python's `dataclass` + `cattrs`:

- [ ] Add `cattrs` to pyproject.toml dependencies
- [ ] Audit all Pydantic models in:
  - `langnet/engine/core.py` - 1 model (LatinQueryResult)
  - `langnet/whitakers_words/core.py` - 6 models
  - `langnet/diogenes/core.py` - 9 models
  - `langnet/cologne/core.py` - 3 models
- [ ] Migrate in dependency order (start with leaf models)
- [ ] Run tests after each migration
- [ ] Update AGENTS.md when complete

#### Model Refactoring Strategy
1. Replace `class X(BaseModel)` with `@dataclass class X`
2. Replace `Field(default=None)` with `field(default=None)`
3. Replace `model_dump()` with `cattrs.unstructure()`
4. Replace `model_validate()` with `cattrs.structure()`

### Phase 2b: Reliability Improvements

### Language Coverage
- [ ] **Greek morphology** via CLTK (currently only diogenes)

### Developer Experience
- [ ] **CLI tool** with subcommands:
  - `langnet query lat benevolens`
  - `langnet langs` (list supported languages)
  - `langnet health` (check backend status)
- [ ] **Interactive mode** for exploring results
- [ ] **Configuration file** for backend URLs
  - [ ] python dotenv tool

### Performance
- [ ] **Response caching** for common queries
- [ ] **Model warming** at startup (avoid cold downloads)
- [ ] **Async backends** for parallel lexicon queries

#### Diogenes Zombie Process Reaper
The Perl diogenes server leaks threads on certain queries. A sidecar process runs continuously:

- [x] `just sidecar` runs `langnet/diogenes/cli_util.py` in a loop
- [x] Checks every hour for zombie perl processes
- [x] Kills orphaned parent processes with SIGTERM
- [ ] Document in README that sidecar should run alongside API server

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

This approach removes dependency on `pycdsl`.

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
