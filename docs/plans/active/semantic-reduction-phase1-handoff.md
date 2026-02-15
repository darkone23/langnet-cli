# Phase 1 Handoff: WSU Extraction Foundation

**Date**: 2026-02-15  
**Status**: Ready to Start  
**Prerequisites**: Phase 0 ✅ Complete

## What Phase 0 Accomplished

1. **Schema Enhanced** - `DictionaryDefinition` now has:
   - `source_ref: str | None` - Stable source references (e.g., "mw:890")
   - `domains: list[str]` - Semantic domains
   - `register: list[str]` - Register classification
   - `confidence: float | None` - Stochastic confidence scores

2. **CDSL Adapter Updated** - Populates `source_ref` from MW/AP90 entry IDs

3. **Tests Passing** - 13 new tests, 31 existing tests still pass

## Phase 1 Goal

Build WSU (Witness Sense Unit) extraction layer that converts `DictionaryDefinition` objects into structured `WitnessSenseUnit` objects for similarity comparison.

## Key Files to Create

```
src/langnet/semantic_reducer/
├── __init__.py
├── wsu_extractor.py      # Extract WSUs from DictionaryEntry
├── normalizer.py         # Gloss normalization for comparison
└── types.py              # WitnessSenseUnit dataclass
```

## First Implementation Steps

### Step 1: Create WSU Type
```python
# src/langnet/semantic_reducer/types.py
@dataclass
class WitnessSenseUnit:
    source: str          # "mw", "ap90", etc.
    sense_ref: str       # "mw:890"
    gloss_raw: str       # Raw gloss text
    gloss_normalized: str  # Normalized for comparison
    domains: list[str]
    register: list[str]
    confidence: float | None
```

### Step 2: Create WSU Extractor
```python
# src/langnet/semantic_reducer/wsu_extractor.py
def extract_wsu_from_definition(definition: DictionaryDefinition) -> WitnessSenseUnit:
    """Convert DictionaryDefinition to WitnessSenseUnit."""
```

### Step 3: Create Normalizer
```python
# src/langnet/semantic_reducer/normalizer.py
def normalize_gloss(gloss: str) -> str:
    """Normalize gloss for similarity comparison.
    
    - Lowercase
    - Unicode normalization
    - Whitespace normalization
    - Tokenization
    """
```

## Reference Documents

- Design: `docs/technical/design/03-classifier-and-reducer.md`
- Adapter requirements: `docs/plans/todo/semantic-reduction-adapter-requirements.md`
- Migration plan: `docs/plans/todo/semantic-reduction-migration-plan.md`

## Success Criteria

- [ ] WSU type defined
- [ ] WSU extraction from CDSL entries working
- [ ] Gloss normalization deterministic
- [ ] Tests for WSU extraction
- [ ] Performance: < 50ms per entry

## Quick Start Commands

```bash
# Test current CDSL output
python -c "
from langnet.cologne.core import SanskritCologneLexicon
from langnet.adapters.cdsl import CDSLBackendAdapter
lex = SanskritCologneLexicon()
data = lex.lookup_ascii('agni')
adapter = CDSLBackendAdapter()
entries = adapter.adapt(data, 'san', 'agni')
for d in entries[0].definitions[:3]:
    print(f'{d.source_ref}: {d.definition[:50]}...')
"

# Run Phase 0 tests
python -m unittest tests.test_semantic_reduction_phase0 -v
```

---
*Phase 0 verified safe. Phase 1 ready to begin.*