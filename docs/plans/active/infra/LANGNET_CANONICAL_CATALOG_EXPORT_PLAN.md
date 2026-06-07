# LangNet Canonical Catalog Export Plan

Status: active
Owner: @architect, @coder, @auditor
Created: 2026-06-05

## Goal

Create a LangNet-native export format for reader/catalog data so the system has
a stable canonical representation independent of the many irregular upstream
inputs: CTS/TEI, DCS, Perseus, Dico/Georges lexica, local plain text, generated
catalog artifacts, and future sources.

This export is not meant to replace source evidence. It is the normalized
LangNet product contract: what our application believes a work/book/lexicon item
is after import, normalization, metadata enrichment, and validation.

## Position

CTS and TEI should remain provenance and scholarly interchange layers, not the
only canonical LangNet representation.

Reasons:

- CTS is strong for citation identity but does not naturally express all LangNet
  reader states, generated didactic metadata, mixed-script layers, search/cache
  hints, lexicon linkage, attestation, or web UI requirements.
- TEI is strong for source encoding but too permissive and source-specific for a
  compact runtime/export contract.
- LangNet imports many non-TEI sources; forcing all outputs back through TEI
  would hide useful normalized structure or invent TEI semantics we do not need.
- We prefer CTSv2 for user-facing canonical addresses, especially where works
  are named by title/opening-line content rather than source directory trees.

## Product model

Introduce two export layers.

### 1. LangNet canonical bundle

The source of truth for LangNet exports.

A bundle is a deterministic directory or `.zip`/`.tar.zst` containing:

```text
manifest.json
works/<work-key>/work.json
works/<work-key>/segments.jsonl
works/<work-key>/citations.jsonl
works/<work-key>/provenance.json
works/<work-key>/metadata.json
lexica/<lex-id>/metadata.json
lexica/<lex-id>/entries.jsonl        # later phase
indexes/catalog-summary.json
checksums/SHA256SUMS
```

The bundle must be rebuildable from `data/build/reader/catalog.duckdb`, per-book
DuckDB artifacts, curated metadata, and lexicon databases.

### 2. Presentation exports

Generated from the canonical bundle, not used as source of truth.

Initial targets:

- EPUB for human reading and classroom sharing.
- Static HTML for web publishing.
- JSONL slices for research/data pipelines.

Potential later targets:

- TEI-lite export for scholarly interchange.
- OPDS feed for ebook catalog browsing.
- SQLite/DuckDB portable bundle for offline app use.

## Canonical identity policy

Each exported work must include three distinct identity layers:

- `langnet_work_id`: stable internal catalog key; may be collection-scoped.
- `canonical_text_id`: preferred user-facing CTSv2 identity.
- `source_ids`: upstream source identifiers, including CTS URNs when present.

Rules:

- User-facing addresses should prefer `canonical_text_id` / CTSv2.
- Raw CTS URNs are provenance, not the universal UI key.
- Synthetic source IDs must be clearly marked as LangNet-generated.
- Collection-scoped collisions are allowed only when internal IDs stay unique
  and source provenance remains explicit.

Example `work.json` shape:

```json
{
  "schema_version": "langnet.catalog_export.work.v1",
  "langnet_work_id": "urn:langnet:ogl:opengreekandlatin_csel:urn:cts:latinLit:stoa0022.stoa014",
  "canonical_text_id": "urn:ctsv2:lat:apologia-altera-prophetae-david-fortasse-plerosque-psalmi",
  "collection_id": "opengreekandlatin_csel",
  "language": "lat",
  "title": "Apologia Altera Prophetae David",
  "authors": [
    {
      "name": "Ambrosius",
      "role": "source_author",
      "authority_id": "urn:cts:latinLit:stoa0022",
      "confidence": "source"
    }
  ],
  "source_ids": {
    "source_id": "stoa0022.stoa014",
    "cts_work_urn": "urn:cts:latinLit:stoa0022.stoa014"
  },
  "canonical_address": "urn:ctsv2:lat:apologia-altera-prophetae-david-fortasse-plerosque-psalmi"
}
```

## Segment model

Use JSONL for stable, streamable text export.

Each segment row should include:

- `segment_id`: LangNet internal segment key.
- `canonical_address`: CTSv2 address when available.
- `citation_path`: local citation path.
- `sort_key`: deterministic order.
- `language`.
- `text`.
- `normalized_text`.
- `display_layers`: source/translation/commentary availability.
- `source_ref`: source file and source citation if known.

