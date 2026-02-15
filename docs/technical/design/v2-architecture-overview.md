# V2 Architecture Overview

**Status**: Draft
**Date**: 2026-02-15
**Priority**: FOUNDATIONAL

## Quick Links

- **Implementation Plan**: `docs/plans/active/v2-implementation-master-plan.md`
- **Start Here**: Read this document for architecture, then read the plan for implementation

## Architecture Documents

| Doc | Stage | Focus |
|-----|-------|-------|
| `query-planning.md` | -1, 0 | User input → NormalizedQuery → ToolPlan |
| `tool-response-pipeline.md` | 1-5 | Tool Call → Raw → Extract → Derive → Claim |
| `hydration-reduction.md` | 4.5, 6 | Hydrate references → Reduce to buckets |
| `tool-fact-architecture.md` | Types | Tool-specific fact types, transformation rules |
| `entry-parsing.md` | 3, 4 | Lark grammars for extraction/derivation |
| `classifier-and-reducer.md` | 6 | Semantic reduction, clustering |
| `witness-contracts.md` | Provenance | Source contracts, witness expectations |
| `semantic-structs.md` | Output | Universal JSON schema |

## Complete Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Stage -1: User Input                                                        │
│   "shiva", "lupus", "λόγος"                                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ Stage 0: Query Planning (query-planning.md)                              │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│   │ Normalize    │ → │ Plan Tools   │ → │ ToolPlan     │                  │
│   │ "shiva"→"śiva"│    │ (cdsl,heritage)│   │ (declarative)│                  │
│   └──────────────┘    └──────────────┘    └──────────────┘                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ Stage 0.5: Plan Execution                                                   │
│   Execute ToolPlan in parallel where possible                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ Stage 1: Tool Calls (tool-response-pipeline.md)                          │
│   HTTP requests to: cdsl, diogenes, heritage, whitakers, cts_index, etc.    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ Stage 2: Raw Responses (tool-response-pipeline.md)                       │
│   Store HTML/XML/JSON exactly as received (immutable, re-parseable)         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ Stage 3: Extractions (entry-parsing.md, tool-response-pipeline.md)   │
│   Format parsing: XML → dict, HTML → blocks, JSON → objects                 │
│   (Tool-specific parsers, Lark grammars)                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ Stage 4: Derivations (entry-parsing.md, tool-fact-architecture.md)   │
│   Content parsing: Extract tool-specific facts                              │
│   CDSLSenseFact, DiogenesDictFact, HeritageMorphFact, etc.                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ Stage 4.5: Hydration (hydration-reduction.md)                            │
│   Expand references: CTS URN → citation text                                │
│   (Optional, configurable depth)                                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ Stage 5: Claims (tool-fact-architecture.md)                              │
│   Transform tool facts → universal claims                                   │
│   predicate: has_gloss, has_morphology, has_citation                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ Stage 6: Reduction (classifier-and-reducer.md, hydration-reduction.md)│
│   Cluster claims → buckets → semantic constants                             │
│   (Mode: open/skeptic, View: didactic/research)                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ Output (semantic-structs.md)                                             │
│   QueryResponse: lemmas, analyses, senses, citations, provenance            │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Key Concepts

### Provenance Chain

Every claim traces back to its origin:

```
Claim
  └─ derivation_id → Derivation
                      └─ extraction_id → Extraction
                                          └─ response_id → RawResponse
                                                            └─ call_id → ToolCall
                                                                          └─ request_url
```

This enables: "Show me the MW entry we used to derive 'fire' for agni."

### Hydration vs Reduction

| Operation | Direction | When |
|-----------|-----------|------|
| Hydration | Expand | After derivation, before claims |
| Reduction | Condense | After claims, before output |

```
Derivation (CTS URN ref) → Hydrate (full text) → Claim → Reduce (bucket)
```

### Query Planning

Decouple plan building from execution:

```
User Query → Normalizer → Planner → ToolPlan
                                    ↓ (can cache)
                               Executor → Tool Calls
```

Tool-specific query transformations:
- CDSL: śiva → SLP1 "Siva"
- Heritage: śiva → Velthuis "ziva"
- Diogenes (Greek): λόγος → Betacode "lo/gos"

