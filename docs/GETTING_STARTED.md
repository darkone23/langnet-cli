# Getting Started with Langnet CLI

A command-line tool for querying classical language lexicons and morphological analysis.

## Quick Setup

```bash
# Enter development environment (preferred)
devenv shell langnet-cli

# Or run a single command with the environment activated
devenv shell langnet-cli -- langnet-cli query lat lupus --output json

# Check available backends (requires external services running)
devenv shell langnet-cli -- langnet-cli verify

# Start API server
devenv shell langnet-cli -- uvicorn-run --reload

# Query words
devenv shell langnet-cli -- langnet-cli query lat lupus      # Latin
devenv shell langnet-cli -- langnet-cli query grc λόγος     # Greek  
devenv shell langnet-cli -- langnet-cli query san agni      # Sanskrit
```

## External Services Required

| Service | Language | Purpose | Status |
|---------|----------|---------|--------|
| **Sanskrit Heritage Platform** | Sanskrit | Morphology + dictionary | Must be running at `localhost:48080` |
| **Diogenes** | Greek/Latin | Lexicons (Lewis & Short, Liddell & Scott) | Must be running at `localhost:8888` |
| **Whitaker's Words** | Latin | Morphological analysis | Binary in `~/.local/bin/whitakers-words` |

These services are not bundled with the project; run them locally before using `langnet-cli verify` or making queries.

## Automated Downloads

These are downloaded on first use:
- **CLTK models** (~500MB) → `~/cltk_data/`
- **CDSL data** → `~/cdsl_data/`

## Commands

### Basic Queries
```bash
devenv shell langnet-cli -- langnet-cli query lat lupus
devenv shell langnet-cli -- langnet-cli query grc ἄνθρωπος  
devenv shell langnet-cli -- langnet-cli query san dharma
```

### Health Checks
```bash
devenv shell langnet-cli -- langnet-cli verify          # Check all backends
devenv shell langnet-cli -- langnet-cli health         # Alias for verify
```

### API Usage
```bash
# Start server
devenv shell langnet-cli -- uvicorn-run --reload

# Query via HTTP
curl "http://localhost:8000/api/q?l=lat&s=lupus"
curl -X POST "http://localhost:8000/api/q" -d "l=lat&s=lupus"
```

### Cache Management
```bash
devenv shell langnet-cli -- langnet-cli cache-clear    # Clear query cache
devenv shell langnet-cli -- langnet-cli cache-stats    # Show cache statistics
```

### Indexer Tools (CTS URN)
```bash
# Build citation index
devenv shell langnet-cli -- langnet-cli indexer build cts-urn --source /path/to/Classics-Data

# Query citation index
devenv shell langnet-cli -- langnet-cli indexer query "Hom. Il." --language grc
```

## Troubleshooting

### Backend Services Not Found
```bash
devenv shell langnet-cli -- langnet-cli verify  # Shows which services are unavailable

# Sanskrit Heritage Platform
curl http://localhost:48080/sktreader

# Diogenes
curl http://localhost:8888

# Whitaker's Words
~/.local/bin/whitakers-words lupus
```

### Common Issues
- **CLTK downloading data**: First query may take ~5 minutes
- **Cache issues**: Run `devenv shell langnet-cli -- langnet-cli cache-clear` if responses seem stale
- **Process restart needed**: After code changes, restart API server with `uvicorn-run`
- **External services missing**: Most queries depend on Heritage, Diogenes, and Whitaker's Words being available locally; `langnet-cli verify` reports which ones are missing.

## Development

See [DEVELOPER.md](DEVELOPER.md) for detailed setup and AI-assisted workflow.
