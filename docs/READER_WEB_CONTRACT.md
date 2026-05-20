# Reader Web Contract

Date: 2026-05-14

This document marks the reader CLI JSON fields intended for downstream web UI
use. The reader reads local DuckDB catalogs of cleaned corpus data; it does not
fetch external text at read time.

Use `--output json` for all integration calls.

The SvelteKit API keeps JSON compatibility by default. Browser clients in this
repo send `Accept: application/msgpack, application/json`; endpoints return
MessagePack only when that header explicitly includes `application/msgpack`.
External consumers that do not opt in continue to receive JSON.

## Catalog Selection

The web app should choose a catalog explicitly.

The intended product catalog is unified across source families:
`data/build/reader/catalog.duckdb` for the default build, or
`examples/debug/reader_full_curated_current/catalog.duckdb` for a local
development build. Source-split catalogs such as classics, Sanskrit, Perseus,
or digilibLT are audit/debug artifacts and should not be presented as separate
product catalogs unless the UI is explicitly in an operator-debug mode.

Supported contract:

- `--catalog <catalog.duckdb>` on every `reader` command;
- or `LANGNET_READER_CATALOG=<catalog.duckdb>`;
- or `reader catalogs --output json` to discover candidate catalogs.

Do not assume `data/build/reader/catalog.duckdb` is non-empty in every checkout.
It exists only after the reader data build has been run against local source
roots. Build requirements and commands are documented in
`docs/READER_DATA_BUILD.md`.

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
- `items[].canonical_text_id`
- `items[].canonical_address`
- `items[].work_kind`
- `items[].parent_work_id`
- `items[].start_citation`
- `items[].end_citation`
- `items[].word_count`
- `items[].word_count_method`
- `items[].metadata_attributions`
- `items[].translator_names`
- `items[].traditional_author_names`
- `items[].attributed_author_names`
- `pagination.next_cursor`
- `pagination.prev_cursor`
- `pagination.limit`

Supported filters: `--language`, `--collection`, `--author`, `--author-id`,
`--attributed-to`, `--query`, `--limit`, and `--cursor`.

`--query` searches title, author, work id, source id, CTS work URN, and catalog
aliases where available.

Use `--author-id` with the selector from `reader authors` to retrieve all works
for a selected author without relying on free-text matching.

Use `--attributed-to` when the user searches for a responsible name that may be
recorded as an attribution claim rather than the public display author, such as
Jerome as Vulgate translator or the traditional seventy-two Septuagint
translators. Work rows expose the matched didactic names as structured
`metadata_attributions` and as convenience arrays for common relation types.

Contained works, such as the `Bhagavadgītā` inside the `Mahābhārata`, are
returned with `work_kind = "contained"` and can be passed to `reader contents`
or `reader show` like any other exact work reference.

`reader contents` also accepts `--char-budget` for reader-page windows. Clients
should use it when rendering a composed page rather than a raw table of
contents: the response keeps at least one segment and trims neighboring
segments when a work is segmented by long chapters instead of short lines.

## Text Search

Reader text search is backed by a derived Lance dataset built and queried
through DuckDB's `lance` extension. Clients should treat it as rebuildable cache
data, not canonical corpus storage.

Build/status/validate:

```bash
just cli reader --catalog $CATALOG search-index build \
  --index data/build/reader/search.lance \
  --language grc \
  --replace \
  --output json

just cli reader --catalog $CATALOG search-index status \
  --index data/build/reader/search.lance \
  --output json

just cli reader --catalog $CATALOG search-index validate \
  --index data/build/reader/search.lance \
  --output json
```

Search:

```bash
just cli reader --catalog $CATALOG search "λόγος" \
  --index data/build/reader/search.lance \
  --language grc \
  --limit 20 \
  --context 1 \
  --output json
```

Stable search response fields:

