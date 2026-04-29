# Codesketch Deletion Roadmap

**Status:** COMPLETE  
**Date:** 2026-04-28  
**Feature Area:** infra  
**Owner Roles:** @architect for scope, @sleuth for dependency checks, @coder for fixture ports, @auditor for deletion readiness

## Purpose

Delete `codesketch/` without losing useful exploratory work. The working rule is
simple: nothing canonical should remain in `codesketch/`; anything useful should
be ported, converted into current fixtures, or captured in a concrete plan.

This roadmap follows the audit in
`docs/plans/active/infra/codesketch-retirement-audit.md` and turns it into an
execution sequence.

## Current State

Completed across the retirement pass:

- Ported the Whitaker line parsers into
  `src/langnet/parsing/whitakers/lineparsers.py`.
- Added reducer coverage in `tests/test_whitakers_lineparsers.py`.
- Removed the old runtime dependency from the Whitaker handler.
- Removed legacy `just` recipes that read `codesketch/`.
- Ported the Diogenes zombie reaper entry point into
  `src/langnet/diogenes/cli_util.py`.
- Deleted the safe V1 code shells and generated fuzz outputs from
  `codesketch/`.
- Captured the first Foster display-label slice in
  `src/langnet/pedagogy/foster.py` and
  `docs/plans/active/pedagogy/foster-display-vocabulary.md`.
- Deleted `codesketch/src/langnet/foster/` after capturing label maps and
  planning the remaining display work.
- Opened the CDSL source-structure plan in
  `docs/plans/active/skt/cdsl-entry-grammar-plan.md`.
- Captured Heritage morphology parser expectations in
  `tests/test_heritage_salvage.py`.
- Captured Sanskrit normalization edge cases for Harvard-Kyoto vs. SLP1
  detection in `tests/test_normalization_pipeline.py`.
- Deleted `codesketch/src/langnet/heritage/`,
  `codesketch/src/langnet/normalization/`, and `codesketch/src/langnet/engine/`
  after that capture.
- Captured semantic reducer overlap concepts in
  `src/langnet/reduction/similarity.py` and
  `tests/test_semantic_similarity.py`. Exact reduction remains the conservative
  default; similarity clustering is opt-in.
- Captured citation preservation and Perseus-to-CTS conversion in
  `tests/test_citation_preservation.py`, with follow-up hydration work tracked
  in `docs/plans/active/infra/citation-resolution-plan.md`.
- Added `src/langnet/citation/resolver.py` as the maintained read-only CTS
  DuckDB resolver. It finds `LANGNET_CTS_DB`, `data/build/cts_urn.duckdb`, or
  `~/.local/share/langnet/cts_urn.duckdb` and keeps unresolved citations
  source-visible.
- Captured the remaining Cologne/CDSL XML lessons in
  `src/langnet/execution/handlers/cdsl.py`,
  `tests/test_cdsl_triples.py`, and
  `docs/plans/active/skt/cdsl-entry-grammar-plan.md`: page refs, `ab`
  abbreviations, compound hints, declension markers, explicit root markers,
  `ls` references, and `s1` cross references.

The remaining tests, fixtures, and examples were reviewed and deleted after
their useful patterns were captured or rejected.

## Phase 1: Safe Cleanup Sweep

Status: complete for the initial pass.

Deleted as superseded or already captured:

- V1 adapters, backend adapter, engine core, ASGI, CLI, schema, config, health,
  validation, and old common types.
- Old Classics Toolkit and Diogenes core implementations.
- Old indexer scaffolding superseded by current DuckDB/CTS build paths.
- Old Whitaker parser sketch after porting the reducer classes.
- Generated `codesketch/examples/debug/fuzz_results*` output directories.

Verification for this phase:

```bash
rg -n "codesketch" src tests justfile README.md GETTING_STARTED.md docs --glob '!docs/archive/**'
just test test_whitakers_lineparsers test_whitakers_triples test_source_text_analysis
LANGNET_DATA_DIR=examples/debug/validation-data just validate-stabilization
```

The `rg` command may still report roadmap and audit references. It should not
report runtime imports, active recipes, or production dependencies.

## Phase 2: Fixture Capture

Goal: preserve high-value examples before more deletion.

Tasks:

- Migrate selected Whitaker golden line-parser fixtures from
  `codesketch/tests/fixtures/whitakers/` into maintained tests if they cover
  cases not already represented.
- Migrate selected CDSL XML/body examples into the source-entry fuzz fixture set,
  especially `key1`, `key2`, `lex`, `info`, `s`, `ls`, `s1`, etymology/root
  markers, page references, and source abbreviations.
  Representative synthetic coverage now lives in `tests/test_cdsl_triples.py`;
  the remaining task is real-entry fuzz expansion, not preserving Cologne code.
