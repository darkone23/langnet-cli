# Roadmap

This is the canonical project roadmap. Detailed implementation tracking lives in `docs/plans/active/infra/design-to-runtime-roadmap.md`.

## Current Status

The project has a working CLI, planner, staged executor, storage layer, and real backend handlers. The current priority is stabilization: make the existing system coherent, tested, documented, and safe to extend.

Current grade: **B+ / 84%**.

- Build health: strong.
- Runtime architecture: usable.
- Claim/evidence layer: improving, fixture-tested across core handlers, and content-addressed for local DICO/Gaffiot raw responses.
- Semantic reduction: designed but not runtime-wired.
- Docs/plans: consolidated in April 2026; archive retained for historical context.

## Milestone 0 — Stabilization Baseline

**Goal:** keep the repo in a clean, reviewable state before new product features.

Done or in progress:

- `just lint-all` passes.
- `just test-fast` passes.
- Primary docs have been reconciled with current CLI reality.
- Historical status reports and superseded plans have been archived.
- Just recipe wiring has been audited and fixed where wrappers drifted from the CLI.
- Local DICO/Gaffiot raw response IDs are deterministic.

Remaining:

- Commit current changes in coherent groups.
- Keep active planning limited to one canonical roadmap plus scoped task files.
- Remove or fix commands that advertise behavior they do not implement.
- Validate fixtures that will become inputs to semantic reduction.
- Keep `just` recipe health documented so recipe failures are classified as wiring, dependency, or expected external-service failures.

## Milestone 1 — Claim Contract Hardening

**Goal:** every handler emits stable, evidence-backed claims suitable for semantic reduction.

Status: **mostly complete for core handlers**.

Implemented coverage:

- Whitaker Latin morphology/sense triples.
- CDSL Sanskrit sense/source-ref triples.
- Diogenes Latin sense/citation triples.
- CLTK pronunciation/Lewis-line triples.
- Heritage morphology triples.
- Local Gaffiot Latin source-gloss triples.
- Local DICO Sanskrit source-gloss triples.

Remaining:

- Normalize predicate constants across handlers.
- Add or document coverage for any secondary/stub handlers.
- Add structured JSON inspection for triples/claims.
- Continue improving reducer-focused inspection workflows.

## Milestone 2 — Evidence Inspection

**Goal:** developers can answer “where did this fact come from?” from CLI output alone.

Tasks:

- Improve `plan-exec` summaries with cache status, skipped-call reasons, stage counts, and handler versions.
- Keep `triples-dump` text filters working and add structured JSON output.
- Document one end-to-end inspection workflow for Latin and Sanskrit.

## Milestone 3 — Semantic Reduction MVP

**Goal:** build a deterministic reducer over claims/triples.

MVP:

- Extract Witness Sense Units from `has_sense` + `gloss` triples.
- Cluster exact or near-exact glosses deterministically.
- Emit stable sense-bucket IDs.
- Preserve witness claim IDs and evidence.

Do not include yet:

- Embeddings.
- Full semantic constants.
- Passage-level context.
- UI-heavy formatting.

## Milestone 4 — Learner-Facing Output

**Goal:** display grouped meanings first, backend details second.

Target order:

1. Word/headword.
2. Sense buckets.
3. Morphology.
4. Citations/evidence.
5. Source disagreements.

Requirements:

- Snapshot tests for terminal output.
- Raw JSON remains available for debugging.
- Single-source or provisional buckets are marked clearly.

## Milestone 5 — Hydration

**Goal:** enrich stable claims without changing their identity.

Examples:

- CTS URN expansion.
- Author/work labels.
- Dictionary entry links.

Rule: semantic buckets must be identical with or without hydration.

## Milestone 6 — Compounds and Passages

**Goal:** extend word-level lookup/reduction to multi-token Sanskrit and eventually passage reading.

Dependency: do not advance broad passage work until Milestones 1–4 are stable.

## Deprioritized

- First-class ASGI rebuild before CLI semantics stabilize.
- Embedding-backed similarity before deterministic buckets exist.
- Passage interpretation before word-level evidence is reliable.
- Large CLI refactors before baseline commits.
