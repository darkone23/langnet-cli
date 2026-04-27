# LangNet Documentation

This directory is the working documentation set for `langnet-cli`.

## Start Here

- `docs/VISION.md` — product promise, audience, principles, and long-term direction.
- `docs/PROJECT_STATUS.md` — current health card, risks, and next decisions.
- `docs/EXECUTION_PLAN.md` — compact roadmap, task, gap, and risk index.
- `docs/REFINEMENT_AUDIT.md` — section-by-section refinement stocktake and acceptance checks.
- `docs/GETTING_STARTED.md` — setup, service requirements, and first commands.
- `docs/ROADMAP.md` — canonical implementation sequence.
- `docs/GOALS.md` — concise goals and current north star.
- `docs/PEDAGOGICAL_PHILOSOPHY.md` — learner-facing grammar and evidence policy.
- `docs/JUST_RECIPE_HEALTH.md` — current recipe wiring and fuzz-harness findings.
- `docs/SEMANTIC_READINESS.md` — current exact-reduction readiness and gaps before broader semantic generalization.
- `docs/TRANSLATION_CACHE_PLAN.md` — lazy DICO/Gaffiot French → English translation cache design.

## Developer References

- `docs/DEVELOPER.md` — local workflow, validation commands, and debugging notes.
- `docs/OUTPUT_GUIDE.md` — current output shapes and evidence inspection.
- `docs/handler-development-guide.md` — how to add or change staged handlers.
- `docs/storage-schema.md` — DuckDB cache/index schema and staged effect tables.

## Technical References

- `docs/technical/ARCHITECTURE.md` — current runtime architecture.
- `docs/technical/design/TECHNICAL_VISION.md` — target technical design map.
- `docs/technical/predicates_evidence.md` — canonical claim/triple predicates and evidence fields.
- `docs/technical/design/` — design notes for semantic reduction, hydration, planning, and witness contracts.
- `docs/technical/backend/` — backend-specific notes for Diogenes, Whitaker, Heritage/CDSL, and related tooling.

## Planning

- `docs/plans/active/infra/design-to-runtime-roadmap.md` — current active plan.
- `docs/plans/active/infra/local-lexicon-witness-handoff.md` — current Gaffiot/DICO source-witness handoff and next steps.
- `docs/plans/completed/` — completed work records.
- `docs/archive/2026-04-cleanup/` — historical reports and superseded plans retained for audit only.

## Maintenance Rule

Keep active docs factual and short. If a document describes completed work, session notes, stale architecture, or speculative old planning, move it to `docs/archive/` instead of leaving it in the main reading path.
