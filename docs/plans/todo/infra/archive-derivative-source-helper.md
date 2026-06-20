# Archive.org Derivative Source Helper

**Status:** todo

**Goal:** Add a reusable helper for recording Archive.org metadata and choosing
candidate derivatives for manifest-backed reader acquisition without downloading
large files by default.

## Why

Current manifests already record Archive.org derivative candidates, but that is
manual and source-specific. The next acquisition rounds need a small reusable
utility that can inspect metadata, rank text-bearing derivatives, and write a
reviewable manifest patch or summary.

## Scope

- Read Archive.org metadata JSON from a local file or a supplied metadata URL.
- Rank derivatives in this order unless a source-specific policy overrides it:
  `_djvu.txt`, EPUB, DjVu XML, ABBYY, hOCR/search text, text PDF, image PDF.
- Emit a JSON summary with filename, format, size, URL, and recommended role.
- Optionally update a manifest only after an explicit CLI flag.
- Do not download large derivatives by default.

## Acceptance

- One fixture-backed test covers derivative ranking.
- One CLI or databuild command emits a derivative summary for a known item.
- Documentation points acquisition workers to the helper before manual manifest
  editing.

## Validation

```bash
just test test_reader_source_acquisition
just ruff-check
just typecheck
```
