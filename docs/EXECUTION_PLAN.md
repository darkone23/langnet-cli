# Project Execution Plan

**Date:** 2026-04-27  
**Mode:** stabilization before feature expansion

This document is the compact operating view for roadmap, tasks, gaps, and risks. Use it when deciding what to work on next.

## Current Thesis

LangNet has enough runtime foundation to be useful and now has a first exact WSU → bucket → `encounter` path. Sanskrit is explicitly Heritage-first for morphology/analysis, with CDSL and DICO used as meaning/gloss supplements. The next work should make this path boring, inspectable, and fixture-tested before adding broader semantic interpretation.

## Stabilization Charter

For the next phase, success means the existing word-level evidence engine becomes repeatable, reviewable, and easy to explain. It does not mean adding passage interpretation, embeddings, a web UI, or broader semantic inference.

Stable foundation means:

- A learner-facing word encounter can be regenerated from fixtures or local sources.
- Every displayed meaning can be traced to claims, triples, and source evidence.
- Translation-derived English text is cache-backed and visibly derived from source-language evidence. Network-backed translation is allowed only for explicit cache population, not implicit learner-facing lookup.
- Tool failures, skipped calls, cache state, and source availability are obvious from CLI output.
- The active queue stays small enough that contributors know what to do next.

Expansion is deferred until these conditions hold for representative Sanskrit, Latin, and Greek examples.

## Source Of Truth Map

| Question | Canonical doc |
| --- | --- |
| Why does the project exist? | `docs/VISION.md` |
| What is the current product/technical state? | `docs/PROJECT_STATUS.md` |
| What is the milestone sequence? | `docs/ROADMAP.md` |
| What should be refined next, section by section? | `docs/REFINEMENT_AUDIT.md` |
| How should the technical pipeline fit together? | `docs/technical/design/TECHNICAL_VISION.md` |
| What is actively being driven? | `docs/plans/active/infra/design-to-runtime-roadmap.md` |
| What small tasks are ready? | This document's pickup queue |

## Immediate Priority Queue

These are the only foundation tasks that should be treated as active. New ideas should either support one of these rows or stay parked until the baseline is committed and inspectable.

### Recently Completed Pickup Tasks

- WSU dataclasses, extractor, and exact bucket reducer.
- First `encounter` CLI output over reduced buckets.
- CDSL IAST display metadata and conservative source-complete terminal display transforms.
- Translation cache key/schema helpers and cache-hit projection into derived triples.
- Structured `triples-dump --output json` support.
- Snapshot-style tests for `encounter` Sanskrit and Latin output.
- Heritage morphology rows in Sanskrit `encounter` output.
- CDSL citation-heavy display fixture that verifies citation segments are preserved.
- Gaffiot and DICO translation cache golden rows with stale-cache miss coverage.
- CDSL/Heritage Sanskrit normalization fixes for `dharma`, `duḥkha`, and `śraddhā`.
- 50-word-per-language diagnostic audit with separate gloss, morphology, and evidence-hit reporting.
- Accepted-output gallery snapshots across Sanskrit, Latin, and Greek `encounter` output.
- `plan-exec --output json` summary with cache status, stage counts, skipped-call reasons, handler versions, and compact claim rows.
- CDSL gloss triples preserve raw source text while carrying conservative `metadata.display_gloss` for learner display; source segments are not omitted by default.
- `OUTPUT_GUIDE.md` includes a Sanskrit `dharma` evidence walkthrough from `encounter` to CDSL JSON triples and source refs.
- CDSL gloss triples now carry `source_entry` and ordered source-complete `source_segments`.
- `OUTPUT_GUIDE.md` includes a DICO/Gaffiot translation-cache walkthrough from source French triples to derived English witnesses.

### Current Pickup Queue

This queue is ordered to refine the integrated WSU/encounter path before adding broader semantic inference. For the section-by-section rationale, use `docs/REFINEMENT_AUDIT.md`.

