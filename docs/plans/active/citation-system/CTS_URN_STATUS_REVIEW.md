# CTS URN Citation System - Status Review & Integration Plan

**Date**: 2026-02-02
**Status**: Phase 2 COMPLETED, Phase 3 IN PROGRESS

---

## Executive Summary

The CTS URN indexer has been successfully rebuilt with filename-based indexing, providing **2,194 authors** and **7,658 works** (up from 1,570 authors). However, the citation system integration needs to be completed - the `CTSUrnMapper` still looks for an old SQLite database while we're now using a DuckDB-based indexer.

---

## Completed Work ✅

### 1. CTS URN Indexer Rebuild (DONE)
- **Location**: `/src/langnet/indexer/cts_urn_indexer.py`
- **Method**: Filename-based IDT file scanning (no longer uses authtab)
- **Authors**: 2,194 (target was 2,189 - exceeded!)
- **Works**: 7,658
- **Database**: DuckDB at `~/.local/share/langnet/cts_urn.duckdb`

### 2. Status Tracking Bug Fix (DONE)
- **Location**: `/src/langnet/indexer/core.py:61-84`
- **Problem**: CLI queries failed because `is_built()` only checked in-memory status
- **Solution**: Added `_check_db_built()` to verify database content

### 3. URN Format Verification (DONE)
```
Cicero De Finibus:  urn:cts:latinLit:lat0474.lat043  ✅
Plato Alcibiades i: urn:cts:greekLit:tlg0059.tlg001   ✅
Vergil Aeneid:     urn:cts:latinLit:lat0690.lat003   ✅
```

---

## Integration Gap ⚠️

### Current Problem
The `CTSUrnMapper` class (`src/langnet/citation/cts_urn.py`) expects:
- **SQLite database** at `/tmp/classical_refs.db`
- **Schema**: `author_index(author_id, author_name, cts_namespace)` and `works(canon_id, work_title, cts_urn)`

But we now have:
- **DuckDB database** at `~/.local/share/langnet/cts_urn.duckdb`
- **Schema**: `author_index(author_id, author_name, language, namespace)` and `works(canon_id, author_id, work_title, cts_urn)`

### Required Integration Work
1. Update `CTSUrnMapper` to use DuckDB instead of SQLite
2. Update database path lookup to check `~/.local/share/langnet/cts_urn.duckdb`
3. Map column names between old and new schemas
4. Write integration tests that verify real data flow

---

## Data Flow: Where We Are

```
User Query (e.g., "lupus")
       ↓
Diogenes Backend
       ↓
DiogenesCitationExtractor → extracts citations (e.g., "Verg. A. 1.1")
       ↓
[ GAP ] CTSUrnMapper should map to CTS URN
       ↓
[ GAP ] Return URN in API response
```

---

## What Still Needs to Be Done

### Priority 1: Wire CTSUrnMapper to New Indexer (2-3 hours)
1. Update `CTSUrnMapper.__init__()` to accept DuckDB path
2. Update `_get_db_path()` to check new location
3. Update `_load_author_cache()` for new schema
4. Update `_load_work_cache()` for new schema
5. Test with real citations from Diogenes

### Priority 2: Integration Tests (2-3 hours)
1. Create `tests/test_cts_urn_indexer_integration.py`
2. Test: Build index → Query index → Map to URN
3. Test: End-to-end with real Diogenes citations
4. Test: Cicero, Vergil, Plato mappings

### Priority 3: API Integration (1-2 hours)
1. Ensure citations flow through `/api/q` endpoint
2. Verify URNs appear in JSON responses

---

## Test Commands

```bash
# Test current indexer
devenv shell langnet-cli -- indexer query-cts "cicero" --language lat
devenv shell langnet-cli -- indexer query-cts "plato" --language grc

# Check database directly
duckdb ~/.local/share/langnet/cts_urn.duckdb "SELECT COUNT(*) FROM author_index;"
duckdb ~/.local/share/langnet/cts_urn.duckdb "SELECT a.author_name, w.work_title, w.cts_urn FROM works w JOIN author_index a ON w.author_id=a.author_id WHERE a.author_name LIKE '%Cicero%' LIMIT 5;"

# Test URN mapper (will fail until integration is done)
python -c "
from langnet.citation.cts_urn import CTSUrnMapper
m = CTSUrnMapper()
print(m.map_text_to_urn('Cic. Fin. 2 24'))
"
```

---

## Schema Comparison

### Old Schema (SQLite)
```sql
author_index(author_id, author_name, cts_namespace)
works(canon_id, work_title, cts_urn)
```

### New Schema (DuckDB)
```sql
author_index(author_id, author_name, language, namespace)
works(canon_id, author_id, work_title, work_reference, cts_urn)
```

### Mapping Required
- `author_index.cts_namespace` → `author_index.namespace`
- `works.canon_id` → `works.work_reference` (with prefix)
- Need JOIN between tables to get author name for works

---

## Success Criteria

1. ✅ CTS URN indexer builds with 2,000+ authors
2. ✅ CLI queries work: `indexer query-cts "cicero"`
3. ⚠️ CTSUrnMapper reads new DuckDB database
4. ⚠️ Real Diogenes citations map to valid URNs
5. ⚠️ Integration tests pass

---

## Next Steps

1. Update this document in `/docs/plans/active/citation-system/`
2. Modify `CTSUrnMapper` to use DuckDB
3. Write integration tests
4. Verify end-to-end flow

---

*Review completed: 2026-02-02*