# Design-to-Runtime Roadmap

**Status**: 🔄 ACTIVE  
**Feature Area**: infra  
**Date**: 2026-04-27  
**Owner Model Roles**: @architect for sequencing, @coder for implementation, @auditor for contracts/tests, @scribe for documentation  

## Purpose

This plan reconciles `docs/technical/design/` with the current codebase and defines a stabilization-first path toward LangNet’s stated goals:

- learner-facing lookup for Latin, Greek, and Sanskrit
- provenance-backed evidence from every source
- deterministic tool-plan execution and cache behavior
- semantic reduction into sense buckets after current claims are stable
- future passage/compound support only after word-level facts are reliable

## Current Reality Snapshot

### Implemented and Healthy

- **CLI surface**: `normalize`, `parse`, `lookup`, `plan`, `plan-exec`, `triples-dump`, `encounter`, `databuild`, `index`.
- **Planner**: `src/langnet/planner/core.py` builds language-specific `ToolPlan` DAGs.
- **Execution pipeline**: `src/langnet/execution/executor.py` runs fetch → extract → derive → claim.
- **Handlers**: real handlers exist for Diogenes, Whitaker, CLTK, spaCy, Heritage, and CDSL.
- **Storage schema**: raw responses, extractions, derivations, claims, provenance, normalization, and plan indexes exist under `src/langnet/storage/`.
- **Predicate/evidence vocabulary**: `src/langnet/execution/predicates.py` and `src/langnet/execution/evidence.py`.
- **Reduction/display**: exact WSU extraction and deterministic buckets are wired into `encounter`.
- **Sanskrit model**: Heritage is the preferred analysis/morphology source; CDSL and DICO provide meaning/gloss supplements.
- **Translation cache**: DICO/Gaffiot cache-hit projection exists; network translation remains explicit cache-population work.
- **Diagnostic audit**: the 50-word per-language fuzz audit now separates evidence/gloss hits from Sanskrit Heritage morphology hits.
- **Quality gate**: `just lint-all && just test-fast` passes.

### Design Docs That Match Current Direction

- `tool-response-pipeline.md`: stage boundaries are broadly implemented.
- `query-planning.md`: planner/executor/cache structure is partially implemented.
- `tool-fact-architecture.md` / `tool-fact-flow.md`: still useful conceptually, but some details are superseded by current effects/claims code.
- `witness-contracts.md`: still the right evidence policy target.
- `classifier-and-reducer.md` / `semantic-structs.md`: still the right broader semantic reduction target; the exact-bucket MVP is runtime-wired, but near-match/general semantic grouping is not.
- `hydration-reduction.md`: important but should follow stable claims and reduction, not precede them.

### Current Mismatches / Risks

- Many historical plans were archived; the remaining risk is keeping this roadmap canonical.
- Claim shape is fixture-tested across core handlers, but predicate constants still need tightening.
- `lookup` is useful but still backend-keyed; `encounter` is the current learner-facing path.
- Semantic reduction is exact-only and should not be treated as broad semantic understanding.
- Hydration (e.g. CTS reference expansion) is still not a separate stage/tool.
- Passage/compound work should not outrun stable word-level claims and sense buckets.
- Accepted-output coverage is still too small to call the learner interface stable.

## Strategic Sequence

The project should move in this order:

1. **Checkpoint the current baseline**
2. **Stabilize word-level evidence**
3. **Contract-test claims/triples**
4. **Improve evidence inspection**
5. **Harden the exact reduction/encounter MVP**
6. **Build accepted learner-output examples**
7. **Add hydration as optional enrichment**
8. **Expand to compounds/passages**

This order keeps educational UX grounded in auditable evidence and prevents semantic/passage work from depending on unstable raw backend payloads.

## Milestone 0 — Stabilization Baseline

**Goal**: Commit a clean, understandable baseline before new feature work.

**Scope**
- Terminal lookup CLI changes.
- Tooling health and helper-script UX.
- Primary documentation reconciliation.
- Completed handoff relocation.
- Junior task backlog.

