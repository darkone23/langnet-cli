# Comprehensive Testing Plan for Debugging Infrastructure

This document outlines a comprehensive testing plan to validate the newly implemented debugging infrastructure for the langnet-cli project.

## Overview

The debugging infrastructure provides:
1. **Tool-specific API endpoints** (`/api/tool/{tool}/{action}`)
2. **CLI debug commands** (`langnet-cli tool {tool} {action}`)
3. **Fuzz testing framework** (`tests/fuzz_tool_outputs.py`)
4. **Fixture management system** (`tests/fixtures/raw_tool_outputs/`)
5. **Comparison utilities** (`tools/compare_tool_outputs.py`)

## Test Categories

### 1. API Endpoint Testing

#### Test Cases:
- **Valid tool requests** (all tools: diogenes, whitakers, heritage, cdsl, cltk)
- **Invalid tool requests** (unknown tools)
- **Valid action requests** (search, parse, analyze, morphology, dictionary, lookup)
- **Invalid action requests** (unknown actions)
- **Parameter validation** (missing required parameters, invalid languages)
- **Error handling** (backend failures, timeouts)
- **Response format validation** (JSON structure, data types)

#### Test Commands:
```bash
# Test Diogenes API
curl -s "http://localhost:8000/api/tool/diogenes/search?lang=lat&query=lupus" | jq .

# Test Whitakers API
curl -s "http://localhost:8000/api/tool/whitakers/search?query=lupus" | jq .

# Test Heritage API
curl -s "http://localhost:8000/api/tool/heritage/search?query=agni" | jq .

# Test CDSL API
curl -s "http://localhost:8000/api/tool/cdsl/search?query=agni" | jq .

# Test CLTK API
curl -s "http://localhost:8000/api/tool/cltk/search?lang=lat&query=lupus" | jq .

# Test error cases
curl -s "http://localhost:8000/api/tool/unknown/search?query=test" | jq .
curl -s "http://localhost:8000/api/tool/diogenes/unknown?lang=lat&query=test" | jq .
curl -s "http://localhost:8000/api/tool/diogenes/search?query=test" | jq .  # missing lang
```

### 2. CLI Command Testing

#### Test Cases:
- **All tool CLI commands** (diogenes, whitakers, heritage, cdsl, cltk)
- **All action types** (search, parse, analyze, morphology, dictionary, lookup)
- **Output formats** (json, pretty, yaml)
- **Fixture generation** (--save option)
- **Error handling** and validation
- **Help documentation** (--help)

#### Test Commands:
```bash
# Test Diogenes CLI commands
langnet-cli tool diogenes search --lang lat --query lupus
langnet-cli tool diogenes search --lang lat --query lupus --output pretty
langnet-cli tool diogenes search --lang lat --query lupus --save test_fixture

# Test Whitakers CLI commands
langnet-cli tool whitakers search --query lupus
langnet-cli tool whitakers search --query lupus --output yaml
langnet-cli tool whitakers search --query lupus --save test_fixture

# Test Heritage CLI commands
langnet-cli tool heritage search --query agni
langnet-cli tool heritage analyze --query agni
langnet-cli tool heritage dictionary --query agni --dict mw

# Test CDSL CLI commands
langnet-cli tool cdsl search --query agni
langnet-cli tool cdsl lookup --query agni --dict mw
langnet-cli tool cdsl search --query agni --save test_fixture

# Test CLTK CLI commands
langnet-cli tool cltk search --lang lat --query lupus
langnet-cli tool cltk morphology --lang grc --query λύκος

# Test error cases
langnet-cli tool unknown search --query test
langnet-cli tool diogenes unknown --lang lat --query test
langnet-cli tool diogenes search --query test  # missing lang

# Test help
langnet-cli tool --help
langnet-cli tool diogenes --help
langnet-cli tool diogenes search --help
```

### 3. Fuzz Testing Framework

#### Test Cases:
- **Automated fixture generation** for all tools
- **Schema validation** against JSON schemas
- **Regression testing** for backend changes
- **Performance testing** with multiple concurrent requests
- **Memory leak detection** during long-running tests

#### Test Commands:
```bash
# Run fuzz testing
python tests/fuzz_tool_outputs.py

# Run fuzz testing with specific tools
python tests/fuzz_tool_outputs.py --tools diogenes,whitakers

# Run fuzz testing with specific actions
python tests/fuzz_tool_outputs.py --actions search,parse

# Run fuzz testing with verbose output
python tests/fuzz_tool_outputs.py --verbose

# Run fuzz testing with specific test count
python tests/fuzz_tool_outputs.py --count 100

# Run fuzz testing with custom query patterns
python tests/fuzz_tool_outputs.py --queries "word1,word2,word3"
```

### 4. Fixture Management Testing

#### Test Cases:
- **Fixture generation** from API responses
- **Schema validation** of generated fixtures
- **Fixture loading** for comparison
- **Fixture organization** by tool/action/language
- **Fixture cleanup** utilities

#### Test Commands:
```bash
# Generate fixtures via API
curl -s "http://localhost:8000/api/tool/diogenes/search?lang=lat&query=lupus&save=true" | jq .

# Validate fixtures
python -c "
from tests.helpers.tool_fixtures import ToolFixtureMixin
fixture = ToolFixtureMixin.load_fixture('diogenes_search_lat_lupus.json')
print(f'Valid fixture: {len(fixture)} entries')
"

# List all fixtures
ls tests/fixtures/raw_tool_outputs/

# Test fixture validation
python tests/helpers/tool_fixtures.py validate-all
```

### 5. Comparison Utility Testing

