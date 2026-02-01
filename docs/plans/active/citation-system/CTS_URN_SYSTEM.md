# CTS URN System Documentation

This section contains comprehensive documentation for the CTS (Canonical Text Service) URN system implementation in langnet-cli.

## Current Status

### Critical Issue: API Integration Gap ⚠️

**PROBLEM**: The CTS URN system is 90% complete but has a critical gap at the API level.

**CURRENT STATE**:
- ✅ CTS URN Mapper: Fully functional with real database
- ✅ Citation Extraction: Working from Diogenes API  
- ✅ Database Integration: Greek authors indexed (2,194 authors, 7,658 works)
- ❌ **API Integration**: `/api/q` endpoint extracts citations but does NOT add CTS URNs

**EVIDENCE**: API returns citations in `citations.items` but missing `cts_urn` field

**ROOT CAUSE**: `_add_citations_to_response()` function in `src/langnet/asgi.py` needs CTS URN mapping

**REQUIRED FIX**: Add CTS URN mapping before adding citations to API response

### Immediate Action Required

**Priority 1: Fix API Integration (HIGH PRIORITY - 1-2 hours)**
- **File**: `src/langnet/asgi.py`  
- **Function**: `_add_citations_to_response()`  
- **Fix**: Add CTS URN mapping to citations before returning API response

```python
# Add this import
from langnet.citation.cts_urn import CTSUrnMapper

# Add CTS URN mapping
cts_mapper = CTSUrnMapper()
updated_citations = cts_mapper.add_urns_to_citations(citations.citations)

# Include cts_urn field in response
"cts_urn": citation.references[0].cts_urn if citation.references and citation.references[0].cts_urn else None,
```

**Priority 2: Complete Integration Testing (MEDIUM PRIORITY - 1 hour)**  
Test API responses to verify CTS URNs appear in citation items.

## System Architecture

### Core Components

#### 1. CTS URN Mapper (`src/langnet/citation/cts_urn.py`)
- **Functionality**: Maps text citations to CTS URNs
- **Database**: Real CTS URN database with Greek authors (2,194 authors, 7,658 works)
- **Fallback**: Handles cases where direct mapping isn't available
- **Language Support**: Greek and Latin (Sanskrit planned)

#### 2. Citation Extraction (`src/langnet/citation/extractors/`)
- **Diogenes Extractor**: Extracts citations from Diogenes API responses
- **Standardized**: Creates consistent Citation objects
- **Integration**: Works with existing API pipeline

#### 3. API Integration (`src/langnet/asgi.py`)
- **Current**: Processes citations but lacks CTS URN mapping
- **Required**: Add CTS URN mapping before response generation
- **Status**: ⚠️ **IN PROGRESS**

### Data Flow

```
CURRENT (BROKEN):
Diogenes API → Citation Extraction → CTS URN Mapping → API Response (CTS URNs lost)

REQUIRED (WORKING):
Diogenes API → Citation Extraction → CTS URN Mapping → API Response (CTS URNs preserved)
```

## Testing and Verification

### Test Commands

#### Test CTS URN Mapper Functionality
```bash
# Test CTS URN mapper functionality
python -c "
from langnet.citation.cts_urn import CTSUrnMapper
m = CTSUrnMapper()
print('Verg. E. 2, 63:', m.map_text_to_urn('Verg. E. 2, 63'))
print('Cic. Fin. 2 24:', m.map_text_to_urn('Cic. Fin. 2 24'))
print('Livy ab urbe condita 1.1:', m.map_text_to_urn('Livy ab urbe condita 1.1'))
"
```

#### Test Current API (Missing CTS URNs)
```bash
# Test API (will show missing CTS URNs)
curl -s "http://localhost:8000/api/q?l=lat&s=lupus" | jq '.citations.items[0]'
# Look for "cts_urn" field - currently missing
```

#### Test API After Fix
```bash
# Test API with CTS URNs
curl -s "http://localhost:8000/api/q?l=lat&s=lupus" | jq '.citations.items[0].cts_urn'
# Should return CTS URN string or null
```

### Test Files

- `test_cts_urn_integration.py` - Basic CTS URN functionality tests
- `test_cts_urn_integration_fixed.py` - Fixed version of integration tests
- `test_cts_urn_integration_real.py` - Real database integration tests
- `test_api_citation_integration.py` - End-to-end API citation tests

## Database Integration

### Current Database State
- **Greek Authors**: 2,194 authors indexed ✅
- **Greek Works**: 7,658 works indexed ✅
- **Latin Authors**: Fallback mappings only ⚠️
- **Latin Works**: Needs full database population

