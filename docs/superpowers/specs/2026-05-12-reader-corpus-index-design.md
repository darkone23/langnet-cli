# Reader Corpus Index Design

## Purpose

LangNet needs a local, addressable corpus layer for exploring classical texts by collection, work, and segment. The first goal is not broad semantic query resolution. The first goal is to build a reproducible local text index that can answer:

- What texts are available on this machine?
- What addressable segments does each text contain?
- Given a stable address or exact alias plus citation path, can LangNet retrieve the text from disk-backed data?
- Can dictionary evidence that already contains a concrete CTS URN or exact citation be connected to local text when possible?

This supports the educational reader workflow: when a dictionary entry cites a passage, LangNet should eventually show the cited passage rather than only preserve the citation string.

## Scope

The MVP builds a reader catalog plus one local DuckDB artifact per imported book/work, rather than one database for an entire corpus. CTS URNs are treated as the preferred address format where available rather than as the only possible identity model.

In scope:

- Perseus canonical Greek and Latin TEI.
- Existing `data/build/cts_urn.duckdb` metadata as an input for Greek/Latin work and edition metadata.
- digilibLT TEI as a Latin supplement.
- PHI/TLG legacy text dumps under `~/Classics-Data/phi-latin` and `~/Classics-Data/tlg_e`.
- Sanskrit vault sources under `~/Classics-Data/sanskrit`, including GRETIL, VPC, DCS/CONLLU, local `texts/`, and translations.
- Curated, composed alias data for exact abbreviation and title matching.
- CLI exploration by collection, language, author, work, edition/book artifact, segment, address, and exact alias.
- Validation reports for missing targets, duplicate aliases, skipped files, parser errors, and per-book database problems.

Out of scope for the MVP:

- Fuzzy work resolution.
- Free-form "resolve this query" behavior.
- LLM interpretation or summarization of texts.
- Runtime reads from Diogenes, Sanskrit Heritage, or external web services.
- Full dictionary citation extraction for every source. Dictionary linking is a later consumer of this index.

## Data Sources

The local machine currently has several useful corpora:

- `~/perseus`: Perseus `canonical-greekLit` and `canonical-latinLit` TEI. These files often include `refsDecl`, `cRefPattern`, `refState`, edition URNs, and line/book citation nodes.
- `~/Classics-Data/phi-latin` and `~/Classics-Data/tlg_e`: PHI/TLG legacy text dumps with `.txt` and `.idt` files. These need a source-specific decoder. The first adapter can preserve coarse sections and source markers before attempting perfect PHI/TLG citation recovery.
- `~/Classics-Data/digiliblt`: Latin TEI files with rich text and page milestones.
- `~/Classics-Data/sanskrit`: GRETIL, VPC, DCS, translations, local OCR/split text folders, JSON token-line corpora, and CONLLU-derived data.

The existing `data/build/cts_urn.duckdb` remains valuable. The reader index should use it as metadata input, not replace it immediately.

## Address Model

CTS URNs are the model for stable, composable text addresses where they fit:

```text
urn:cts:greekLit:tlg0012.tlg002:3.74
urn:cts:latinLit:phi0959.phi006:1.1
```

For non-CTS sources, LangNet should mint stable local addresses with the same broad structure: collection, work, edition/source, and segment path. The exact syntax can be finalized during implementation, but it must be deterministic and source-backed.

Examples:

```text
langnet:reader:gretil:sa_kAlidAsa-raghuvaMza:1
langnet:reader:dcs:rigveda:chapter-0001:line-0001
```

Segments should preserve:

- canonical address, if available
- source-local address or citation path
- parent work
- parent edition/source
- segment kind, such as line, verse, paragraph, chapter, or page
- original text
- normalized text for lookup/display support

## Storage Layout

The storage layout should keep the global index small and make individual text artifacts easy to inspect, rebuild, move, or delete:

