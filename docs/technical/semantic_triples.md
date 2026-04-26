# Semantic Triples

Semantic triples are the bridge between backend-specific outputs and future learner-facing semantic reduction.

## Purpose

Backends disagree in shape and detail. Triples provide a small common projection:

```json
{
  "subject": "lex:lupus",
  "predicate": "has_sense",
  "object": "sense:lex:lupus#...",
  "metadata": {
    "evidence": {
      "source_tool": "diogenes",
      "claim_id": "..."
    }
  }
}
```

Raw payloads are still preserved. Triples are not a lossy replacement; they are a queryable projection for reduction and display.

## Modeling Rules

- Forms are surface observations: `form:amarem`.
- Interpretations scope ambiguity: `interp:form:amarem→lex:amo#verb`.
- Lexemes hold lexical facts: `lex:amo#verb`.
- Sense nodes hold gloss facts: `sense:lex:amo#verb#...`.
- Evidence stays in metadata.

## Current Uses

- Whitaker: form → interpretation → lexeme → morphology/sense.
- Diogenes: lexeme → sense/gloss/citation.
- CLTK: pronunciation, Lewis lines, and inflection links.
- Heritage: morphology objects.
- CDSL: Sanskrit dictionary senses and source references.

## Next Use

The semantic reducer should consume triples, not raw backend payloads:

```text
has_sense + gloss triples
  → Witness Sense Units
  → deterministic sense buckets
  → learner-facing meaning groups
```

## Canonical Contract

Use `docs/technical/predicates_evidence.md` for predicates, anchors, and evidence fields.
