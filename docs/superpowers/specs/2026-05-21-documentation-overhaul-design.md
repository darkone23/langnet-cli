# Documentation Overhaul Design

**Date:** 2026-05-21

## Purpose

LangNet's documentation should accurately describe the codebase, preserve useful
project knowledge, and make the next development moves concrete. The overhaul
will reconcile the current docs, roadmap, and plans against the implemented CLI,
reader corpus, webapp, storage, translation cache, and backend code.

The work is not a cosmetic rewrite. It is a classification, consolidation, and
actionability pass across the whole documentation tree.

## Goals

- Make the current product surface clear: CLI-first runtime, SvelteKit webapp
  adapter, reader corpus tooling, word index, paradigm support, translation
  cache, and evidence inspection.
- Remove or merge redundant documents from the main reading path without losing
  useful information.
- Reduce the maintained current reading path drastically. A healthy target for
  this repository is about 30-40 current Markdown documents across root
  documentation, `docs/`, `webapp/docs/`, and data docs, excluding archive and
  upstream reference material.
- Move stale implementation plans, session notes, and superseded architecture
  into archive paths with clear historical labels.
- Keep active plans realistic, scoped, and tied to actual code and tests. The
  active plan set should be closer to 3-5 genuinely active plans, not a backlog
  of completed implementation records.
- Make roadmap documents actionable: each current priority should point to a
  current plan, command, test, or known decision gate.
- Fix stale references to removed or superseded surfaces such as the old ASGI
  `/api/q` path where they appear in current docs.
- Improve links so readers can move from overview, to operation, to technical
  detail, to active work without guessing which document is canonical.

## Non-Goals

- Do not rewrite upstream reference files under `docs/upstream-docs/` except to
  clarify their index labels.
- Do not delete historical information outright when it still explains a past
  decision, source, or migration. Move it to archive or merge the useful portion
  into a current document.
- Do not introduce new runtime behavior as part of the documentation overhaul.
- Do not make live external services a prerequisite for documentation
  verification.

## Document Taxonomy

Each document should have one primary role.

| Role | Meaning | Expected Location |
| --- | --- | --- |
| Canonical overview | Current project promise, product surface, and where to start | `README.md`, `docs/README.md`, `docs/VISION.md` |
| Operator guide | Commands a user or maintainer runs today | `docs/GETTING_STARTED.md`, reader/web/data guides |
| Developer guide | Development workflow, validation, architecture entry points | `docs/DEVELOPER.md`, `docs/technical/` |
| Current roadmap | Milestones, active priorities, decision gates | `docs/ROADMAP.md`, `docs/EXECUTION_PLAN.md`, one baseline/status doc |
| Active plan | Work that is actually being driven now | `docs/plans/active/<area>/` |
| Todo plan | Scoped future work with enough detail to pick up later | `docs/plans/todo/<area>/` |
| Completed record | Implemented work retained for handoff/audit | `docs/plans/completed/<area>/` |
| Historical archive | Superseded plans, old reports, stale architecture | `docs/archive/` |
| Upstream reference | Source/vendor documentation copied for local reference | `docs/upstream-docs/` |

## Consolidation Policy

Use preservation by consolidation:

1. If two documents say the same thing and both are current, keep the clearer
   one as canonical and merge unique factual details into it.
2. If a document is mostly stale but contains useful decisions, extract those
   decisions into the relevant canonical doc or plan, then archive the original.
3. If a plan describes work already implemented, move it to completed or archive
   depending on whether it remains useful as an implementation record.
4. If a plan is too broad to act on, split it into a short roadmap pointer plus
   one or more scoped active/todo plans.
5. If a document is a historical snapshot, keep it only if its path and header
   make that status obvious.
6. If a document references removed code, commands, or architecture, update the
   reference or mark the document archived.

## Current Drift To Resolve

The initial scan found these likely inconsistencies:

- `AGENTS.md` still references a Starlette ASGI entry, `LanguageEngine`, and
  `/api/q`; the current checkout exposes a Click CLI and SvelteKit API routes.
- Top-level docs correctly emphasize the CLI, but they under-describe the
  current webapp, reader corpus, reader search, and word-index surfaces.
