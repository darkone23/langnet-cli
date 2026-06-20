# OGL Patrologia Source-View Mapping And Attribution Review

**Status:** TODO  
**Created:** 2026-06-19  
**Feature Area:** infra / reader

## Purpose

Extend the completed OpenGreekAndLatin importer audit slice into a broader
Patrologia review pass without changing importer precedence prematurely.

The active audit work added `reader ogl-audit`, `reader ogl-view-comparison`,
scorecards, and direct CTS-key comparison artifacts. The remaining work is
research and mapping-heavy: many alternate `corrected`, `split`, and `volumes`
files use PL filename/volume identifiers that do not directly match selected
`data/` CTS paths.

## Inputs

- `data/reference/ogl_import_audit/current_ogl_audit.json`
- `data/reference/ogl_import_audit/opengreekandlatin_patrologia_source_view_comparison.json`
- `data/reference/ogl_import_audit/opengreekandlatin_patrologia_source_view_comparison.tsv`
- `data/reference/ogl_import_audit/opengreekandlatin_patrologia_view_comparison_review.json`
- `data/reference/ogl_import_audit/opengreekandlatin_patrologia_view_comparison_review.tsv`
- Raw search artifacts under `.firecrawl/`, especially:
  - `.firecrawl/ogl-vitae-patrum-ephraem-pl73-74-search.json`
  - `.firecrawl/ogl-pl73-74-vitae-patrum-search.json`

## Remaining Work

1. Build PL filename/volume mapping for alternate Patrologia views.
   - Map `corrected/PL*`, `split/PL*`, and `volumes/PL*` rows to selected
     `data/` CTS works only when evidence is stronger than author-level
     coincidence.
2. Produce the original target sample:
   - 10 `data`/`corrected` comparisons;
   - 10 `data`/`split` comparisons.
3. Run open-web legitimacy review for sampled rows.
   - Confirm title, author, PL volume, and whether the alternate file is a
     work, volume heading, table of contents, collection, or apparatus.
4. Add overlays only for reviewed author/title corrections.
5. Change source-view precedence only if the evidence shows a view is better
   for a collection or work class.

## Acceptance

- A reviewed TSV/JSON identifies at least 20 mapped comparison rows or explains
  why fewer high-confidence rows exist.
- Each recommended action is one of: `keep`, `overlay_author`,
  `overlay_title`, `split_work`, `suppress`, `needs_human_review`,
  or `acquire_missing_source`.
- No importer source-view precedence changes happen without linked evidence.
