# Headword Form Display Implementation Record

Status: completed and archived.

This file began as an implementation plan. It is kept as a curated record of
the design decision rather than as active work.

## Goal

Sanskrit and Greek result headers should use native UTF-8 forms as the primary
headword when available. Romanized forms, encoded keys, and source entry forms
remain visible, but they are metadata rather than competing titles.

## Current Implementation

- `src/lib/headword-display.ts` owns the script-aware display model.
- `buildHeadwordDisplay()` chooses a native Sanskrit or Greek title when a
  matching word-index anchor provides one.
- Latin keeps the lexeme as its primary title.
- Supporting forms are deduplicated against the primary title and rendered as a
  compact metadata row.
- Sanskrit roman fallbacks can be transliterated into Devanagari when a native
  anchor is not available.

## Protected By

- `src/lib/headword-display.test.ts`
- `docs/UI.md`, "Result Titles"
- `docs/REGRESSION_CASES.md`, "Display Model Unit Cases"

## Notes

This record supersedes the original unchecked task list. Future changes should
update the implementation files and the current docs above rather than treating
this archived plan as a pending checklist.
