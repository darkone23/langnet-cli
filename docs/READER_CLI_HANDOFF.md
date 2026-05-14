# Reader CLI Handoff

Date: 2026-05-14

This document is a practical handoff for someone encountering the LangNet
reader corpus CLI today. The current state is suitable for an informed early
user or corpus operator. It is not yet a polished end-user release or final web
UI.

The reader CLI explores local DuckDB catalogs of cleaned/imported texts. It
does not fetch external texts at read time.

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
- Friendly dictionary shorthand is secondary; canonical `work_id` and
  `cts_work_urn` are the reliable path.
- Citation schemes are source-native. DCS Sanskrit texts often use sentence IDs
  such as `386927`, not always book/line numbering.
- Catalogs under `examples/debug/` are generated development artifacts, not
  durable packaged data.

## Current Catalogs

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

Perseus and digilibLT audit catalogs also exist:

```bash
examples/debug/reader_perseus_full_curated_current/catalog.duckdb
examples/debug/reader_digiliblt_anonymous_overlay_verify/catalog.duckdb
```

## First Commands

Run from the project root.

```bash
export CATALOG=examples/debug/reader_classics_legacy_full_curated_current/catalog.duckdb

just cli reader --catalog $CATALOG summary
just cli reader --catalog $CATALOG works --author Homer
just cli reader --catalog $CATALOG contents urn:cts:greekLit:tlg0012.tlg002 --limit 5
just cli reader --catalog $CATALOG show urn:cts:greekLit:tlg0012.tlg002 --segment 1.1
```

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
