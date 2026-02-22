# Documentation Audit (2026-02-15)

Purpose: capture the current documentation state, highlight drift, and define next actions before the next planning cycle. This is a living tracker—update it as cleanup lands.

## Current Observations
- **Handoff consolidation**: Tool executor + triples status is now canonical at `docs/handoff/tool-execution-and-triples.md` with an index in `docs/handoff/README.md`. Older handoff fragments were removed.
- **Scoped triples alignment**: `docs/technical/semantic_triples.md` now points to `docs/technical/triples_txt.md` for anchor/predicate rules; the active plan `docs/plans/active/tool-fact-indexing.md` references both and the handoff.
- **Plan layout**: Semantic-reduction plans remain split across multiple status/checklist files under `docs/plans/active/semantic-reduction/`; several are overlapping (current-status, gaps, phase0-qa, getting-started). Needs consolidation into one status + one getting-started.
- **Output expectations**: `OUTPUT_GUIDE.md` includes per-language sample responses and display rules; live snapshots would still help.
- **Entry-point duplication trimmed**: `docs/README.md` defers to the root `README.md`; plan structure guidance lives in `docs/plans/README.md`.

## High-Priority Next Steps
1. **Semantic-reduction doc merge** (@auditor @scribe): DONE — consolidated into `SEMANTIC_REDUCTION_README.md` (status/priorities) + concise `semantic-reduction-getting-started.md`; redundant status/checklist/QA files removed.
2. **Predicate/evidence constants surfaced** (@architect @scribe): add a small constants table to `docs/technical/semantic_triples.md` (mirroring `tool-fact-indexing.md`) and ensure handlers refer to it.
3. **Capture real outputs** (@coder @scribe): augment `OUTPUT_GUIDE.md` with live CLI/API snapshots (LAT/GRC/SAN) once backends are available; include foster codes and citations.
4. **Feature-area discipline** (@scribe): keep new plans inside feature subfolders (`skt/`, `whitakers`, `dico`, `pedagogy`, `infra`); add a one-page index per area as they grow.

## Reliable Launch Points (use these first)
- `docs/GETTING_STARTED.md` — setup and first queries.
- `docs/OUTPUT_GUIDE.md` — schema overview for CLI/API output.
- `docs/DEVELOPER.md` — dev workflow, debugging, and test commands.
- `docs/technical/ARCHITECTURE.md` — request flow, adapters, and schema boundaries.
- `docs/plans/README.md` — how to structure new plans and where to move them.

Update this file after each cleanup to keep the audit useful.
