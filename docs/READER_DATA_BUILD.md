# Reader Data Build

The reader product target is one unified, source-agnostic catalog. A reader or
web client should be able to ask "what books do we have?" without knowing
whether a text came from PHI, TLG, Perseus, digilibLT, or Sanskrit/DCS.

The split catalogs under `examples/debug/` are audit artifacts. Keep them when
debugging an importer or validating a source family, but do not treat them as
the product catalog.

## Required Data

The build command does not download corpus data. Point it at local source roots
that already exist on the machine.

Useful source roots:

- PHI Latin text dump directory: `--phi-latin-dir /path/to/phi-latin`
- TLG Greek text dump directory: `--tlg-e-dir /path/to/tlg_e`
- Perseus corpus root or fixture directory: `--perseus-dir /path/to/perseus`
- digilibLT TEI corpus root: `--digiliblt-dir /path/to/digiliblt`
- Sanskrit/DCS JSON or plain-text corpus root: `--sanskrit-dir /path/to/sanskrit`

Curated repo data should be included in normal builds:

- aliases: `data/curated/reader_aliases`
- display metadata overlays: `data/curated/reader_metadata`
- attribution claims: `data/curated/reader_attributions`
- contained works: `data/curated/reader_contained_works`
- work maps/table-of-contents data: `data/curated/reader_work_maps`

The curated directories have CLI defaults, but pass them explicitly in handoff
commands so the build inputs are visible.

## Build The Unified Catalog

Default product-style output:

```bash
just cli-databuild reader \
  --phi-latin-dir /path/to/phi-latin \
  --tlg-e-dir /path/to/tlg_e \
  --perseus-dir /path/to/perseus \
  --digiliblt-dir /path/to/digiliblt \
  --sanskrit-dir /path/to/sanskrit \
  --metadata-overlay-dir data/curated/reader_metadata \
  --metadata-attribution-dir data/curated/reader_attributions \
  --alias-dir data/curated/reader_aliases \
  --contained-work-dir data/curated/reader_contained_works \
  --work-map-dir data/curated/reader_work_maps \
  --progress-every 100
```

This writes `data/build/reader/catalog.duckdb` by default.

Development output that is easy to compare with existing debug artifacts:

```bash
just cli-databuild reader \
  --phi-latin-dir /path/to/phi-latin \
  --tlg-e-dir /path/to/tlg_e \
  --perseus-dir /path/to/perseus \
  --digiliblt-dir /path/to/digiliblt \
  --sanskrit-dir /path/to/sanskrit \
  --metadata-overlay-dir data/curated/reader_metadata \
  --metadata-attribution-dir data/curated/reader_attributions \
  --alias-dir data/curated/reader_aliases \
  --contained-work-dir data/curated/reader_contained_works \
  --work-map-dir data/curated/reader_work_maps \
  --progress-every 100 \
  --output-root examples/debug/reader_full_curated_current
```

If a source root is unavailable, omit that flag and document the omission in
the build notes. The resulting catalog is still valid for the included sources,
but it is not the full product target.

After parser, importer, overlay, contained-work, or work-map changes, rebuild
the catalog. Applying selected overlay sync commands can be useful for quick
checks, but parser and importer behavior is baked into the generated book DBs.

## Rebuild The Search Index

The Lance search index is derived cache data. Rebuild it after every catalog
rebuild.

```bash
export CATALOG=data/build/reader/catalog.duckdb
export SEARCH_INDEX=data/build/reader/search.lance

just cli reader --catalog $CATALOG search-index build \
  --index $SEARCH_INDEX \
  --replace \
  --output json

just cli reader --catalog $CATALOG search-index validate \
  --index $SEARCH_INDEX \
  --output json
```

For language-scoped debugging, add `--language grc`, `--language lat`, or
`--language san` to the build command.

## Validate And Smoke Test

Run these against the exact catalog path being handed to a user or web app:

```bash
export CATALOG=data/build/reader/catalog.duckdb
export SEARCH_INDEX=data/build/reader/search.lance

just cli reader --catalog $CATALOG summary
just cli reader --catalog $CATALOG validate --output json
just cli reader --catalog $CATALOG coverage --output json
just cli reader --catalog $CATALOG contents urn:cts:greekLit:tlg0012.tlg002 --limit 5
just cli reader --catalog $CATALOG search-index validate \
  --index $SEARCH_INDEX \
  --output json
```

For a development unified catalog, set:

```bash
export CATALOG=examples/debug/reader_full_curated_current/catalog.duckdb
```

