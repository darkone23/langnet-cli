# Refinement Audit

**Date:** 2026-04-27  
**Purpose:** section-by-section stock of what is integrated, what is weak, and what should be refined next.

Use this document when the project is not blocked by missing foundation, but the current behavior still needs polish before it is learner-ready. The execution queue remains `docs/EXECUTION_PLAN.md`; this audit explains why those tasks matter and what good refinement should look like.

## 1. Baseline And Release Hygiene

**What is strong**

- The core gate has recently passed with `just lint-all` and `just test-fast`.
- The project now has service-free tests for claim contracts, WSU extraction, reduction, translation cache identity, translation projection, and CDSL display behavior.
- The roadmap and status docs agree that stabilization comes before broad feature expansion.

**What is weak**

- The worktree contains a large integrated change set across docs, CLI behavior, CDSL handling, translation helpers, and reduction modules.
- That makes review harder until the work is split into coherent commits.
- Some historical docs still describe older milestones and can distract from the current queue.

**Refinement action**

- Preserve the current passing baseline.
- Commit changes in reviewable groups: docs, CDSL/display, reduction/encounter, translation/cache, fuzz/tooling.
- Keep one canonical operating queue in `docs/EXECUTION_PLAN.md`.

**Acceptance check**

- `git status --short` is understandable.
- `just lint-all` and `just test-fast` pass after each behavior change group.

## 2. CLI Surfaces

**What is strong**

- `lookup`, `plan`, `plan-exec`, `triples-dump`, and `encounter` now cover increasingly refined layers of the system.
- `encounter` is the right first learner-facing path because it uses reduced evidence instead of raw backend output.
- `triples-dump` remains useful for direct evidence inspection.

**What is weak**

- `lookup` is still backend-keyed and should not be treated as the learner schema.
- `triples-dump` now has structured JSON output, but its shape needs to stay aligned with reducer/debug needs.
- `encounter` has first snapshot-style accepted-output tests across Sanskrit, Latin, and Greek, but the gallery is still intentionally small.
- Display ranking is still basic; large dictionary entries can dominate the first learner impression.

**Refinement action**

- Keep `triples-dump --output json` stable as the inspection contract evolves.
- Expand snapshot tests for representative `encounter` outputs.
- Keep `lookup` as a raw inspection path, but route learner-facing examples toward `encounter`.
- Improve bucket ordering only after snapshots capture the current behavior.

**Acceptance check**

- A developer can inspect the same facts as text or JSON without scraping terminal output.
- Sanskrit `encounter san dharma cdsl` and Latin `encounter lat lupus ...` have stable fixture-backed expectations.

## 3. Evidence And Claim Contracts

**What is strong**

- The staged runtime keeps normalize, plan, fetch, extract, derive, and claim effects distinct.
- Core handlers emit evidence-backed triples suitable for reduction.
- Local DICO/Gaffiot raw response IDs are content-addressed, which improves reproducibility.

**What is weak**

- Predicate constants are not used everywhere yet.
- Claim value shapes still vary by handler.
- Runtime summaries do not always make skipped calls, cache state, source failures, and handler versions obvious enough.

**Refinement action**

- Gradually replace ad hoc predicate strings with constants from `langnet.execution.predicates`.
- Keep reducers consuming triples/evidence, not backend-specific `claim.value` payloads.
- Improve `plan-exec` summary output before adding more semantic inference.

**Acceptance check**

- A reduced bucket can be traced back to claim IDs and evidence IDs.
- `plan-exec` makes missing tools, skipped calls, and cache hits distinguishable from empty results.

## 4. Sanskrit CDSL

**What is strong**

- CDSL entries now expose learner-facing IAST display fields while preserving source-near SLP1 keys.
- `encounter` shows IAST forms first and source keys separately.
- Conservative terminal display transforms improve CDSL transliteration without dropping source content.

**What is weak**

- CDSL entries are still mostly flat strings.
- Citations, source abbreviations, grammar notes, compounds, and actual gloss text are mixed together.
- Display transforms are necessarily heuristic and must stay source-complete; source notes should be separated into explicit fields before ranking changes treat them differently.
- Exact reduction can overvalue very long, undifferentiated CDSL gloss strings.

**Refinement action**

- Add focused CDSL fixtures for `dharma`, `krsna`, `agni`, and one citation-heavy entry.
- Split source notation into explicit fields enough for ranking and learner output.
- Preserve raw CDSL text, source notation, and `source_ref` in display/evidence paths.

**Acceptance check**

- CDSL learner output shows IAST words and readable glosses.
- Raw source keys, raw text, and source references remain inspectable.
- Tests prove that source abbreviations are not accidentally transliterated as Sanskrit words.

## 5. DICO And Gaffiot Translation

**What is strong**

- Local DICO and Gaffiot entries now emit source-gloss triples.
- Translation cache identity helpers exist.
- Cached English translations can be projected into derived evidence before reduction.
- The demo script can write translation cache rows and show cache keys.
- Golden Gaffiot and DICO cache rows now prove cache hits project English evidence and stale source-text hashes do not.

