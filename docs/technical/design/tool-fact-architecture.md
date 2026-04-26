# Tool Fact Architecture

Tool facts are normalized projections over backend outputs.

## Current Implementation

The current implementation uses claim triples rather than a separate fact table.

```text
backend response
  → extraction
  → derivation
  → claim/triples
```

## Fact Shape

The useful common shape is:

- subject
- predicate
- object
- metadata/evidence

This aligns with `docs/technical/predicates_evidence.md`.

## Design Direction

Do not introduce a parallel fact system until claim triples prove insufficient. Semantic reduction should consume existing claim triples first.
