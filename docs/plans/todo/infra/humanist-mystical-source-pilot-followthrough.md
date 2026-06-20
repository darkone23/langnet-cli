# Humanist And Mystical Source Pilot Follow-Through

**Status:** todo

**Goal:** Promote one Project Orion humanist, scholastic, or mystical source
candidate from manifest/source review into a source-index-visible reader import.

## Candidate Order

- Cusanus: already imported; needs post-import reader and Library provenance QA.
- Ficino: compare 1489, 1529, and 1549 OCR/text derivatives before staging.
- Agrippa: keep deferred until OCR cleanup and long-s/early-modern spelling
  policy is explicit.
- Aquinas or Duns Scotus: only after a bounded source witness and paragraph or
  article structure are clear.

## Scope

- Use the reusable manifest-backed staged JSONL path.
- Preserve source witnesses and control witnesses separately.
- Record OCR, attribution, or edition uncertainty in the manifest and known
  issues table.
- Avoid importing translations as Latin, Greek, or Sanskrit source text.

## Acceptance

- One candidate has a manifest, staged sample, source-index row, and quality
  status.
- `/library` distinguishes imported work from wanted/acquisition context.
- Relationship metadata is added only where source-backed.

## Validation

```bash
just cli reader source-index --query cusanus --limit 5 --output json
just cli reader library-watchlist --query ficino --output json
just test test_reader_source_acquisition
```
