# Foster TOC Summary Pipeline

Goal: make Foster summaries reliable enough to support later “Essentials of the
Reginaldus Foster Method” rollups and application learning experiences.

Current slice:

- Treat the structured TOC as the canonical encounter list.
- Add `toc-entry` summary scope.
- Build each summary input from the TOC entry and its inferred page span.
- Normalize valid generated JSON into `generated_json`.
- Mark invalid generated rows with `validation_issues`.
- Add `experience` rollup scope from valid TOC-entry summary JSONL.
- Keep generated summaries as explicit artifacts, not source truth.
- Preserve source refs, input hashes, model names, and prompt versions.

Observed first-batch result:

- First 10 TOC entries generated: 8 valid, 2 invalid.
- Invalid rows were useful failures: one omitted page refs, one returned invalid
  JSON. Both are caught before rollups.
- A partial `experience:1` rollup over the 8 valid rows generated successfully
  and preserved TOC/page citations.

Next slices:

- Roll experience summaries into an essentials artifact.
- Add targeted regeneration/retry for invalid TOC-entry rows.
- Map extracted Foster claims into LangNet’s grammar taxonomy and reader flows.