**Acceptance Criteria**
- `just lint-all` passes.
- `just test-fast` passes.
- Current changed files are reviewed and committed in coherent groups.
- Known false affordances are removed or made real.
- New fixtures have validation tests.

**Recommended Commit Groups**
1. Terminal lookup feature: `src/langnet/cli.py`, `docs/plans/completed/pedagogy/terminal-lookup-complete.md`.
2. Tooling health: `justfile`, `.justscripts/`, `src/langnet/normalizer/core.py`, `tests/fuzz_parser_robustness.py`.
3. Documentation reconciliation: `README.md`, `docs/GETTING_STARTED.md`, `docs/OUTPUT_GUIDE.md`, `docs/DEVELOPER.md`, `docs/technical/ARCHITECTURE.md`, `docs/plans/README.md`, this roadmap, junior backlog.

## Milestone 1 — Claim Contract Hardening

**Goal**: Make every handler emit stable, evidence-backed claims that can feed reduction.

**Why First**
- Semantic reduction needs clean witness/sense units.
- Hydration needs stable references.
- Learner-facing output must distinguish facts from source assertions.

**Tasks**
1. Define a small claim contract test helper.
2. For each handler, assert:
   - claim has stable `claim_id`
   - `subject`, `predicate`, `value`, and `provenance_chain` are present
   - value triples use known predicates where applicable
   - evidence contains tool/call/response/extraction/derivation/claim IDs where available
3. Add fixture-backed tests for:
   - Diogenes Latin sense + citation
   - Whitaker Latin morphology ambiguity
   - CLTK pronunciation / Lewis line
   - Heritage morphology
   - CDSL sense with `source_ref`
4. Document any handler that cannot yet meet the contract.

**Primary Files**
- `src/langnet/execution/handlers/*.py`
- `src/langnet/execution/predicates.py`
- `src/langnet/execution/evidence.py`
- `tests/test_*triples*.py`

**Acceptance Criteria**
- Contract tests run without live services.
- All real handlers either pass or have explicit xfail/skip with reason.
- `triples-dump` output is explainable from claim contracts.

**Junior-Friendly Slices**
- Add tests for one handler at a time.
- Convert hard-coded predicate strings in one handler to constants.
- Add one fixture and one assertion file per backend.

## Milestone 2 — Runtime Evidence Inspection

**Goal**: Make the index-first evidence layer inspectable enough for debugging and review.

**Tasks**
1. Improve `plan-exec` output with:
   - cache hit/miss state
   - skipped calls and reasons
   - counts per stage
   - handler versions
2. Add or polish `triples-dump` filters:
   - by tool
   - by predicate
   - by subject prefix (`form:`, `lex:`, `sense:`)
3. Add docs showing how to inspect one query from plan to claim.

**Primary Files**
- `src/langnet/cli.py`
- `src/langnet/execution/executor.py`
- `docs/GETTING_STARTED.md`
- `docs/OUTPUT_GUIDE.md`

**Acceptance Criteria**
- A developer can answer “where did this gloss come from?” from CLI output alone.
- No live backend required for fixture-based inspection tests.

## Milestone 3 — Minimal Semantic Reduction MVP

**Goal**: Harden the runtime exact reducer that consumes claims/triples, not legacy backend payloads.

**Current MVP**
- Input: claim effects from `plan-exec` / indexed claims.
- Extract Witness Sense Units (WSUs) from `has_sense` + `gloss` triples.
- Cluster exact or near-exact glosses deterministically.
- Output stable bucket IDs with witness provenance.
- Display through `langnet-cli encounter`.
- Preserve Sanskrit Heritage analysis rows separately from meaning buckets.

**Do Not Do Yet**
- Embedding similarity.
- Full semantic constant registry.
- Passage-level context selection.
- UI-heavy formatting.

**Remaining Tasks**
1. Add structured bucket JSON examples alongside terminal snapshots.
2. Improve display ranking using source quality, structured gloss/source-note fields, length, and witness count.
3. Strengthen CDSL source/gloss/source-note structure while preserving raw text and `source_ref`.
4. Keep near-match clustering behind tests until exact buckets are boring.

