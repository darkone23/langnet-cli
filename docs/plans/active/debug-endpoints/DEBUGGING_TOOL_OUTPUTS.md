# Debugging Tool Outputs & Schema Evolution

This guide provides comprehensive workflows for debugging individual backend tools and managing schema evolution in the langnet project.

## Overview

The debugging infrastructure provides three main capabilities:

1. **Tool-Specific Endpoints** - Direct access to raw backend outputs
2. **CLI Debug Commands** - Command-line interface for tool testing
3. **Fuzz Testing & Comparison** - Automated testing and validation

## Using Tool-Specific Endpoints

### API Endpoints

The `/api/tool/{tool}/{action}` endpoints provide direct access to individual backend tools:

```bash
# Diogenes search for Latin word
curl "http://localhost:8000/api/tool/diogenes/search?lang=lat&query=lupus"

# Whitaker's analysis for Latin word
curl "http://localhost:8000/api/tool/whitakers/analyze?query=lupus"

# Heritage morphology for Sanskrit word
curl "http://localhost:8000/api/tool/heritage/morphology?query=agni"

# CDSL lookup for Sanskrit word
curl "http://localhost:8000/api/tool/cdsl/lookup?dict=mw&query=agni"

# CLTK morphology for Greek word
curl "http://localhost:8000/api/tool/cltk/morphology?lang=grc&query=logos"
```

### Response Format

All endpoints return raw backend data in JSON format without any adapter conversion:

```json
{
  "chunks": [
    {
      "headword": "lupus",
      "morphology": {
        "morphs": [
          {
            "stem": ["lup"],
            "tags": ["noun"],
            "defs": ["wolf"]
          }
        ]
      }
    }
  ],
  "dg_parsed": true
}
```

### Error Handling

- **400 Bad Request**: Missing or invalid parameters
- **404 Not Found**: Unknown tool or action
- **500 Internal Server Error**: Backend service error

## CLI Debug Commands

### Basic Tool Commands

The `langnet-cli tool` command group provides access to all backend tools:

```bash
# Diogenes commands
langnet-cli tool diogenes search --lang lat --query lupus
langnet-cli tool diogenes parse --lang grc --query logos

# Whitaker's commands
langnet-cli tool whitakers analyze --query lupus

# Heritage commands
langnet-cli tool heritage morphology --query agni
langnet-cli tool heritage dictionary --query yoga --dict mw
langnet-cli tool heritage analyze --query dharma

# CDSL commands
langnet-cli tool cdsl lookup --dict mw --query agni
langnet-cli tool cdsl search --query yoga

# CLTK commands
langnet-cli tool cltk morphology --lang lat --query lupus
langnet-cli tool cltk parse --lang grc --query logos
```

### Output Formats

Use the `--output` option to control output format:

```bash
# JSON output (default)
langnet-cli tool diogenes search --lang lat --query lupus --output json

# Pretty formatted output
langnet-cli tool diogenes search --lang lat --query lupus --output pretty

# YAML output
langnet-cli tool diogenes search --lang lat --query lupus --output yaml
```

### Generating Fixtures

The `--save` option automatically saves outputs as fixtures:

```bash
# Generate fixture for Diogenes search
langnet-cli tool diogenes search --lang lat --query lupus --save

# Generate fixture for Heritage analysis
langnet-cli tool heritage analyze --query agni --save --dict mw

# Fixtures are saved to tests/fixtures/raw_tool_outputs/
```

### Generic Query Interface

Use the `tool query` command for flexible testing:

```bash
langnet-cli tool query \
  --tool diogenes \
  --action search \
  --lang lat \
  --query lupus \
  --output pretty \
  --save
```

## Fuzz Testing & Validation

### Running Fuzz Tests

The fuzz testing module provides automated testing for all tools:

```bash
# Test specific tool and action
python -m tests.fuzz_tool_outputs \
  --tool diogenes \
  --action search \
  --words "lupus,arma,vir"

# Validate fixtures against schemas
python -m tests.fuzz_tool_outputs \
  --tool heritage \
  --action morphology \
  --validate

# Compare raw vs unified outputs
python -m tests.fuzz_tool_outputs \
  --tool cdsl \
  --action lookup \
  --compare

# Run comprehensive test
python -m tests.fuzz_tool_outputs \
  --validate \
  --compare
```

