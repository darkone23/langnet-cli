# CTS URN System - Critical Status Update

**Date**: 2026-02-02  
**Status**: 🚨 **CRITICAL - API Integration Gap**  
**Priority**: HIGH - Must fix to complete core functionality

## 🚨 Critical Issue Summary

The CTS URN citation system is **90% complete** but has a **critical gap** at the API level that prevents the system from working end-to-end for users.

### The Problem
- **What**: The `/api/q` endpoint extracts citations from Diogenes but does NOT add CTS URNs to the response
- **Impact**: Users get citations but no standardized CTS URNs for external linking
- **Evidence**: API returns `citations.items` but missing `cts_urn` field
- **Root Cause**: `_add_citations_to_response()` function in `src/langnet/asgi.py` missing CTS URN mapping

### Current Status
✅ **WORKING**:
- CTS URN Mapper: Fully functional with real database
- Citation Extraction: Working from Diogenes API
- Database Integration: Greek authors indexed (2,194 authors, 7,658 works)
- Fallback Mappings: Enhanced for common Latin works

❌ **BROKEN**:
- API Integration: Citains processed but CTS URNs not included in `/api/q` responses

## 🔧 Immediate Fix Required

### File to Modify: `src/langnet/asgi.py`
### Function: `_add_citations_to_response()`

**Current Code (Lines ~180-200)**:
```python
def _add_citations_to_response(result: dict, lang: str) -> dict:
    citations = CitationCollection(citations=[])
    
    # Extract citations from Diogenes (Latin/Greek)
    if "diogenes" in result and isinstance(result["diogenes"], dict):
        diogenes_citations = _extract_citations_from_diogenes_result(result["diogenes"])
        if diogenes_citations.citations:
            citations.citations.extend(diogenes_citations.citations)
    
    # Add citations to result if we found any
    if citations.citations:
        result["citations"] = {
            "total_count": len(citations.citations),
            "language": lang,
            "items": [
                {
                    "text": citation.references[0].text if citation.references else "",
                    "type": citation.references[0].type.value if citation.references else "unknown",
                    "short_title": citation.short_title or "",
                    "full_name": citation.full_name or "",
                    "description": citation.description or "",
                    # ❌ cts_urn field is MISSING!
                }
                for citation in citations.citations  # ❌ Not using CTS URN mapping
            ],
        }
```

**Required Fix**:
```python
def _add_citations_to_response(result: dict, lang: str) -> dict:
    citations = CitationCollection(citations=[])
    
    # Extract citations from Diogenes (Latin/Greek)
    if "diogenes" in result and isinstance(result["diogenes"], dict):
        diogenes_citations = _extract_citations_from_diogenes_result(result["diogenes"])
        if diogenes_citations.citations:
            citations.citations.extend(diogenes_citations.citations)
    
    # Add CTS URNs to citations
    cts_mapper = CTSUrnMapper()
    updated_citations = cts_mapper.add_urns_to_citations(citations.citations)
    
    # Add citations to result if we found any
    if updated_citations:  # Use updated_citations instead of citations.citations
        result["citations"] = {
            "total_count": len(updated_citations),
            "language": lang,
            "items": [
                {
                    "text": citation.references[0].text if citation.references else "",
                    "type": citation.references[0].type.value if citation.references else "unknown",
                    "short_title": citation.short_title or "",
                    "full_name": citation.full_name or "",
                    "description": citation.description or "",
                    "cts_urn": citation.references[0].cts_urn if citation.references and citation.references[0].cts_urn else None,  # ✅ ADD THIS LINE
                }
                for citation in updated_citations  # ✅ Use updated_citations
            ],
        }
```

### Required Import
Add this line at the top of the file:
```python
from langnet.citation.cts_urn import CTSUrnMapper  # noqa: E402
```

## 🧪 Testing After Fix

### Test Command
```bash
# Clear cache and restart server
just cli cache-clear
pkill -f "uvicorn langnet.asgi:app"
devenv shell langnet-cli -- uvicorn langnet.asgi:app --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &

# Test API response includes CTS URNs
curl -s "http://localhost:8000/api/q?l=lat&s=lupus" | jq '.citations.items[0].cts_urn'
# Should return: "urn:cts:greekLit:tlg0001.tlg001" or similar

# Test multiple citations
curl -s "http://localhost:8000/api/q?l=lat&s=lupus" | jq '.citations.items[:3] | .[].cts_urn'
# Should show CTS URNs for citations
```

## 🎯 Expected Results After Fix

### Before Fix
```json
{
  "citations": {
    "items": [
      {
        "text": "Verg. E. 2, 63",
        "description": "Diogenes reference: perseus:abo:phi,0690,001:2:63",
        "cts_urn": null  // ❌ MISSING
      }
    ]
  }
}
```

### After Fix
```json
{
  "citations": {
    "items": [
      {
        "text": "Verg. E. 2, 63", 
        "description": "Diogenes reference: perseus:abo:phi,0690,001:2:63",
        "cts_urn": "urn:cts:greekLit:tlg0001.tlg001:2.63"  // ✅ PRESENT
      }
    ]
  }
}
```

## 📋 Impact Assessment

### High Priority (Must Fix)
- **User Experience**: CTS URNs are essential for external linking and standardization
- **Educational Value**: Students need standardized citations for research
- **System Completeness**: Core functionality is incomplete without this fix

### Medium Priority (After Fix)
- **Latin Database**: Populate Latin authors for better coverage
- **Performance**: Optimize citation processing
- **Enhanced Features**: CLI improvements, educational rendering

## 🚨 Timeline

### **Immediate** (1-2 hours)
1. ✅ Apply the fix to `src/langnet/asgi.py`
2. ✅ Restart server with cache clear
3. ✅ Test API responses for CTS URNs
4. ✅ Verify end-to-end functionality

### **Next Steps** (After API fix)
1. Update documentation to reflect completion
2. Run comprehensive test suite
3. Consider Latin database enhancement
4. Move to Phase 3c (enhanced features)

## 📞 Emergency Contact

This is a **critical blocking issue** for the CTS URN system completion. For questions:
- **API Fix**: Focus on `src/langnet/asgi.py` lines 180-200
- **CTS URN Logic**: `src/langnet/citation/cts_urn.py`
- **Testing**: Use `test_api_citation_integration.py`

---

**🚨 ACTION REQUIRED**: This fix is essential for the CTS URN system to function properly. The core components are working - we just need to bridge the final gap in the API response.