### Re-parsing

Each stage can be re-run independently:

| Scenario | Re-run From | Cost |
|----------|-------------|------|
| Improved format parser | Raw Response | No re-fetch |
| Improved content parser | Extractions | No re-extract |
| Improved transformation | Derivations | No re-parse |
| Improved hydration | Derivations | No re-transform |
| Updated citation index | Hydration | No re-derive |

## Tool Registry

All tools follow the same pattern:

| Tool | Query Format | Response Format | Produces |
|------|-------------|-----------------|----------|
| cdsl | SLP1 | XML | CDSLSenseFact |
| heritage | Velthuis | JSON | HeritageMorphFact |
| diogenes | ASCII/Betacode | HTML | DiogenesDictFact, DiogenesCitationFact |
| whitakers | ASCII | Text | WhitakersAnalysisFact |
| cltk | Native | JSON | CLTKMorphFact |
| cts_index | URN/Lemma | JSON | CitationFact (hydration) |

## Storage Schema (DuckDB)

```
tool_calls          ← Stage 1
raw_responses       ← Stage 2
extractions         ← Stage 3
derivations         ← Stage 4
claims              ← Stage 5
buckets             ← Stage 6 (optional, for caching)

tool_plans          ← Stage 0 (cached plans)
hydration_cache     ← Stage 4.5
```

## Codebase Organization

V1 is preserved as a **working sketch** for reference:

```
src/langnet/
├── codesketch/            # V1 reference implementation
│   ├── adapters/          # Study, don't import
│   ├── diogenes/
│   ├── heritage/
│   ├── whitakers_words/
│   ├── cologne/
│   ├── normalization/     # PORT: transliteration code
│   ├── semantic_reducer/  # PORT: clustering pipeline
│   └── ...
├── v2/                    # Clean V2 implementation
│   ├── storage/
│   ├── normalizer/
│   ├── registry/
│   ├── planner/
│   ├── executor/
│   ├── processor/
│   ├── extractors/
│   ├── derivators/
│   ├── hydration/
│   ├── transform/
│   └── pipeline/
└── __init__.py
```

**Design principle**: V2 is a tree copy, not imports. Study `codesketch/` to understand patterns, build fresh in `v2/`.

## Implementation Priority

### Phase 1: Core Pipeline (Weeks 1-3)
1. Define proto schemas for all stages
2. Implement storage layer (DuckDB)
3. Build pipeline runner

### Phase 2: Query Planning (Weeks 4-5)
1. Build Query Normalizer (use existing code)
2. Build Tool Registry
3. Build Query Planner

### Phase 3: Per-Tool Adapters (Weeks 6-10)
1. CDSL extractor + derivator
2. Diogenes extractor + derivator
3. Heritage extractor + derivator
4. Whitakers extractor + derivator
5. CLTK adapter

### Phase 4: Hydration (Weeks 11-12)
1. Separate hydration from Diogenes
2. Build CTS Index hydrator
3. Build other hydrators

### Phase 5: Reduction (Weeks 13-14)
1. Wire semantic reducer to Claims
2. Implement mode/view variations
3. Add embedding similarity

### Phase 6: V2 API/CLI (Weeks 15-16)
1. New endpoints
2. Side-by-side with V1
3. Feature flag rollout

## V1 vs V2

| Aspect | V1 (Current) | V2 (Target) |
|--------|--------------|-------------|
| Pipeline stages | Conflated | Explicit, stored |
| Query planning | Ad-hoc in adapters | Declarative ToolPlan |
| Provenance | Partial (source_ref) | Full chain (call_id → claim_id) |
| Hydration | Inline (Diogenes) | Separate stage |
| Re-parsing | Not possible | At any stage |
| Tool format handling | Hardcoded | Registry + transform |
| Caching | Response-level | Per-stage |

## Related Documents

- `docs/plans/active/tool-fact-indexing.md` - Implementation roadmap
- `docs/technical/backend/tool-capabilities.md` - Per-tool expectations
- `docs/technical/design/mermaid/tool-fact-flow.md` - Diagrams
