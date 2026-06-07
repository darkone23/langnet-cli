# Rebuilding Reader Sources

This document explains how LangNet's reader corpus is assembled, what kinds of data participate in the rebuild, and what to regenerate after adding or changing source texts.

## Mental Model

The reader is built from several layers:

- Upstream source texts: TEI/XML, HTML, plain text, EPUB, OCR derivatives, PDFs, and corpus-specific data files.
- Source manifests: provenance records for acquired external texts and large source material.
- Reader catalog build: DuckDB catalog tables plus per-work book artifacts.
- Curated data: human-reviewed overlays, aliases, attributions, citation maps, work maps, contained works, and didactic search concepts.
- Generated data: model-assisted classifications and popularity/shelf metadata.
- Reference exports: checked-in TSV snapshots that let humans inspect what was imported.
- UI/API surfaces: `/reader`, `/library`, `/api/reader`, and CLI reader commands.

The catalog should be treated as a rebuildable product of source data, curated overlays, and generated metadata. It is not the only record of provenance.

## Source Texts

Source texts are the upstream material we transform into reader works.

Current source families include:

- Perseus/TLG/PHI/First1KGreek style classical corpora.
- OpenGreekAndLatin directories.
- Sanskrit corpora and JSON/text sources.
- Future electronic text sources such as Latin Library, Archive.org derivatives, Esoteric Archives Bruno pages, Project Gutenberg, OCR/PDF outputs, and other mirrored/downloaded sources.

Source text quality varies. LangNet reader texts are electronic reading editions/source witnesses, not critical editions. Some are clean; some need emendation, segmentation, or OCR correction.

## Source Manifests

Source manifests are planned as the durable provenance layer for acquired external material.

They should record:

- Source id.
- Homepage/source URL.
- Retrieval date.
- Retrieval method.
- Raw local path or external storage path.
- Selected derivative file, when applicable.
- Rights/usage note.
- Quality status.
- Known authors/works.
- Checksums when available.
- Notes about OCR, segmentation, or cleanup needs.

Recommended future location:

```text
data/sources_external/<source_family>/<source_id>/manifest.yaml
```

Large raw files do not necessarily belong in Git. The manifest should be committed even when raw source material lives on mounted storage.

## Reader Catalog Build

The reader build produces:

- `data/build/reader/catalog.duckdb`
- `data/build/reader/books/**.duckdb`
- `data/build/reader/search.lance`

The catalog contains source, work, edition, artifact, alias, metadata, classification, and structure tables.

Important source/provenance tables include:

- `works`
- `editions`
- `artifacts`
- `source_files`
- `source_metadata`
- `source_witnesses`
- `work_relations`

Important reader structure/metadata tables include:

- `aliases`
- `metadata_overlays`
- `metadata_attributions`
- `contained_works`
- `work_map_nodes`
- `division_metadata`
- `citation_maps`
- `work_classifications`
- `author_classifications`

## Curated Data

Curated data is human-reviewed data that should be preserved and reapplied after rebuilds.

Current curated roots include:

- `data/curated/reader_aliases/`
- `data/curated/reader_attributions/`
- `data/curated/reader_citation_maps/`
- `data/curated/reader_contained_works/`
- `data/curated/reader_division_metadata/`
- `data/curated/reader_metadata/`
- `data/curated/reader_search/`
- `data/curated/reader_work_maps/`

Curated data answers questions like:

- What aliases should resolve to this work?
- Which author attribution is traditional, source-backed, uncertain, or translated?
- What canonical citation references should resolve?
- What are the traditional divisions of this work?
- Which contained works should be surfaced as independent didactic units?
- Which pedagogical concepts should improve reader search?

Curated data should not be overwritten by generated classifier output.

## Generated Data

Generated data is model-assisted metadata, usually stored as CSV under:

```text
data/generated/reader_classifications/
```

It currently covers:

- Work discovery classification.
- Primary shelf/group placement.
- Discovery tags.
- Popularity scores and tiers.
- Period/date/category/status notes.
- Author/agent classification.
- Author historicity, region, period, and prominence.

Generated data is useful for discovery but should preserve model/run provenance.

The generated work classification loop is:

