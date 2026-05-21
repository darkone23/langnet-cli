# Design Notes

These files describe intended architecture around the current runtime. Start with `TECHNICAL_VISION.md`; it explains how the design pieces fit together and where implementation stops today.

Design files are not proof of implementation. Check `../ARCHITECTURE.md`,
`../../ROADMAP.md`, and `../../EXECUTION_PLAN.md` for current status.

## Implemented Runtime Contracts

- CLI-first staged runtime: normalize, plan, fetch, extract, derive, claim.
- CLI JSON surfaces for lookup, encounter, reader, word-index, paradigm,
  translation-cache, tools, langs, and doctor.
- SvelteKit adapter routes for search, reader, word-index, paradigm, MOTD, and
  translation-cache.
- Local DuckDB-backed source/index stores for DICO, Gaffiot, Bailly, Lewis
  1890, CTS metadata, reader corpora, word indexes, and translation cache.
- Claim/triple evidence projection and exact Witness Sense Unit reduction for
  learner encounter output.

## Future Design Targets

1. Broader source-specific entry segmentation and compact gloss coverage.
2. Optional hydration that does not alter base evidence or bucket identity.
3. Near-match semantic reduction only after exact-bucket behavior is stable.
4. Passage-level interpretation after word-level and reader surfaces are stable.
5. Compound handling with explicit source evidence.

## Files

- `TECHNICAL_VISION.md` — canonical design map from staged effects to learner output.
- `tool-response-pipeline.md` — staged fetch/extract/derive/claim model.
- `query-planning.md` — planner and execution expectations.
- `entry-parsing.md` — dictionary-entry parsing notes.
- `witness-contracts.md` — evidence and witness requirements.
- `classifier-and-reducer.md` — claim-to-sense-bucket design.
- `semantic-structs.md` — current reducer/display structures and future fields.
- `hydration-reduction.md` — optional post-claim enrichment.
- `tool-fact-architecture.md` and `mermaid/tool-fact-flow.md` — older conceptual notes retained for reference.

Historical duplicate: `../../archive/2026-05-doc-overhaul/technical/v2-architecture-overview.md`.

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
