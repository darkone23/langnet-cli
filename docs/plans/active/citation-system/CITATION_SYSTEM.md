# Citation System Documentation

## Overview

This section contains comprehensive documentation for the langnet-cli citation system, which includes CTS URN support, dictionary abbreviation explanations, and educational rendering for classical language citations.

## Core Components

### 1. CTS URN Citation System - Phase 3: Enhancement

**Status**: **CRITICAL - API Integration Gap Identified**  
**Priority**: HIGH - Fix API integration to complete CTS URN system

#### 🚨 Critical Issue: API Integration Gap

**PROBLEM**: The CTS URN system is 90% complete but has a critical gap at the API level.

**CURRENT STATE**:
- ✅ CTS URN Mapper: Fully functional with real database
- ✅ Citation Extraction: Working from Diogenes API  
- ✅ Database Integration: Greek authors indexed (2,194 authors, 7,658 works)
- ❌ **API Integration**: `/api/q` endpoint extracts citations but does NOT add CTS URNs

**EVIDENCE**: API returns citations in `citations.items` but missing `cts_urn` field

**ROOT CAUSE**: `_add_citations_to_response()` function in `src/langnet/asgi.py` needs CTS URN mapping

**REQUIRED FIX**: Add CTS URN mapping before adding citations to API response

##### Immediate Action Required

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

#### Current System Status

##### ✅ Working Components
1. **CTS URN Mapper** - Fully functional
   - Maps text citations to CTS URNs
   - Handles Greek/Latin with fallback mechanism
   - Real database integration working

2. **Citation Extraction** - Fully functional  
   - Extracts from Diogenes API responses
   - Standardized Citation objects created

3. **Database** - Partially functional
   - Greek authors: 2,194 authors, 7,658 works ✅
   - Latin authors: Only fallback mappings ⚠️

##### ❌ Critical Missing Component
**API Level Integration**: Citains processed but CTS URNs not included in responses

#### Updated Data Flow

```
Diogenes API → Citation Extraction → CTS URN Mapping → API Response (CURRENTLY BROKEN HERE)
                                       ↑
                                  MISSING STEP
```

**REQUIRED FLOW**:
```
Diogenes API → Citation Extraction → CTS URN Mapping → API Response (WORKING)
```

#### Testing Commands

##### Test Current System
```bash
# Test CTS URN mapper functionality
python -c "
from langnet.citation.cts_urn import CTSUrnMapper
m = CTSUrnMapper()
print('Verg. E. 2, 63:', m.map_text_to_urn('Verg. E. 2, 63'))
print('Cic. Fin. 2 24:', m.map_text_to_urn('Cic. Fin. 2 24'))
print('Livy ab urbe condita 1.1:', m.map_text_to_urn('Livy ab urbe condita 1.1'))
"

# Test API (will show missing CTS URNs)
curl -s "http://localhost:8000/api/q?l=lat&s=lupus" | jq '.citations.items[0]'
# Look for "cts_urn" field - currently missing
```

##### After Fix
```bash
# Test API with CTS URNs
curl -s "http://localhost:8000/api/q?l=lat&s=lupus" | jq '.citations.items[0].cts_urn'
# Should return CTS URN string or null
```

#### Success Criteria

##### **PRIMARY GOAL (MUST COMPLETE)**
- [x] CTS URNs can be mapped from text citations ✅
- [x] Citations extracted from Diogenes API ✅  
- [x] CTS URNs included in `/api/q` responses ❌ **MISSING**
- [ ] System handles both Greek and Latin citations

##### **SECONDARY GOALS**
- [ ] Full Latin database coverage
- [ ] Performance optimization
- [ ] Comprehensive test coverage

#### Remaining Work (After API Fix)

##### Phase 3a: ✅ COMPLETE
- [x] Core CTS URN mapping
- [x] Database integration (Greek)
- [x] Citation extraction

##### Phase 3b: 🔄 IN PROGRESS  
- [x] CTS URN indexer rebuild
- [x] Fallback mechanism enhancement  
- [x] Integration testing
- [ ] **API integration completion** ⚠️ **IN PROGRESS**

##### Phase 3c: 📅 PENDING
- [ ] Enhanced CLI commands
- [ ] Educational rendering
- [ ] Performance optimization

#### Risks & Mitigations

##### **Critical Risk**: API Integration Gap
- **Impact**: CTS URN system appears non-functional to users
- **Mitigation**: Fix immediately, test with real API calls
- **Timeline**: 1-2 hours to implement and verify

##### **Secondary Risk**: Latin Database Coverage
- **Impact**: Latin citations rely on fallback only
- **Mitigation**: Can be addressed after API integration complete
- **Timeline**: 2-3 hours to populate Latin authors

#### Contact Information

For questions about this critical gap:
- **API Integration**: Focus on `src/langnet/asgi.py` `_add_citations_to_response()`
- **CTS URN Logic**: Review `src/langnet/citation/cts_urn.py`
- **Testing**: Use `test_api_citation_integration.py`

---

**🚨 URGENT**: The CTS URN system is one small fix away from completion. Focus on API integration to complete the core functionality.

### 2. Comprehensive Citation System Integration Plan

**Status**: 📋 TODO (Not Started)  
**Priority**: High (P1.5 - Between Citation Display and Enhanced Formatting)

#### Overview

Create a unified citation system that:
1. **Extends existing Diogenes `.origjump` parsing** with structured data
2. **Adds CTS URN support** for canonical text references
3. **Explains dictionary abbreviations** (cf. L&S, see GEL, MW, etc.)
4. **Provides educational explanations** for scholarly citations
5. **Enables "follow the citation" navigation**

