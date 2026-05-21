# AI Agent Instructions

## Project Context

`langnet-cli` is a classical language education tool for Latin, Greek, and
Sanskrit. It helps students, teachers, and researchers connect words in
classical texts to dictionary definitions, morphological parsing, and
source-backed grammatical information.

**Multi-Model AI Development:** This project uses OpenRouter-backed personas for
planning, debugging, implementation, optimization, documentation, and review.

**Educational Focus:** When making changes, consider how they affect students
reading classical texts, researchers checking evidence, and readers building
vocabulary and grammar fluency.

## Documentation

### Plan Management Structure

Project plans are organized in `docs/plans/` with three lifecycle stages:

```text
docs/plans/
├── active/                     # Currently being worked on
│   └── <feature-name>/
│       └── PLAN_NAME.md
├── todo/                       # Planned but not started
│   └── <feature-name>/
│       └── PLAN_NAME.md
└── completed/                  # Finished plans
    └── <feature-name>/
        └── PLAN_NAME.md
```

Feature areas include `skt/`, `whitakers/`, `dico/`, `pedagogy/`, and `infra/`.
When creating new plans, choose the lifecycle and feature area deliberately, use
clear filenames, and include `@agentname` mentions for persona handoffs.

### Human-Readable Documentation

Start with:

- [README.md](README.md) - project overview and primary reading path
- [docs/README.md](docs/README.md) - documentation map
- [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) - setup and first commands
- [docs/OUTPUT_GUIDE.md](docs/OUTPUT_GUIDE.md) - CLI and JSON output guide
- [docs/DEVELOPER.md](docs/DEVELOPER.md) - development workflow
- [docs/ROADMAP.md](docs/ROADMAP.md) - milestone roadmap
- [docs/EXECUTION_PLAN.md](docs/EXECUTION_PLAN.md) - current active queue
- [docs/PEDAGOGICAL_PHILOSOPHY.md](docs/PEDAGOGICAL_PHILOSOPHY.md) - learner-facing grammar and evidence policy
- [docs/technical/opencode/MULTI_MODEL_GUIDE.md](docs/technical/opencode/MULTI_MODEL_GUIDE.md) - AI-assisted development workflow

## Critical Patterns

### Runtime Entry Points

- CLI entry: `langnet-cli` from `langnet.cli:main`
- Root CLI wrapper: `just cli <command>`
- Data builders: `just cli-databuild <builder> ...`
- Web adapter: SvelteKit routes under `webapp/src/routes/api/`
- Current web routes: `/api/search`, `/api/reader`, `/api/word-index`,
  `/api/paradigm`, `/api/motd`, and `/api/translation-cache`

There is no current Python product API surface in this checkout. Use CLI JSON as
the backend contract and the SvelteKit API routes as the web adapter.

### CLI Usage

Use `just cli <command>` for routine CLI work:

```bash
just cli lookup lat lupus --output json
just cli encounter san agni all --output json
just cli translation-cache status --output json
```

This keeps command execution aligned with the repository wrappers and avoids
direct environment activation drift.

### Diogenes Chunk Processing

1. Split response by `<hr />`
2. Classify via `get_next_chunk()`
3. Process via `process_chunk()`
4. Serialize via cattrs

### Whitaker's Line Parsers

- `SensesReducer`: lines with `;`
- `CodesReducer`: lines with `]`
- `FactsReducer`: term pattern lines

## Gotchas

1. CLTK cold download: about 500MB on first query.
2. Diogenes zombie threads: run `langnet-dg-reaper`.
3. `get_whitakers_proc()` returns `sh.Command`, not string.
4. Greek UTF-8 to Betacode conversion is needed for Diogenes paths.
5. `AttributeValueList` lacks string methods.
6. Use `dataclass` with `cattrs` for serialization.
7. Restart long-running web or process-manager sessions after code changes so
   cached Python modules and CLI subprocess behavior reload.

## OpenCode Configuration

This project uses OpenRouter for multi-model AI development with six specialized
personas configured in `.opencode/opencode.json`.

| Persona | Primary Task Areas | Key Commands |
| --- | --- | --- |
| **The Architect** | System design, planning, complex logic | High-level design, architecture planning |
| **The Sleuth** | Debugging, root cause analysis | `LANGNET_LOG_LEVEL=DEBUG`, troubleshooting |
| **The Artisan** | Code optimization, style improvements | `just ruff-format`, `just ruff-check`, `just typecheck` |
| **The Coder** | Feature implementation, testing | `just test`, API development, CLI commands |
| **The Scribe** | Documentation, comments | Documentation updates, code comments |
| **The Auditor** | Code review, security, edge cases | Security review, quality assurance |

Use `@agentname` mention syntax to route tasks:

```markdown
@architect "Design a new caching system for the Sanskrit dictionary"
@sleuth "Debug the memory leak in the DuckDB cache"
@coder "Write comprehensive tests for the new module"
@auditor "Check for security vulnerabilities"
@artisan "Optimize the hot path in the cache module"
@scribe "Document the new API endpoints"
```

## Multi-Model Development Strategy

| Persona | Task Category | Primary Model | Rationale |
| --- | --- | --- | --- |
| **The Architect** | System Design, Planning | `deepseek/deepseek-v3.2` | High reasoning for complex logic |
| **The Sleuth** | Debugging, Root Cause | `z-ai/glm-4.7` | Conservative, less likely to hallucinate |
| **The Artisan** | Optimization, Style | `minimax/minimax-m2.1` | High throughput for large modules |
| **The Coder** | Feature Build, Tests | `z-ai/glm-4.5-air` | Fast execution with reliable tool-use |
| **The Scribe** | Docs, Comments | `xiaomi/mimo-v2-flash` | Ultra-low cost for prose generation |
| **The Auditor** | Code Review, Security | `openai/gpt-oss-120b` | Peak instruction following for edge cases |

Operational workflow:

1. Planning phase: use Architect.
2. Building phase: use Coder.
3. Debugging phase: use Sleuth.
4. Review phase: use Auditor.

Cost guidance: use Air/Flash models for routine work, reserve larger models for
logic-heavy decisions, and use different personas for building and reviewing.

## See Also

- [docs/DEVELOPER.md](docs/DEVELOPER.md) - development workflow
- [docs/technical/opencode/LLM_PROVIDER_GUIDE.md](docs/technical/opencode/LLM_PROVIDER_GUIDE.md) - multi-model provider guide

## Important

- Never download and install new tools from the internet without explicit instruction.
- Use `just` commands instead of ad-hoc runtime programs.
- If local debug, verification, or ad-hoc test files are needed, put them in
  `./examples/debug`.
