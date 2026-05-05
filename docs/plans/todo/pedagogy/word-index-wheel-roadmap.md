# Word Index, Wheel, and Neighborhood Roadmap

**Status:** ⏳ TODO  
**Feature Area:** pedagogy  
**Owner Roles:** @architect for contract and source model, @sleuth for Diogenes navigation research, @coder for implementation, @auditor for schema/reliability review

## Goal

Expose a reliable index of known dictionary hits for every supported language,
then use that index to power learner-facing "wheel of words" and "word
neighborhood" experiences.

This should make the CLI more self-describing and more exploratory:

- list all locally known headword hits by language/source;
- page through the index deterministically;
- ask for entries around a term;
- request a random or seeded wheel of study terms;
- optionally attach a small neighborhood to `encounter` results without changing
  the meaning of the primary lookup.

## Research Findings

The current codebase already has several enumerable sources:

- **Sanskrit / CDSL**: `data/build/cdsl_<dict>.duckdb` is built by
  `src/langnet/databuild/cdsl.py`. It contains `entries` and `headwords`
  tables. `headwords` has `dict_id`, `key`, `key_normalized`, `lnum`, `hom`,
  `is_primary`, and `search_key`. `entries` carries source body/plain text and
  page metadata. This is the strongest Sanskrit headword index.
- **Sanskrit / DICO**: `data/build/lex_dico.duckdb` is built from Heritage DICO
  HTML by `src/langnet/databuild/dico.py`. It has `entries_fr` with
  `entry_id`, `headword_deva`, `headword_roma`, `headword_norm`, `source_page`,
  and `plain_text`. This is already suitable for Devanagari/romanized display
  and source-backed lookup.
- **Latin / Gaffiot**: `data/build/lex_gaffiot.duckdb` is built by
  `src/langnet/databuild/gaffiot.py`. It has `entries_fr` with `entry_id`,
  `headword_raw`, `headword_norm`, `variant_num`, and `plain_text`. This is
  immediately enumerable.
- **Greek and Latin / Diogenes**: the current Diogenes client supports Greek
  `word_list` lookup and Greek/Latin parse lookup in
  `src/langnet/diogenes/client.py`. The staged Diogenes parser also notices
  `prevEntry(...)` JavaScript in dictionary pages. This suggests two paths:
  on-demand neighborhoods from returned dictionary pages now, and a full
  Diogenes enumeration crawler after confirming the exact next/previous CGI
  contract.
- **Whitaker's Words and CLTK**: these are useful supplemental sources but are
  not yet represented as stable local all-headword DuckDB indexes. Treat them as
  later candidates unless we add dedicated builders.

The project already has public self-description commands for languages and tools
via `src/langnet/tool_catalog.py`. The word index should follow the same pattern:
schema-backed JSON first, terse text display second.

## Definition Of "Known Hit"

For the first implementation, a known hit is a locally enumerable dictionary
headword or dictionary entry that LangNet can use as an `encounter` query.

This intentionally excludes:

- every theoretically possible inflected form;
- every morphology analyzer parse output;
- unverified generated terms;
- live network-only terms that are not materialized in a local index.

Later work can add a second `kind=form` layer for morphology-generated forms,
but the first contract should remain headword/entry based.

## Proposed JSON Contract

Add schema version `langnet.word_index.v1`.

Top-level shape:

```json
{
  "schema_version": "langnet.word_index.v1",
  "request": {
    "language": "san",
    "source": "all",
    "mode": "list|neighborhood|wheel",
    "query": "dharma",
    "limit": 25,
    "cursor": null
  },
  "sources": [
    {
      "source": "cdsl",
      "language": "san",
      "dictionary": "mw",
      "available": true,
      "entry_count": 12345
    }
  ],
  "items": [
    {
      "language": "san",
      "source": "cdsl",
      "dictionary": "mw",
      "kind": "headword",
      "canonical_name": "धर्म",
      "lookup": "dharma",
      "display": {
        "primary": "धर्म",
        "transliteration": "dharma",
        "source_key": "Darma"
      },
      "sort_key": "darma",
      "source_ref": "cdsl:mw:100000",
      "encounter": {
        "language": "san",
        "q": "dharma",
        "dictionary": "cdsl"
      }
    }
  ],
  "neighborhood": {
    "anchor": "dharma",
    "before": [],
    "after": [],
    "radius": 10
  },
  "pagination": {
    "next_cursor": "opaque",
    "prev_cursor": null
  },
  "warnings": []
}
```

The item shape should deliberately mirror the recent `word-of-day` canonical
projection: `canonical_name` is easy for a web frontend, while `display` preserves
script/transliteration/source-key detail.

