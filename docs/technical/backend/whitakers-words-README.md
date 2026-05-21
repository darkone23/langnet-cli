# Whitaker's Words Backend

Whitaker's Words supplies Latin morphology, lemmas, and senses. It is also a
useful Latin source for word-index builds because its output gives compact
headword and morphology evidence.

## Requirement

The binary is expected at:

```text
~/.local/bin/whitakers-words
```

Check local discovery with:

```bash
just cli doctor --output json
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
just cli triples-dump lat amarem whitakers
just cli word-index sections lat --output json
```

## Testing

See `tests/test_whitakers_triples.py`.