**Design References**
- `docs/technical/design/classifier-and-reducer.md`
- `docs/technical/design/semantic-structs.md`
- `docs/plans/todo/semantic-reduction/semantic-reduction-mvp.md`

**Acceptance Criteria**
- Same input claims produce same buckets across runs.
- Each bucket lists all witness claims.
- No witness appears in two buckets.
- Sanskrit examples show Heritage analysis as analysis, not as dictionary meaning evidence.
- Accepted-output tests catch ranking/display regressions.
- `just lint-all && just test-fast` passes.

**Junior-Friendly Slices**
- Implement dataclasses only.
- Add exact-match clustering test.
- Add WSU extraction test from a hand-written claim fixture.
- Document one sample semantic output.

## Milestone 4 — Learner-Facing Semantic Output

**Goal**: Move from the current `encounter` prototype to didactic output ordered for students.

**Target Display Order**
1. Headword / form
2. Senses grouped by semantic bucket
3. Morphology
4. References and evidence
5. Source disagreements / caveats

**Tasks**
1. Add a semantic output formatter separate from backend pretty output.
2. Preserve `lookup --output json` for raw/backend debugging.
3. Add snapshot tests for terminal output ordering.
4. Explicitly mark provisional or single-witness buckets.

**Acceptance Criteria**
- Learner output does not require users to understand backend names first.
- Evidence remains available on demand.
- Output order is regression-tested.

## Milestone 5 — Hydration as Optional Enrichment

**Goal**: Expand references after claims/reduction without polluting extraction.

**Examples**
- CTS URN lookup for citations.
- Expanded author/work labels.
- Dictionary entry references.

**Tasks**
1. Treat hydration as a post-claim or post-reduction stage.
2. Use `databuild cts` output as a hydrator input.
3. Store hydrated metadata separately from base claim IDs.
4. Add `--hydrate` / `--no-hydrate` behavior only after MVP tests pass.

**Design Reference**
- `docs/technical/design/hydration-reduction.md`

**Acceptance Criteria**
- Base semantic buckets are identical with or without hydration.
- Hydration can be rerun without refetching tools.

## Milestone 6 — Compounds and Passage Support

**Goal**: Apply stable word-level lookup/reduction to multi-token Sanskrit and eventually passage reading.

**Dependency**
- Do not advance this beyond local tokenizer tests until Milestones 1–4 are stable.

**Tasks**
1. Finish Sanskrit tokenization normalization.
2. Query components through the same claim/reduction path.
3. Add compound structure explanation as a pedagogical layer.

**Design / Plan References**
- `docs/plans/todo/skt/sanskrit-tokenization-compound-plan.md`
- `docs/plans/todo/pedagogy/compound-term-lookup.md`

## What to Deprioritize for Now

- Rebuilding a first-class ASGI API before CLI/runtime semantics stabilize.
- Embedding-backed similarity before deterministic claim-to-WSU reduction exists.
- Full semantic constants before buckets and evidence are stable.
- Broad behavior-changing CLI refactors before the current cleanup baseline is checkpointed.
- Passage analysis before compounds can reuse word-level reduction.

## Immediate Next Work Items

1. **Checkpoint current baseline** using the groups above.
2. **Strengthen CDSL source/gloss/source-note structure** around citation-heavy entries.
3. **Add an evidence-inspection example** tracing `encounter` output back to `triples-dump --output json`.
4. **Expand no-network DICO/Gaffiot translation-cache fixtures** beyond the first golden rows.
5. **Keep ranking policy and predicate-constant cleanup incremental** and fixture-backed.

## Success Metrics

- All primary learner commands are documented and tested.
- Every handler has at least one fixture-backed claim contract test.
- `triples-dump` can explain source evidence for Latin, Greek, and Sanskrit examples.
- Exact reducer output has accepted snapshots for representative Sanskrit, Latin, and Greek examples.
- Learner-facing output remains stable under snapshot tests.

## Cleanup Note

Superseded V2, semantic-reduction, parser, and session-status plans were archived under `docs/archive/2026-04-cleanup/`. Treat this roadmap as canonical unless it is explicitly replaced.
