# Project Plans Overview

This repository organises its design and implementation plans under `docs/plans/` using clear lifecycle categories:

| Category | Directory | What it contains |
|----------|-----------|------------------|
| **Active** | `docs/plans/active/` | Plans that are currently being worked on. They may have partially‑implemented code, ongoing tests, or upcoming milestones. |
| **Todo** | `docs/plans/todo/` | High‑level ideas, future work, or plans that have not yet started. |
| **Completed** | `docs/plans/completed/` | Plans whose work has been fully implemented and verified by tests. |

---

## ✅ Completed Plans

No plans have been moved into `docs/plans/completed/` yet. Update this section when a plan ships.

## 🚧 Active Plans

- `active/infra/SANSKRIT_CANONICAL_CLEANUP.md` — Finish Sanskrit canonicalization propagation (canonical hints, fixtures, CLI surfacing).
- `active/infra/SANSKRIT_HANDOFF.md` — QA for recent Sanskrit normalization/hit-rate changes and Diogenes citation cleanup.
- `active/pedagogy/MAPPING_PHASE_ALIGNMENT.md` — Align `/api/q` mapping with pedagogy-first outputs and Foster function coverage.
- `active/roadmap/TODO.md` — Running list of near-term cleanup items and known regressions.

## 📋 Todo Plans (Not Started)

- **DICO (bilingual)**: `todo/dico/*` (integration, implementation guide, bilingual pipeline, scholarship translation)
- **Diogenes**: `todo/diogenes/GETTING-STARTED.md`, `todo/diogenes/REMOVE_UNRELIABLE_SENSES.md`
- **Infrastructure**: `todo/infra/CTS_INDEXER_PERSEUS_REBUILD.md`, `todo/infra/UNIFIED_TOOL_INTEGRATION.md`
- **Normalization**: `todo/normalization/CANONICAL_QUERY_NORMALIZATION_TODO.md`
- **Pedagogy**: `todo/pedagogy/CITATION_ENRICHMENT_NEXT.md`, `todo/pedagogy/DICTIONARY_FOSTER_AND_ABBREVS*.md`, `todo/pedagogy/HERITAGE_ABBR_FOLLOWUPS.md`, `todo/pedagogy/MAPPING_PHASE_HANDOFF.md`
- **Schema**: `todo/schema/UNIVERSAL_SCHEMA_DEBUG_PLAN.md`
- **Sanskrit**: `todo/skt/HERITAGE_INTEGRATION_NEXT_STEPS.md`

## Status Notes

- Current open issues are tracked in `docs/TODO.md` (Diogenes sense extraction/CTS URNs, Sanskrit canonicalization gaps, CDSL SLP1 artifacts, universal schema). Plans above aim to address them.
- External services (Heritage, Diogenes, Whitaker's Words) remain required for most work and for running tests.

For detailed roadmap and priorities, see [docs/ROADMAP.md](../ROADMAP.md) and the individual plan files listed here.

### Maintenance Guidelines

1. **When a plan moves from active to completed** – move its markdown file to `docs/plans/completed/` and update this README.
2. **When a new high‑level idea appears** – add a markdown file under `docs/plans/todo/`.
3. **Avoid duplicate files** – each plan should live in only one of the three directories.
4. **Review implementation status** - Check if "active" plans are actually complete before updating.
5. **Keep structure clean** - Remove redundant files and directories.
6. **Track progress** - Update status markers (✅ COMPLETE, 🔄 IN PROGRESS, ⏳ PENDING) as work progresses.

### 📚 Related Documentation
- **[docs/ROADMAP.md](../ROADMAP.md)** - Current roadmap and priorities
- **[docs/DEVELOPER.md](../DEVELOPER.md)** - Development workflow and AI integration
