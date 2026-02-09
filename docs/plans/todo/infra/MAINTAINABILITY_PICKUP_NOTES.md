# Maintainability Refactor – Pickup Notes (closeout)

Use this to finish the remaining maintainability/decoupling work and then move the plan to `completed/`. Keep scope narrow—do not restart earlier phases.

- **Read first**: 
  - Plan: `docs/plans/todo/infra/MAINTAINABILITY_DECOUPLING_PLAN.md` (phases + regression checks)
  - Context: `docs/technical/MAINTAINABILITY_STATUS.md`
- **Work in phases**: Don’t mix phases. Start with Phase 1 (wiring/config) before normalization/adapters.
- **Regression gates**: Use the checks listed per phase. Keep API shapes stable unless explicitly approved.
- **Shell**: Run everything via devenv: `devenv shell langnet-cli -- <cmd>`.
- **Testing**:
  - Fast/unit: maintain/run the “fast” target (unit/schema tests that don’t need services).
  - Integration: mark tests needing external services; keep them opt-in.
  - Fuzz: for adapter/normalizer changes, run `just fuzz-tools` (per backend) or `just fuzz-query` and diff outputs; only update fixtures with clear rationale.
- **Targets**: `just test-fast` runs nose2 with `-A '!integration'`. Integration suites are still under `just test`.
- **Smoke API**: After wiring/health changes, hit `/api/health` and `/api/q` (lat/grc/san) or run `langnet-cli verify` inside devenv.
- **Docs**: Update `docs/technical/*` and the plan as phases land; note any fixture updates.
- **Health probes**: `/api/health` now calls `src/langnet/health.py`. Extend there (cache stats, degraded messaging) rather than inlining logic in ASGI/CLI.
- **Adapters**: Split complete. Use `src/langnet/adapters/*` for backend-specific changes; legacy `src/langnet/backend_adapter.py` is just a shim. Adapters now emit full universal-schema entries (definitions + morphology + dictionary blocks) for `diogenes`, `whitakers`, `cltk|spacy`, `heritage`, `cdsl`.
- **Fuzzing**: Harness expects a running API server (default http://localhost:8000). Current `just fuzz-query` artifacts under `examples/debug/fuzz_results_query/` need refresh; rerun with server up before judging outputs.
- **Hygiene**: No `__pycache__` or ad-hoc artifacts checked in; put scratch/debug outputs under `examples/debug`. Restart API after backend changes: `just restart-server`.

## Progress snapshot
- `/api/health` + `langnet verify` aligned; cache reports `not_configured` cleanly with duration/message and exits non-zero on degraded.
- Sanskrit tool paths now reuse `SanskritQueryNormalizer` for CDSL/Heritage tool endpoints; backend errors share a consistent envelope (backend + request id when available).

## Closeout checklist (ship these, then archive this doc)
1) **Health follow-through (P0)**  
   - Cache: keep `not_configured` status; add real stats provider when available and document degraded states.  
   - CLI/API: `langnet-cli verify` now reflects `/api/health`; extend docs and tests for degraded paths.  
   - Tests: extend health tests to cover cache/degraded paths.
2) **Validation threading (P0)**  
   - Replace bespoke validation in CLI/adapters with `src/langnet/validation.py`; keep shared rules as the single source.  
   - Tests: unit coverage for the shared validation entrypoints.
3) **Normalization/encoding dedupe (P1)**  
   - Fold straggling helpers into `heritage.encoding_service`; tighten Sanskrit transliteration heuristics.  
   - Tests/fixtures: canonicalization cases (`agni`, `vrika`, long vowels).
4) **Observability polish (P1)**  
   - Standardize adapter error envelopes (backend + duration + request id); remove silent swallowing.  
   - Tests: add a small adapter error harness to assert envelope shape.
5) **Fuzz refresh (P2)**  
   - Rerun `just fuzz-query` with server running; update `examples/debug/fuzz_results_query/` only when outputs improve/regress with rationale.  
   - Record notable diffs in `docs/technical/MAINTAINABILITY_STATUS.md`.

**Definition of done:** All above items landed with tests/docs, health + validation unified, fuzz artifacts refreshed. Then move `MAINTAINABILITY_DECOUPLING_PLAN.md` and this file to `docs/plans/completed/infra/` and note the closure in `docs/plans/README.md`.
