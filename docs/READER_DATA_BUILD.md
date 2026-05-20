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
- First1KGreek TEI corpus root: `--first1k-greek-dir /path/to/First1KGreek`
- digilibLT TEI corpus root: `--digiliblt-dir /path/to/digiliblt`
- Sanskrit/DCS JSON or plain-text corpus root: `--sanskrit-dir /path/to/sanskrit`

The reader builder collates these local inputs:

- `--phi-latin-dir`: PHI `.txt` legacy dumps, plus sibling `.idt` files when
  present, and legacy source metadata files loaded by the PHI metadata adapter.
- `--tlg-e-dir`: TLG `.txt` legacy dumps, sibling `.idt` files when present,
  and `cd.authors.php`/`doccan*.txt` author metadata files.
- `--perseus-dir`: Perseus TEI `.xml` text files discovered recursively.
- `--first1k-greek-dir`: First1KGreek TEI `.xml` text files discovered
  recursively. When the same CTS work is available from Perseus/First1K and a
  legacy TLG row, the curated build prefers the TEI source and deletes the
  superseded legacy catalog row.
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
  --first1k-greek-dir /path/to/First1KGreek \
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
  --first1k-greek-dir /path/to/First1KGreek \
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

## Restore Generated Discovery Metadata

Generated work and author classifications are catalog metadata used by
`reader shelves`, `reader popular`, discovery facets, and prominence-sorted
author views. A full `cli-databuild reader` rebuild creates the base catalog
and book artifacts, but it does not regenerate LLM classification CSVs. Restore
the current generated metadata layer before declaring shelves or discovery
surfaces ready.

Use replace mode for the first full-language file, then `--merge` for the
remaining language files and small correction layers:

```bash
export CATALOG=data/build/reader/catalog.duckdb

just cli reader --catalog $CATALOG sync-classifications \
  --classification-csv examples/debug/reader-full-classification-2026-05-16/discovery/greek-generated-discovery-b50.csv \
  --output json
just cli reader --catalog $CATALOG sync-classifications \
  --classification-csv examples/debug/reader-full-classification-2026-05-16/discovery/latin-generated-discovery-b50.csv \
  --merge \
  --output json
just cli reader --catalog $CATALOG sync-classifications \
  --classification-csv examples/debug/reader-full-classification-2026-05-16/discovery/sanskrit-generated-discovery.csv \
  --merge \
  --output json
just cli reader --catalog $CATALOG sync-classifications \
  --classification-csv examples/debug/reader-full-classification-2026-05-16/discovery/audit-corrections-2026-05-17.csv \
  --merge \
  --output json
just cli reader --catalog $CATALOG prune-stale-classifications --output json

just cli reader --catalog $CATALOG sync-author-classifications \
  --classification-csv examples/debug/reader-full-classification-2026-05-16/authors/full/grc-author-full-generated-v2-b10.csv \
  --output json
just cli reader --catalog $CATALOG sync-author-classifications \
  --classification-csv examples/debug/reader-full-classification-2026-05-16/authors/full/lat-author-full-generated-v2.csv \
  --merge \
  --output json
just cli reader --catalog $CATALOG sync-author-classifications \
  --classification-csv examples/debug/reader-full-classification-2026-05-16/authors/full/san-author-full-generated-merged-b10.csv \
  --merge \
  --output json
```

The sync commands only insert generated rows whose work or author is present in
the current catalog. Work sync resolves generated rows through the catalog's
`work_id`, `source_id`, and `cts_work_urn` aliases, so a legacy row such as
`langnet:reader:tlg:tlg0059.030` still attaches to the current
`urn:cts:greekLit:tlg0059.tlg030` work after TEI source preference. Author sync
accepts compact-equivalent source ids, such as `tlg0059` matching
`urn:cts:greekLit:tlg0059`, and synthetic display-author selectors for sources
that do not carry stable author ids. This is important after dedupe or
source-preference changes: stale classifier rows from older builds must not
survive as orphan metadata, but equivalent legacy/CTS work and author ids must
still keep their generated metadata. `prune-stale-classifications` additionally
removes generated work rows imported from the wrong language batch.

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
- Incremental registration replaces stale same-work catalog rows, editions,
  artifacts, source witnesses, and generated aliases. It must not globally wipe
  aliases or leave old same-work artifacts referenced in the catalog.
- Rebuild all affected source files after parser behavior changes. A
  source-slice rebuild is appropriate for stale per-book artifacts, duplicate
  work repair, and one-source metadata refreshes; a full rebuild is still the
  safer handoff path after broad adapter or catalog-schema changes.
- Rebuild the derived search index after any source-slice repair that changes
  visible text, segment counts, titles, canonical addresses, or aliases.

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

First1KGreek is imported with `--first1k-greek-dir` as collection
`first1kgreek`. Its TEI files are parsed from `data/**/*.xml`, excluding
`__cts__.xml`, and only Greek text editions are registered. When First1KGreek
has multiple Greek edition files for the same CTS work directory, the default
full build chooses one preferred edition deterministically, with `grc1`
preferred over later same-work editions. First1KGreek source URNs are preserved
as aliases and `source_witnesses`; they are not treated as LangNet canonical
identity. When a First1KGreek text overlaps a legacy TLG row by exact
same-language CTS work URN or canonical CTSv2 text id, the lower priority
legacy row is removed from the visible catalog during build.

New builds also mint a public `canonical_text_id` for visible works using the
LangNet CTSv2 shape `urn:ctsv2:<language>:<title>-<incipit>`. Existing
`work_id`, `cts_work_urn`, TLG/PHI ids, and source URNs remain accepted as AKA
names/aliases, but downstream links should prefer `canonical_text_id` and
segment `canonical_address` when present.

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
just cli reader --catalog $CATALOG shelves --language san --limit 12 --sample-limit 2 --output json
just cli reader --catalog $CATALOG shelves --language grc --limit 12 --sample-limit 2 --output json
just cli reader --catalog $CATALOG shelves --language lat --limit 12 --sample-limit 2 --output json
just cli reader --catalog $CATALOG contents urn:cts:greekLit:tlg0012.tlg002 --limit 5
just cli reader --catalog $CATALOG search-index validate \
  --index $SEARCH_INDEX \
  --output json
```

For a development unified catalog, set:

```bash
export CATALOG=examples/debug/reader_full_curated_current/catalog.duckdb
```
