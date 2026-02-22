# Tool Executor Progress & Next Steps

## Summary of Recent Work
- Added staged effect data classes (`ExtractionEffect`, `DerivationEffect`, `ClaimEffect`) with stable IDs/provenance (`src/langnet/execution/effects.py`).
- Extended DuckDB schema and indices for derivations/claims; extraction index now stores durations and accepts effect inserts (`src/langnet/storage/schemas/langnet.sql`, `extraction_index.py`, `derivation_index.py`, `claim_index.py`).
- Implemented staged executor with registry dispatch, cache reuse via `PlanResponseIndex`, and INFO logging per stage (`src/langnet/execution/executor.py`).
- CLI build result printing fixed for `returns.result` Success/Failure.
- Data layout split into `data/build` (heavy) and `data/cache` (ephemeral), with `just clean-cache`.
- CTS builder now ingests Packard PHI/TLG authtab/idt by default; logging shows every file opened (`src/langnet/databuild/cts.py`).
- CDSL builder now streams rows (no full fetchall), logs batch timings, and sample builds succeed (`just cli databuild cdsl MW/AP90 --limit 1000`).

## What Remains for Tool Executor
- **Tool handlers**: Implement `extract.*`, `derive.*`, `claim.*` for planned tools using generated protos (`langnet_spec`, `diogenes_spec`, `heritage_spec`, `cdsl_spec`, `whitakers_spec`). Reuse parsing logic from `codesketch` (heritage parsers, diogenes scraper, Whitaker line reducers, CDSL XML parsing).
- **Registry wiring**: Register handlers in a single place and plug into `execute_plan_staged`.
- **Node-level memoization**: Add deterministic hashes per node (call_id + payload) and short-circuit per stage (not just plan-level cache).
- **CLI**: Add `langnet-cli plan-exec` and `effects show` commands to run plan→execute→claim and inspect stored effects.
- **Tests**: Fixture-backed executor tests for fetch→extract→derive→claim across SAN/GRC/LAT with stubs; verify IDs/provenance and cache hits.
- **Docs**: Update `docs/technical/design/tool-response-pipeline.md` with executor/registry usage and data/cache layout.

## Pointers
- Plans: `docs/plans/active/infra/tool-plan-execution-to-claims.md` (phase details).
- Current executor code: `src/langnet/execution/executor.py` (logging enabled).
- Storage schema: `src/langnet/storage/schemas/langnet.sql` (derivation_index, claims).
- Generated protos: `vendor/langnet-spec/generated/python/*` (`import langnet_spec`, etc.); regenerated via `just codegen`.
- Legacy parsing examples: `codesketch/src/langnet/engine/core.py` and `codesketch/src/langnet/heritage/*`, `.../diogenes/*`, `.../whitakers/*`.

## Open Questions / Decisions
- Claim schema shape: finalize subject/predicate/value/provenance flattening per tool.
- How to store handler versioning for memo keys (include parser version?).
- Whether to gate raw-response persistence via flag in executor (currently always stores when running).

## Temporary Stubs
- `src/langnet/execution/handlers_stub.py` has fallback extract/derive/claim handlers emitting placeholder payloads to keep plan execution flowing until real tool handlers are wired.
