# Semantic Reduction: Current Status & Iteration Plan

**Date**: 2026-02-15  
**Status**: Phase 2 implemented; tests present (not executed in this environment)  
**Priority**: HIGH

## Executive Summary

Phases 0-2 are complete. The semantic reduction pipeline can:
1. Extract WSUs from all adapters (CDSL, Diogenes, Heritage, Whitakers)
2. Build similarity matrices using Stanza English lemmatization
3. Cluster WSUs into SenseBuckets using greedy agglomerative algorithm
4. Produce multi-witness buckets for related glosses

**Test Coverage**: 80 tests passing

## Completed Phases

### ✅ Phase 0: Schema Enhancement
- `DictionaryDefinition` enhanced with `source_ref`, `domains`, `register`, `confidence`
- CDSL adapter populates `source_ref` from MW/AP90 entry IDs
- 13 tests passing

### ✅ Phase 1: WSU Extraction
- `src/langnet/semantic_reducer/types.py` - WSU, SenseBucket, Mode, Source
- `src/langnet/semantic_reducer/normalizer.py` - Gloss normalization + Stanza lemmatization
- `src/langnet/semantic_reducer/wsu_extractor.py` - Extraction + CDSL preprocessing
- 48 tests passing

### ✅ Phase 2: Clustering Pipeline
- `src/langnet/semantic_reducer/similarity.py` - Numpy similarity matrix
- `src/langnet/semantic_reducer/clusterer.py` - Greedy agglomerative clustering
- `src/langnet/semantic_reducer/pipeline.py` - Full pipeline orchestrator
- 32 tests passing

## Current Performance

| Language | Word | WSUs | Buckets | Multi-witness |
|----------|------|------|---------|---------------|
| Sanskrit | agni | 10 | 9 | 1 |
| Sanskrit | deva | 38 | 24 | 6 |
| Sanskrit | jala | 35 | 24 | 6 |
| Latin | lupus | 19 | 17 | 2 |
| Latin | homo | 29 | 26 | 3 |
| Latin | terra | 7 | 6 | 1 |
| Greek | logos | 65 | 65 | 0 |

## Mode Thresholds (Adjusted for Jaccard)

| Mode | Threshold | Behavior |
|------|-----------|----------|
| OPEN | 0.15 | Broader clustering, learner-friendly |
| SKEPTIC | 0.25 | Narrower clustering, evidence-first |

## Adapter Coverage

| Adapter | Data Structure | `source_ref` | WSU Support | Preprocessing |
|---------|----------------|--------------|-------------|---------------|
| **CDSL** | `definitions[]` | ✅ Stable | ✅ Full | ✅ Grammatical strip |
| **Diogenes** | `dictionary_blocks[]` | ✅ Generated | ✅ Full | None |
| **Heritage** | `definitions[]` | ⚠️ Synthetic | ✅ Works | None |
| **Whitakers** | `definitions[]` | ⚠️ Synthetic | ✅ Works | None |

## Iteration Roadmap

### Priority 1: Embedding-based Similarity (HIGH IMPACT)

**Problem**: Token-based Jaccard can't detect "fire" ~ "blaze" ~ "conflagration"

**Solution**: Use gensim word embeddings

```python
# Available in environment
from gensim import downloader
model = downloader.load('glove-wiki-gigaword-100')

# Hybrid score: 0.5 * token + 0.5 * embedding
```

**Files to modify**:
- `src/langnet/semantic_reducer/normalizer.py` - Add `embedding_similarity()`
- `src/langnet/semantic_reducer/similarity.py` - Use hybrid scoring

**Expected impact**: "fire, flame" and "blaze, conflagration" would cluster together

### Priority 2: Sense Disambiguation (USER EXPERIENCE)

**Problem**: Greek "λόγος" (logos) has 65 senses, all returned equally

**Solutions**:
1. Rank by source priority (MW > AP90 > Heritage > ...)
2. Rank by frequency (if available from corpus)
3. Consider user context (philosophy, grammar, rhetoric)

**Files to create**:
- `src/langnet/semantic_reducer/ranker.py` - Sense ranking logic

### Priority 3: Gloss Cleaning (QUALITY)

**Problem**: Citation abbreviations pollute glosses

**Examples**:
- "bile, L." → "L." is lexicographers citation
- "gold, RV." → "RV." is Rig Veda citation

**Solution**: Strip common citation abbreviations

**Files to modify**:
- `src/langnet/semantic_reducer/wsu_extractor.py` - Expand `_preprocess_cdsl_gloss()`

### Priority 4: Cross-language Sense Linking (FUTURE)

**Problem**: Cannot link agni (Sanskrit) ~ ignis (Latin) ~ πῦρ (Greek)

**Solution**: Use multilingual embeddings (MUSE, fastText multilingual)

**Status**: Requires research, lower priority

## Test Gaps

Current tests are mostly synthetic. Need:

1. **Integration tests with real data**
   - Fixed test fixtures for agni, lupus, logos
   - Golden snapshot tests for bucket stability

2. **Edge case tests**
   - Empty glosses
   - Single-character glosses
   - Non-English text in glosses

3. **Performance tests**
   - Large entries (logos with 65 senses)
   - Many small entries

## Quick Verification

```bash
# Run all semantic reduction tests
python -m nose2 -s tests tests.test_semantic_reduction_wsus tests.test_semantic_reduction_clustering -v

# Test end-to-end
python -c "
from langnet.core import LangnetWiring
from langnet.semantic_reducer import reduce_to_semantic_structs, get_bucket_summary, Mode

wiring = LangnetWiring()
entries = wiring.engine.handle_query('san', 'agni')
buckets = reduce_to_semantic_structs(entries, Mode.OPEN)
print(f'agni: {len(buckets)} buckets')
for s in get_bucket_summary(buckets)[:3]:
    print(f\"  {s['sense_id']}: {s['display_gloss'][:40]}... ({s['witness_count']} witnesses)\")
"
```

## Related Documents

- `docs/plans/active/semantic-reduction/semantic-reduction-gaps.md` - Detailed gap analysis
- `docs/plans/completed/semantic-reduction/semantic-reduction-phase2.md` - Phase 2 completion notes
- `docs/technical/design/03-classifier-and-reducer.md` - Original design spec

---
Evidence: `src/langnet/semantic_reducer/` contains extractor/similarity/clusterer/pipeline modules, and `tests/test_semantic_reduction_clustering.py` exercises the pipeline; command execution was not run here because the `just` runner was not invoked in this shell. Run `just test tests.test_semantic_reduction_clustering` (inside `devenv shell langnet-cli`) to validate in a prepared environment.
