# codesketch/

This directory contains the **working sketch** that informed the V2 architecture.

## What This Is

The code here represents iterative exploration that led to the current architecture design. It works, but it conflates concerns that V2 separates:

- Query planning mixed with execution
- Extraction mixed with derivation
- Hydration mixed with reduction
- Caching mixed with storage

## How to Use This

**Study, don't import.** This code is reference material for understanding:

| Module | What to Learn |
|--------|---------------|
| `normalization/` | SLP1, IAST, Velthuis, Betacode conversions |
| `heritage/velthuis_converter.py` | Encoding transformations |
| `semantic_reducer/` | Clustering pipeline (WSU → buckets) |
| `foster/` | Functional grammar labels |
| `diogenes/core.py` | HTML parsing patterns |
| `heritage/morphology.py` | JSON response handling |
| `whitakers_words/` | Line-based text parsing |
| `cologne/` | CDSL XML handling |

## Code to Port

These modules are mature enough to port directly to `src/langnet/`:

- `normalization/sanskrit.py` → Query normalizer
- `normalization/greek.py` → Query normalizer
- `heritage/velthuis_converter.py` → Encoding layer
- `semantic_reducer/` → Reduction layer (adapt for Claims)

## Code to Rewrite

These modules informed the design but should be rebuilt with V2 architecture:

| Current | V2 Approach |
|---------|-------------|
| `adapters/*.py` | Split into Extractor + Derivator |
| `diogenes/core.py` | DiogenesExtractor, DiogenesDerivator |
| `heritage/morphology.py` | HeritageExtractor, HeritageDerivator |
| `engine/core.py` | V2Pipeline orchestrator |
| `indexer/` | Cache layers in storage/ |

## Architecture Evolution

See `docs/technical/design/v2-architecture-overview.md` for the target architecture.

Key differences:

| Aspect | codesketch (V1) | V2 |
|--------|-----------------|-----|
| Query flow | Ad-hoc in adapters | QueryPlanner → ToolPlan → Executor |
| Pipeline stages | Conflated | Explicit: Extract → Derive → Hydrate → Reduce |
| Caching | Response-level | 4 transparent layers |
| Provenance | Partial | Full chain from query to claim |
| Hydration | Inline (Diogenes) | Separate stage |

## Related Documentation

- `docs/plans/active/v2-implementation-master-plan.md` - Implementation roadmap
- `docs/technical/design/query-planning.md` - Query planning architecture
- `docs/technical/design/tool-response-pipeline.md` - Response pipeline