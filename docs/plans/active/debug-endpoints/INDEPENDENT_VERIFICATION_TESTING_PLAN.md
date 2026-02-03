# Independent Verification Testing Plan for Debugging Infrastructure

## Overview

This testing plan provides an independent audit framework for the newly implemented debugging infrastructure in the langnet-cli project. The plan focuses on verifying that the shared utility functions used by both the API endpoints and CLI commands are working correctly and consistently.

**File Location:** `/home/nixos/langnet-tools/langnet-cli/docs/INDEPENDENT_VERIFICATION_TESTING_PLAN.md`

## Testing Philosophy

### Core Principles
1. **Shared Code Testing**: Verify that the same utility functions are used across both API endpoints and CLI commands
2. **Independent Verification**: Test logic without relying on the implementation details of the CLI
3. **Comprehensive Coverage**: Validate all components of the debugging infrastructure
4. **Reproducible Tests**: Ensure tests can be run independently and produce consistent results

### Architecture Overview
The debugging infrastructure consists of:
- **Core Engine Methods**: `get_tool_data()` and tool-specific methods in `src/langnet/engine/core.py`
- **API Endpoint**: `/api/tool/{tool}/{action}` in `src/langnet/asgi.py`
- **CLI Interface**: `langnet-cli tool {tool} {action}` in `src/langnet/cli.py`
- **Shared Utilities**: `_tool_query()` and related functions
- **Testing Framework**: `tests/fuzz_tool_outputs.py` and `tests/helpers/tool_fixtures.py`

## Test Categories

### 1. Core Engine Functionality Testing

**Objective**: Verify that the `get_tool_data()` method and its tool-specific implementations work correctly.

**Test Cases**:
- **Tool Validation**: Test invalid tool and action parameters
- **Parameter Validation**: Test missing required parameters for each tool
- **Backend Integration**: Test actual backend calls for all supported tools
- **Response Format**: Validate JSON response structure and data types
- **Error Handling**: Test error propagation and exception handling

**Test Commands**:
```bash
# Test direct engine functionality
python -c "
from src.langnet.engine.core import LanguageEngineConfig, LanguageEngine
from langnet.cache.core import NoOpCache
from src.langnet.diogenes.core import DiogenesScraper
from src.langnet.whitakers_words.core import WhitakersWords
from src.langnet.cologne.core import SanskritCologneLexicon
from src.langnet.classics_toolkit.core import ClassicsToolkit
from src.langnet.heritage.morphology import HeritageMorphologyService
from src.langnet.heritage.dictionary import HeritageDictionaryService

config = LanguageEngineConfig(
    scraper=DiogenesScraper(),
    whitakers=WhitakersWords(),
    cltk=ClassicsToolkit(),
    cdsl=SanskritCologneLexicon(),
    heritage_morphology=HeritageMorphologyService(),
    heritage_dictionary=HeritageDictionaryService(),
    cache=NoOpCache(),
    normalization_pipeline=None,
    enable_normalization=False
)

engine = LanguageEngine(config)

# Test all tools
test_cases = [
    ('diogenes', 'search', 'lat', 'lupus'),
    ('whitakers', 'search', None, 'lupus'),
    ('heritage', 'search', None, 'agni'),
    ('cdsl', 'search', None, 'agni'),
    ('cltk', 'search', 'lat', 'lupus'),
]

for tool, action, lang, query in test_cases:
    try:
        result = engine.get_tool_data(tool, action, lang, query)
        print(f'✓ {tool}: {len(result)} entries')
    except Exception as e:
        print(f'✗ {tool}: {e}')
"

# Test error cases
python -c "
from src.langnet.engine.core import LanguageEngineConfig, LanguageEngine
from langnet.cache.core import NoOpCache

config = LanguageEngineConfig(
    scraper=None, whitakers=None, cltk=None, cdsl=None,
    heritage_morphology=None, heritage_dictionary=None, cache=NoOpCache(),
    normalization_pipeline=None, enable_normalization=False
)

engine = LanguageEngine(config)

# Test invalid tools
try:
    engine.get_tool_data('invalid', 'search', None, 'test')
    print('✗ Should have failed for invalid tool')
except ValueError as e:
    print(f'✓ Invalid tool error: {e}')

# Test invalid actions
try:
    engine.get_tool_data('diogenes', 'invalid', 'lat', 'test')
    print('✗ Should have failed for invalid action')
except ValueError as e:
    print(f'✓ Invalid action error: {e}')
"
```