```text
data/build/reader/
  catalog.duckdb
  books/
    perseus/greekLit/tlg0012/tlg002/perseus-grc2.duckdb
    perseus/latinLit/phi0959/phi006/perseus-lat2.duckdb
    digiliblt/dlt000001.duckdb
    gretil/sa_kAlidAsa-raghuvaMza.duckdb
```

In this design, "book" means the smallest durable reader artifact LangNet imports as a standalone text database. For Perseus this is usually an edition/work file, even when the ancient work contains internal books such as `Odyssey` books 1-24. If a source already supplies a better standalone unit, an adapter may choose that source unit, but it must record the choice in catalog metadata.

## Catalog Schema

The catalog database at `data/build/reader/catalog.duckdb` should contain global discovery and routing tables:

- `collections`: corpus families such as `perseus`, `digiliblt`, `gretil`, `vpc`, `dcs`, `phi`, and `tlg`.
- `authors`: language-neutral author/person/group rows derived from source metadata where available.
- `works`: language-neutral work metadata, including language, author, title, source collection, source ID, optional CTS work URN, and display labels.
- `editions`: source edition/version metadata, optional CTS edition URN, source file path, and language.
- `book_artifacts`: one row per per-book DuckDB file, including work ID, edition ID, source path, artifact path, segment count, token count, adapter name/version, source hash, and build status.
- `aliases`: built alias rows loaded from curated files and discovered source metadata.
- `build_sources`: source file, adapter name, adapter version, file hash, import status, row counts, artifact path, and error details.

The schema should support a work index or metadata page without requiring AI-generated prose. A summary can be computed from structured metadata: collection, title, author, language, edition count, segment count, available address schemes, source paths, and known aliases.

## Book Database Schema

Each per-book DuckDB file should contain the text-bearing tables for one imported reader artifact:

- `book_metadata`: title, author, language, collection, work ID, edition ID, source path, source hash, adapter name/version, and optional CTS work/edition URNs.
- `segments`: retrievable text units with segment ID, segment kind, citation path, text, normalized text, and ordering fields.
- `segment_addresses`: one-to-many addresses for each segment, including CTS URNs, LangNet URNs, source IDs, and citation strings.
- `tokens`: optional source-provided token rows, especially for Sanskrit JSON, GRETIL, and DCS/CONLLU inputs.
- `local_aliases`: optional aliases that are specific to this book artifact and are copied into the catalog during build.

The catalog routes a lookup to the correct book database. The book database serves the actual text, segment addresses, and token rows.

For direct segment retrieval, the catalog should only identify the relevant artifact. After that, a request such as "line 800 of this book" should be a lookup against that book's DuckDB file, not a scan of a corpus-wide segment table.

## Curated Aliases

Aliases and abbreviations should be project data, not Python conditionals. They should live in many small composed YAML files under:

```text
data/curated/reader_aliases/
  greek/
  latin/
  sanskrit/
  sources/
```

Example file:

```yaml
aliases:
  - alias: "Od."
    language: "grc"
    kind: "work_abbreviation"
    target: "urn:cts:greekLit:tlg0012.tlg002"
    display: "Homer, Odyssey"
    sources: ["lsj", "diogenes", "manual"]

  - alias: "Śivasūtra"
    language: "san"
    kind: "work_title"
    target: "langnet:reader:sanskrit:panini:sivasutra"
    display: "Pāṇini, Śivasūtra"
    sources: ["manual"]
```

The builder composes all YAML files into the catalog `aliases` table. Manual curated aliases supplement source-discovered aliases. Conflicts should be reported rather than silently hidden.

The initial resolver should handle exact matches only:

- exact CTS URN
- exact LangNet reader URN
- exact alias plus citation path, such as `Od. 3.74`
- exact title alias, such as `Śivasūtra`, only if curated or imported as a direct metadata hit

No fuzzy matching is promised in the MVP.

## CLI Surface

The first CLI surface should be small and inspectable:

```bash
just cli reader build
just cli reader build-book Od.
just cli reader collections
just cli reader authors --lang grc
just cli reader works --lang grc
just cli reader works --author Homer
just cli reader summary Od.
just cli reader contents Od.
just cli reader show urn:cts:greekLit:tlg0012.tlg002:3.74
just cli reader show Od. --segment 3.74
just cli reader resolve-address "Od. 3.74"
just cli reader aliases --query Od
just cli reader alias-check
```

