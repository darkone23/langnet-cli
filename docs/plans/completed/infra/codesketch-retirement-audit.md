# Codesketch Retirement Audit

**Status:** COMPLETE  
**Date:** 2026-04-28  
**Feature Area:** infra  
**Owner Roles:** @architect for scope, @sleuth for dependency audit, @coder for ports, @auditor for deletion readiness

## Purpose

Retire `codesketch/` as a project dependency without losing useful exploratory
patterns. The target state is:

- no runtime imports from `codesketch/`;
- no `just` recipes that require `codesketch/`;
- any still-useful implementation pattern either ported into `src/langnet/`,
  converted into docs/fixtures, or explicitly rejected;
- `codesketch/` can be deleted without changing behavior.

## Current Findings

The directory was not only dead reference material. One production path still
depended on it before this audit:

- `src/langnet/execution/handlers/whitakers.py` dynamically loaded
  `codesketch/src/langnet/whitakers_words/lineparsers`.

That dependency is now being captured under:

- `src/langnet/parsing/whitakers/lineparsers.py`
- `src/langnet/parsing/whitakers/grammars/*.ebnf`
- `tests/test_whitakers_lineparsers.py`

The remaining review found no other runtime imports from `codesketch/`. The
useful patterns were captured as maintained code, tests, or plans before the
directory was removed.

## Cleanup Pass: 2026-04-28

The first safe deletion sweep removed superseded implementation sketches and
generated debug output:

- V1 adapters, backend adapter, engine core, ASGI, CLI, schema, config, health,
  validation, and old common types.
- Old Classics Toolkit and Diogenes core implementations.
- Old indexer scaffolding.
- Old Whitaker parser sketch after the line reducers were ported.
- Generated `codesketch/examples/debug/fuzz_results*` directories.

One package-entry issue was found and fixed before deletion: `pyproject.toml`
advertised `langnet-dg-reaper = "langnet.diogenes.cli_util:cli"`, while the
module still lived only in `codesketch/`. The reaper utility now lives in
`src/langnet/diogenes/cli_util.py`.

The completed deletion sequence is tracked in:

- `docs/plans/completed/infra/codesketch-deletion-roadmap.md`

Additional capture completed after the first cleanup:

- Foster mappings now live in `src/langnet/pedagogy/foster.py`, with tests in
  `tests/test_foster_pedagogy.py`.
- The Foster plan lives in
  `docs/plans/completed/pedagogy/foster-display-vocabulary.md`.
- `codesketch/src/langnet/foster/` has been deleted after the mapping capture.
- The CDSL source-structure plan lives in
  `docs/plans/completed/skt/cdsl-entry-grammar-plan.md`.
- CDSL body parsing now uses standard Sanskrit case numbering and tests
  compound `info lex` gender sets.
- Heritage morphology parser behavior and Heritage semicolon query planning are
  captured in `tests/test_heritage_salvage.py`.
- Sanskrit Harvard-Kyoto vs. SLP1 normalization edge cases are captured in
  `tests/test_normalization_pipeline.py`.
- `codesketch/src/langnet/heritage/`, `codesketch/src/langnet/normalization/`,
  and `codesketch/src/langnet/engine/` have been deleted after capture.
- Semantic similarity concepts from the old reducer are captured in
  `src/langnet/reduction/similarity.py` and
  `tests/test_semantic_similarity.py`.
- Citation preservation and direct Perseus-to-CTS conversion are captured in
  `tests/test_citation_preservation.py`; deeper hydration is tracked in
  `docs/plans/todo/infra/citation-resolution-plan.md`.
- The maintained CTS resolver now lives in `src/langnet/citation/resolver.py`
  and reads the local DuckDB index in read-only mode.
- Cologne/CDSL XML lessons are captured in current CDSL code and tests: page
  refs, `ab` abbreviations, compound hints, declension markers, explicit roots,
  `ls` references, and `s1` cross references.

## Decision Summary

| Decision | Areas | Rationale |
| --- | --- | --- |
| Safe to delete after documentation cleanup | V1 adapters, V1 engine, V1 CLI/API wrappers, old validation module, old examples/debug outputs | Current `src/` architecture has planner, executor, staged handlers, CLI commands, and current fuzz/debug locations. These files should not be ported wholesale. |
| Already captured in `src/` | Whitaker line parsers, structured logging, Heritage client/html extraction, CTS builder/resolver, parts of Sanskrit normalization, CDSL body helpers, CDSL Cologne XML lessons, opt-in semantic similarity helpers | Equivalent or better runtime paths exist. Keep tests on `src/`, not old files. |
| Needs explicit integration plan before deletion | Foster display labels, selected Heritage morphology fixtures, selected Sanskrit normalization fixtures, selected Whitaker golden fixtures, real CDSL fuzz expansion | These are useful ideas or fixtures, but not production dependencies. Capture the useful part in focused plans/tests before deleting the sketch. |

