# Reader Author Classification Plan

**Goal:** Add generated metadata for reader author/agent rows so the author
index can distinguish people from work titles, groups, traditions, anonymous
labels, pseudonymous names, and mythical or legendary figures.

**Why:** The current author index inherits display strings from source catalogs.
Rows such as `Acts of Thomas` can appear as authors even though they are work
titles, and names such as Dionysius or Paul may require historicity and
pseudonymity notes. The author index needs a generated metadata layer similar
to work classification so CLI and web clients can sort, filter, and explain
author/agent records without mutating source data.

## Proposed Generated Fields

- `author_id`: stable author/agent key from the reader author index.
- `author_display_name`: source display name used for classification context.
- `author_language`: primary language bucket for corpus discovery.
- `author_agent_kind`: strict value:
  - `person`: identifiable individual person.
  - `collective`: school, group, community, or corporate attribution.
  - `tradition`: broad tradition or lineage used as attribution.
  - `work_title`: a title or text label that is currently occupying the author slot.
  - `anonymous_label`: anonymous, unknown, or generic author label.
  - `ambiguous`: insufficient evidence or mixed use.
- `author_historicity_status`: strict value:
  - `historical`
  - `legendary`
  - `mythic`
  - `pseudonymous`
  - `traditional`
  - `uncertain`
  - `not_applicable`
- `author_prominence_score`: 0-100 prominence within the language corpus.
- `author_prominence_tier`: `canonical`, `major`, `common`, `specialist`, or `obscure`.
- `author_confidence`: `high`, `medium`, or `low`.
- `author_notes`: reader-facing prose explaining the classification.
- `author_generator_models`, `author_generator_run_id`, `author_source_file`.

## CLI Shape

```bash
just cli reader author-classification-export \
  --language grc \
  --path examples/debug/reader-author-classification-greek.csv

just cli reader classify-authors \
  --input-csv examples/debug/reader-author-classification-greek.csv \
  --output-csv examples/debug/reader-author-generated-greek.csv \
  --batch-size 50 \
  --shuffle-seed reader-authors-grc-2026-05-17 \
  --raw-response-dir examples/debug/reader-author-classifier-raw/grc \
  --output json

just cli reader --catalog $CATALOG sync-author-classifications \
  --classification-csv examples/debug/reader-author-generated-greek.csv \
  --merge \
  --output json

just cli reader authors --language grc --agent-kind person --sort prominence
just cli reader authors --language grc --historicity pseudonymous
just cli reader authors --language grc --agent-kind work_title
```

## Storage Shape

Add a `author_classifications` catalog table keyed by `(author_id, language)`.
The table should be separate from source author rows and overlays. Generated
classifications can be replaced wholesale or merged by `(author_id, language)`,
matching the work classification lifecycle.

## Implementation Notes

- Export should include counts and examples from the current author index:
  work count, total word count, representative titles, collections, and source
  ids. This is important for strings that are ambiguous without context.
- Generated data should be treated as generated metadata, not candidate data,
  with model/run provenance preserved.
- Do not overwrite source author names. The classifier supplies metadata that
  helps the UI decide how to display, group, filter, and explain them.
- Keep work attribution overlays separate. This layer classifies the author
  index entry; it does not decide whether a specific work is truly by that
  person.

## First Test Targets

- [x] Loader accepts generated author classification CSV and validates strict
  values.
- [x] Storage merge replaces only matching `(author_id, language)` rows.
- [x] `reader authors` can filter by `--agent-kind` and `--historicity`.
- [x] `reader author-facets` or `reader facets` exposes the strict author values
  alongside work discovery groups and tags.
