# Data Layout

- `build/`: long-running, reproducible artifacts (e.g., `cts_urn.duckdb`, `cdsl_*.duckdb`). These can be large and slow to regenerate; build via the `databuild` commands.
- `build/reader/catalog.duckdb`: global reader corpus index for local text enumeration, aliases, and artifact routing.
- `build/reader/books/`: per-book DuckDB files used for direct segment lookup.
- `cache/`: ephemeral runtime caches safe to delete (e.g., `langnet.duckdb` normalization/plan cache, scratch files). Recreated automatically.
- `curated/reader_aliases/`: small editable alias files for explicit work abbreviations and title aliases.
- `curated/reader_metadata/`: evidence-backed display metadata overlays.
- `curated/reader_attributions/`: evidence-backed attribution claims that remain queryable without necessarily changing display author.

Environment override: set `LANGNET_DATA_DIR` to change the root `data/` location; `build/` and `cache/` are created beneath it.

Suggested commands:
- `just databuild cts ...` → writes to `data/build/cts_urn.duckdb` by default.
- `just databuild cdsl ...` → writes to `data/build/cdsl_<dict>.duckdb` by default.
- `just cli-databuild reader --perseus-dir ~/perseus --digiliblt-dir ~/Classics-Data/digiliblt --phi-latin-dir ~/Classics-Data/phi-latin --tlg-e-dir ~/Classics-Data/tlg_e --sanskrit-dir ~/Classics-Data/sanskrit` → builds local reader artifacts.
- `just cli reader collections`, `authors`, `works`, and `contents` → enumerate imported reader sources.
- `just cli reader show <address>` → retrieve one segment by CTS URN or registered address.
- `just cli reader resolve-address "Od. 3.74"` → resolve an alias/citation address and retrieve the segment when indexed.
- `just cli reader validate` → validate the reader catalog and per-book artifacts.
- `just clean-cache` → removes `data/cache/` contents.

Reader handoff docs:
- `docs/READER_CORPUS_STATUS.md` → current corpus status, metadata policy, verified catalogs, and next checkpoints.
- `docs/READER_CLI_BEGINNER_GUIDE.md` → beginner-facing commands for discovering and reading texts.
