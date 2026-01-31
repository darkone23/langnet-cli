# Project Plans Overview

This repository organises its design and implementation plans under `docs/plans/` using three clear categories:

| Category | Directory | What it contains |
|----------|-----------|------------------|
| **Completed** | `docs/plans/completed/` | Plans whose work has been fully implemented and verified by tests. |
| **Active** | `docs/plans/active/` | Plans that are currently being worked on. They may have partially‑implemented code, ongoing tests, or upcoming milestones. |
| **Todo** | `docs/plans/todo/` | High‑level ideas, future work, or plans that have not yet started. |

---

## ✅ Completed Plans

- `whitakers_test_coverage.md`
- `WHITAKERS_PARSER_TESTING_PLAN.md`
- `heritage_parser_migration.md` (under `completed/` – reflects the migration of the older parser to the newer implementation.)

> **Note:** The `heritage_parser_migration.md` file in `completed/` documents the final state of the legacy parser migration. The earlier duplicate in `todo/` has been removed to avoid confusion.

## 🚧 Active Plans

- **Normalization** – `CANONICAL_QUERY_NORMALIZATION_PLAN.md`
- **Heritage Platform** –
  - `HERITAGE_INTEGRATION_PLAN.md`
  - `HERITAGE_ENCODING_STRATEGY.md`
  - `HERITAGE_PARSER_LARK_MIGRATION_PLAN.md`
  - `HERITAGE_PARSER_SPRINT_REVIEW.md`
- **Pedagogy** – `PEDAGOGICAL_ROADMAP.md` and `PEDAGOGY_GOALS_STATUS.md`

These plans contain concrete milestones (e.g., smart‑encoding detection, Lark‑based parser migration) and are reflected by code that is partially implemented in the `src/` tree.

## 📋 Todo Plans

- **DICO (French‑Sanskrit bilingual dictionary)** – integration, implementation guide, and pipeline documents (`DICO_INTEGRATION_PLAN.md`, `DICO_IMPLEMENTATION_GUIDE.md`, `DICO_BILINGUAL_PIPELINE.md`).
- Any additional future work that has not yet been started.

---

### Maintenance Guidelines

1. **When a plan moves from active to completed** – move its markdown file to `docs/plans/completed/` and update this README.
2. **When a new high‑level idea appears** – add a markdown file under `docs/plans/todo/`.
3. **Avoid duplicate files** – each plan should live in only one of the three directories.

Feel free to add or edit the entries above as the project evolves.
