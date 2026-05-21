# Diogenes Backend

Diogenes supplies Greek and Latin dictionary data, especially Lewis & Short and
Liddell & Scott entries. It also backs Greek/Latin source-backed paradigm tables
through the Diogenes `do=inflect` path.

## Requirement

Diogenes must be running locally, usually at:

```text
http://localhost:8888
```

## Runtime Role

Diogenes participates in:

```text
fetch.diogenes → extract.diogenes.html → derive.diogenes.morph → claim.diogenes.morph
```

Claims can include:

- lexeme senses
- glosses
- citations
- morphology features when present

## Debugging

```bash
just cli parse diogenes lat lupus --format pretty
just cli plan-exec lat lupus
just cli triples-dump lat lupus diogenes
just cli paradigm grc logos --output json
```

Diogenes dictionary evidence may also contribute to word-index and reader
workflows through local databuild/index steps, depending on which source indexes
are present.

## Testing

Use fixture-backed tests for parser and claim behavior. Live Diogenes should be reserved for integration checks.
