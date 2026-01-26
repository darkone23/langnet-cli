# Cologne Sanskrit Lexicon (CDSL)

High-performance Sanskrit dictionary lookup from the [Cologne Digital Sanskrit Lexicon](https://www.sanskrit-lexicon.uni-koeln.de/) (CDSL).

## Overview

This module provides:
- **ETL Pipeline**: Convert CDSL XML data into indexed DuckDB databases
- **Fast Lookup**: O(log n) dictionary searches with prefix autocomplete
- **Transliteration**: Multi-scheme support (HK, IAST, Devanagari, SLP1)
- **CLI Interface**: Command-line tools for building and querying dictionaries

## Supported Dictionaries

| ID | Name | Approx. Entries |
|----|------|-----------------|
| MW | Monier-Williams (1899) | ~70,000 |
| AP90 | Apte Practical (1957-1959) | ~60,000 |
| BHS | Buddhist Hybrid Sanskrit | ~10,000 |
| PWG | PW Sanskrit-Wörterbuch | ~50,000 |

## Quick Start

### 1. Acquire CDSL Data

Download XML data from [cdsl.uni-koeln.de](https://www.sanskrit-lexicon.uni-koeln.de/scans/CDSL/index) and place in `~/cdsl_data/{DICT_ID}/`:

```
~/cdsl_data/MW/
├── web/
│   └── sqlite/
│       └── mw.sqlite  (or XML files)
└── tei/
    └── mw.xml
```

### 2. Build the Index

```bash
# Build a single dictionary
python -m langnet.cologne.load_cdsl MW

# Build with limit for testing
python -m langnet.cologne.load_cdsl MW --limit 1000

# Force rebuild (overwrite existing)
python -m langnet.cologne.load_cdsl AP90 --force

# Custom batch size and workers
python -m langnet.cologne.load_cdsl MW --batch-size 2000 --workers 4
```

### 3. Query from CLI

```bash
# Lookup a word
langnet-cli lookup MW agni

# Prefix search for autocomplete
langnet-cli prefix-search MW "agn"
```

## Diagnostic Logging

Enable verbose logging to monitor ETL progress:

```bash
LANGNET_LOG_LEVEL=INFO python -m langnet.cologne.load_cdsl MW
```

Expected output:
```
processing_batches dict_id=MW batches=47 workers=8 batch_size=1500
batch_progress dict_id=MW batch=5/47 entries=142 headwords=203 progress="5/47" pct_complete=10.6 elapsed_seconds=3.45
all_batches_complete dict_id=MW total_batches=47 total_entries=70342 total_headwords=89451 elapsed_seconds=127.3
indexing_bulk_insert dict_id=MW entries=70342 headwords=89451
indexing_complete dict_id=MW entries=70342 headwords=89451
```

## Python API

### Basic Lookup

```python
from langnet.cologne.core import SanskritCologneLexicon

cdsl = SanskritCologneLexicon()
result = cdsl.lookup_ascii("agni")
```

Returns:
```python
{
    "mw": [
        {
            "term": "agni",
            "iast": "agni",
            "hk": "agni",
            "deva": "अग्नि",
            "entries": [
                {"id": "1", "meaning": "fire", "subid": None},
                {"id": "2", "meaning": "the god of fire", "subid": None}
            ]
        }
    ],
    "ap90": [...]
}
```

### Direct Index Access

```python
from langnet.cologne.core import CdslIndex

with CdslIndex(Path("~/.local/share/langnet/mw.db")) as index:
    # Exact lookup
    results = index.lookup("MW", "agni")

    # Prefix search (for autocomplete)
    suggestions = index.prefix_search("MW", "agn", limit=10)

    # Dictionary info
    info = index.get_info("MW")
    # {'dict_id': 'MW', 'entry_count': 70342, ...}
```

### Transliteration

```python
from langnet.cologne.core import to_slp1

slp1_key = to_slp1("अग्नि")  # Returns "agni"
```

## Architecture

### ETL Pipeline

```
CDSL SQLite/XML
      ↓
  parse_batch()  [ProcessPoolExecutor]
      ↓
  entries + headwords
      ↓
 DuckDB bulk insert
      ↓
 Indexed database (.db)
```

### Database Schema

**entries**: Main dictionary entries
```
(dict_id, key, key_normalized, key2, key2_normalized, lnum, data, body, page_ref)
```

**headwords**: Fast lookup index
```
(dict_id, key, key_normalized, lnum, is_primary)
```

**dict_metadata**: Dictionary provenance
```
(dict_id, title, author, year, license, ...)
```

### Key Files

| File | Purpose |
|------|---------|
| `core.py` | Main ETL and query logic |
| `models.py` | Dataclass definitions |
| `parser.py` | XML entry parsing |
| `transcoder.py` | Transliteration utilities |
| `sql/schema.sql` | DuckDB schema |

## CLI Reference

### load_cdsl

Build a DuckDB index from CDSL data.

```bash
python -m langnet.cologne.load_cdsl DICT_ID [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--limit N` | None | Process only first N entries (for testing) |
| `--force` | False | Overwrite existing database |
| `--batch-size N` | auto | Entries per batch (auto: max(100, total/workers)) |
| `--workers N` | CPU count | Parallel processing workers |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LANGNET_LOG_LEVEL` | WARNING | DEBUG/INFO/WARNING/ERROR for verbose output |
| `LANGNET_CDSL_DICT_DIR` | ~/cdsl_data | Root directory for CDSL dictionaries |
| `LANGNET_CDSL_DB_DIR` | ~/.local/share/langnet | Output directory for .db files |

## Performance

Actual build times from production runs:

| Dictionary | Entries | Headwords | Batch Time | Total Build Time | DB Size | Lookup Time |
|------------|---------|-----------|------------|------------------|---------|-------------|
| MW | 286,537 | 573,074 | ~90 min | ~90 min | TBD | ~1ms |
| AP90 | 32,877 | 65,754 | ~0.6s | ~8 min | TBD | ~1ms |

Notes:
- Build time dominated by DuckDB bulk insert phase
- Batch parsing is fast; indexing into DB is the bottleneck

Optimization tips:
- Use `--batch-size 1000-2000` for large dictionaries
- Match `--workers` to CPU cores
- Ensure SSD storage for database

## Data Flow

```
User Input ("agni" in HK)
        ↓
to_slp1() → "agni"
        ↓
CdslIndex.lookup("MW", "agni")
        ↓
DuckDB query: WHERE key_normalized = 'agni'
        ↓
Parse results into SanskritDictionaryEntry
        ↓
Transliterate to IAST/Devanagari
        ↓
Return formatted response
```

## Integration

### With LanguageEngine

The Cologne module integrates with the main langnet engine:

```python
from langnet.engine.core import LanguageEngine

engine = LanguageEngine()
result = engine.handle_query(language="san", search_term="agni")
# Uses CdslIndex internally
```

### Adding New Dictionaries

1. Place CDSL data in `~/cdsl_data/{DICT_ID}/`
2. Run `python -m langnet.cologne.load_cdsl {DICT_ID}`
3. Query via `CdslIndex.lookup("{DICT_ID}", term)`

## Troubleshooting

### "Dictionary not indexed"
- Run `python -m langnet.cologne.load_cdsl DICT_ID` first
- Verify `LANGNET_CDSL_DB_DIR` points to correct location

### Slow Performance
- Reduce `--batch-size` if memory limited
- Increase `--workers` for CPU-bound workloads
- Ensure database is on SSD

### XML Parse Errors
- Validate CDSL XML format matches expected TEI structure
- Check source download integrity

## Dependencies

- `duckdb` - Embedded OLAP database
- `indic-transliteration` - Sanskrit transliteration
- `click` - CLI framework
- `structlog` - Structured logging

## License

CDSL data is under respective dictionary licenses. See [cdsl.uni-koeln.de](https://www.sanskrit-lexicon.uni-koeln.de/scans/CDSL/licence) for details.
