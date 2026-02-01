# Technical Reference

## Architecture

```
                        ┌─────────────────────┐
                        │   langnet-cli        │
                        │ (src/langnet/cli)   │
                        └──────────┬──────────┘
                                   │
                        ┌──────────▼──────────┐
                        │   langnet/asgi.py    │  ← Starlette ASGI app
                        │   /api/q endpoint    │
                        └──────────┬──────────┘
                                   │
                        ┌──────────▼──────────┐
                        │ LanguageEngine      │
                        │ (query routing)     │
                        └──────────┬──────────┘
               ┌────────────┬────┴────┬────────────┐
               │            │         │            │
    ┌──────────▼───┐ ┌──────▼──┐ ┌────▼────┐ ┌─────▼──────┐
    │ DiogenesScraper│ │Whitakers│ │Classics │ │Cologne    │
    │ (Greek/Latin) │ │ Words   │ │Toolkit  │ │(Sanskrit) │
    └───────────────┘ └─────────┘ └─────────┘ └───────────┘
           │              │          │            │
    ┌──────▼─────┐  ┌──────▼──┐ ┌────▼────┐ ┌────▼────┐
    │ DuckDB     │  │ whitakers│ │ CLTK    │ │ CDSL    │
    │ cache      │  │ -words   │ │ models  │ │ data    │
    └────────────┘  └─────────┘ └─────────┘ └─────────┘
```

## Encoding Support

### Greek (Betacode)

