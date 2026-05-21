# Semantic Reduction Refinement

**Status:** MVP implemented; first similarity refinement captured  
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
- Deterministic token-similarity helpers inspired by the retired prototype:
  - normalized token sets;
  - Jaccard/Dice-style overlap;
  - source-priority tie breaking;
  - open vs. skeptic thresholds;
  - stable bucket IDs independent of input order.

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

## Prototype Capture Notes

Keep concepts, not the old schema:

- Similarity should operate on current
  `langnet.reduction.models.WitnessSenseUnit` objects.
- Exact-gloss bucketing remains the conservative default.
- Broader clustering should be opt-in until real dictionary examples show
  acceptable precision.
- First capture slice lives in `src/langnet/reduction/similarity.py`, with
  regression coverage in `tests/test_semantic_similarity.py`.
- Tests should include cross-source near matches such as `fire`, `sacrificial
  fire`, and `fire deity`, plus clear non-matches such as `fire` vs. `water`.
- Sanskrit CDSL and DICO examples must be represented alongside Latin and Greek
  examples so the reducer does not optimize only for classical Latin/Greek
  dictionary prose.
