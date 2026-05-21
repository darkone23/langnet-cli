> Completed implementation record. Moved out of active/ during the 2026-05 documentation overhaul after code/tests confirmed the core slice exists.

# Reader Corpus Metrics And Work Maps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrich the reader corpus catalog with research-backed metadata for word/token counts and table-of-contents style work maps.

**Architecture:** Keep fast aggregate metadata in the catalog DuckDB and keep full text reads in per-book DuckDB files. Add curated YAML work-map data under `data/curated/reader_work_maps/`, import accepted map nodes into catalog tables during databuild, and expose a `reader map <work-ref>` command that returns native, curated, or inferred structure with provenance and confidence.

**Tech Stack:** Python dataclasses, DuckDB catalog/book artifacts, Click CLI, small project-local YAML readers, `nose2` tests via `just test`.

---

## Scope

This plan covers two connected corpus-enrichment features:

- Catalog-level word-count style metrics exposed as `word_count`, backed by the existing `artifacts.token_count` field and labeled with `word_count_method`.
- A work-map/ToC layer that can represent known structure such as Bhagavadgītā chapter names and ranges while remaining honest about provenance.

The first implementation should be deterministic. Curated and native map nodes are in scope. Heuristic map inference can be added as a later phase, but any inferred node must carry `provenance = "inferred"` and low/medium confidence.

## Files

- Modify: `src/langnet/reader/models.py`
  - Add `ReaderWorkMapNode`.
- Modify: `src/langnet/reader/storage.py`
  - Add `work_map_nodes` catalog table.
  - Register curated nodes.
  - Aggregate `word_count` for collections, authors, works, contained works, and reader summary.
  - Add `work_map_for_work()`.
- Create: `src/langnet/reader/work_map.py`
  - Load curated work-map YAML files.
  - Validate required fields and accepted status.
- Modify: `src/langnet/reader/builder.py`
  - Load curated map nodes from `data/curated/reader_work_maps`.
  - Register them during catalog build.
- Modify: `src/langnet/cli_databuild.py`
  - Add `--work-map-dir`, defaulting to `data/curated/reader_work_maps`.
- Modify: `src/langnet/reader/service.py`
  - Add `map_payload(work_ref)`.
- Modify: `src/langnet/cli.py`
  - Add `reader map <work-ref>`.
- Create: `data/curated/reader_work_maps/sanskrit/bhagavadgita.yaml`
  - Add accepted curated chapter map for the 18 Bhagavadgītā chapters.
- Modify: `docs/READER_WEB_CONTRACT.md`
  - Document `word_count`, `word_count_method`, and `reader map`.
- Test: `tests/test_reader_storage.py`
  - Aggregates word counts for works/authors/collections and contained works.
  - Reads map nodes for a work.
- Test: `tests/test_reader_cli.py`
  - Verifies `reader map` JSON output.
- Test: `tests/test_reader_work_map.py`
  - Verifies curated YAML loading and validation.

## Task 1: Word Counts In Catalog Responses

- [ ] **Step 1: Write failing storage tests**

Add tests that fixture two artifacts with different `token_count` values and assert:

- `list_collections()` includes `word_count`.
- `list_works()` includes `word_count` and `word_count_method = "whitespace_tokens"`.
- `list_author_index()` includes aggregate `word_count`.
- `reader_summary()` includes aggregate `word_count`.

Run:

```bash
just test test_reader_storage
```

Expected: FAIL because `word_count` fields are absent.

- [ ] **Step 2: Implement catalog aggregate joins**

In `src/langnet/reader/storage.py`, aggregate from `artifacts` by `work_id`:

```sql
SELECT work_id,
       COALESCE(SUM(segment_count), 0) AS segment_count,
       COALESCE(SUM(token_count), 0) AS word_count
FROM artifacts
GROUP BY work_id
```

Use this aggregate in collection, work, author, and summary queries. Return:

```python
"word_count": int(row.get("word_count") or 0),
"word_count_method": "whitespace_tokens",
```

- [ ] **Step 3: Verify focused tests**

Run:

```bash
just test test_reader_storage
```

Expected: PASS.

## Task 2: Curated Work Map Data Model

- [ ] **Step 1: Write failing parser tests**

Create `tests/test_reader_work_map.py` with a temporary YAML file:

```yaml
work_maps:
  - work_id: "urn:cts:sanskritLit:mbh.bhg"
    node_id: "bhg-01"
    parent_node_id: ""
    level: 1
    kind: "chapter"
    label: "Arjuna Viṣāda Yoga"
    native_label: "अर्जुनविषादयोग"
    ordinal: 1
    start_citation: "230573_1"
    end_citation: "230646"
    provenance: "curated"
    confidence: "high"
    status: "accepted"
    note: "Fixture chapter."
    evidence:
      - source_type: "source-root"
        citation: "fixture"
        label: "fixture"
```

Assert the loader returns one accepted node and rejects missing evidence.

Run:

```bash
just test test_reader_work_map
```

