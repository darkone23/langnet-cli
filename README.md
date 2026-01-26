# langnet-cli

A unified backend API for querying classical language data (Latin, Greek, Sanskrit) from multiple lexicon sources.

## Overview

langnet-cli aggregates several classical language resources into a single query interface:

| Source | Latin | Greek | Sanskrit |
|--------|-------|-------|----------|
| Diogenes (Perseus) | lexicon + morphology | lexicon + morphology | - |
| Whitaker's Words | morphology | - | - |
| CLTK | lexicon | - | lemmatization |
| CDSL (Cologne) | - | - | dictionary |

## Why langnet-cli?

Classical language resources are fragmented across many projects, each with different interfaces, data formats, and installation requirements. langnet-cli provides:

- **Unified API**: Single endpoint for querying multiple backends
- **Response aggregation**: Results from different sources merged by language
- **Eager initialization**: All toolkits and ML models load at server startup (~15s for spaCy Greek model)
- **Extensible architecture**: Add new backends by implementing the scraper interface

## Quick Start

```sh
# Enter development environment
devenv shell

# Start API server (uvicorn-run wraps uvicorn langnet.asgi:app)
uvicorn-run

# CLI usage
langnet-cli query lat lupus
langnet-cli query grc Nike
langnet-cli verify
langnet-cli langs

# API usage (alternative to CLI)
curl 'localhost:8000/api/q?l=lat&s=benevolens' | jq .
curl --data-urlencode 's=*ousi/a' --data-urlencode 'l=grk' 'localhost:8000/api/q' | jq .
curl --data-urlencode 's=.agni' --data-urlencode 'l=san' 'localhost:8000/api/q' | jq .
```

## Encoding Support

langnet-cli supports ASCII-encoded input for Greek and Sanskrit, eliminating the need for Unicode characters in queries.

### Greek (Betacode)

