# Tool Plan Execution → Effects → Claims

**Status**: Draft  
**Owner**: Core team (@architect for design, @coder for build, @sleuth for debugging, @scribe for docs, @auditor for review)  
**Scope**: Execute ToolPlans end-to-end, capture effects (fetch/parse/derive), and emit normalized semantic claims without confidence scores.

## Context (What Exists Today)
- Normalization + canonicalization works: `langnet-cli normalize` hits diogenes/heritage/whitaker via the canonical pipeline, capturing raw responses and extractions into DuckDB (`RawResponseIndex`, `ExtractionIndex`, `NormalizationService` + `CanonicalPipeline`).
- Tool planning works: `ToolPlanner` builds per-language DAGs (fetch → extract → derive → claim) with stable hashes; `langnet-cli plan` renders them.
- Execution sketch exists: `execute_plan` runs ToolPlans over `ToolClient`s, stores raw responses, and records executed plan refs; there is no stage-aware parsing/deriving/claiming.
- Storage: DuckDB schema for raw responses, extractions, claims, plan/cache indices; plan/response index round-trips are tested.
- Clients: HTTP/subprocess/file wrappers plus capturing shim; adapters for diogenes word_list/parse and whitaker are normalization-focused only.
- Missing: stage-aware executor, per-tool fetch runners mapped to planned tool names, parse/derive functions for `internal://...`, claim emitters, and effect journaling beyond raw responses.

## Goal
Deliver a deterministic executor that runs ToolPlans, captures all effects (fetch, parse, derive, claim), reuses/memoizes via DuckDB, and produces normalized semantic claims (triples with provenance) ready for downstream semantic reduction. No confidence fields added to raw dictionary extractions.

## Phased Plan

### Phase 0 — Inventory & Alignment (@architect @auditor)
- [ ] Map planned tool names → client/handler modules (e.g., `fetch.diogenes`, `extract.diogenes.html`, `derive.diogenes.morph`, `claim.diogenes.morph`, `fetch.cdsl`, `extract.cdsl.xml`, `derive.cdsl.sense`, `claim.cdsl.sense`, `fetch.heritage`, `extract.heritage.html`, `derive.heritage.morph`, `claim.heritage.morph`, `fetch.whitakers`, `derive.whitakers.facts`, etc.).
- [ ] Confirm effect/claim table ownership and IDs (stage tags, provenance chain shape, hashing strategy) against `storage/schemas/langnet.sql`.
- [ ] Decide minimal per-tool fact structs (dataclasses or proto-backed) to carry source_ref/domains/register without confidence.

### Phase 1 — Effect Contracts & Executor Core (@architect @coder)
- [ ] Define effect dataclasses for `RawResponseEffect` (exists), `ExtractionEffect`, `DerivationEffect`, `ClaimEffect` with stable IDs, `stage`, `source_call_id`, `tool`, and provenance chain.
- [ ] Extend storage layer: indexes/tables for extractions, derivations, claims with deterministic keys (response_id/extraction_id) and DuckDB CRUD helpers.
- [ ] Implement stage-aware executor: topologically execute ToolPlan nodes, dispatch by `tool` prefix (fetch/extract/derive/claim), enforce dependencies, capture timing, and short-circuit on memo hits (plan_hash + node hash).
- [ ] Wire executor to plan/response indices so executed plans can be reused; keep raw responses optional but default-on capture via `RawResponseIndex`.

### Phase 2 — Fetch Runners (Tool-Specific) (@coder @sleuth)
- [ ] Diogenes HTTP runner for `fetch.diogenes` (parse endpoint) with capturing wrapper.
- [ ] Heritage HTTP runner for `fetch.heritage` (sktreader) using velthuis params.
- [ ] CDSL DuckDB runner for `fetch.cdsl` (reads from built `cdsl_*.duckdb`; returns XML blob rows).
- [ ] Whitaker runner for `fetch.whitakers` (local binary via `SubprocessToolClient`).
- [ ] CLTK runner for `fetch.cltk` (local module call or HTTP stub), CTS runner for `fetch.cts_index` (DuckDB lookup).
- [ ] Normalize runner registry so new tools can be added without touching executor.

