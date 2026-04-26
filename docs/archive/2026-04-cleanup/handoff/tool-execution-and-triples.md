# Tool Execution + Triples — Canonical Handoff

Purpose: single source of truth for the current executor/claims state and the triples projection direction. Use this instead of the older handoff notes.

## Current Implementation Snapshot
- Staged executor in `src/langnet/execution/executor.py` runs fetch → extract → derive → claim with cache reuse via `PlanResponseIndex`; effect dataclasses exist for extraction/derivation/claim with provenance (`src/langnet/execution/effects.py`).
- DuckDB schema/indices in `src/langnet/storage/schemas/langnet.sql` plus `extraction_index.py`, `derivation_index.py`, `claim_index.py`; raw/extraction/derivation/claim IDs are deterministic.
- Registry supports real handlers when available and stubs as fallback (`src/langnet/execution/registry.py`, `.../handlers_stub.py`).
- Handlers: Diogenes path is wired; Whitaker + CLTK run for Latin via `plan-exec` but triple projection is still rough (Whitaker mixes headword/form subjects; CLTK emits lemmas only). Other tools (Heritage/CDSL) still rely on stubs.
- CLI: `just cli plan-exec <lang> <word> [--use-stub-handlers|--no-stub-handlers] [--no-cache]` runs normalize → plan → execute and prints counts; data layout separates `data/build` (artifacts) and `data/cache` (ephemeral), with `just clean-cache`.
- Tests: `tests/test_execution_executor.py` covers executor flow, stub registry, and Diogenes E2E claims; more fixture-based tests are needed for Whitaker/CLTK and cache determinism.

## Open Gaps / Priorities (ordered)
1) **Real handlers + registry**: Finish Whitaker/Heritage/CLTK/CDSL handlers using generated protos; keep stubs only when `--use-stub-handlers` is set. Add handler versioning to memo keys.
2) **Node-level memoization**: Hash per node (payload + handler version) so extract/derive/claim can short-circuit even when the plan hash changes.
3) **Claim/triple schema**: Finalize subject/predicate/value + evidence shape; ensure provenance_chain is populated and domains/register/source_ref travel with values.
4) **Triples projection**: Implement scoped triples per `docs/technical/semantic_triples.md` and `docs/plans/active/tool-fact-indexing.md` (see below).
5) **CLI + UX**: Improve `plan-exec` output (skip reasons, cache hits, claim details), add `effects show` inspector and a small “dump triples for a word” helper.
6) **Fixtures/tests**: Add mock-backed executor tests per language, small CDSL/CTS fixtures, regression for deterministic IDs and memo hits.

## Triples Projection Direction (key points)
- Use clean nodes (form/headword/sense) with evidence in metadata, not in IDs. Keep `has_form` literal when using opaque form ids.
- Whitaker (highest priority): Form → `inflection_of` headword; scoped predicates per anchor (form/interp/lex/sense); add `variant_of` for secondary lemmas; include `has_sense` on lex nodes with evidence; keep `raw_text`.
- Diogenes: Project morph entries to form nodes + `inflection_of`; dictionary blocks to headword `has_sense`; citations to `has_citation`. Keep `raw_html` and chunk map.
- CLTK: Form → lemma `inflection_of`, lemma `has_pronunciation`, `has_sense` from Lewis lines. Keep raw payload.
- Follow predicate/evidence rules in `docs/technical/semantic_triples.md` and `docs/plans/active/tool-fact-indexing.md`.

## Interlocks
- Semantic reduction consumes claims; keep gloss/citation separation and provenance intact so reducers have clean WSUs.
- Dictionary parsing parsers should be reused inside derive/claim handlers to avoid “gloss + citation mashed” outputs.
- Stubs: emit placeholder claims flagged as stubs to avoid polluting reducers when assets are missing (e.g., no CDSL DB).

## Endpoint/Asset Notes
- Diogenes parse default: `http://localhost:8888/Perseus.cgi` (planner builds `fetch.diogenes` calls).
- Heritage base default: `http://localhost:48080/cgi-bin/skt/sktreader` (configurable).
- Whitaker binary expected on PATH as `whitakers-words`/`words`; accessed via `SubprocessToolClient`.
- CDSL DBs live in `data/build/cdsl_<dict>.duckdb` (AP90 available; MW pending).

## Quick Commands
- Clear caches: `just clean-cache`.
- End-to-end Latin sanity (no cache): `just cli plan-exec lat lupus --no-cache --use-stub-handlers` (swap `--no-stub-handlers` to force real handlers).
- Small CDSL build: `just cli databuild cdsl AP90 --limit 1000 --batch-size 500`.
- Small CTS build: `just cli databuild cts --max-works 1`.

## Immediate Next Steps
1) Wire handler registry with real Whitaker/CLTK/Heritage/CDSL handlers (with versioned memo keys); keep stubs only behind the flag.
2) Implement scoped triple emission for Whitaker (form→interp→lex→sense anchors) and mirror for Diogenes/CLTK; adopt shared predicate/evidence constants.
3) Add fixture-backed executor/triple tests and a `plan-exec` UX pass (skip reasons, cache hits, claim dump).
