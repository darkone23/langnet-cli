# Reader Source-Backed Enrichment Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

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

## Task 1: Source Evidence Model

- [x] Add a normalized source evidence dataclass or mapping convention for:
  - `collection_id`
  - `subject_kind`
  - `subject_id`
  - `key`
  - `value`
  - `source_path`
  - source citation/provenance fields where applicable.
- [x] Ensure source rows can represent:
  - Perseus subject membership and catalog URLs.
  - Perseus series/editor/year metadata when useful.
  - DCS author, time slot, subject, and completion/link flags.
  - DCS chapter metadata from `chapter-info.xml`.

## Task 2: Perseus Catalog Harvester

- [x] Implement a parser for saved or fetched Perseus Catalog result pages.
- [x] Extract title, CTS edition URN, work URN, author, editor/translator, year, language, subject, and source URL.
- [x] Match local works by `cts_work_urn`, then by normalized `source_id`.
- [x] Register subject membership as `source_metadata`.
- [ ] Emit candidate metadata overlays only when Perseus provides a field correction.

## Task 3: DCS Corpus Metadata Importer

- [x] Parse the DCS corpus table export into rows keyed by DCS text name.
- [x] Match rows to `sanskrit_dcs` works by title/source id/local path.
- [x] Register:
  - `dcs_author`
  - `dcs_time_slot`
  - `dcs_subject`
  - `dcs_completed`
  - `dcs_has_show`
  - `dcs_has_bib`
  - `dcs_has_dict`
  - `dcs_has_freq`
- [x] Parse `chapter-info.xml` and register chapter id/order/time-slot metadata.
- [ ] Feed chapter structure into work-map sync where it is reliable.

## Task 4: Classifier Context Integration

- [x] Extend `reader classification-export` with a compact `source_metadata_summary` field.
- [x] Include:
  - high-value source subjects;
  - DCS author/time-slot/subject;
  - Perseus subject/series hints;
  - source URL labels only when needed for provenance.
- [x] Update the bulk classifier prompt to treat source-backed context as evidence and generated fields as synthesis.
- [x] Preserve deterministic shuffle batching.

## Task 5: Full Regeneration Lifecycle

- [ ] Let the current Sanskrit/Latin classifier runs finish as a baseline.
- [x] Import Perseus and DCS source-backed evidence.
- [x] Re-export classification CSVs with enriched context.
- [ ] Re-run classification for affected languages.
- [ ] Sync generated classifications into the catalog.
- [ ] Spot-check:
  - popular Greek medical texts;
  - Latin grammar texts by scope popularity;
  - Sanskrit Ayurveda/Kosha/Paniniya/Vedic works.

## Self-Review

- Source-backed facts and generated judgments are separate.
- Overlays remain reserved for display metadata corrections.
- Perseus is language-filtered to avoid mixed Latin/Greek subject pages.
- DCS corpus metadata is treated as first-class evidence for Sanskrit classification.
- The plan supports current workflows: catalog enrichment, classifier export, generated CSV sync, and reader `popular` queries.
