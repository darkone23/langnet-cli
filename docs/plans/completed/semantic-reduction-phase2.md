# Semantic Reduction: Clustering Pipeline Complete

**Date**: 2026-02-15  
**Status**: ✅ Complete

## Summary

Implemented the full semantic reduction pipeline from DictionaryEntry to SenseBucket, including:
- Similarity matrix construction using Stanza English lemmatization
- Greedy agglomerative clustering with mode-specific thresholds
- Full pipeline orchestrator with summary utilities
- CDSL gloss preprocessing to strip grammatical metadata

## Files Created

```
src/langnet/semantic_reducer/
├── similarity.py         # Numpy-based similarity matrix with lemmatization
├── clusterer.py          # Greedy agglomerative clustering
└── pipeline.py           # Full pipeline orchestrator

tests/
├── test_semantic_reduction_wsus.py        # WSU extraction tests (48 tests)
└── test_semantic_reduction_clustering.py  # Clustering tests (32 tests)
```

## Key Implementation Details

### 1. Stanza English Lemmatization

Gloss text is lemmatized using Stanza's EN pipeline for improved similarity matching:

```python
from langnet.semantic_reducer import lemmatize_gloss

lemmatize_gloss("the gods of fire")  # -> ['the', 'god', 'of', 'fire']
lemmatize_gloss("digestive faculties")  # -> ['digestive', 'faculty']
```

### 2. CDSL Gloss Preprocessing

Monier-Williams glosses are preprocessed to strip grammatical metadata:

```python
from langnet.semantic_reducer.wsu_extractor import _preprocess_cdsl_gloss

_preprocess_cdsl_gloss("agni/   m. (√ ag, Uṇ.) fire, sacrificial fire")
# -> "fire, sacrificial fire"
```

### 3. Mode Thresholds (Adjusted for Jaccard)

| Mode | Threshold | Use Case |
|------|-----------|----------|
| OPEN | 0.15 | Learner-friendly, broader clustering |
| SKEPTIC | 0.25 | Evidence-first, narrower clustering |

### 4. Numpy Similarity Matrix

```python
from langnet.semantic_reducer import build_similarity_matrix

matrix = build_similarity_matrix(wsus)  # Returns np.ndarray
```

## Test Results

| Language | Word | Buckets | Multi-witness |
|----------|------|---------|---------------|
| Sanskrit | agni | 9 | 1 |
| Sanskrit | deva | 24 | 6 |
| Sanskrit | jala | 24 | 6 |
| Latin | lupus | 17 | 2 |
| Latin | homo | 26 | 3 |
| Latin | terra | 6 | 1 |
| Greek | logos | 65 | 0 |

Total tests: 80 passing (48 WSU + 32 clustering)

## Known Gaps

See `docs/plans/active/semantic-reduction-gaps.md` for details:

1. **Token-based similarity is limited** - Need embedding-based similarity (gensim)
2. **Low similarity scores for related senses** - Even semantically related glosses score 0.1-0.15
3. **No cross-language sense linking** - Cannot link agni ~ ignis ~ πῦρ
4. **No sense disambiguation** - All senses returned without ranking

## Quick Start

```bash
# Run all semantic reduction tests
python -m nose2 -s tests tests.test_semantic_reduction_wsus tests.test_semantic_reduction_clustering -v

# Test end-to-end with real data
python -c "
from langnet.core import LangnetWiring
from langnet.semantic_reducer import reduce_to_semantic_structs, get_bucket_summary, Mode

wiring = LangnetWiring()
entries = wiring.engine.handle_query('san', 'agni')
buckets = reduce_to_semantic_structs(entries, Mode.OPEN)
for s in get_bucket_summary(buckets)[:5]:
    print(f\"{s['sense_id']}: {s['display_gloss'][:50]}...\")
"
```