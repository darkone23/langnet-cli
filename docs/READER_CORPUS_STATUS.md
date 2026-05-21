# Reader Corpus Status

This document summarizes the current state of the reader corpus work: what is
usable, how to explore it, what has been verified, and what remains pending.

## Goal

The reader corpus is a local, cleaned, DuckDB-indexed library of classical
texts. It should answer learner-facing catalog questions without requiring
knowledge of import sources:

- What books do we have?
- What authors do we have?
- What works are by, or attributed to, a person?
- What is inside this work?
- Can I read this exact segment/address?

Import sources remain available for audit and debugging, but the normal reader
interface is source-agnostic.

## Data Build Target

The product target is one unified reader catalog:

```bash
data/build/reader/catalog.duckdb
```

In older handoff notes, local development often used:

```bash
examples/debug/reader_full_curated_current/catalog.duckdb
```

Treat that as a historical/debug comparison path. Normal current commands should
use `data/build/reader/catalog.duckdb` unless an operator is explicitly
validating a debug artifact. Build the unified catalog from the local source
roots that are available:
PHI Latin, TLG Greek, Perseus, digilibLT, and Sanskrit/DCS. Include the curated
repo layers for aliases, display metadata, attribution claims, contained works,
and work maps. Concrete build and smoke-test commands are in
`docs/READER_DATA_BUILD.md`.

The source-split `reader_classics`, `reader_sanskrit`, `reader_perseus`, and
`reader_digiliblt` catalogs are generated audit artifacts. They are useful for
importer debugging and source-family validation, but they are not the catalog
shape the product should expose.

After parser/importer changes, rebuild the catalog. After any catalog rebuild,
rebuild the derived Lance search index before validating search behavior.

## Current CLI

Use commands from the project root:

```bash
just cli reader --catalog <catalog.duckdb> summary
just cli reader catalogs --output json
just cli reader --catalog <catalog.duckdb> author-sections --language lat
just cli reader --catalog <catalog.duckdb> authors --language lat --section V --limit 50
just cli reader --catalog <catalog.duckdb> works
just cli reader --catalog <catalog.duckdb> works --query homer --limit 50
just cli reader --catalog <catalog.duckdb> works --language lat --author-id phi0690
just cli reader --catalog <catalog.duckdb> works --author Plato
just cli reader --catalog <catalog.duckdb> works --attributed-to Plato
just cli reader --catalog <catalog.duckdb> facets --language grc --output json
just cli reader --catalog <catalog.duckdb> groups --language lat --output json
just cli reader --catalog <catalog.duckdb> tags --language san --output json
just cli reader --catalog <catalog.duckdb> author-facets --output json
just cli reader --catalog <catalog.duckdb> shelves --language san --sample-limit 3 --output json
just cli reader --catalog <catalog.duckdb> search "λόγος" --index data/build/reader/search.lance --language grc --mode fuzzy
just cli reader --catalog <catalog.duckdb> search-index validate --index data/build/reader/search.lance --output json
just cli reader --catalog <catalog.duckdb> contents <work_id>
just cli reader --catalog <catalog.duckdb> contents <work_id> --around <citation> --radius 20
just cli reader --catalog <catalog.duckdb> show <work_id> --segment <citation>
just cli reader --catalog <catalog.duckdb> resolve-address "Od. 3.74"
just cli reader --catalog <catalog.duckdb> validate
```

`reader works` pretty output includes the addressable `work_id` in brackets.
JSON output is available with `--output json` and is intended to be filtered
with `nu`.

The web-facing JSON contract is documented in `docs/READER_WEB_CONTRACT.md`.

## Current Catalogs

Current verified development catalogs live under `examples/debug/`.
These are generated audit artifacts, not durable public data or the product
catalog target.

- `reader_perseus_full_curated_current/catalog.duckdb`
  - 1,223 works, 2,298 artifacts, 950,141 segments.
  - Strict validation passes with 0 issues.
  - No unknown authors after Appendix Vergiliana overlays.
