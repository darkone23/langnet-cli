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
- [x] **Greek morphology** via CLTK/spacy (grc_odycy_joint_sm model loaded in ClassicsToolkit)

### Structured Logging
- [x] Add structured logging using structlog with logfmt output
- [x] Restore useful log messages that were removed:
  - [x] `get_whitakers_proc()`: log which whitakers binary is being used
  - [x] `fixup()`: log wordlist transformation statistics
  - [x] `WhitakersWordsChunker.smart_merge()`: log merge collisions (was `OH NO A COLLISION!`)
  - [x] `DiogenesScraper`: log chunk classification, duplicate sense removal
- [x] Define log levels:
  - [x] DEBUG: parsing steps, chunk classification
  - [x] INFO: backend selection, query initialization
  - [x] WARN: missing optional data, merge conflicts
  - [x] ERROR: failed queries, unavailable backends
- [x] Use `pamburus/hl` for colored logfmt output in development
  - `hl` command now available
- [x] Log format example: `ts=2026-01-25T10:00:00Z level=INFO msg="using whitakers binary" path=/home/user/.local/bin/whitakers-words`

### Developer Experience
- [x] **CLI tool** (via click) with subcommands:
  - [x] `langnet-cli query lat benevolens`
  - [x] `langnet-cli langs` (list supported languages)
  - [x] `langnet-cli health` (check backend status)
- [x] **Configuration file** for backend URLs
  - [x] python dotenv tool
    - [x] able to specify diogenes endpoint via DIOGENES_URL
    - [x] able to configure log level via LOG_LEVEL

#### Diogenes Zombie Process Reaper
The Perl diogenes server leaks threads on certain queries. The langnet-dg-reaper process runs continuously:

- [x] `just langnet-dg-reaper` runs `langnet/diogenes/cli_util.py` in a loop
- [x] Checks every hour for zombie perl processes
- [x] Kills orphaned parent processes with SIGTERM
- [x] Document in README that langnet-dg-reaper should run alongside API server

#### Error Handling Improvements
- [x] Add health check endpoint `/api/health`
- [x] Check diogenes connectivity before querying (via `--verify` flag)
- [x] Handle missing CLTK models gracefully

### Phase 3: Sanskrit Integration

#### CDSL DuckDB Indexing (COMPLETED)

The native CDSL parser has been implemented, removing the blocked `pycdsl` dependency:

- [x] Parse CDSL TEI XML files directly from `~/cdsl_data/`
- [x] Store results as duckdb database
- [x] Support MW (Monier-Williams) and AP90 (Apte) dictionaries
- [x] Implement entry grouping by headword ID
- [x] Add transliteration support (IAST, HK, Devanagari)
- [x] Wire to `SanskritCologneLexicon` and `LanguageEngine`
- [x] Integrate into Sanskrit query endpoint (`/api/q?l=san&s=<word>`)
- [x] Add diagnostic logging for batch processing

##### CDSL ETL Performance Observations

**Current Bottleneck**: The parallel XML parsing阶段 (ProcessPoolExecutor) completes nearly instantly, but the final DuckDB bulk INSERT is the bottleneck (~35 rows/second).

Typical profile for MW (~70K entries):
```
batch_progress logs: ~2-3 seconds total for ALL batches
indexing_bulk_insert: ~90 minutes for 70K entries (~35 rows/sec)
```

**Root Cause**: DuckDB's `executemany()` with 70K+ records is I/O-bound, not CPU-bound.

##### Future Performance Optimization Opportunities

1. **Divide and Conquer: Sharded Database Merge (RECOMMENDED)**

This approach splits the workload into independent shards that can be processed in parallel, then merged at the end:

**Phase 1: Partition and Build Shards**
- Partition source data by:
  - **Alphabet range**: Assign each worker a letter range (a-e, f-j, k-o, ...)
  - **Hash bucket**: `hash(headword) % num_workers`
  - **Sequential chunks**: Split rows into equal-sized batches
- Each worker:
  1. Receives its partition of rows
  2. Parses XML entries
  3. Writes to its own temporary DuckDB database (`/tmp/shard_{N}.db`)
  4. Returns when complete
- Benefits:
  - No shared memory bottleneck (each process owns its DB)
  - True parallelism (no locking/coordination during writes)
  - Failures isolated to individual shards

**Phase 2: Merge Shards**
- After all shards complete:
  ```python
  # Open main DB and all shard DBs
  main_conn = duckdb.connect(str(output_db))
  for i in range(num_shards):
      shard_conn = duckdb.connect(f"/tmp/shard_{i}.db")

      # Copy data from shard to main
      main_conn.execute("""
          INSERT INTO entries
          SELECT * FROM shard_{i}.entries
      """)
      main_conn.execute("""
          INSERT INTO headwords
          SELECT * FROM shard_{i}.headwords
      """)

      # Close and cleanup shard
      shard_conn.close()
      Path(f"/tmp/shard_{i}.db").unlink()
  ```