| Rank | Task | Why now | Validation |
| --- | --- | --- | --- |
| 1 | CDSL structure follow-through | Add typed source-note/citation/grammar fields only where fixture evidence supports them; keep raw and display text source-complete by default | focused CDSL display tests + `just lint-all` |
| 2 | Evidence inspection examples | Show how to trace a displayed meaning back through `triples-dump --output json` without relying on tribal knowledge | docs examples + existing triples/encounter tests |
| 3 | Translation cache examples | Add more fixture-backed DICO/Gaffiot cache rows and inspection examples without invoking the network | focused translation tests + docs |
| 4 | Ranking policy | Keep the current simple ranking explicit: cache-backed English, then witness count, then deterministic fallback | encounter snapshot tests |
| 5 | Predicate/claim cleanup | Reduce drift by moving low-risk string predicates to canonical constants while keeping reducer input triple/evidence-based | claim contract tests + `just lint-all` |

### Refinement Backlog, Not Expansion

Do after the current pickup queue, not before it:

- Fuzz diagnostics aligned with `encounter` and `triples-dump --output json`.

Defer until the above is stable:

- Embedding-backed similarity.
- LLM semantic merging.
- Passage-level interpretation.
- Compound workflow expansion.
- API/UI product work.

### P0: Preserve The Baseline

Goal: keep the repo clean, reviewable, and safe to extend.

Tasks:

- Keep `just lint-all` passing.
- Keep `just test-fast` passing before behavior changes land.
- Commit documentation, tooling, and runtime changes in coherent groups.
- Avoid new feature work that makes evidence inspection harder.

Primary references:

- `docs/PROJECT_STATUS.md`
- `docs/JUST_RECIPE_HEALTH.md`

### P1: Evidence Inspection

Goal: make it easy to answer where a fact came from.

Tasks:

- Keep structured JSON inspection for triples or claims aligned with reducer needs.
- Keep `plan-exec` summaries aligned with cache status, skipped-call reasons, stage counts, and handler versions.
- Add one end-to-end docs example tracing a gloss from triple to evidence.

Ready slices:

- `JT-012: Evidence Inspection Example`
- `JT-015: Triples Dump Inspection Example`

Primary references:

- `docs/OUTPUT_GUIDE.md`
- `docs/technical/predicates_evidence.md`

### P2: Claim-To-WSU Path

Goal: start semantic reduction from claims, not backend payloads.

Completed baseline:

- Add `WitnessSenseUnit`, `SenseBucket`, and `ReductionResult` containers.
- Add a fixture-driven WSU extraction test.
- Implement a tiny extractor over `has_sense + gloss + evidence`.
- Add exact-match bucket grouping only after extraction is tested.

Current refinement:

- Keep structured inspection JSON aligned with the triples the reducer consumes.
- Expand snapshots for the `encounter` display path.
- Improve source-specific structure and ranking before semantic merging.

Primary references:

- `docs/SEMANTIC_READINESS.md`
- `docs/plans/todo/semantic-reduction/semantic-reduction-mvp.md`
- `docs/technical/design/classifier-and-reducer.md`
- `tests/fixtures/lupus_claims_wsu.json`

### P3: Source Display And Translation Readiness

Goal: make learner-visible text readable without weakening evidence.

Completed baseline:

- Add CDSL IAST display fields while preserving raw source encodings.
- Add translation cache schema/key helpers before translated Gaffiot/DICO glosses influence reduction.
- Keep French source evidence distinct from translated English evidence.

Current refinement:

- Keep cache hits exact by source hash, prompt hash, hint hash, model, lexicon, entry, and occurrence.
- CDSL structure follow-through after the initial source/display split.

Primary references:

- `docs/TRANSLATION_CACHE_PLAN.md`
- `docs/plans/active/infra/local-lexicon-witness-handoff.md`
- `docs/plans/todo/dico/DICO_ACTION_PLAN.md`