### 2. API Endpoint Testing

**Objective**: Verify that the `/api/tool/{tool}/{action}` endpoint works correctly and uses the same core engine methods.

**Test Cases**:
- **Endpoint Availability**: Test that the endpoint is accessible and properly configured
- **Parameter Handling**: Test query parameter parsing and validation
- **Response Consistency**: Verify API responses match direct engine calls
- **Error Handling**: Test error responses for invalid inputs
- **Performance**: Test response times and resource usage

**Test Commands**:
```bash
# Test API endpoint availability
curl -s "http://localhost:8000/api/health" | jq .

# Test valid API calls
curl -s "http://localhost:8000/api/tool/diogenes/search?lang=lat&query=lupus" | jq .
curl -s "http://localhost:8000/api/tool/whitakers/search?query=lupus" | jq .
curl -s "http://localhost:8000/api/tool/cdsl/search?query=agni" | jq .

# Test error cases
curl -s "http://localhost:8000/api/tool/invalid/search?query=test" | jq .
curl -s "http://localhost:8000/api/tool/diogenes/invalid?lang=lat&query=test" | jq .
curl -s "http://localhost:8000/api/tool/diogenes/search?query=test" | jq .  # missing lang

# Test parameter validation
curl -s "http://localhost:8000/api/tool/diogenes/search?lang=invalid&query=test" | jq .
curl -s "http://localhost:8000/api/tool/cltk/search?lang=lat&query=test" | jq .  # missing action
```

### 3. CLI Interface Testing

**Objective**: Verify that CLI commands use the same shared utility functions and produce consistent results.

**Test Cases**:
- **Command Structure**: Test all CLI commands and their options
- **Parameter Validation**: Test CLI parameter handling and validation
- **Output Formats**: Test JSON, pretty, and YAML output formats
- **Fixture Generation**: Test `--save` option for generating test fixtures
- **Help Documentation**: Test `--help` output accuracy

**Test Commands**:
```bash
# Test CLI command structure
langnet-cli tool --help
langnet-cli tool diogenes --help
langnet-cli tool diogenes search --help

# Test all CLI tools
langnet-cli tool diogenes search --lang lat --query lupus
langnet-cli tool diogenes search --lang lat --query lupus --output pretty
langnet-cli tool whitakers search --query lupus
langnet-cli tool whitakers search --query lupus --output yaml
langnet-cli tool heritage search --query agni
langnet-cli tool cdsl search --query agni
langnet-cli tool cltk search --lang lat --query lupus

# Test fixture generation
langnet-cli tool diogenes search --lang lat --query lupus --save test_diogenes_fixture
langnet-cli tool whitakers search --query lupus --save test_whitakers_fixture

# Test error cases
langnet-cli tool invalid search --query test
langnet-cli tool diogenes invalid --lang lat --query test
langnet-cli tool diogenes search --query test  # missing lang
```

### 4. Shared Utility Function Testing

**Objective**: Verify that `_tool_query()` and other shared functions work consistently across both API and CLI.

**Test Cases**:
- **Function Consistency**: Test that the same function is called by both API and CLI
- **Parameter Handling**: Test parameter validation and transformation
- **HTTP Client**: Test HTTP request handling and response parsing
- **Output Formatting**: Test consistent output formatting across interfaces
- **Error Propagation**: Test error handling and propagation

