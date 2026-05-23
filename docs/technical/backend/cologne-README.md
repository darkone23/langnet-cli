# CDSL / Cologne Sanskrit Backend

CDSL data provides Sanskrit dictionary entries, including Monier-Williams and AP90 when built locally.

## Runtime Role

CDSL participates in:

```text
fetch.cdsl → extract.cdsl.xml → derive.cdsl.sense → claim.cdsl.sense
```

Claims can include:

- Sanskrit lexeme anchors
- sense nodes
- glosses
- dictionary source references such as `mw:123`
- grammar details preserved under `has_feature`

## Encoding Boundary

CDSL rows use source-native SLP1 keys. Sanskrit lookup may arrive through
reader-friendly ASCII, IAST, Devanagari, Heritage dictionary anchors, or
Heritage Velthuis-like forms. Normalize all CDSL fetch keys before planning or
fetching; do not pass Heritage display anchors directly to CDSL.

One important Heritage dialect rule is fixture-backed: Heritage dictionary
anchors can use bare `f` for `ṅ`, while ordinary Velthuis `.r` still maps to
SLP1 `f`. For example, `tinanta` can normalize through Heritage as
`tiṅanta` with anchor `tifanta`, but the CDSL/MW key is `tiNanta`.

The planner and Sanskrit normalizer both preserve this boundary:

```text
reader input tinanta → Heritage tiṅanta/tifanta → CDSL tiNanta
```

CDSL display helpers should preserve raw evidence while projecting
learner-facing IAST where safe. For example, source text `tiN—anta` should
display as `tiṅ—anta`, while the raw SLP1 remains available in evidence.

## Data

CDSL data is not assumed to be present by default. Build local data with the project’s `databuild` commands when needed.

```bash
just cli-databuild cdsl --help
```

Built CDSL rows also feed the Sanskrit `word-index` surface when the word-index
databuild includes Sanskrit dictionary sources.

## Debugging

```bash
just cli lookup san tinanta --dict mw --output json
just cli encounter san tinanta cdsl --translation-mode cache --output json
just cli encounter san tinanta cdsl --no-cache --translation-mode cache --output json
just cli triples-dump san agni cdsl
just cli word-index sections san --output json
```

Use `--no-cache` when verifying changes to normalization, planning, or handler
semantics. Then rerun without `--no-cache` to confirm the cached path has the
same learner-facing result.

## Testing

Fixture-backed CDSL claim coverage lives in `tests/test_cdsl_triples.py` and does not require a DuckDB CDSL database.
Planner coverage for Heritage-to-CDSL key conversion lives in
`tests/test_planner_core.py`; Sanskrit normalizer edge cases live in
`tests/test_normalization_pipeline.py`.