- Several status/roadmap docs overlap: `PROJECT_STATUS.md`,
  `BASELINE_AND_ROADMAP.md`, `EXECUTION_PLAN.md`, `ROADMAP.md`,
  `REFINEMENT_AUDIT.md`, and `SEMANTIC_READINESS.md`.
- `docs/plans/active/` contains many files. Some may be completed, stale,
  duplicates, or broad tracking documents rather than active implementation
  plans.
- Some todo plans likely describe features that now have completed
  implementation records, such as paradigm generation or word-index work.
- Archive files are generally labeled historical, but current docs should avoid
  linking to them as if they were active guidance.

## Audit Method

Create a documentation audit ledger before broad edits. The ledger should list:

- path;
- role;
- current status: keep, update, merge, move to completed, move to todo, archive;
- canonical successor when merged or archived;
- code or command surfaces checked;
- specific edits needed;
- verification notes.

The ledger should live at `docs/DOCUMENTATION_AUDIT.md` unless an existing
audit document is revised and promoted to this role.

## Code Comparison Method

Compare documentation claims to these sources of truth:

- CLI commands from `just cli --help` and subcommand help.
- Recipe list from `just --list` and `webapp/justfile`.
- Python entry points from `pyproject.toml`.
- Runtime modules under `src/langnet/`.
- Webapp API routes under `webapp/src/routes/api/`.
- Tests and fixtures under `tests/` and `webapp/src/lib/*.test.ts`.
- Schema files under `docs/schemas/`.

When the code and docs disagree, prefer the code unless tests or committed plans
show the code is intentionally transitional.

## Target Reading Path

After the overhaul, the main path should be:

1. `README.md` for project promise, quick start, reliable surfaces, and links.
2. `docs/README.md` for the documentation map.
3. `docs/GETTING_STARTED.md` for setup and first commands.
4. `docs/OUTPUT_GUIDE.md` for CLI and JSON interpretation.
5. `docs/READER_CLI_BEGINNER_GUIDE.md`, `docs/READER_CORPUS_STATUS.md`,
   `docs/READER_DATA_BUILD.md`, and `docs/READER_WEB_CONTRACT.md` for reader
   corpus/web integration.
6. `webapp/README.md` for SvelteKit operation.
7. `docs/DEVELOPER.md` and `docs/technical/ARCHITECTURE.md` for development.
8. `docs/ROADMAP.md` and `docs/EXECUTION_PLAN.md` for current priorities.
9. `docs/plans/README.md` for active/todo/completed work.

## Acceptance Criteria

- Every non-archive Markdown file under `docs/` has a clear role in the docs
  map or is intentionally marked as an upstream/reference file.
- `README.md`, `docs/README.md`, `AGENTS.md`, and `docs/DEVELOPER.md` agree on
  the current entry points and command surfaces.
- Stale ASGI `/api/q` guidance is removed from current docs or moved to archive.
- Active plans are reduced to work that is genuinely active and actionable.
- Todo plans are scoped enough to resume without reading stale status reports.
- Completed plans are not listed as active work.
- Roadmap/status docs do not duplicate each other without a stated purpose.
- All command examples use current `just`/CLI forms.
- Cross-links point to existing files.
- The overhaul can be reviewed from `docs/DOCUMENTATION_AUDIT.md` plus the
  resulting file moves/edits.

## Verification

Use lightweight, service-free checks:

- `rg` scans for stale tokens such as `/api/q`, `LanguageEngine`, removed
  command names, broken plan references, and duplicate status claims.
- `just cli --help` and relevant subcommand help to validate command examples.
- `just --list` and `webapp/justfile` to validate recipe references.
- `just lint-all` after edits that touch code examples only if the edit could
  affect formatting or generated docs expectations.
- Link/path checks with repository-local file scans.

Live Diogenes, Heritage, Whitaker, OpenRouter, or reader data builds are not
required for this docs pass.

## Review Model

Perform the overhaul in reviewable slices:

1. Build the audit ledger.
2. Clean the canonical reading path.
3. Reconcile reader/web/data documentation.
4. Triage active/todo/completed plans.
5. Reconcile technical architecture/design docs.
6. Run stale-reference and link checks.
7. Summarize final retained canonical docs and archived/merged documents.

Each slice should preserve useful information before moving or deleting a
document from the active path.