#### Test Cases:
- **Raw vs Unified comparison** for all tools
- **Schema change detection** between versions
- **Regression identification** in adapters
- **Difference reporting** with visual formatting
- **Batch comparison** across multiple tools

#### Test Commands:
```bash
# Compare raw and unified outputs
python tools/compare_tool_outputs.py diogenes --lang lat --query lupus

# Compare specific fixtures
python tools/compare_tool_outputs.py compare --fixture1 diogenes_search_lat_lupus.json --fixture2 unified_lupus.json

# Generate comparison report
python tools/compare_tool_outputs.py report --tool diogenes --output comparison_report.html

# Batch comparison across all tools
python tools/compare_tool_outputs.py batch-compare --tools diogenes,whitakers,heritage,cdsl,cltk
```

### 6. Integration Testing

#### Test Cases:
- **End-to-end workflow** from CLI to API to fixtures
- **Multi-tool queries** for same word across different backends
- **Cache interaction** with debugging endpoints
- **Error propagation** through the entire system
- **Performance benchmarking** of debugging vs normal queries

#### Test Commands:
```bash
# Complete workflow test
langnet-cli tool diogenes search --lang lat --query lupus --save diogenes_fixture
langnet-cli tool whitakers search --query lupus --save whitakers_fixture
python tools/compare_tool_outputs.py compare --fixture1 diogenes_fixture.json --fixture2 whitakers_fixture.json

# Multi-tool comparison for same word
langnet-cli tool diogenes search --lang lat --query lupus --save diogenes_lupus
langnet-cli tool cltk search --lang lat --query lupus --save cltk_lupus
python tools/compare_tool_outputs.py compare --fixture1 diogenes_lupus.json --fixture2 cltk_lupus.json

# Performance comparison
time curl -s "http://localhost:8000/api/q?l=lat&s=lupus" | jq .
time curl -s "http://localhost:8000/api/tool/diogenes/search?lang=lat&query=lupus" | jq .
```

## Test Environment Setup

### Prerequisites:
1. **Backend services running** (Diogenes, Heritage Platform, etc.)
2. **API server running** (`localhost:8000`)
3. **Test fixtures directory** created
4. **Environment variables** set (if needed)
5. **Dependencies installed** (all tools available)

### Setup Commands:
```bash
# Start backend services
# (Ensure Diogenes, Heritage Platform, etc. are running)

# Start API server
# (Run the langnet API server)

# Create test fixtures directory
mkdir -p tests/fixtures/raw_tool_outputs

# Install dependencies
pip install -r devenv.requirements.txt

# Run server health check
curl -s "http://localhost:8000/api/health" | jq .
```

## Test Execution Plan

### Phase 1: Unit Testing (1-2 hours)
- Test individual components in isolation
- Validate parameter validation logic
- Test error handling and edge cases

### Phase 2: API Testing (1-2 hours)
- Test all API endpoints with various inputs
- Validate response formats and error codes
- Test concurrent request handling

### Phase 3: CLI Testing (1-2 hours)
- Test all CLI commands and options
- Validate output formats and fixture generation
- Test help documentation

### Phase 4: Integration Testing (2-3 hours)
- Test end-to-end workflows
- Validate fixture generation and comparison
- Test multi-tool scenarios

### Phase 5: Performance and Regression Testing (1-2 hours)
- Run fuzz testing framework
- Validate performance characteristics
- Test for memory leaks and resource usage

## Success Criteria

### Functional Criteria:
- All API endpoints return valid responses
- All CLI commands work as expected
- Fixture generation creates valid JSON files
- Comparison utilities detect differences correctly
- Fuzz testing catches edge cases

### Performance Criteria:
- API response time < 5 seconds for most queries
- CLI commands complete within 10 seconds
- Memory usage remains stable during testing
- Concurrent requests handled gracefully

### Quality Criteria:
- All code compiles without errors
- Error messages are clear and helpful
- Documentation is accurate and complete
- Test coverage is comprehensive

## Troubleshooting

### Common Issues:
1. **Backend services not available**
   - Solution: Ensure all backend services are running and accessible
   - Check: `curl -s "http://localhost:8000/api/health" | jq .`

2. **API server not running**
   - Solution: Start the API server using the appropriate command
   - Check: Ensure server is listening on port 8000

3. **Permission issues with fixtures**
   - Solution: Check write permissions for `tests/fixtures/` directory
   - Solution: Run with appropriate user permissions

4. **Missing dependencies**
   - Solution: Install all required dependencies
   - Solution: Check environment activation

5. **Invalid fixture schemas**
   - Solution: Run schema validation
   - Solution: Check JSON syntax in fixture files

## Test Reporting

### Output Files:
- **API test results**: Console output with curl commands and responses
- **CLI test results**: Command output and error messages
- **Fuzz test reports**: `tests/fuzz_reports/` directory
- **Comparison reports**: HTML and JSON comparison outputs
- **Performance logs**: Timing and resource usage metrics

### Summary Metrics:
- Total test cases executed
- Success rate percentage
- Performance benchmarks
- Error categorization
- Regression detection summary

## Continuous Integration

### Automated Testing:
- Add debugging infrastructure tests to CI pipeline
- Schedule regular fuzz testing runs
- Monitor performance metrics over time
- Track schema changes and adapter updates

### Monitoring:
- Log test results and failures
- Monitor API response times
- Track fixture generation success rates
- Monitor memory usage patterns

---

This comprehensive testing plan ensures that the debugging infrastructure is thoroughly validated and ready for production use. The systematic approach covers all components and their interactions, providing confidence in the reliability and effectiveness of the tools.