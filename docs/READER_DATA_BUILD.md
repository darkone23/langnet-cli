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

The reader builder collates these local inputs:

- `--phi-latin-dir`: PHI `.txt` legacy dumps, plus sibling `.idt` files when
  present, and legacy source metadata files loaded by the PHI metadata adapter.
- `--tlg-e-dir`: TLG `.txt` legacy dumps, sibling `.idt` files when present,
  and `cd.authors.php`/`doccan*.txt` author metadata files.
- `--perseus-dir`: Perseus TEI `.xml` text files discovered recursively.
- `--digiliblt-dir`: digilibLT TEI `.xml` files in the root directory.
- `--sanskrit-dir`: Sanskrit `.json` corpus files, plain `.txt` files,
  grouped split plain-text chunks, DCS `.conllu`/`.conllu_parsed` files, and
  DCS enrichment tables such as `chapter-info.xml` and corpus-table XML.

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

## Rebuild One Input Source

Use a source-slice rebuild when one input file has changed or when an importer
bug only affects a small source family. This updates the selected source's
catalog rows and rewrites its per-book DuckDB artifact without wiping the rest
of the catalog.

Rules for this pattern:

- Keep the relevant root flag, such as `--sanskrit-dir`, in the command. The
  `--source-path` flag selects files inside the normal source root; it does not
  replace the source root.
- Always pair `--source-path` with `--no-wipe --force` when repairing an
  existing catalog. Without `--no-wipe`, the command creates a new partial
  catalog containing only the selected source slice.
- Pass `--source-path` more than once when a logical work is represented by
  multiple files, such as grouped split plain-text chunks or DCS chapter groups.
- Rebuild all affected source files after parser behavior changes. A
  source-slice rebuild is appropriate for stale per-book artifacts, duplicate
  work repair, and one-source metadata refreshes; a full rebuild is still the
  safer handoff path after broad adapter or catalog-schema changes.

```bash
just cli-databuild reader \
  --sanskrit-dir /home/nixos/Classics-Data/sanskrit/corpus \
  --output-root examples/debug/reader_full_curated_current \
  --source-path /home/nixos/Classics-Data/sanskrit/corpus/GRETIL/sa_aSTasAhasrikA-prajJApAramitA.txt \
  --no-wipe \
  --force
```

This pattern is required when parser behavior changes. Do not try to fix stale
reader artifacts by filtering UI rows: citation paths and navigation are stored
inside each book DuckDB. If a stale artifact has `#Text` stored as citation
`1`, hiding that row still leaves references wrong. Rebuild the source slice so
the first reading line is stored as citation `1`.

For paired Sanskrit GRETIL sources, the reader build treats
`GRETIL/<stem>.txt` as the reader-facing work and `GRETIL/corpus/<stem>.json`
as a duplicate/derived tokenized representation. Whenever the builder has the
Sanskrit root, it removes stale paired `sanskrit_json` reader works for all
known GRETIL TXT works already present in the catalog. That cleanup is part of
the build/repair path, not a query-time display filter. If duplicates still
appear in `reader works`, treat the catalog as stale and run a source-slice
repair.

For Greek and Latin CTS works, the reader build treats same-language Perseus
TEI as the reader-facing canonical source when it overlaps a legacy TLG or PHI
row with the same `cts_work_urn`. The cleanup deletes the superseded `tlg` or
`phi` catalog row during build/repair. It intentionally requires a language
match, so an English Perseus translation does not remove the Greek or Latin
legacy original when no same-language Perseus text is present.

The TXT header lines remain available as `source_metadata` values such as
`gretil_text`, `gretil_author`, `gretil_edition`, `gretil_notes`, and
`gretil_comments`, but they are not stored as reader segments.

The catalog delete step removes stale rows for superseded duplicate works. It
does not currently delete the old orphaned per-book artifact file from disk.
That file is harmless because the catalog no longer references it, but disk
maintenance can remove orphaned artifacts separately if space becomes tight.

After a source-slice rebuild, smoke test both the work list and the first
contents rows:

```bash
export CATALOG=examples/debug/reader_full_curated_current/catalog.duckdb

just cli reader --catalog $CATALOG works \
  --language san \
  --query 'Aṣṭasāhasrikā' \
  --output json

just cli reader --catalog $CATALOG contents \
  'langnet:reader:sanskrit_texts:GRETIL_sa_aSTasAhasrikA-prajJApAramitA' \
  --limit 5 \
  --output json
```

Expected result: the paired `sanskrit_json` GRETIL work is absent from the
catalog-backed work listing because it has been deleted from the catalog, and
citation `1` is the first reading line, not a GRETIL header line.

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