- `schema_version`
- `mode`
- `catalog_path`
- `index_path`
- `request.query`
- `request.language`
- `items[].score`
- `items[].work_id`
- `items[].collection_id`
- `items[].language`
- `items[].title`
- `items[].author`
- `items[].canonical_author_id`
- `items[].canonical_author_name`
- `items[].cts_work_urn`
- `items[].citation_path`
- `items[].segment_id`
- `items[].sort_key`
- `items[].text`
- `items[].snippet`
- `items[].context_before`
- `items[].context_after`
- `items[].target.work_ref`
- `items[].target.segment`
- `pagination.next_cursor`
- `pagination.prev_cursor`
- `pagination.limit`

Supported filters: `--language`, `--collection`, `--work-id`, `--author-id`,
`--group`, `--tag`, `--mode keyword|phrase|exact`, `--field`, `--context`,
`--limit`, and `--cursor`.

`search-index inspect-normalize --language <lang> <text> --output json` exposes
the segment/query normalization fields used to build and query the index.
Clients can use it for debugging query expansion and explaining why a search
matches.

`reader search --mode fuzzy` expands user-facing forms into language-aware
search candidates and searches them in rank order with deduplication. Greek
ASCII transliteration such as `logos` and `andra` is expanded to Greek folded
search forms; Sanskrit folded variants such as `sankara`/`samkara` are exposed
through the same candidate contract. Fuzzy response payloads include
`request.query_candidates`, and each matched item includes `matched_query`,
`input_query`, `matched_field`, `match_type`, and `candidate_rank`.

Encounter integration:

```bash
just cli encounter grc logos all \
  --include-reader-search \
  --output json \
  --translation-mode off

just cli encounter grc logos all \
  --reader-search-index data/build/reader/search.lance \
  --reader-search-all-candidates \
  --reader-search-limit 5 \
  --reader-search-context 1 \
  --output json \
  --translation-mode off
```

Stable encounter additions:

- `request.include_reader_search`
- `request.reader_search_index`
- `request.reader_search_limit`
- `request.reader_search_context`
- `request.reader_search_field`
- `request.reader_search_all_candidates`
- `reader_search.schema_version`
- `reader_search.query_candidates`
- `reader_search.search_all_candidates`
- `reader_search.index_path`
- `reader_search.actions`
- `reader_search.items`
- `reader_search.warnings`
- `actions[]` item with `kind = "search_reader_corpus"`

When `--reader-search-all-candidates` is supplied, encounter searches each
query candidate from the encounter pipeline and deduplicates inline hits by
segment id or work/citation fallback. Each `reader_search.items[]` result
includes `matched_query`, `input_query`, `match_type`, and `candidate_rank` so
the UI can explain why a corpus example appeared.

## Authors

```bash
just cli reader --catalog $CATALOG authors \
  --language san --query kalidasa --limit 50 --cursor 0 --output json
just cli reader --catalog $CATALOG authors \
  --language san --section क --limit 50 --cursor 0 --output json
just cli reader --catalog $CATALOG author langnet:reader:author:san:kalidasa \
  --language san --output json
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
- `items[].word_count`
- `items[].word_count_method`
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

`reader author <author-ref>` returns one author-index item plus a
`representative_works` list and a `query` object that can be passed back to
`reader works`. The author reference may be a public author selector, source
author id, canonical author id, or exact/substring display name.

When a display author name maps to multiple source authorities, the reader may
append a disambiguation suffix to `display_name` and `author`, such as
`Georgius (Acropolites)`, `Plato (Phil.)`, `Plato (Comic.)`, or
`Pausanias (Perieg.)`. Research-backed accepted overlays may also canonicalize
the display itself, such as `Philoxenus Cytherius`, `Saint Jerome`, or
`Mark the Evangelist`. Clients should use `author_id`, not display text, as the
stable selector.

## Corpus QA Exports

```bash
just cli reader --catalog $CATALOG duplicate-audit \
  --kind authors --language grc --limit 100 --output json

just cli reader --catalog $CATALOG classification-export \
  --language grc --path examples/debug/reader-classification-export.csv