Greek queries accept [Betacode](https://en.wikipedia.org/wiki/Betacode) input:

| Char | Example | Meaning |
|-----|---------|---------|
| `*` | `*a` | rough breathing |
| `\` | `a\` | smooth breathing |
| `/` | `a/` | iota subscript |
| `+` | `a+` | acute |
| `=` | `a=` | circumflex |
| `|` | `a|` | grave |

```sh
langnet-cli query grc *ou=sia   # οὐσία (being)
langnet-cli query grc *qw=s     # πῶς (how?)
```

### Sanskrit (Velthuis)

Sanskrit queries accept [Velthuis](https://en.wikipedia.org/wiki/Velthuis) encoding:

| Pattern | Example | Devanagari |
|---------|---------|------------|
| `.a` | `.agni` | अग्नि |
| `.i` | `.indra` | इन्द्र |
| `.u` | `.uru` | उरु |

```sh
langnet-cli query san .agni      # अग्नि (fire)
langnet-cli query san .rAmAyaNa # रामायण
```

## Response Caching

### How It Works

1. **Cache lookup**: Check DuckDB for matching (lang, word) key
2. **Backend query**: If miss, query all backends for language
3. **Cache store**: Persist result to DuckDB
4. **Cache return**: Return cached result on hit

### Cache Backend

- **Database**: [DuckDB](https://duckdb.org/) (embedded SQL)
- **Location**: `~/.local/share/langnet/langnet_cache.duckdb`
- **Table schema**:
  ```sql
  CREATE TABLE query_cache (
    id INTEGER PRIMARY KEY,
    lang VARCHAR NOT NULL,
    query VARCHAR NOT NULL,
    result VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  ```

### Cache Operations

```sql
-- View cached entries
SELECT lang, query, created_at FROM query_cache LIMIT 10;

-- View by language
SELECT * FROM query_cache WHERE lang = 'lat';

-- View entries older than 24 hours
SELECT * FROM query_cache WHERE created_at < NOW() - INTERVAL '24 hours';

-- Clear all entries
TRUNCATE query_cache;

-- Clear by language
DELETE FROM query_cache WHERE lang = 'lat';
```

### Debug Cache Behavior

Enable DEBUG logging to trace cache operations:

```
# First query (cache miss)
query_started lang=lat word=lupus
cache_miss lang=lat query=lupus
backend_failed backend=diogenes error=...
query_completed lang=lat word=lupus

# Second query (cache hit - skips backend calls)
query_started lang=lat word=lupus
cache_hit lang=lat query=lupus
query_cached lang=lat word=lupus
```

## Backend Details

### Diogenes (Greek/Latin)

- HTTP client to local Perl server at `http://localhost:8888`
- Parses HTML responses using state machine
- Splits by `<hr />` separators, classifies chunks
- **Gotcha**: Perl server leaks threads; run `just langnet-dg-reaper`
- **Status**: ✅ FULLY IMPLEMENTED

### Whitaker's Words (Latin)

- CLI wrapper around `whitakers-words` binary
- Line-based parsing with modular reducers:
  - `SensesReducer`: dictionary senses (`;`)
  - `CodesReducer`: morphological codes (`]`)
  - `FactsReducer`: word data lines
- **Gotcha**: Returns `sh.Command`, not string
- **Status**: ✅ FULLY IMPLEMENTED

### CLTK (Latin/Greek)

- Uses spaCy Greek model (`grc_odycy_joint_sm`)
- Downloads ~500MB on first query
- Latin lemmatization via `lat_models_cltk`
- **Status**: ✅ FULLY IMPLEMENTED

### CDSL (Sanskrit)

- Cologne Sanskrit Lexicon (Monier-Williams, AP90)
- Velthuis ASCII input → Unicode conversion
- **Status**: ✅ FULLY IMPLEMENTED with Heritage Platform integration

### Heritage Platform (Sanskrit)

- Lark-based parser migration completed
- Smart encoding detection (Devanagari, IAST, Velthuis, SLP1, HK, ASCII)
- Enhanced normalization with ASCII enrichment
- **Status**: ✅ FULLY IMPLEMENTED

### Foster Functional Grammar

- Core pedagogical approach across all three languages
- Shows what words *do* in sentences, not just technical labels
- **Examples**: "Naming Function" (nominative), "Receiving Function" (accusative)
- **Status**: ✅ FULLY IMPLEMENTED

## Implementation Status

### ✅ Fully Implemented & Working
- **Core Query Engine**: Multi-language routing and aggregation
- **All Language Backends**: Diogenes, Whitaker's, CLTK, CDSL, Heritage
- **Foster Functional Grammar**: All three languages complete
- **Normalization Pipeline**: 381 tests passing, robust validation
- **Response Caching**: DuckDB-based caching system
- **AI-Assisted Development**: Multi-model persona system

### 🔄 Partially Implemented
- **ASCII Enrichment**: Sanskrit only, Latin/Greek pending
- **Citation Display**: Basic integration, needs enhancement
- **Universal Schema**: Design complete, implementation pending

### ⏳ Not Started
- **Fuzzy Search**: Critical for user experience
- **DICO Integration**: French-Sanskrit dictionary
- **CTS URN System**: Scholarly text references
- **Cross-Lexicon Etymology**: Advanced research feature

For detailed roadmap and priorities, see [docs/TODO.md](docs/TODO.md).

## Data Models

Uses Python `dataclass` with `cattrs` for serialization:

```python
from dataclasses import dataclass
from cattrs import Converter

@dataclass
class WordResult:
    lemma: str
    meanings: list[str]

converter = Converter(omit_if_default=True)
result = converter.unstructure(word_obj)
```

## Startup Behavior

Eager initialization at server start (~16s total):

| Component | Time | Notes |
|-----------|------|-------|
| ClassicsToolkit | ~15s | spaCy Greek model download |
| WhitakersWords | ~0.1s | Binary validation |
| DiogenesScraper | ~1s | Connectivity check |

First queries trigger CLTK model downloads (~500MB).

## Further Reading

### 📚 Complete Documentation

- **[docs/README.md](docs/README.md)** - Complete documentation hub and navigation guide
- **[docs/TODO.md](docs/TODO.md)** - Current roadmap, active development, and priorities
- **[docs/DEVELOPER.md](docs/DEVELOPER.md)** - Development setup, conventions, and AI workflow
- **[docs/PEDAGOGICAL_PHILOSOPHY.md](docs/PEDAGOGICAL_PHILOSOPHY.md)** - Core educational approach and Foster functional grammar
- **[docs/PEDAGOGY.md](docs/PEDAGOGY.md)** - Pedagogical goals and priorities

### Project Planning

- **[docs/plans/README.md](docs/plans/README.md)** - Overview of project plans (active, completed, todo)
- **[docs/plans/ACTIVE_WORK_SUMMARY.md](docs/plans/ACTIVE_WORK_SUMMARY.md)** - Current implementation status

### AI Development

- **[docs/opencode/MULTI_MODEL_GUIDE.md](docs/opencode/MULTI_MODEL_GUIDE.md)** - Multi-model AI strategy
- **[docs/opencode/LLM_PROVIDER_GUIDE.md](docs/opencode/LLM_PROVIDER_GUIDE.md)** - LLM provider configuration
- **[.opencode/skills/README.md](../.opencode/skills/README.md)** - AI-assisted development skills
