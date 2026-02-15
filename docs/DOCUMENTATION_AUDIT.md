# Documentation Audit (2026-02-15)

Purpose: capture the current documentation state, highlight drift, and define next actions before the next planning cycle. This is a living tracker—update it as cleanup lands.

## Current Observations
- **Plan layout normalized**: Semantic-reduction plans live under `docs/plans/active/semantic-reduction/`, `docs/plans/todo/semantic-reduction/`, and `docs/plans/completed/semantic-reduction/`.
- **Status caveats added**: Semantic-reduction docs note Phase 0–2 modules/tests exist; tests were not executed here (use `just test tests.test_semantic_reduction_clustering` inside the devenv shell).
- **Legacy note removed**: `docs/TODO.md` was deleted; any remaining nuggets should already exist in semantic-reduction plan files.
- **Entry-point duplication trimmed**: `docs/README.md` is now an index that defers to the root `README.md`.
- **Output expectations**: `OUTPUT_GUIDE.md` now includes per-language sample responses and display rules; real environment snapshots would still help.

## High-Priority Next Steps
1. **Verify semantic-reduction claims** (@architect @auditor): run the semantic-reduction tests via `devenv shell just -- test tests.test_semantic_reduction_clustering`; adjust statuses based on results.
2. **Add feature-area discipline** (@scribe): create subfolders for other workstreams (`skt/`, `whitakers`, `dico`, `pedagogy`, `infra`) as new plans appear, with a one-page index per area.
3. **Capture real outputs** (@coder @scribe): replace/sample-augment `OUTPUT_GUIDE.md` with live CLI/API responses (Latin, Greek, Sanskrit) once backends are available; ensure foster codes and citations are shown in examples.
4. **Prune redundant semantic-reduction text** (@auditor): after verification, merge or remove overlapping status docs to keep one concise status and one plan index.

## Reliable Launch Points (use these first)
- `docs/GETTING_STARTED.md` — setup and first queries.
- `docs/OUTPUT_GUIDE.md` — schema overview for CLI/API output.
- `docs/DEVELOPER.md` — dev workflow, debugging, and test commands.
- `docs/technical/ARCHITECTURE.md` — request flow, adapters, and schema boundaries.
- `docs/plans/README.md` — how to structure new plans and where to move them.

Update this file after each cleanup to keep the audit useful.