## Proposed CLI Surface

Keep this as ordinary CLI JSON, not a service gateway.

```bash
just cli word-index sources --output json
just cli word-index list san --source all --limit 50 --output json
just cli word-index list lat --source gaffiot --prefix lu --limit 25 --output json
just cli word-index neighborhood grc logos --source diogenes --radius 10 --output json
just cli word-index wheel all --count 12 --seed daily-2026-05-05 --output json
```

Optional later integration:

```bash
just cli encounter san dharma all --neighbors 6 --output json
```

If added to `encounter`, neighborhoods should be optional and compact. The
primary encounter result must remain source evidence for the requested term, not
an exploratory page.

## Source Adapters

Create a small word-index layer rather than putting SQL directly in `cli.py`:

```text
src/langnet/word_index/
  __init__.py
  models.py
  service.py
  sources.py
  cdsl.py
  dico.py
  gaffiot.py
  diogenes.py
```

Core adapter protocol:

```python
class WordIndexSource(Protocol):
    source_id: str
    language: str

    def status(self) -> WordIndexSourceStatus: ...
    def list(self, request: WordIndexRequest) -> WordIndexPage: ...
    def neighborhood(self, request: WordNeighborhoodRequest) -> WordIndexNeighborhood: ...
    def wheel(self, request: WordWheelRequest) -> WordIndexPage: ...
```

Use `connect_duckdb_ro` for all read-only DuckDB access. Do not share DuckDB
connections across requests.

## Source Implementation Notes

### CDSL

- Enumerate from `headwords` joined to `entries` by `(dict_id, lnum)`.
- Prefer primary headwords, but keep homograph metadata.
- Use `lnum` as source order and as part of cursoring.
- Generate learner display forms from existing SLP1/IAST helpers where possible.
- Include `mw` and `ap90` initially because those are already catalogued.

### DICO

- Enumerate from `entries_fr`.
- Use `headword_deva` for `canonical_name` when available.
- Use `headword_roma` or `headword_norm` as lookup key.
- Use `(source_page, entry_id, occurrence)` as stable source order.

### Gaffiot

- Enumerate from `entries_fr`.
- Use `headword_raw` for display and normalized `headword_norm` for lookup.
- Cursor by `headword_norm, entry_id`.

### Diogenes

The first materialized implementation is in place:

1. `databuild diogenes-index lat|grc --mode direct` imports Diogenes' local
   one-entry-per-line XML dictionary files when available.
2. `--mode crawl` seeds a normal Diogenes lookup and then crawls a fixed window
   through `prev_entry`/`next_entry` for verification or partial indexes.
3. The builder stores headwords and navigation offsets in
   `data/build/lex_diogenes_<lang>.duckdb`.
4. Runtime `word-index` reads the materialized DB for `sources`, `list`,
   `neighborhood`, and `wheel`.

Do not try to crawl Diogenes live during normal `word-index list`; it should use
cached/built data or return a clear source-unavailable warning.

## Wheel Semantics

The wheel should not be random noise. It should select verified index rows.

MVP wheel modes:

- `--seed`: deterministic shuffle from source rows;
- `--source`: restrict to one dictionary/source;
- `--level`: later, prefer shorter/common entries when source frequency exists;
- `--require-encounter-hit`: optional expensive verification mode that probes
  selected rows through `encounter` before returning them.

The first version can sample locally from indexed rows, then trust source
presence as verification. A later high-confidence mode can run bounded encounter
checks.

## Neighborhood Semantics

Support two kinds of neighborhood:

- **lexical order neighborhood**: entries before/after the anchor by source sort
  order, e.g. CDSL `lnum`, Gaffiot normalized headword order, DICO source page
  order;
- **lookup neighborhood**: alternatives returned by `word_list`, fuzzy matches,
  or source-provided nearest entries.

The JSON should label this explicitly:

```json
{
  "neighborhood_kind": "lexical_order|lookup_alternatives",
  "anchor_status": "exact|nearest|not_found"
}
```

This matters pedagogically: nearby dictionary entries are not the same as better
matches for user intent.

## Language Ordering And Collation

The first implementation can expose source order, but Sanskrit and Greek need
explicit collation keys before the neighborhood experience should be considered
finished.

- Sanskrit should not depend only on raw SLP1/Velthuis/ASCII sort order. Add a
  `collation_key` projection that normalizes Devanagari, IAST, and SLP1 into one
  Sanskrit lexical ordering policy.
- Greek should not depend on Diogenes display strings or accent-bearing Unicode
  order. Add a Greek `collation_key` that folds breathings/accents for ordering
  while preserving UTF-8 Greek display.
