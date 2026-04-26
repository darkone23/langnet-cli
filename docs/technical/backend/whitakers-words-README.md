# Whitaker's Words Backend

Whitaker's Words supplies Latin morphology, lemmas, and senses.

## Requirement

The binary is expected at:

```text
~/.local/bin/whitakers-words
```

## Runtime Role

Whitaker participates in:

```text
fetch.whitakers → extract.whitakers.lines → derive.whitakers.facts → claim.whitakers
```

Claims can include:

- form interpretations
- lexeme realization
- morphology features
- source senses/glosses

Whitaker is currently one of the best fixtures for scoped interpretations because Latin forms are often ambiguous.

## Debugging

```bash
just cli parse whitakers lat amarem --format json
just triples-dump lat amarem whitakers
```

## Testing

See `tests/test_whitakers_triples.py`.