- `reader_sanskrit_full_curated_current/catalog.duckdb`
  - 977 works/artifacts, 3,319,944 segments, 26,382,642 tokens.
  - 977 physical book DuckDB files; output size is about 2.3G.
  - Strict validation passes with 0 issues after the refreshed curated rebuild.
  - Source errors: 0.
  - 564 works remain `Unknown`; these are the next metadata-enrichment target.
  - Accepted attribution claims are present at claim level: 26 attributed
    authors, 4 traditional authors, 3 possible authors, 2 commentators, 2
    compilers, and 1 redactor.
- `reader_digiliblt_anonymous_overlay_verify/catalog.duckdb`
  - 390 works/artifacts, 112,104 segments.
  - Strict validation passes with 0 issues.
  - `Unattributed` and source `Anonymus` display gaps are resolved to
    reader-facing canonical forms.
- `reader_classics_legacy_full_curated_current/catalog.duckdb`
  - 7,836 works/artifacts, 10,591,345 segments, 87,197,666 tokens.
  - 2,196 physical book DuckDB files shared by source text file; output size is
    about 6.6G.
  - Strict validation passes with 0 issues after catalog-local alias filtering.
  - Source errors: 0.
  - PHI expected 1,235 IDT works; 1,209 imported with segment text, and 26
    zero-segment IDT rows were skipped.
  - TLG expected and imported 6,627 works.
  - One display author is `Anonymous`
    (`urn:cts:greekLit:tlg4005.tlg001`, Euclid book XV tradition); this is an
    accepted reviewed label for now.

## Metadata Policy

Display metadata and scholarly attribution history are separate.

Use `data/curated/reader_metadata/` for accepted display fields:

- `author`
- `author_id`
- `title`
- `language`
- `cts_work_urn`

Use `data/curated/reader_attributions/` for evidence-backed relationships that
must remain queryable without necessarily changing display metadata:

- `attributed_author`
- `possible_author`
- `traditional_author`
- `misattributed_author`
- `translator`
- `commentator`
- `editor`
- `redactor`
- `compiler`

For example, Arthaśāstra can be found with both `--attributed-to Kauṭilya` and
`--attributed-to Chanakya` in the attribution proof catalog even when display
author remains unresolved.

## Duplicate Policy

Not every duplicate-looking record is bad.

Accidental duplicates should be collapsed or overwritten during import:

- the same source file copied into two scanned paths;
- two inputs that produce the same `work_id`, edition id, and segment ids;
- repeated parsed DCS fixture/source files with identical canonical ids.

Scholarly duplicates should be preserved explicitly:

- multiple editions or translations of the same work;
- multiple witnesses of a work from different source corpora;
- source-faithful pseudonymous or anonymous traditions;
- competing authorship attributions.

The catalog policy is:

- `work_id` is the canonical work-level identity when we are confident.
- `edition_id` and artifact rows preserve edition/witness/import differences.
- exact segment addresses must resolve unambiguously.
- physical book DB reuse is an implementation detail; it must not merge works
  or hide distinct editions in the learner-facing catalog.
- ambiguous authorship belongs in attribution claims, not as lossy display text.
- duplicate display-author names are audit signals, not automatic merge keys.
  If one display name maps to more than one authority id, preserve the
  authority ids and add a disambiguated display/index label or a researched
  canonicalization overlay.
- the native author index disambiguates homonyms with the best deterministic
  label available. TLG canon author-name descriptors are preferred when they
  clarify identity, then TLG canon categories are used, so examples include
  `Georgius (Acropolites)`, `Plato (Phil.)` vs. `Plato (Comic.)`,
  `Pausanias (Perieg.)`, and `Patrocles (Hist.)`. Researched geographic or
  identity labels such as `Philoxenus Cytherius` should be promoted through
  accepted `author_id` metadata overlays.
- repeated titles such as `Fragmenta` are expected. A title alone is not a
  work identity; learner-facing displays should disambiguate by author,
  language, work id, and CTS URN where available.
- PHI/TLG support files such as `doccan1` and `doccan2` are source metadata,
  not reader works. They can provide canon cross-checks and category hints,
  but must not appear in `reader works`.

