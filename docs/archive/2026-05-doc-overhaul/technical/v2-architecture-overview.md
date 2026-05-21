# Archived: V2 Architecture Overview

Archived on 2026-05-21 during the documentation overhaul.

This is a historical duplicate of the implemented staged-runtime architecture.
Current successors are:

- `docs/technical/ARCHITECTURE.md`
- `docs/technical/design/TECHNICAL_VISION.md`
- `docs/storage-schema.md`

---

This document records the architectural direction that is now mostly implemented in the runtime.

## Implemented Foundation

- CLI command surface.
- Query normalization.
- Tool planning.
- Staged execution.
- Raw/extraction/derivation/claim effects.
- DuckDB-backed storage indexes.
- Handler versioning.
- Claim/triple projection for core handlers.

## Remaining V2 Work

- Better narrative evidence inspection examples in docs.
- Release-quality learner-facing display.
- Reader-form/headword ranking.
- Compact gloss display over full source evidence.
- Optional hydration.

## Current Canonical References

- `docs/technical/ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `docs/plans/active/infra/design-to-runtime-roadmap.md`

Older V2 implementation plans were archived during the April 2026 documentation cleanup.
