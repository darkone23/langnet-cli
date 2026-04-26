# Project Status

**Date:** 2026-04-26  
**Overall grade:** B- / 78%

## Summary

LangNet has crossed the foundation threshold. The CLI, planner, staged executor, storage indexes, and core backend handlers exist. The next phase should be stabilization, not feature expansion.

The main project risk is no longer “can the system run?” It is “can we keep the current system coherent, documented, inspectable, and boring enough to build on?”

## Health Card

| Area | Grade | Status |
| --- | --- | --- |
| Build and validation | A- | `just lint-all` and `just test-fast` pass. |
| CLI surface | B+ | Commands exist and are documented; learner UX still backend-keyed. |
| Planner/executor | B+ | Tool plans and staged execution are implemented. |
| Claims/evidence | B | Core handlers now have fixture-backed claim contract coverage. |
| Semantic reduction | C | Design exists; runtime MVP not built. |
| Documentation | B | Active docs consolidated; archive retained for old reports/plans. |
| Release hygiene | C+ | Many changes are still uncommitted and should be checkpointed. |

## Implemented Runtime

- CLI commands: `lookup`, `parse`, `normalize`, `plan`, `plan-exec`, `triples-dump`, `databuild`, `index`.
- Language coverage:
  - Latin: Whitaker, Diogenes, CLTK.
  - Greek: Diogenes, CLTK/spaCy where configured.
  - Sanskrit: Heritage, CDSL.
- Pipeline: fetch → extract → derive → claim.
- Storage: raw responses, extraction indexes, derivation indexes, claims, provenance, and plan indexes.
- Tests: service-free claim contract fixtures for Whitaker, CDSL, Diogenes, CLTK, and Heritage.

## Current Gaps

- `lookup` output is still backend-keyed, not semantic-bucketed.
- Semantic reduction from claims to Witness Sense Units is not implemented.
- Evidence inspection works but needs better filters and summaries.
- Fuzz recipes are diagnostic only; query/compare modes still reflect older API assumptions.
- CLTK may fail cleanly when model data is absent.
- Active planning needs discipline: one canonical roadmap, scoped task files, archive old reports.
- External services remain required for live lookup.

## Immediate Priorities

1. Commit the current baseline in coherent groups.
2. Finish soft cleanup: remove false affordances, stale docs, and unvalidated fixtures.
3. Finish Milestone 1 cleanup: predicate constants and any missing handler contract coverage.
4. Improve `plan-exec` / `triples-dump` evidence inspection.
5. Only then implement the minimal claim-to-WSU extractor.

## Decision Log

- CLI is the reliable interface for now.
- HTTP/API work is deferred until runtime semantics stabilize.
- Deterministic reduction comes before embeddings or semantic constants.
- Passage/compound work must reuse word-level claims and buckets, not bypass them.
- Stabilization work has priority over new learner-facing features until the baseline is committed and inspectable.

## Canonical References

- Roadmap: `docs/ROADMAP.md`
- Active implementation plan: `docs/plans/active/infra/design-to-runtime-roadmap.md`
- Goals: `docs/GOALS.md`
- Architecture: `docs/technical/ARCHITECTURE.md`
- Predicate/evidence contract: `docs/technical/predicates_evidence.md`
- Recipe health: `docs/JUST_RECIPE_HEALTH.md`
- Semantic readiness: `docs/SEMANTIC_READINESS.md`
