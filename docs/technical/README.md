# Technical Documentation

Use this directory for implementation-facing references.

## Current References

- `ARCHITECTURE.md` — current CLI/runtime architecture.
- `predicates_evidence.md` — canonical claim/triple predicates and evidence fields.
- `semantic_triples.md` — graph-model notes for claims and downstream reduction.
- `triples_txt.md` — older but still useful explanation of scoped interpretations.
- `backend/` — backend-specific operational notes.
- `design/TECHNICAL_VISION.md` — technical design map from staged effects to learner output.
- `design/` — detailed design notes for planning, witnesses, semantic reduction, and hydration.
- `opencode/` — AI/persona workflow notes.

## Maintenance Rules

- Keep `ARCHITECTURE.md` aligned with code that exists now.
- Keep speculative designs under `design/`.
- Keep historical implementation reports in `docs/archive/`, not here.
- When predicates or evidence fields change, update `predicates_evidence.md` and the related tests.
