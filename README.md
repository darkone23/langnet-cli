# langnet-cli

A command-line tool for querying classical language lexicons and morphology. External services (Heritage, Diogenes, Whitaker's Words) are not bundled and must already be running.

## Quick Start

```sh
# Enter the devenv shell (preferred)
devenv shell langnet-cli

# Or run a one-off command with the environment activated
devenv shell just -- cli query lat lupus --output json

# Start/restart the API server (requires external services running)
devenv shell just -- restart-server

# Check backend services
devenv shell just -- cli verify
```

## Language Support

| Language | Lexicon | Morphology | Encoding Support |
|----------|---------|------------|------------------|
| **Latin** | Diogenes (Lewis & Short) | Whitaker's Words | UTF-8 |
| **Greek** | Diogenes (Liddell & Scott) | Diogenes + CLTK | UTF-8, Betacode |
| **Sanskrit** | CDSL (Monier-Williams/AP90) | Heritage Platform | IAST, Devanagari, SLP1, Velthuis |

## External Dependencies

Services that must be installed and running locally:
1. **Sanskrit Heritage Platform** (`localhost:48080`) – Sanskrit morphology
2. **Diogenes** (`localhost:8888`) – Greek/Latin lexicons
3. **Whitaker's Words** (`~/.local/bin/whitakers-words`) – Latin morphology

Manually sourced or downloaded data (plan ahead before running indexers or semantic reduction):
- **Perseus canonical corpora** (`~/perseus`): `canonical-greekLit` and `canonical-latinLit` trees needed for CTS URN indexing and citation lookups.
- **Classics-Data (PHI CD-ROM) legacy corpus** (`~/Classics-Data`): optional gap-fill for works missing from Perseus.
- **Stanza resources** (`~/stanza_resources/`): downloaded automatically on first Stanza use; allow network or preinstall to avoid runtime stalls.
- **Gensim embeddings** (`~/gensim-data/`) used by the semantic reducer for similarity scoring
- **CLTK models** (to `~/cltk_data/`)
- **CDSL data** (to `~/cdsl_data/`)

After code changes, restart your long-running server process so Python modules reload (`just restart-server` to pick up changes).

## Documentation

- **[docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)** - Installation and first queries
- **[docs/DEVELOPER.md](docs/DEVELOPER.md)** - Development setup and workflow
- **[docs/PEDAGOGICAL_PHILOSOPHY.md](docs/PEDAGOGICAL_PHILOSOPHY.md)** - Educational approach
- **[docs/OUTPUT_GUIDE.md](docs/OUTPUT_GUIDE.md)** - How to read CLI/API JSON (pedagogy-first)
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
- Several open issues remain: Diogenes sense extraction and CTS URN enrichment are flaky, Sanskrit canonicalization and DICO dictionary integration are not complete, CDSL outputs often contain SLP1 artifacts, and the universal schema/fuzzy search are still in design (see `docs/plans/` for status).
- Tests and health checks expect the services above; they have not been run in this workspace during this audit. Use `just test` and `just lint-all` inside `devenv shell langnet-cli` if your environment has all dependencies, and restart long-lived servers after code changes.
- Planning docs live under `docs/plans/`; active ideas are tracked in `docs/plans/todo/` and consolidated roadmap items are in `docs/ROADMAP.md`.
