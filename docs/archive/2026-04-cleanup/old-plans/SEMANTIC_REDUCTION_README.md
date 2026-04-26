# Semantic Reduction — Canonical README

**Last Updated**: 2026-02-15  
**Scope**: Status, priorities, and how to start. Use this instead of the older status/checklist docs.

## Current State
- Reference implementation exists in `codesketch/src/langnet/semantic_reducer/` (WSU extraction, similarity, clustering); ~80 tests passing there.
- V1 schema evolution landed (source_ref/domains/register/confidence fields added; CDSL populates source_ref). Phase 0 QA passed in prior work.
- Semantic format in `langnet-cli semantic` still uses the legacy converter; the reducer pipeline is not wired into runtime yet.
- Similarity is token/Jaccard-based; thresholds are OPEN=0.15 / SKEPTIC=0.25. Embedding-based similarity and ranking are TODO.

## Key Gaps / Next Moves
1) **Similarity quality**: Add embedding-backed similarity (e.g., glove-wiki-gigaword-100) and hybrid scoring; replace Jaccard-only scoring.
2) **Gloss cleaning**: Strip citation abbreviations (CDSL/Heritage) before similarity.
3) **Sense ranking**: Rank by witness count + source priority; consider domain/frequency when available.
4) **Runtime wiring**: Replace legacy semantic converter with reducer pipeline; ensure deterministic bucket IDs and evidence preservation.
5) **Fixtures/tests**: Golden snapshots for agni/lupus/logos; integration tests to assert deterministic buckets and performance bounds.

## Quickstart (dev)
- Environment: `devenv shell langnet-cli`
- Sanity check (legacy semantic path): `langnet-cli semantic san agni --output json`
- Inspect codesketch reference: `codesketch/src/langnet/semantic_reducer/` (types, normalizer, similarity, clusterer, pipeline)
- Useful tests (once wired): `just test tests.test_semantic_reduction_clustering` (may require assets)

## Performance Snapshot (codesketch runs)
| Language | Word | WSUs | Buckets | Multi-witness |
|----------|------|------|---------|---------------|
| Sanskrit | agni | 10 | 9 | 1 |
| Sanskrit | deva | 38 | 24 | 6 |
| Latin | lupus | 19 | 17 | 2 |
| Greek | logos | 65 | 65 | 0 |

## Adapter Coverage (reference)
- **CDSL**: definitions with stable `source_ref`; WSU extraction works after schema enhancement.
- **Diogenes**: dictionary blocks yield WSUs; `source_ref` synthetic.
- **Heritage**: definitions yield WSUs; `source_ref` synthetic.
- **Whitakers**: definitions yield WSUs; `source_ref` synthetic.

## Work Plan Pointers
- Implementation roadmap & migration steps: `docs/plans/todo/semantic-reduction/semantic-reduction-migration-plan.md`, `semantic-reduction-roadmap.md`
- Gap details and algorithm specs: `semantic-reduction-gap-analysis.md`, `semantic-reduction-similarity-spec.md`, `semantic-reduction-adapter-requirements.md`
- Clustering/classifier design: `docs/technical/design/classifier-and-reducer.md`

## Success Criteria (when rewired)
- Semantic format uses reducer pipeline with deterministic bucket IDs.
- Similarity/clustering produce stable buckets (OPEN/SKEPTIC) with evidence retained.
- Benchmarks: <500ms typical query; deterministic outputs; fixture tests green.

## Notes
- This README supersedes older status/checklist/QA files in this folder. If you need historical detail, check git history.
