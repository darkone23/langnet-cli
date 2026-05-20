# Reader CLI Handoff

Date: 2026-05-14

This document is a practical handoff for someone encountering the LangNet
reader corpus CLI today. The current state is suitable for an informed early
user or corpus operator. It is not yet a polished end-user release or final web
UI.

The reader CLI explores local DuckDB catalogs of cleaned/imported texts. It
does not fetch external texts at read time.

The product target is one unified reader catalog at
`data/build/reader/catalog.duckdb`, or
`examples/debug/reader_full_curated_current/catalog.duckdb` during local
development. Source-split catalogs are useful audit/debug outputs, not the
normal catalog a learner or web app should see. See
`docs/READER_DATA_BUILD.md` for required source inputs and rebuild commands.

## Readiness

Ready today for:

- enumerating available works, authors, collections, and aliases;
- discovering candidate catalogs with `reader catalogs`;
- searching and paginating works and authors for web UI use;
- browsing native author sections with `reader author-sections`;
- retrieving works by stable author selector with `reader works --author-id`;
- listing the contents of a work;
- windowed contents reads with `--cursor`, `--from`, and `--around`;
- reading exact segments by catalog-native `work_id` or CTS-style work URN;
- next/previous segment pointers from JSON `reader show` responses;
- exact work metadata lookup by `work_id`, CTS work URN, or alias;
- additive Sanskrit display layers, including Devanagari where conversion is
  available;
- validating catalog and book artifacts;
- reviewing evidence-backed metadata overlays and attribution claims.

Not yet final:

- Sanskrit still has 564 `Unknown` display authors.
- Friendly dictionary shorthand is secondary. New catalogs should prefer
  `canonical_text_id` / `canonical_address`; older `work_id` and `cts_work_urn`
  remain reliable compatibility paths.
- Citation schemes are source-native. DCS Sanskrit texts often use sentence IDs
  such as `386927`, not always book/line numbering.
- Catalogs under `examples/debug/` are generated development artifacts, not
  durable packaged data.

## Catalog Targets

Default unified catalog:

```bash
data/build/reader/catalog.duckdb
```

Development unified catalog:

```bash
examples/debug/reader_full_curated_current/catalog.duckdb
```

Build it from all available source roots:

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

Add `--output-root examples/debug/reader_full_curated_current` for a local
development build. Rebuild after parser/importer changes, then rebuild the
derived search index.

Reader outputs now include LangNet CTSv2 addresses when the catalog was built
with current code:

- `canonical_text_id`: flat logical text id such as
  `urn:ctsv2:lat:aeneid-arma-virumque-cano`;
- `canonical_address`: segment/resource address such as
  `urn:ctsv2:lat:aeneid-arma-virumque-cano?ref=1.23`.

Downstream consumers should prefer CTSv2 fields for new links. Existing
`work_id`, `cts_work_urn`, TLG/PHI ids, and source URNs remain compatibility
aliases.

## Current Audit Catalogs

PHI/TLG classics:

```bash
examples/debug/reader_classics_legacy_full_curated_current/catalog.duckdb
```

Current status:

- 7,836 works
- 10,591,345 segments
- 87,197,666 tokens
- 2,196 physical book DuckDB files
- 0 source errors
- strict validation: 0 issues

Sanskrit:

```bash
examples/debug/reader_sanskrit_full_curated_current/catalog.duckdb
```

Current status:

- 977 works
- 3,319,944 segments
- 26,382,642 tokens
- 0 source errors
- strict validation: 0 issues
- 564 remaining `Unknown` display authors
- 38 accepted claim-level attribution records

Perseus and digilibLT audit catalogs also exist. These split catalogs are
generated audit artifacts for importer review, not product catalogs:

```bash
examples/debug/reader_perseus_full_curated_current/catalog.duckdb
examples/debug/reader_digiliblt_anonymous_overlay_verify/catalog.duckdb
```

## First Commands

Run from the project root.

```bash
export CATALOG=examples/debug/reader_full_curated_current/catalog.duckdb

just cli reader --catalog $CATALOG summary
just cli reader --catalog $CATALOG works --author Homer
just cli reader --catalog $CATALOG contents urn:cts:greekLit:tlg0012.tlg002 --limit 5
just cli reader --catalog $CATALOG show urn:cts:greekLit:tlg0012.tlg002 --segment 1.1
```

If the unified development catalog has not been built, use
`examples/debug/reader_classics_legacy_full_curated_current/catalog.duckdb` as
an audit-catalog fallback for this Homer smoke test.

