# Tool Response Pipeline

The runtime pipeline is:

```text
fetch → extract → derive → claim
```

## Fetch

Calls a backend or local data source and stores a `RawResponseEffect`.

Examples:

- Diogenes HTTP response
- Heritage HTML response
- Whitaker plain text
- CDSL DuckDB JSON rows

## Extract

Parses raw response bytes into structured data. Extraction should preserve raw references.

## Derive

Normalizes extracted data into handler-specific derivations. This is where backend quirks should be made explicit.

## Claim

Projects derivations into stable claim values and triples with evidence.

Claims are the intended input for semantic reduction.

## Testing Rule

Every backend should have at least one fixture-backed path through extract → derive → claim.
