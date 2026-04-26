# Storage Schema

LangNet uses local DuckDB-backed indexes to make staged execution inspectable and cacheable.

## Purpose

Storage supports:

- query normalization caching
- tool-plan caching
- raw backend response storage
- extraction/derivation/claim indexes
- provenance inspection
- handler-version invalidation

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
- provenance chain
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
just triples-dump lat lupus whitakers
```

Use these to inspect whether a query reaches the expected stage and emits expected claims.

## Operational Notes

- Live backend failures should be represented explicitly.
- Unit tests should prefer fixtures over live cache state.
- Long-running processes may cache Python modules; restart them after code changes.
- Do not rely on old cache rows when handler versions or payload semantics changed.