**Test Commands**:
```bash
# Test _tool_query function directly
python -c "
from src.langnet.cli import _tool_query
import json

# Test Diogenes via _tool_query
print('Testing _tool_query with Diogenes:')
try:
    _tool_query('diogenes', 'search', lang='lat', query='lupus', output='json')
    print('✓ Diogenes _tool_query test passed')
except Exception as e:
    print(f'✗ Diogenes _tool_query test failed: {e}')

# Test Whitakers via _tool_query
print('Testing _tool_query with Whitakers:')
try:
    _tool_query('whitakers', 'search', query='lupus', output='json')
    print('✓ Whitakers _tool_query test passed')
except Exception as e:
    print(f'✗ Whitakers _tool_query test failed: {e}')
"

# Test parameter validation
python -c "
from src.langnet.cli import _tool_query

# Test missing required parameters
try:
    _tool_query('diogenes', 'search', query='lupus')  # missing lang
    print('✗ Should have failed for missing lang')
except Exception as e:
    print(f'✓ Missing lang error: {e}')

try:
    _tool_query('whitakers', 'search')  # missing query
    print('✗ Should have failed for missing query')
except Exception as e:
    print(f'✓ Missing query error: {e}')
"
```

### 5. Fuzz Testing Framework Verification

**Objective**: Verify that the fuzz testing framework can systematically test all debugging infrastructure components.

**Test Cases**:
- **Fuzz Generation**: Test automated test case generation
- **Schema Validation**: Test JSON schema validation of fixtures
- **Regression Testing**: Test detection of backend changes
- **Performance Testing**: Test concurrent request handling
- **Memory Testing**: Test memory leak detection

**Test Commands**:
```bash
# Run comprehensive fuzz testing
python tests/fuzz_tool_outputs.py

# Run fuzz testing with specific tools
python tests/fuzz_tool_outputs.py --tools diogenes,whitakers,heritage

# Run fuzz testing with verbose output
python tests/fuzz_tool_outputs.py --verbose --count 50

# Test schema validation
python -c "
from tests.helpers.tool_fixtures import ToolFixtureMixin
import json
from pathlib import Path

# Test fixture loading and validation
try:
    fixture = ToolFixtureMixin.load_fixture('diogenes_search_lat_lupus.json')
    print(f'✓ Fixture loaded: {len(fixture)} entries')
    
    # Test validation
    is_valid = ToolFixtureMixin.validate_fixture(fixture, 'diogenes', 'search')
    print(f'✓ Fixture validation: {is_valid}')
except Exception as e:
    print(f'✗ Fixture test failed: {e}')
"

# Test comparison utilities
python tools/compare_tool_outputs.py --help
```

### 6. Fixture Management Testing

**Objective**: Verify that fixture generation and validation work correctly.

**Test Cases**:
- **Fixture Generation**: Test generating fixtures from API responses
- **Schema Validation**: Test validation against JSON schemas
- **Fixture Loading**: Test loading fixtures for comparison
- **Fixture Organization**: Test proper organization by tool/action/language
- **Cleanup**: Test fixture management utilities

**Test Commands**:
```bash
# Generate fixtures via API
curl -s "http://localhost:8000/api/tool/diogenes/search?lang=lat&query=lupus&save=true" | jq .

# List generated fixtures
ls -la tests/fixtures/raw_tool_outputs/

# Test fixture validation
python -c "
from tests.helpers.tool_fixtures import ToolFixtureMixin
from pathlib import Path

# Test loading and validation
fixture_dir = Path('tests/fixtures/raw_tool_outputs')
if fixture_dir.exists():
    for fixture_file in fixture_dir.glob('*.json'):
        try:
            fixture = ToolFixtureMixin.load_fixture(fixture_file.name)
            is_valid = ToolFixtureMixin.validate_fixture(fixture, 'diogenes', 'search')
            print(f'✓ {fixture_file.name}: {is_valid}')
        except Exception as e:
            print(f'✗ {fixture_file.name}: {e}')
else:
    print('✗ Fixtures directory not found')
"

# Test comparison utilities
python -c "
from tools.compare_tool_outputs import compare_tools
import json

# Test tool comparison
try:
    result = compare_tools(['diogenes', 'whitakers'], query='lupus')
    print(f'✓ Tool comparison completed: {len(result)} results')
except Exception as e:
    print(f'✗ Tool comparison failed: {e}')
"
```