#### Current State Analysis

##### ✅ Already Working
- **Diogenes extracts `.origjump` references** as `citations` dict
- **Perseus reference parsing** via existing parser
- **Basic citation fields** in `DiogenesDefinitionBlock`

##### 🚫 Missing Features
- **No structured citation model** - uses plain dict
- **No abbreviation explanations** - students see "cf. L&S" without explanation
- **No CTS URN support** - cannot handle canonical text references
- **No educational rendering** - citations appear as raw text
- **No cross-language consistency** - Sanskrit results lack citation support

#### Architecture Design

##### Core Data Models

```python
# src/langnet/citation/models.py
class CitationType(str, Enum):
    PERSEUS_REFERENCE = "perseus_reference"
    CTS_URN = "cts_urn"
    DICTIONARY_ABBREVIATION = "dictionary_abbreviation"
    CROSS_REFERENCE = "cross_reference"
    HERITAGE_REFERENCE = "heritage_reference"

@dataclass
class Citation:
    type: CitationType
    reference: str                    # Original citation text
    target: str | None = None         # Resolvable URL
    description: str | None = None    # Human explanation
    abbreviation: str | None = None   # For dictionary citations
    work_title: str | None = None     # Full work title
    author: str | None = None         # Author name
```

##### Dictionary Abbreviation Registry

```python
DICTIONARY_ABBREVS = {
    "L&S": ("Lewis and Short", "Latin Dictionary (1879)"),
    "GEL": ("Liddell-Scott-Jones", "Greek-English Lexicon"),
    "MW": ("Monier-Williams", "Sanskrit-English Dictionary"),
    "DP": ("Dharmakīrti", "Pramāṇavārttika"),
    "cf.": ("compare", "Cross-reference marker"),
    "vid.": ("see", "Latin 'vide' abbreviation"),
    "G.": ("Greek", "Greek language marker"),
    "L.": ("Latin", "Latin language marker"),
    "S.": ("Sanskrit", "Sanskrit language marker"),
}
```

#### Implementation Phases

##### Phase 1: Core Models & Parser Updates (2-3 days)
1. **Create citation models** (`src/langnet/citation/`)
2. **Enhance Diogenes parser** to use new models
3. **Add abbreviation extractor** for dictionary citations
4. **Maintain backward compatibility** with existing API

**Deliverables**:
- `Citation` dataclass with rich metadata
- `CitationExtractor` for parsing multiple formats
- Updated Diogenes parser with new citation model

##### Phase 2: CTS URN Integration (2-3 days)
5. **Create CTS URN module** with Sanskrit support
6. **Map Perseus references → CTS URNs**
7. **Add Sanskrit collection** (`sanskritLit`)
8. **Test with real texts** (Iliad, Aeneid, Bhagavad Gita)

**Deliverables**:
- `CTSUrn` dataclass with parsing/validation
- Perseus-to-CTS mapping utilities
- Sanskrit CTS examples and tests

##### Phase 3: Educational Rendering (1-2 days)
9. **Create Foster citation renderer**
10. **Add CLI explanation commands**
11. **Enhance API response formatting**

**Deliverables**:
- `CitationRenderer` for educational display
- `explain-citation` CLI command
- Enhanced API citation formatting

##### Phase 4: Cross-Language Support (2-3 days)
12. **Add citations to Heritage results**
13. **Add citations to CDSL results**
14. **Create citation helper for all languages**
15. **Comprehensive testing**

**Deliverables**:
- Citation support for all backends
- Unified citation display across languages
- Complete test coverage

#### Educational Value

##### For Students:
1. **Understand Abbreviations**: "cf. L&S" → "Lewis and Short Latin Dictionary"
2. **Follow Citations**: Clickable links to referenced texts
3. **Learn Scholarly Conventions**: Understand standard citation formats
4. **Cross-Reference**: Connect definitions across dictionaries

##### Example Workflow:
```
Student query: "amor"
Result includes: "cf. L&S 127.3"
Student action: langnet-cli explain-citation "L&S"
Response: "Lewis and Short Latin Dictionary (1879)"
Student action: langnet-cli follow-citation "L&S 127.3"
Result: Opens Perseus/CTS reference
```

#### Timeline

**Total**: 7-11 days
```
Phase 1 (2-3 days): Core Models & Parser Updates
Phase 2 (2-3 days): CTS URN Integration  
Phase 3 (1-2 days): Educational Rendering
Phase 4 (2-3 days): Cross-Language Support
```

#### Dependencies

1. **Sanskrit Heritage Integration** - ✅ COMPLETED
2. **Existing Diogenes Parser** - ✅ COMPLETED
3. **Foster Renderer Infrastructure** - ✅ COMPLETED
4. **CLI Framework** - ✅ COMPLETED

#### Impact Assessment

This system transforms langnet-cli from a **lookup tool** into a **citation-aware research assistant**, significantly enhancing its educational value for classical language students and researchers.

## Related Files

### Active Work
- `docs/plans/active/citation-system/` - Detailed implementation plans and handoffs

### Key Source Files
- `src/langnet/citation/` - Citation system implementation
- `src/langnet/asgi.py` - API integration (needs CTS URN fix)
- `test_api_citation_integration.py` - Integration tests

### Archived Documents
- `docs/ARCHIVES/OLD_HANDOFFS/` - Previous handoff documents
- `docs/ARCHIVES/COMPLETED_PLANS/` - Completed implementation plans