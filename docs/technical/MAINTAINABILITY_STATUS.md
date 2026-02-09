# Maintainability Status (consolidated)

Purpose: single snapshot of the maintainability/decoupling effort, replacing the separate handoff/review narratives. For task tracking, continue to use `docs/plans/todo/infra/MAINTAINABILITY_DECOUPLING_PLAN.md` and `docs/plans/todo/infra/MAINTAINABILITY_PICKUP_NOTES.md`.

## Completed
- Wiring/config/logging: `LangnetSettings` + wiring factory with warmup toggles; ASGI request-scoped logging; import-time logging removed.
- Sanskrit normalization: `SanskritQueryNormalizer` service with tests; Heritage dictionary join wired via CDSL lemma lookup.
?- Adapters: split into per-backend modules under `src/langnet/adapters/`; registry composes per language; adapters emit full universal-schema objects; test suites green.
- Validation: shared module `src/langnet/validation.py` used by ASGI and engine; CLI shares aliases.
- Health: probes in `src/langnet/health.py` and `/api/health` (Diogenes parse ping, Heritage HTTP with canonical path, spaCy/CLTK presence, Whitaker’s binary, CDSL DB presence, cache placeholder).
- Tests/hygiene: integration tests tagged (`integration=True`); `just test-fast` skips them; `just test` passes.
- Server verified post-adapter work: Latin/Greek now have Diogenes definitions + citations; Sanskrit consolidated CDSL entries; Whitaker’s/CLTK/Heritage intact.
- Health follow-through: `/api/health` now reports cache `not_configured` cleanly; CLI `verify` honors health payloads (table/json) and flags degraded components; cache stats hook retained.
- Sanskrit tool path dedupe: engine now reuses `SanskritQueryNormalizer` for tool endpoints (CDSL/Heritage) to avoid divergent encoding heuristics; backend errors share a consistent envelope with backend + request id where available.

## Remaining (track in plan)
- Health follow-through: add real cache stats probe (beyond not_configured) and document degraded states explicitly in developer docs.
- Validation: finish threading shared validation into CLI/adapter utilities to eliminate bespoke checks.
- Normalization: tighten Sanskrit transliteration heuristics inside `heritage.encoding_service` if additional edge cases surface.
- Observability: consider adding per-adapter duration hints in responses/logs; ensure no silent swallowing beyond current envelope.
- Fuzz: rerun/update `just fuzz-query` artifacts with server running after backend changes.
- Minor hygiene: ensure `__pycache__` ignored; keep fast vs integration split enforced.

## How to continue
1) Use the plan: `docs/plans/todo/infra/MAINTAINABILITY_DECOUPLING_PLAN.md` (phased tasks) and `docs/plans/todo/infra/MAINTAINABILITY_PICKUP_NOTES.md` (working notes).
2) After backend changes, restart server (`just restart-server`), run `just test` and `just fuzz-query` with server up, and update artifacts if outputs change materially.
3) Update this status doc when major milestones land; keep the detailed plan as the source of truth for task ownership.