just cli reader classify-works \
  --input-csv examples/debug/reader-classification-export.csv \
  --output-csv examples/debug/reader-generated-classifications.csv \
  --model openai:deepseek/deepseek-v4-flash \
  --batch-size 25 \
  --concurrency 4 \
  --timeout-seconds 120 \
  --max-attempts 3 \
  --raw-response-dir examples/debug/reader-classifier-raw \
  --shuffle-seed reader-classifier-2026-05-15 \
  --output json

just cli reader --catalog $CATALOG sync-classifications \
  --classification-csv examples/debug/reader-generated-classifications.csv \
  --output json

# For a shared catalog, such as Latin and Greek in the same DuckDB file,
# merge one generated file without dropping classifications from the other language.
just cli reader --catalog $CATALOG sync-classifications \
  --classification-csv examples/debug/reader-generated-latin-classifications.csv \
  --merge \
  --output json

just cli reader --catalog $CATALOG popular --language grc --output json
just cli reader --catalog $CATALOG facets --output json

just cli reader --catalog $CATALOG author-classification-export \
  --language lat --path examples/debug/reader-author-classification-latin.csv
just cli reader --catalog $CATALOG sync-author-classifications \
  --classification-csv examples/debug/reader-author-generated-latin.csv \
  --merge --output json
just cli reader --catalog $CATALOG authors --agent-kind work_title --output json

just cli reader --catalog $CATALOG sync-metadata-overlays \
  --metadata-overlay-dir data/curated/reader_metadata --output json
