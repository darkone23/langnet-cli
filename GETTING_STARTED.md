# Getting Started with V2 Implementation

This document is a quick-start guide for implementing the V2 architecture.

## Read These First (in order)

1. `docs/plans/active/v2-implementation-master-plan.md` - The master plan (read top to bottom)
2. `codesketch/README.md` - What reference code exists
3. `docs/technical/design/v2-architecture-overview.md` - Architecture overview

## Core Concepts

- **Effects**: A query produces effects (tool calls, responses, extractions, derivations, claims)
- **Lexicon Artifacts**: Each tool produces its own artifact type (CDSLArtifact, DiogenesArtifact, etc.)
- **Pipeline**: Parse → Reduce → Distill
- **Schema-driven**: Define proto schemas before writing implementation code
- **Caches**: 4 transparent, disposable layers (query, plan, derivation, claim)

## Architecture

```
Query → ToolPlan → Execute → Effects → Parse → Reduce → Distill → Output
                        │
                        ├── ToolCallEffect
                        ├── RawResponseEffect  
                        ├── ExtractionEffect (produces LexiconArtifact)
                        ├── DerivationEffect
                        └── ClaimEffect
```

## DuckDB Files

```
~/.local/share/langnet/
├── langnet.duckdb        # Cross-tool: query_cache, plan_cache, claims
└── tools/
    ├── cdsl.duckdb       # CDSL: raw_responses, extractions, derivations
    ├── diogenes.duckdb
    ├── heritage.duckdb
    ├── whitakers.duckdb
    ├── cltk.duckdb
    └── cts_index.duckdb  # CTS URN lookups (also a tool)
```

## First Task: Define query.proto

1. Create `vendor/langnet-spec/schema/query.proto`
2. Define `NormalizedQuery` with: original, language, canonical_forms, normalizations
3. Define `ToolPlan` with: plan_id, plan_hash, query, tool_calls, dependencies
4. Run `just codegen`
5. Write test that constructs a ToolPlan object

## Second Task: Define Storage Schema

1. Create `src/langnet/storage/schemas/langnet.sql`
2. Define tables: query_cache, plan_cache, claims, provenance
3. Write test with in-memory DuckDB

## Key Commands

```bash
just codegen        # Generate Python from proto
just test           # Run tests
just typecheck      # Type check
just ruff-check     # Lint
```

## Reference Code

Look in `codesketch/src/langnet/` for working implementations:
- `normalization/` - Transliteration (port this)
- `semantic_reducer/` - Clustering (port this)
- `diogenes/core.py` - HTML parsing patterns (study, don't port)
- `heritage/morphology.py` - JSON handling (study, don't port)

## Questions?

See `docs/plans/active/v2-implementation-master-plan.md` for full details.