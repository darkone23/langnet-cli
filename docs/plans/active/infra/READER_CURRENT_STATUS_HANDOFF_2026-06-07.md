# Reader Current Status Handoff - 2026-06-07

This handoff records the current verified state of the reader/library work after the PL122/Eriugena import and `/library` integration pass.

## Executive Summary

The reader stack is usable for the current PL122 pilot and Library provenance browsing:

- `/library` now server-renders initial catalog rows and acquisition watchlist data.
- `/library` now uses compact expandable source rows instead of one large card per work.
- The Library acquisition watchlist is backed by curated YAML, CLI, and `/api/reader`.
- Fourteen PL122 Joannes Scotus Eriugena works are imported, classified, provenance-visible, and readable.
- One Patrologia Graeca pilot sample (`patrologia_graeca_pilot`) is staged, imported, and visible in CLI/source-index output.
- Sanskrit translation-path rows and PHI non-primary-language rows are fixed in importer guards and in the current catalog.
- Web type checking and production build pass.
- The running service on `43210` was restarted after the verified production build.

Remaining high-priority content-quality watch items are segmentation boundary confidence on PL122 imports and OCR noise in the PG pilot sample, both currently flagged `machine_text_needs_segmentation`.

Latest implementation reality:

- PL122 front-matter filtering in `src/langnet/reader/source_acquisition.py` now strips prefatory `MONITUM` and marker+title/front-matter lines in staging, with regression coverage in `tests/test_reader_source_acquisition.py`.
- The PL122 front-matter issue has been verified in reader output with the full selected work set after re-staging and import.

New corpus-quality defects identified after the Library handoff are tracked in:

```text
data/reference/reader_quality_audit/current_known_issues.tsv
```

Current corpus-quality queue:

- Sanskrit translation files were appearing as primary Sanskrit works; fixed in importer guard and current catalog on 2026-06-07.
- PHI Coptic/Sahidic rows were appearing in the primary classical reader surface; fixed in importer guard and current catalog on 2026-06-07.
- Large Library result sets were too unwieldy as cards; fixed with compact expandable rows on 2026-06-07.
- PL122 front matter and segmentation filtering implementation is complete in parser logic; full staged sample verification is now complete and shows text-first output on sampled work entries.
- CSEL coverage gap is now explicit in `current_known_issues.tsv` (`csel_volume_gap_coverage`) and queue-managed in `data/reference/ogl_import_audit/pl_pg_acquisition_next_steps.tsv` row 8 via `data/sources_external/csel/volume-61/manifest.yaml`.

## Verified Commands And Outcomes

Run from `/home/nixos/langnet-tools/langnet-cli` unless otherwise noted.

```bash
cd webapp && bun run check
```

Outcome:

- `svelte-check found 0 errors and 0 warnings`

```bash
cd webapp && bun run build
```

Outcome:

- Production build completed successfully.
- Only the existing plugin timing notice was emitted.

```bash
curl -fsS 'http://127.0.0.1:43210/library' > /tmp/langnet-library-rendered.html
rg -q 'Ars maior' /tmp/langnet-library-rendered.html
rg -q 'Joannes Scotus Eriugena' /tmp/langnet-library-rendered.html
```

Outcome:

- `/library` rendered HTML is about `325638` bytes.
- `Ars maior` is present in server-rendered HTML.
- `Joannes Scotus Eriugena` is present in server-rendered HTML.

```bash
curl -fsS 'http://127.0.0.1:43210/api/health'
```

Outcome:

```json
{"ok":true,"service":"langnet-web"}
```

```bash
python -m py_compile src/langnet/reader/builder.py
```

Outcome:

- Reader builder syntax check passed after importer guard changes.

```bash
just cli reader source-index-export --output-dir data/reference/reader_source_index --output json
```

Outcome:

- Source-index TSV snapshots regenerated after catalog refresh.
- Final reported row count: `10592`.
- `patrologia_latina_wikisource.tsv` row count: `14`.
- `patrologia_graeca_pilot.tsv` row count: `1`.
- `sanskrit_texts.tsv` row count: `320`.
- `phi.tsv` row count: `784`.

```bash
curl -fsS 'http://127.0.0.1:43210/api/reader?mode=source-index&q=eriugena&limit=5'
```

Outcome:

- Returns fourteen `patrologia_latina_wikisource` rows:
- `urn:ctsv2:lat:de-divisione-naturae-magister-saepe-mihi`
- `urn:ctsv2:lat:de-praedestinatione-dominis-illustribus-et`
- `urn:ctsv2:lat:expositiones-super-ierarchiam-caelestem-s-dionysii-cod-vat-sec`
- `urn:ctsv2:lat:versio-operum-s-dionysii-editio-colomensis-a`
- `urn:ctsv2:lat:commentarius-in-evangelium-secundum-joannem-fragmentum-i-cap`
- `urn:ctsv2:lat:homilia-in-prologum-evangelii-secundum-joannem-omelia-joannis-scoti`
- `urn:ctsv2:lat:de-egressu-et-regressu-animae-ad-deum-possident-fluere-et`
- `urn:ctsv2:lat:expositiones-in-mysticam-theologiam-s-dionysii-incipit-prologus-joannis`
- `urn:ctsv2:lat:expositiones-super-ierarchiam-ecclesiasticam-s-dionysii-poem-expositiones-super`

```bash
curl -fsS 'http://127.0.0.1:43210/api/reader?mode=library-watchlist&q=ficino&limit=5'
```

Outcome:

- Returns `latin-ficino` from `data/curated/reader_library_watchlist/high_value_targets.yaml`.

```bash
just cli reader works --query eriugena --limit 5 --output json
```

Outcome:

- Returns the fourteen imported Eriugena works.
- Work classification metadata is present.

```bash
just cli reader source-index --collection patrologia_latina_wikisource --limit 10 --output json
```

Outcome:

- Returns all fourteen PL122 works with source path, source hash, edition label, segment counts, token counts, and source witness metadata.

```bash
just cli reader contents urn:ctsv2:lat:de-divisione-naturae-magister-saepe-mihi --limit 2 --output json
```

Outcome:

- Content is accessible.
- This command should be re-run after the refreshed staging pass:
- `just cli reader stage-pl-wikisource --manifest data/sources_external/patrologia_latina/pl122/manifest.yaml`
- `just cli reader contents urn:ctsv2:lat:de-divisione-naturae-magister-saepe-mihi --limit 2 --output json`
- Expected front-facing rows should begin at text paragraphs (for example `ΠΕΡΙ ΦΥΣΕΩΣ...` / `MAGISTER...`) rather than `122.1022B De divisione naturae` or `Editio princeps A`.

```bash
just cli reader source-index --language san --query translation --limit 20 --output json
```

Outcome:

- Returns zero rows after cleanup.
- Existing bad rows from `/home/nixos/Classics-Data/sanskrit/translations` and other `translation`/`translations` path components were deleted from the current catalog.

```bash
just cli reader source-index --collection phi --language cop --limit 20 --output json
```

Outcome:

- Returns zero rows after cleanup.
- PHI now contains only primary reader languages in the current source-index snapshot: `lat` and `grc`.

```bash
curl -fsS 'http://127.0.0.1:43210/api/reader?mode=source-index&language=san&q=translation&limit=5'
curl -fsS 'http://127.0.0.1:43210/api/reader?mode=source-index&collection=phi&q=cop&limit=20'
```

Outcome:

- Live API returned zero Sanskrit translation-path rows.
- Live API returned zero PHI rows for `q=cop`.
- Note: `language=cop` is intentionally not a valid UI language parameter, so PHI non-primary checks should use collection/query or CLI catalog inspection.

## Running Service State

