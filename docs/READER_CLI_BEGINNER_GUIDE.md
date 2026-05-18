# Reader CLI Beginner Guide

The reader CLI explores a local DuckDB library of cleaned texts. It does not
fetch external texts at read time; the catalog points at imported book
databases.

The normal user question is source-agnostic: "what books do we have?" Import
sources such as Perseus XML, PHI/TLG CD data, DCS, Sanskrit text files, or
digilibLT are provenance/debug details, not the main reading interface.

Use `just cli reader ...` from the project root.

## Required Data

The reader does not download corpus data. A full build needs local source roots
for the corpora you want included:

- PHI Latin: `--phi-latin-dir /path/to/phi-latin`
- TLG Greek: `--tlg-e-dir /path/to/tlg_e`
- Perseus: `--perseus-dir /path/to/perseus`
- digilibLT: `--digiliblt-dir /path/to/digiliblt`
- Sanskrit/DCS: `--sanskrit-dir /path/to/sanskrit`

Normal builds should also include the curated repo layers:
`data/curated/reader_aliases`, `data/curated/reader_metadata`,
`data/curated/reader_attributions`, `data/curated/reader_contained_works`, and
`data/curated/reader_work_maps`.

## Pick A Catalog

A production-style reader build should combine all available corpora into one
catalog. During development we also keep smaller debug catalogs so each import
family can be audited independently.

Default unified catalog:

```bash
export CATALOG=data/build/reader/catalog.duckdb
just cli reader --catalog $CATALOG summary
```

Unified curated development catalog, when present:

```bash
export CATALOG=examples/debug/reader_full_curated_current/catalog.duckdb
just cli reader --catalog $CATALOG summary
```

If the unified debug catalog has not been built yet, use one of the current
curated audit catalogs while import families are being validated separately:

```bash
export CATALOG=examples/debug/reader_perseus_full_curated_current/catalog.duckdb
just cli reader --catalog $CATALOG summary
```

Other current curated audit catalogs:

```bash
just cli reader --catalog examples/debug/reader_perseus_full_curated_current/catalog.duckdb summary
just cli reader --catalog examples/debug/reader_digiliblt_anonymous_overlay_verify/catalog.duckdb summary
just cli reader --catalog examples/debug/reader_sanskrit_full_curated_current/catalog.duckdb summary
just cli reader --catalog examples/debug/reader_classics_legacy_full_curated_current/catalog.duckdb summary
```

If no `--catalog` is passed, the CLI looks for the default unified build
catalog at `data/build/reader/catalog.duckdb`. You can also set
`LANGNET_READER_CATALOG` for a process, or inspect likely choices with:

```bash
just cli reader catalogs --output json
```

For long operator rebuilds, use progress output:

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

Omit unavailable source-root flags for partial local builds, and document the
omission. Rebuild the catalog after parser/importer changes. Rebuild the
derived search index after every catalog rebuild; see
`docs/READER_DATA_BUILD.md` for the search-index command.

## Ask What Is In The Library

List collections. This is mostly useful for technical inspection; readers
usually start with authors or works:

```bash
just cli reader --catalog $CATALOG collections
```

List authors:

```bash
just cli reader --catalog $CATALOG author-sections --language lat
just cli reader --catalog $CATALOG authors --language lat --section V --limit 50
```

Author sections are native to the selected language: Latin A-Z with abbreviated
Roman praenomina ignored, Greek section keys in Greek alphabet order, and
Sanskrit section keys in Devanagari/Sanskrit pedagogical order where
transliteration is available.

List every work. This is the main "what books do we have?" command, regardless
of where each text originally came from. The pretty output includes the
addressable `work_id` in brackets:

```bash
just cli reader --catalog $CATALOG works --limit 50
```

Search works without loading the full library:

```bash
just cli reader --catalog $CATALOG works --query odys --limit 10
```

Filter works by language:

```bash
just cli reader --catalog $CATALOG works --language grc
just cli reader --catalog $CATALOG works --language lat
```

Filter works by visible display author:

```bash
just cli reader --catalog $CATALOG works --author Plato
```

Once an author is selected from `reader authors`, use its `author_id` selector
to retrieve all of that author's works without free-text matching:

```bash
just cli reader --catalog $CATALOG works --language lat --author-id phi0690
```