### Word Lists

Predefined word lists are available for each language:

```python
from tests.fuzz_tool_outputs import get_test_word_lists

words = get_test_word_lists()
print(words["latin"])    # ["lupus", "arma", "vir", "rosa", "amicus"]
print(words["greek"])    # ["logos", "anthropos", "polis", "theos", "bios"]
print(words["sanskrit"]) # ["agni", "yoga", "karma", "dharma", "atman"]
```

## Fixtures Management

### Directory Structure

```
tests/fixtures/raw_tool_outputs/
├── diogenes/
│   ├── schema_diogenes.json
│   ├── search_lat_lupus.json
│   ├── search_grc_logos.json
│   └── parse_lat_arma.json
├── whitakers/
│   ├── schema_whitakers.json
│   ├── analyze_lupus.json
│   └── analyze_arma.json
├── heritage/
│   ├── schema_heritage.json
│   ├── morphology_sanskrit_agni.json
│   ├── dictionary_mw_yoga.json
│   └── analyze_dharma.json
├── cdsl/
│   ├── schema_cdsl.json
│   ├── lookup_mw_agni.json
│   └── search_yoga.json
└── cltk/
    ├── schema_cltk.json
    ├── morphology_lat_lupus.json
    ├── morphology_grc_logos.json
    └── morphology_sanskrit_agni.json
```

### Generating Fixtures

Use CLI commands to generate fixtures:

```bash
# Generate multiple fixtures
for word in lupus arma vir; do
  langnet-cli tool diogenes search --lang lat --query $word --save
done

# Generate for all tools
for tool in diogenes whitakers heritage cdsl cltk; do
  langnet-cli tool $tool query --query test --save 2>/dev/null || echo "Failed: $tool"
done
```

### Schema Validation

Each tool has a JSON schema for validation:

```bash
# Validate all fixtures for a tool
python -c "
from tests.fuzz_tool_outputs import ToolFuzzer
fuzzer = ToolFuzzer()
fuzzer.validate_fixtures('diogenes', 'search')
"

# Check schema compliance
python -c "
import jsonschema
with open('tests/fixtures/raw_tool_outputs/diogenes/schema_diogenes.json') as f:
    schema = json.load(f)
with open('tests/fixtures/raw_tool_outputs/diogenes/search_lat_lupus.json') as f:
    data = json.load(f)
jsonschema.validate(data, schema)
print('Fixture is valid!')
"
```

## Tool Output Comparison

### Comparing Raw vs Unified Outputs

Use the comparison tool to analyze differences between raw backend outputs and unified schema outputs:

```bash
# Compare specific word
python tools/compare_tool_outputs.py \
  --tool diogenes \
  --action search \
  --word lupus \
  --generate-fixes

# Detect schema drift
python tools/compare_tool_outputs.py \
  --tool heritage \
  --action morphology \
  --generate-fixes

# Save comparison results
python tools/compare_tool_outputs.py \
  --tool cdsl \
  --action lookup \
  --word agni \
  --output comparison_results.json
```

### Understanding Comparison Results

The comparison tool identifies:

- **Key Differences**: Missing or extra fields in unified output
- **Structural Changes**: Changes in data structure over time
- **Breaking Changes**: Changes that break adapter compatibility
- **Adapter Suggestions**: Code suggestions for fixing adapters

```json
{
  "key_differences": [
    {
      "type": "missing_in_unified",
      "path": "chunks[0].morphology.morphs[0].defs",
      "raw_value": ["wolf"]
    }
  ],
  "adapter_suggestions": [
    "Raw output uses 'chunks' structure - adapter should flatten to senses"
  ]
}
```

## Common Debugging Scenarios

### 1. Backend Not Responding

**Problem**: Tool API endpoint returns 500 error

