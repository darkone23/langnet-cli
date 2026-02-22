# Semantic Reduction: Getting Started (Concise)

**Audience**: New developer picking up semantic reduction.  
**Read alongside**: `SEMANTIC_REDUCTION_README.md` for status + priorities.

## Quick Start
```bash
devenv shell langnet-cli
# Legacy semantic sanity (reducer not yet wired)
langnet-cli semantic san agni --output json
```

## First Hour
1. Skim `SEMANTIC_REDUCTION_README.md` for current state/gaps.
2. Browse reference code: `codesketch/src/langnet/semantic_reducer/` (types, normalizer, similarity, clusterer, pipeline).
3. Locate schema/adapter touch points: `src/langnet/schema.py`, `src/langnet/adapters/cdsl.py`.

## Immediate Tasks (recommended order)
1) Wire reducer pipeline into runtime (replace legacy semantic converter) while preserving evidence and determinism.  
2) Upgrade similarity to hybrid token + embeddings; strip citation abbreviations before scoring.  
3) Add sense ranking (witness count + source priority) and fixtures for agni/lupus/logos.  
4) Add golden snapshot tests and performance checks (<500ms typical query).

## Useful Commands
```bash
just test tests.test_semantic_reduction_clustering   # once wired
just typecheck
just ruff-format && just ruff-check
```

## References
- Roadmap/migration/specs: `docs/plans/todo/semantic-reduction/semantic-reduction-{migration-plan,roadmap,gap-analysis,adapter-requirements,similarity-spec}.md`
- Design: `docs/technical/design/classifier-and-reducer.md`
- Status/priorities: `SEMANTIC_REDUCTION_README.md`
1. Check existing adapter implementations
2. Run examples to understand data flow
3. Update tests to verify expectations
4. Document decisions made

---

*This guide should get you started in < 1 hour. Update it as you make progress.*
