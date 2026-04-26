# Design Notes

These files describe intended architecture beyond the current runtime.

## Current Priority

1. Claim/evidence contract stability.
2. Evidence inspection.
3. Semantic reduction MVP.
4. Learner-facing semantic output.
5. Hydration.
6. Compounds/passages.

## Files

- `tool-response-pipeline.md` — staged fetch/extract/derive/claim model.
- `witness-contracts.md` — evidence and witness requirements.
- `classifier-and-reducer.md` — claim-to-sense-bucket design.
- `semantic-structs.md` — planned dataclasses for reduction.
- `hydration-reduction.md` — optional post-claim enrichment.
- `query-planning.md` — planner and execution expectations.
- `entry-parsing.md` — dictionary-entry parsing notes.
- `tool-fact-architecture.md` and `tool-fact-flow.md` — older conceptual notes retained for reference.

Design files are not proof of implementation. Check `docs/PROJECT_STATUS.md` and `docs/ROADMAP.md` for current status.
