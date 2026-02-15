# Getting Started with Langnet CLI

A command-line tool for querying classical language lexicons and morphological analysis.

## Quick Setup

```bash
# Enter development environment (preferred)
devenv shell langnet-cli

# Or run a single command with the environment activated
devenv shell just -- cli query lat lupus --output json

# Check available backends (requires external services running)
devenv shell just -- cli verify

# Query words
devenv shell just -- cli query lat lupus      # Latin
devenv shell just -- cli query grc λόγος     # Greek  
devenv shell just -- cli query san agni      # Sanskrit
```

## External Services Required

| Service | Language | Purpose | Status |
|---------|----------|---------|--------|
| **Sanskrit Heritage Platform** | Sanskrit | Morphology + dictionary | Must be running at `localhost:48080` |
| **Diogenes** | Greek/Latin | Lexicons (Lewis & Short, Liddell & Scott) | Must be running at `localhost:8888` |
| **Whitaker's Words** | Latin | Morphological analysis | Binary in `~/.local/bin/whitakers-words` |

These services are not bundled with the project; run them locally before using `langnet-cli verify` or making queries.

## Commands

### Basic Queries
```bash
devenv shell just -- cli query lat lupus
devenv shell just -- cli query grc ἄνθρωπος  
devenv shell just -- cli query san dharma
```

To learn how to consume the JSON output (what fields to show learners first, where references and Foster functions live), see **[docs/OUTPUT_GUIDE.md](OUTPUT_GUIDE.md)**.

### Health Checks
```bash
devenv shell just -- cli verify          # Check all backends
devenv shell just -- cli health         # Alias for verify
```

### API Usage
```bash

# Query via HTTP
curl "http://localhost:8000/api/q?l=lat&s=lupus"
curl -X POST "http://localhost:8000/api/q" -d "l=lat&s=lupus"
```

### Indexer Tools (CTS URN)
```bash
# Build citation index
devenv shell just -- cli indexer build cts-urn --source /path/to/Classics-Data

# Query citation index
devenv shell just -- cli indexer query "Hom. Il." --language grc
```

## Troubleshooting

### Backend Services Not Found
```bash
devenv shell just -- cli verify  # Shows which services are unavailable

# Sanskrit Heritage Platform
curl http://localhost:48080/sktreader

# Diogenes
curl http://localhost:8888

# Whitaker's Words
~/.local/bin/whitakers-words lupus
```

### Common Issues
- **CLTK downloading data**: First query may take ~5 minutes
- **Process restart needed**: After code changes, restart API server with `just restart-server`
- **External services missing**: Most queries depend on Heritage, Diogenes, and Whitaker's Words being available locally; `devenv shell just -- cli verify` reports which ones are missing.

## Development

See [DEVELOPER.md](DEVELOPER.md) for detailed setup and AI-assisted workflow.
