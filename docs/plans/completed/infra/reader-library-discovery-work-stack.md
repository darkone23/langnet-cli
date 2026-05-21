> Completed implementation record. Moved out of active/ during the 2026-05 documentation overhaul after code/tests confirmed the core slice exists.

# Reader Library Discovery Work Stack

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose reader catalog discovery metadata in shapes that let downstream clients build language-specific library shelves, useful filters, and reliable detail pages without frontend hardcoding.

**Architecture:** Keep the reader catalog as the source of truth. Add read-only storage helpers that summarize existing `works`, `artifacts`, `work_classifications`, `author_classifications`, overlays, and attribution claims. Surface those helpers through `ReaderService` and Click commands using the existing `langnet.reader.v1` payload contract.

**Tech Stack:** DuckDB reader catalogs, Click CLI, `ReaderService`, strict discovery taxonomy helpers, existing reader classification tables, `just test`, `just ruff-check`.

---

## Priority Stack

### P0: Discovery Facets And Shelves

- [x] Add language-scoped `reader groups --language ...` output with group labels, descriptions, work counts, classified work counts, author counts, and ordering metadata.
- [x] Add language-scoped `reader tags --language ...` output with tag labels, descriptions, work counts, classified work counts, author counts, and ordering metadata.
- [x] Add `reader facets --language ...` so the `discovery_groups` and `discovery_tags` facet values are catalog/language-aware when a language is supplied, while preserving global static behavior when no language is supplied.
- [x] Add `reader shelves --language ...` that returns high-level discovery cards built from real classified catalog contents.
- [x] Include `query` objects on shelves, e.g. `{ "group": "medicine", "sort": "group-popularity" }`.
- [x] Include representative `sample_works` on shelves using existing `reader works --group ... --sort group-popularity` semantics.
- [x] Document the JSON contract and CLI examples.

### P1: Discovery Coverage Metadata

- [x] Add `reader coverage --output json` with per-language work, author, segment, token, classified-work, classified-author, and discoverability counts.
- [x] Mark `san`, `grc`, and `lat` as currently supported reader UI languages.
- [x] Distinguish languages merely present in a catalog from languages that have discovery facets and author classifications.
- [x] Document how web clients should use coverage to decide which language tabs to expose.

### P1.5: Fuzzy Encounter Reader Search

- [x] Add `encounter --reader-search-all-candidates` so inline reader search can query every useful encounter candidate instead of only the first one.
- [x] Deduplicate inline reader-search hits by `segment_id` when available, otherwise by `(work_id, citation_path)`.
- [x] Add `matched_query`, `input_query`, `match_type`, and `candidate_rank` metadata to inline reader-search hits.
- [x] Keep action-only mode working when no reader search index is supplied.
- [x] Add a later `reader search --mode fuzzy` or `--match fuzzy` option for standalone expanded search.
- [x] Add Greek ASCII/transliteration expansion cases such as `logos` -> `λόγος` and `andra` -> useful native Greek candidates.
- [x] Add Sanskrit Romanization/source-script expansion where the index supports it.
- [x] Add `reader search-index inspect-query ... --mode fuzzy` for inspectable candidate generation.

### P2: Author And Work Detail Bundles

- [x] Add `reader author <author-id-or-name> --language ... --output json`.
- [x] Add `reader work <work-id-or-urn> --output json`.
- [x] Include canonical/source author identity, attribution claims, generated classification, counts, representative works, and retrieval query hints.
- [x] Keep detail bundles as read-only composition over existing catalog metadata.
- [x] Document stable and provisional fields.

### P3: UI-Safe Source And Edition Labels

- [x] Add source label helpers for work payloads, detail payloads, and shelf samples.
- [x] Provide `source_label`, `edition_label`, and `short_disambiguation_label` fields where source identifiers are available.
- [x] Preserve raw identifiers for routing/debugging.
- [x] Document duplicate-title display guidance.

### P4: Unsupported-Language Script Display Polish

- [x] Improve display metadata for Hebrew and Coptic segments where possible.
- [x] Preserve current support boundary: web reader UX remains focused on `san`, `grc`, and `lat`.
- [x] Document that this is display polish, not full Hebrew/Coptic reader support.

## Implementation Tasks

### Task 1: Storage Summaries For Discovery Groups And Tags

**Files:**
- Modify: `src/langnet/reader/storage.py`
- Test: `tests/test_reader_storage.py`

- [x] Add tests proving group summaries are filtered by language and omit zero-count groups for language-scoped output.
- [x] Add tests proving tag summaries split pipe-delimited tags and count each classified work once per tag.
- [x] Implement `list_discovery_group_summaries(catalog_path, language=None)`.
- [x] Implement `list_discovery_tag_summaries(catalog_path, language=None)`.
- [x] Ensure old catalogs without `work_classifications.discovery_group_id` or `discovery_tags` return empty summaries instead of failing.