## Citation Policy

Curated evidence must use durable citations:

- durable web URLs;
- portable source-root references such as `sanskrit-dcs:data/...`,
  `perseus:canonical-latinLit/...`, or `digiliblt:dlt000616.xml`.

Do not store host-local paths, `Classics-Data`, or `examples/debug` paths in
curated metadata files. Debug paths belong only in operator notes.

## Verified Tooling Behavior

Catalog-level questions are answered from the catalog DuckDB.

- `reader works --author <name>` searches display authors.
- `reader works --attributed-to <name>` searches display authors plus accepted
  attribution claims, including translator claims such as Jerome for the
  Vulgate and the traditional seventy-two translators for Septuagint rows.
- Non-pseudo author searches exclude `Pseudo-*` display authors unless the
  query itself asks for a pseudo-author.
- Verified example: `--author Plutarch` excludes `Pseudo-Plutarch`, while
  `--author Pseudo-Plutarch` returns the pseudo-Plutarchan rows explicitly.
- The priority addressing surface is stable work IDs, CTS URNs where available,
  `contents`, and exact segment reads. Friendly shorthand such as `Od. 3.74` is
  useful but secondary to canonical/catalog-native addresses.
- Exact work references now resolve by alias, `work_id`, or `cts_work_urn`.
  This means `contents <cts_work_urn>` and `show <cts_work_urn> --segment <path>`
  work even when the stored work id is an internal `langnet:reader:...` id.
- `reader work <work-ref>` returns exact work metadata by alias, `work_id`, or
  `cts_work_urn`.
- `reader works` and `reader authors` support `--query`, `--limit`, and
  `--cursor` for web and learner-facing browsing.
- `reader author-sections` returns a complete author table of contents by
  source-language section for Latin, Greek, and Sanskrit.
- `reader authors --section <key>` returns source-agnostic author rows for a
  selected section, including display names, index names, native names where
  available, section keys, and stable author selectors.
- `reader works --author-id <selector>` returns all works for an author index
  selector without requiring free-text author matching.
- Accepted contained works participate in catalog-level work discovery and
  author-selector browsing. Verified example: the contained `Bhagavadgītā`
  appears under `Vyāsa` with selector `langnet:reader:author:san:vyasa`.
- `reader contents` supports `--cursor`, `--from`, `--around`, and
  `--char-budget` windows. `--char-budget` caps returned text characters while
  preserving at least one segment, so chapter-sized segments do not produce
  oversized reader pages.
- JSON `reader show` responses include next/previous segment pointers.
- Sanskrit segment JSON includes additive display fields for transliteration
  and Devanagari where conversion is available. The stored `text` field remains
  unchanged.
- Catalog builds only register aliases that resolve to a `work_id` or
  `cts_work_urn` present in that catalog. Validation reports any remaining
  unresolved alias target as a catalog error.
- `resolve-address "Od. 3.74"` resolves the alias before reading the targeted
  book DB.
- Friendly `show` addresses such as `show "Odyssey book 1 line 8"` follow the
  same catalog-first path.
- Direct `langnet:reader:...` segment addresses route to the addressed work's
  artifact from catalog metadata rather than probing unrelated book DBs.
- Direct full CTS segment URNs can be translated to the stored internal segment
  address when the catalog row has the corresponding `cts_work_urn`.
- PHI/TLG legacy builds now populate `cts_work_urn` from clean IDT author/work
  ids: TLG works map to `urn:cts:greekLit:tlgNNNN.tlgMMM`, and PHI works map to
  `urn:cts:latinLit:phiNNNN.phiMMM`.
- Validation flags clean PHI/TLG legacy rows that should have this
  CTS-equivalent work URN but do not.
- PHI/TLG legacy imports now keep one catalog artifact per work, but share the
  physical book DuckDB by source text file. This avoids thousands of tiny
  per-work DuckDB files while preserving source-agnostic work enumeration and
  exact segment lookup.
