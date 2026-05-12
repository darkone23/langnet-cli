# Reader Corpus Index Design

## Purpose

LangNet needs a local, addressable corpus layer for exploring classical texts by collection, work, and segment. The first goal is not broad semantic query resolution. The first goal is to build a reproducible local text index that can answer:

- What texts are available on this machine?
- What addressable segments does each text contain?
- Given a stable address or exact alias plus citation path, can LangNet retrieve the text from disk-backed data?
- Can dictionary evidence that already contains a concrete CTS URN or exact citation be connected to local text when possible?

This supports the educational reader workflow: when a dictionary entry cites a passage, LangNet should eventually show the cited passage rather than only preserve the citation string.

## Scope

The MVP builds a new offline reader artifact at `data/build/reader.duckdb`. It imports local corpora into a language-neutral schema, with CTS URNs treated as the preferred address format where available rather than as the only possible identity model.

In scope:

- Perseus canonical Greek and Latin TEI.
- Existing `data/build/cts_urn.duckdb` metadata as an input for Greek/Latin work and edition metadata.
- digilibLT TEI as a Latin supplement.
- Sanskrit vault sources under `~/Classics-Data/sanskrit`, especially structured JSON and DCS/CONLLU material.
- Curated, composed alias data for exact abbreviation and title matching.
- CLI exploration by collection, work, segment, address, and exact alias.
- Validation reports for missing targets, duplicate aliases, skipped files, and parser errors.

Out of scope for the MVP:

- Fuzzy work resolution.
- Free-form "resolve this query" behavior.
- LLM interpretation or summarization of texts.
- Runtime reads from Diogenes, Sanskrit Heritage, or external web services.
- Full dictionary citation extraction for every source. Dictionary linking is a later consumer of this index.

## Data Sources

The local machine currently has several useful corpora:

- `~/perseus`: Perseus `canonical-greekLit` and `canonical-latinLit` TEI. These files often include `refsDecl`, `cRefPattern`, `refState`, edition URNs, and line/book citation nodes.
- `~/Classics-Data/phi-latin` and `~/Classics-Data/tlg_e`: PHI/TLG legacy text dumps with `.txt` and `.idt` files. These need a source-specific decoder and should follow after the TEI and Sanskrit adapters.
- `~/Classics-Data/digiliblt`: Latin TEI files with rich text and page milestones.
- `~/Classics-Data/sanskrit`: GRETIL, VPC, DCS, translations, JSON token-line corpora, and CONLLU-derived data.

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

## Schema

The reader DuckDB artifact should contain these core tables:

- `collections`: corpus families such as `perseus`, `digiliblt`, `gretil`, `vpc`, `dcs`, `phi`, and `tlg`.
- `works`: language-neutral work metadata, including language, author, title, source collection, source ID, optional CTS work URN, and display labels.
- `editions`: source edition/version metadata, optional CTS edition URN, source file path, and language.
- `segments`: retrievable text units with segment ID, work ID, edition ID, segment kind, citation path, text, normalized text, and ordering fields.
- `segment_addresses`: one-to-many addresses for each segment, including CTS URNs, LangNet URNs, source IDs, and citation strings.
- `aliases`: built alias rows loaded from curated files and discovered source metadata.
- `tokens`: optional source-provided token rows, especially for Sanskrit JSON, GRETIL, and DCS/CONLLU inputs.
- `build_sources`: source file, adapter name, adapter version, file hash, import status, row counts, and error details.

The schema should support a work index or metadata page without requiring AI-generated prose. A summary can be computed from structured metadata: collection, title, author, language, edition count, segment count, available address schemes, source paths, and known aliases.

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

The builder composes all YAML files into the `aliases` table. Manual curated aliases supplement source-discovered aliases. Conflicts should be reported rather than silently hidden.

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
just cli reader collections
just cli reader works --lang grc
just cli reader summary Od.
just cli reader show urn:cts:greekLit:tlg0012.tlg002:3.74
just cli reader resolve-address "Od. 3.74"
just cli reader aliases --query Od
just cli reader alias-check
```

For Sanskrit, the first version should support direct metadata and alias hits rather than fuzzy search:

```bash
just cli reader summary "Śivasūtra"
just cli reader segments <exact-work-id-or-alias>
```

The CLI should make failure modes explicit. If an alias is ambiguous, missing, or points to a work without imported segments, the command should say so directly.

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
- `dcs_conllu`: parse DCS metadata, chapter files, line IDs, tokens, lemma IDs, occurrence IDs, and unsandhied forms where available.
- `phi_tlg_legacy`: later adapter for PHI/TLG text dumps after a clear decoder boundary is designed.

Each adapter should return normalized intermediate records rather than write arbitrary SQL directly. The builder owns database writes, validation, and stats.

## Validation

The build should report:

- duplicate aliases that point to different targets
- aliases that point to missing works
- works without segments
- segments without addresses
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
- a DuckDB integration test that verifies address lookup and exact alias resolution

The local full corpus can be used for manual verification through `just cli reader build`, but unit tests must remain fast and reproducible.

## Open Implementation Choices

- Final LangNet reader URN syntax for non-CTS sources.
- Whether the alias YAML parser uses an existing dependency or a small constrained YAML subset.
- Whether `reader.duckdb` should embed copied CTS metadata or attach/read `cts_urn.duckdb` during build only.
- How much nearby context `reader show` should return by default.
- Whether token rows are built in the first implementation pass or added after segment retrieval works.
