# Semantic Triples Implementation Handoff

Use this as the starting point to emit scoped triples from each tool. It points to the canonical rules, current state, and what to build next.

## Canonical Rules & Constants
- Anchors/predicates/evidence: `docs/technical/predicates_evidence.md` (JSON export: `docs/technical/predicates_evidence.json`).
- Scoped anchors & flat facts: `docs/technical/triples_txt.md`.
- Triple projection model: `docs/technical/semantic_triples.md`.
- Pipeline stages (fetch→extract→derive→claim): `docs/technical/design/tool-response-pipeline.md`.

## Current State (Executor/Handlers)
- Status and gaps: `docs/handoff/tool-execution-and-triples.md`.
- Executor/registry/stubs: `src/langnet/execution/*`, `registry.py`, `handlers_stub.py`.
- CLI sanity: `just cli plan-exec <lang> <word> [--use-stub-handlers|--no-stub-handlers] [--no-cache]`; clear caches with `just clean-cache`.

## Work Plan (follow this)
- Active plan: `docs/plans/active/tool-fact-indexing.md` (Q1 tasks: predicates/evidence alignment, per-tool projections, memoization, CLI inspect).

## What to Implement per Tool
- **Whitaker** (highest priority): form→interp→lex→sense anchors; `has_interpretation/realizes_lexeme` for inflection links; morph qualifiers; `variant_form` for secondary lemmas; `has_sense/gloss` on lex/sense; keep `raw_text` + evidence.
- **Diogenes**: morph entries → form nodes + morph qualifiers; dictionary blocks → lex/sense `has_sense/gloss`; citations → `has_citation` with evidence; keep `raw_html` + chunk map.
- **CLTK**: form→lemma via `realizes_lexeme`; `has_pronunciation`; Lewis lines as `has_sense/gloss`; keep raw payload.
- **Heritage/CDSL**: reuse parsers; emit sense facts with domains/register/root/source_ref; gate with stubs when DBs absent.

## Provenance & Schema
- Use predicate/evidence constants for claim payloads and memo hashes.
- Evidence block per triple: `source_tool`, `call_id`, `response_id`, `extraction_id`, `derivation_id`, `claim_id`, optional `raw_ref/raw_blob_ref/source_ref`.
- Do not bake provenance into IDs; anchors are scoped per `predicates_evidence.md`.

## Tests & Fixtures
- Fixture-backed executor/triple tests per tool (no network); assert deterministic anchors/claim IDs and cache hits.
- Golden snapshots for agni/lupus/logos once projections are in place.

## Quick Commands
- Run plan-exec: `just cli plan-exec lat lupus --no-cache --no-stub-handlers` (or `--use-stub-handlers` if assets missing).
- Clear caches: `just clean-cache`.

## Navigation Shortcuts
- Rules/constants: `docs/technical/predicates_evidence.md`, `docs/technical/triples_txt.md`, `docs/technical/semantic_triples.md`.
- Status/gaps: `docs/handoff/tool-execution-and-triples.md`.
- Work tracker: `docs/plans/active/tool-fact-indexing.md`.
