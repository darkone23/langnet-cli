# Reader Web Contract

Date: 2026-05-14

This document marks the reader CLI JSON fields intended for downstream web UI
use. The reader reads local DuckDB catalogs of cleaned corpus data; it does not
fetch external text at read time.

Use `--output json` for all integration calls.

## Catalog Selection

The web app should choose a catalog explicitly.

Supported contract:

- `--catalog <catalog.duckdb>` on every `reader` command;
- or `LANGNET_READER_CATALOG=<catalog.duckdb>`;
- or `reader catalogs --output json` to discover candidate catalogs.

Do not assume `data/build/reader/catalog.duckdb` is non-empty in every checkout.

Stable `reader catalogs` fields:

- `schema_version`
- `mode`
- `items[].id`
- `items[].label`
- `items[].path`
- `items[].exists`
- `items[].work_count`
- `items[].segment_count`
- `items[].languages`
- `items[].readiness`

## Works

```bash
just cli reader --catalog $CATALOG works \
  --language grc --query homer --limit 50 --cursor 0 --output json
```

Stable fields:

- `items[].work_id`
- `items[].collection_id`
- `items[].language`
- `items[].title`
- `items[].author`
- `items[].author_id`
- `items[].source_id`
- `items[].cts_work_urn`
- `items[].work_kind`
- `items[].parent_work_id`
- `items[].start_citation`
- `items[].end_citation`
- `pagination.next_cursor`
- `pagination.prev_cursor`
- `pagination.limit`

Supported filters: `--language`, `--collection`, `--author`, `--author-id`,
`--attributed-to`, `--query`, `--limit`, and `--cursor`.

`--query` searches title, author, work id, source id, CTS work URN, and catalog
aliases where available.

Use `--author-id` with the selector from `reader authors` to retrieve all works
for a selected author without relying on free-text matching.

Contained works, such as the `Bhagavadgītā` inside the `Mahābhārata`, are
returned with `work_kind = "contained"` and can be passed to `reader contents`
or `reader show` like any other exact work reference.

## Authors

```bash
just cli reader --catalog $CATALOG authors \
  --language san --query kalidasa --limit 50 --cursor 0 --output json
just cli reader --catalog $CATALOG authors \
  --language san --section क --limit 50 --cursor 0 --output json
```

Stable fields:

- `items[].author_id`
- `items[].source_author_id`
- `items[].display_name`
- `items[].index_name`
- `items[].native_name`
- `items[].section_key`
- `items[].author`
- `items[].language`
- `items[].work_count`
- `items[].alternate_names`
- `items[].sort_key`
- `pagination.next_cursor`
- `pagination.prev_cursor`
- `pagination.limit`

`Unknown`, `Anonymous`, and `Pseudo-*` are metadata states, not UI errors. The
web UI may choose to group or explain them, but should not silently discard
them.

`author_id` is the selector to pass back to `reader works --author-id`. When a
source authority ID is available, `source_author_id` preserves it. When a corpus
has only a display name, the selector is a stable synthetic
`langnet:reader:author:<language>:<slug>` value.

When a display author name maps to multiple source authorities, the reader may
append a disambiguation suffix to `display_name` and `author`, such as
`Georgius (Acropolites)`, `Plato (Phil.)`, `Plato (Comic.)`, or
`Pausanias (Perieg.)`. Research-backed accepted overlays may also canonicalize
the display itself, such as `Philoxenus Cytherius`. Clients should use
`author_id`, not display text, as the stable selector.

## Corpus QA Exports

```bash
just cli reader --catalog $CATALOG duplicate-audit \
  --kind authors --language grc --limit 100 --output json

just cli reader --catalog $CATALOG classification-export \
  --language grc --path examples/debug/reader-classification-export.csv
```

`duplicate-audit --kind authors` reports display-author names that map to more
than one authority id. It does not report a single author simply because that
author has many works.

`classification-export` emits one CSV row per work with stable identifiers and
blank enrichment columns for bulk classification, including
`classification_category`, `classification_period`,
`classification_date_range`, `classification_authorship_status`,
`classification_popularity_score`, and `classification_notes`.

## Author Sections

```bash
just cli reader --catalog $CATALOG author-sections --language lat --output json
just cli reader --catalog $CATALOG author-sections --language grc --output json
just cli reader --catalog $CATALOG author-sections --language san --output json
```

Stable fields:

- `items[].key`
- `items[].label`
- `items[].native_label`
- `items[].sort_key`
- `items[].author_count`
- `items[].work_count`

Section rules are language-specific:

- Latin uses A-Z and ignores abbreviated Roman praenomina for placement, so
  `P. Vergilius Maro (Virgil)` indexes under `V`.
- Greek uses Greek section keys in Greek alphabet order. For Latinized Greek
  authority names, sectioning is best-effort.
- Sanskrit uses Devanagari section keys in Sanskrit pedagogical order when
  romanized names can be transliterated.

## Work Lookup

```bash
just cli reader --catalog $CATALOG work urn:cts:greekLit:tlg0012.tlg002 --output json
```

Stable fields:

- `item.work_id`
- `item.collection_id`
- `item.language`
- `item.title`
- `item.author`
- `item.author_id`
- `item.source_id`
- `item.cts_work_urn`

The work reference may be a `work_id`, `cts_work_urn`, or catalog alias.

## Contents

```bash
just cli reader --catalog $CATALOG contents <work-ref> --limit 50 --cursor 0 --output json
just cli reader --catalog $CATALOG contents <work-ref> --from 3.74 --limit 50 --output json
just cli reader --catalog $CATALOG contents <work-ref> --around 3.74 --radius 20 --output json
```

Stable fields:

- `items[].segment_id`
- `items[].work_id`
- `items[].edition_id`
- `items[].segment_kind`
- `items[].citation_path`
- `items[].text`
- `items[].normalized_text`
- `items[].sort_key`
- `items[].language`
- `items[].display`
- `items[].available_layers`
- `window.anchor`
- `window.before_count`
- `window.after_count`
- `pagination.next_cursor`
- `pagination.prev_cursor`
- `pagination.limit`

`text` remains the stored source text. Display layers are additive.

Sanskrit segment display fields:

- `display.primary`: preferred learner display, Devanagari when conversion is
  available;
- `display.transliteration`: the stored roman/IAST-style text;
- `display.script`: the primary display script;
- `display.native_script`: Devanagari when conversion is available;
- `available_layers`: includes `transliteration` and, when available,
  `devanagari`.

## Show

```bash
just cli reader --catalog $CATALOG show <work-ref> --segment <citation> --output json
just cli reader --catalog $CATALOG show <full-segment-address> --output json
```

Stable fields:

- `segment`: same segment contract as `contents`;
- `navigation.previous.citation_path`
- `navigation.previous.address`
- `navigation.next.citation_path`
- `navigation.next.address`

Navigation addresses prefer the work's CTS work URN when present, falling back
to the catalog `work_id`.

## Resolve Address

```bash
just cli reader --catalog $CATALOG resolve-address "Od. 3.74" --output json
```

Stable fields:

- `address`
- `resolved_address`
- `segment`

Friendly shorthand is useful when aliases exist, but canonical `work_id`,
`cts_work_urn`, `contents`, and exact `show` calls are the primary web contract.

## Metadata And Provenance Commands

The following JSON commands are stable for operator or advanced metadata UI:

- `summary`
- `collections`
- `aliases`
- `attributions`
- `overlays`
- `validate`

Fields containing local filesystem paths, including `catalog_path`,
`artifact.artifact_path`, and source paths, are diagnostic. Do not expose them
as learner-facing durable identifiers.
