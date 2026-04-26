# Classifier and Reducer Design

## Goal

Convert evidence-backed claim triples into learner-facing sense buckets.

## Current Runtime Boundary

Implemented:

- handlers emit claims/triples
- core handlers have fixture-backed claim contract tests

Not implemented:

- Witness Sense Unit extraction
- deterministic sense buckets
- semantic constants
- embedding or LLM similarity

## MVP Input

Claims containing triples:

- `lex:* has_sense sense:*`
- `sense:* gloss "..."`;
- optional citations/evidence in `metadata.evidence`

## MVP Output

```python
WitnessSenseUnit
SenseBucket
ReductionResult
```

Each bucket must preserve witness IDs and evidence.

## Reduction Algorithm

Start deterministic:

1. Extract WSUs from `has_sense` + `gloss`.
2. Normalize gloss text conservatively.
3. Group exact normalized matches.
4. Add simple Jaccard/substring grouping only with explicit tests.
5. Emit stable bucket IDs from normalized contents and witness IDs.

## Non-Goals For MVP

- embeddings
- semantic constant registry
- passage-aware ranking
- generated definitions

## Acceptance Criteria

- same input produces same output
- no witness appears in two buckets
- buckets contain evidence references
- tests use service-free fixtures