Greek queries accept [Betacode](https://en.wikipedia.org/wiki/Betacode) input, an ASCII encoding used by classical scholars:

| Character | Example | Meaning |
|-----------|---------|---------|
| `*` | `*a` | alpha with rough breathing |
| `\` | `a\` | alpha with smooth breathing |
| `/` | `a/` | alpha with iota subscript |
| `+` | `a+` | alpha with acute |
| `=` | `a=` | alpha with circumflex |
| `|` | `a\|` | alpha with grave |

**Examples:**
```sh
# Query using Betacode
curl --data-urlencode 's=*ou=sia' --data-urlencode 'l=grk' 'localhost:8000/api/q' | jq .
# Returns: οὐσία (being, essence)

langnet-cli query grc *qw=s
# Returns: πῶς (how?)
```

### Sanskrit (Velthuis)

Sanskrit queries accept [Velthuis](https://en.wikipedia.org/wiki/Velthuis) encoding, a LaTeX-based ASCII representation of Devanagari:

| Pattern | Example | Devanagari |
|---------|---------|------------|
| `.a` | `.agni` | अग्नि (fire) |
| `.i` | `.indra` | इन्द्र (Indra) |
| `.u` | `.uru` | उरु (wide) |
| `.m` | `.karman` | कर्मन् (action) |
| `.h` | `.buddhi.h` | बुद्धिह् (intellect) |

**Examples:**
```sh
# Query using Velthuis
curl --data-urlencode 's=.agni' --data-urlencode 'l=san' 'localhost:8000/api/q' | jq .
# Returns: अग्नि (fire, Agni)

langnet-cli query san .rAmAyaNa
# Returns: रामायण (Ramayana)
```

The transliteration layer automatically converts ASCII input to Unicode before querying backend services.

## Dependencies

### Required (Manual Installation)

1. **diogenes** - Perl server for Perseus lexicon data
   - Repository: https://github.com/pjheslin/diogenes
   - Run at `http://localhost:8888`
   - Required for Greek/Latin queries
   - **Note**: Leaks threads; run `just sidecar` continuously to clean up
   - **Note**: Instructions for installing/running Diogenes are maintained upstream and are out of scope for this project

2. **whitakers-words** - Latin morphological analyzer
   - Binary: `~/.local/bin/whitakers-words`
   - Repository: https://github.com/mk270/whitakers-words
   - Optional: Latin-only, but highly recommended for accurate morphology
   - Prebuilt x86_64 binaries only. ARM users: build from source following upstream instructions.

### Managed by Tests

3. **CLTK models** - Classical language data for Python library
   - Installed to `~/cltk_data/` by test suite
   - Downloads lat_models_cltk on first run

4. **CDSL data** - Cologne Sanskrit Lexicon files
   - Installed to `~/cdsl_data/` by test suite
   - MW (Monier-Williams) and AP90 (Apte) dictionaries

## Startup Behavior

The API server performs eager initialization at startup to ensure fast queries:

1. **ClassicsToolkit**: Loads CLTK Latin models (~14s on first run) and spaCy Greek model
2. **WhitakersWords**: Validates binary is available
3. **DiogenesScraper**: Tests connectivity to local Perl server

This means the first `uvicorn-run` will take ~15-30 seconds to start, but all subsequent queries are fast (<1s).

```
# Typical startup time breakdown
Initializing ClassicsToolkit... ~15s (spaCy grc_odycy_joint_sm model)
Validating Whitakers binary... ~0.1s
Checking Diogenes connectivity... ~1s
Total startup time... ~16s
```

## CLI Reference

The `langnet-cli` provides a unified interface to query classical language resources.

### Commands

| Command | Description |
|---------|-------------|
| `langnet-cli query <lang> <word>` | Query a word in Latin (lat), Greek (grc), or Sanskrit (san) |
| `langnet-cli verify` | Check backend connectivity and health status |
| `langnet-cli health` | Alias for verify |
| `langnet-cli langs` | List supported language codes |

### Options

- `--api-url URL` - Override API server URL (default: `http://localhost:8000`)
- `--output json\|table` - Output format for query results (default: table)
- `--timeout SECONDS` - Request timeout for health checks

### Examples

```sh
# Query Latin word
langnet-cli query lat lupus

# Query Greek word (table output)
langnet-cli query grc Nike

# Query with JSON output (pipable to jq)
langnet-cli query lat lupus --output json | jq '.diogenes'

# Check all backends are healthy
langnet-cli verify

# Query Sanskrit
langnet-cli query san agni
```

## Architecture

```
                              ┌─────────────────────┐
                              │   langnet-cli       │
                              │ (src/langnet/cli)  │
                              └──────────┬──────────┘
                                         │
                              ┌──────────▼──────────┐
                              │   langnet/asgi.py   │  ← Starlette ASGI app
                              │   /api/q endpoint   │
                              └──────────┬──────────┘
                                         │
                              ┌──────────▼──────────┐
                              │ LanguageEngine      │
                              │ (src/langnet/engine)│  ← Query routing & aggregation
                              └──────────┬──────────┘
                     ┌────────────┬────┴────┬────────────┐
                     │            │         │            │
          ┌──────────▼───┐ ┌──────▼──┐ ┌────▼────┐ ┌─────▼──────┐
          │ DiogenesScraper│ │Whitakers│ │Classics │ │Cologne    │
          │ (Greek/Latin) │ │ Words   │ │Toolkit  │ │(Sanskrit) │
          └───────────────┘ └─────────┘ └─────────┘ └───────────┘
```

## Project Structure

```
src/langnet/
├── asgi.py                  # Starlette ASGI application entry point
├── cli.py                   # CLI interface (Click-based)
├── core.py                  # LangnetWiring (dependency injection container)
├── engine/
│   └── core.py              # LanguageEngine (query orchestration)
├── diogenes/
│   ├── core.py              # DiogenesScraper (HTTP client + HTML parsing)
│   ├── cli_util.py          # Zombie process reaper utility
│   └── README.md            # Diogenes integration docs
├── whitakers_words/
│   ├── core.py              # WhitakersWords (CLI wrapper + line parsing)
│   ├── lineparsers/         # Modular line parsers (senses, codes, facts)
│   └── README.md            # Whitaker's integration docs
├── classics_toolkit/
│   └── core.py              # ClassicsToolkit (CLTK wrapper)
├── cologne/
│   └── core.py              # SanskritCologneLexicon (CDSL wrapper)
└── README.md                # This file
```

## Development

```sh
# Run all tests (requires --config flag)
nose2 -s tests --config tests/nose2.cfg

# Run single test
nose2 -s tests <TestClass>.<test_method> --config tests/nose2.cfg

# Run tests with INFO level logging
LANGNET_LOG_LEVEL=INFO nose2 -s tests --config tests/nose2.cfg

# Run tests with DEBUG level logging
LANGNET_LOG_LEVEL=DEBUG nose2 -s tests --config tests/nose2.cfg

# Start API server with auto-reload
uvicorn-run --reload

# Start zombie process reaper (runs continuously in background)
just sidecar
```

### Logging Configuration

langnet-cli uses structlog for structured logging. By default, only WARNING and above messages are shown.

| Level | Command |
|-------|---------|
| WARNING+ (default) | `nose2 -s tests --config tests/nose2.cfg` |
| INFO | `LANGNET_LOG_LEVEL=INFO nose2 -s tests --config tests/nose2.cfg` |
| DEBUG | `LANGNET_LOG_LEVEL=DEBUG nose2 -s tests --config tests/nose2.cfg` |

The `LANGNET_LOG_LEVEL` environment variable only affects langnet's own loggers, not third-party libraries (sh, urllib3, nose2, etc.).

### Code Conventions

See [AGENTS.md](AGENTS.md) for detailed coding standards including:
- Naming conventions (snake_case functions, PascalCase classes)
- Type hint requirements
- Import ordering
- Error handling patterns
- cattrs migration roadmap

## Known Limitations

- **Diogenes reliability**: Perl server leaks threads; run `just sidecar` periodically
- **Whitakers ARM**: Build from source on ARM platforms (see Dependencies section)
- **CDSL incomplete**: Cologne module returns placeholders; full integration pending
- **cattrs migration**: Data models use Python dataclass with cattrs serialization

## Related Projects

- lute-v3 / lwt - Learning with texts fork
- lingq - Language learning platform
- scaife/perseus - Ancient Greek/Roman texts
- wisdomlib - Indian texts library
- archive.org - Historical texts archive
