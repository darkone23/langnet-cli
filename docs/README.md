# LangNet Documentation

This directory is the maintained documentation map for `langnet-cli`. Use it to
find the current guide for a task; archived and upstream-reference material is
kept for history, not day-to-day operation.

## Current Path

Start here:

- `README.md` - project overview and current product surfaces.
- `docs/GETTING_STARTED.md` - setup, services, and first commands.
- `docs/OUTPUT_GUIDE.md` - CLI and JSON output guide.
- `docs/DEVELOPER.md` - local workflow, validation, and debugging notes.
- `docs/ROADMAP.md` - canonical milestone roadmap.
- `docs/EXECUTION_PLAN.md` - compact active queue and decision gates.
- `docs/READER_CLI_BEGINNER_GUIDE.md` - reader corpus operation.
- `webapp/README.md` - SvelteKit webapp operation.

## Reader And Web

- `docs/READER_CLI_BEGINNER_GUIDE.md` - discover, enumerate, and read locally indexed texts.
- `docs/READER_CORPUS_STATUS.md` - reader corpus status and validation checkpoints.
- `docs/READER_DATA_BUILD.md` - reader data build and index workflow.
- `docs/READER_WEB_CONTRACT.md` - reader/web integration contract.
- `webapp/README.md` - webapp setup and operational notes.
- `webapp/docs/` - webapp-specific backend, UI, operations, and regression notes.

## Developer References

- `docs/DEVELOPER.md` - development workflow and validation commands.
- `docs/OUTPUT_GUIDE.md` - output shapes, evidence inspection, and JSON contracts.
- `docs/GOALS.md` - concise product goals and non-goals.
- `docs/VISION.md` - product promise, audience, and principles.
- `docs/PEDAGOGICAL_PHILOSOPHY.md` - learner-facing grammar and evidence policy.
- `docs/reference/foster-ossa/DIDACTIC_SYNTHESIS.md` - Foster Ossa synthesis and platform implications.
- `docs/SEMANTIC_READINESS.md` - semantic-reduction readiness gates.
- `docs/TRANSLATION_CACHE_PLAN.md` - translation cache behavior and constraints.

## Technical References

- `docs/technical/README.md` - technical documentation map.
- `docs/technical/ARCHITECTURE.md` - current runtime architecture.
- `docs/technical/backend/` - backend-specific notes.
- `docs/technical/design/` - design notes for planning, reduction, hydration, and witness contracts.
- `docs/technical/predicates_evidence.md` - canonical predicates and evidence fields.
- `docs/storage-schema.md` - DuckDB cache and index schema notes.
- `docs/CITATIONS.md` - source credits and attribution.

## Planning

- `docs/plans/README.md` - current active, todo, and completed plan map.
- `docs/ROADMAP.md` - durable milestone sequence.
- `docs/EXECUTION_PLAN.md` - current operating queue.
- `docs/DOCUMENTATION_AUDIT.md` - documentation overhaul ledger.

Avoid maintaining separate lists of many active plans here; `docs/plans/README.md`
is the canonical plan index.

## Archive And Upstream References

- `docs/archive/` - historical reports, superseded plans, and dated status docs.
- `docs/upstream-docs/` - copied upstream/vendor references.
- `docs/superpowers/` - overhaul specs and implementation plans for the agent workflow.

Archive files may contain stale commands or older architecture names. Use them
only for historical context unless a current doc points to a specific decision.

## Maintenance Rule

Keep current docs factual and short. If a document describes completed work,
session notes, stale architecture, or speculative old planning, move it to
`docs/archive/` or `docs/plans/completed/` instead of leaving it in the main
reading path.
