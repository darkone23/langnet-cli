# Reader Source Acquisition

Reader source acquisition is the controlled path from an external witness to a
reader catalog row. It is not a bulk-import shortcut. Every new source family
should preserve provenance, source role, quality status, and review state before
text becomes learner-facing reader content.

## Current Rule

Do not import raw web, OCR, or mirrored text directly into the reader catalog.

Use this sequence:

1. Create or update a source manifest under `data/sources_external/...`.
2. Store raw source material under the manifest `raw_storage` path, or record an
   external storage location and checksum when the raw material is too large.
3. Stage readable text into JSONL under `data/build/reader_import_staging/...`.
4. Inspect a bounded sample for language, boundaries, boilerplate, OCR noise,
   citation shape, and source role.
5. Import only staged JSONL or a source-specific staging output.
6. Export or inspect source-index rows so provenance is visible from CLI, API,
   and `/library`.

## Manifest Fields

Use YAML. Existing manifests are intentionally readable rather than a strict
machine schema. Prefer these fields:

```yaml
source_id: cusanus:de_docta_ignorantia
label: Nicolaus Cusanus, De docta ignorantia
source_type: wikisource_and_archive_org_text_witness
series: Orion humanist/mystical source library
status: imported_source_index_exported
retrieved_at: 2026-06-07
retrieval_method: firecrawl_search_and_source_record_scrape
raw_storage: data/sources_external/cusanus/de-docta-ignorantia/raw
staging_storage: data/build/reader_import_staging/cusanus/de_docta_ignorantia
source_use_note: Open/mirrorable Latin philosophical source candidate.
quality_status: imported_with_uncertain_source_provenance
language: lat
authors:
  - Nicolaus Cusanus
works:
  - title: De docta ignorantia
    language: lat
    status: candidate
primary_candidates: []
selection_decision:
  status: imported_source_index_exported
checksums: []
```

The important invariant is that a manifest explains what the source is, why it
is being used, what role each witness plays, and which quality or boundary risks
remain.

## Source Roles

Use explicit source roles in `primary_candidates` and import notes. Common
roles are:

- `primary_electronic_text_candidate`: clean text candidate for staging.
- `primary_pdf_ocr_djvu_text_candidate`: OCR-derived source candidate.
- `printed_control_witness`: scan/OCR witness used to check another electronic
  text.
- `toc_and_legitimacy_primary_candidate`: table-of-contents or work-boundary
  evidence.
- `bibliographic_worklist_and_identity_control`: identity evidence only.
- `quality_benchmark`: comparison witness, not necessarily selected text.
- `english_translation_and_structure_reference_not_source_text`: structure or
  reception context only; do not import as Latin, Greek, or Sanskrit source text.

Do not let source-role language imply critical-edition authority. Reader imports
are electronic reading editions and source witnesses with known quality.

## Quality Status

Use the quality labels from the corpus acquisition framework when possible:

- `machine_text_clean`
- `machine_text_needs_segmentation`
- `html_needs_boilerplate_strip`
- `ocr_usable_with_artifacts`
- `ocr_needs_correction`
- `image_pdf_needs_ocr`
- `mixed_provenance_needs_spot_check`
- `metadata_only`
- `wanted`

Project-specific statuses such as `imported_source_index_exported` or
`sample_staged_needs_review` are acceptable in manifests, but source-index rows
should still expose a learner-useful quality/status phrase.

## Implemented Commands

Use `just cli` wrappers for routine work:

```bash
just cli reader stage-pl-wikisource --output json
just cli reader import-pl-wikisource --output json

just cli reader stage-pg-pilot --output json
just cli reader import-pg-pilot --output json

just cli reader import-staged-jsonl \
  --segments data/build/reader_import_staging/cusanus/de_docta_ignorantia/cusanus-de-docta-ignorantia.segments.jsonl \
  --collection-id cusanus_latin_wikisource \
  --namespace cusanus \
  --edition-label "Latin Wikisource with Archive.org control witness" \
  --edition-suffix wikisource_archive_control \
  --output json
```

The PL and PG commands are source-specific staging/import paths. The
`import-staged-jsonl` command is the reusable path for a reviewed staged work
whose JSONL already contains source metadata.

## Current Framework Evidence

The framework is active in these artifacts:

- PL122/Eriugena manifest and Wikisource staging/import:
  `data/sources_external/patrologia_latina/pl122/manifest.yaml`
- Patrologia Graeca pilot manifest and staged OCR sample:
  `data/sources_external/patrologia_graeca/pilot/manifest.yaml`
- Cusanus reusable staged JSONL import:
  `data/sources_external/cusanus/de-docta-ignorantia/manifest.yaml`
- Agrippa and Ficino source-candidate manifests:
  `data/sources_external/agrippa/de-occulta-philosophia/manifest.yaml`
  and `data/sources_external/ficino/de-vita-libri-tres/manifest.yaml`
- Reader source-index exports:
  `data/reference/reader_source_index/`
- Acquisition scorecards:
  `data/reference/ogl_import_audit/`

## Verification

For source-acquisition code changes, run the narrow tests first:

```bash
just test test_reader_source_acquisition
just test test_reader_storage
```

For a real acquisition import, verify the catalog surface:

```bash
just cli reader works --query cusanus --limit 5 --output json
just cli reader source-index --collection cusanus_latin_wikisource --output json
just cli reader source-index-export --output-dir data/reference/reader_source_index --output json
```

Update `data/reference/reader_quality_audit/current_known_issues.tsv` when a
source has visible OCR noise, segmentation defects, uncertain attribution, or a
known source-role caveat.
