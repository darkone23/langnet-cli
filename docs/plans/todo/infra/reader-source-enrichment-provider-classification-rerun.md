# Reader Source-Enrichment Provider Classification Rerun

**Status:** TODO  
**Created:** 2026-06-19  
**Feature Area:** infra / reader

## Purpose

Run a fresh provider-backed reader classification pass from the source-enriched
classification export inputs.

The implementation work is complete: DCS/Perseus source metadata sync,
candidate metadata overlay emission, DCS chapter work-map candidate emission,
classification export context, generated classification sync, and catalog
spot-checks are in place. This todo is only for the paid/provider generation
step that should not be hidden inside an implementation closeout.

## Inputs

Generated after source-enrichment sync:

- `examples/debug/reader-classification-export-grc-source-enriched-2026-06-19.csv`
- `examples/debug/reader-classification-export-lat-source-enriched-2026-06-19.csv`
- `examples/debug/reader-classification-export-san-source-enriched-2026-06-19.csv`

## Suggested Commands

Use the current project model/provider policy at run time. Preserve raw
responses under `examples/debug/` and sync generated rows with `--merge`.

```bash
just cli reader classify-works --input-csv examples/debug/reader-classification-export-grc-source-enriched-2026-06-19.csv --output-csv examples/debug/reader-generated-classifications-grc-source-enriched-2026-06-19.csv --raw-response-dir examples/debug/reader-classification-raw-source-enriched-2026-06-19
just cli reader classify-works --input-csv examples/debug/reader-classification-export-lat-source-enriched-2026-06-19.csv --output-csv examples/debug/reader-generated-classifications-lat-source-enriched-2026-06-19.csv --raw-response-dir examples/debug/reader-classification-raw-source-enriched-2026-06-19
just cli reader classify-works --input-csv examples/debug/reader-classification-export-san-source-enriched-2026-06-19.csv --output-csv examples/debug/reader-generated-classifications-san-source-enriched-2026-06-19.csv --raw-response-dir examples/debug/reader-classification-raw-source-enriched-2026-06-19
```

Then:

```bash
just cli reader sync-classifications --classification-csv examples/debug/reader-generated-classifications-grc-source-enriched-2026-06-19.csv --merge --output json
just cli reader sync-classifications --classification-csv examples/debug/reader-generated-classifications-lat-source-enriched-2026-06-19.csv --merge --output json
just cli reader sync-classifications --classification-csv examples/debug/reader-generated-classifications-san-source-enriched-2026-06-19.csv --merge --output json
```

## Acceptance

- Generated rows are synced with `metadata_status=generated`.
- Greek medicine, Latin grammar, Sanskrit Ayurveda/Kosha/Paniniya/Vedic
  `reader popular` checks still return sensible rows.
- Source-backed metadata remains separate from generated classification fields.
