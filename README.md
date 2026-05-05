# langnet-cli

LangNet is a local evidence engine for reading Latin, Greek, and Sanskrit. It connects inflected words to dictionary meanings, morphological analyses, and source-backed claims so students, teachers, and researchers can see both the answer and the evidence behind it.

The reliable product surface today is the CLI. External services such as Heritage, Diogenes, and Whitaker's Words are not bundled and must already be running for live lookup.

## Quick Start

```sh
# Enter the devenv shell, then run commands normally
devenv shell
langnet-cli --help

# Or run a one-off command with the environment activated
just cli lookup lat lupus --output json

# Inspect the staged plan, source evidence, and learner-facing MVP
just cli plan lat lupus
just triples-dump lat lupus whitakers
devenv shell -- bash -c 'langnet-cli encounter san dharma all --no-cache'

# Use cache-backed DICO/Gaffiot English evidence when available
just cli encounter lat arma gaffiot --translation-mode cache
just cli encounter san dharma dico --translation-mode cache
just cli reader-eval --limit 3 --translation-mode cache

# Explicitly populate missing DICO/Gaffiot translations, then display them
just cli encounter lat cano gaffiot --translation-mode auto

# Ask for learner word recommendations backed by encounter probes
just cli word-of-day san --output json
just cli recommend-words lat --count 3
```

## Language Support

| Language | Lexicon | Morphology | Encoding Support |
|----------|---------|------------|------------------|
| **Latin** | Diogenes (Lewis & Short), local Gaffiot | Whitaker's Words | UTF-8 |
| **Greek** | Diogenes (Liddell & Scott) | Diogenes + CLTK | UTF-8, Betacode |
| **Sanskrit** | CDSL (Monier-Williams/AP90), local DICO | Heritage Platform | IAST, Devanagari, SLP1, Velthuis |

## External Dependencies

Services that must be installed and running locally:
1. **Sanskrit Heritage Platform** (`localhost:48080`) – preferred Sanskrit analysis/morphology source
2. **Diogenes** (`localhost:8888`) – Greek/Latin lexicons
3. **Whitaker's Words** (`~/.local/bin/whitakers-words`) – Latin morphology

Manually sourced or downloaded data (plan ahead before running indexers or semantic reduction):
- **Perseus canonical corpora** (`~/perseus`): `canonical-greekLit` and `canonical-latinLit` trees needed for CTS URN indexing and citation lookups.
- **Classics-Data (PHI CD-ROM) legacy corpus** (`~/Classics-Data`): optional gap-fill for works missing from Perseus.
- **Stanza resources** (`~/stanza_resources/`): downloaded automatically on first Stanza use; allow network or preinstall to avoid runtime stalls.
- **Gensim embeddings** (`~/gensim-data/`): not required yet; embeddings are explicitly deferred until deterministic semantic buckets exist.
- **CLTK models** (to `~/cltk_data/`)
- **CDSL data** (to `~/cdsl_data/`)

After code changes, restart any long-running local process manager so Python modules reload.

## Documentation

- **[docs/VISION.md](docs/VISION.md)** - Product vision, audience, and strategic direction
- **[docs/BASELINE_AND_ROADMAP.md](docs/BASELINE_AND_ROADMAP.md)** - Current working baseline, vision comparison, and next concrete steps
- **[docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)** - Installation and first queries
- **[docs/DEVELOPER.md](docs/DEVELOPER.md)** - Development setup and workflow
- **[docs/EXECUTION_PLAN.md](docs/EXECUTION_PLAN.md)** - Roadmap, task, gap, and risk operating view
- **[docs/GOALS.md](docs/GOALS.md)** - Educational approach and product goals
- **[docs/PEDAGOGICAL_PHILOSOPHY.md](docs/PEDAGOGICAL_PHILOSOPHY.md)** - Learner-facing grammar and evidence principles
- **[docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md)** - Current health card and next priorities
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

- External services are required for live lookup; without them `langnet-cli lookup` returns per-tool errors for unavailable sources.
- The current learner-facing MVP is `langnet-cli encounter`. It reduces claim triples into exact Witness Sense Unit buckets and shows source-backed meanings plus Heritage morphology analysis for Sanskrit.
- `word-of-day` and `recommend-words` provide on-demand learner word suggestions. JSON output uses `langnet.word_of_day.v1` and includes verified encounter summaries when lookup evidence is available.
- `triples-dump --output json` is the current evidence-inspection surface for claims, triples, source refs, and display metadata.
- DICO/Gaffiot French source entries are wired as source evidence. Cache-backed English translations can be projected into `encounter` with `--translation-mode cache`; missing rows can be populated only when explicitly requested with `--translation-mode auto`.
- Several open issues remain: CTS URN enrichment is deferred, CDSL entries are still flat source-heavy strings, some long upstream entries need better source segmentation, and exact buckets are not yet broad semantic merging.
- Use `just test-fast` and `just lint-all` for local validation; these recipes enter `devenv` automatically. Restart long-lived servers after code changes.
- Planning docs live under `docs/plans/`; the canonical roadmap is `docs/ROADMAP.md`, with the active implementation plan at `docs/plans/active/infra/design-to-runtime-roadmap.md`.