Expected: FAIL because `langnet.reader.work_map` does not exist.

- [ ] **Step 2: Implement `ReaderWorkMapNode` and loader**

Create a focused YAML reader matching the existing curated metadata loaders. Support required keys:

```python
work_id, node_id, level, kind, label, ordinal,
start_citation, end_citation, provenance, confidence, status, note, evidence
```

Optional keys:

```python
parent_node_id, native_label, source_file
```

Accepted provenance values:

```python
native, curated, inferred
```

Accepted confidence values:

```python
high, medium, low
```

- [ ] **Step 3: Verify parser tests**

Run:

```bash
just test test_reader_work_map
```

Expected: PASS.

## Task 3: Register And Query Work Maps

- [ ] **Step 1: Write failing storage tests**

In `tests/test_reader_storage.py`, register a fixture work-map node and assert `work_map_for_work(catalog_path, work_ref)` returns:

```python
{
    "work_id": "...",
    "node_id": "bhg-01",
    "kind": "chapter",
    "label": "Arjuna Viṣāda Yoga",
    "start_citation": "start",
    "end_citation": "end",
    "word_count": 10,
    "word_count_method": "whitespace_tokens",
    "provenance": "curated",
    "confidence": "high",
}
```

For contained works, resolve `work_ref` through the contained-work parent and calculate node word counts from the node citation range.

Run:

```bash
just test test_reader_storage
```

Expected: FAIL because storage registration/query functions are absent.

- [ ] **Step 2: Add catalog table and registration**

Add `work_map_nodes` to catalog schema:

```sql
CREATE TABLE IF NOT EXISTS work_map_nodes (
    work_id VARCHAR NOT NULL,
    node_id VARCHAR NOT NULL,
    parent_node_id VARCHAR,
    level INTEGER NOT NULL,
    kind VARCHAR NOT NULL,
    label TEXT NOT NULL,
    native_label TEXT,
    ordinal INTEGER NOT NULL,
    start_citation VARCHAR NOT NULL,
    end_citation VARCHAR NOT NULL,
    provenance VARCHAR NOT NULL,
    confidence VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    note TEXT NOT NULL,
    source_file VARCHAR NOT NULL,
    evidence_source_type VARCHAR NOT NULL,
    evidence_citation TEXT NOT NULL,
    evidence_label TEXT NOT NULL,
    evidence_retrieved_at VARCHAR
);
```

Add `register_work_map_nodes()` and `work_map_for_work()`.

- [ ] **Step 3: Verify storage tests**

Run:

```bash
just test test_reader_storage
```

Expected: PASS.

## Task 4: CLI And Service Surface

- [ ] **Step 1: Write failing CLI test**

In `tests/test_reader_cli.py`, create a fixture catalog with a map node and assert:

```bash
just cli reader --catalog <catalog> map <work-ref> --output json
```

returns:

```json
{
  "schema_version": "langnet.reader.v1",
  "mode": "map",
  "items": [
    {
      "kind": "chapter",
      "label": "Arjuna Viṣāda Yoga",
      "word_count_method": "whitespace_tokens"
    }
  ]
}
```

Run:

```bash
just test test_reader_cli
```

Expected: FAIL because the command is absent.

- [ ] **Step 2: Implement service and CLI**

Add `ReaderService.map_payload(work_ref)` and `reader map` in `src/langnet/cli.py`.

- [ ] **Step 3: Verify CLI tests**

Run:

```bash
just test test_reader_cli
```

Expected: PASS.

## Task 5: Databuild Sync And Bhagavadgītā Seed Curation

- [ ] **Step 1: Write failing databuild/loader integration test**

Use a temporary curated `reader_work_maps` directory and assert a databuild registers accepted nodes.

Run:

```bash
just test test_reader_databuild test_reader_work_map
```

Expected: FAIL until builder registration is wired.

- [ ] **Step 2: Wire builder config**

Add `work_map_dir` to reader databuild config and register accepted nodes after catalog creation.

- [ ] **Step 3: Add seed Bhagavadgītā map**

Create `data/curated/reader_work_maps/sanskrit/bhagavadgita.yaml` with the 18 accepted chapter names and DCS citation ranges. Preserve evidence and note that DCS sentence ids are the current address surface.

- [ ] **Step 4: Verify focused and fast suites**

Run:

```bash
just test test_reader_work_map test_reader_storage test_reader_cli
just ruff-check
just test-fast
```

Expected: all pass.

## Acceptance Criteria

- `reader summary` exposes total `word_count`.
- `reader collections` exposes per-corpus `word_count`.
- `reader authors` and `reader author-sections` expose aggregate `word_count`.
- `reader works` exposes per-work `word_count`.
- `reader map <work-ref>` exposes ToC/map nodes with labels, ranges, counts, provenance, confidence, and evidence-backed source file metadata.
- The Bhagavadgītā has a curated 18-chapter seed map.
- All new metadata is synced through databuild from curated project data, not hard-coded Python conditionals.
