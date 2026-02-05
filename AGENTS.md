# AI Agent Instructions

## Project Context

langnet-cli is a classical language education tool designed to help students and scholars study Latin, Greek, and Sanskrit. The tool provides instant access to dictionary definitions, morphological parsing, and grammatical information to supplement language learning and text comprehension.

**Multi-Model AI Development**: This project uses a multi-model architecture via OpenRouter for AI-assisted development. Different AI personas are used for specific tasks: The Architect for planning, The Sleuth for debugging, The Artisan for optimization, The Coder for building, The Scribe for documentation, and the Auditor for code review.

**Educational Focus**: This is not just a data processing tool—it's designed for:
- Students reading classical texts (Homer, Virgil, Sanskrit epics)
- Researchers studying classical literature and linguistics
- Anyone building vocabulary and understanding grammar

When making changes, consider how they affect the educational user experience.

## Documentation

### Plan Management Structure

Project plans are organized in `docs/plans/` with three lifecycle stages:

```
docs/plans/
├── active/                     # Currently being worked on
│   └── <feature-name>/        # Subdirectory for feature area
│       └── PLAN_NAME.md       # Plan files
├── todo/                      # Planned but not started
│   └── <feature-name>/
│       └── PLAN_NAME.md
└── completed/                 # Finished plans
    └── <feature-name>/
        └── PLAN_NAME.md
```

**Feature Areas:**
- `skt/` - Sanskrit Heritage Platform integration
- `whitakers/` - Whitaker's Words parsers
- `dico/` - Bilingual dictionary features  
- `pedagogy/` - Educational enhancements
- `infra/` - Infrastructure and tooling

**When creating new plans:**
1. Determine feature area (skt, whitakers, dico, etc.)
2. Place in appropriate lifecycle directory (active/todo/completed)
3. Use clear, descriptive filenames
4. Include @mentions for AI personas in plan phases

### Human-Readable Documentation

See these key documents:

- [README.md](README.md) - Overview, educational use cases, and quick start
- [docs/DEVELOPER.md](docs/DEVELOPER.md) - Code conventions, testing, project structure
- [docs/PEDAGOGICAL_PHILOSOPHY.md](docs/PEDAGOGICAL_PHILOSOPHY.md) - Educational approach and Foster grammar
- [docs/reference/opencode/MULTI_MODEL_GUIDE.md](docs/reference/opencode/MULTI_MODEL_GUIDE.md) - AI-assisted development workflow

## Critical Patterns

### Starlette ASGI
- Entry: `langnet/asgi.py`
- Wire: `LanguageEngine.handle_query()` to `/api/q` endpoint
- Use `ORJSONResponse` for JSON serialization

### CLI Usage
- Use `devenv shell langnet-cli -- <command>` to run CLI commands
- Example: `devenv shell langnet-cli -- query lat lupus --output json`
- This ensures proper environment activation and avoids dependency issues

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

1. CLTK cold download: ~500MB on first query
2. Diogenes zombie threads: run `langnet-dg-reaper`
3. `get_whitakers_proc()` returns `sh.Command`, not string
4. Greek UTF-8 → betacode conversion for diogenes
5. `AttributeValueList` lacks string methods
6. Use `dataclass` with `cattrs` for serialization
7. **Process restart for code changes**: Server processes cache Python modules. After code changes, ask user to restart the process manager before verifying via API/curl.
   ```bash
   # User manages process restart
   # Then verify with:
   langnet-cli cache-clear && curl -s -X POST "http://localhost:8000/api/q" -d "l=san&s=agni"
   ```

## OpenCode Configuration

This project uses OpenRouter for multi-model AI development with 6 specialized personas configured in `.opencode/opencode.json`:

| Persona | Primary Task Areas | Key Commands |
|---------|-------------------|--------------|
| **The Architect** | System design, planning, complex logic | High-level design, architecture planning |
| **The Sleuth** | Debugging, root cause analysis | `LANGNET_LOG_LEVEL=DEBUG`, troubleshooting |
| **The Artisan** | Code optimization, style improvements | `just ruff-format`, `just ruff-check`, `just typecheck` |
| **The Coder** | Feature implementation, testing | `just test`, API development, CLI commands |
| **The Scribe** | Documentation, comments | Documentation updates, code comments |
| **The Auditor** | Code review, security, edge cases | Security review, quality assurance |

When performing tasks, reference the appropriate AI persona using `@agentname` syntax for optimal results.

## Multi-Model Development Strategy

This project follows a multi-model approach using OpenRouter for AI-assisted development:

### Expert Persona Matrix
| Persona | Task Category | Primary Model | Rationale |
| --- | --- | --- | --- |
| **The Architect** | System Design, Planning | `deepseek/deepseek-v3.2` | High reasoning for complex logic |
| **The Sleuth** | Debugging, Root Cause | `z-ai/glm-4.7` | Conservative, less likely to hallucinate |
| **The Artisan** | Optimization, Style | `minimax/minimax-m2.1` | High throughput for large modules |
| **The Coder** | Feature Build, Tests | `z-ai/glm-4.5-air` | Fast execution with reliable tool-use |
| **The Scribe** | Docs, Comments | `xiaomi/mimo-v2-flash` | Ultra-low cost for prose generation |
| **The Auditor** | Code Review, Security | `openai/gpt-oss-120b` | Peak instruction following for edge cases |

### Using AI Personas

Agents are configured in `.opencode/opencode.json`. Use the `@agentname` mention syntax to route tasks:

```markdown
@architect "Design a new caching system for the Sanskrit dictionary"
@sleuth "Debug the memory leak in the DuckDB cache"
@coder "Write comprehensive tests for the new module"
@auditor "Check for security vulnerabilities"
@artisan "Optimize the hot path in the cache module"
@scribe "Document the new API endpoints"
```

### Model Configuration
- Configuration: `.opencode/opencode.json`
- Provider: OpenRouter (https://openrouter.ai)
- Environment: Set `OPENAI_API_BASE=https://openrouter.ai/api/v1` and `OPENAI_API_KEY`

### Operational Workflow
1. **Planning Phase**: Use Architect persona for high-level design
2. **Building Phase**: Use coder persona for code generation
3. **Debugging Phase**: Use Sleuth persona for complex issues
4. **Review Phase**: Use Auditor persona for security and edge cases

### Cost Optimization
- Use "Air"/"Flash" models for 90% of boilerplate
- Reserve "Thinking"/larger models for 10% logic-heavy tasks
- Always use different personas for building vs reviewing

## See Also

- [docs/DEVELOPER.md](docs/DEVELOPER.md) - End-user opencode usage guide
- [docs/reference/opencode/LLM_PROVIDER_GUIDE.md](docs/reference/opencode/LLM_PROVIDER_GUIDE.md) - Multi-model strategy guide

## Important

- You never download and install new tools from the internet without explicit instruction.
- You always use `just` commands instead of running ad-hoc programs.
- If you need to save local debug/verification/ad-hoc-test files put them in ./examples/debug
