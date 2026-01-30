# Cache Management

Manage DuckDB response cache for query results.

## Cache Commands

View cache statistics:
```bash
langnet-cli cache-stats
```

Clear all cache:
```bash
langnet-cli cache-clear
```

Clear specific language cache:
```bash
langnet-cli cache-clear --lang lat
langnet-cli cache-clear --lang grc
langnet-cli cache-clear --lang san
```

## Cache Location

Default cache database: `~/.cache/langnet/cache.db` (auto-created)

## Cache Implementation

`src/langnet/cache/core.py` - QueryCache class using DuckDB

```python
from langnet.cache.core import QueryCache, get_cache_path

# Get cache
cache = QueryCache(get_cache_path())

# Get cached result
cached = cache.get(lang, word)

# Store result
cache.put(lang, word, result)

# Clear all
cache.clear()

# Clear by language
count = cache.clear_by_lang("lat")
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LANGNET_CACHE_ENABLED` | Enable response caching | `true` |
| `LANGNET_CACHE_PATH` | Custom cache database path | auto |

## Cache Statistics Endpoint

```bash
curl -s "http://localhost:8000/api/cache/stats"
```

Returns:
```json
{
  "total_entries": 1234,
  "total_size_bytes": 567890,
  "total_size_human": "554.6KB",
  "languages": [
    {"lang": "lat", "entries": 500, "size_bytes": 200000, "size_human": "195.3KB"},
    {"lang": "grc", "entries": 400, "size_bytes": 180000, "size_human": "175.8KB"},
    {"lang": "san", "entries": 334, "size_bytes": 187890, "size_human": "183.5KB"}
  ]
}
```

## Testing with Fresh Data

When debugging backend issues, clear cache to ensure fresh queries:

```bash
langnet-cli cache-clear && curl -s -X POST "http://localhost:8000/api/q" -d "l=san&s=agni"
```

## Multi-Model AI Persona

**Recommended Persona**: The Refactorer (`openrouter/minimax/minimax-m2.1:refactorer`)

Use this persona for:
- Cache performance optimization
- Cache invalidation strategies
- Database schema improvements
- Memory optimization work

Example:
```bash
/model openrouter/minimax/minimax-m2.1:refactorer
"Optimize the DuckDB cache schema for faster lookups"
```

## Performance Notes

- Cache speeds up repeated queries significantly
- Cache hit logged at DEBUG level: `query_cached`
- Cache miss logged at DEBUG level: `query_started`
