# Llull Latin Source Research Continuation

**Status:** todo

**Goal:** Identify one open, extractable Latin source witness for Ramon
Llull/Raimundus Lullus before attempting reader staging or import.

## Context

The Bruno/Llull active acquisition slice proved the Bruno path through direct
Latin HTML and Archive.org control witnesses. Llull remains high-value but does
not yet have a clean open Latin electronic-text candidate in this checkout.

Known leads:

- Science History Institute `Ars brevis and Ars abbreviata praedicandi, versio
  latinus II`: open digitized object, likely OCR/PDF/image lane rather than clean
  text.
- Archive.org `selectedworksofr00v1llul`: useful bibliographic/translation
  context, not yet a clean Latin source-work candidate.
- Corpus Christianorum `Raimundi Lulli Opera latina`: bibliographic authority,
  not an open text-import source.
- University of Barcelona Ramon Llull Documentation Center and related Llull DB
  paths: research leads, source role not yet established.

## Acceptance Before Import

- One Latin work has an open/mirrorable text, OCR, hOCR, PDF, or image witness.
- A source manifest exists under `data/sources_external/llull/...`.
- Source role is classified as clean text, OCR witness, page-image witness,
  bibliography, or translation/context.
- A small source-quality sample is reviewed before any reader catalog import.

## Validation

```bash
just cli reader library-watchlist --query llull --output json
```