The process listening on `43210` was killed after the production build, and process-compose restarted it.

Last verified listener:

```text
0.0.0.0:43210 node pid=1746426
```

This pid is expected to change after future restarts.

## Files Added Or Updated In This Stack

Library and API:

- `webapp/src/routes/library/+page.server.ts`
- `webapp/src/routes/library/+page.svelte`
- `webapp/src/routes/api/reader/+server.ts`
- `webapp/src/lib/server/reader-cli.ts`
- `webapp/src/lib/reader/reader-api.ts`
- `webapp/src/lib/reader/library-watchlist.ts`
- `data/reference/reader_quality_audit/current_known_issues.tsv`
- `data/reference/reader_source_index/*.tsv`

CLI and reader support:

- `src/langnet/reader/builder.py`
- `src/langnet/reader/library_watchlist.py`
- `src/langnet/cli.py`

Curated data and planning:

- `data/curated/reader_library_watchlist/high_value_targets.yaml`
- `docs/plans/active/infra/READER_GOALS_COORDINATION_PLAN.md`
- `docs/plans/active/infra/READER_CURRENT_STATUS_HANDOFF_2026-06-07.md`
- `data/reference/ogl_import_audit/pl_pg_acquisition_next_steps.tsv`

Previously completed PL122 artifacts:

- `data/sources_external/patrologia_latina/pl122/manifest.yaml`
- `data/sources_external/patrologia_latina/pl122/raw/`
- `data/build/reader_import_staging/patrologia_latina/pl122/`
- `data/reference/reader_source_index/patrologia_latina_wikisource.tsv`
- `data/generated/reader_classifications/2026-06-07/discovery/pl122-eriugena-selected-imports.csv`
- `data/generated/reader_classifications/2026-06-07/authors/pl122-eriugena-author.csv`

## What Works

- `/library` can answer "what source rows are in the catalog?" from server-rendered source-index data.
- `/library` uses compact expandable source rows by default, so large collections are less unwieldy than the earlier full-card layout.
- Sanskrit translation-path rows and PHI non-primary-language rows have been removed from the current catalog, and future reader builds skip those primary-import candidates.
- `/library` shows a curated acquisition watchlist from the backend rather than frontend-only constants.
- `/api/reader?mode=source-index` exposes catalog provenance.
- `/api/reader?mode=library-watchlist` exposes curated acquisition targets.
- `reader library-watchlist` exposes the same watchlist through CLI.
- Fourteen Eriugena PL122 works are visible through CLI, API, source-index, and Library.
- Web type checking and production build pass.

## What Is In Progress

- PL122 is a pilot acquisition, not a fully polished import.
- `machine_text_needs_segmentation` is intentionally still present on the imported PL122 source rows pending review after re-staging.
- Patrologia Graeca now has one imported pilot work from `OGL-PatrologiaGraecaDev` Vol.-1 and is visible in source-index JSONL exports.
- Imported watchlist targets and planned acquisition targets are visible, but the UI can still better distinguish "already acquired" from "wanted".
- PL/PG/CSEL scorecards exist and are being used to guide acquisition; PG is in an evidence-gathering pilot phase.
- Segmentation/front-matter quality for PL122 and OCR noise in PG are in watch mode, both intentionally tagged `machine_text_needs_segmentation`.
- CSEL gap item moved into active execution (volume 61 manifest created, discovery-first work pending).

## Close-Out Checkpoint

The current master driver is `docs/plans/active/infra/READER_GOALS_COORDINATION_PLAN.md`. The working parity goal is provenance-and-reader-quality parity, not raw corpus-count parity.

Before starting a new broad expansion batch, confirm:

- New source family has a manifest before import.
- At least one representative sample is staged/imported and inspected.
- Source-index, `/library`, and CLI/API views expose the work with provenance and quality status.
- Known issues are logged in `data/reference/reader_quality_audit/current_known_issues.tsv`.
- Expansion queues separate source gaps, local checkout gaps, importer gaps, and UI/search gaps.