If no `--catalog` is passed, set `LANGNET_READER_CATALOG` to choose the catalog
for the process, or let the CLI fall back to the default unified build at
`data/build/reader/catalog.duckdb`. Use `reader catalogs --output json` to
inspect candidate catalogs before a web app chooses one.

Web-facing JSON contracts are documented in:

```bash
docs/READER_WEB_CONTRACT.md
```

Expected reading result: Odyssey 1.1 should return:

```text
Ἄνδρα μοι ἔννεπε, Μοῦσα, πολύτροπον, ὃς μάλα πολλὰ
```

## Full Text Search

Full text search uses a rebuildable derived Lance dataset built and queried
through DuckDB's `lance` extension. The reader catalog and per-book DuckDB files
remain canonical; rebuilding the search index does not mutate corpus data.

Build and inspect an index:

```bash
export SEARCH_INDEX=data/build/reader/search.lance

just cli reader --catalog $CATALOG search-index build \
  --index $SEARCH_INDEX \
  --language grc \
  --replace \
  --output json

just cli reader --catalog $CATALOG search-index status \
  --index $SEARCH_INDEX \
  --output json

just cli reader --catalog $CATALOG search-index validate \
  --index $SEARCH_INDEX \
  --output json
```

Search examples:

```bash
just cli reader --catalog $CATALOG search "λογος" \
  --index $SEARCH_INDEX --language grc --limit 10

just cli reader --catalog $CATALOG search "iulius uiuit" \
  --index $SEARCH_INDEX --language lat --context 1 --output json

just cli reader --catalog $CATALOG search "sankara" \
  --index $SEARCH_INDEX --language san --output json
```

Normalization is inspectable:

```bash
just cli reader search-index inspect-normalize --language grc "λόγος"
just cli reader search-index inspect-normalize --language san "Śaṃkara"
just cli reader search-index inspect-query --language grc --mode fuzzy logos --output json
```

Current search is BM25-like Lance FTS at the segment level. It folds Greek
accents/breathings and final sigma, handles Latin `i/j` and `u/v` variants, and
gives Sanskrit ASCII searches such as `sankara` a route to IAST text such as
`Śaṃkara`. The CLI/result contract stays backend-neutral for future hybrid
search work. `reader search --mode fuzzy` expands the input into inspectable
language-aware candidates before searching, for example Greek ASCII
transliteration such as `logos` -> `λογοσ` or `andra` -> `ανδρα`, and Sanskrit
folded forms such as `sankara` -> `samkara`. Fuzzy result items include
`matched_query`, `input_query`, `matched_field`, `match_type`, and
`candidate_rank`.

Encounter can expose reader-search followups:

```bash
just cli encounter grc logos all \
  --include-reader-search \
  --output json \
  --translation-mode off
```

When a Lance search index is available, encounter can include top corpus hits
inline:

```bash
just cli encounter grc logos all \
  --reader-search-index $SEARCH_INDEX \
  --reader-search-all-candidates \
  --reader-search-limit 5 \
  --reader-search-context 1 \
  --output json \
  --translation-mode off
```

By default, inline reader search uses the first encounter query candidate to
preserve the original narrow behavior. Add `--reader-search-all-candidates`
when the caller wants encounter to search every useful candidate, deduplicate
hits, and attach `matched_query`, `input_query`, `match_type`, and
`candidate_rank` to each inline corpus result. This is the first fuzzy-search
increment; standalone `reader search --mode fuzzy` and inspectable expanded
query generation remain lower on the active stack.

For translated or tradition-heavy works, the public reader `author` should name
the agent responsible for the text in the displayed language when that is the
most useful discovery behavior. The Latin Vulgate PHI/CIV family (`civ0004`)
is curated to display under Saint Jerome with CTS author URN
`urn:cts:latinLit:stoa0162`. The Greek New Testament Gospel rows
`civ0003.001` through `civ0003.004` are curated at the individual work level to
display under the traditional evangelist names Matthew, Mark, Luke, and John.
Use attribution records for secondary, traditional, possible, or
original-source claims that should remain queryable without replacing the public
display author. Accepted attribution records are surfaced on work rows through
`metadata_attributions` plus convenience name arrays such as `translator_names`,
`traditional_author_names`, and `attributed_author_names`; this lets the reader
show “translated by Jerome” or the traditional Septuagint translator tradition
without collapsing those claims into the main author field.

Existing catalogs can apply accepted display overlays without a rebuild:

```bash
just cli reader --catalog $CATALOG sync-metadata-overlays \
  --metadata-overlay-dir data/curated/reader_metadata \
  --output json

just cli reader --catalog $CATALOG sync-metadata-attributions \
  --metadata-attribution-dir data/curated/reader_attributions \
  --output json
```

Current Bible attribution seeds:

- Latin Vulgate PHI/CIV (`civ0004`): `translator_names=["Saint Jerome"]`.
- Septuagint / Old Greek Bible PHI/CIV (`civ0002`): traditional
  `translator_names=["Seventy-two translators"]`.
- TLG Septuaginta (`tlg0527`): traditional
  `translator_names=["Seventy-two translators"]`.
- Pentateuch/Torah rows currently seeded for Vulgate, PHI Septuagint, and TLG
  Septuaginta carry `traditional_author_names=["Moses"]`.
- Revelation / Apocalypse rows currently seeded for Greek New Testament and
  Vulgate carry `traditional_author_names=["John of Patmos"]`.

PHI/CIV legacy sources in the Latin source directory can include non-Latin
texts. Use the repair command after importer changes or source metadata syncs:

```bash
just cli reader --catalog $CATALOG repair-languages --output json
just cli reader --catalog $CATALOG prune-stale-classifications --output json
```

Current source-family handling moves Hebrew Bible (`civ0001`) to `heb`,
Septuagint and Greek New Testament (`civ0002`, `civ0003`) to `grc`, and
Sahidic Coptic (`cop0001`) to `cop`; Latin Vulgate (`civ0004`) remains `lat`.
The repair path recognizes these exact family ids, so author overlays such as
`civ0003.002 -> Mark the Evangelist` do not make later language repairs depend
on stale source-author labels.

Sanskrit example:

```bash
export CATALOG=examples/debug/reader_sanskrit_full_curated_current/catalog.duckdb

just cli reader --catalog $CATALOG works --author Kālidāsa
just cli reader --catalog $CATALOG contents langnet:reader:sanskrit_dcs:dcs_250 --limit 3
just cli reader --catalog $CATALOG show langnet:reader:sanskrit_dcs:dcs_250 --segment 386927
```

Expected reading result: Meghadūta sentence `386927` should return:

```text
kaścit kāntāvirahaguruṇā svādhikārāt pramattaḥ śāpenāstaṃgamitamahimā varṣabhogyeṇa bhartuḥ
```

## Useful Discovery Commands

List all works:

```bash
just cli reader --catalog $CATALOG works --limit 50
just cli reader --catalog $CATALOG works --query odys --limit 10
just cli reader --catalog $CATALOG author-sections --language lat
just cli reader --catalog $CATALOG authors --language lat --section V --limit 50
just cli reader --catalog $CATALOG author urn:cts:greekLit:tlg0012 --language grc --output json
```

Explore generated discovery metadata:

```bash
just cli reader --catalog $CATALOG facets --output json
just cli reader --catalog $CATALOG facets --language grc --output json
just cli reader --catalog $CATALOG groups --output json
just cli reader --catalog $CATALOG groups --language lat --output json
just cli reader --catalog $CATALOG tags --output json
just cli reader --catalog $CATALOG tags --language san --output json
just cli reader --catalog $CATALOG shelves --language san --sample-limit 3 --output json
just cli reader --catalog $CATALOG coverage --output json
just cli reader --catalog $CATALOG works --language san --tag ayurveda --sort group-popularity
just cli reader --catalog $CATALOG works --language lat --group grammar --sort group-popularity
just cli reader --catalog $CATALOG popular --language grc --group medicine --limit 10
just cli reader --catalog $CATALOG popular --language grc --tag tragedy --limit 10
just cli reader --catalog $CATALOG works --language grc --sort global-popularity
```

The generated classifier uses one strict `classification_discovery_group_id` as
the peer bucket for group popularity, plus pipe-delimited strict
`classification_discovery_tags` for faceted discovery. `--scope` remains a
compatibility filter for older generated CSVs, but new workflows should prefer
`--group` and `--tag`. `reader facets` is the executable discovery guide: it
lists available groups, tags, sort modes, and example query shapes for prompts
such as "show me popular Ayurvedic texts" or "show me Latin grammar texts by
popularity". When `--language` is supplied, `reader facets`, `reader groups`,
and `reader tags` return only values that have classified works in that
language and include `work_count`, `classified_work_count`, `author_count`, and
`max_group_popularity_score`.