## Detailed Pattern Inventory

| Codesketch area | Current project status | Retirement action |
| --- | --- | --- |
| `whitakers_words/lineparsers` | Runtime dependency before this audit; now ported | Done: ported to `src/langnet/parsing/whitakers/` with reducer tests. Remaining task: optionally migrate a small golden fixture set from `codesketch/tests/fixtures/whitakers/`. |
| `whitakers_words/core.py` and `enums.py` | Superseded by staged fetch/extract/derive/claim handler and source parser reducers | Reject monolithic core. Keep the code-to-label maps already in `execution/handlers/whitakers.py`; migrate only selected golden fixtures if useful. |
| `adapters/*`, `backend_adapter.py`, `engine/core.py` | Superseded by `ToolPlanner`, `execute_plan_staged`, and source-specific staged handlers | Safe to delete after audit. The old composite adapter timing pattern is not worth porting; current executor should own timing/provenance. |
| `diogenes/core.py` | Superseded by `execution/handlers/diogenes.py`, `diogenes_parser.py`, and current Diogenes adapters | Safe to delete as implementation. If any old tests expose missing citation cases, migrate those cases to current parser/handler fixtures. |
| `classics_toolkit/core.py` | Superseded by current CLTK client/handler and parsed Lewis integration | Safe to delete as implementation. No direct port needed. |
| `heritage/client.py`, `html_extractor.py`, `velthuis_converter.py`, `abbr_data.json` | Already represented in `src/langnet/heritage` and `execution/handlers/heritage.py`; deleted from sketch after salvage tests were added. | Done for source code. Continue reviewing old tests only for fixture cases not already represented. |
| `heritage/morphology.py`, `parameters.py`, `parsers.py`, `types.py` | Current Heritage staged handler covers morphology, segment grouping, fallback guesses, and dictionary URLs. Salvage tests now cover compact/text morphology parsing and semicolon Heritage planning. | Done for source code. Do not port service classes wholesale. |
| `cologne/*` | Current CDSL handler includes DuckDB lookup, IAST/SLP1 display, body metadata parsing, source segment typing, source notes, page-ref evidence, body XML abbreviations, compound/declension/root metadata, `ls` references, and `s1` cross references. | Done for source code. Remaining CDSL work is real-entry fuzz expansion under the Sanskrit plan, not preservation of the old Cologne abstraction. |
| `semantic_reducer/*` | Current reducer is claim/triple-native. Exact-gloss bucketing remains default, and opt-in similarity helpers now cover token normalization, Jaccard/Dice/cosine overlap, source priority, open/skeptic thresholds, stable bucket IDs, and clustering tests over current WSU models. | Done for source code. Keep future refinement in the semantic-reduction roadmap; do not keep the old sketch package. |
| `foster/*` | Deleted after the first label-map slice was captured in `src/langnet/pedagogy/foster.py`. Old tests remain as review material for rendering/wiring expectations. | Keep the plan, not the old subsystem. Remaining useful ideas are display rendering and optional CLI output wiring. |
| `normalization/*`, `engine/sanskrit_normalizer.py` | Current `src/langnet/normalizer` and Sanskrit tokenization/normalization paths are separate and already more aligned with staged planning. Deleted after adding Harvard-Kyoto/SLP1 regression coverage. | Done for source code. Continue with fixture-only review if old tests expose new reader-visible cases. |
| `citation/cts_urn.py` | Current `databuild/cts.py` builds the DuckDB index; `src/langnet/citation/resolver.py` reads it; Diogenes has direct CTS conversion for Perseus-like refs; tests require raw citation preservation. The old mapper has broader non-CTS abbreviation handling and DB-backed citation lookup. | Done for source code. Deeper staged hydration is tracked in the citation-resolution plan; grow abbreviation fixtures from tests, not sketch code. |
| `indexer/*` | Current `databuild/cts.py`, storage paths, and DuckDB indexes supersede old indexer scaffolding. `cdsl_indexer.py` was not the current path. | Safe to delete after confirming CTS builder tests remain green. No wholesale port. |
| `fuzz_results*`, `compare_tool_outputs.py`, parser demos | Historical debug/probe outputs and ad hoc examples | Safe to delete as files. Any still-useful real inputs should be copied into maintained fixtures under `tests/fixtures` or `examples/debug` generated by current commands. |
| `asgi.py`, `cli.py`, `core.py`, `schema.py`, `types.py`, `config.py`, `health.py` | V1 shell around the old architecture | Safe to delete. Current ASGI/CLI/schema/effects models live under `src/`. |
| `logging.py` | Current `src/langnet/logging.py` is effectively the same pattern | Already captured. Safe to delete. |
| `validation.py` | Basic language/tool/action validation | Safe to delete. Current Click parsing and planner validation cover the maintained CLI surfaces; add explicit validation helpers only if an API surface needs them. |