### Database Schema
The CTS URN system uses a DuckDB database with the following structure:
- **Authors**: CTS author URNs and metadata
- **Works**: CTS work URNs and their relationships to authors
- **Mappings**: Text citation patterns to CTS URN mappings

### Performance
- **Indexing**: Fast lookup with pre-built indexes
- **Caching**: In-memory caching for frequently accessed URNs
- **Fallback**: Graceful handling of missing mappings

## Implementation Details

### CTS URN Format
```
urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1.1
│   │        │           │               │
│   │        │           │               └── Passage reference
│   │        │           └── Version identifier
│   │        └── Work identifier
│   └── Collection identifier
└── URN scheme
```

### Supported Collections
- **greekLit**: Ancient Greek literature
- **latinLit**: Latin literature  
- **sanskritLit**: Sanskrit literature (planned)

### Citation Patterns
The system handles various citation formats:
- **Vergil**: `Verg. A. 1.1`, `Aen. 1.1`, `Virgil Aeneid 1.1`
- **Cicero**: `Cic. Fin. 2.24`, `Cicero De Finibus 2.24`
- **Homer**: `Hom. Il. 1.1`, `Iliad 1.1`
- **Livy**: `Livy 1.1`, `Ab urbe condita 1.1`

## Future Enhancements

### Phase 3b: Current Work
- [x] CTS URN indexer rebuild ✅
- [x] Fallback mechanism enhancement ✅  
- [x] Integration testing ✅
- [ ] **API integration completion** ⚠️ **IN PROGRESS**

### Phase 3c: Future Work
- [ ] Enhanced CLI commands for CTS URN operations
- [ ] Educational rendering of CTS URNs
- [ ] Performance optimization for large datasets
- [ ] Comprehensive test coverage

### Phase 4: Cross-Language Support
- [ ] Add CTS URN support to Sanskrit Heritage results
- [ ] Add CTS URN support to CDSL results
- [ ] Create unified CTS URN helper for all languages
- [ ] Complete test coverage across languages

## Troubleshooting

### Common Issues

1. **Missing CTS URNs in API Response**
   - **Cause**: API integration not complete
   - **Fix**: Implement `_add_citations_to_response()` fix in `src/langnet/asgi.py`

2. **Database Connection Issues**
   - **Cause**: Database not initialized or corrupted
   - **Fix**: Run `python scripts/cts_urn_indexer.py` to rebuild database

3. **Fallback Mappings Only**
   - **Cause**: Latin database not fully populated
   - **Fix**: Populate Latin authors database (planned for Phase 3c)

### Debug Commands

```bash
# Check database status
python -c "
from langnet.citation.cts_urn import CTSUrnMapper
m = CTSUrnMapper()
print(f'Database loaded: {m.db is not None}')
if m.db:
    print(f'Greek authors: {len(m.authors)}')
    print(f'Greek works: {len(m.works)}')
"

# Test specific mappings
python -c "
from langnet.citation.cts_urn import CTSUrnMapper
m = CTSUrnMapper()
test_cases = ['Verg. E. 2, 63', 'Cic. Fin. 2 24', 'Livy ab urbe condita 1.1']
for case in test_cases:
    result = m.map_text_to_urn(case)
    print(f'{case}: {result}')
"
```

## Contact Information

For questions about the CTS URN system:
- **API Integration**: Focus on `src/langnet/asgi.py` `_add_citations_to_response()`
- **CTS URN Logic**: Review `src/langnet/citation/cts_urn.py`
- **Database Issues**: Check `scripts/cts_urn_indexer.py`
- **Testing**: Use `test_api_citation_integration.py`

---

**🚨 URGENT**: The CTS URN system is one small fix away from completion. Focus on API integration to complete the core functionality.

## Related Files

### Source Code
- `src/langnet/citation/cts_urn.py` - CTS URN mapper implementation
- `src/langnet/citation/extractors/` - Citation extractors
- `src/langnet/asgi.py` - API integration (needs fix)
- `scripts/cts_urn_indexer.py` - Database indexing script

### Tests
- `test_cts_urn_integration.py` - Basic functionality tests
- `test_cts_urn_integration_fixed.py` - Fixed integration tests
- `test_cts_urn_integration_real.py` - Real database tests
- `test_api_citation_integration.py` - End-to-end API tests

### Documentation
- `docs/CITATION_SYSTEM.md` - Comprehensive citation system docs
- `docs/plans/active/citation-system/` - Implementation plans