### 7. Integration Testing

**Objective**: Verify that all components work together correctly.

**Test Cases**:
- **End-to-End Workflow**: Test complete workflow from CLI to API to fixtures
- **Multi-Tool Consistency**: Test same word across different backends
- **Cache Interaction**: Test cache interaction with debugging endpoints
- **Error Propagation**: Test error handling through the entire system
- **Performance Benchmarking**: Compare debugging vs normal query performance

**Test Commands**:
```bash
# Complete workflow test
echo "Testing complete workflow:"
echo "1. Generate fixtures via CLI"
langnet-cli tool diogenes search --lang lat --query lupus --save diogenes_lupus
langnet-cli tool whitakers search --query lupus --save whitakers_lupus

echo "2. Compare fixtures"
python tools/compare_tool_outputs.py compare --fixture1 diogenes_lupus.json --fixture2 whitakers_lupus.json

echo "3. Test API consistency"
curl -s "http://localhost:8000/api/tool/diogenes/search?lang=lat&query=lupus" > api_diogenes.json
curl -s "http://localhost:8000/api/tool/whitakers/search?query=lupus" > api_whitakers.json

echo "4. Compare API vs CLI fixtures"
python tools/compare_tool_outputs.py compare --fixture1 diogenes_lupus.json --fixture2 api_diogenes.json

# Performance comparison
echo "Performance testing:"
time curl -s "http://localhost:8000/api/q?l=lat&s=lupus" > normal_query.json
time curl -s "http://localhost:8000/api/tool/diogenes/search?lang=lat&query=lupus" > debug_query.json
echo "Normal query: $(wc -c < normal_query.json) bytes"
echo "Debug query: $(wc -c < debug_query.json) bytes"
```

## Test Environment Setup

### Prerequisites Checklist
- [ ] **Backend Services**: Diogenes, Heritage Platform, CLTK, Whitakers' Words, CDSL running
- [ ] **API Server**: langnet API server running on `localhost:8000`
- [ ] **Dependencies**: All Python dependencies installed
- [ ] **Test Directories**: `tests/fixtures/raw_tool_outputs/` exists
- [ ] **Environment**: Proper environment variables set
- [ ] **Permissions**: Write permissions for test directories

### Setup Commands
```bash
# Check backend services
curl -s "http://localhost:8000/api/health" | jq .

# Verify API server is running
curl -s "http://localhost:8000/api/q?l=lat&s=test" | jq .

# Create test directories
mkdir -p tests/fixtures/raw_tool_outputs
mkdir -p tests/fuzz_reports

# Install dependencies
pip install -r devenv.requirements.txt

# Verify all tools are accessible
which whitakers-words 2>/dev/null || echo "Whitakers' Words not found"
python -c "from src.langnet.diogenes.core import DiogenesScraper; print('Diogenes OK')" 2>/dev/null || echo "Diogenes failed"
python -c "from src.langnet.cologne.core import SanskritCologneLexicon; print('CDSL OK')" 2>/dev/null || echo "CDSL failed"
python -c "from src.langnet.heritage.morphology import HeritageMorphologyService; print('Heritage OK')" 2>/dev/null || echo "Heritage failed"
```

## Test Execution Procedure

### Phase 1: Core Engine Testing (30 minutes)
1. Run the core engine test commands
2. Verify all tools return expected results
3. Check error handling for invalid inputs
4. Document any failures

### Phase 2: API Endpoint Testing (30 minutes)
1. Test API endpoint availability
2. Test parameter validation
3. Verify response consistency with engine calls
4. Test error responses

### Phase 3: CLI Interface Testing (30 minutes)
1. Test all CLI commands
2. Verify output formats
3. Test fixture generation
4. Check help documentation

### Phase 4: Shared Utility Testing (20 minutes)
1. Test `_tool_query()` function directly
2. Verify parameter handling
3. Test error propagation

### Phase 5: Fuzz Testing (45 minutes)
1. Run comprehensive fuzz testing
2. Test schema validation
3. Check performance metrics
4. Review regression testing results

