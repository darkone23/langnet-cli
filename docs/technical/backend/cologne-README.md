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

## Data

CDSL data is not assumed to be present by default. Build local data with the project’s `databuild` commands when needed.

```bash
just cli-databuild --help
```

## Debugging

```bash
just triples-dump san agni cdsl
```

## Testing

Fixture-backed CDSL claim coverage lives in `tests/test_cdsl_triples.py` and does not require a DuckDB CDSL database.
