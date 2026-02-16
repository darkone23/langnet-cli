# Offline Indexing Reintroduction Plan

## Goals
- Restore offline index builds (CDSL XML → DuckDB, Perseus/Packard → CTS URN DuckDB) inside the V2 codebase.
- Provide a consistent CLI entry (`just cli databuild <module> ...`) to run builders with sensible defaults and config flags.
- Align outputs with repo-local data storage (`data/*.duckdb` by default, override via env/flag) and document operational expectations for education users.

## Scope
- In scope: port or rewrite indexer code from `codesketch/src/langnet/indexer/*`, unify config/paths, minimal smoke tests, CLI wiring, and docs.
- Out of scope: new data sources, major schema redesigns, or production automation (cron/k8s jobs) beyond a CLI runner.

## Current Assets
- Reference builders in `codesketch/src/langnet/indexer/cts_urn_indexer.py` (functional) and `cdsl_indexer.py` (stub; known slow path).
- Old CLI scaffolding at `codesketch/src/langnet/indexer/cli.py` plus `core.py`/`utils.py` for IndexManager/IndexType/IndexStatus.
- Data assumptions (defaults to preserve): Perseus corpus under `~/perseus` (latinLit/greekLit); Packard/legacy supplements under `~/Classics-Data` (auto-include when present, no opt-in); CDSL XML dictionaries under `~/cdsl_data`; DuckDB outputs live in repo `data/` unless overridden.

## Phased Plan
- Phase 0 — Design/API shape (@architect): confirm target package location (`src/langnet/databuild/`), data paths, DuckDB schema contracts, and error/reporting style. Decide whether to keep IndexManager abstraction or replace with a simpler registry under `storage/`.
- Phase 1 — CTS URN builder port (@coder, @sleuth): lift `CtsUrnIndexer` into V2 module, align DuckDB schema with planned contract, add batch/config flags (perseus_dir, legacy_dir, wipe, force). Add smoke test over tiny fixture to assert row counts and language mapping.
- Phase 2 — CDSL builder implementation (@coder, @sleuth): implement XML→DuckDB pipeline using existing `src/langnet/cologne` parsing helpers; support dictionary selection, batching, and progress logging. Default source `~/cdsl_data`; add fixture-driven test validating headword count and key columns; instrument for known slowness (chunking + progress).
- Phase 3 — CLI + just wiring (@coder, @scribe): expose `langnet/cli.py` group `databuild` with subcommands `cts` and `cdsl` (common flags: `--output`, `--wipe/--no-wipe`, `--force`, source-dir flags). Add `just cli databuild <module>` recipes and update README/GETTING_STARTED with usage, expected runtime, and data prerequisites. Default sources: `~/perseus`, `~/Classics-Data` included when present, `~/cdsl_data`; outputs default to repo `data/`.
- Phase 4 — QA & review (@auditor): run typecheck/lint/tests; verify DuckDB files created under `~/.local/share/langnet/tools/`; confirm help text and failure modes are user-friendly; review for regressions and storage collisions.

## Deliverables
- New databuild module(s) in `src/langnet/` with CTS and CDSL builders plus shared utilities (paths, logging, validation).
- CLI commands reachable via `langnet-cli databuild <module>` and `just cli databuild <module>`.
- Tests covering minimal build flows; updated docs for operators/educators on prerequisites and expected artifacts.

## Open Questions / Risks
- Do we keep IndexManager persistence (JSON config) or replace with a simpler “build and report path” flow?
- What is the canonical location for CDSL XML in V2 (keep `data/cologne` or rely on external download)? Need to avoid large fixtures in git.
- Should CTS builder continue to import legacy Packard supplements by default, or make this opt-in to reduce build time? → Decision: include when the files exist (default-on, auto-detect).