```bash
just cli reader classification-export --language lat --path /tmp/lat-classification-input.csv

just cli reader classify-works \
  --input-csv /tmp/lat-classification-input.csv \
  --output-csv data/generated/reader_classifications/<date>/discovery/latin-generated.csv \
  --batch-size 50 \
  --raw-response-dir examples/debug/reader-classifier-raw/lat \
  --output json

just cli reader --catalog data/build/reader/catalog.duckdb sync-classifications \
  --classification-csv data/generated/reader_classifications/<date>/discovery/latin-generated.csv \
  --merge \
  --output json

just cli reader --catalog data/build/reader/catalog.duckdb prune-stale-classifications --output json
```

The generated author classification loop is:

```bash
just cli reader author-classification-export --language lat --path /tmp/lat-authors.csv

just cli reader classify-authors \
  --input-csv /tmp/lat-authors.csv \
  --output-csv data/generated/reader_classifications/<date>/authors/full/lat-author-generated.csv \
  --batch-size 50 \
  --raw-response-dir examples/debug/reader-author-classifier-raw/lat \
  --output json

just cli reader --catalog data/build/reader/catalog.duckdb sync-author-classifications \
  --classification-csv data/generated/reader_classifications/<date>/authors/full/lat-author-generated.csv \
  --merge \
  --output json
```

After adding a new source collection, prefer classifying only the new rows or collection rather than rerunning the entire corpus.

## Source Index TSVs

The source-index TSV files are human-readable snapshots of the catalog provenance.

Location:

```text
data/reference/reader_source_index/
```

Regenerate after reader imports or catalog rebuilds:

```bash
just cli reader source-index-export \
  --output-dir data/reference/reader_source_index \
  --output json
```

This writes:

- `all_collections.tsv`
- one `<collection_id>.tsv` per collection
- `duplicate_canonical_text_ids.tsv`
- `README.md`

These files answer:

- What collections exist?
- What works came from each collection?
- What source path produced each work?
- How many segments/words were built?
- Which canonical ids have duplicate visible works?

The `/library` page and `/api/reader?mode=source-index` are the interactive counterpart to these TSVs.

## Open-Web Import Audit

For high-value or questionable rows, source-index presence is not enough. Audit should verify whether the author/title/source mapping is legitimate against open-web evidence.

Use Firecrawl or another web research tool to check:

- Is this title attested under this author?
- Is this work present in the claimed volume or corpus?
- Is the row a real work, a volume heading, a table of contents, a commentary, a fragment, or a translation?
- Does an external source confirm the author/title relationship?

Good evidence targets include:

- Latin Wikisource volume/work pages.
- Archive.org metadata and derivative volume tables of contents.
- Documenta Catholica Omnia author pages.
- Corpus Christianorum/Brepols pages for bibliographic context.
- Library/catalog records.
- OGL CTS inventory files and TEI headers.

Firecrawl outputs should remain raw research artifacts. Reviewed conclusions should be promoted into curated overlays, source manifests, or audit reports.

## Recommended Post-Import Loop

After importing or changing reader source data:

1. Rebuild the reader catalog/artifacts with the appropriate databuild command.
2. Reapply curated overlays, aliases, attributions, citation maps, work maps, contained works, and division metadata as required by the build path.
3. Regenerate or update generated classification inputs for the new/changed collection.
4. Run `classify-works` and/or `classify-authors` for new rows when shelf/period/author metadata is missing.
5. Sync generated classifications with `--merge`.
6. Run `prune-stale-classifications`.
7. Rebuild or validate the reader search index if source text changed.
8. Regenerate source-index TSVs.
9. Inspect `/library` or `reader source-index` for the imported collection.
10. Spot-check `/reader` for at least one representative work.

## Current Verified Reader State: 2026-06-07

The latest handoff is:

```text
docs/plans/active/infra/READER_CURRENT_STATUS_HANDOFF_2026-06-07.md
```

Verified in the current stack:

