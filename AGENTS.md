# AI Agent Instructions

See these human-readable docs:

- [README.md](README.md) - Overview and quick start
- [DEVELOPER.md](DEVELOPER.md) - Code conventions, testing, project structure
- [TECHNICAL.md](TECHNICAL.md) - Architecture, encoding, caching, backend details

## Critical Patterns

### Starlette ASGI
- Entry: `langnet/asgi.py`
- Wire: `LanguageEngine.handle_query()` to `/api/q` endpoint
- Use `ORJSONResponse` for JSON serialization

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