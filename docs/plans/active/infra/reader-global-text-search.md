# Reader Global Text Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add global corpus text search across reader catalogs, backed by a rebuildable derived search index with language-aware normalization and a CLI/API shape that can later feed the `encounter` tool.

**Architecture:** Keep reader catalog DuckDBs and per-book DuckDBs as the canonical corpus store. Build a separate derived Lance dataset from catalog artifacts and segment rows using DuckDB's `lance` extension. Store both display text and normalized searchable text. Expose index build/status/validation commands, a `reader search` command, and an optional `encounter` integration that surfaces corpus-search actions and, later, inline passage hits.

**Tech Stack:** Click CLI, reader catalog DuckDB, per-book DuckDB segment tables, DuckDB `lance` extension, Lance inverted FTS indexes with BM25-like scores, Python normalization/tokenization helpers, `nose2` tests via project `just` commands.

---

## Roles

- @architect: Keep the search index rebuildable, separate from canonical reader data, and stable enough for web routing.
- @coder: Implement the builder, storage adapter, service payloads, and CLI commands with focused tests.
- @scribe: Document search index lifecycle, query modes, JSON contracts, and encounter integration.
- @auditor: Review normalization semantics, phrase/exact search behavior, performance assumptions, and index/catalog consistency checks.

## Scope

In scope:

- Build a segment-level global search index from one reader catalog.
- Support BM25 keyword search over normalized segment text.
- Preserve user-facing display text and source text separately from search text.
- Filter by language, collection, work, author, canonical author id, discovery group, and discovery tag.
- Return segment hits with score, citation, work metadata, snippet, address-like target fields, and optional context.
- Provide enough CLI shape for web reader and `encounter` integration.

Out of scope for the first implementation:

- Semantic/vector search.
- Cross-catalog federated search in one command.
- Morphological lemmatized search.
- Web UI changes.
- Mutating canonical reader book DuckDBs.

Hybrid/vector search can be added later once lexical search is stable.

## Data Flow

```text
reader catalog.duckdb
  -> artifacts table
  -> per-book DuckDB segments
  -> language normalizer/tokenizer
  -> derived Lance dataset
  -> Lance inverted FTS indexes
  -> DuckDB lance_fts(...)
  -> reader search CLI/service
  -> optional encounter actions/results
```

The search index is a derived artifact. Rebuilding it must not change the reader catalog or book DBs.

## Search Index Row Shape

Each Lance row represents one reader segment.

Required metadata:

```text
search_id
catalog_fingerprint
artifact_id
segment_id
work_id
collection_id
language
title
author
source_author
source_author_id
canonical_author_id
canonical_author_name
cts_work_urn
citation_path
sort_key
work_kind
```

Text fields:

```text
display_text          # learner-facing segment text
source_text           # original/source-ish segment text where available
normalized_text       # current reader normalized text
search_text           # primary normalized search text
search_text_folded    # accent/diacritic/case folded text
token_text            # tokenizer/debug/search fallback text
```

Discovery metadata:

```text
classification_discovery_group_id
classification_discovery_tags
classification_global_popularity_score
classification_group_popularity_score
```

Index metadata:

```text
index_schema_version
normalizer_version
indexed_at
source_artifact_hash
```

Lance FTS indexes:

- `search_text_idx` on `search_text`
- `search_text_folded_idx` on `search_text_folded`
- `token_text_idx` on `token_text`

The first implementation uses DuckDB `lance_fts` and returns BM25-like `_score` values. The FTS indexes preserve positions and stop words so phrase queries can be supported.

## Normalization Contract

The search builder must preserve display text while producing explicit searchable fields. The first implementation should be conservative and inspectable.

Latin:

- Unicode normalize.
- Lowercase.
- Treat punctuation as token boundaries.
- Produce folded variants for common `j/i` and `v/u` search behavior.
- Do not use English stemming.

Greek:

- Unicode normalize.
- Lowercase.
- Normalize final sigma.
- Produce a folded field without accents/breathings.
- Preserve polytonic display text.
- Do not use English stemming.

