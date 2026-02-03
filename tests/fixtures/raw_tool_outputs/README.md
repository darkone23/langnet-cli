# Raw Tool Output Fixtures

This directory contains raw output fixtures from individual backend tools for testing and debugging purposes.

## Directory Structure

```
tests/fixtures/raw_tool_outputs/
├── diogenes/          # Diogenes backend outputs (Latin/Greek)
├── whitakers/         # Whitaker's Words outputs (Latin)
├── heritage/          # Heritage Platform outputs (Sanskrit)
├── cdsl/             # CDSL outputs (Sanskrit)
└── cltk/             # CLTK outputs (Latin/Greek/Sanskrit)
```

## File Naming Convention

Files are named using the pattern: `{tool}_{action}_{lang}_{query}.json`

Examples:
- `diogenes_search_lat_lupus.json` - Diogenes search for "lupus" in Latin
- `heritage_morphology_sanskrit_agni.json` - Heritage morphology for "agni" in Sanskrit
- `whitakers_analyze_lupus.json` - Whitaker's analysis for "lupus"

## Generating Fixtures

Use the CLI tool commands to generate fixtures:

```bash
# Generate Diogenes fixture
langnet-cli tool diogenes search --lang lat --query lupus --save

# Generate Heritage fixture
langnet-cli tool heritage morphology --query agni --save

# Generate Whitakers fixture
langnet-cli tool whitakers analyze --query lupus --save
```

## Using Fixtures in Tests

Fixtures can be loaded in tests using the helper functions:

```python
from tests.helpers.tool_fixtures import load_tool_fixture

# Load a fixture
data = load_tool_fixture("diogenes", "search", "lat", "lupus")
```

## Schema Validation

Each tool should have a corresponding schema file:
- `diogenes/schema_diogenes.json`
- `whitakers/schema_whitakers.json`
- `heritage/schema_heritage.json`
- `cdsl/schema_cdsl.json`
- `cltk/schema_cltk.json`

These schemas define the expected structure of raw tool outputs.

## Git Ignore

Large fixture files should be added to `.gitignore` to avoid committing binary data. Only schema files and small sample fixtures should be committed.

## Updating Fixtures

When backend APIs change, fixtures should be updated by re-running the CLI commands with the `--save` flag. Use the comparison tools to detect schema changes.

## Best Practices

1. **Commit only schema files**: Large fixture files should not be committed to version control
2. **Use descriptive names**: Include language and query information in filenames
3. **Update regularly**: Regenerate fixtures when backends change
4. **Validate structure**: Use schema validation to ensure fixture integrity
5. **Document changes**: Keep track of when and why fixtures were updated