Plain author searches keep pseudo-author labels separate. For example,
`--author Plato` does not include `Pseudo-Plato`; ask for the pseudo label
explicitly when that is what you mean:

```bash
just cli reader --catalog $CATALOG works --author Pseudo-Plato
```

Ask for works thought to be associated with an author. This is still a
catalog-level question: it searches display authors plus accepted authorship
attribution claims and does not read book text:

```bash
just cli reader --catalog $CATALOG works --attributed-to Plato
```

Use JSON when you want to inspect or filter with `nu`. For repeatable checks,
save the command output first:

```bash
mkdir -p examples/debug/reader-guide-verify
just cli reader --catalog $CATALOG works --output json \
  > examples/debug/reader-guide-verify/works.json
nu -c 'open examples/debug/reader-guide-verify/works.json | get items | where author == Homer | select author title work_id'
```

Find a title or author:

```bash
nu -c 'open examples/debug/reader-guide-verify/works.json | get items | where work_id =~ "tlg0012.tlg002" | select author title work_id'
```

```bash
nu -c 'open examples/debug/reader-guide-verify/works.json | get items | where author =~ "Cicero" | select author title work_id | first 10'
```

## Read A Text

The most reliable reading path is canonical/catalog-native addressing:
discover a `work_id` or stored `cts_work_urn` with `reader works`, list its
contents, then read an exact segment. Friendly citation shorthand is useful
where aliases exist, but it is not the primary contract.

Aliases are catalog-local: if `reader aliases` lists an alias, its target is
expected to resolve inside the current catalog.

List the first segments of a work:

```bash
just cli reader --catalog $CATALOG \
  contents urn:cts:greekLit:tlg0012.tlg002 --limit 5
```

List a window around a known citation:

```bash
just cli reader --catalog $CATALOG \
  contents urn:cts:greekLit:tlg0012.tlg002 --around 3.74 --radius 5
```

Show one exact segment by CTS address:

```bash
just cli reader --catalog $CATALOG \
  show urn:cts:greekLit:tlg0012.tlg002:3.74
```

Show one segment using work plus `--segment`:

```bash
just cli reader --catalog $CATALOG \
  show urn:cts:greekLit:tlg0012.tlg002 --segment 3.74
```

JSON `show` output includes adjacent segment pointers. Sanskrit segment JSON
also includes additive display layers while keeping `text` as the stored source
text:

```bash
just cli reader --catalog examples/debug/reader_sanskrit_full_curated_current/catalog.duckdb \
  show langnet:reader:sanskrit_dcs:dcs_250 --segment 386927 --output json
```

When a corpus stores an internal `work_id` plus a separate `cts_work_urn`, the
CTS work URN is still accepted by `contents` and by `show ... --segment`.

Resolve a dictionary-style shorthand when aliases exist:

```bash
just cli reader --catalog $CATALOG \
  resolve-address "Od. 3.74"
```

The address returned by `resolve-address` can then be passed to `show`.

## Inspect Metadata Quality

The fastest metadata audit starts by enumerating all works and grouping the
visible author strings:

```bash
just cli reader --catalog $CATALOG works --output json \
  > examples/debug/reader-guide-verify/works.json
nu -c 'open examples/debug/reader-guide-verify/works.json | get items | group-by author | transpose author rows | each {|r| {author: $r.author, count: ($r.rows | length)}} | sort-by count --reverse | first 30'
```

Find suspicious author labels:

```bash
nu -c 'open examples/debug/reader-guide-verify/works.json | get items | where author =~ "(?i)unknown|anonym|unattributed|ps\\.|pseudo|\\(ps\\.\\)" | select collection_id author title source_id | first 80'
```

Interpret the result carefully:

- `Anonymous` is the reader-facing canonical display for anonymous works,
  including source authority labels such as digilibLT `Anonymus`.
- `Anonymi ...`, `Pseudo-*`, and `(Ps.)` can be source-faithful conventional
  labels when the work really is anonymous or pseudonymous.
- `Unknown` or `Unattributed` means we still lack a verified display author.
- Dangling labels such as `Pseudo-` are import artifacts and should be fixed at
  the import/authority layer.
- Researched corrections should be added as metadata overlays with evidence.

List curated metadata overlays:

```bash
just cli reader --catalog $CATALOG \
  overlays --match-value dcs_347
```

List attribution claims. These preserve ambiguous or competing traditions
without changing the canonical display author:

```bash
just cli reader --catalog $CATALOG attributions
```

Filter attribution claims by person or relation:

```bash
just cli reader --catalog $CATALOG \
  attributions --agent Chanakya --output json \
  > examples/debug/reader-guide-verify/chanakya-attributions.json
nu -c 'open examples/debug/reader-guide-verify/chanakya-attributions.json | get items | select relation_type agent match_value confidence'
```

Use attribution claims for cases like "possibly Aristotle or Avicenna." Use a
metadata overlay only when you are ready to change the reader-facing display
author.

You can also ask for works by an attribution agent directly from the works
catalog:

```bash
just cli reader --catalog examples/debug/reader_attributions_seed_verify/catalog.duckdb \
  works --attributed-to Chanakya
```

During the current build-out, the real-data attribution proof catalog is:

```bash
just cli reader --catalog examples/debug/reader_attributions_seed_verify/catalog.duckdb \
  attributions --match-value dcs_354
```

Review candidate overlays before accepting them:

```bash
just cli reader overlay-review --metadata-overlay-dir data/curated/reader_metadata --reviewer rule
```

Use the LLM reviewer for recommendations, then approve interactively:

```bash
just cli reader overlay-review \
  --metadata-overlay-dir data/curated/reader_metadata \
  --reviewer llm \
  --model openai:deepseek/deepseek-v4-flash \
  --apply
```

`--apply --yes` only promotes explicit `accept` recommendations. It leaves
`needs_review` records unchanged.

## Validate A Catalog

```bash
just cli reader --catalog $CATALOG validate
```

JSON validation is useful for checks:

```bash
mkdir -p examples/debug/reader-guide-verify

just cli reader --catalog $CATALOG summary
just cli reader --catalog $CATALOG validate --output json \
  > examples/debug/reader-guide-verify/validate.json
just cli reader --catalog $CATALOG coverage --output json
just cli reader --catalog $CATALOG contents urn:cts:greekLit:tlg0012.tlg002 --limit 5
just cli reader --catalog $CATALOG search-index validate \
  --index data/build/reader/search.lance \
  --output json
nu -c 'open examples/debug/reader-guide-verify/validate.json | get items | length'
```

An empty validation item list means the reader catalog passed the current QA
checks. The search-index check is required after the derived index has been
rebuilt for the catalog.

## First-Session Walkthrough

For someone encountering the library for the first time, the fastest useful
path is:

```bash
export CATALOG=examples/debug/reader_full_curated_current/catalog.duckdb
just cli reader --catalog $CATALOG summary
just cli reader --catalog $CATALOG works --author Homer
just cli reader --catalog $CATALOG contents urn:cts:greekLit:tlg0012.tlg002 --limit 10
just cli reader --catalog $CATALOG show urn:cts:greekLit:tlg0012.tlg002 --segment 1.1
```

If that catalog is not present yet, use a source-split audit catalog for the
same walkthrough while the unified build is being prepared:

```bash
export CATALOG=examples/debug/reader_classics_legacy_full_curated_current/catalog.duckdb
```

The same pattern works for any catalog:

1. `summary` confirms the catalog is present.
2. `works` answers what books and authors are available.
3. `contents <work_id-or-cts-work-urn>` shows the addressable segments inside a
   work.
4. `show <work_id-or-cts-work-urn> --segment <citation>` reads one exact
   segment.
5. `validate` checks whether the imported text/index currently passes QA.

## Operator Signoff

Before pointing another person at a catalog, run:

```bash
mkdir -p examples/debug/reader-guide-verify
just cli reader --catalog $CATALOG validate --output json \
  > examples/debug/reader-guide-verify/validate.json
just cli reader --catalog $CATALOG works --output json \
  > examples/debug/reader-guide-verify/works.json
nu -c 'open examples/debug/reader-guide-verify/validate.json | get items | length'
nu -c 'open examples/debug/reader-guide-verify/works.json | get items | where author =~ "(?i)unknown|unattributed|pseudo-$" | select language author title work_id | first 40'
```

Do not describe a catalog as ready for learners until validation is clean and
the suspicious-author scan has been reviewed.