just cli reader --catalog $CATALOG repair-languages --output json
just cli reader --catalog $CATALOG prune-stale-classifications --output json
```

`duplicate-audit --kind authors` reports display-author names that map to more
than one authority id. It does not report a single author simply because that
author has many works.

`classification-export` emits one CSV row per work with stable identifiers and
blank enrichment columns for bulk classification, including
`classification_discovery_group_id`, `classification_discovery_tags`,
`classification_global_popularity_score`,
`classification_global_popularity_tier`,
`classification_group_popularity_score`,
`classification_group_popularity_tier`, `classification_category`,
`classification_period`,
`classification_date_range`, `classification_authorship_status`,
`classification_popularity_score`, `classification_scope`,
`classification_scope_popularity_score`, and `classification_notes`.

`classify-works` sends exported rows to the configured OpenRouter/aisuite model
in batches and writes generated classification rows. The default batch size is
25, with one model batch in flight by default, three attempts, and a
120-second timeout per provider call. Use `--concurrency N` for provider-bound
bulk jobs; `4` has worked well for Latin, and `8` is reasonable for larger
resumable runs when the provider is stable. If a batch
returns incomplete generated metadata, including rows without
`classification_notes`, the classifier retries that batch by splitting it into
smaller batches, so large corpus runs can keep useful throughput without
requiring one model call per work. When `--raw-response-dir` is set, completed
`batch-XXXX.json` responses are reused on rerun, which makes interrupted
provider runs resumable. When `--shuffle-seed` is set, rows are shuffled
deterministically before batching and written back in input CSV order. This
spreads catalog-order clusters, such as many works by one author, across model
requests while preserving stable output files. This output is generated
metadata, not candidate metadata: `sync-classifications` imports it directly
into the reader catalog while preserving `classification_generator_models` and
`classification_generator_run_id` provenance. By default, sync replaces the
catalog's generated classification table. Pass `--merge` to replace only the
work ids present in the CSV, which is the correct mode when Latin and Greek
classifications are generated separately for the shared classics catalog.
`sync-classifications` only inserts rows whose work can be resolved in the
current catalog, and `sync-author-classifications` only inserts rows for current
catalog authors. Work sync resolves generated rows through catalog `work_id`,
`source_id`, and `cts_work_urn` aliases, so a generated row keyed as
`langnet:reader:tlg:tlg0059.030` still applies to a TEI-preferred catalog work
keyed as `urn:cts:greekLit:tlg0059.tlg030`. Author sync treats compact and CTS
source ids as equivalent, so a generated row keyed as `tlg0059` still applies to
a catalog author keyed as `urn:cts:greekLit:tlg0059`. Run
`prune-stale-classifications` after merging generated files to remove rows that
came from the wrong language batch. Discovery shelves and prominence-sorted
author surfaces are not ready after a full catalog rebuild until this generated
work and author metadata layer has been restored.

`reader authors --sort prominence` ranks by generated prominence score, then
prominence tier, then catalog evidence (`work_count`, `word_count`) before
falling back to catalog order. This prevents score ties from turning into an
alphabetical "top authors" list.
`popular` and
`works --sort popularity` then use `classification_popularity_score` to rank
works, with unclassified works sorted after classified works. New clients should
prefer `--sort global-popularity` for the whole-language score and
`--sort group-popularity` for the score within the work's discovery group.

The classifier prompt includes structured allowed values for fields that need
stable downstream behavior:

`reader facets` returns the discovery affordances clients can expose directly:
strict work discovery groups, strict discovery tags, supported sort modes, and
example query shapes. It also includes generated author classification facets.
`reader groups`, `reader tags`, and `reader author-facets` remain narrower
commands for listing only those controlled value sets. `reader facets
--language ...`, `reader groups --language ...`, and `reader tags --language
...` return only values present in the selected catalog language and add
`work_count`, `classified_work_count`, `author_count`, and
`max_group_popularity_score` to each discovery value.

`reader shelves --language ...` returns discovery-card payloads for the reader
landing page. Each item has `id`, `label`, `description`, `query`,
`work_count`, `classified_work_count`, `author_count`, and `sample_works`.
The `query` object can be passed back into `reader works`; for example
`{"group": "medicine", "sort": "group-popularity"}` represents
`reader works --language <language> --group medicine --sort group-popularity`.
For shelf and language-scoped facet payloads, `author_count` counts distinct
nonblank author ids and falls back to meaningful display author names when a
source has no normalized author id. Blank and `Unknown` authors are excluded, so
Sanskrit shelves can show real author coverage without inflating anonymous
scriptural shelves.

`reader coverage` returns one item per language present in the catalog. Clients
should use `supported_reader_language` plus `has_discovery_facets` to decide
which language tabs or landing pages are ready for the reader UI. Languages
such as `eng`, `heb`, or `cop` may be present in a catalog while still reporting
`supported_reader_language: false`.

- `classification_period`: language-specific values for `grc`, `lat`, and `san`;
- `classification_discovery_group_id`: one strict primary peer bucket such as
  `medicine`, `grammar`, `epic`, `ethics`, `rhetoric`, or `philosophy`;
- `classification_discovery_tags`: zero or more strict pipe-delimited tag IDs
  such as `ayurveda|medicine|technical`;
- `classification_authorship_status`: `single_attributed`, `traditional`,
  `anonymous`, `attributed`, `uncertain`, `disputed`, `composite`,
  `pseudepigraphic`;
- `classification_popularity_tier`: `canonical`, `major`, `common`,
  `specialist`, `obscure`;
- `classification_global_popularity_tier`: same tier values for the
  whole-language score;
- `classification_group_popularity_tier`: same tier values for the score within
  `classification_discovery_group_id`;
- `classification_confidence`: `high`, `medium`, `low`.

`classification_category` and `classification_scope` are compatibility fields.
The classifier prompt now centers the strict discovery group and tag taxonomy;
legacy category/scope fields can be derived from the group when omitted.
`classification_notes` are requested as standalone scholarly prose for a
reader-facing catalog, including alternate edition/source copy rows.

`classification_global_popularity_score` and the compatibility
`classification_popularity_score` are calibrated within the whole language
corpus for the row's language. `classification_group_popularity_score` and the
compatibility `classification_scope_popularity_score` are calibrated within the
single primary `classification_discovery_group_id`.

Author classification is separate from work classification. The source author
string remains available as `items[].display_name`/`items[].author`; generated
author metadata adds `items[].author_canonical_name`,
`items[].author_agent_kind`, `items[].author_historicity_status`,
`items[].author_prominence_score`, `items[].author_prominence_tier`,
`items[].author_classification_confidence`, and
`items[].author_classification_notes`. `reader authors --agent-kind` and
`reader authors --historicity` filter this generated layer, and
`reader authors --sort prominence` orders classified authors by generated
prominence.

The prompt includes this popularity rubric:

- `canonical`, 90-100: central across the language corpus and broad curricula;
- `major`, 70-89: widely studied across the language tradition;
- `common`, 40-69: often read or cited beyond a narrow specialty;
- `specialist`, 10-39: important mainly within a specialty or research subfield;
- `obscure`, 0-9: rarely read, fragmentary, marginal, or minimally attested.

`source_id` and `work_id` are prompt context for row matching and edition
awareness. Reader-facing notes should be phrased around title, author,
tradition, genre, and scholarly role; source collection names belong in
identifier and provenance fields.

For curation into smaller groups, use the strict discovery filters:

- `--group medicine`: filter by primary peer group;
- `--tag ayurveda`: filter by secondary discovery tag;
- `--sort global-popularity`: sort by whole-language score;
- `--sort group-popularity`: sort by popularity among peers in the selected
  discovery group.

The `popular` and `works` commands still accept `--scope` as a compatibility
alias matching generated scope/category text. New workflows should use `--group`
or `--tag`:

```bash
just cli reader --catalog $CATALOG popular \
  --language san --tag ayurveda --output json

