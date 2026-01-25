# langnet

A unified backend API for querying classical language data (Latin, Greek, Sanskrit) from multiple lexicon sources.

## Overview

langnet aggregates several classical language resources into a single query interface:

| Source | Latin | Greek | Sanskrit |
|--------|-------|-------|----------|
| Diogenes (Perseus) | lexicon + morphology | lexicon + morphology | - |
| Whitaker's Words | morphology | - | - |
| CLTK | lexicon | - | lemmatization |
| CDSL (Cologne) | - | - | dictionary |

## Why langnet?

Classical language resources are fragmented across many projects, each with different interfaces, data formats, and installation requirements. langnet provides:

- **Unified API**: Single endpoint for querying multiple backends
- **Response aggregation**: Results from different sources merged by language
- **Cold start management**: API server caches loaded models (CLTK downloads are expensive)
- **Extensible architecture**: Add new backends by implementing the scraper interface

## Quick Start

```sh
# Enter development environment
devenv shell

# Start API server (uvicorn-run wraps uvicorn langnet.asgi:app)
uvicorn-run

# Query examples
curl 'localhost:8000/api/q?l=lat&s=benevolens' | jq .
curl --data-urlencode 's=οὐσία' --data-urlencode 'l=grk' 'localhost:8000/api/q' | jq .
curl --data-urlencode 's=sa.msk.rta' --data-urlencode 'l=san' 'localhost:8000/api/q' | jq .
```

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

## Architecture

```
                              ┌─────────────────────┐
                              │   API Client (curl) │
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
# Run all tests
nose2 -s tests

# Run single test
nose2 -s tests <TestClass>.<test_method>

# Start API server with auto-reload
uvicorn-run --reload

# Start zombie process reaper (runs continuously in background)
just sidecar
```

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
