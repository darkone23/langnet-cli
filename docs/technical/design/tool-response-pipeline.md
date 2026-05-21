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
- DICO, Gaffiot, Bailly, and Lewis 1890 DuckDB rows
- CTS index rows
- reader catalog/search rows and word-index rows when exposed through CLI JSON

## Extract

Parses raw response bytes into structured data. Extraction should preserve raw references.

## Derive

Normalizes extracted data into handler-specific derivations. This is where backend quirks should be made explicit.

## Claim

Projects derivations into stable claim values and triples with evidence.

Claims are the intended input for semantic reduction.

Reader catalog/search, word-index, paradigm, and translation-cache commands may
return purpose-built JSON schemas rather than claim triples. The SvelteKit
adapter should consume those CLI JSON contracts directly instead of inventing a
parallel backend contract.

## Testing Rule

Every backend should have at least one fixture-backed path through extract → derive → claim.
