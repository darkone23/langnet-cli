# Universal Schema Plan

**Status**: 🔄 PLANNED (Not Started)
**Priority**: Medium
**Dependencies**: Sanskrit Heritage Integration complete

## Goal

Create a single, language‑agnostic JSON‑compatible data model that all back‑ends (Heritage, CDSL, Whitaker's, etc.) must return. The model will include:
- `DictionaryEntry` – the top‑level container for a queried term.
- `Sense` – a specific meaning, with part‑of‑speech, definition, example sentences, and **sense‑level citations**.
- `Citation` – source reference (URL, title, author, page, optional excerpt).
- `MorphologyInfo` – optional field for morphological parsing results (lemmas, stems, grammar tags).

## Current Status Analysis

### ✅ COMPLETED PREREQUISITES
1. **Sanskrit Heritage Integration** - Fully implemented with Lark parser
2. **Normalization Pipeline** - Complete with canonical query support
3. **Encoding Detection** - Working for 6 encoding types
4. **Type System** - Existing dataclass structure works well

### ⚠️ CURRENT GAP
- No universal schema implementation exists
- Each backend returns different data structures
- No consistent citation support across languages

## Tasks

### Phase 1: Schema Design (1-2 days)
1. **Define dataclasses** in `src/langnet/schema.py` mirroring the spec:
   - `DictionaryEntry` - top-level container
   - `Sense` - meaning with citations
   - `Citation` - source references
   - `MorphologyInfo` - grammatical analysis
   
2. **Create conversion utilities** using `cattrs`:
   - Transformers for each backend output
   - Standard serialization format
   - Backward compatibility layer

3. **Document the schema** in `docs/UNIVERSAL_SCHEMA.md` with examples for each language.

### Phase 2: Backend Adapter Updates (3-4 days)
4. **Update BaseBackendAdapter** (`src/langnet/backend_adapter.py`) to return the new dataclasses:
   - Define common interface
   - Implement for each existing backend
   - Maintain backward compatibility

5. **Write unit tests** ensuring adapters correctly produce `DictionaryEntry` objects:
   - Test each language backend
   - Verify citation extraction
   - Check serialization compatibility

### Phase 3: Integration (2-3 days)
6. **Add JSON serialization** utilities (using `cattrs` or `orjson`):
   - Ensure API `/api/q` returns objects serializable without custom encoders
   - Test with existing API consumers

7. **Integrate with existing pipelines**:
   - Update normalization pipeline to emit new model
   - Update heritage modules to use new schema
   - Ensure backward compatibility

### Phase 4: Testing & Migration (2-3 days)
8. **Update all tests** to use new schema:
   - Ensure all existing tests pass
   - Add new tests for citation support
   - Verify performance impact

9. **Review and move to completed** once all back‑ends conform:
   - All tests passing
   - No breaking changes
   - Documentation updated

## Implementation Details

### Core Data Classes
```python
@dataclass
class Citation:
    url: str | None
    title: str | None
    author: str | None
    page: str | None
    excerpt: str | None

@dataclass
class Sense:
    pos: str
    definition: str
    examples: list[str]
    citations: list[Citation]
    metadata: dict[str, Any]

@dataclass
class DictionaryEntry:
    word: str
    language: str
    senses: list[Sense]
    morphology: MorphologyInfo | None
    source: str  # "heritage", "cdsl", "whitakers", etc.
    metadata: dict[str, Any]

@dataclass
class MorphologyInfo:
    lemma: str
    pos: str
    features: dict[str, str]
    confidence: float
```

### Backward Compatibility
- Temporary adapter layer for existing consumers
- Feature flag for gradual rollout
- Deprecation warnings for old format
- Migration guide for API users

## Acceptance Criteria

1. **All existing tests pass** after migration
2. **New tests confirm presence** of `sense.citations` for every sense
3. **API `/api/q` returns objects** that can be `orjson.dumps` without custom encoders
4. **Documentation clearly shows** how to extend the schema for future back‑ends
5. **Performance impact** < 10% increase in response time
6. **Memory usage** similar to current implementation

## Risk Assessment

### Low Risk Areas
- Schema design (well-defined problem)
- Test coverage (extensive existing tests)
- Backward compatibility (adapter layer)

### Medium Risk Areas
- Performance impact on large responses
- Memory overhead of additional objects
- Complex citation extraction from some backends

### High Risk Areas
- Whitaker's Words citation extraction (may not have citations)
- CDSL citation format (may need parsing)
- Heritage Platform HTML scraping for citations

## Dependencies

1. **Sanskrit Heritage Integration** - ✅ COMPLETED
2. **Normalization Pipeline** - ✅ COMPLETED  
3. **Existing test suite** - ✅ COMPLETED
4. **Backend interfaces** - ✅ COMPLETED (needs updates)

## Timeline

**Total**: 8-12 days
```
Week 1: Schema design & backend adapter updates
Week 2: Integration, testing, and migration
```

## Success Metrics

1. **Code Quality**: 100% test coverage for new schema module
2. **Performance**: < 10% increase in response time
3. **Compatibility**: All existing API consumers work unchanged
4. **Adoption**: Easy to add new backends using the schema

## Next Steps

1. **Create `src/langnet/schema.py`** with dataclass definitions
2. **Design citation extraction** for each backend
3. **Implement adapter transformers** for each backend
4. **Update API endpoints** to use new schema
5. **Test thoroughly** with real-world queries
6. **Deploy gradually** with feature flag