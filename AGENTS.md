# AGENTS.md

Instructions for AI agents working on this codebase.

## Development Commands

| Task | Command | Notes |
|------|---------|-------|
| Run all tests | `nose2 -s tests --config tests/nose2.cfg` | Runs nose2 test discovery in tests/ |
| Run single test | `nose2 -s tests <TestClass>.<test_method> --config tests/nose2.cfg` | Full dotted path required |
| Enter shell | `devenv shell` | Loads Python venv, sets env vars |

## Operator-Only Commands

These are only to be run by the human-in-the-loop and never the agent.

| Task | Command | Notes |
|------|---------|-------|
| Start dev server | `uvicorn-run` | Wraps `uvicorn langnet.asgi:app` |
| Start sidecar | `just sidecar` | Runs zombie diogenes reaper (see cli_util.py) |

## Environment

- **PYTHONPATH**: `src:$PYTHONPATH` (set in devenv.nix enterShell)
- **Python version**: 3.11 (specified in devenv.nix for CLTK compatibility)
- **Package manager**: Poetry (pyproject.toml)
- **Test framework**: nose2
- **Type checker**: ty
- **Code formatter**: ruff

## Code Style

### Naming Conventions
- **Functions**: `snake_case` (e.g., `handle_query`, `get_next_word`)
- **Classes**: `PascalCase` (e.g., `LanguageEngine`, `DiogenesScraper`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `DiogenesChunkType`)

### Type Hints
- Required for all function signatures
- Use `|` for union types: `str | None` not `Optional[str]`
- Complex generic types from `typing` module: `list[str]`, `dict[str, int]`

### Imports
Order required (this order is enforced by existing code):
1. Standard library (`from pathlib import Path`)
2. Third-party packages (`from rich.pretty import pprint`)
3. Local modules - relative before absolute
   - `from .lineparsers import FactsReducer`
   - `from langnet.diogenes.core import DiogenesScraper`

### Module Organization
- Prefer `@staticmethod` methods on classes over bare module-level functions
- Classes prevent namespace pollution and avoid import-time side effects
- Example: Use `HealthChecker.diogenes()` instead of `check_diogenes()`

### Data Models
- **Current**: Python `dataclass` with `cattrs` for serialization

### Error Handling
- Raise `ValueError(msg)` for invalid input
- Raise `NotImplementedError(msg)` for missing features
- Raise `AssertionError(msg)` for programmer errors (invariant violations)
- Use `print()` for expected failure cases (e.g., missing whitakers binary)

### Comments
- **Never** add comments for obvious code
- **Always** add comments for non-obvious logic (algorithm choices, workarounds, assumptions)
- Comment format: short sentence, lowercase, no trailing period

## Critical Patterns

### Starlette ASGI App
The entry point is `langnet/asgi.py`. Currently a stub. When implementing:
- Import `Request` from `starlette.requests`
- Use `ORJSONResponse` or similar for JSON serialization
- Wire `LanguageEngine.handle_query()` to `/api/q` endpoint

### Diogenes Chunk Processing
The `DiogenesScraper` uses a state machine to classify HTML responses:
1. Split response by `<hr />` (document separators)
2. Classify each chunk via `get_next_chunk()`
3. Process chunk via `process_chunk()`
4. Serialize to dataclass models via cattrs

### Line Parsers (Whitakers)
Modular design: each line type has a reducer:
- `SensesReducer` - lines with `;` (dictionary senses)
- `CodesReducer` - lines with `]` (morphological codes)
- `FactsReducer` - lines matching term pattern (word data)

## Gotchas

1. **CLTK cold download**: First query downloads ~500MB model data
2. **Diogenes zombie threads**: Perl server leaks threads; run `langnet-dg-reaper`
3. **Whitakers return type**: `get_whitakers_proc()` returns `sh.Command`, not a string
4. **Unicode conversion**: Greek UTF-8 must convert to betacode for diogenes
5. **BeautifulSoup types**: BeautifulSoup's `AttributeValueList` lacks string methods
6. **Data models**: Use `dataclass` with `cattrs` for serialization

### Logging Configuration

Logging uses structlog with the following characteristics:
- **Default level**: WARNING (INFO and DEBUG are suppressed by default)
- **Environment variable**: `LANGNET_LOG_LEVEL` (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **Scope**: Only affects `langnet.*` loggers, not third-party libraries
- **Output format**: ISO timestamps with colored ConsoleRenderer
- **Configuration**: Auto-configured on import via `langnet/logging.py`

Example usage:
```bash
# Suppress all output (WARNING+ only)
nose2 -s tests --config tests/nose2.cfg

# Show INFO messages
LANGNET_LOG_LEVEL=INFO nose2 -s tests --config tests/nose2.cfg

# Show DEBUG messages
LANGNET_LOG_LEVEL=DEBUG nose2 -s tests --config tests/nose2.cfg
```

The `tests/testconf.py` plugin ensures logging is configured before tests run via the `startTestRun` hook.