**What is weak**

- The cache is still populated explicitly, usually by network-backed translation runs.
- Translation-backed accepted-output examples are not yet broad enough to serve as release fixtures.
- DICO and Gaffiot source French must not be confused with translated English evidence.

**Refinement action**

- Add accepted-output examples that exercise the golden cache rows through `encounter`.
- Keep network-backed translation limited to explicit cache population.
- Keep translated triples visibly derived and metadata-rich.

**Acceptance check**

- `encounter --use-translation-cache` changes output only when cache rows match by source hash, model, prompt hash, and hints.
- Tests show source French evidence and translated English evidence remain distinct.

## 6. Reduction And Semantic Layer

**What is strong**

- `WitnessSenseUnit`, `SenseBucket`, and `ReductionResult` exist.
- WSU extraction preserves display metadata and evidence.
- Exact bucket reduction is wired into the runtime through `encounter`.

**What is weak**

- Bucketing is exact only.
- There is no mature ranking, synonym grouping, or confidence model.
- Long dictionary entries can become unwieldy buckets.
- The project is ready for MVP extension, not broad semantic generalization.

**Refinement action**

- Stabilize exact buckets before adding similarity.
- Add structured bucket JSON and terminal snapshots.
- Introduce ranking based on source quality, structured gloss/source-note fields, length, and witness count before embeddings or LLM similarity.

**Acceptance check**

- The same input produces deterministic bucket IDs and stable display ordering.
- Every WSU in a bucket carries claim/evidence IDs.
- Hydration or translation does not silently change source-bucket identity.

## 7. Fuzz And Hit Rates

**What is strong**

- The fuzz tooling is useful for broad diagnostic coverage across common Sanskrit, Greek, and Latin words.
- Recent fuzz work helped expose practical resolution questions before learner-facing output hardened around them.

**What is weak**

- Some fuzz assumptions still reflect older query modes.
- Hit rates are not yet release gates.
- Fuzz output does not yet map cleanly onto learner-facing acceptance criteria.

**Refinement action**

- Define a small gold list per language and tool family.
- Track expected hit, partial-hit, and known-miss categories.
- Keep fuzz as diagnostics until it is aligned with `encounter` and structured triples output.

**Acceptance check**

- Fuzz reports can answer: "Does this word produce evidence?", "Does it reduce?", and "Is the display learner-readable?"

## 8. Documentation And Onboarding

**What is strong**

- The project now has a vision document, pedagogical philosophy, roadmap, technical vision, execution plan, output guide, and start-packet docs.
- The docs correctly emphasize evidence-first educational output instead of opaque generated prose.

**What is weak**

- There are still several overlapping planning documents.
- Junior pickup tasks can become stale quickly as implementation work lands.
- Some docs are milestone-level while a new engineer needs exact next commands and acceptance checks.

**Refinement action**

- Point new contributors first to `docs/EXECUTION_PLAN.md`, then to this audit, then to the specific plan file for their task.
- Mark completed junior tasks as complete or move them out of the active pickup queue.
- Keep every ready task in the form: goal, files likely touched, command to run, acceptance check.

**Acceptance check**

- A new engineer can choose one task without asking which roadmap is current.
- No task advertises behavior that already exists or that current code cannot reasonably support.

## 9. Learner-Facing Readiness

**What is strong**

- The architecture now has the right shape: source evidence becomes claims, claims become WSUs, WSUs become buckets, and buckets become `encounter` output.
- Sanskrit display has improved enough that IAST learner forms can be shown while source keys remain visible.
- Translation cache projection gives a plausible route from French dictionary sources to English learner text without making network calls part of normal lookup.

**What is weak**

- The learner-facing output is still a prototype.
- CDSL source structuring and source ranking are not strong enough yet for broad educational confidence.
- There are not enough golden examples showing translated-cache and multi-source "good" output across Sanskrit, Latin, and Greek.

**Refinement action**

- Treat the next milestone as learner-output hardening, not semantic expansion.
- Extend the accepted-output gallery with Sanskrit DICO translated cache, Latin Gaffiot translated cache, and Latin Whitaker/Diogenes multi-source examples.
- Use those examples to drive ranking and display improvements.

**Acceptance check**

- A learner-facing example can be regenerated from CLI commands and compared against expected output.
- Raw evidence remains reachable from every displayed meaning.

## Recommended Immediate Order

1. Commit or otherwise isolate the current integrated baseline.
2. Expand CDSL fixtures into stronger source/gloss/source-note structure without omitting source content by default.
3. Add a narrative evidence-inspection example that traces `encounter` output back to triples and source refs.
4. Re-run fuzz diagnostics against the refined `encounter` and JSON inspection surfaces.

## Working Rule

For the next phase, prefer refinement that makes current behavior inspectable, stable, and educationally readable. Avoid adding broader semantic inference until source display, evidence inspection, and snapshot coverage are boring.
