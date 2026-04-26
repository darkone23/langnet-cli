# Semantic Reduction MVP

**Status:** ⏳ TODO  
**Feature Area:** semantic-reduction  
**Owner Roles:** @architect for design, @coder for implementation, @auditor for contract review

## Goal

Build the first runtime reducer over claim triples.

Input:

- `ClaimEffect` values from `plan-exec` or indexed claims.
- Triples with `has_sense` and `gloss`.

Output:

- Witness Sense Units.
- Deterministic sense buckets.
- Evidence links back to original claims.

## Scope

### In

- Dataclasses for `WitnessSenseUnit`, `SenseBucket`, and `ReductionResult`.
- Extraction from claim triples.
- Exact-match and simple deterministic near-match grouping.
- Service-free fixtures for `lupus` and `agni`.

### Out

- Embeddings.
- LLM-generated semantic constants.
- Passage-level disambiguation.
- Hydration/citation expansion.

## Acceptance Criteria

- Same input claims produce identical bucket IDs across runs.
- Every WSU points back to a claim ID and evidence block.
- No witness appears in two buckets.
- `just lint-all` and targeted semantic reducer tests pass.

## First Junior Slice

Create a hand-written claim fixture with 3–5 triples and expected WSUs. Do not implement clustering in the same task.