### Phase 3 — Parse/Extract Stage (@coder)
- [ ] Implement extractors matching plan tool names:
  - `extract.diogenes.html`: HTML → structured blocks (morph entries, citations).
  - `extract.heritage.html`: HTML → morph tables/entries.
  - `extract.cdsl.xml`: XML rows → entry objects.
  - `extract.whitakers.lines`: text → tagged lines via existing line parsers.
  - `extract.cts_index.json`: CTS lookup → citation payloads.
- [ ] Store `ExtractionEffect` with `extraction_id`, `source_call_id`, `kind`, `canonical`, payload, duration, and provenance links back to `RawResponseEffect`.

### Phase 4 — Derive Stage (@coder @sleuth)
- [ ] Define per-tool fact builders:
  - Diogenes: morph facts + citation refs from parsed blocks.
  - Heritage: morph facts (case/number/gender) from tables.
  - CDSL: sense facts (gloss, pos/gender/root, source_ref, domains/register when present).
  - Whitaker: lex/morph facts from tagged lines.
  - CTS: hydrated citation facts.
- [ ] Emit `DerivationEffect` with `derivation_id`, `source_extraction_id`, fact payload, canonical target, and provenance metadata.
- [ ] Add deterministic hashing (payload + canonical) for memoization.

### Phase 5 — Claim Stage (@coder)
- [ ] Define minimal triple schema: `subject` (lemma or URN), `predicate` (e.g., has_gloss, has_pos, has_citation, has_form), `value` (JSON), `source`, `source_ref`, `mode` (open/skeptic ready), `provenance_chain`.
- [ ] Implement per-tool claim mappers (derive.* → claim.*) that flatten tool facts into triples without altering semantics; include domains/register/source_ref, skip confidence.
- [ ] Persist claims in DuckDB with provenance entries; ensure deterministic `claim_id`.

### Phase 6 — CLI + Ops (@scribe @coder)
- [ ] Add `langnet-cli plan-exec --language <lang> <text>` to normalize → plan → execute → emit effect summary/claim count; include `--plan-hash` reuse and `--no-fetch` for cache-only.
- [ ] Add `langnet-cli effects show <response_id|extraction_id|derivation_id|claim_id>` for debugging.
- [ ] Wire `just cli plan-exec ...` helper and update `docs/technical/design/tool-response-pipeline.md` and GETTING_STARTED with executor usage and cache locations.

### Phase 7 — Tests & QA (@coder @auditor)
- [ ] Fixture-backed executor tests for SAN/GRC/LAT covering dependency order, memo hits, and deterministic IDs/hashes.
- [ ] Integration tests exercising one happy path per language with local stubs/mocks (no external network).
- [ ] Regression tests for plan hash stability and claim shape (schema validation).
- [ ] Profiling hooks for fetch/parse/derive timing; ensure DuckDB indices are applied lazily but correctly.

## Risks / Mitigations
- **Tool availability**: Provide stubs/fallbacks for missing local services; mark optional nodes to keep executor progressing.
- **Storage bloat**: Gate raw blob persistence with a flag; compress large payloads where needed.
- **Non-determinism**: Hash inputs excluding volatile fields; sort lists before hashing.
- **Schema drift**: Centralize tool-name→handler registry; add versioning to memoization keys.

## Definition of Done
- ToolPlans execute end-to-end through fetch/parse/derive/claim with effects journaled in DuckDB and memoized by hash.
- Per-tool runners + parsers + derivations exist for diogenes, heritage, cdsl, whitakers, cltk, cts.
- Claims are emitted as normalized triples with provenance (no confidence fields on dictionary extractions).
- CLI surfaces plan execution and effect inspection; tests cover core flows with deterministic IDs.