just cli reader --catalog $CATALOG works \
  --language lat --group grammar --sort group-popularity --output json

just cli reader --catalog $CATALOG groups --output json

just cli reader --catalog $CATALOG tags --output json
```

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
- `items[].word_count`
- `items[].word_count_method`

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
- `item.source_label`
- `item.edition_label`
- `item.short_disambiguation_label`
- `item.cts_work_urn`

The work reference may be a `work_id`, `cts_work_urn`, or catalog alias.
List, shelf sample, and work-detail payloads preserve raw ids while exposing
UI-safe labels for duplicate-title disambiguation.

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

## Work Map

```bash
just cli reader --catalog $CATALOG map <work-ref> --output json
```

Stable fields:

- `items[].work_id`
- `items[].canonical_text_id`
- `items[].canonical_address`
- `items[].node_id`
- `items[].parent_node_id`
- `items[].level`
- `items[].kind`
- `items[].label`
- `items[].native_label`
- `items[].ordinal`
- `items[].start_citation`
- `items[].end_citation`
- `items[].word_count`
- `items[].word_count_method`
- `items[].provenance`
- `items[].confidence`
- `items[].note`
- `items[].source_file`

`reader map` returns table-of-contents style structure when the catalog has
native or curated structure data. Curated nodes are imported from
`data/curated/reader_work_maps/`; inferred nodes, when added later, must be
marked with `provenance = "inferred"` and an explicit confidence value.

Operator sync command for applying updated research curation to an existing
catalog without a full corpus rebuild:

```bash
just cli reader --catalog $CATALOG sync-work-maps \
  --work-map-dir data/curated/reader_work_maps --output json
```

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
just cli reader --catalog $CATALOG show 'urn:ctsv2:lat:aeneid-arma-virumque-cano?ref=1.23' --output json
```

Stable fields:

- `segment`: same segment contract as `contents`;
- `segment.canonical_text_id`: preferred LangNet CTSv2 logical text id when
  available;
- `segment.canonical_address`: preferred CTSv2 resource address when available;
- `navigation.previous.citation_path`
- `navigation.previous.address`
- `navigation.next.citation_path`
- `navigation.next.address`

Navigation addresses prefer CTSv2 when present, then the work's CTS work URN,
then the catalog `work_id`.

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
