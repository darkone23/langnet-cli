# Roadmap

This is the canonical milestone roadmap. It turns the vision in `docs/VISION.md` into implementation order. The compact operating queue is `docs/EXECUTION_PLAN.md`; detailed implementation tracking lives in `docs/plans/active/infra/design-to-runtime-roadmap.md`.

## Current Status

The project has a working CLI, planner, staged executor, storage layer, and real backend handlers. The current priority is stabilization: make the existing system coherent, tested, documented, and safe to extend.

Current grade: **B / 84%**.

- Build health: strong.
- Runtime architecture: usable.
- Claim/evidence layer: improving, fixture-tested across core handlers, and content-addressed for local DICO/Gaffiot raw responses.
- Semantic reduction: exact WSU/bucket MVP is runtime-wired through `encounter`,
  but learner display quality is still below the product bar for hard terms.
- Sanskrit runtime model: Heritage is the preferred analysis/morphology source; CDSL and DICO provide source-gloss supplements.
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
- CDSL exposes IAST display fields while preserving SLP1 source keys.
- Translation cache helpers and cache-hit projection exist.
- `triples-dump --output json` exposes structured claim/triple inspection.
- Snapshot-style tests cover representative `encounter` output, including Sanskrit Heritage analysis rows.
- The 50-word lexical audit separates gloss coverage from Heritage morphology coverage.

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
- First exact-gloss WSU reduction and `encounter` CLI output.

Remaining:

- Normalize predicate constants across handlers.
- Add or document coverage for any secondary/stub handlers.
- Continue improving reducer-focused inspection workflows.
- Keep translated DICO/Gaffiot cache hits as derived evidence without replacing source French evidence.

## Milestone 2 — Evidence Inspection

**Goal:** developers can answer “where did this fact come from?” from CLI output alone.

Tasks:

- Improve `plan-exec` summaries with cache status, skipped-call reasons, stage counts, and handler versions.
- Keep `triples-dump` text and JSON inspection working.
- Document one end-to-end inspection workflow for Latin and Sanskrit.

## Milestone 3 — Semantic Reduction MVP

**Goal:** build a deterministic reducer over claims/triples.

MVP:

- Extract Witness Sense Units from `has_sense` + `gloss` triples.
- Cluster exact or near-exact glosses deterministically.
- Emit stable sense-bucket IDs.
- Preserve witness claim IDs and evidence.

Current implementation covers exact buckets, structured triples JSON, first encounter snapshots across Sanskrit/Latin/Greek, translation-cache golden rows, Heritage analysis display, and structured `plan-exec` summaries. Remaining MVP work is mostly interface hardening: clearer display ranking, better source-specific structuring, and narrative evidence-inspection examples.

Do not include yet:

- Embeddings.
- Full semantic constants.
- Passage-level context.
- UI-heavy formatting.

## Milestone 4 — Learner-Facing Output

**Goal:** display grouped meanings first, backend details second.

Active plan: `docs/plans/active/pedagogy/learner-encounter-roadmap.md`.

Target order:

1. Word/headword.
2. Source-backed analysis or morphology where it is the best guide to the form, especially Sanskrit Heritage.
3. Sense buckets.
4. Citations/evidence.
5. Source disagreements.

Requirements:

- Snapshot tests for terminal output.
- Raw JSON remains available for debugging.
- Single-source or provisional buckets are marked clearly.
- CDSL learner text should show IAST forms while raw SLP1/source keys remain inspectable.
- Default output should hide unrelated candidate noise and developer diagnostics.
- Cached DICO/Gaffiot translations should enrich learner output when exact cache
  rows exist, without invoking live translation by default.
- Sanskrit, Latin, and Greek must each have accepted-output examples for a hard
  common word before this milestone is considered stable.

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
