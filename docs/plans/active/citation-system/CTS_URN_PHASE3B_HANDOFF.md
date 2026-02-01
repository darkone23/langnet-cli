# CTS URN Citation System - Phase 3b COMPLETE Handoff

**Date**: 2026-02-02
**Status**: COMPLETE - Ready for Integration

## Executive Summary

The CTS URN indexer and citation mapper are complete. The key insight:

1. **URN Mapping**: Diogenes returns Perseus format → maps **directly** to CTS URN (no DB lookup)
2. **Enrichment**: Database provides full author/work names (optional enhancement)

## Data Flow: Citation → URN (Core)

```
Diogenes Response
  {"perseus:abo:phi,0474,005:2:2:124": "Cic. Verr. 2, 2, 50, § 124"}
         ↓
  _map_perseus_to_urn()  [Direct transformation - O(1)]
         ↓
  {"urn:cts:latinLit:phi0474.phi005:2.2.124": "Cic. Verr. 2, 2, 50, § 124"}
```

## Data Flow: Enrichment (Optional)

```
Perseus ID: phi0474.phi005
         ↓
  Database lookup (author_index + works)
         ↓
  Returns: "M. Tullius Cicero" - "In Verrem"
         ↓
  {"urn:cts:latinLit:phi0474.phi005:2.2.124": {
    "abbreviation": "Cic. Verr. 2, 2, 50, § 124",
    "author": "M. Tullius Cicero",
    "work": "In Verrem"
  }}
```

## Two Use Cases

### Use Case 1: URN Mapping (Required)
- Input: `perseus:abo:phi,0474,005:2:2:124`
- Output: `urn:cts:latinLit:phi0474.phi005:2.2.124`
- Method: Direct string transformation

### Use Case 2: Citation Enrichment (Optional)
- Input: `perseus:abo:phi,0474,005:2:2:124`
- Output: `{"author": "M. Tullius Cicero", "work": "In Verrem"}`
- Method: Database lookup by author_id + work_id

## Key Files

| File | Purpose |
|------|---------|
| `src/langnet/indexer/cts_urn_indexer.py` | DuckDB indexer using filename-based IDT scanning |
| `src/langnet/citation/cts_urn.py` | Perseus → CTS URN mapper |
| `src/langnet/indexer/core.py` | Status tracking fix |

## Mapping Reference

### Perseus Format → CTS URN

| Perseus Reference | CTS URN |
|-------------------|---------|
| `perseus:abo:tlg,0011,001:911` | `urn:cts:greekLit:tlg0011.tlg001:911` |
| `perseus:abo:phi,0690,003:1:2` | `urn:cts:latinLit:phi0690.phi003:1:2` |
| `perseus:abo:phi,0474,043:2:3:6` | `urn:cts:latinLit:phi0474.phi043:2:3:6` |
| `perseus:abo:phi,0119,001:17` | `urn:cts:latinLit:phi0119.phi001:17` |

### Format Specification

```
perseus:abo:{collection},{author_id},{work_id}:{location}

Where:
  - collection: tlg (Greek) or phi (Latin)
  - author_id: 4-digit number (zero-padded)
  - work_id: 3-digit number (zero-padded)
  - location: book:line:subdivisions
```

## Test Commands

```bash
# Test Perseus to CTS URN mapping
python3 -c "
from langnet.citation.cts_urn import CTSUrnMapper
m = CTSUrnMapper()
print(m.map_text_to_urn('perseus:abo:phi,0690,003:1:2'))
# Output: urn:cts:latinLit:phi0690.phi003:1:2
"

# Build/verify index
devenv shell langnet-cli -- indexer build-cts --source /home/nixos/Classics-Data --overwrite
duckdb ~/.local/share/langnet/cts_urn.duckdb "SELECT COUNT(*) FROM author_index;"
# Expected: 2194
```

## Integration Points

1. **DiogenesCitationExtractor**: Already outputs Perseus format
2. **Add URNs**: Call `CTSUrnMapper._map_perseus_to_urn()` on each citation key
3. **API Response**: Include URNs in citation metadata

## What's NOT Needed

- Author name lookups (Perseus IDs are authoritative)
- Work title matching (work_id is in the reference)
- Database queries for mapping (direct transformation)

## Verification

All citations from `example.cmd` and `lat.cmd` map correctly:

```bash
# From lat.cmd
perseus:abo:phi,0690,003:1:2 → urn:cts:latinLit:phi0690.phi003:1:2 ✅
perseus:abo:phi,0474,043:2:3:6 → urn:cts:latinLit:phi0474.phi043:2:3:6 ✅

# From example.cmd
perseus:abo:tlg,0011,001:911 → urn:cts:greekLit:tlg0011.tlg001:911 ✅
perseus:abo:tlg,0059,030:551b → urn:cts:greekLit:tlg0059.tlg030:551b ✅
```

## Next Steps

1. ✅ Phase 3b complete
2. **Phase 3c**: Wire URNs into API response (minor update to `asgi.py`)
3. **Phase 3d**: Add CTS API resolution (optional - resolves URNs to text)

---

*Phase 3b completed: 2026-02-02*
*Document: docs/plans/active/citation-system/CTS_URN_PHASE3B_HANDOFF.md*