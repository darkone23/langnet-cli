# Developer Guide

## Development Environment

```sh
# Enter development shell (loads Python venv, sets env vars)
devenv shell

# Start API server with auto-reload
uvicorn-run --reload

# Start zombie process reaper (runs continuously)
just langnet-dg-reaper
```

## Testing

```sh
# Run all tests
nose2 -s tests --config tests/nose2.cfg

# Run single test (full dotted path required)
nose2 -s tests <TestClass>.<test_method> --config tests/nose2.cfg

# Run tests with verbose logging
LANGNET_LOG_LEVEL=INFO nose2 -s tests --config tests/nose2.cfg
LANGNET_LOG_LEVEL=DEBUG nose2 -s tests --config tests/nose2.cfg
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PYTHONPATH` | Python module search path | `src:$PYTHONPATH` |
| `LANGNET_LOG_LEVEL` | Logging level (DEBUG/INFO/WARNING/ERROR) | `WARNING` |
| `LANGNET_CACHE_ENABLED` | Enable response caching | `true` |
| `LANGNET_CACHE_PATH` | Custom cache database path | auto |

## Code Conventions

### Naming

- Functions: `snake_case` (e.g., `handle_query`)
- Classes: `PascalCase` (e.g., `LanguageEngine`)
- Constants: `UPPER_SNAKE_CASE`

### Type Hints

- Required for all function signatures
- Use `|` for unions: `str | None` not `Optional[str]`
- Generics: `list[str]`, `dict[str, int]`

### Import Order

1. Standard library
2. Third-party packages
3. Local modules (relative before absolute)

### Module Organization

- Prefer `@staticmethod` methods on classes
- Classes prevent namespace pollution and import-time side effects
- Example: `HealthChecker.diogenes()` over `check_diogenes()`

### Error Handling

- `ValueError(msg)` - invalid input
- `NotImplementedError(msg)` - missing features
- `AssertionError(msg)` - invariant violations
- `print()` - expected failures (e.g., missing binary)

### Comments

- Never comment obvious code
- Always comment non-obvious logic (algorithm choices, workarounds)
- Format: lowercase, no trailing period

## Project Structure

```
src/langnet/
├── asgi.py                  # Starlette ASGI application
├── cache/
│   └── core.py              # QueryCache (DuckDB) and NoOpCache
├── cli.py                   # Click-based CLI
├── core.py                  # Dependency injection container
├── engine/
│   └── core.py              # Query routing and aggregation
├── diogenes/
│   ├── core.py              # HTTP client + HTML parsing
│   ├── cli_util.py          # Zombie process reaper
│   └── README.md            # Diogenes integration docs
├── whitakers_words/
│   ├── core.py              # CLI wrapper + line parsing
│   ├── lineparsers/         # Modular line parsers
│   └── README.md            # Whitaker's integration docs
├── classics_toolkit/
│   └── core.py              # CLTK wrapper
├── cologne/
│   └── core.py              # CDSL wrapper
└── logging.py               # structlog configuration
```

## Adding a New Backend

1. Create module in `src/langnet/<backend>/`
2. Implement core class with query method
3. Wire into `LanguageEngine.handle_query()` in `engine/core.py`
4. Add tests in `tests/`
5. Document in module README

## Code Style Tools

- **Formatter**: `ruff format`
- **Type checker**: `ty check`
- **Linter**: `ruff check`

See [AGENTS.md](AGENTS.md) for AI agent-specific instructions.