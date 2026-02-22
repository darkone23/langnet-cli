# Tool Fact Indexing: Implementation Roadmap

**Status**: Active Plan  
**Date**: 2026-02-15  
**Priority**: HIGH  
**Related**: `tool-fact-architecture.md`, `tool-response-pipeline.md`, `tool-fact-flow.md`, `docs/technical/semantic_triples.md`, `docs/technical/triples_txt.md`, `docs/technical/predicates_evidence.md`, `docs/handoff/tool-execution-and-triples.md`

## Canonical References
- Scoped anchors/predicates and flat-fact rules: `docs/technical/triples_txt.md`
- Triple projection + evidence model: `docs/technical/semantic_triples.md`
- Current executor/handler status: `docs/handoff/tool-execution-and-triples.md`
- Pipeline stage boundaries: `docs/technical/design/tool-response-pipeline.md`

## Goal

Emit scoped, provenance-backed triples/facts from every tool so the index-first query path has deterministic anchors/predicates and clean evidence. Queries hit the indexed claims first; tools are fetched only on cache miss or explicit refresh.

## Canonical Model (anchors, predicates, evidence)
- Anchors: `form:<surface>`, `interp:form:<surface>→lex:<lemma>#<pos>`, `lex:<lemma>#<pos>`, `sense:<lex>#<sense-key>`.
- Predicates: `has_interpretation`, `realizes_lexeme`, `pos`, `has_sense`, `gloss`, `variant_form`, `variant_of`, `has_pronunciation`, `has_citation`, plus `has_feature`/qualifiers for morph bundles (case/number/gender/person/tense/voice/mood/degree/declension/conjugation).
- Evidence: provenance chain from effects + `evidence/source_json` (tool, call_id/response_id, raw_ref/raw_blob_ref). Never bake provenance into IDs.
- Scoping rules: forms only link to interpretations; POS on interpretations (and optionally lex); senses live on lex/sense nodes; variants attach to lex.

## Current Context
- Executor + registry exist; Diogenes handlers are real, Whitaker/CLTK run for Latin but need scoped triples, Heritage/CDSL are stubbed. Claims carry raw payloads; triple projection must align to the scoped-anchor model.
- DuckDB schemas for raw/extraction/derivation/claim are present; predicate constants/evidence schema need to be published and enforced in handlers and memo hashes.

## Work Plan (2026 Q1)
1) **Predicate + evidence constants** (@architect @scribe)  
   Publish a canonical predicate list and evidence schema (refs above) and wire into handlers/tests. Deliverable: updated sections in `semantic_triples.md` and constants consumed by handlers.
2) **Whitaker triple projection** (@coder)  
   Emit scoped anchors (form→interp→lex→sense), `has_interpretation/realizes_lexeme` to represent `inflection_of`, morph qualifiers, `variant_form` for secondary lemmas, `has_sense/gloss` on lex/sense nodes; keep `raw_text`. Tests: fixture-backed Latin verb/pronoun ambiguity.
3) **Diogenes projection** (@coder @sleuth)  
   Morph entries → form nodes with morph qualifiers; dictionary blocks → lex/sense with `has_sense/gloss`; citations → `has_citation` with evidence; keep `raw_html` + chunk map. Tests: fixture HTML; deterministic anchors and claim IDs.
4) **CLTK projection** (@coder)  
   Form→lemma mapping via `realizes_lexeme`, `has_pronunciation`, Lewis lines as `has_sense/gloss`; keep raw payload. Tests: mocked CLTK responses.
5) **Heritage/CDSL projection** (@coder)  
   Reuse entry parsers; emit sense facts with domains/register/root/source_ref; guard with stubs when DBs absent. Tests: small XML/HTML fixtures (AP90/MW).
6) **Executor/registry memoization** (@coder)  
   Add handler-versioned node hashes so extract/derive/claim stages short-circuit; integrate predicate constants into hashing/validation. Tests: cache hit/miss determinism, claim shape validation.
7) **CLI/inspection** (@scribe @coder)  
   Add `effects show`/triples dump helpers; surface skip reasons/cache hits in `plan-exec`. Docs: update GETTING_STARTED/handbook with new commands and cache locations.

## Definition of Done
- All LAT/GRC/SAN tools emit scoped triples aligned to `semantic_triples.md` + `triples_txt.md`, with evidence preserved and deterministic anchors.
- Predicate/evidence constants are documented and enforced in handlers and tests.
- Executor node-level memoization respects handler versions; stubs remain behind flags.
- CLI exposes plan execution and triple inspection; fixtures cover core flows with stable IDs.
