# Getting Started with Langnet CLI

A command-line tool for querying classical language lexicons and morphological analysis.

## Quick Setup

```bash
# Enter development environment
devenv shell

# Check available backends
langnet-cli verify

# Start API server
uvicorn-run

# Query words
langnet-cli query lat lupus      # Latin
langnet-cli query grc λόγος     # Greek  
langnet-cli query san agni      # Sanskrit
```

## External Services Required

| Service | Language | Purpose | Status |
|---------|----------|---------|--------|
| **Sanskrit Heritage Platform** | Sanskrit | Morphology + dictionary | Must be running at `localhost:48080` |
| **Diogenes** | Greek/Latin | Lexicons (Lewis & Short, Liddell & Scott) | Must be running at `localhost:8888` |
| **Whitaker's Words** | Latin | Morphological analysis | Binary in `~/.local/bin/whitakers-words` |

## Automated Downloads

These are downloaded on first use:
- **CLTK models** (~500MB) → `~/cltk_data/`
- **CDSL data** → `~/cdsl_data/`

## Commands

### Basic Queries
```bash
langnet-cli query lat lupus
langnet-cli query grc ἄνθρωπος  
langnet-cli query san dharma
```

### Health Checks
```bash
langnet-cli verify          # Check all backends
langnet-cli health         # Alias for verify
```

### API Usage
```bash
# Start server
uvicorn-run

# Query via HTTP
curl "http://localhost:8000/api/q?l=lat&s=lupus"
curl -X POST "http://localhost:8000/api/q" -d "l=lat&s=lupus"
```

### Cache Management
```bash
langnet-cli cache-clear    # Clear query cache
langnet-cli cache-stats    # Show cache statistics
```

### Indexer Tools (CTS URN)
```bash
# Build citation index
langnet-cli indexer build cts-urn --source /path/to/Classics-Data

# Query citation index
langnet-cli indexer query "Hom. Il." --language grc
```

## Troubleshooting

### Backend Services Not Found
```bash
langnet-cli verify  # Shows which services are unavailable

# Sanskrit Heritage Platform
curl http://localhost:48080/sktreader

# Diogenes
curl http://localhost:8888

# Whitaker's Words
~/.local/bin/whitakers-words lupus
```

### Common Issues
- **CLTK downloading data**: First query may take ~5 minutes
- **Cache issues**: Run `langnet-cli cache-clear` if responses seem stale
- **Process restart needed**: After code changes, restart API server with `uvicorn-run`

## Development

See [DEVELOPER.md](DEVELOPER.md) for detailed setup and AI-assisted workflow.