# Classifier and Reducer Design

## Goal

Convert evidence-backed claim triples into learner-facing sense buckets.

## Current Runtime Boundary

Implemented:

- handlers emit claims/triples
- core handlers have fixture-backed claim contract tests
- Witness Sense Unit extraction over `has_sense` + `gloss`
- deterministic exact-match sense buckets
- `encounter` display over reduced buckets
- accepted-output snapshots for representative word encounters

Not implemented:

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

## Current Encounter Ranking Policy

The current learner-facing display order is intentionally simple and
fixture-backed:

1. Cache-backed English translation buckets rank before untranslated source-language buckets.
2. Within the same translation class, buckets with more witnesses rank before weaker buckets.
3. Remaining ties use deterministic gloss text ordering.

This is not yet a broad source-quality model. Do not add source-quality,
near-match, or semantic-similarity ranking without accepted-output tests that
explain the intended behavior.

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