- Or use DuckDB's `ATTACH` and `COPY`:
  ```python
  main_conn.execute(f"ATTACH '/tmp/shard_{i}.db' AS shard_{i}")
  main_conn.execute(f"""
      COPY main.entries FROM (
          SELECT * FROM shard_{i}.entries
      )
  """)
  ```

**Phase 3: Optimize and Vacuum**
- Run `VACUUM` to reclaim space after merge
- Rebuild indexes: `PRAGMA reindex`
- Optimize statistics: `ANALYZE`

**Implementation Steps**:
1. Create `build_shard()` function that:
   - Accepts: `shard_id, dict_id, rows_partition, temp_dir`
   - Parses entries for its partition
   - Creates shard database at `{temp_dir}/shard_{shard_id}.db`
   - Returns shard path and entry count

2. Modify `CdslIndexBuilder.build()`:
   - Partition rows by hash/alphabet/sequence
   - Launch workers with `ProcessPoolExecutor`
   - Collect shard paths from workers
   - Merge all shards into final database

3. Add CLI flags:
   - `--shards N`: Number of shards (default: CPU count)
   - `--partition-method`: hash | alphabet | sequential

**Expected Performance Improvement**:
- Current: ~90 min for MW (70K entries) - single-threaded INSERT
- Estimated: ~10-15 min with 8 shards - parallel writes + fast merge
- Memory: Reduced from holding all entries in RAM to shard-sized batches

2. **COPY FROM for Bulk Loading**
   - DuckDB's `COPY` command is 10-100x faster than INSERT
   - Export parsed data to Parquet/CSV, then `COPY INTO table FROM file`
   - Example:
      ```python
      # Write batch to temp Parquet
      duckdf = pl.DataFrame(batch_data)
      duckdf.write_parquet(f"/tmp/batch_{i}.parquet")
      # Bulk load
      conn.execute(f"COPY entries FROM '/tmp/batch_{i}.parquet' (FORMAT PARQUET)")
      ```

3. **Batch INSERT with Transactions**
   - Split bulk insert into smaller transactions (e.g., 10K records per COMMIT)
   - Reduces memory pressure and enables better parallelization

4. **Concurrent INSERT with ThreadPoolExecutor**
   - Open multiple DuckDB connections, insert in parallel
   - Each connection handles separate batches
   - Requires managing transaction boundaries

5. **Streaming XML Parser**
   - Use SAX/iterparse instead of lxml.etree for memory efficiency
   - Process entries as they are read, no full DOM in memory

6. **Pre-sort by lnum**
   - Sort entries by (dict_id, lnum) before INSERT
   - Improves B-tree index maintenance

7. **Disk-based Temporary Tables**
   - `CREATE TEMP TABLE ... ON COMMIT PRESERVE ROWS` for staging
   - Reduces memory footprint for large dictionaries

8. **Profile with DuckDB EXPLAIN ANALYZE**
   - Identify exact hotspots in INSERT execution plan

### Latin Lewis Dictionary Parser

The CLTK `LatinLewisLexicon.lookup()` returns raw dictionary entry text. Parsing this into structured data is significant work:

- [ ] Analyze Lewis entry format: headword, part of speech, etymology, definitions, word family, citations
- [ ] Create `LewisEntry` dataclass model
- [ ] Implement parser with robust handling of edge cases
- [ ] Wire parsed output to `LatinQueryResult` in `ClassicsToolkit.latin_query()`
- [ ] Add comprehensive test coverage for entry variations

## Future Ideas (Backlog)

### Local Data Storage Layer (Post-Implementation)

After core functionality is complete, add polars/duckdb for local knowledge base:

- [ ] **Store derived lexicon data** from CDSL, CLTK, Diogenes, Whitaker's
- [ ] **generic schema design**:
  - `words`: term, language, headword, IPA, part_of_speech
  - `senses`: word_id, definition, citations, source_lemma
  - `morphology`: word_id, tags, stems, endings
  - `cognates`: word_id, related_word_id, relationship_type
- [x] **Cached lookups**: Query local DB before hitting external services
- [ ] **Precomputed indexes**: IPA, lemmas, morphological tags for fast search
- [ ] **Cross-lexicon queries**: Enable etymology research ("find Latin words with Greek cognates")

**Technologies**: duckdb (OLAP queries on CDSL TEI XML, CLTK data), polars (data transformation)

### Performance / Observability
- [x] **Response caching** for common queries
- [x] **Model warming** at startup (avoid cold downloads)
- [ ] **Async backends** for parallel lexicon queries
- [ ] Add correlation IDs for tracing requests through multiple backends
