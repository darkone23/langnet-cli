# Reader Generated Classifications

This directory stores generated-but-reviewed reader metadata that the product
uses as rebuild input.

These CSVs are durable generated data, not cited evidence. They may drive
reader shelves, `reader popular`, discovery facets, author prominence, author
bios, and classification notes. They must not be used as proof of source
identity, authorship, citation boundaries, or contained-work ranges.

Use `data/curated/reader_*` for research-backed curated facts and claims. Use
this directory for generated interpretation that has been reviewed enough to
restore into the product catalog.

For future work-classification generation, use the default reliable loop:
`classify-works --output-profile slim --batch-order stratified --shuffle-seed langnet-reader-classification-v1`.
The model sees a smaller requested output surface, catalog clusters are
deterministically interleaved before batching, and the final CSV is restored to
input order with compatibility fields derived locally.

Use `openai:deepseek/deepseek-v4-flash` for the broad pass and
`openai:deepseek/deepseek-v4-pro` for the bounded escalation audit queue.

Current restore inputs:

- `2026-05-17/manifest.json`
- `2026-06-01/manifest.json`
