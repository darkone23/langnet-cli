# Maintainability Work Handoff

Status update for the decoupling/maintainability initiative. See `docs/plans/todo/infra/MAINTAINABILITY_DECOUPLING_PLAN.md` for phased tasks and `docs/plans/todo/infra/MAINTAINABILITY_PICKUP_NOTES.md` for working instructions.

## Completed this round
- Wiring/config/logging hardened: `LangnetSettings` + `build_langnet_wiring` with warmup toggles; ASGI uses request-scoped logging; import-time logging removed from backends.
- Sanskrit normalization extracted: `SanskritQueryNormalizer` service with unit tests; engine now consumes the service; encoding detection centralized via Heritage encoding service; Heritage dictionary join wired via CDSL lemma lookup.
- Shared validation module: `src/langnet/validation.py` with tests; ASGI and engine tool-data paths now share validation; CLI query command uses shared validation and aliases.
- Tests: `just test` (nose2, 444 tests) passing. Heritage sktsearch now resolves via canonical path; suite passes.
- Health probes landed: new `src/langnet/health.py` provides real probes (Diogenes parse ping, Heritage sktsearch HTTP with fallback path, spaCy/CLTK import checks, Whitaker’s binary, CDSL DB presence, cache placeholder). ASGI `/api/health` now reports degraded states instead of blanket “healthy,” and the tool endpoint indentation bug is fixed.
- Fuzz: `just fuzz-query` passes against running server; artifacts in `examples/debug/fuzz_results_query/` for content spot-checks (sources populated for all targets).
- Adapter split: `src/langnet/backend_adapter.py` decomposed into per-backend modules under `src/langnet/adapters/`; registry composes per language; adapters now emit full universal-schema objects (definitions, morphology, dictionary blocks) with sources `diogenes`, `whitakers`, `cltk|spacy`, `heritage`, `cdsl`. Full suite now green.

## In flight / remaining
- Health checks follow-through: document expected degraded states, keep CLI verify aligned, and wire real cache stats once a cache exists. Heritage `sktsearch` now defaults to `/cgi-bin/sktsearch` to avoid 404s; keep alternate paths as fallback and document the canonical one.
- Validation: thread shared validation into remaining CLI/adapter paths and remove bespoke checks; keep fuzz harness on when touching adapters.
- Normalization follow-ups: deduplicate remaining encoding/transliteration helpers with `heritage.encoding_service`; tighten heuristics in the new normalizer.
- Test hygiene: clean `__pycache__`, mark integration tests, and add a “fast” target; integrate fuzz targets into workflow without committing artifacts. ✅ Integration tests now carry `integration=True`; `just test-fast` runs without them.
- Fuzz spot-check: `just fuzz-query` failed because the API server was not running; artifacts saved under `examples/debug/fuzz_results_query/`. Rerun with the server up to assess pedagogical richness.

## Quick pick-up pointers
- Use `devenv shell langnet-cli -- <cmd>`; preferred tests: `just test` (full), add a fast subset once defined.
- When touching adapters/normalizer, run fuzz harness (`just fuzz-tools` / `just fuzz-query`) if available and diff outputs.
- Keep docs in sync: update plan and review docs as phases land; record fixture updates.
