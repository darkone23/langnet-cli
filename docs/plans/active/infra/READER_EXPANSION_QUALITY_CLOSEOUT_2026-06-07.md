# Reader Expansion Quality Close-Out

> **Purpose:** Freeze the current reader-expansion state so future work can resume without re-opening solved questions or accidentally importing staged-but-not-ready material.

## Current Policy

- Pause broad expansion until started work has clear quality gates.
- Treat staged samples as evidence, not reader imports.
- Preserve uncertain source, edition, OCR, and witness-role status in manifests and source-index metadata.
- Keep every reader segment at paragraph size or smaller unless a source-specific structure requires a smaller unit.
- Do not import translations as source texts unless they are explicitly modeled as translations.
- Fix reader/library quality regressions before adding new acquisition targets.

## Ready For Later Pickup

| Target | Current state | Next safe action |
| --- | --- | --- |
| Cusanus, `De docta ignorantia` | `imported_source_index_exported` | Post-import reader/Library provenance QA; do not acquire more Cusanus before confirming uncertain-source and Archive control-witness display. |
| Aquinas, `Summa theologiae` I q.50 | `deferred_non_importable_quality_gate` | Preserved as evidence only; future work requires a dedicated OCR/article-structure cleanup task or a q.1 witness decision. |
| Duns Scotus | `deferred_source_decision_required` | No active staging remains; future work starts with an Ordinatio witness decision or explicit non-Ordinatio pivot. |
| Agrippa, `De occulta philosophia` | `deferred_lexeme_cleanup_needed` | Leave deferred until long-s/f, ligature, u/v, i/j, and lexeme-level OCR policy exists. |
| Ficino, `De vita` | `source_candidate_verified` | Compare candidate witnesses only after the current quality gates are closed. |
| CSEL61 | `source_candidate_verified` | Parse/fetch one PDF/OCR witness and stage a small sample only after boundary checks. |
| PG pilot | `machine_text_needs_segmentation` | Keep as calibration pilot; no broad PG import until mixed-script/OCR filtering improves. |

## Non-Importable Current Artifacts

- `data/build/reader_import_staging/aquinas/scholastic_core/aquinas-summa-theologiae-i-q50-sample.segments.jsonl`
- `data/build/reader_import_staging/agrippa/de_occulta_philosophia/agrippa-de-occulta-philosophia-book-i-sample.segments.jsonl`
- PG pilot OCR samples with `machine_text_needs_segmentation` status.

These are useful evidence and staging artifacts. They are closed as non-importable for the current stack and should not be treated as clean reader catalog content.

## Integrated This Pass

Cusanus is now integrated because:

- full work staging exists as 104 paragraph-level segments
- Latin text is clean relative to OCR candidates
- Archive.org 1913 hOCR search text is available as source-control evidence
- `reader import-staged-jsonl` imported the work into `cusanus_latin_wikisource`
- `reader source-index-export` regenerated `data/reference/reader_source_index/cusanus_latin_wikisource.tsv`

Remaining post-import QA:

- confirm reader and Library surfaces display the Wikisource uncertain-source/edition status and Archive control-witness role clearly.

## Reader/Library Close-Out

The `/library` source-index explorer no longer treats a small source-index sample as a complete collection view.

Close-out work completed:

- source-index API cap raised from 1000 to 20000 rows
- `/library` server load raised from 100 to 20000 rows
- `/library` filtered source-index loads raised from 200 to 20000 rows
- capped-result warning added when returned row count reaches the active request limit

Remaining QA:

- restart any running web server so route/module changes reload
- confirm PHI collection browsing shows all rows under the audit limit
- confirm very large collections show the capped-result warning instead of silently stopping

## Current Quality Audit Rows

The active quality audit is:

- `data/reference/reader_quality_audit/current_known_issues.tsv`

New close-out rows added in this pass:

- `cusanus_uncertain_wikisource_source_import_gate`
- `aquinas_q50_ocr_sample_not_import_ready`
- `duns_scotus_no_ordinatio_primary_witness_yet`
- `library_source_index_rows_truncated`

## Recommended Next Session

1. Do not expand to new authors first.
2. QA `/library` PHI/source-index browsing after web restart.
3. QA Cusanus reader and Library provenance display.
4. Open a new dedicated task before resuming Aquinas q.50 OCR/article cleanup.
5. Open a new dedicated task before resuming Scotus source-decision work.
6. Update the quality audit before changing any scorecard status to imported or import-ready.