The canonical bundle should preserve segment granularity as imported. Later
presentation exports may group segments into chapters or sections.

## Provenance model

Every bundle must keep source and transformation evidence:

- source collection and source path or durable source URI.
- upstream source ID / CTS URN / fallback ID.
- import adapter name.
- source hash.
- import status and skip metadata for source files.
- generated metadata run IDs when classifications are included.
- curated metadata files used.
- build timestamp and LangNet version marker.

## CLI design

Add a new command group:

```bash
just cli reader export bundle --output-path data/export/reader-catalog
just cli reader export work <work-id> --output-path data/export/work
just cli reader export epub <work-id> --output-path data/export/epub
just cli reader export manifest --output json
```

Initial options:

```text
--collection <id>
--language <lang>
--work-id <id>
--include-source-metadata / --no-include-source-metadata
--include-generated-metadata / --no-include-generated-metadata
--include-lexicon-links / --no-include-lexicon-links
--format directory|zip|tar-zst
--replace
--output json|pretty
```

## Validation

Add export validation commands:

```bash
just cli reader export validate data/export/reader-catalog --output json
```

Validation requirements:

- Manifest schema version present.
- Every work has `langnet_work_id`, `canonical_text_id`, title, language, and
  at least one author/agent record.
- No exported work has display author `Unknown` unless status is explicitly
  `unresolved` with reason.
- Every segment has stable ordering and belongs to an exported work.
- Every work has at least one segment unless explicitly marked metadata-only.
- CTSv2 canonical address is present for reader-facing text works.
- Source provenance is present for every work.
- Checksums match files.
- Re-exporting the same catalog produces deterministic file paths and stable
  checksums when source data is unchanged.

## OGL-specific requirements

The OpenGreek+Latin import work revealed constraints this export must preserve:

- CSEL and Patrologia can share source CTS URNs; the export must not collapse
  them.
- LangNet-scoped catalog IDs are valid internal keys.
- CTS inventory metadata from `__cts__.xml` is source evidence and should be
  included in provenance.
- Patrologia editorial or uncertain materials should use explicit labels such
  as `Patrologia Latina editor`, `Incertus`, `Concilium`, or source-backed
  author names rather than `Unknown`.
- Very short fragments and massive volume-like chunks should be marked with
  quality flags so presentation exports can include/exclude them deliberately.

## Quality flags

Add export-time quality flags without suppressing source data:

```json
{
  "quality_flags": [
    "very_short_text",
    "volume_level_chunk",
    "editorial_apparatus",
    "uncertain_author",
    "synthetic_source_identity"
  ]
}
```

These flags should help UI and EPUB export decide default inclusion without
silently deleting source material.

## Implementation phases

### Phase 1: Bundle schema and writer

@architect / @coder

- Define export dataclasses or typed dicts.
- Add `src/langnet/reader/catalog_export.py`.
- Export one work to directory JSON/JSONL.
- Include manifest, work metadata, segments, provenance, checksums.
- Add focused unit tests with temp catalogs/artifacts.

### Phase 2: Full catalog export

@coder

- Stream all works from catalog.
- Support collection/language filters.
- Keep memory bounded.
- Write deterministic paths.
- Add validation command.

### Phase 3: EPUB export

@coder / @scribe

- Generate EPUB from canonical bundle/work export.
- Map segments to XHTML chapters.
- Include Dublin Core metadata.
- Include source/provenance page.
- Preserve CTSv2 canonical ID in metadata.
- Keep source CTS URNs in provenance, not primary UI title/address.

### Phase 4: Migration/server portability

@architect / @auditor

- Document how to rebuild exports on a new server.
- Decide whether exports are artifacts to transfer or rebuild outputs.
- Add size estimates.
- Add smoke validation commands for restored bundles.

## Immediate next tasks

1. Finish OGL reader audit and reimport cleanup.
2. Do not rebuild stale reader search index until OGL audit is complete.
3. Add a small `reader export work` prototype for one OGL CSEL work.
4. Validate that exported canonical addresses use CTSv2 while source CTS URNs
   remain in provenance.
5. Use the prototype to decide whether directory or zip should be the default
   bundle packaging.

## Open questions

- Should canonical bundles include generated classification metadata by default,
  or keep it as an optional layer?
- Should lexicon links be embedded in segment exports or emitted as separate
  alignment files?
- Should EPUB include critical apparatus/source notes by default, or offer a
  learner mode that omits noisy apparatus?
- What retention policy do we want for large exported bundles on the production
  server?
