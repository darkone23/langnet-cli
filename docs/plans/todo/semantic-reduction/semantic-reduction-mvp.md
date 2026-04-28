# Semantic Reduction Refinement

**Status:** MVP implemented; refinement pending  
**Feature Area:** semantic-reduction  
**Owner Roles:** @architect for design, @coder for implementation, @auditor for contract review

## Goal

Refine the first runtime reducer over claim triples.

Implemented baseline:

- `ClaimEffect` values from `plan-exec` or indexed claims.
- WSU extraction from triples with `has_sense` and `gloss`.
- Deterministic exact buckets.
- Evidence links back to original claims.
- `langnet-cli encounter` display over reduced buckets.

## Scope

### In For Next Refinement

- Reader-form eval fixtures.
- Compact gloss display metadata.
- Source-aware ranking backed by accepted-output tests.
- More structured source fields for long dictionary entries.

### Out

- Embeddings.
- LLM-generated semantic constants.
- Passage-level disambiguation.
- Hydration/citation expansion.

## Acceptance Criteria

- Same input claims continue to produce identical bucket IDs across runs.
- Every WSU points back to a claim ID and evidence block.
- No witness appears in two buckets.
- Reader-form eval fixtures catch known misses before ranking changes land.
- `just lint-all` and targeted semantic reducer tests pass.

## First Refinement Slice

Create reader-form fixtures for `virumque`, `μῆνιν`, `θεὰ`, and
`karma/karman`. Assert expected top-1/top-3 lemma and rough gloss behavior
without hardcoding full terminal output.