- Keep the corrected Sanskrit case numbering covered in maintained CDSL and
  Foster tests.
- Continue reviewing old Heritage tests only for fixtures not covered by
  `tests/test_claim_contracts.py`, `tests/test_heritage_salvage.py`, and
  encounter snapshots.
- Continue reviewing old Sanskrit normalization tests only for edge cases not
  covered by `tests/test_normalization_pipeline.py`.
- Migrate semantic reducer examples only as current WSU clustering tests, not as
  old schema tests.

Acceptance:

```bash
just test test_whitakers_lineparsers test_cdsl_triples test_source_text_analysis
just test test_normalization_pipeline test_claim_contracts
```

## Phase 3: Planned Integrations

Goal: convert useful ideas into current architecture plans or implementation
tasks.

Plans to create or update:

- CDSL dictionary-entry grammar and fuzzing plan.
  The next CDSL work should use Lark grammar coverage where practical and
  classify ambiguous sections into learner-useful segments.
- Foster display vocabulary plan.
  The useful output is a pedagogy-facing label layer over current morphology
  rows/triples, not a return to the old backend payload shape.
- CDSL source-structure plan.
  The useful output is a grammar/classifier path over current CDSL rows and
  source-entry metadata, not a return to the old Cologne index abstraction.
  First XML metadata capture is implemented in the current CDSL handler.
- Semantic reduction clustering plan.
  The useful output is deterministic grouping over current
  `WitnessSenseUnit` objects: normalized tokens, source priority, mode
  thresholds, stable bucket IDs, and confidence calculation.
  First slice implemented in `src/langnet/reduction/similarity.py`.
- Citation resolver plan.
  The useful output is optional citation hydration that preserves raw source
  citation strings when no resolver match exists. First preservation slice is
  covered in `tests/test_citation_preservation.py`; deeper hydration is tracked
  in `docs/plans/active/infra/citation-resolution-plan.md`.
- Heritage and Sanskrit normalization capture plan.
  This should explicitly keep Sanskrit parity with Latin and Greek by making
  Heritage/CDSL normalization fixtures part of the same verification loop.

Acceptance:

- Every retained `codesketch/` subsystem is linked to a live plan, ported into
  `src/`, or explicitly rejected in the audit.
- The plans specify current `src/` ownership and test targets.
- Remaining old tests/examples were reviewed as historical V1 material. Useful
  cases are covered by maintained tests and plans; the rest depend on deleted
  sketch modules or obsolete command shapes.

## Phase 4: Remaining Code Deletion

After Phase 2 and Phase 3 are complete, delete retained implementation sketches
whose useful parts have been captured. The implementation sketch set is now
empty under `codesketch/src/langnet/`.

Examples can be deleted once their useful command shapes or input data have
been either migrated or rejected. This is now complete:

- `codesketch/examples/aisuite_examples/`
- `codesketch/examples/example/`
- `codesketch/examples/debug/`
- one-off scripts under `codesketch/examples/`

The remaining `codesketch/tests/` files are obsolete V1 tests. Their useful
expectations have been captured in maintained tests for Whitaker line parsers,
Foster labels, Heritage parsing, Sanskrit normalization, semantic similarity,
CTS citation resolution, and CDSL XML metadata.

Acceptance:

```bash
rg -n "codesketch" src tests justfile README.md GETTING_STARTED.md docs --glob '!docs/archive/**'
just test test_whitakers_lineparsers test_whitakers_triples test_source_text_analysis test_cdsl_triples
LANGNET_DATA_DIR=examples/debug/validation-data just validate-stabilization
```

## Phase 5: Final Tree Deletion

Delete the remaining `codesketch/` directory after:

- no production code imports it;
- no package entry point resolves only to sketch code;
- no `just` recipe depends on it;
- all useful tests and fixtures are in maintained locations;
- all deferred ideas are in active or todo plans;
- full stabilization validation passes.

Status: complete. `codesketch/` was deleted after the 2026-04-29 stabilization
pass.

Final check:

```bash
test ! -d codesketch
just lint-all
just test-fast
LANGNET_DATA_DIR=examples/debug/validation-data just validate-stabilization
```

## Guardrails

- Do not port old subsystems wholesale.
- Do not preserve dead architecture for sentiment.
- Keep learner-facing value as the deciding criterion: retrieval hit rate,
  meaningful glosses, morphology clarity, citation preservation, and Sanskrit
  parity.
- Prefer small fixture-backed integrations over broad rewrites.
