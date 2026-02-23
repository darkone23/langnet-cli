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
- Triples dump helper: `just triples-dump lat lupus` now logs normalize/execute timings; CLTK is currently disabled there to avoid cold-start overhead (re-enable by toggling `include_cltk` in `.justscripts/triples_dump.py`).
- Parse-only helpers (pre-triples): `just parse diogenes|whitakers|cltk <lang> <word> [opt]` for raw parsed JSON; `just diogenes-parse <lang> <word>` is kept for convenience. Use these to inspect full dictionary hierarchy/morphology (Diogenes), Whitaker wordlists, or CLTK IPA/Lewis payloads.

## Work Plan (follow this)
- Active plan: `docs/plans/active/tool-fact-indexing.md` (Q1 tasks: predicates/evidence alignment, per-tool projections, memoization, CLI inspect).

## What to Implement per Tool
- **Whitaker** (highest priority): form→interp→lex→sense anchors; `has_interpretation/realizes_lexeme` plus `inflection_of` form→lex; morph qualifiers; code-to-label decoding for freq/age/area/geo/source and tense/voice/mood/number/case/gender/degree; pronoun/numeral subtypes; `variant_form` for secondary lemmas; `has_sense/gloss` on lex/sense; keep `raw_text` + evidence.
- **Diogenes**: morph entries → form nodes + morph qualifiers; dictionary blocks → lex/sense `has_sense/gloss`; citations → `has_citation` with evidence; keep `raw_html` + chunk map. (Implemented in `execution/handlers/diogenes.py`, wired in registry; jump refs now mapped to CTS URNs where possible, with original citation text stored in metadata.)
- **CLTK**: form→lemma via `realizes_lexeme`; `has_pronunciation`; Lewis lines as `has_sense/gloss`; keep raw payload. (Triples implemented in `execution/handlers/cltk.py`, but disabled in the triples-dump helper to avoid CLTK cold-start latency.)
- **Heritage/CDSL**: reuse parsers; emit sense facts with domains/register/root/source_ref; gate with stubs when DBs absent.

## Greek Path: Status + Next Steps
- Scope: Greek currently relies on Diogenes (LSJ + Perseus morph) and CLTK morphology; Whitaker has no Greek path, so expect fewer sources than Latin.
- Anchor normalization fixed: Diogenes/CLTK now share `normalize_greekish_token` (accent stripping, final-sigma folding, betacode collapse), so Greek lemmas/forms mint anchors like `lex:logos`/`form:logos` instead of `None`. Tests cover `λόγος`.
- Query normalization: keep UTF-8 input for CLTK, but convert to betacode for Diogenes fetch; strip accents when hashing anchors so `λόγος`/`λογος`/`*logos` converge.
- Normalization cache: Greek candidates are re-ranked on read (ω/ο folded, frequency tie-break) so stale cache rows no longer surface lower-frequency variants; `just cli normalize grc phos` now prefers `φῶς` even with cached results.
- LSJ projection: keep `entryid`/indent map from Diogenes blocks so Greek senses (e.g., `logos` 65 blocks) can be clustered; citations already carry CTS URNs in metadata—preserve `citation_ref` + text for LSJ abbreviations.
- CLTK Greek status: endpoint reachable but currently returns lemma-only payloads (empty IPA/blank Lewis lines) in this environment; plan to add a Greek morph/IPA source or spaCy-backed path for richer triples.
- Tests/fixtures: add `triples-dump grc logos diogenes` golden (anchors not `None`), and a CLTK Greek morph fixture that at least exercises `has_pronunciation`/`inflection_of` without Lewis lines.
- Quick checks once normalization is fixed: `just cli plan-exec grc logos --no-cache --no-stub-handlers` (Diogenes + CLTK), `just triples-dump grc logos diogenes` (fast) and `just triples-dump grc logos cltk` (CLTK warmup).
- Helper flags: `python ./.justscripts/tool_parse.py diogenes grc logos --normalize` uses the normalizer’s best candidate (betacode/Greek) for Diogenes; `python ./.justscripts/triples_dump.py grc logos diogenes --normalize` defaults to normalized queries (use `--no-normalize` to bypass). `just parse ...` now passes `--no-normalize` by default; add `--normalize` explicitly when you want the normalizer to pick the query form.

## Provenance & Schema
- Use predicate/evidence constants for claim payloads and memo hashes.
- Evidence block per triple: `source_tool`, `call_id`, `response_id`, `extraction_id`, `derivation_id`, `claim_id`, optional `raw_ref/raw_blob_ref/source_ref`.
- Do not bake provenance into IDs; anchors are scoped per `predicates_evidence.md`.

## Tests & Fixtures
- Fixture-backed executor/triple tests per tool (no network); assert deterministic anchors/claim IDs and cache hits.
- Golden snapshots for agni/lupus/logos once projections are in place.
- Needs: add deterministic fixtures for Diogenes/Whitaker/CLTK triples; add regression to check timing (e.g., client build skips CLTK unless enabled).

## Quick Commands
- Run plan-exec: `just cli plan-exec lat lupus --no-cache --no-stub-handlers` (or `--use-stub-handlers` if assets missing).
- Clear caches: `just clean-cache`.
- Triples dump (fast, Diogenes+Whitaker): `just triples-dump lat lupus` (CLTK disabled; flip `include_cltk` in `.justscripts/triples_dump.py` to re-enable, expect ~15s CLTK warmup).
- Parse only: `just parse diogenes lat lupus` (full entry hierarchy), `just parse whitakers lat lupus` (wordlist), `just parse cltk lat lupus` (IPA + Lewis lines).

## Verification Guide
1) Parse layer (pre-triples)
   - Diogenes: `just parse diogenes lat is` → expect `PerseusAnalysisHeader` + dictionary entries (e.g., ĕo, is) with block counts.
   - Whitaker: `just parse whitakers lat is` → expect wordlist with codeline terms (e.g., `is, ea, id`).
   - CLTK: `just parse cltk lat lupus` → expect IPA and Lewis lines in the parsed JSON.
   - Greek sanity: `just parse diogenes grc logos --normalize` (LSJ blocks + Perseus morph for λόγος); `just parse diogenes grc logos` exercises ASCII path; `just parse cltk grc logos --normalize` currently returns lemma-only payloads.
   These confirm full extraction before projection.
2) Triples layer
   - `just triples-dump lat is diogenes` → sense counts per lexeme and triples for morphology/citations.
   - `just triples-dump lat is whitakers` → look for decoded features (frequency “very frequent”, mapped tense/case/gender, pronoun/numeral subtypes when applicable) and `inflection_of` form→lex links.
   - `just triples-dump grc logos diogenes --normalize` → expect anchors `lex:logos`/`form:logos` (no `None`), sense/gloss triples, citations preserved.
   - If needed, enable CLTK in `.justscripts/triples_dump.py` (set `include_cltk=True`) and run `just triples-dump lat lupus cltk` to confirm IPA/gloss triples.

## Navigation Shortcuts
- Rules/constants: `docs/technical/predicates_evidence.md`, `docs/technical/triples_txt.md`, `docs/technical/semantic_triples.md`.
- Status/gaps: `docs/handoff/tool-execution-and-triples.md`.
- Work tracker: `docs/plans/active/tool-fact-indexing.md`.
