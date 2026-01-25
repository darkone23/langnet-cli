# AGENTS.md

Instructions for AI agents working on this codebase.

## Development Commands

| Task | Command | Notes |
|------|---------|-------|
| Run all tests | `nose2 -s tests` | Runs nose2 test discovery in tests/ |
| Run single test | `nose2 -s tests <TestClass>.<test_method>` | Full dotted path required |
| Start dev server | `uvicorn-run` | Wraps `uvicorn langnet.asgi:app` |
| Start sidecar | `just sidecar` | Runs zombie diogenes reaper (see cli_util.py) |
| Enter shell | `devenv shell` | Loads Python venv, sets env vars |

## Environment

- **PYTHONPATH**: `src:$PYTHONPATH` (set in devenv.nix enterShell)
- **Python version**: 3.11 (specified in devenv.nix for CLTK compatibility)
- **Package manager**: Poetry (pyproject.toml), but poetry commands disabled
- **Test framework**: nose2

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

### Data Models
- **Current**: Pydantic `BaseModel` with `Field(default=...)` for optional fields
- **Target**: Python `dataclass` + `cattrs` for serialization
- See TODO.md for migration plan

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
4. Serialize to Pydantic models

### Line Parsers (Whitakers)
Modular design: each line type has a reducer:
- `SensesReducer` - lines with `;` (dictionary senses)
- `CodesReducer` - lines with `]` (morphological codes)
- `FactsReducer` - lines matching term pattern (word data)

## Gotchas

1. **CLTK cold download**: First query downloads ~500MB model data
2. **Diogenes zombie threads**: Perl server leaks threads; run `just sidecar`
3. **Whitakers return type**: `get_whitakers_proc()` returns `sh.Command`, not a string
4. **Betacode conversion**: Greek UTF-8 must convert to betacode for diogenes
5. **BeautifulSoup types**: BeautifulSoup's `AttributeValueList` lacks string methods
6. **Pydantic deprecation**: Models use v2 syntax (`model_dump()` not `dict()`)