`reader shelves --language ...` builds discovery cards from the same classified
catalog data. Each shelf includes a `query` object for the corresponding
`reader works --group ... --sort group-popularity` request plus representative
`sample_works`. `reader coverage` reports per-language catalog presence and
discovery readiness, including work, author, segment, token, classification,
facet, and supported-reader-language counts. Shelf and facet `author_count`
uses distinct nonblank author ids when available, falling back to meaningful
display author names and excluding blank/`Unknown` values. This matters for
Sanskrit sources where many named works do not carry normalized author ids.

For bulk generation, use `reader classify-works --concurrency N` to run several
provider requests at once. Raw response caching still applies, so interrupted
runs can resume completed batches. A conservative value is `4`; `8` is a good
starting point for large Greek/Latin runs when provider connections are stable.

Current full generated work-classification artifacts:

- Greek:
  `examples/debug/reader-full-classification-2026-05-16/discovery/greek-generated-discovery-b50.csv`
  generated from
  `examples/debug/reader-full-classification-2026-05-16/greek-enriched-export-v2.csv`
  with raw cache
  `examples/debug/reader-full-classification-2026-05-16/discovery/greek-discovery-raw-b50`.
- Latin:
  `examples/debug/reader-full-classification-2026-05-16/discovery/latin-generated-discovery-b50.csv`.
- Sanskrit:
  `examples/debug/reader-full-classification-2026-05-16/discovery/sanskrit-generated-discovery.csv`.

The unified catalog is shared. After a full rebuild, restore discovery metadata
before verifying shelves: sync one full-language file in replace mode, sync the
other full-language files and correction layers with `--merge`, then prune rows
that came from the wrong language batch. The sync commands now only insert
generated rows whose work exists in the current catalog, so classifier CSVs from
older builds do not leave orphan metadata after dedupe or source-preference
changes. Work sync resolves generated rows through catalog `work_id`,
`source_id`, and `cts_work_urn` aliases, so a generated
`langnet:reader:tlg:tlg0059.030` row still applies when the current catalog uses
`urn:cts:greekLit:tlg0059.tlg030`. Author sync also treats compact and CTS
author ids as equivalent, so a generated `tlg0059` author row still applies when
the current work catalog uses `urn:cts:greekLit:tlg0059`.

```bash
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
```

Current audit correction layer:

- `examples/debug/reader-full-classification-2026-05-16/discovery/audit-corrections-2026-05-17.csv`

This is a small generated-plus-audit merge layer for known over-ranking cases,
mainly fragmentary rows that inherited too much popularity from a canonical
author. Apply it after the full Greek/Latin generated CSVs:

```bash
just cli reader --catalog $CATALOG sync-classifications \
  --classification-csv examples/debug/reader-full-classification-2026-05-16/discovery/audit-corrections-2026-05-17.csv \
  --merge \
  --output json
```

For high-popularity authors, prefer source-backed author overlays rather than
trying to make the generated classifier carry biographical authority. Generated
work classifications are suitable for broad discovery and sorting; cited
overlays should provide canonical author identity, aliases, region, period, and
short bios for the authors users are most likely to see first.

`sync-classifications` replaces generated classifications by default. Use
`--merge` when syncing one language or source slice into a catalog that already
contains another slice, especially the shared Greek/Latin catalog:

```bash
just cli reader --catalog $CATALOG sync-classifications \
  --classification-csv examples/debug/reader-full-classification-2026-05-16/discovery/greek-generated-discovery-b50.csv \
  --merge \
  --output json
```

Filter by display author:

```bash
just cli reader --catalog $CATALOG works --author Cicero
just cli reader --catalog $CATALOG works --language lat --author-id phi0690
```

Filter by accepted authorship attribution claims as well as display author:

```bash
just cli reader --catalog $CATALOG works --attributed-to Kālidāsa
```

Inspect accepted attribution claims:

```bash
just cli reader --catalog $CATALOG attributions --relation-type attributed_author
```

Generated author classification is a separate layer from work classification.
It keeps feed-provided author strings intact while adding normalized/canonical
agent metadata for author-index navigation:

```bash
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

just cli reader --catalog $CATALOG author-classification-export \
  --language lat \
  --path examples/debug/reader-author-classification-latin.csv

just cli reader --catalog $CATALOG sync-author-classifications \
  --classification-csv examples/debug/reader-author-generated-latin.csv \
  --merge \
  --output json

just cli reader --catalog $CATALOG author-facets --output json
just cli reader --catalog $CATALOG authors --language lat --agent-kind person --sort prominence
just cli reader --catalog $CATALOG authors --agent-kind work_title
just cli reader --catalog $CATALOG authors --historicity pseudonymous
```