### Phase 6: Fixture Management (20 minutes)
1. Test fixture generation
2. Validate fixtures
3. Test comparison utilities

### Phase 7: Integration Testing (45 minutes)
1. Test complete workflows
2. Compare multi-tool results
3. Performance benchmarking
4. Error handling verification

## Success Criteria

### Functional Requirements
- [ ] All core engine methods work correctly for all tools
- [ ] API endpoints return consistent responses with engine calls
- [ ] CLI commands use shared utility functions consistently
- [ ] Fuzz testing generates valid test cases
- [ ] Fixture generation creates valid JSON files
- [ ] Comparison utilities detect differences correctly

### Performance Requirements
- [ ] API response time < 5 seconds for most queries
- [ ] CLI commands complete within 10 seconds
- [ ] Memory usage remains stable during testing
- [ ] Concurrent requests handled gracefully

### Quality Requirements
- [ ] All code compiles without errors
- [ ] Error messages are clear and helpful
- [ ] Documentation is accurate and complete
- [ ] Test coverage is comprehensive
- [ ] Same code used across API and CLI interfaces

## Test Reporting

### Required Documentation
1. **Test Results Log**: Detailed output of all test commands
2. **Failure Reports**: Documented failures with error details
3. **Performance Metrics**: Timing and resource usage data
4. **Comparison Reports**: Differences detected by comparison tools
5. **Issue Tracking**: List of identified issues and their status

### Summary Metrics
- Total test cases executed
- Success rate percentage
- Performance benchmarks
- Error categorization
- Regression detection summary
- Coverage analysis

## Troubleshooting Guide

### Common Issues
1. **Backend Services Unavailable**
   - Check: `curl -s "http://localhost:8000/api/health"`
   - Solution: Ensure all backend services are running

2. **API Server Not Running**
   - Check: Ensure server is listening on port 8000
   - Solution: Start the API server

3. **Permission Issues**
   - Check: Write permissions for `tests/fixtures/`
   - Solution: Run with appropriate user permissions

4. **Missing Dependencies**
   - Check: All Python packages installed
   - Solution: Run `pip install -r devenv.requirements.txt`

5. **Invalid Fixture Schemas**
   - Check: JSON syntax in fixture files
   - Solution: Run schema validation

### Debug Commands
```bash
# Test individual backends
python -c "from src.langnet.diogenes.core import DiogenesScraper; DiogenesScraper().parse_word('lupus', 'LATIN')"
python -c "from src.langnet.whitakers_words.core import WhitakersWords; WhitakersWords().words(['lupus'])"

# Test server connectivity
curl -v "http://localhost:8000/api/health"

# Check logs
tail -f logs/langnet.log 2>/dev/null || echo "No logs found"

# Test with verbose output
curl -v "http://localhost:8000/api/tool/diogenes/search?lang=lat&query=lupus"
```

## Independent Verification Checklist

### Code Review Points
1. [ ] Verify that API endpoints call `get_tool_data()` directly
2. [ ] Verify that CLI commands use `_tool_query()` function
3. [ ] Verify that `_tool_query()` calls the API endpoints
4. [ ] Verify that no hardcoded logic exists in CLI commands
5. [ ] Verify that error handling is consistent across interfaces

### Test Execution Points
1. [ ] Run all test commands as specified
2. [ ] Document actual vs expected results
3. [ ] Verify that the same functions are being called
4. [ ] Check that responses are consistent across interfaces
5. [ ] Validate that generated fixtures are correct

### Final Verification
1. [ ] All tests pass successfully
2. [ ] No duplicate or conflicting logic found
3. [ ] Performance meets requirements
4. [ ] Documentation is accurate
5. [ ] Issues are documented and resolved

---

**Testing Plan Location**: `/home/nixos/langnet-tools/langnet-cli/docs/INDEPENDENT_VERIFICATION_TESTING_PLAN.md`

**Contact**: For questions about this testing plan, refer to the project documentation or development team.

**Note**: This testing plan should be executed by an independent tester who has not participated in the development of the debugging infrastructure to ensure unbiased verification.