**Solution**:
```bash
# Check backend health
curl http://localhost:8000/api/health

# Test backend directly
curl "http://localhost:8000/api/tool/diogenes/search?lang=lat&query=lupus"

# Check if backend services are running
ps aux | grep -E "(diogenes|whitakers|heritage|cdsl|cltk)"
```

### 2. Wrong Parameters

**Problem**: 400 Bad Request error

**Solution**:
```bash
# Check required parameters for each tool
echo "Diogenes: lang + query required"
echo "Whitakers: query required"
echo "Heritage: query required"
echo "CDSL: query + dict optional"
echo "CLTK: lang + query required"

# Validate parameters before calling
curl "http://localhost:8000/api/tool/diogenes/search?lang=lat&query="
# Returns: Missing required parameter: query for diogenes tool
```

### 3. Adapter Conversion Issues

**Problem**: Raw data looks correct but unified output is missing fields

**Solution**:
```bash
# Compare raw vs unified outputs
python tools/compare_tool_outputs.py \
  --tool diogenes \
  --action search \
  --word lupus

# Check adapter implementation
grep -r "adapt" src/langnet/backend_adapter.py

# Generate adapter fixes
python tools/compare_tool_outputs.py \
  --tool diogenes \
  --action search \
  --word lupus \
  --generate-fixes
```

### 4. Schema Validation Failures

**Problem**: New fixture doesn't match existing schema

**Solution**:
```bash
# Validate against schema
python -c "
import json, jsonschema
with open('tests/fixtures/raw_tool_outputs/diogenes/schema_diogenes.json') as f:
    schema = json.load(f)
with open('tests/fixtures/raw_tool_outputs/diogenes/search_lat_lupus.json') as f:
    data = json.load(f)
try:
    jsonschema.validate(data, schema)
    print('✓ Valid')
except jsonschema.ValidationError as e:
    print(f'✗ Invalid: {e.message}')
"

# Update schema if needed
# 1. Identify new fields in raw output
# 2. Update schema definition
# 3. Re-validate all fixtures
```

### 5. Performance Issues

**Problem**: Tool endpoints are slow

**Solution**:
```bash
# Time API responses
time curl "http://localhost:8000/api/tool/diogenes/search?lang=lat&query=lupus"

# Check cache performance
curl http://localhost:8000/api/cache/stats

# Test with different word lengths
for word in a aa aaa aaaaa; do
  echo "Testing: $word"
  time curl -s "http://localhost:8000/api/tool/diogenes/search?lang=lat&query=$word" > /dev/null
done
```

## Best Practices

### 1. Regular Fixture Updates

- Regenerate fixtures when backend APIs change
- Use `--save` flag when testing new queries
- Commit schema files but exclude large fixture files

### 2. Schema Evolution

- Monitor schema drift with comparison tools
- Update adapter code when breaking changes are detected
- Maintain backward compatibility where possible

### 3. Testing Strategy

- Use fuzz testing for comprehensive validation
- Test edge cases with CLI commands
- Validate fixtures against schemas regularly

### 4. Performance Monitoring

- Track response times for tool endpoints
- Monitor cache hit rates
- Profile memory usage for large responses

### 5. Documentation

- Update tool schemas when backends change
- Document new tool parameters
- Keep this guide updated with new debugging workflows

## Troubleshooting Quick Reference

| Issue | Command | Solution |
|-------|---------|----------|
| Backend not responding | `curl /api/health` | Check service status |
| Wrong parameters | `curl /api/tool/{tool}/{action}?lang=lat&query=` | Validate required params |
| Adapter issues | `python tools/compare_tool_outputs.py` | Compare raw vs unified |
| Schema errors | `python -c "import jsonschema; validate(...)"` | Update schema definition |
| Performance issues | `time curl /api/tool/...` | Check cache and optimize |

## Integration with Existing Workflow

The debugging tools integrate seamlessly with the existing langnet workflow:

1. **During Development**: Use CLI commands to test individual backends
2. **During Testing**: Generate fixtures and run fuzz tests
3. **During Maintenance**: Monitor schema drift and update adapters
4. **During Debugging**: Compare raw vs unified outputs to isolate issues

This infrastructure provides the "point in time" snapshot capability needed to manage the universal schema evolution process effectively.