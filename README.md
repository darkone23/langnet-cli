# langnet-cli

LangNet is a local evidence engine for reading Latin, Greek, and Sanskrit. It
connects inflected words to dictionary meanings, morphological analyses, source
claims, and reader-oriented explanations so students, teachers, and researchers
can see both the answer and the evidence behind it.

The reliable backend contract today is CLI JSON. The webapp is a SvelteKit
adapter over that contract, with API routes for search, reader texts, word
index browsing, paradigms, message-of-the-day data, and translation-cache
inspection.

## Quick Start

```sh
# Enter the devenv shell, then run commands normally.
devenv shell
langnet-cli --help

# Or run one-off commands through the maintained wrapper.
just cli lookup lat lupus --output json
just cli encounter san dharma all --output json
just cli translation-cache status --output json

# Inspect source-backed learner output and evidence.
just cli plan lat lupus
just triples-dump lat lupus whitakers
just cli encounter lat arma gaffiot --translation-mode cache
just cli encounter san dharma dico --translation-mode cache

# Inspect source-backed inflection tables.
just cli paradigm san putra --kind declension --gender Mas --output json
just cli paradigm san gam --kind conjugation --class 1 --output json
just cli paradigm lat amo --kind conjugation --output json
just cli paradigm grc lo/gos --kind declension --output json
```

## Language Support

| Language | Lexicon | Morphology | Encoding Support |
| --- | --- | --- | --- |
| **Latin** | Diogenes Lewis & Short, local Gaffiot, Lewis 1890 index data | Whitaker's Words | UTF-8 |
| **Greek** | Diogenes Liddell & Scott | Diogenes + CLTK where configured | UTF-8, Betacode |
| **Sanskrit** | CDSL Monier-Williams/AP90, local DICO | Heritage Platform | IAST, Devanagari, SLP1, Velthuis |
| **French-to-English lexicon support** | DICO, Gaffiot, Bailly | Translation cache projection | Cache-backed English derived evidence |

Bailly and Lewis surfaces are local data/index surfaces, not replacements for
the CLI encounter contract. Bailly/Gaffiot/DICO French source entries can be
projected through the translation cache when exact cache rows exist or when
population is explicitly requested.

## Current Surfaces

- `langnet-cli encounter` is the learner-facing word encounter.
- `langnet-cli lookup`, `plan`, `plan-exec`, and `triples-dump` are inspection
  and debugging surfaces.
- `word-index`, `reader`, `paradigm`, `translation-cache`, `word-of-day`, and
  `recommend-words` expose reader and learning workflows.
- The SvelteKit webapp lives in `webapp/` and adapts CLI-backed data through
  `/api/search`, `/api/reader`, `/api/word-index`, `/api/paradigm`,
  `/api/motd`, and `/api/translation-cache`.

External services and local data remain environment-dependent. Sanskrit
Heritage, Diogenes, Whitaker's Words, CLTK data, CDSL data, and corpus/index
databases must be installed or built separately for live lookup and browsing.

## Documentation

- **[docs/README.md](docs/README.md)** - documentation map
- **[docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)** - setup and first commands
- **[docs/OUTPUT_GUIDE.md](docs/OUTPUT_GUIDE.md)** - CLI and JSON output guide
- **[docs/DEVELOPER.md](docs/DEVELOPER.md)** - development workflow
- **[docs/ROADMAP.md](docs/ROADMAP.md)** - milestone roadmap
- **[docs/EXECUTION_PLAN.md](docs/EXECUTION_PLAN.md)** - current active queue
- **[docs/READER_CLI_BEGINNER_GUIDE.md](docs/READER_CLI_BEGINNER_GUIDE.md)** - reader corpus operation
- **[docs/READER_WEB_CONTRACT.md](docs/READER_WEB_CONTRACT.md)** - reader/web integration contract
- **[webapp/README.md](webapp/README.md)** - SvelteKit webapp operation
- **[AGENTS.md](AGENTS.md)** - AI-agent workflow notes

## Development

This project uses multi-model AI-assisted development via OpenRouter. See
`AGENTS.md` for specialized agent usage:

- **@architect** - system design and planning
- **@sleuth** - debugging and root cause analysis
- **@coder** - feature implementation and testing
- **@artisan** - code optimization and style
- **@scribe** - documentation and comments
- **@auditor** - code review and security

Use `just lint-all`, `just test-fast`, and focused `just test ...` recipes for
local validation. Run recipe probes sequentially when auditing recipe health,
and restart long-lived web or process-manager sessions after code changes.
