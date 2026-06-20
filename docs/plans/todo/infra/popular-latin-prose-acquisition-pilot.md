# Popular Latin Prose Acquisition Pilot

**Status:** todo

**Goal:** Import one high-demand classroom Latin prose work through the
manifest-backed acquisition path.

## First Target

Prefer Caesar `De bello Gallico` or Sallust `Bellum Catilinae`, after checking
existing reader catalog coverage and open/mirrorable source availability.

## Scope

- Confirm the target is not already discoverable through aliases/search.
- Create a source manifest under `data/sources_external/...`.
- Preserve canonical citation shape before import.
- Stage one readable work or bounded book-level sample.
- Import only after sample inspection confirms language, boundaries, and
  source-role quality.
- Add source-index export and Library/watchlist visibility.

## Acceptance

- `reader works` and `/library` surface the target by common Latin and English
  aliases.
- Source-index rows show source path, witness role, segment count, token count,
  and quality status.
- Any source caveats are tracked in
  `data/reference/reader_quality_audit/current_known_issues.tsv`.

## Validation

```bash
just cli reader works --query caesar --limit 5 --output json
just cli reader source-index --query caesar --limit 5 --output json
just test test_reader_source_acquisition
```