## Integration Plans To Create Or Update

These items should be opened as plans or added to existing active plans before
deleting `codesketch/`:

1. **CDSL dictionary-entry grammar plan**
   - Extend the active dictionary-entry grammar fuzz work with CDSL-specific
     XML/body cases.
   - Migrate selected old cases for `key1`/`key2`, `lex`, `info`, `s`, `ls`,
     `s1`, etymology/root markers, page refs, and source abbreviations.
   - Status: representative maintained coverage added to
     `tests/test_cdsl_triples.py`; real-entry fuzz expansion remains.
   - Acceptance: `test_cdsl_triples` plus new CDSL source-entry fuzz cases pass.

2. **Foster display vocabulary plan**
   - Port label maps and renderer tests into a current `src/langnet/pedagogy`
     or display module.
   - Consume morphology rows/triples, not old backend payloads.
   - Acceptance: learner display can show optional functional grammar labels
     while JSON still exposes exact grammatical predicates.

3. **Semantic reduction clustering plan**
   - Update `docs/plans/todo/semantic-reduction/semantic-reduction-mvp.md` with
     the old reducer concepts: token normalization, Jaccard/Dice/cosine,
     source priority, open/skeptic thresholds, deterministic bucket IDs, and
     confidence calculation.
   - Status: first slice implemented in `src/langnet/reduction/similarity.py`.
   - Acceptance: clustering tests run over current
     `langnet.reduction.models.WitnessSenseUnit`, not old schema objects.

4. **Citation resolver plan**
   - Decide whether CTS hydration is in scope for dictionary citations.
   - If yes, preserve useful old ideas: non-CTS abbreviation allowlist,
     author/work hint extraction, DB-backed author/work lookup, and betacode
     conversion.
   - Status: preservation plan created in
     `docs/plans/todo/infra/citation-resolution-plan.md`.
   - Acceptance: source citation strings remain preserved even when resolver
     cannot map them to CTS.

5. **Fixture migration pass**
   - Copy only high-value tests, not all old tests. Candidate fixture groups:
     Whitaker lineparser goldens, Sanskrit normalization edge cases, Heritage
     morphology/compound examples, CDSL XML/body examples, and semantic reducer
     clustering examples.
   - Status: high-value coverage has been captured in maintained tests. The
     remaining sketch tests import deleted V1 modules or exercise obsolete
     adapter/output shapes.
   - Acceptance: migrated fixtures live under `tests/fixtures` and are exercised
     by current test modules.

## Safe Deletion Set

The implementation sketch source has been removed. The remaining
`codesketch/tests/` and `codesketch/examples/` files are safe to delete because
their useful cases have been captured or explicitly rejected:

- Whitaker parser cases are covered by `tests/test_whitakers_lineparsers.py`.
- Foster label concepts are covered by `tests/test_foster_pedagogy.py` and the
  active Foster plan.
- Heritage morphology/connectivity lessons are covered by
  `tests/test_heritage_salvage.py` and current handler tests.
- Sanskrit normalization edge cases are covered by
  `tests/test_normalization_pipeline.py`.
- Semantic reduction lessons are covered by `tests/test_semantic_similarity.py`
  and the semantic-reduction roadmap.
- CTS citation lessons are covered by `tests/test_citation_preservation.py`,
  `tests/test_cts_citation_resolver.py`, and the citation-resolution plan.
- CDSL XML/body lessons are covered by `tests/test_cdsl_triples.py` and the
  active Sanskrit CDSL plan.
- Remaining examples demonstrate obsolete V1 imports or command shapes.

## Not Safe To Delete Without Capture

No remaining file blocks deletion after the 2026-04-29 capture pass.

## Deletion Criteria

Before deleting `codesketch/`, run:

```bash
rg -n "codesketch" src tests justfile README.md GETTING_STARTED.md docs --glob '!docs/archive/**'
just test test_whitakers_lineparsers test_whitakers_triples
LANGNET_DATA_DIR=examples/debug/validation-data just validate-stabilization
```

Deletion is ready when the first command has no live references outside archive
docs, or each remaining reference is explicitly marked historical.

## Guardrails

- Do not leave canonical code in `codesketch/`.
- Do not import from `codesketch/`.
- Do not delete it until useful patterns have been captured or intentionally
  rejected.
- Prefer small ports with fixture tests over large V1 subsystem migrations.
