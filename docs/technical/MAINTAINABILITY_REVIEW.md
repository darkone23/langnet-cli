# Maintainability Review (2024-XX-XX)

Scope: high-level audit of langnet-cli for long-term maintenance and decoupling. Focused on ASGI/CLI entrypoints, `LanguageEngine` orchestration, adapters, Sanskrit normalization, and supporting infra/tests. This snapshot includes the initial wiring/config/logging hardening (LangnetSettings + wiring factory + request-context logging).

Work tracking: improvement tasks are broken down in `docs/plans/todo/infra/MAINTAINABILITY_DECOUPLING_PLAN.md` (phased, file-by-file, with @persona owners).

## What Looks Solid
- Clear universal schema and adapter layer keeps backend-specific data at the edges (`src/langnet/backend_adapter.py`).
- Strong developer docs and task automation (`docs/DEVELOPER.md`, `docs/technical/*`, `justfile`) reduce onboarding friction.
- CLI + ASGI share common surface area and already expose raw tool endpoints, which helps debugging and fixture generation.
- Tests exist for most subsystems (Heritage, CDSL, Whitaker’s, Foster), giving a good safety net once the external services are available.

## Findings (ordered by impact)
1) **Wiring now configurable (addressed)** — `LangnetWiring` has been replaced by a factory + config object (`src/langnet/core.py`) with warmup toggles. Residual risk: backend classes like `SanskritCologneLexicon` still hold internal singletons and should be revisited when adapters are split.
2) **Sanskrit normalization refactored (addressed)** — `_normalize_sanskrit_word` was extracted into a dedicated `SanskritQueryNormalizer` service with deterministic output and tests (`src/langnet/engine/sanskrit_normalizer.py`, `tests/test_sanskrit_normalizer.py`). Remaining risk: encoding helpers still duplicated with `heritage.encoding_service` and should be unified.
3) **Heritage dictionary join** — Now wired to CDSL lookup when a lemma is present (`src/langnet/engine/core.py`). Combined analyses are populated; further refinement needed to allow alternate dictionary sources and clearer error envelopes.
4) **Health checks improved but still shallow** — `/api/health` now calls real probes via `src/langnet/health.py` (Diogenes parse ping, Heritage HTTP, spaCy/CLTK presence, Whitaker’s binary, CDSL DB existence). Remaining gaps: cache stats are still a stub, degraded states need documenting, and Heritage 404s need a clear policy.
5) **Validation duplication reduced (partial)** — Shared validation now lives in `src/langnet/validation.py` and is used by ASGI + engine. CLI still has bespoke validation; remaining risk of drift until CLI and adapters migrate.
6) **Configuration is ad-hoc (addressed, monitor rollout)** — `LangnetSettings` now reads env once, validates URLs/timeouts, and is injectable (`src/langnet/config.py`). Follow-up: thread settings through remaining modules that still use module-level defaults (e.g., Heritage client/env fallbacks) and ensure prod/test profiles are honored.
7) **Adapters file is overgrown** — `src/langnet/backend_adapter.py` houses five adapters plus shared helpers (>1,200 LOC) with mixed responsibilities (citation normalization, morphology enrichment, POS heuristics). Cross-cutting helpers (betacode handling, Foster mapping) are not reusable elsewhere without importing the whole module.
8) **Testing hygiene** — `tests/__pycache__` artifacts are checked in, and many tests rely on live services without marking or skipping when unavailable. Nose2 is configured, but there is no split between fast unit tests and integration/fuzz runs, so CI would be brittle.
9) **Observability gaps (partial)** — Logging now requires explicit setup with request/task context hooks, and ASGI binds request metadata (`src/langnet/logging.py`, `src/langnet/asgi.py`). Remaining gaps: adapters still swallow stack traces into `{ "error": str(e) }` and lack backend/duration tagging.

## Forward Plan (prioritized)
**Stabilize wiring and configuration**
- ✅ Replace the global `LangnetWiring` singleton with an explicit factory that accepts a config object and backend factories; warmup toggles now live in `LangnetWiringConfig`.
- ✅ Introduce a typed settings object that reads env once, validates URLs/timeouts, and is injected into ASGI/CLI/engine. Follow-up: thread settings through remaining heritage/CDSL helpers and profile-specific defaults. (@architect, @coder)

**Decouple Sanskrit normalization and backends**
- ✅ Extract a `SanskritNormalizer` service with clear inputs/outputs and deterministic logging; added unit coverage. Follow-up: deduplicate encoding detection with `heritage.encoding_service` and tighten transliteration heuristics.
- ✅ Fix the unreachable Heritage dictionary join by wiring the CDSL lookup; combined block now populated. Follow-up: support alternate dictionary sources and better error envelopes. (@coder)

**Make health/validation trustworthy**
- Rework health checks to hit minimal backend probes (cheap HEAD/parse for Diogenes, model presence for spaCy/CLTK, HTTP ping for Heritage/CDSL) and surface degraded state with actionable messages. ✅ Probes implemented in `src/langnet/health.py` and wired to `/api/health`; follow-up: cache stats probe + clearer degraded messaging + CLI parity. (@coder)
- ✅ Centralize validation rules (languages, tools/actions) in one module used by ASGI and `LanguageEngine` with unit tests. Follow-up: thread through CLI and adapter utilities. (@coder)

**Right-size adapters and observability**
- Split `backend_adapter.py` into per-backend modules with shared utilities (citations, Foster mapping, betacode/Greek helpers). Keep a thin registry that composes them. (@architect for slice plan, @coder for refactor)
- Standardize error envelopes and logging: attach request ids, backend names, and durations; avoid swallowing stack traces in adapters. (@artisan for logging shape)

**Testing/fixtures hygiene**
- Remove committed `tests/__pycache__` and add ignore rules; mark integration tests that need external services and provide lightweight contract tests for adapter interfaces using fixtures. (@coder, @auditor for coverage review)
- Add a “fast” test target that runs schema/unit tests without external processes; keep fuzz/integration behind explicit just targets. (@coder)

## Next Checkpoints
1. Draft a wiring/config RFC with interface boundaries and rollout steps (singleton removal, settings injection).  
2. Implement Sanskrit normalization extraction with golden fixtures to prevent regressions.  
3. Ship honest health endpoints and shared validation utilities.  
4. Split adapters and tighten logging/telemetry.  
5. Clean test tree and establish fast vs integration suites.
