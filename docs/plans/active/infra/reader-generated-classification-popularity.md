# Reader Generated Classification Popularity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an end-to-end generated metadata path for reader work classification and popularity ranking.

**Architecture:** `reader classification-export` remains the CSV handoff to an external classifier, with extra context fields that help models classify work rows. A new generated-classification loader imports classifier-filled CSV files into a `work_classifications` DuckDB table, and reader work listings join those generated fields back into API/CLI payloads. Popularity sorting is implemented in catalog queries and surfaced through `reader works --sort popularity` plus a convenience `reader popular` command.

**Tech Stack:** Click CLI, DuckDB catalog tables, Polars bulk insertion, Python `csv`, reader service/storage modules, pytest through project `just` commands.

---

## Roles

- @architect: Keep generated metadata semantics explicit: no candidate gating, but keep model/run provenance.
- @coder: Implement TDD slices in loader, storage, service, and CLI.
- @scribe: Update the reader web contract with CSV fields and sync commands.
- @auditor: Review the generated-data trust model and popularity ordering behavior.

## File Structure

- Create `src/langnet/reader/classification.py`: CSV loader and validation for generated classification rows.
- Modify `src/langnet/reader/models.py`: add `ReaderWorkClassification`.
- Modify `src/langnet/reader/storage.py`: add `work_classifications`, registration, joins, and popularity ordering.
- Modify `src/langnet/reader/service.py`: add sync payload and sort plumbing.
- Modify `src/langnet/cli.py`: add sync/popular commands, export fields, and works sort option.
- Modify `docs/READER_WEB_CONTRACT.md`: document generated classification lifecycle.
- Add `tests/test_reader_classification.py`: loader behavior.
- Modify `tests/test_reader_storage.py`: classification persistence and sorting behavior.
- Modify `tests/test_reader_cli.py`: CLI export/sync/popular behavior.

## Tasks

### Task 1: Loader Red Test

**Files:**
- Create: `tests/test_reader_classification.py`
- Create: `src/langnet/reader/classification.py`
- Modify: `src/langnet/reader/models.py`

- [ ] **Step 1: Write failing loader tests**

Add tests that write a classifier-filled CSV under a temporary directory and expect `load_work_classifications()` to return generated metadata objects with:

- `work_id`
- `category`
- `period`
- `date_range`
- `authorship_status`
- integer `popularity_score`
- `popularity_tier`
- `confidence`
- `note`
- `generator_models`
- `generator_run_id`
- `source_file`

Also assert that malformed popularity scores raise `ValueError`.

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
just test test_reader_classification
```

Expected: fail because `langnet.reader.classification` and `ReaderWorkClassification` are missing.

- [ ] **Step 3: Implement minimal loader**

Implement `ReaderWorkClassification` and CSV loading. Treat rows as generated data. Do not require `status`, `accepted`, or review fields.

- [ ] **Step 4: Run focused test and verify GREEN**

Run:

```bash
just test test_reader_classification
```

Expected: pass.

### Task 2: Storage Red/Green

**Files:**
- Modify: `tests/test_reader_storage.py`
- Modify: `src/langnet/reader/storage.py`

- [ ] **Step 1: Write failing storage tests**

Add tests for:

- `register_work_classifications()` persists generated metadata.
- `list_works(..., sort="popularity")` returns higher `popularity_score` first.
- unclassified works remain available and sort after classified works.

- [ ] **Step 2: Run focused test and verify RED**

Run:

```bash
just test test_reader_storage
```

Expected: fail because storage APIs and joined fields are missing.

- [ ] **Step 3: Implement minimal storage**

Add a `work_classifications` table keyed by `work_id`, a registration function that replaces table contents, and joins in `list_works()` and contained-work rows. Add `sort="catalog"` default and `sort="popularity"` ordering.

- [ ] **Step 4: Run focused test and verify GREEN**

Run:

```bash
just test test_reader_storage
```

Expected: pass.

### Task 3: Service And CLI Red/Green

**Files:**
- Modify: `tests/test_reader_cli.py`
- Modify: `src/langnet/reader/service.py`
- Modify: `src/langnet/cli.py`

- [ ] **Step 1: Write failing CLI tests**

Add tests for:

- `reader classification-export` includes word counts and generated-classification columns.
- `reader sync-classifications --classification-csv path.csv --output json` returns `synced_count`.
- `reader popular --language grc --output json` returns works sorted by generated popularity.
- `reader works --sort popularity --output json` matches the same ordering.

- [ ] **Step 2: Run focused test and verify RED**

Run:

```bash
just test test_reader_cli
```

Expected: fail because commands/options are missing.

- [ ] **Step 3: Implement service and CLI**

Add `sync_classifications_payload()`, pass `sort` through `works_payload()`, add `reader sync-classifications`, `reader popular`, and `reader works --sort`.

- [ ] **Step 4: Run focused test and verify GREEN**

Run:

```bash
just test test_reader_cli
```

Expected: pass.

### Task 4: Documentation And Verification

**Files:**
- Modify: `docs/READER_WEB_CONTRACT.md`

- [ ] **Step 1: Update docs**

Document:

- CSV export fields.
- Generated classifier fields.
- `reader sync-classifications`.
- `reader popular`.
- That generated data is immediately usable metadata with model/run provenance, not candidate data.

- [ ] **Step 2: Run lint and focused tests**

Run:

```bash
just ruff-check
just test test_reader_classification test_reader_storage test_reader_cli
```

Expected: pass.

- [ ] **Step 3: Run full fast suite**

Run:

```bash
just test-fast
```

Expected: pass.

## Self-Review

- Spec coverage: export, generated import, DuckDB persistence, popularity sorting, and docs are each mapped to tasks.
- Placeholder scan: no deferred implementation placeholders; the only open work is the explicit task checklist.
- Type consistency: the same `ReaderWorkClassification`, `work_classifications`, `classification_*`, `generator_models`, and `generator_run_id` names are used throughout.