- Interleaved wheels should prefer romanized `lookup` for compact display, but
  source-local neighborhoods should expose both native/script display and
  collation metadata.
- Cross-language similarity should remain a separate future mode; it should not
  be confused with lexical before/after neighborhoods.

## Crawler And Builder Strategy

Full-source crawling belongs in `databuild`, not in interactive `word-index` or
`encounter` calls.

- **DICO**: the current DICO builder already crawls/parses local Heritage DICO
  HTML files into `lex_dico.duckdb`. The next crawler work is coverage and
  freshness: report source page counts, skipped anchors, duplicate bodies, and
  rebuild provenance.
- **Diogenes**: `databuild diogenes-index lat|grc` now imports full local XML
  files in direct mode and crawls fixed windows around configurable seed words
  in crawl mode. Crawl defaults are `amo` for Latin and `apo` for Greek.
  Runtime `word-index list` only reads the materialized DB.
- **Failure mode**: if a crawl/index is missing, return `available: false` and a
  warning. Do not silently start a crawl from an interactive command.

## Implementation Phases

### Phase 1: Contract and Local DB Sources

- Add `WordIndexItem`, `WordIndexSourceStatus`, request/page models. ✅ first
  slice exists in `src/langnet/word_index/`.
- Add `docs/schemas/word_index.v1.schema.json`. ✅
- Implement source status plus list/neighborhood for Gaffiot, DICO, CDSL. ✅
- Add `word-index sources`, `word-index list`, and `word-index neighborhood`. ✅
- Keep all operations read-only against existing built DBs.
- Next: add explicit Sanskrit/Greek collation keys and accepted-output fixtures.

### Phase 2: Wheel

- Add deterministic seeded sampling across one or more source adapters. ✅ first
  slice samples within each local DuckDB source before interleaving.
- Expose `word-index wheel`. ✅
- Reuse canonical display projection from word-of-day where practical.
- Add basic text output and JSON schema tests.
- Next: filter out learner-hostile rows, such as numbered proper-name variants,
  unless explicitly requested.

### Phase 3: Encounter Integration

- Add optional `--neighbors N` to `encounter`.
- Attach compact `neighborhood` metadata beside the existing display payload.
- Ensure no live crawler or translation population happens because a caller asked
  for neighbors.

### Phase 4: Diogenes Enumeration

- Research exact Diogenes next/previous CGI contract with fixture captures. ✅
- Extend parser to preserve previous/next navigation offsets. ✅
- Add a `databuild diogenes-index lat|grc` command. ✅
- Store Diogenes headwords locally before enabling `word-index list grc
  --source diogenes`. ✅
- Prefer direct XML import for full dictionary enumeration; keep CGI crawl mode
  for fixed windows and verification. ✅
- Next: add a coverage report comparing direct-import counts against crawl
  windows and common-term hit fixtures.

### Phase 5: Quality and Pedagogy

- Add source coverage reports: counts by language/source/dictionary.
- Add acceptance fixtures for common terms and adjacent neighborhoods.
- Add optional scoring for learner-friendly wheel items:
  short headword, has source gloss, not punctuation fragment, not obscure variant
  unless explicitly requested.

## Testing Plan

- Unit tests with tiny in-memory DuckDB fixtures for CDSL, DICO, and Gaffiot
  source adapters.
- Schema tests for `word-index sources`, `list`, `neighborhood`, and `wheel`.
- CLI tests with temporary DB paths or monkeypatched default paths.
- Regression tests for canonical display:
  Sanskrit returns Devanagari when available, Greek returns UTF-8 Greek, Latin
  returns Latin headword.
- DuckDB tests must verify read-only access and missing-DB warnings.
- Encounter integration tests must prove `--neighbors` does not change primary
  ranking or source evidence.

## Open Questions

- Should `word-index list all` interleave languages, or should `all` be reserved
  for `wheel`?
- Should DICO and Gaffiot French-source dictionaries be included by default in
  `all`, or only when translation-capable sources are requested?
- Should CDSL `headwords` include non-primary aliases by default, or should those
  require `--include-aliases`?
- What is the exact Diogenes next/previous call shape for both LSJ and Lewis &
  Short, and can it be crawled without stressing the local service?

## Recommended First Cut

Start with Phase 1 for CDSL, DICO, and Gaffiot. That provides immediate value,
requires no live crawler, fits the existing DuckDB strategy, and gives the web
interface a stable JSON surface for exploration. Then add `wheel`, then attach
optional neighborhoods to `encounter`.
