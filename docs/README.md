# LangNet Documentation

This directory is the working documentation set for `langnet-cli`.

## Start Here

- `docs/PROJECT_STATUS.md` — current health card, risks, and next decisions.
- `docs/GETTING_STARTED.md` — setup, service requirements, and first commands.
- `docs/ROADMAP.md` — canonical implementation sequence.
- `docs/GOALS.md` — product philosophy and long-term educational direction.
- `docs/JUST_RECIPE_HEALTH.md` — current recipe wiring and fuzz-harness findings.
- `docs/SEMANTIC_READINESS.md` — gaps before semantic reduction is safe to implement.

## Developer References

- `docs/DEVELOPER.md` — local workflow, validation commands, and debugging notes.
- `docs/OUTPUT_GUIDE.md` — current output shapes and evidence inspection.
- `docs/handler-development-guide.md` — how to add or change staged handlers.
- `docs/storage-schema.md` — DuckDB cache/index schema and staged effect tables.

## Technical References

- `docs/technical/ARCHITECTURE.md` — current runtime architecture.
- `docs/technical/predicates_evidence.md` — canonical claim/triple predicates and evidence fields.
- `docs/technical/design/` — design notes for semantic reduction, hydration, planning, and witness contracts.
- `docs/technical/backend/` — backend-specific notes for Diogenes, Whitaker, Heritage/CDSL, and related tooling.

## Planning

- `docs/plans/active/infra/design-to-runtime-roadmap.md` — current active plan.
- `docs/plans/todo/infra/junior-task-backlog.md` — small tasks suitable for intermittent junior-engineer work.
- `docs/plans/completed/` — completed work records.
- `docs/archive/2026-04-cleanup/` — historical reports and superseded plans retained for audit only.

## Maintenance Rule

Keep active docs factual and short. If a document describes completed work, session notes, stale architecture, or speculative old planning, move it to `docs/archive/` instead of leaving it in the main reading path.
