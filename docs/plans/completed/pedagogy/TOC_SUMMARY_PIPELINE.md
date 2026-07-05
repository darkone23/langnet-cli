# Foster TOC Summary Pipeline

Goal: make Foster summaries reliable enough to support later "Essentials of the
Reginaldus Foster Method" rollups and application learning experiences.

## Status

Complete. All three planned slices are implemented and tested (79 Foster tests
passing). The pipeline produces a full 105-entry run with experience rollups,
essentials carry `experience:*` refs, invalid-row retry is available as a CLI
command, and Foster bridge data surfaces in the reader word-context payload.

## Completed Slices

- Treat the structured TOC as the canonical encounter list.
- `toc-entry` summary scope with prompt v2.
- Build each summary input from the TOC entry and its inferred page span.
- Normalize valid generated JSON into `generated_json`.
- Mark invalid generated rows with `validation_issues`.
- `experience` rollup scope from valid TOC-entry summary JSONL.
- Full 105-entry TOC-entry summary run (Experiences 1, 3, 4) — all valid.
- Experience rollups generated for Experiences 1, 3, 4.
- Markdown docs rendered under `docs/reference/foster-ossa/generated/`.
- Taxonomy audit mapping extracted Foster terms against LangNet's grammar
  concept registry.
- Foster essentials pack (7 essentials) with validation and bridge to learning
  layer.
- Search index built and validated.
- Essentials now carry `experience:*` summary refs alongside `toc:*` refs.
- `--retry-only` CLI option for targeted regeneration of invalid TOC-entry rows
  via `invalid_source_refs_from_summary_jsonl`.
- Foster bridge data surfaces in the reader word-context payload
  (`foster_bridge` field) when morphology analysis matches Foster essentials'
  `morphology_predicates`.

## Generated Artifacts

- `data/build/foster_ossa.duckdb` — structured index
- `data/build/foster_ossa_search.lance/` — full-text search index
- `data/build/foster_essentials.json` — validated essentials pack
- `docs/reference/foster-ossa/generated/` — 105-entry summary docs
- `docs/reference/foster-ossa/{TAXONOMY_AUDIT,INTEGRATION_STATUS,...}.md`