Author classification answers what kind of agent a source author label is:
`person`, `collective`, `tradition`, `work_title`, `anonymous_label`, or
`ambiguous`, plus historicity such as `historical`, `legendary`, `mythic`,
`pseudonymous`, `traditional`, `uncertain`, or `not_applicable`. This is where
labels like `Acts of Thomas`, `English Bible (KJV or AV)`, or
`Pseudo-Dionysius` are normalized/explained; work rows still retain their source
author strings.

Reader payloads distinguish source author headings from canonical author
authorities. `source_author` / `source_author_id` preserve the feed label and
source selector. Public `author` uses the canonical author when one is known. If
the source author slot is a title, anonymous heading, or ambiguous non-author
label, public `author` is `Unknown` and `canonical_author_id` is a
language-scoped LangNet CTS-shaped authority such as
`urn:cts:langnet:author.grc.unknown`. Generated notes about the source heading
remain available under `source_author_*` fields; bios, regions, and time periods
belong to canonical authors rather than source headings.

Inspect metadata overlays:

```bash
just cli reader --catalog $CATALOG overlays --status accepted
```

List a local context window around an addressable segment:

```bash
just cli reader --catalog $CATALOG contents urn:cts:greekLit:tlg0012.tlg002 --around 3.74 --radius 5
```

## Validation

Before handing a catalog to another person, run:

```bash
mkdir -p examples/debug/reader-guide-verify

just cli reader --catalog $CATALOG validate --output json \
  > examples/debug/reader-guide-verify/validate.json

nu -c 'open examples/debug/reader-guide-verify/validate.json | get items | length'
```

The result should be `0`.

Check suspicious display authors:

```bash
just cli reader --catalog $CATALOG works --output json \
  > examples/debug/reader-guide-verify/works.json

nu -c 'open examples/debug/reader-guide-verify/works.json | get items | where author =~ "(?i)unknown|unattributed|pseudo-$" | select language author title work_id | first 40'
```

For the Sanskrit catalog, `Unknown` rows are expected today and should be
treated as the metadata enrichment backlog, not as text-import failures.

## What Was Recently Fixed

- PHI/TLG now uses one physical book DuckDB per source text file while keeping
  one catalog work per IDT work.
- `contents <work>` filters correctly inside shared physical DBs.
- `show <work> --segment <missing>` returns quickly with a null segment instead
  of scanning unrelated book DBs.
- `works` and `authors` support query, cursor, and limit controls for the web
  reader.
- `works` supports strict generated discovery filters via `--group` and `--tag`,
  and can sort by `global-popularity` or `group-popularity`.
- `author-sections` and `authors --section` support complete native author
  indexes for Latin, Greek, and Sanskrit.
- `works --author-id` retrieves all works for an author selector from the
  native author index.
- `contents` supports cursor, `--from`, and `--around` windows.
- JSON `show` responses include adjacent segment pointers.
- Sanskrit segment JSON includes additive display fields while preserving the
  stored source text.
- Attribution CLI output is claim-level rather than duplicated once per
  evidence citation.
- Catalog aliases are catalog-local: aliases only register when their target is
  present in the catalog.

## Known Caveats

- The source path shown inside JSON artifact payloads may still include local
  machine paths. Curated citation YAML must not use those paths; it uses durable
  URLs and portable source-root references instead.
- PHI has 26 IDT rows that produced no segment text and are skipped from
  learner-facing enumeration.
- Sanskrit traditional corpora should not be force-filled with modern-looking
  authors when the responsible tradition is anonymous, composite, or uncertain.
- Chronology/date metadata is deferred. It should be represented as a separate
  evidence-backed layer later.

## Next Backlog

1. Continue Sanskrit metadata enrichment for the remaining 564 `Unknown` works,
   prioritizing clear named DCS works.
2. Add explicit exception reporting for skipped PHI zero-segment IDT rows if
   operators need to audit them from the CLI.
3. Validate the beginner guide against a unified all-family catalog once that
   combined build is promoted.
4. Add a chronology candidate/export layer after metadata quality is stable.

## Related Docs

- `docs/READER_CLI_BEGINNER_GUIDE.md`
- `docs/READER_CORPUS_STATUS.md`
- `docs/plans/active/infra/reader-corpus-quality-roadmap.md`
- `examples/debug/reader-audit/NOTES.md`
