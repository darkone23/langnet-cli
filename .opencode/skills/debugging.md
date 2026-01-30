# Debugging and Troubleshooting

Debug and troubleshoot common issues in langnet-cli.

## Enable Debug Logging

```bash
# Set log level to DEBUG
LANGNET_LOG_LEVEL=DEBUG devenv shell

# Or inline
LANGNET_LOG_LEVEL=DEBUG langnet-cli query lat lupus
```

## Common Issues

### Diogenes Zombie Processes

Symptom: Diogenes queries hanging or timing out

Solution: Run zombie process reaper
```bash
just langnet-dg-reaper  # Continuous reaper
just reap  # One-shot reaper
```

### Server Not Responding After Code Changes

Symptom: API returns old responses or errors after code modification

Solution: Restart server (modules are cached)
```bash
# Stop uvicorn (Ctrl+C)
uvicorn-run --reload  # Restart
```

### CLTK Models Not Downloading

Symptom: CLTK queries failing with model not found

Solution: Models download automatically on first run (~500MB)
```bash
# Force redownload if needed
rm -rf ~/cltk_data/
LANGNET_LOG_LEVEL=INFO langnet-cli query lat lupus
```

### Cache Returning Stale Data

Symptom: Backend bug fixes not visible in responses

Solution: Clear cache
```bash
langnet-cli cache-clear
langnet-cli cache-clear --lang lat  # Clear specific language
```

### Whitaker's Words Not Found

Symptom: Latin morphology queries failing

Solution: Install binary
```bash
# Check installation
ls ~/.local/bin/whitakers-words

# The binary should exist, or queries return empty results
```

## Debugging Queries

```bash
# Enable debug logs
LANGNET_LOG_LEVEL=DEBUG langnet-cli query lat lupus

# Clear cache to force fresh queries
langnet-cli cache-clear && langnet-cli query lat lupus

# Test backend directly (via Python REPL)
python3 -c "from langnet.diogenes.core import DiogenesScraper; s = DiogenesScraper(); print(s.parse_word('lupus', 'lat'))"
```

## Health Check

```bash
# Check all backends
langnet-cli verify

# Check specific endpoint
curl -s "http://localhost:8000/api/health"

# View cache stats
langnet-cli cache-stats
curl -s "http://localhost:8000/api/cache/stats"
```

## Test Suite Debugging

```bash
# Run single test with verbose output
LANGNET_LOG_LEVEL=DEBUG nose2 -s tests tests.test_api_integration.TestGreekSpacyIntegration.test_greek_query_includes_spacy_response --config tests/nose2.cfg

# Run tests without cache
LANGNET_CACHE_ENABLED=false nose2 -s tests --config tests/nose2.cfg
```

## Structured Logging

Logs use logfmt format with context:
```
ts=2026-01-25T10:00:00Z level=INFO msg="query_started" lang=lat word=lupus
ts=2026-01-25T10:00:01Z level=DEBUG msg="routing_to_latin_backends" lang=lat word=lupus
ts=2026-01-25T10:00:02Z level=INFO msg="query_completed" lang=lat word=lupus
```

Use `hl` command for colored logfmt output:
```bash
LANGNET_LOG_LEVEL=DEBUG langnet-cli query lat lupus | hl
```

## Log Levels

- DEBUG: Parsing steps, chunk classification, cache hits/misses
- INFO: Backend selection, query initialization, cache operations
- WARN: Missing optional data, merge conflicts, degraded health
- ERROR: Failed queries, unavailable backends, connection errors

## Multi-Model AI Persona

**Recommended Persona**: The Detective (`openrouter/zhipuai/glm-4.7:detective`)

Use this persona for:
- Complex bug investigation
- Root cause analysis
- Performance debugging
- Concurrency issue troubleshooting

Example:
```bash
/model openrouter/zhipuai/glm-4.7:detective
/improve "Debug the deadlock issue in the Diogenes scraper when handling multiple simultaneous requests"
```

## Troubleshooting Checklist

1. Is server running? `curl -s "http://localhost:8000/api/health"`
2. Are backends healthy? `langnet-cli verify`
3. Did you restart after code changes? Stop and restart uvicorn
4. Is cache stale? `langnet-cli cache-clear`
5. Are logs informative? `LANGNET_LOG_LEVEL=DEBUG`
6. Are Diogenes zombies accumulating? `just reap`
