> Completed implementation record. Moved out of active/ during the 2026-05 documentation overhaul after code/tests confirmed the core slice exists.

# CLI Concurrency Stabilization Plan

## Context

The web study desk runs overlapping CLI workflows:

- foreground `encounter` lookups,
- sidebar `word-index nearby` navigation,
- background `word-of-day` recommendations.

Foreground reader calls must remain stable even when background learning features are slow or write-capable. DuckDB contention must be explicit and machine-readable, not an unstructured traceback.

## Research Findings

- `word-index nearby` uses read-only DuckDB connections for index databases and is already shaped as a safe foreground/sidebar read path.
- `encounter --translation-mode cache` avoids translation writes, but normalization could still write on cache miss through the shared normalization cache.
- `--no-cache` is too blunt for the web foreground use case because it disables cache reads as well as writes.
- Translation `auto` and `populate` may legitimately write translation cache rows; these should remain explicit enrichment modes.
- Translation cache status was read-oriented but used a write-lock connection; status can safely use read-only DuckDB access.
- The `just cli` delegation path interpolated variadic arguments with `{{ args }}`. That is fragile for spaces/shell metacharacters and weakens confidence in concurrent subprocess argument isolation.

## Contract For This Iteration

| Command shape | Cache behavior | Foreground safe | Notes |
| --- | --- | --- | --- |
| `encounter --translation-mode cache --cache-policy read-only` | reads warmed normalization and translation cache only | yes | recommended web foreground profile |
| `encounter --translation-mode off --cache-policy read-only` | reads warmed normalization cache only | yes | no translation cache access |
| `encounter --translation-mode auto --cache-policy read-only` | normalization read-only; translation may write | conditional | use when enrichment delay is acceptable |
| `encounter --cache-policy read-write` | may write normalization cache | no strict read-only guarantee | CLI default for local use |
| `encounter --cache-policy off` or `--no-cache` | no normalization cache reads or writes | yes | slower, bypasses warmed cache |
| `word-index nearby` | read-only index lookup | yes | suitable for sidebar/navigation |
| `word-of-day` cached/curated probes | no shared normalization writer path | yes | generation may still be slow if LLM-backed |

## Implementation Checklist

- Add `--cache-policy` to `encounter` with `read-write`, `read-only`, and `off`.
- Include `cache_policy` in `encounter` JSON success and error `request` metadata.
- Include explicit `normalization_cache_writes` and `translation_cache_writes` booleans in `encounter` JSON request metadata.
- Make `read-only` normalization cache policy read warmed rows but skip cache upserts on misses.
- Preserve `--no-cache` as an alias for effective normalization cache policy `off`.
- Return structured JSON for DuckDB/file-lock contention:
  - `code=database_busy`
  - `kind=database_busy`
  - `retryable=true`
  - `retry_after_ms=1500`
  - `readonly_available=true`
- Use read-only DuckDB access for translation cache status.
- Use Just positional argument forwarding and `"$@"` for variadic CLI wrappers.
- Pass `--cache-policy read-only` from the web encounter adapter for foreground searches.
- Add regression tests for read-only cache misses and structured busy errors.
- Verify focused tests, lint, and the broader suite.

## Follow-Up Candidates

- Add a documented `word-of-day` cached-only command shape for the web background panel.
- Add a lightweight CLI concurrency harness under `examples/debug` for local stress testing.
- Consider a stable subprocess wrapper that bypasses nested `just` invocation for production web use.
