# Reader Source-Backed Enrichment Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Status:** COMPLETED 2026-06-19

**Goal:** Integrate Perseus Catalog subject metadata and Sanskrit DCS corpus metadata into the reader catalog so generated classification/popularity metadata is grounded in source-backed evidence.

**Recommendation:** Keep three layers separate:

1. **Source-backed evidence:** factual metadata imported from Perseus Catalog, DCS local data, and DCS corpus tables.
2. **Deterministic normalization:** rules that map source labels into reader classifier context fields and known scope hints.
3. **Generated metadata:** LLM-synthesized classification, popularity, period, authorship status, and notes, with model/run provenance.

Use `metadata_overlays` only for fields that correct display metadata (`author`, `author_id`, `title`, `language`, `cts_work_urn`). Use `source_metadata` for subject membership, period labels, source classifications, links, and other evidence fields.

---

## Roles

- @architect: Keep source-backed assertions distinct from generated judgments.
- @coder: Implement importer, storage, export-context, and CLI slices with tests.
- @scribe: Document provenance, citation, and regeneration lifecycle.
- @auditor: Review source/generation boundaries and failure modes.

## Inputs

### Perseus Catalog

Discovery:

```text
https://catalog.perseus.org/catalog/facet/subjects?f%5Bexp_language%5D%5B%5D=lat&per_page=100&sort=auth_name+asc%2C+work_title+asc
https://catalog.perseus.org/catalog/facet/subjects?f%5Bexp_language%5D%5B%5D=grc&per_page=100&sort=auth_name+asc%2C+work_title+asc
```

Subject result pattern:

```text
https://catalog.perseus.org/?f%5Bexp_language%5D%5B%5D={lat|grc}&f%5Bsubjects%5D%5B%5D={urlencoded-subject}&per_page=100&sort=auth_name+asc%2C+work_title+asc
```

Seed subjects are listed in:

```text
examples/debug/perseus-catalog-subject-url-plan-2026-05-16.md
```

### DCS

Public pages:

```text
http://www.sanskrit-linguistics.org/dcs/index.php
http://www.sanskrit-linguistics.org/dcs/index.php?contents=texte
```

Local data:

```text
/home/nixos/Classics-Data/sanskrit/dcs/data/conllu
/home/nixos/Classics-Data/sanskrit/dcs/data/conllu/lookup/chapter-info.xml
```

DCS corpus metadata table fields:

```text
Text, Author, Time slot, Subject, Completed, Show, Bib., Dict., Freq.
```

Research note:

```text
examples/debug/dcs-overlay-source-note-2026-05-16.md
```

## File Structure

- Create `src/langnet/reader/source_enrichment.py`
  - Parse Perseus harvested records and DCS corpus/lookup records into normalized evidence rows.
- Modify `src/langnet/reader/storage.py`
  - Register source-backed evidence rows without replacing unrelated source metadata.
- Modify `src/langnet/reader/service.py`
  - Add a work-level source metadata summary used by classification export.
- Modify `src/langnet/cli.py`
  - Add CLI entry points for source enrichment import/export if not handled through databuild.
- Modify `src/langnet/reader/bulk_classification.py`
  - Include compact evidence fields in classifier payload rows.
- Modify `docs/READER_WEB_CONTRACT.md`
  - Document source-backed evidence and generated classification lifecycle.
- Tests:
  - Add `tests/test_reader_source_enrichment.py`.
  - Extend `tests/test_reader_bulk_classification.py`.
  - Extend `tests/test_reader_cli.py` or `tests/test_reader_storage.py`.

## Completed Baseline

The source evidence model, Perseus/DCS import paths, source metadata storage,
classification export context, and bulk-classifier prompt integration are in
place. This active plan now tracks only the remaining enrichment/regeneration
work.

## Remaining Work

1. Emit candidate metadata overlays only when Perseus provides a display-field
   correction. Completed 2026-06-19.
   - `sync-source-enrichment` now reports candidate overlays for direct display
     corrections such as `author`, `language`, or `cts_work_urn`.
   - Perseus subject membership, dates, editors, translators, and catalog URLs
     remain source metadata, not overlays.
2. Feed DCS chapter structure into work-map sync where it is reliable.
   Completed 2026-06-19 as candidate emission.
   - `sync-source-enrichment --dcs-chapter-info` now reports candidate native
     work-map chapter nodes for complete DCS chapter rows that match current
     `sanskrit_dcs` catalog works.
   - The command does not write those candidates into `work_map_nodes`, because
     the current work-map storage sync is replacement-oriented and curated
     review should remain the applying step.
3. Re-run classification for affected languages using the enriched context.
   Completed up to the provider boundary 2026-06-19.
   - Fresh source-enriched classification input CSVs were exported for Greek,
     Latin, and Sanskrit under `examples/debug/`.
   - A fresh paid/provider model generation run was deliberately split to
     `docs/plans/todo/infra/reader-source-enrichment-provider-classification-rerun.md`.
4. Sync generated classifications into the catalog. Completed 2026-06-19.
   - Existing normalized generated classification CSVs for Greek, Latin, and
     Sanskrit were merged into `data/build/reader/catalog.duckdb`.
5. Spot-check. Completed 2026-06-19:
   - popular Greek medical texts;
   - Latin grammar texts by scope popularity;
   - Sanskrit Ayurveda/Kosha/Paniniya/Vedic works.

## Closeout Evidence

- `sync-source-enrichment --dcs-chapter-info` imported 78,665 DCS chapter
  metadata rows and emitted 15,733 candidate work-map nodes.
- Source-enriched classification inputs were exported:
  - `examples/debug/reader-classification-export-grc-source-enriched-2026-06-19.csv`
  - `examples/debug/reader-classification-export-lat-source-enriched-2026-06-19.csv`
  - `examples/debug/reader-classification-export-san-source-enriched-2026-06-19.csv`
- Existing generated classification rows were merged:
  - Greek: 100 rows
  - Latin: 100 rows
  - Sanskrit: 100 rows
- Spot checks returned expected rows for Greek Medicine, Latin Grammar,
  Sanskrit Ayurveda, Sanskrit Grammar/Paniniya, Sanskrit Vedic Texts, and
  Sanskrit Lexicography/Kosha.

## Self-Review

- Source-backed facts and generated judgments are separate.
- Overlays remain reserved for display metadata corrections.
- Perseus is language-filtered to avoid mixed Latin/Greek subject pages.
- DCS corpus metadata is treated as first-class evidence for Sanskrit classification.
- The plan supports current workflows: catalog enrichment, classifier export, generated CSV sync, and reader `popular` queries.
