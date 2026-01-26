# API Development

Develop and debug the Starlette ASGI API server.

## Entry Point

`src/langnet/asgi.py` - Starlette application with routes

## Routes

- `GET/POST /api/q` - Query endpoint for word lookups
- `GET /api/health` - Health check endpoint
- `GET /api/cache/stats` - Cache statistics

## Starting Server

```bash
devenv shell
uvicorn-run  # Start with auto-reload
uvicorn-run --reload  # Explicit reload mode
```

## Testing API

```bash
# Quick test
curl -s "http://localhost:8000/api/health"

# Query Latin
curl -s -X POST "http://localhost:8000/api/q" -d "l=lat&s=lupus"

# Query Greek
curl -s -X POST "http://localhost:8000/api/q" -d "l=grc&s=λόγος"

# Query Sanskrit
curl -s -X POST "http://localhost:8000/api/q" -d "l=san&s=agni"
```

## Code Changes Require Restart

**CRITICAL**: Server processes cache Python modules. After code changes, you MUST restart the server before testing:

1. Stop the uvicorn process (Ctrl+C)
2. Restart with `uvicorn-run --reload`
3. Clear cache to test fresh queries: `langnet-cli cache-clear`
4. Verify with curl or CLI: `langnet-cli query lat lupus`

## Adding New Route

```python
async def my_endpoint(request: Request):
    if not hasattr(request.app.state, "wiring"):
        request.app.state.wiring = LangnetWiring()
    wiring: LangnetWiring = request.app.state.wiring
    # your code
    return ORJsonResponse(result)

# Add to routes list
routes = [
    Route("/api/q", query_api, methods=["GET", "POST"]),
    Route("/api/health", health_check),
    Route("/api/my-endpoint", my_endpoint),  # new route
]
```

## Error Handling

```python
try:
    result = wiring.engine.handle_query(lang, word)
    return ORJsonResponse(result)
except ValueError as e:
    return ORJsonResponse({"error": str(e)}, status_code=400)
except Exception as e:
    return ORJsonResponse({"error": str(e)}, status_code=500)
```

## JSON Serialization

Use `ORJsonResponse` for fast JSON serialization with orjson:

```python
class ORJsonResponse(Response):
    media_type = "application/json"

    def render(self, content: Any) -> bytes:
        return orjson.dumps(content)
```

## Wiring Pattern

Dependency injection via `LangnetWiring`:

```python
from langnet.core import LangnetWiring

# In endpoint
if not hasattr(request.app.state, "wiring"):
    request.app.state.wiring = LangnetWiring()
wiring: LangnetWiring = request.app.state.wiring
```

See `src/langnet/core.py` for wiring definition.
