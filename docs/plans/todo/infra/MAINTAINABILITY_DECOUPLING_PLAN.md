# Maintainability & Decoupling Plan

Context: Following `docs/technical/MAINTAINABILITY_REVIEW.md`, this plan tracks file-by-file improvements to reduce coupling, make backends swappable, and harden observability/test hygiene.

## Goals
- Replace fragile singletons with injectable wiring and validated settings.
- Isolate Sanskrit normalization and backend-specific logic behind testable seams.
- Split oversized adapter modules and standardize validation/logging/health checks.
- Establish reliable test tiers (fast vs integration) and clean artifacts.

## Status
- Phase 1 wiring/config/logging started: LangnetSettings added, wiring factory replaces singleton with warmup toggles, ASGI now binds request context for logs.
- Phase 2 kicked off: SanskritQueryNormalizer extracted with unit tests; Heritage dictionary join now uses CDSL lookups for lemmas.
- Phase 3 completed: Adapters split into per-backend modules with universal-schema outputs; registry composes backends per language; `just test`/`just test-fast` green.
- Phase 4 started: Real health probes landed via `src/langnet/health.py` and ASGI `/api/health`; tool endpoint indentation bug fixed.

## Phases & Tasks

### Phase 1 – Wiring & Config Foundations (@architect design, @coder build)
- `src/langnet/core.py`: Replace `LangnetWiring` singleton with a wiring factory that accepts a typed settings object and per-backend factories; allow lazy warmup toggles.
- `src/langnet/config.py`: Introduce validated settings (dataclass/pydantic) reading env once; ensure `heritage_url` and timeouts come from env, not class defaults; expose profiles (dev/test/prod).
- `src/langnet/logging.py`: Move setup behind explicit init; add request/task correlation hooks.
- Regression checks: run fast unit suite; smoke ASGI `/api/health` + `/api/q` lat/grc/san against fixtures; no API surface changes.

### Phase 2 – Sanskrit Normalization & Heritage Path (@coder, @sleuth for regression)
- `src/langnet/engine/core.py`: Extract `_normalize_sanskrit_word` into `SanskritNormalizer` service with deterministic I/O and logging; drop silent exception swallowing.
- `src/langnet/engine/core.py`: Fix unreachable Heritage dictionary join by wiring a dictionary client or removing the dead block; add regression tests.
- `src/langnet/heritage/morphology.py` & `src/langnet/normalization/*`: Deduplicate encoding detection/canonicalization; add small unit fixtures.
- Regression checks: targeted unit tests for normalizer; run `just fuzz-tools` for heritage/cdsl (validate); rerun Sanskrit integration tests gated on service availability.

### Phase 3 – Adapters Split & Validation Unification (@architect slice, @coder build)
- `src/langnet/backend_adapter.py`: Split per backend (`adapters/{diogenes,whitakers,heritage,cdsl,cltk}.py`) plus shared utils (citations, Foster mapping, betacode helpers). ✅ Completed; legacy shim remains.
- `src/langnet/engine/core.py`, `src/langnet/asgi.py`, `src/langnet/cli.py`: Centralize tool/action/lang validation in one module; reuse everywhere; add unit tests for validation rules.
- Standardize adapter error envelopes and logging fields (backend, duration, hint) to aid observability. (open)
- Regression checks: unit tests for validators; run `just fuzz-tools` (per backend) and `just fuzz-query` to detect schema drift; diff results against saved fixtures before/after split. ✅ Tests green; rerun fuzz with server up to refresh snapshots.

### Phase 4 – Health Checks & Observability (@coder, @artisan for logging polish)
- `src/langnet/asgi.py`: Replace stub health with real probes (cheap parse/ping for Diogenes, model presence for spaCy/CLTK, HTTP for Heritage/CDSL, Whitaker’s binary check); surface degraded states clearly. ✅ Health probes added via `src/langnet/health.py` and wired to `/api/health`; Heritage probe now defaults to `/cgi-bin/sktsearch` (no more 404) with fallback paths retained. Cache component now reports `not_configured` until a cache is wired. Follow-up: real cache stats + documented degraded responses.
- Add request/operation IDs threaded through ASGI and adapters; ensure errors retain stack/context in logs.
- `src/langnet/cli.py`: Share validation with ASGI; improve citation list command to match actual API payloads.
- Regression checks: unit tests for health probe helpers; manual/smoke run `langnet-cli verify`; ASGI `/api/health` should reflect degraded states; ensure no breaking change to `/api/q` responses.
- Regression status: `just test` green; `just fuzz-query` to be rerun with server running to spot-check pedagogical richness.

### Phase 5 – Test & Fixture Hygiene (@coder, @auditor review)
- Remove `tests/__pycache__` and add ignore rules; ensure fixtures are not regenerated in-tree by default.
- Mark integration tests that require external services; add a “fast” just target for unit/schema tests; keep fuzz/integration behind opt-in targets. ✅ Integration tests now set `integration=True`; `just test-fast` runs `nose2 -A '!integration'`.
- Add focused unit tests for new seams: SanskritNormalizer, validation module, adapter splits.
- Integrate existing fuzz harness (`just autobot fuzz run ...`) as an opt-in regression net for adapter changes; regenerate/gate per backend after refactors land to catch schema drift.
- Regression checks: verify “fast” suite passes without external services; ensure integration/fuzz are opt-in and documented; update fixtures only with review/diff of expected changes.

## Deliverables
- Updated modules per phases, passing fast tests; integration tests gated by service availability.
- Docs refreshed (developer guide + architecture notes) to match new wiring/config and health behaviors.
- Changelogs in `docs/technical/MAINTAINABILITY_REVIEW.md` as work lands.
