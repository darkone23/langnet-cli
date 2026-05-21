# Reader Attribution Claims

This directory stores evidence-backed attribution claims that should be
queryable but should not necessarily change `works.author`.

Use this layer when a source or scholarly reference records ambiguity, such as:

- possible author: Aristotle
- possible author: Avicenna
- traditional author: Vyāsa
- misattributed author: Virgil
- translator, commentator, editor, redactor, or compiler relationships

Do not add fabricated examples. A claim should name a real imported work and
include evidence. If a single display author is appropriate, use
`data/curated/reader_metadata` instead or in addition.

Accepted relation types used by the reader docs are:

- `attributed_author`
- `possible_author`
- `traditional_author`
- `misattributed_author`
- `translator`
- `commentator`
- `editor`
- `redactor`
- `compiler`

Evidence should cite durable sources: stable web URLs, source-root references
such as `sanskrit-dcs:data/...`, `perseus:canonical-latinLit/...`, or
`digiliblt:dlt000616.xml`, and other portable citations that are meaningful
outside one local checkout. Do not put host-local paths or `examples/debug`
paths in curated attribution files.

Sync accepted attribution claims into an existing catalog:

```bash
export CATALOG=data/build/reader/catalog.duckdb

just cli reader --catalog $CATALOG sync-metadata-attributions \
  --metadata-attribution-dir data/curated/reader_attributions \
  --output json
```

Query the accepted claims:

```bash
just cli reader --catalog $CATALOG attributions --output json
just cli reader --catalog $CATALOG attributions --agent Chanakya --output json
just cli reader --catalog $CATALOG attributions --relation-type attributed_author --output json
```

Find works through display authors plus accepted attribution claims:

```bash
just cli reader --catalog $CATALOG works --attributed-to Chanakya --output json
```
