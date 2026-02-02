# CTS URN Citation System Plan

## Overview

Simple, working citation system that maps classical text references to CTS URNs (Canonical Text Service Uniform Resource Names).

## Core Components

### 1. CTS URN Indexer (`src/langnet/indexer/cts_urn_indexer.py`)

Parses PHI CD data files from `/home/nixos/Classics-Data/` to build a DuckDB index containing:
- Author names and IDs (e.g., `tlg0012` = Homer)
- Work titles and references
- CTS URN mappings (e.g., `urn:cts:greekLit:tlg0012.tlg001:1.1`)

**Usage:**
```bash
# Build the index
langnet-cli indexer build cts-urn --source /path/to/Classics-Data

# Query for abbreviations
langnet-cli indexer query "Hom. Il." --language grc
```

### 2. CTS URN Mapper (`src/langnet/citation/cts_urn.py`)

Maps text references to CTS URNs using the index:
- Input: `"Hom. Il. 1.1"` or `"perseus:abo:tlg,0011,001:911"`
- Output: `"urn:cts:greekLit:tlg0011.tlg001:911"`

**Example:**
```python
from langnet.citation.cts_urn import CTSUrnMapper

mapper = CTSUrnMapper()
urn = mapper.map_text_to_urn("perseus:abo:tlg,0011,001:911")
# Returns: "urn:cts:greekLit:tlg0011.tlg001:911"
```

### 3. Citation Models (`src/langnet/citation/models.py`)

Structured dataclasses for citations:
- `CitationType` - Enum for citation types (LINE_REFERENCE, DICTIONARY_ABBREVIATION, etc.)
- `TextReference` - Individual reference with author, work, location
- `Citation` - Collection of text references

## Architecture

```
Diogenes API Response
    ↓
.extract structured citations (origjump)
    ↓
CTSUrnMapper.map_text_to_urn()
    ↓
Database Lookup (DuckDB index)
    ↓
CTS URN (e.g., urn:cts:greekLit:tlg0012.tlg001:1.1)
```

## Files

| File | Purpose |
|------|---------|
| `src/langnet/indexer/cts_urn_indexer.py` | Parse PHI CD data, build DuckDB index |
| `src/langnet/citation/cts_urn.py` | Map text references to CTS URNs |
| `src/langnet/citation/models.py` | Citation dataclasses |
| `tests/test_cts_urn_basic.py` | Basic CTS URN tests |

## Commands

```bash
# Build CTS URN index
langnet-cli indexer build cts-urn

# Show index stats
langnet-cli indexer stats cts-urn

# List indexes
langnet-cli indexer list

# Query abbreviations
langnet-cli indexer query "Verg. A." --language lat
```

## Data Sources

- Greek texts: `/home/nixos/Classics-Data/tlg_e/*.idt`
- Latin texts: `/home/nixos/Classics-Data/phi-latin/*.idt`

## Status

**COMPLETE**: Core functionality is working. Indexer builds successfully and mapper correctly converts Perseus references to CTS URNs.