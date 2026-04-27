# Design Notes

These files describe intended architecture around the current runtime. Start with `TECHNICAL_VISION.md`; it explains how the design pieces fit together and where implementation stops today.

Design files are not proof of implementation. Check `../ARCHITECTURE.md`, `../../PROJECT_STATUS.md`, and `../../ROADMAP.md` for current status.

## Current Priority

1. Claim/evidence contract stability.
2. Evidence inspection.
3. Semantic reduction MVP.
4. Learner-facing semantic output.
5. Hydration.
6. Compounds/passages.

## Files

- `TECHNICAL_VISION.md` — canonical design map from staged effects to learner output.
- `v2-architecture-overview.md` — summary of the mostly implemented V2 foundation.
- `tool-response-pipeline.md` — staged fetch/extract/derive/claim model.
- `query-planning.md` — planner and execution expectations.
- `entry-parsing.md` — dictionary-entry parsing notes.
- `witness-contracts.md` — evidence and witness requirements.
- `classifier-and-reducer.md` — claim-to-sense-bucket design.
- `semantic-structs.md` — planned dataclasses for reduction.
- `hydration-reduction.md` — optional post-claim enrichment.
- `tool-fact-architecture.md` and `tool-fact-flow.md` — older conceptual notes retained for reference.

## Reading Order

1. `TECHNICAL_VISION.md`
2. `../ARCHITECTURE.md`
3. `../predicates_evidence.md`
4. `tool-response-pipeline.md`
5. `witness-contracts.md`
6. `classifier-and-reducer.md`
7. `hydration-reduction.md`

## Maintenance Rules

- Keep implemented behavior in `../ARCHITECTURE.md`.
- Keep target design and constraints here.
- If a design becomes implemented, update both this directory and the architecture/status docs.
- If a design is superseded, mark it clearly or move it to `../../archive/`.
