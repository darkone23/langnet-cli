# Tool Plan Execution → Claims: Handoff (2026-02-21)

## Current Implementation
- **Executor**: `src/langnet/execution/executor.py` runs ToolPlans with stage awareness (fetch/extract/derive/claim), plan hash caching, and INFO logging. Optional nodes skip gracefully when a client/handler is missing; dependents skip accordingly.
- **Effects/Storage**: Dataclasses for extraction/derivation/claim effects with stable IDs & provenance (`src/langnet/execution/effects.py`); DuckDB tables and indices for derivations/claims added (`langnet.sql`, `derivation_index.py`, `claim_index.py`, updated `extraction_index.py`).
- **Handlers**: Real Diogenes path only: `extract.diogenes.html` (lemma scrape), `derive.diogenes.morph` (carry lemmas), `claim.diogenes.morph` (`has_lemmas`). All other tools fall back to stubs (`src/langnet/execution/handlers_stub.py`). Registry with stubs in `src/langnet/execution/registry.py`.
- **CLI**: `plan-exec` command added to normalize → plan → execute → show counts and claims. Uses stub clients/handlers when real ones are unavailable. Example: `just cli plan-exec lat lupus --use-stub-handlers`.
- **Caching/Data layout**: `data/build` for heavy artifacts, `data/cache` for ephemeral caches. `just clean-cache` wipes cache. CTS build pulls Packard authtab/idt by default; CDSL build streams rows; sample MW/AP90 builds succeed with limits.
- **Tests**: `tests/test_execution_executor.py` covers executor flow, stub registry, and diogenes end-to-end claim creation.

## Gaps / Next Work
1) **Real handlers** (replace stubs):
   - Whitaker: fetch via subprocess; extract lines using existing parsers; derive facts; claim lex/morph facts.
   - Heritage: fetch HTML; extract morph tables; derive morph facts; claim forms. (Endpoint config from codesketch if needed.)
   - CLTK: fetch IPA/morph; derive; claim.
   - CDSL: blocked until DB available; then parse XML rows, derive sense facts, claim glosses/pos/gender/root with source_ref.
2) **Registry wiring**: Register all handlers centrally; keep stub fallback only when `--use-stub-handlers` is set. Consider handler versioning for memo keys.
3) **Memoization**: Add per-node hash/cache (payload + handler version) to short-circuit stages beyond raw fetch; current cache is plan-level for fetch responses.
4) **Claim schema**: Finalize subject/predicate/value per tool (include domains/register/source_ref) and ensure provenance_chain is populated.
5) **CLI UX**: Improve `plan-exec` output (skipped nodes, cache hits, claim details), and add `effects show` inspector. Remove include_* toggles; rely on optional nodes + stubs for missing tools.
6) **Tests/fixtures**: Add fixture-backed executor tests per language with mocked clients (no network), plus small CDSL/CTS samples for CI. Verify deterministic IDs and cache reuse.
7) **Docs**: Update `docs/technical/design/tool-response-pipeline.md` with registry/handler behavior, skipping semantics, cache layout, and new CLI commands. Keep `docs/handoff/tool-execution-integration.md` in sync.

## Endpoint Notes
- Diogenes parse default: `http://localhost:8888/Perseus.cgi` (planner builds `fetch.diogenes` calls).
- Heritage base default: `http://localhost:48080/cgi-bin/skt/sktreader` (configurable).
- Whitaker binary: `whitakers-words` / `words` on PATH; use SubprocessToolClient.
- CDSL DBs: `data/build/cdsl_<dict>.duckdb` (MW/AP90). AP90 is available; MW pending.

## Known Issues
- `plan-exec` currently produces stub claims for missing handlers/tools. Use `--no-stub-handlers` to fail when real handlers are absent.
- Lemma extraction for diogenes is minimal (HTML scrape); should be upgraded using richer parsers when available.

## Useful Commands
- Clear caches: `just clean-cache`
- Sample plan-exec: `just cli plan-exec lat lupus --use-stub-handlers --no-cache`
- Sample CDSL build (fast): `just cli databuild cdsl AP90 --limit 1000 --batch-size 500`
- Sample CTS build (small): `just cli databuild cts --max-works 1`
