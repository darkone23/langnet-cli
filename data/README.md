# Data Layout

- `build/`: long-running, reproducible artifacts (e.g., `cts_urn.duckdb`, `cdsl_*.duckdb`). These can be large and slow to regenerate; build via the `databuild` commands.
- `cache/`: ephemeral runtime caches safe to delete (e.g., `langnet.duckdb` normalization/plan cache, scratch files). Recreated automatically.

Environment override: set `LANGNET_DATA_DIR` to change the root `data/` location; `build/` and `cache/` are created beneath it.

Suggested commands:
- `just databuild cts ...` → writes to `data/build/cts_urn.duckdb` by default.
- `just databuild cdsl ...` → writes to `data/build/cdsl_<dict>.duckdb` by default.
- `just clean-cache` → removes `data/cache/` contents.
