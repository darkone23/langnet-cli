# Diogenes Scraper

HTTP client and HTML parser for [diogenes](https://d.iogen.es/web/) - a Perl server providing programmatic access to Perseus classical texts and lexica.

## Background

Diogenes is a Perl web application that wraps the Perseus Digital Library's tools:
- **Perseus Morpheus**: Greek/Latin morphological analysis
- **LSJ**: Liddell-Scott-Jones Greek-English Lexicon (1940)
- **Lewis & Short**: Latin-English Dictionary (1879)

The server runs as a standalone Perl process, exposing HTTP endpoints for parsing words and retrieving dictionary entries.

## Capabilities

- **Word parsing**: GET `/Perseus.cgi?do=parse&lang=<lat|grk>&q=<word>`
- **Dictionary lookup**: Integrated with parse results
- **Greek betacode**: Auto-converts UTF-8 to betacode for diogenes
- **HTML parsing**: BeautifulSoup extraction of lexicon entries

## Usage

```python
from langnet.diogenes.core import DiogenesScraper, DiogenesLanguages

scraper = DiogenesScraper(base_url="http://localhost:8888")

# Latin query
result = scraper.parse_word("benevolens", DiogenesLanguages.LATIN)
# DiogenesResultT(chunks=[...], dg_parsed=True)

# Greek query (UTF-8 auto-converted to betacode)
result = scraper.parse_word("οὐσία", DiogenesLanguages.GREEK)
```

## Architecture

### DiogenesChunkType (Classification)

The parser classifies each HTML fragment into types:

| Type | Description | Example |
|------|-------------|---------|
| `PerseusAnalysisHeader` | Morphology from Morpheus | "amabat: V3IAI---" |
| `NoMatchFoundHeader` | Logeion link shown | Perseus lookup link |
| `DiogenesMatchingReference` | Dictionary entry found | LSJ/L&S definitions |
| `DiogenesFuzzyReference` | Partial match | Did you mean... |
| `UnknownChunkType` | Unrecognized | Fallback |

### Parsing Pipeline

```
HTTP Response (text/html)
    ↓
Split by <hr /> (document separators)
    ↓
For each document:
    ├─ get_next_chunk(): Classify HTML via BeautifulSoup
    │   ├─ Find <h1>Perseus an...</h1> → PerseusAnalysisHeader
    │   ├─ Find .logeion-link → NoMatchFoundHeader
    │   └─ Find prevEntry onclick → Reference
    │
    └─ process_chunk(): Extract structured data
        ├─ handle_morphology(): Parse <li>/<p> tags
        ├─ handle_references(): Parse #sense blocks
        └─ Serialize to Pydantic model
    ↓
Aggregate chunks into DiogenesResultT
```

### handle_references() Details

This function extracts dictionary entries with:
- **Senses**: Numbered definitions (parsed from `<b>` tags)
- **Citations**: Author/work references (`.origjump` links)
- **Headings**: Section headers (short text with trailing period)
- **Warnings**: Parenthesized notes (extracted and removed)

Hierarchical indentation is tracked via CSS `padding-left` values, converted to n-dimensional coordinates for flat storage.

## Integration Points

- **Input**: Word string, language code (lat/grk)
- **Output**: `DiogenesResultT` Pydantic model
- **Called by**: `LanguageEngine.handle_query()` for Latin/Greek

## Sidecar Process

A companion process (`langnet/diogenes/cli_util.py`) runs in a loop to clean up zombie threads:

```sh
python3 -m langnet.diogenes.cli_util                    # loop mode (default interval: 3600s)
python3 -m langnet.diogenes.cli_util --interval 1800    # loop mode (30s interval)
python3 -m langnet.diogenes.cli_util reap --once        # one-shot mode
```

This process:
1. Scans for `perl <defunct>` zombie processes
2. Finds the parent PID (PPID) of each zombie
3. Sends SIGTERM to the parent (the Diogenes Perl server)
4. Sleeps for the configured interval before repeating

### Server Termination

The sidecar terminates the Diogenes server (via SIGTERM to its parent process). This is necessary because zombie processes cannot be killed directly - you must kill their parent so init can reap the zombies.

**An external process manager is required** to restart the Diogenes server after it is terminated. Without one, the server will remain down until manually restarted.

## Known Issues

1. **Zombie threads**: Diogenes Perl process leaks threads on certain queries. The `just sidecar` command runs continuously, checking every hour and killing orphaned parent processes.
2. **Chunk classification brittleness**: Relies on specific HTML structure that may change
3. **Fuzzy matching**: DiogenesFuzzyReference not properly distinguished
4. **Duplicate senses**: Code attempts deduping but may miss edge cases

## Configuration

- **Default URL**: `http://localhost:8888/`
- **Override**: Pass `base_url` to `DiogenesScraper.__init__()`
- **Timeout**: No timeout set (relies on requests defaults)