### Task 2: Service And CLI Facet Commands

**Files:**
- Modify: `src/langnet/reader/service.py`
- Modify: `src/langnet/cli.py`
- Test: `tests/test_reader_cli.py`

- [x] Add failing CLI tests for `reader groups --language`, `reader tags --language`, and `reader facets --language`.
- [x] Add optional `language` parameters to service payload methods.
- [x] Add `--language` options to the Click commands.
- [x] Preserve current static global output when `--language` is absent.
- [x] Document updated commands in `docs/READER_CLI_HANDOFF.md` and `docs/READER_WEB_CONTRACT.md`.

### Task 3: Discovery Shelves

**Files:**
- Modify: `src/langnet/reader/storage.py`
- Modify: `src/langnet/reader/service.py`
- Modify: `src/langnet/cli.py`
- Test: `tests/test_reader_storage.py`
- Test: `tests/test_reader_cli.py`

- [x] Add tests proving shelves are language-scoped and include counts, query objects, and representative sample works.
- [x] Implement shelf construction from group summaries plus `list_works(... classification_group=..., sort="group-popularity")`.
- [x] Order shelves by useful language-specific priority when known, then by work count and group popularity.
- [x] Add `reader shelves --language ... --limit ... --sample-limit ...`.
- [x] Document shelf payload shape and example web usage.

### Task 4: Coverage Metadata

**Files:**
- Modify: `src/langnet/reader/storage.py`
- Modify: `src/langnet/reader/service.py`
- Modify: `src/langnet/cli.py`
- Test: `tests/test_reader_storage.py`
- Test: `tests/test_reader_cli.py`

- [x] Add tests for per-language coverage using a fixture catalog with classified and unclassified languages.
- [x] Implement `reader_discovery_coverage(catalog_path)`.
- [x] Add `ReaderService.coverage_payload()`.
- [x] Add `reader coverage --output pretty|json`.
- [x] Document how `has_discovery_facets`, `has_author_classifications`, and `supported_reader_language` should be interpreted.

### Task 5: Lower-Stack Detail And Display Followups

**Files:**
- Modify after P0/P1 stabilizes: `src/langnet/reader/storage.py`
- Modify after P0/P1 stabilizes: `src/langnet/reader/service.py`
- Modify after P0/P1 stabilizes: `src/langnet/cli.py`
- Test after P0/P1 stabilizes: `tests/test_reader_storage.py`
- Test after P0/P1 stabilizes: `tests/test_reader_cli.py`

- [x] Design detail bundle fields against real web needs before implementation.
- [x] Add author detail command.
- [x] Add work detail command.
- [x] Add UI-safe source/edition labels.
- [x] Add Hebrew/Coptic display-script polish.

### Task 6: Encounter All-Candidates Reader Search Increment

**Files:**
- Modify: `src/langnet/cli.py`
- Test: `tests/test_cli_encounter_output.py`
- Document: `docs/READER_CLI_HANDOFF.md`
- Document: `docs/READER_WEB_CONTRACT.md`

- [x] Add failing tests proving `--reader-search-all-candidates` searches more than the first candidate.
- [x] Add failing tests proving duplicate hits across candidates collapse to one item.
- [x] Add failing tests proving each hit includes match metadata.
- [x] Add the Click option and request payload field.
- [x] Update `_encounter_reader_search_context()` to loop over candidates when requested.
- [x] Keep the current first-candidate behavior as the default.

## Verification Checklist

- [x] `just test test_reader_storage test_reader_cli`
- [x] `just ruff-check`
- [x] Smoke `reader groups --language grc --output json` against `examples/debug/reader_classics_legacy_full_curated_current/catalog.duckdb`.
- [x] Smoke `reader shelves --language lat --output json` against `examples/debug/reader_classics_legacy_full_curated_current/catalog.duckdb`.
- [x] Smoke `reader shelves --language san --output json` against `examples/debug/reader_sanskrit_full_curated_current/catalog.duckdb`.
- [x] Smoke `reader coverage --output json` against both current debug catalogs.
- [x] Smoke `reader search-index inspect-query --language grc --mode fuzzy logos --output json`.
- [x] Smoke `reader search andra --mode fuzzy` against `examples/debug/reader-search-smoke-grc.lance`.

## Notes

- “Deferred” means lower on this stack, not dropped.
- Facet values must come from the strict taxonomy; generated classifications choose from explicit IDs.
- Shelf cards should represent actual catalog contents, not a static fantasy list.
- Read-only CLI commands should continue using read-only DuckDB connections.