For Sanskrit, the first version should support direct metadata and alias hits rather than fuzzy search:

```bash
just cli reader summary "Śivasūtra"
just cli reader segments "Śivasūtra"
```

The CLI should make failure modes explicit. If an alias is ambiguous, missing, or points to a work without imported segments, the command should say so directly.

Enumeration commands such as `collections`, `authors`, `works`, `summary`, and `contents` should read from `catalog.duckdb`. Retrieval commands such as `show` and `segments` should resolve through `catalog.duckdb`, open only the relevant per-book database, and then read the text-bearing rows from that book database.

## Example Reference Flow

Dictionary evidence may contain a citation like:

```text
ψυχὰς παρθέμενοι ... Od. 3.74, 9.255
```

The reader index should make the deterministic parts possible:

1. `Od.` resolves through curated or imported aliases to Homer, Odyssey.
2. The Odyssey work maps to `urn:cts:greekLit:tlg0012.tlg002` when present.
3. `3.74` maps to an imported line segment if the chosen edition has that segment.
4. The CLI can show the segment text and nearby context.
5. `9.255` follows the same path.

The dictionary parser that extracts `Od. 3.74, 9.255` from LSJ/Diogenes evidence is a separate later task. This design only ensures the reader index can answer once a concrete reference is available.

## Import Adapters

Adapters should be independent and testable:

- `perseus_tei`: parse CTS-capable TEI, editions, `refsDecl`, `div type="textpart"`, lines, paragraphs, and citation paths.
- `digiliblt_tei`: parse TEI header metadata, paragraphs, page milestones, and source IDs.
- `sanskrit_json`: parse GRETIL/VPC-style JSON line/token corpora.
- `sanskrit_text`: parse plain text, split text, OCR text, and translation files into coarse line/paragraph segments with source-backed addresses.
- `dcs_conllu`: parse DCS metadata, chapter files, line IDs, tokens, lemma IDs, occurrence IDs, and unsandhied forms where available.
- `phi_tlg_legacy`: parse PHI/TLG `.txt`/`.idt` dumps into source-backed sections and segments. Fine-grained citation recovery can improve over time, but the files should still be enumerable and retrievable in the first complete corpus pass.

Each adapter should return normalized intermediate records rather than write arbitrary SQL directly. The builder owns database writes, validation, stats, and catalog registration. Rebuilding one book should not require rebuilding the whole corpus.

## Validation

The build should report:

- duplicate aliases that point to different targets
- aliases that point to missing works
- works without segments
- segments without addresses
- catalog book artifact rows that point to missing DuckDB files
- per-book DuckDB files that are missing required tables
- duplicate addresses
- edition/work mismatches
- skipped files
- parser errors
- source files that produced no importable content

Validation should be available as part of `reader build` and independently through `reader validate` or `reader alias-check`.

## Testing

Tests should use small fixtures, not the full local corpora:

- minimal Perseus CTS TEI with book and line references
- minimal digilibLT-style TEI with paragraphs and page milestones
- minimal Sanskrit JSON token-line fixture
- minimal alias YAML files with both valid and conflicting aliases
- a DuckDB integration test that verifies catalog lookup, per-book database opening, address lookup, and exact alias resolution

The local full corpus can be used for manual verification through `just cli reader build`, but unit tests must remain fast and reproducible.

## Open Implementation Choices

- Final LangNet reader URN syntax for non-CTS sources.
- Whether the alias YAML parser uses an existing dependency or a small constrained YAML subset.
- Exact artifact boundary for sources where "book", "work", "edition", and file do not line up cleanly.
- Whether `catalog.duckdb` should embed copied CTS metadata or attach/read `cts_urn.duckdb` during build only.
- How much nearby context `reader show` should return by default.
- Whether token rows are built in the first implementation pass or added after segment retrieval works.
