# AI Agent Instructions

## Project Context

langnet-cli is a classical language education tool designed to help students and scholars study Latin, Greek, and Sanskrit. The tool provides instant access to dictionary definitions, morphological parsing, and grammatical information to supplement language learning and text comprehension.

**Educational Focus**: This is not just a data processing tool—it's designed for:
- Students reading classical texts (Homer, Virgil, Sanskrit epics)
- Researchers studying classical literature and linguistics
- Anyone building vocabulary and understanding grammar

When making changes, consider how they affect the educational user experience.

## Documentation

See these human-readable docs:

- [README.md](README.md) - Overview, educational use cases, and quick start
- [DEVELOPER.md](DEVELOPER.md) - Code conventions, testing, project structure
- [`.opencode/skills/project-tools.md`](.opencode/skills/project-tools.md) - Project automation and autobot tool usage

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

## Opencode Skills

This project includes opencode skills in [`.opencode/skills/`](.opencode/skills/) for common development tasks:

 | Skill | Key Commands |
|-------|--------------|
| [testing.md](.opencode/skills/testing.md) | Run tests: `nose2 -s tests --config tests/nose2.cfg` |
| [backend-integration.md](.opencode/skills/backend-integration.md) | Add data providers (dictionaries/morphology tools), wire to `LanguageEngine.handle_query()` |
| [data-models.md](.opencode/skills/data-models.md) | Use `@dataclass` + `cattrs`, NOT pydantic |
| [api-development.md](.opencode/skills/api-development.md) | Modify `src/langnet/asgi.py`, restart server after changes |
| [cache-management.md](.opencode/skills/cache-management.md) | `devenv shell langnet-cli -- cache-clear` to force fresh queries |
| [debugging.md](.opencode/skills/debugging.md) | `LANGNET_LOG_LEVEL=DEBUG`, check health endpoints |
| [cli-development.md](.opencode/skills/cli-development.md) | Add Click commands in `src/langnet/cli.py` |
| [code-style.md](.opencode/skills/code-style.md) | Run `just ruff-format`, `just ruff-check`, `just typecheck`, `just test` |

When performing tasks, reference the relevant skill for context and patterns.

## See Also

- [`.opencode/skills/README.md`](.opencode/skills/README.md) - Complete skill documentation
- [DEVELOPER.md](DEVELOPER.md) - End-user opencode usage guide

## Important

- You never download and install new tools from the internet without explicit instruction.
- You always use `just` commands instead of running ad-hoc programs.
- If you need to save local debug/verification/ad-hoc-test files put them in ./examples/debug
