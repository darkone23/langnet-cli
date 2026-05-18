# Devanagari Illuminated Title Implementation Record

Status: completed and archived.

This file began as an implementation plan. It is kept as a curated record of
the Sanskrit title treatment rather than as active work.

## Goal

Sanskrit native headwords should keep their first grapheme visually emphasized
without making the word feel broken. The treatment should preserve a
Devanagari-style topline across the illuminated grapheme and the smaller
remainder where possible.

## Current Implementation

- `src/lib/headword-display.ts` splits Devanagari titles into an initial
  grapheme and the remaining text.
- `Intl.Segmenter` is used when available, with an `Array.from` fallback.
- `src/routes/+page.svelte` renders the Devanagari title structure only when
  the display model marks the title as Devanagari.
- `src/app.css` owns the illuminated block, connector bar, remainder alignment,
  and overflow-safe title spacing.
- Greek and Latin title paths stay plain and do not use the Devanagari connector
  treatment.

## Protected By

- `src/lib/headword-display.test.ts`
- `docs/UI.md`, "Result Titles"
- `docs/REGRESSION_CASES.md`, "Display Model Unit Cases"

## Notes

Do not use this archived record as an active checklist. If the illuminated title
visuals change, update the current implementation docs and regression cases
alongside the code.