Sanskrit:

- Unicode normalize.
- Preserve IAST/Devanagari display text.
- Produce IAST-style and folded search forms where possible.
- Support common ASCII user input such as `sankara` matching `Śaṃkara`.
- Devanagari-to-IAST and IAST-to-Devanagari query expansion can be added after the first stable pass.

The CLI must include an inspection command so operators can see exactly what the normalizer emits for a query or segment.

## CLI Contract

### Build

```bash
just cli reader search-index build \
  --catalog examples/debug/reader_sanskrit_full_curated_current/catalog.duckdb \
  --index data/build/reader/search.lance \
  --language san \
  --replace \
  --batch-size 50000
```

Options:

```text
--catalog PATH              reader catalog DuckDB
--index PATH                derived Lance search dataset
--language lat|grc|san      optional language slice
--collection ID             optional collection slice
--replace                   replace existing table/index
--append                    append/update rows for the selected slice
--batch-size N              segment rows per write batch
--limit N                   debug-only segment cap
--output pretty|json
```

JSON summary:

```json
{
  "schema_version": "langnet.reader_search_index.v1",
  "mode": "search-index-build",
  "catalog_path": "...",
  "index_path": "...",
  "summary": {
    "segment_count": 3319944,
    "work_count": 977,
    "language_counts": {"san": 3319944},
    "normalizer_version": "reader-search-normalizer-v1",
    "replaced": true
  }
}
```

### Status

```bash
just cli reader search-index status \
  --index data/build/reader/search.lance \
  --output json
```

Returns table existence, row count, language counts, schema version, normalizer version, index creation state, and source catalog fingerprint.

### Validate

```bash
just cli reader search-index validate \
  --catalog examples/debug/reader_sanskrit_full_curated_current/catalog.duckdb \
  --index data/build/reader/search.lance \
  --output json
```

Validation checks:

- indexed segment count matches catalog artifacts for selected scope;
- all indexed `work_id` values exist in the catalog;
- sample `segment_id` values still exist in book DBs;
- normalizer/index schema versions match supported versions;
- required FTS indexes exist.

### Inspect Normalization

```bash
just cli reader search-index inspect-normalize \
  --language grc \
  "λόγος"
```

Pretty output should show:

```text
display: λόγος
search_text: λόγος
search_text_folded: λογος
token_text: λογος
query_variants: λόγος | λογος
```

### Search

```bash
just cli reader search "arma virumque" \
  --catalog $CATALOG \
  --index data/build/reader/search.lance \
  --language lat \
  --limit 20
```

Additional examples:

```bash
just cli reader search "sankara" \
  --catalog $CATALOG \
  --index data/build/reader/search.lance \
  --language san \
  --mode auto \
  --context 2 \
  --output json

just cli reader search "λόγος" \
  --catalog $CATALOG \
  --index data/build/reader/search.lance \
  --language grc \
  --author-id urn:cts:greekLit:tlg0059 \
  --group philosophy

just cli reader search "πάντα πέτρον κινεῖν" \
  --language grc \
  --mode phrase \
  --field folded
```

Search options:

```text
--catalog PATH
--index PATH
--language lat|grc|san
--collection ID
--work-id ID
--author TEXT
--author-id ID
--group DISCOVERY_GROUP_ID
--tag DISCOVERY_TAG
--mode auto|keyword|phrase|exact
--field auto|display|search|folded
--context N
--limit N
--cursor OFFSET
--output pretty|json
```

JSON result shape:

```json
{
  "schema_version": "langnet.reader_search.v1",
  "mode": "search",
  "catalog_path": "...",
  "index_path": "...",
  "request": {
    "query": "sankara",
    "language": "san",
    "search_mode": "auto",
    "field": "auto"
  },
  "items": [
    {
      "score": 12.4,
      "work_id": "langnet:reader:sanskrit_json:corpus_sa_aitareyopaniSad-comm",
      "collection_id": "sanskrit_json",
      "language": "san",
      "title": "Aitareyopaniṣadbhāṣya",
      "author": "Śaṃkarācārya",
      "canonical_author_id": "urn:cts:langnet:author.san.samkaracarya",
      "cts_work_urn": null,
      "citation_path": "1.3",
      "segment_id": "...",
      "sort_key": 123,
      "text": "...",
      "snippet": "...",
      "context_before": [],
      "context_after": [],
      "target": {
        "reader_command": "reader show",
        "work_ref": "langnet:reader:sanskrit_json:corpus_sa_aitareyopaniSad-comm",
        "segment": "1.3"
      }
    }
  ],
  "pagination": {
    "next_cursor": "20",
    "prev_cursor": null,
    "limit": 20
  }
}
```

## Encounter Integration

Stage 1 should add action-only integration. Dictionary lookup remains primary.

```bash
just cli encounter grc logos all --include-reader-search
```

JSON addition:

```json
"reader_search": {
  "query_candidates": ["λόγος", "logos"],
  "actions": [
    {
      "label": "Search corpus for λόγος",
      "command": "reader search",
      "target": {
        "query": "λόγος",
        "language": "grc"
      }
    }
  ]
}
```

Stage 2 can include top corpus hits inline when an index is supplied.

```bash
just cli encounter grc logos all \
  --reader-search-index data/build/reader/search.lance \
  --reader-search-limit 5
```

Possible encounter options:

```text
--include-reader-search/--no-include-reader-search
--reader-search-index PATH
--reader-search-limit N
--reader-search-context N
--reader-search-all-candidates/--no-reader-search-all-candidates
```

The inline `reader_search.items` shape reuses `reader search` result items and,
when all-candidates mode is enabled, adds `matched_query`, `input_query`,
`match_type`, and `candidate_rank`.

## File Structure

Create:

- `src/langnet/reader/search_index.py`
  - DuckDB Lance index build/status/validate/search adapter.
- `src/langnet/reader/search_normalization.py`
  - language-aware text and query normalization.
- `tests/test_reader_search_normalization.py`
- `tests/test_reader_search_index.py`

Modify:

- `src/langnet/reader/service.py`
  - add search-index and search payload methods.
- `src/langnet/reader/storage.py`
  - add helpers for streaming indexed segment rows and decorating hits, if needed.
- `src/langnet/cli.py`
  - add `reader search-index ...`, `reader search`, and encounter options.
- `docs/READER_WEB_CONTRACT.md`
  - document search CLI/API JSON.
- `docs/READER_CLI_HANDOFF.md`
  - add operator commands.

## Tasks

### Task 1: Normalization Contract

- [x] **Step 1: Write failing tests**

Create `tests/test_reader_search_normalization.py` covering:

- Latin lowercasing and `v/u`, `j/i` variants.
- Greek accent/breathing folding and final sigma handling.
- Sanskrit folded matching for `Śaṃkara`, `samkara`, and `sankara`.
- Punctuation as token boundaries.

Run:

```bash
just test test_reader_search_normalization
```

Expected: fail because module does not exist.

- [x] **Step 2: Implement normalizer**

Create `src/langnet/reader/search_normalization.py` with:

```python
normalize_segment_for_search(language: str, text: str) -> ReaderSearchText
normalize_query_for_search(language: str, query: str) -> ReaderSearchQuery
```

Return display/search/folded/token/query-variant fields.

- [x] **Step 3: Verify**

Run:

```bash
just test test_reader_search_normalization
```

Expected: pass.

### Task 2: Search Index Builder

- [x] **Step 1: Write failing builder tests**

Create `tests/test_reader_search_index.py` with a tiny fixture catalog containing Latin, Greek, and Sanskrit segment rows. Assert that `build_reader_search_index()` writes a searchable Lance dataset with expected normalized fields and metadata.

Run:

```bash
just test test_reader_search_index
```

Expected: fail because builder does not exist.

- [x] **Step 2: Implement builder**

Create `src/langnet/reader/search_index.py` with:

