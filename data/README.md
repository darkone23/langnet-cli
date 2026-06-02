# Data Layout

- `build/`: long-running, reproducible artifacts (e.g., `cts_urn.duckdb`, `cdsl_*.duckdb`). These can be large and slow to regenerate; build via `just cli-databuild ...`.
- `build/reader/catalog.duckdb`: global reader corpus index for local text enumeration, aliases, and artifact routing.
- `build/reader/`: generated reader catalog, book DuckDBs, and derived reader data.
- `build/reader/books/`: per-book DuckDB files used for direct segment lookup.
- `build/reader/search.lance`: derived Lance text-search index for `reader search`.
  This can be large; see `docs/technical/reader-full-text-search.md` for
  disk-footprint checks and safe rebuild/cleanup policy.
- `cache/`: ephemeral runtime caches safe to delete (e.g., `langnet.duckdb` normalization/plan cache, scratch files). Recreated automatically.
- `curated/reader_aliases/`: small editable alias files for explicit work abbreviations and title aliases.
- `curated/reader_metadata/`: evidence-backed display metadata overlays.
- `curated/reader_attributions/`: evidence-backed attribution claims that remain queryable without necessarily changing display author.
- `curated/reader_contained_works/`: accepted contained-work definitions, such as embedded works inside larger corpora.
- `curated/reader_work_maps/`: curated table-of-contents/work-map data.
- `curated/reader_citation_maps/`: source/work-specific maps from softer scholarly or dictionary citation conventions to local machine citation shapes.
- `generated/reader_classifications/`: generated-but-reviewed CSV inputs for restoring reader shelves, popular lists, discovery facets, and author prominence after catalog rebuilds.
- `generated/motd_pool/`: generated-but-reviewed word-of-day pool JSON snapshots for restoring the ignored `build/motd_pool.duckdb` runtime artifact.

Environment override: set `LANGNET_DATA_DIR` to change the root `data/` location; `build/` and `cache/` are created beneath it.

Suggested commands:
- `just cli-databuild cts --help` → inspect CTS build options; default output is under `data/build/`.
- `just cli-databuild cdsl --help` → inspect CDSL build options; default output is under `data/build/`.
- `just cli-databuild reader --help` → inspect reader build options.
- `just cli-databuild reader --perseus-dir ~/perseus --digiliblt-dir ~/Classics-Data/digiliblt --phi-latin-dir ~/Classics-Data/phi-latin --tlg-e-dir ~/Classics-Data/tlg_e --sanskrit-dir ~/Classics-Data/sanskrit` → builds local reader artifacts.
- `just reader-restore-generated-metadata data/build/reader/catalog.duckdb` → restores tracked generated reader classification metadata into a rebuilt reader catalog.
- `just cli reader collections`, `authors`, `works`, and `contents` → enumerate imported reader sources.
- `just cli reader show <address>` → retrieve one segment by CTS URN or registered address.
- `just cli reader resolve-address "Od. 3.74"` → resolve an alias/citation address and retrieve the segment when indexed.
- `just cli reader validate` → validate the reader catalog and per-book artifacts.
- `just cli motd-pool restore --path data/generated/motd_pool/2026-06-02/motd-pool-reviewed.json --output json` → restore the reviewed word-of-day pool into `data/build/motd_pool.duckdb`.
- `just clean-cache` → removes `data/cache/` contents.

Reader handoff docs:
- `docs/READER_CORPUS_STATUS.md` → current corpus status, metadata policy, verified catalogs, and next checkpoints.
- `docs/READER_CLI_BEGINNER_GUIDE.md` → beginner-facing commands for discovering and reading texts.
- `docs/READER_DATA_BUILD.md` → canonical reader build, sync, search-index, and validation guide.
