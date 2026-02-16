# Getting Started with V2 Implementation

This is the quick-start for continuing the V2 build, now focused on canonical candidate generation. Read the handoff first: `docs/handoff/handoff-20260216-candidates.md` (it supersedes earlier setup tasks).

## Read These First (in order)

1. `docs/plans/active/v2-implementation-master-plan.md` - Master plan
2. `docs/handoff/handoff-20260216-candidates.md` - Current workstream + next steps
3. `codesketch/README.md` - What reference code exists
4. `docs/technical/design/v2-architecture-overview.md` - Architecture overview

## Where We Are

- Proto schemas in `vendor/langnet-spec/schema/` are defined and codegen is in place.
- Normalization pipeline lives in `src/langnet/normalizer/` (`core.py`, `sanskrit.py`) with tests passing.
- Tool clients exist (`heritage/client.py`, `diogenes/client.py`, `clients/http.py`, `clients/subprocess.py`).
- DuckDB cache for normalization is in `src/langnet/storage/normalization_index.py`.

## Current Focus: Canonical Candidates

We completed the first milestone: **user input → canonical search terms** with proper sources and caching. Next up is the second milestone: **canonical search term → tool plan**.

### Immediate Tasks (from the handoff)

1) **Plan generation**: build `ToolPlan` creation from `NormalizedQuery` (canonical → plan) with language-specific tool calls.  
2) **Execution wiring**: ensure the resulting plan flows into the executor and stores effects for downstream parsing.  
3) **CLI smoke**: extend `langnet-cli` (or a just target) to print the generated plan for a sample query per language.  
4) **Regression guardrails**: add/extend tests covering plan construction for SAN/GRC/LAT to lock in the milestone.
5) **Plan staging**: ToolPlan now emits staged nodes (fetch → extract → derive → claim) with dependencies per language (Heritage/CDSL for SAN, Diogenes/Whitaker/CLTK for LAT, Diogenes/CTS/CLTK for GRC).

## Quick Architecture Reminder

```
Query → ToolPlan → Execute → Effects → Parse → Reduce → Distill → Output
                        │
                        ├── ToolCallEffect
                        ├── RawResponseEffect
                        ├── ExtractionEffect (LexiconArtifact)
                        ├── DerivationEffect
                        └── ClaimEffect
```

## DuckDB Layout

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

## Commands

```bash
just codegen        # Generate Python from proto
just test           # Run tests
just typecheck      # Type check
just ruff-check     # Lint
# Planning smoke: inspect staged tool plan for a query (fetch/extract/derive/claim)
#   just cli plan san krishna
#   just cli plan lat ea
#   just cli plan grc logos
# Offline builds (run inside repo root):
#   just cli databuild cts   --perseus-dir ~/perseus --legacy-dir ~/Classics-Data
#   just cli databuild cdsl <DICT_ID> --source-dir ~/cdsl_data/dict
# Normalizer cache: CLI writes/reads DuckDB at data/langnet.duckdb by default; override with --db-path or LANGNET_DATA_DIR.
```

For quick manual checks while wiring the normalizer, use the Python snippet in the handoff to confirm `sources` reflects the real tool client (`heritage_sktsearch`, diogenes, etc.).