```python
build_reader_search_index(...)
reader_search_index_status(...)
validate_reader_search_index(...)
```

The builder should stream catalog artifacts, read book DB segments in batches, attach work/author/discovery metadata, normalize text, and write LanceDB rows.

- [x] **Step 3: Add lexical index creation**

Create Lance inverted FTS indexes on `search_text`, `search_text_folded`, and `token_text`.

- [x] **Step 4: Verify**

Run:

```bash
just test test_reader_search_index
```

Expected: pass.

### Task 3: Search Query Service

- [x] **Step 1: Write failing search tests**

Extend `tests/test_reader_search_index.py` to assert:

- keyword search returns expected segment hits;
- folded Greek search matches accented text;
- Sanskrit `sankara` matches `Śaṃkara`;
- metadata filters restrict results;
- context windows are returned when requested.

- [x] **Step 2: Implement search API**

Add:

```python
search_reader_segments(...)
```

Support `mode`, `field`, filters, limit/cursor, and context lookup. Context rows should come from the canonical book DBs using `work_id`, `sort_key`, and `context`.

- [x] **Step 3: Verify**

Run:

```bash
just test test_reader_search_index
```

Expected: pass.

### Task 4: CLI Commands

- [x] **Step 1: Write failing CLI tests**

Extend `tests/test_reader_cli.py` for:

- `reader search-index build --output json`;
- `reader search-index status --output json`;
- `reader search-index validate --output json`;
- `reader search-index inspect-normalize`;
- `reader search ... --output json`;
- pretty `reader search` output.

- [x] **Step 2: Implement CLI**

Add a `reader search-index` command group and a `reader search` command in `src/langnet/cli.py`.

- [x] **Step 3: Verify**

Run:

```bash
just test test_reader_cli
```

Expected: pass.

### Task 5: Encounter Action Integration

- [x] **Step 1: Write failing encounter tests**

Add tests that `encounter --include-reader-search --output json` includes action-only `reader_search` metadata with query candidates, without requiring an index.

- [x] **Step 2: Implement action-only integration**

Generate language-aware query candidates from the encounter input, reduction output, and preferred lemmas already computed by encounter. Add actions to JSON only; keep pretty output compact.

- [x] **Step 3: Verify**

Run:

```bash
just test test_cli_encounter_output
```

Expected: pass.

### Task 6: Encounter Inline Search Hits

- [x] **Step 1: Write failing tests**

Add fixture search index tests asserting that `encounter --reader-search-index ... --reader-search-limit 3 --output json` includes `reader_search.items`.

- [x] **Step 2: Implement optional inline search**

When `--reader-search-index` is supplied, run `search_reader_segments()` using the best query candidates and include compact hit items.

- [x] **Step 3: Verify**

Run:

```bash
just test test_cli_encounter_output test_reader_search_index
```

Expected: pass.

### Task 7: Documentation And Operator Handoff

- [x] **Step 1: Update docs**

Update:

- `docs/READER_WEB_CONTRACT.md`
- `docs/READER_CLI_HANDOFF.md`

Document:

- index build lifecycle;
- derived-artifact semantics;
- CLI commands;
- JSON contracts;
- normalization caveats;
- encounter integration.

- [x] **Step 2: Final verification**

Run:

```bash
just ruff-check
just test test_reader_search_normalization test_reader_search_index test_reader_cli test_cli_encounter_output
```

Expected: pass.

## Open Questions

- Should the first promoted index be one per catalog or one per language?
- Should the default `reader search` require `--index`, or should it discover `data/build/reader/search.lance`?
- Should phrase search default to folded text or display text?
- Should Greek and Sanskrit query expansion be returned in JSON for web UI transparency?
- Should search results include work-map node membership when table-of-contents data exists?

## Recommended First Milestone

Implement through Task 4 first: BM25-only global segment search with build/status/validate/search CLI. Then add encounter action-only integration as the second milestone. Inline encounter passage hits should wait until the standalone `reader search` contract is stable.
