# Semantic Reduction: Gap Analysis & Action Items

**Date**: 2026-02-15  
**Last Updated**: 2026-02-15  
**Status**: Active Development

## Critical Gaps

### 1. Token-based Similarity is Limited ⚠️ HIGH IMPACT

**Current State**: Jaccard similarity on lemmatized tokens

**Problem**:
```
"fire, flame" vs "blaze, conflagration"
→ Token overlap: 0 (no shared tokens)
→ Jaccard: 0.0
→ Semantic similarity: HIGH (all are about fire)
```

**Impact**: Related senses don't cluster together

**Solution**: Add word embedding similarity

**Implementation**:
```python
# src/langnet/semantic_reducer/normalizer.py

import gensim.downloader as api
from gensim.models import KeyedVectors

_embedding_model = None

def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = api.load('glove-wiki-gigaword-100')
    return _embedding_model

def embedding_similarity(tokens1: list[str], tokens2: list[str]) -> float:
    """Compute semantic similarity using word embeddings."""
    model = _get_embedding_model()
    
    # Filter to known words
    vecs1 = [model[t] for t in tokens1 if t in model]
    vecs2 = [model[t] for t in tokens2 if t in model]
    
    if not vecs1 or not vecs2:
        return 0.0
    
    # Average vectors
    avg1 = np.mean(vecs1, axis=0)
    avg2 = np.mean(vecs2, axis=0)
    
    # Cosine similarity
    return float(np.dot(avg1, avg2) / (np.linalg.norm(avg1) * np.linalg.norm(avg2)))

def hybrid_similarity(tokens1: list[str], tokens2: list[str], alpha: float = 0.5) -> float:
    """Combine token and embedding similarity."""
    token_sim = jaccard_similarity(tokens1, tokens2)
    embed_sim = embedding_similarity(tokens1, tokens2)
    return alpha * token_sim + (1 - alpha) * embed_sim
```

**Files to Modify**:
- `src/langnet/semantic_reducer/normalizer.py` - Add functions above
- `src/langnet/semantic_reducer/similarity.py` - Use `hybrid_similarity`

**Test Cases**:
```python
assert embedding_similarity(["fire", "flame"], ["blaze", "conflagration"]) > 0.5
assert hybrid_similarity(["fire", "flame"], ["blaze"]) > 0.3
```

---

### 2. Low Similarity Scores ⚠️ MEDIUM IMPACT

**Current State**: Even semantically related glosses score 0.08-0.15

**Example** (Sanskrit "agni"):
```
"fire, sacrificial fire" vs "the god of fire"
→ Shared tokens: "fire"
→ Jaccard: 0.12
→ Should cluster: YES (both about fire)
```

**Mitigation Applied**: Lowered thresholds to 0.15 (OPEN) / 0.25 (SKEPTIC)

**Better Solution**: See #1 above (embedding similarity)

---

### 3. Citation Abbreviations in Glosses ⚠️ MEDIUM IMPACT

**Current State**: CDSL glosses contain citation abbreviations

**Examples**:
```
"bile, L."         → "L." = lexicographers (citation)
"gold, RV."        → "RV." = Rig Veda (citation)
"heavenly, MBh."   → "MBh." = Mahabharata (citation)
```

**Impact**: Noise in similarity comparison

**Solution**: Strip citation abbreviations

**Implementation**:
```python
# src/langnet/semantic_reducer/wsu_extractor.py

CITATION_ABBREVIATIONS = {
    "L.", "RV.", "RV", "AV.", "AV", "TS.", "TS",
    "MS.", "MS", "KS.", "KS", "JB.", "JB",
    "ChUp.", "BrUp.", "KausUp.", "MBh.", "MBh",
    "R.", "Hariv.", "Ragh.", "Kumārs.", "Kāv.",
    "Kād.", "Daśakum.", "MārkP.", "VP.", "BhP.",
    "AgP.", "MatsyP.", "VāyuP.", "BrahmāṇḍP.",
    "Sūryas.", "Sūryapr.", "VarBṛS.", "Hcat.",
    "Ratnak.", "Laghuj.", "Sāh.", "Kpr.",
}

def _strip_citations(gloss: str) -> str:
    """Remove citation abbreviations from gloss."""
    tokens = gloss.split()
    cleaned = [t for t in tokens if t not in CITATION_ABBREVIATIONS]
    return " ".join(cleaned)
```

---

### 4. No Cross-language Sense Linking ⚠️ LOW PRIORITY

**Problem**: Cannot link senses across languages

**Example**:
```
Sanskrit: agni (fire)
Latin: ignis (fire)  
Greek: πῦρ (fire)
→ Should link to same semantic concept
```

**Solution**: Use multilingual embeddings (MUSE, fastText)

**Status**: Research needed, lower priority for educational tool

---

### 5. No Sense Disambiguation ⚠️ USER EXPERIENCE

**Problem**: All senses returned equally without ranking

**Example**: Greek "λόγος" (logos) has 65 senses in LSJ
- Philosophy, grammar, rhetoric, computation, etc.
- User context not considered

**Solutions**:
1. **Source priority ranking**: MW > AP90 > Heritage > LSJ > Whitakers
2. **Frequency-based ranking**: If corpus data available
3. **Domain detection**: Philosophy, grammar, etc.
4. **User context**: Optional context parameter

**Implementation**:
```python
# src/langnet/semantic_reducer/ranker.py (NEW FILE)

def rank_buckets(buckets: list[SenseBucket]) -> list[SenseBucket]:
    """Rank buckets by importance."""
    return sorted(buckets, key=lambda b: (
        -len(b.witnesses),           # More witnesses first
        -_source_priority(b),         # Higher priority sources
        -b.confidence,                # Higher confidence
    ))
```

---

## Test Coverage Gaps

### Missing Test Types

1. **Golden Snapshot Tests**
   - Fixed inputs → expected bucket counts/IDs
   - Should be deterministic across runs

2. **Integration Tests with Real Data**
   ```python
   def test_sanskrit_agni_deterministic():
       entries = engine.handle_query('san', 'agni')
       buckets1 = reduce_to_semantic_structs(entries, Mode.OPEN)
       buckets2 = reduce_to_semantic_structs(entries, Mode.OPEN)
       assert [b.sense_id for b in buckets1] == [b.sense_id for b in buckets2]
   ```

3. **Edge Cases**
   - Empty glosses
   - Single-character glosses  
   - Non-ASCII text
   - Very long glosses (>1000 chars)

4. **Performance Tests**
   - Large entries (logos: 65 WSUs)
   - Many small entries (100+ entries)

---

## Performance Considerations

### Current Bottleneck: Stanza Lemmatization

- Stanza EN pipeline adds ~4 seconds to test suite
- First call loads model (~1 second)
- Subsequent calls are fast

**Mitigation Options**:
1. Cache lemmatized tokens in WSU
2. Batch lemmatization
3. Use lighter model (stanza `en` vs `en_ewt`)

### Matrix Construction

- O(n²) for n WSUs
- Current: acceptable for n < 100
- Future: Consider sparse matrices for large n

---

## Recommended Iteration Order

1. **Embedding similarity** (highest impact)
   - Add `glove-wiki-gigaword-100`
   - Implement hybrid scoring
   - Adjust thresholds

2. **Citation stripping** (quality improvement)
   - Expand abbreviation list
   - Add tests

3. **Golden snapshot tests** (stability)
   - Create fixtures
   - Add determinism checks

4. **Sense ranking** (UX improvement)
   - Add `ranker.py`
   - Integrate with pipeline

5. **Cross-language linking** (future)
   - Research multilingual embeddings
   - Design linking algorithm
