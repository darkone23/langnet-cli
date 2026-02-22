# Tool Executor → Claims → Semantic Reduction: Integration Notes

This stitches together the active plans:
- `docs/plans/active/infra/tool-plan-execution-to-claims.md` (staged executor)
- `docs/plans/active/semantic-reduction/semantic-reduction-handoff-checklist.md`
- `docs/plans/active/dictionary-entry-parsing-handoff.md`

## Current State (what’s implemented)
- Staged executor scaffold with cache reuse and logging (`src/langnet/execution/executor.py`), effect dataclasses, and DuckDB tables for extractions/derivations/claims.
- Stub handlers available (`ToolRegistry.with_stubs`, `src/langnet/execution/handlers_stub.py`) to unblock execution until real handlers land.
- Data layout split: heavy builds in `data/build`, caches in `data/cache`; `just clean-cache` wipes caches.
- CTS builder includes Packard PHI/TLG authtab/idt by default; CDSL builder streams rows; sample MW/AP90 builds succeed with `--limit`.

## Gaps to Close (ordered)
1) **Tool handlers**: Implement real `extract/derive/claim` for planned tools using generated protos (`langnet_spec`, `diogenes_spec`, `heritage_spec`, `cdsl_spec`, `whitakers_spec`). Reuse parsers from `codesketch/src/langnet/*` (heritage parsers, diogenes scraper, Whitaker line reducers, CDSL XML parsing). Keep stubs as fallback for missing assets (e.g., when CDSL DBs are absent).
2) **Registry wiring**: Central registry mapping tool names → handlers; integrate with `execute_plan_staged`. Add handler versioning to memo keys to avoid stale caches.
3) **Node-level memoization**: Hash per call/node (payload + handler version) so stages short-circuit without re-fetching. Plan-level cache exists; extend to stage caches.
4) **Claims shape**: Finalize subject/predicate/value per tool; include source_ref/domains/register; keep provenance chain intact.
5) **CLI + UX**: Add `langnet-cli plan-exec` and `effects show` commands; surface cache hits, durations, and claim counts. Document cache locations and `just clean-cache`.
6) **Tests**: Fixture-backed executor tests per language with stubs/mocks (no network). Add regression for deterministic IDs and memo hits. Include small sample CDSL/CTS fixtures (since full DBs are large).

## Interlocks with Semantic Reduction
- Claims produced here become WSUs for semantic reduction. Ensure claims include clean gloss/citation separation (see dictionary parsing plan) so reducers don’t ingest grammar noise.
- Need WSU extraction rules aligned with dictionary parsing outputs: senses/citations as WSUs, grammatical metadata stays in metadata.
- Evidence/provenance required by semantic reduction; keep provenance_chain populated from raw→extraction→derivation→claim.

## Interlocks with Dictionary Entry Parsing
- Use cleaned parsers (CDSL/Diogenes/CLTK Lewis) from `dictionary-entry-parsing` plan inside derive/claim handlers to avoid “gloss + citation mashed” issues.
- If handlers are stubbed due to missing assets (e.g., no CDSL DB), emit placeholder claims with a clear `stub` flag to avoid polluting semantic reducers.

## Immediate Next Steps
1. Stand up a handler registry module, wire stubs as default, and add a CLI flag to choose stubs vs real handlers.
2. Implement one end-to-end path with real handlers (e.g., Diogenes parse: fetch→extract HTML→derive morph facts→claim has_form/has_citation) using `diogenes_spec`.
3. Add minimal fixtures for executor tests (mock HTTP/subprocess/file clients) to validate deterministic IDs, cache reuse, and claim shape.
4. Update `docs/technical/design/tool-response-pipeline.md` with executor/registry usage and cache locations.

## Useful Commands
- Clear caches: `just clean-cache` (removes `data/cache`).
- Sample CDSL build (fast): `just cli databuild cdsl MW --limit 1000 --batch-size 500`.
- Sample CTS build with Packard: `just cli databuild cts --max-works 1` (shows authtab/idt logs).
