# Storage Schema

LangNet uses local DuckDB-backed indexes plus a few adjacent local index
formats to make staged execution, dictionary lookup, and reader search
inspectable and cacheable.

## Purpose

Storage supports:

- query normalization caching
- tool-plan caching
- raw backend response storage
- extraction/derivation/claim indexes
- provenance inspection
- handler-version invalidation
- local dictionary source indexes for DICO, Gaffiot, Bailly, Lewis 1890,
  Whitaker's, Diogenes, and CDSL
- reader catalog, passage, metadata-overlay, work-map, and search-index stores
- word-index stores for dictionary headword exploration
- CTS URN/citation metadata indexes
- translation-cache rows for DICO, Gaffiot, and Bailly English projections

## Staged Data Model

```text
query_normalization_index
  ↓
query_plan_index
  ↓
plan_response_index
  ↓
raw_response_index
  ↓
extraction_index
  ↓
derivation_index
  ↓
claims
  ↓
provenance
```

## Effect Tables

### Raw Responses

Raw backend responses preserve:

- response ID
- tool/call ID
- endpoint
- status/content type/headers
- raw body
- fetch timing

### Extractions

Extractions preserve:

- extraction ID
- source response ID
- extraction kind
- canonical value if known
- structured payload
- handler version

### Derivations

Derivations preserve:

- derivation ID
- source extraction ID
- derivation kind
- canonical value if known
- normalized payload
- handler version

### Claims

Claims preserve:

- claim ID
- source derivation ID
- subject and predicate
- claim value
- provenance chain
- handler version

Claim values may include triples. Triples should carry `metadata.evidence`.

## Handler Versioning

Handlers use version strings to avoid stale derived data. If a handler’s output semantics change, bump its `@versioned(...)` value so old cached rows are not treated as current.

Handler versions are especially important for source-entry parsing and
translation-cache projection. A source parser can preserve the same raw rows
while changing extracted segments, source references, translated segments, or
claim triples; those changes should invalidate downstream cached effects.

## Cache Behavior

The intended cache model is stage-aware:

- unchanged raw response can be reused
- extraction can be invalidated independently
- derivation can be invalidated independently
- claim projection can be invalidated independently

This keeps live backend calls expensive but downstream parsing/projection cheap.

## Development Commands

```bash
just cli plan lat lupus
just cli plan-exec lat lupus
just cli triples-dump lat lupus whitakers
just cli reader catalogs --output json
just cli word-index sections lat --output json
just cli translation-cache status --output json
```

Use these to inspect whether a query reaches the expected stage and emits expected claims.

## Source And Product Stores

Common local DuckDB stores include:

| Store family | Typical role |
| --- | --- |
| staged-effect indexes | raw responses, extractions, derivations, claims, and provenance |
| `data/build/lex_dico.duckdb` | Sanskrit DICO dictionary rows |
| `data/build/lex_gaffiot.duckdb` | Latin Gaffiot dictionary rows |
| `data/build/lex_bailly.duckdb` | Greek Bailly dictionary rows |
| `data/build/lex_lewis_1890.duckdb` | Latin Lewis 1890 dictionary rows |
| `data/build/lex_whitakers.duckdb` | Whitaker's Words dictionary rows |
| `data/build/lex_diogenes_<lang>.duckdb` | Diogenes dictionary rows by language |
| `data/build/foster_ossa.duckdb` | Foster Ossa extracted pages, sections, encounters, concept mentions, and summary slots |
| `data/build/foster_ossa_search.lance` | Foster Ossa page/encounter full-text search artifact |
| `data/build/cts_urn.duckdb` | CTS URN/citation metadata used by reader/citation workflows |
| reader catalog/search builds | DuckDB reader catalog/work-map files plus `data/build/reader/search.lance` text search |
| word-index builds | per-language dictionary headword sections and entries |
| `data/cache/langnet.duckdb` | translation-cache rows and other local cache data |

Exact paths may be configurable by commands, but documentation examples should
use repository `just cli` and `just cli-databuild` wrappers.

## Operational Notes

- Live backend failures should be represented explicitly.
- Unit tests should prefer fixtures over live cache state.
- Long-running processes may cache Python modules; restart them after code changes.
- Do not rely on old cache rows when handler versions or payload semantics changed.
- Reader, word-index, paradigm, and translation-cache JSON are user-facing CLI
  contracts and SvelteKit adapter inputs; schema changes should be deliberate.