Current close-out state:

- PL122/Eriugena: acceptable to move forward after fourteen imported works; keep segmentation watch open.
- PG pilot: do not broaden until OCR/segmentation calibration is recorded.
- CSEL61: source-candidate gate is now recorded; do not import until a Google Books/OeAW PDF/OCR witness is parsed and sample quality/work-boundaries are checked.
- Library: browser interaction QA remains open after CLI/API/server-rendered verification.
- Search index: rebuild remains deferred until the next approved expansion or quality gate.

## Remaining Work

Priority 1:

- Keep corpus-quality blockers in `data/reference/reader_quality_audit/current_known_issues.tsv` updated as new issues appear.
- Treat Sanskrit translation files as translation witnesses, not primary Sanskrit works, if they are intentionally added later.
- Treat Coptic/Hebrew/English PHI material as separate audit/non-primary collections if they are intentionally added later.

Priority 2:

- Verify ongoing PL122 segmentation quality by periodic re-staging and sampling reader contents; keep watch on machine_text_needs_segmentation and column marker boundaries.
- Preserve PL column markers as useful provenance/address metadata while keeping non-reading front matter out of the main reading flow.

Priority 3:

- Continue CSEL Volume 61 from the verified source-candidate state: parse a Google Books/OeAW PDF/OCR witness, stage only after source quality and work-boundary checks, and then map high-value Prudentius works for importer handoff.

Acceptance:
- These continuation works are planned and will be visible through `reader works --query "Eriugena"` and `reader source-index --collection patrologia_latina_wikisource` after import.
- Source metadata still preserves PL122 provenance and segment-level quality status.
- Library entries show these as imported works rather than only wanted targets.

Priority 4:

- Browser QA:
- Open `/library`.
- Search `Eriugena`, `Ficino`, `Axiochus`, `Spinoza`.
- Select `patrologia_latina_wikisource`.
- Open the imported Eriugena works in `/reader`.
- Confirm acquisition watchlist entries do not look like imported works unless they really are imported.

Priority 5:

- Compare the PG pilot sample against Calfa overlap where available and update acquisition recommendation.
- Choose a missing CSEL range from the scorecard and create a source-acquisition target.
- Continue Patrologia source-view quality audit before changing OGL importer precedence.

### Deferred (Post-signoff)

- Search index rebuild (`data/build/reader/search.lance`) remains deferred until the above reader-quality gates and coverage expansion batch are approved.

## Known Non-Goals For This Pass

- No full Python test suite was run.
- No broad reader catalog rebuild was run.
- No full search-index rebuild was completed.
- No Cloudflare/Caddy/process-compose config change was made in this specific pass.

## Safe Handoff Prompt

```text
Work from docs/plans/active/infra/READER_CURRENT_STATUS_HANDOFF_2026-06-07.md and docs/plans/active/infra/READER_GOALS_COORDINATION_PLAN.md.

Current verified state:
- /library server-renders source-index rows and YAML-backed acquisition watchlist entries.
- /library uses compact expandable source rows.
- PL122 Eriugena works are imported, classified, and provenance-visible.
- Known Sanskrit translation-path and PHI non-primary-language catalog bugs are fixed in importer guards and in the current catalog.
- data/reference/reader_source_index/*.tsv was regenerated after catalog cleanup and PG pilot import; latest row count is 10592.
- webapp bun run check and bun run build pass.
- Search-index rebuild remains pending.
- PL122 segmentation/front matter remains the highest content-quality gap.

Before changing behavior:
- Use just cli reader ... for CLI checks.
- If applying web changes, run cd webapp && bun run check and cd webapp && bun run build.
- To apply server changes, kill the process listening on 43210 after the prod build and let process-compose restart it.

Do not claim Eriugena reader search is complete until data/build/reader/search.lance has been rebuilt/refreshed and a reader search query has been verified.
```
