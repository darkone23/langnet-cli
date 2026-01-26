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

## Quick Start

```sh
# Enter development environment
devenv shell

# Start API server
uvicorn-run

# CLI usage
langnet-cli query lat lupus
langnet-cli query grc Nike
langnet-cli verify
langnet-cli langs
```

## Dependencies

### Required (Manual Installation)

1. **diogenes** - Perl server for Perseus lexicon data
   - Repository: https://github.com/pjheslin/diogenes
   - Run at `http://localhost:8888`
   - Required for Greek/Latin queries

2. **whitakers-words** - Latin morphological analyzer
   - Binary: `~/.local/bin/whitakers-words`
   - Prebuilt x86_64 binaries only

### Managed by Tests

- **CLTK models**: Installed to `~/cltk_data/`
- **CDSL data**: Installed to `~/cdsl_data/`

## CLI Reference

| Command | Description |
|---------|-------------|
| `langnet-cli query <lang> <word>` | Query a word |
| `langnet-cli verify` | Check backend connectivity |
| `langnet-cli health` | Alias for verify |
| `langnet-cli langs` | List supported languages |

## Known Limitations

- Diogenes leaks threads; run `just langnet-dg-reaper` periodically
- Whitakers ARM builds require source compilation
- CDSL integration is incomplete

## Further Reading

- [DEVELOPER.md](DEVELOPER.md) - Development setup and code conventions
- [TECHNICAL.md](TECHNICAL.md) - Architecture, caching, and encoding docs