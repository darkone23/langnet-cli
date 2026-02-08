# langnet-cli

A command-line tool for querying classical language lexicons and morphology. External services (Heritage, Diogenes, Whitaker's Words) are not bundled and must already be running.

## Quick Start

```sh
# Enter the devenv shell (preferred)
devenv shell langnet-cli

# Or run a one-off command with the environment activated
devenv shell langnet-cli -- langnet-cli query lat lupus --output json

# Start the API server (requires external services running)
devenv shell langnet-cli -- uvicorn-run --reload

# Check backend services
devenv shell langnet-cli -- langnet-cli verify
```

## Language Support

| Language | Lexicon | Morphology | Encoding Support |
|----------|---------|------------|------------------|
| **Latin** | Diogenes (Lewis & Short) | Whitaker's Words | UTF-8 |
| **Greek** | Diogenes (Liddell & Scott) | Diogenes + CLTK | UTF-8, Betacode |
| **Sanskrit** | CDSL (Monier-Williams/AP90) | Heritage Platform | IAST, Devanagari, SLP1, Velthuis |

## External Dependencies

These must be installed separately before any queries will work:
1. **Sanskrit Heritage Platform** (`localhost:48080`) - Sanskrit morphology
2. **Diogenes** (`localhost:8888`) - Greek/Latin lexicons
3. **Whitaker's Words** (`~/.local/bin/whitakers-words`) - Latin morphology

Automatic dependencies (download on first use):
- **CLTK models** (~500MB to `~/cltk_data/`)
- **CDSL data** (to `~/cdsl_data/`)

After code changes, restart your long-running server process so Python modules reload (`uvicorn-run` caches imports).

## Documentation

- **[docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)** - Installation and first queries
- **[docs/DEVELOPER.md](docs/DEVELOPER.md)** - Development setup and workflow
- **[docs/PEDAGOGICAL_PHILOSOPHY.md](docs/PEDAGOGICAL_PHILOSOPHY.md)** - Educational approach
- **[docs/technical/](docs/technical/)** - Technical reference docs
- **[AGENTS.md](AGENTS.md)** - Multi-model AI personas and workflows

## Development

This project uses multi-model AI-assisted development via OpenRouter. See `AGENTS.md` for specialized agent usage:
- **@architect** - System design and planning
- **@sleuth** - Debugging and root cause analysis  
- **@coder** - Feature implementation and testing
- **@artisan** - Code optimization and style
- **@scribe** - Documentation and comments
- **@auditor** - Code review and security

## Current Status and Known Gaps

- External services are required for most functionality; without them `langnet-cli verify` and queries will fail.
- Several open issues remain: Diogenes sense extraction and CTS URN enrichment are flaky, Sanskrit canonicalization and DICO dictionary integration are not complete, CDSL outputs often contain SLP1 artifacts, and the universal schema/fuzzy search are still in design (see `docs/TODO.md`).
- Tests and health checks expect the services above; they have not been run in this workspace during this audit. Use `just test` and `just lint-all` inside `devenv shell langnet-cli` if your environment has all dependencies.
- Planning docs live under `docs/plans/`; active work is tracked in `docs/plans/active/` and ideas in `docs/plans/todo/`.