- TLG canon files are preserved as source metadata for validation. The importer
  extracts canon author names, work titles, and category values such as
  `Epic.`, `Hist.`, or `Biogr. et Phil.` for later classifier input, while
  excluding the canon documents themselves from reader work enumeration.
- `reader duplicate-audit --kind authors` reports display-author names that map
  to multiple authority ids. It intentionally does not report one author with
  many works.
- `reader duplicate-audit --kind titles` reports repeated title displays and
  includes a suggested policy. Most high-count Greek title duplicates are
  fragment/testimonium style records that should be preserved and
  disambiguated by author.
- `reader classification-export` emits CSV scaffolding for bulk enrichment,
  including `classification_category`, period/date range, authorship status,
  popularity score, and notes columns.

Book DBs should only be opened when segment text is actually needed.

## Corpus Signoff Checklist

A reader catalog is ready to hand to a learner or downstream UI only after the
following checks pass against the exact catalog path being documented:

```bash
export CATALOG=<catalog.duckdb>
just cli reader --catalog $CATALOG summary
just cli reader --catalog $CATALOG validate --output json \
  > examples/debug/reader-audit/current_validate.json
nu -c 'open examples/debug/reader-audit/current_validate.json | get items | length'
just cli reader --catalog $CATALOG coverage --output json
just cli reader --catalog $CATALOG works --output json \
  > examples/debug/reader-audit/current_works.json
just cli reader --catalog $CATALOG contents urn:cts:greekLit:tlg0012.tlg002 --limit 5
just cli reader --catalog $CATALOG search-index validate \
  --index data/build/reader/search.lance \
  --output json
```

For long corpus imports, pass `--progress-every <N>` to `cli-databuild reader` to
print parsed source, artifact, segment, and latest-source counts every `N`
parsed books.

The validation issue count must be `0`, or every issue must be documented as an
accepted exception with a follow-up task.

Catalog-level signoff checks:

- `works` can answer "what books do we have?" without import-source filters.
- `works --author <name>` returns display-author matches and keeps
  pseudo-author labels separate.
- `works --attributed-to <name>` includes accepted attribution claims.
- `aliases` contains only targets addressable in this catalog.
- suspicious display authors such as `Unknown`, `Unattributed`, dangling
  `Pseudo-`, or source-local anonymous labels have been reviewed.
- source errors and zero-segment artifacts are either zero or documented.

Reading signoff checks:

- `contents <work_id>` works for representative Latin, Greek, and Sanskrit
  works.
- `contents <cts_work_urn>` works when a CTS work URN is present.
- `show <work_id> --segment <citation>` returns the expected segment text.
- `show <cts_work_urn> --segment <citation>` works for a representative PHI/TLG
  legacy work with a generated CTS URN.
- physical book DB reuse does not change address resolution: each catalog work
  still resolves only its own segments.
- missing `show <work> --segment <citation>` requests return quickly with a
  null segment rather than scanning unrelated book DBs.

Documentation signoff checks:

- `docs/READER_CLI_BEGINNER_GUIDE.md` commands have been run against the current
  catalog or updated to point at a catalog that exists.
- any generated audit JSON remains under `examples/debug/reader-audit/`.
- curated YAML evidence contains durable citations only, never host-local paths
  or debug files.

## Deferred Chronology Layer

We do not yet have normalized work age/date metadata.

The planned approach is author chronology first, then per-work chronology for
cases where author chronology would be misleading:

- spurious or pseudo works;
- anonymous works;
- composite/traditional corpora;
- works whose date materially differs from the author's floruit.

Chronology should be represented as a separate catalog layer with date kind,
range, label, confidence, status, and evidence. Do not conflate edition
publication dates with text composition dates.

## Next Checkpoints

1. Continue Sanskrit metadata enrichment for the remaining `Unknown` works,
   prioritizing high-value DCS and named-title cases.
2. Validate the beginner guide against the final current catalogs.
3. Decide whether skipped PHI zero-segment IDT rows should become explicit
   catalog exceptions or remain excluded from learner-facing enumeration.
4. Add the chronology candidate/export layer after the import and metadata
   quality checkpoint is stable.