## Known Gaps

| Gap | Impact | Next action |
| --- | --- | --- |
| `lookup` output is backend-keyed | Learners see tool structure before meaning structure | Build semantic output only after WSU/bucket MVP |
| `triples-dump --output json` is new | Reducer/debug tooling now has structure, but the contract still needs real examples | Add accepted inspection examples and keep tests aligned |
| Exact buckets only | Similar meanings remain split across long source strings | Add ranking and structure before semantic merging |
| Predicate constants are not used everywhere | Drift risk across handlers | Convert handler strings gradually with tests |
| Claim value shapes vary by handler | Reducer could become backend-specific | Consume triples/evidence, not raw `claim.value` fields |
| CDSL entries are flat strings | Sanskrit learner UX still sees undifferentiated dictionary material | Parse/label source fields while preserving raw evidence and display completeness |
| Gaffiot/DICO translation cache is mostly manually populated | Translated glosses exist only after explicit population | Keep cache identity strict and add accepted translated-output examples |
| CLTK depends on local model data | Live behavior can vary by machine | Keep semantic tests service-free and fixture-based |
| Fuzz harness has legacy query assumptions | It is not a release gate | Keep the 50-word audit diagnostic and add accepted-output checks for quality |

## Risk Register

### R1: Semantic Output Outruns Evidence

Risk: learner-facing summaries could look authoritative while hiding weak or missing provenance.

Mitigation:

- Do not expand semantic display beyond evidence-preserving `encounter` output.
- Mark single-witness or provisional buckets.
- Keep raw JSON/inspection paths available.

### R2: Parallel Roadmaps Drift

Risk: active plans, todo files, roadmap, and status docs diverge.

Mitigation:

- Keep `docs/ROADMAP.md` as the milestone sequence.
- Keep this file as the operating queue.
- Move stale plans to `docs/archive/`.
- Update `docs/PROJECT_STATUS.md` when priorities change materially.

### R3: Translation Becomes Opaque

Risk: French source glosses and generated English translations get mixed as if they were the same evidence.

Mitigation:

- Translation cache keys must include source hash, model, prompt hash, and hint hash.
- Translated triples must carry translation metadata.
- Reducer must distinguish source glosses from translated glosses.

### R4: Backend-Specific Details Leak Into Reduction

Risk: the reducer depends on Diogenes, Whitaker, CDSL, or Heritage payload quirks.

Mitigation:

- Reducer input is claims/triples only.
- Backend quirks stay in extract/derive handlers.
- Tests use saved claim fixtures, not live tools.

### R5: External Services Hide Regressions

Risk: missing Diogenes, Heritage, Whitaker, CLTK, or local data makes failures hard to classify.

Mitigation:

- Keep core tests service-free.
- Use per-tool errors for unavailable live services.
- Document recipe health separately from dependency readiness.

## Decision Gates

Advance semantic reduction beyond exact buckets only when:

- WSU extraction works from fixture claims.
- Each WSU carries claim/evidence IDs.
- The reducer can be tested without live services.
- Inspection output exposes the same facts the reducer consumes.

Advance learner-facing semantic output beyond the current `encounter` MVP only when:

- Sense buckets are deterministic.
- Source witnesses remain visible.
- Terminal output has snapshot tests for each accepted example family.
- Backend-keyed JSON remains available for debugging.

Advance translation-backed reduction only when:

- Translation cache identity helpers exist.
- Cache-hit behavior is fixture-tested.
- Translated gloss triples carry translation evidence.
- Network calls remain explicit opt-in.

Start compound or passage work only after:

- Word-level claims and buckets are stable.
- Component lookups reuse the normal claim/reduction path.
- Fixture tests cover the first compound or context example.

## Deprioritized

- ASGI/API rebuild as a product contract.
- Embeddings or LLM similarity.
- Passage-level interpretation.
- Broad CLI rewrites.
- Translation network calls in tests.
