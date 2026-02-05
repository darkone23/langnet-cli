# langnet-cli

A command-line tool for querying classical language lexicons and morphological analysis.

## Quick Start

```sh
# Enter development environment
devenv shell

# Start the API server
uvicorn-run

# Look up words
langnet-cli query lat lupus      # Latin
langnet-cli query grc λόγος     # Greek  
langnet-cli query san agni      # Sanskrit

# Check backend services
langnet-cli verify
```

## Language Support

| Language | Lexicon | Morphology | Encoding Support |
|----------|---------|------------|------------------|
| **Latin** | Diogenes (Lewis & Short) | Whitaker's Words | UTF-8 |
| **Greek** | Diogenes (Liddell & Scott) | Diogenes + CLTK | UTF-8, Betacode |
| **Sanskrit** | CDSL (Monier-Williams/AP90) | Heritage Platform | IAST, Devanagari, SLP1, Velthuis |

## External Dependencies

These must be installed separately:
1. **Sanskrit Heritage Platform** (`localhost:48080`) - Sanskrit morphology
2. **Diogenes** (`localhost:8888`) - Greek/Latin lexicons
3. **Whitaker's Words** (`~/.local/bin/whitakers-words`) - Latin morphology

Automatic dependencies (download on first use):
- **CLTK models** (~500MB to `~/cltk_data/`)
- **CDSL data** (to `~/cdsl_data/`)

## Documentation

- **[docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)** - Installation and first queries
- **[docs/DEVELOPER.md](docs/DEVELOPER.md)** - Development setup and workflow
- **[docs/PEDAGOGICAL_PHILOSOPHY.md](docs/PEDAGOGICAL_PHILOSOPHY.md)** - Educational approach
- **[docs/reference/](docs/reference/)** - Technical reference docs

## Development

This project uses multi-model AI-assisted development via OpenRouter. See `AGENTS.md` for specialized agent usage:
- **@architect** - System design and planning
- **@sleuth** - Debugging and root cause analysis  
- **@coder** - Feature implementation and testing
- **@artisan** - Code optimization and style
- **@scribe** - Documentation and comments
- **@auditor** - Code review and security