- `/library` server-renders initial source-index rows, collection data, and acquisition watchlist targets.
- `/library` uses compact expandable source-index rows for large collections.
- `reader library-watchlist` reads `data/curated/reader_library_watchlist/high_value_targets.yaml`.
- `/api/reader?mode=library-watchlist` exposes the same curated targets.
- `/api/reader?mode=source-index&q=eriugena` exposes the selected PL122 Eriugena imports.
- `src/langnet/reader/builder.py` now skips Sanskrit source paths with `translation` or `translations` path components for primary Sanskrit text import.
- PHI/TLG legacy source import now skips parsed books outside primary reader languages: `lat`, `grc`, and `san`.
- Current catalog cleanup removed existing Sanskrit translation-path rows and PHI non-primary-language rows.
- `data/reference/reader_source_index/*.tsv` was regenerated after cleanup; latest reported row count is `10579`.
- `cd webapp && bun run check` passes with 0 errors and 0 warnings.
- `cd webapp && bun run build` passes.

Known remaining gaps:

- `data/build/reader/search.lance` still needs a successful rebuild or incremental refresh.
- PL122 front matter and segmentation need cleanup before broader PL import.
- Browser-level QA remains for `/library` searches, filters, and `/reader` navigation.

## Useful Inspection Commands

List source collections:

```bash
just cli reader collections --output json
```

Search visible works:

```bash
just cli reader works --query "dionysius" --limit 10 --output json
```

Search provenance rows:

```bash
just cli reader source-index --query "dionysius" --limit 10 --output json
```

Inspect one collection:

```bash
just cli reader source-index \
  --collection opengreekandlatin_csel \
  --limit 20 \
  --output json
```

Audit OpenGreekAndLatin source selection:

```bash
just cli reader ogl-audit --output json
```

Reference audit artifacts live under:

```text
data/reference/ogl_import_audit/
```

Use the CSEL/Patrologia scorecard there to distinguish:

- external corpus coverage,
- local checkout coverage,
- and actual reader catalog coverage.

Use the PL/PG acquisition scorecard there to choose source roles:

- `primary_text_source` or `primary_pg_ocr_corpus_candidate` for import prototypes.
- `bulk_ocr_fallback_and_missing_volume_acquisition` for absent volumes such as PL122.
- `toc_and_legitimacy` for author/work/volume corroboration before import.
- `bibliographic_reference_and_download_catalog` for source discovery without direct text ingestion.
- `identity_control_authority_not_text_source` for canon/author mapping such as local TLG CD listings.

Export source-index snapshots:

```bash
just cli reader source-index-export \
  --output-dir data/reference/reader_source_index \
  --output json
```

View shelves:

```bash
just cli reader shelves --language lat --output json
```

View groups/tags:

```bash
just cli reader groups --language lat --output json
just cli reader tags --language lat --output json
```

## Server Migration Considerations

As the corpus grows, raw mirrors, Archive derivatives, PDFs, images, OCR outputs, DuckDB artifacts, and search indexes will need more disk space.

Recommended split:

- Git repo: code, docs, curated metadata, generated CSVs, source manifests, reference TSVs.
- External storage: raw mirrors, PDFs, image sets, OCR intermediate output, large Archive derivatives, large build artifacts if needed.
- Rebuildable cache: CLTK data, search indexes, temporary classifier raw responses.

Future environment variables should let us move large paths off repo-local `data/`:

- `LANGNET_DATA_ROOT`
- `LANGNET_SOURCE_ROOT`
- `LANGNET_BUILD_ROOT`
- `LANGNET_CACHE_ROOT`
- `LANGNET_READER_CATALOG_PATH`

The goal is that a new server can either copy bulky storage with `rsync` or rehydrate from source manifests.

## Button-Up Checklist Before Major Expansion

- `reader source-index-export` exists and has been run after the latest catalog state.
- `/library` can browse source-index rows.
- Duplicate canonical ids are visible in `duplicate_canonical_text_ids.tsv`.
- Curated data roots are documented and preserved.
- Generated classification loop is documented.
- PL/PG acquisition source rankings are captured in `data/reference/ogl_import_audit/pl_pg_acquisition_source_scorecard.tsv`.
- High-value misses such as Eriugena/PL122 are represented as acquisition targets, not misdiagnosed as importer bugs.
- Patrologia Graeca has a pilot manifest/sample before broad PG import is attempted.
- New acquisition plans use source manifests before importing raw text.
- Large raw sources are not accidentally committed without an explicit decision.
