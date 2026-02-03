# Tool-Specific Debug Endpoints & Fuzz Testing Plan

**Status**: 🎯 ACTIVE (Implementation Phase)
**Priority**: HIGH
**Dependencies**: Universal Schema plan in progress
**Target Audience**: Developers with minimal langnet experience

## Goal
Create tool-specific debug endpoints (`/api/tool/{tool}/{action}`) and CLI commands (`langnet-cli tool`) to expose raw backend data for debugging schema evolution and fixing broken tests.

## Problem Statement
The universal schema conversion makes debugging difficult because:
1. Raw backend outputs are hidden inside adapter conversions
2. Broken tests don't show which backend is failing
3. Schema evolution is opaque - hard to see what changed
4. No way to test individual backend components independently

## Solution Overview
Expose individual backend tools through dedicated endpoints and CLI commands, enabling:
- Direct testing of each backend tool
- Capture of real backend outputs for fixture generation
- Comparison between raw data and unified schema outputs
- Systematic debugging of adapter conversion issues

## Tool Capabilities Matrix

| Tool | Primary Methods | Supported Actions | Languages | Output Type |
|------|----------------|-------------------|-----------|-------------|
| **Diogenes** | `parse_word(word, language)` | `search`, `parse` | `lat`, `grc`/`grk` | `DiogenesResultT` |
| **Whitaker's Words** | `words(search: list[str])` | `analyze` | `lat` only | `WhitakersWordsResult` |
| **CLTK** | `latin_query(word)`, `greek_morphology_query(word)`, `sanskrit_morphology_query(word)` | `morphology`, `dictionary` | `lat`, `grc`, `san` | Various `*Result` types |
| **Heritage Platform** | `analyze_word(word)`, `lookup_word(word, dict_id)` | `morphology`, `dictionary`, `analyze`, `batch` | `san` only | `HeritageMorphologyResult`, dict |
| **CDSL** | `lookup_ascii(data)`, `lookup(dict_id, key)` | `lookup`, `search`, `prefix` | `san` only | `CdslQueryResult` list |

---

## PHASE 1: Tool-Specific API Endpoints (Est: 3 days)

### 1.1 Create `/api/tool/{tool}/{action}` Endpoint
**File**: `src/langnet/asgi.py`
**Success Criteria**: Endpoint responds with raw tool data for valid tool/action combinations

**Checklist**:
- [ ] Add `tool_api()` function to handle tool requests
- [ ] Add route: `Route("/api/tool/{tool}/{action}", tool_api, methods=["GET"])`
- [ ] Implement parameter validation (lang, query, dict_id)
- [ ] Add error handling for invalid tool/action combinations
- [ ] Return raw tool output as JSON (no adapter conversion)

**Endpoint Examples**:
- `GET /api/tool/diogenes/search?lang=lat&query=lupus`
- `GET /api/tool/whitakers/analyze?query=lupus`
- `GET /api/tool/heritage/morphology?query=agni`
- `GET /api/tool/cdsl/lookup?dict=mw&query=agni`
- `GET /api/tool/cltk/morphology?lang=grc&query=logos`

### 1.2 Add Tool-Specific Methods to LanguageEngine
**File**: `src/langnet/engine/core.py`
**Success Criteria**: Each tool's raw output is accessible via public methods

**Checklist**:
- [ ] Add `get_tool_data(tool, action, lang=None, query=None, dict_name=None)` method
- [ ] Implement `_get_diogenes_raw(lang, query)` method
- [ ] Implement `_get_whitakers_raw(query)` method
- [ ] Implement `_get_heritage_raw(query, action)` method
- [ ] Implement `_get_cdsl_raw(query, dict_name)` method
- [ ] Implement `_get_cltk_raw(lang, query, action)` method
- [ ] Add proper error handling for missing parameters

### 1.3 Update ASGI Application
**File**: `src/langnet/asgi.py`
**Success Criteria**: All tool endpoints work and return appropriate HTTP status codes

**Checklist**:
- [ ] Add `tool_api()` function implementation
- [ ] Wire up `LanguageEngine.get_tool_data()` calls
- [ ] Add comprehensive error responses (404 for invalid tool, 400 for missing params)
- [ ] Ensure CORS headers if needed
- [ ] Add request logging for debugging

---

## PHASE 2: CLI Debug Commands (Est: 2 days)

### 2.1 Add `langnet-cli tool` Command Group
**File**: `src/langnet/cli.py`
**Success Criteria**: All tool commands work via CLI with proper output formatting

**Checklist**:
- [ ] Add `@click.group()` for `tool` command group
- [ ] Add `tool diogenes` subcommand with `--lang`, `--query`, `--action` options
- [ ] Add `tool whitakers` subcommand with `--query`, `--action` options
- [ ] Add `tool heritage` subcommand with `--query`, `--action`, `--dict` options
- [ ] Add `tool cdsl` subcommand with `--dict`, `--query`, `--action` options
- [ ] Add `tool cltk` subcommand with `--lang`, `--query`, `--action` options
- [ ] Add `--output` option (json, pretty, yaml)
- [ ] Add `--save` option to save output to fixture file

### 2.2 Add Generic Tool Query Command
**File**: `src/langnet/cli.py`
**Success Criteria**: Single command can query any tool with flexible parameters

**Checklist**:
- [ ] Add `tool query` command with all tool/action parameters
- [ ] Support `--tool`, `--action`, `--lang`, `--query`, `--dict` parameters
- [ ] Add validation for required parameters per tool
- [ ] Implement direct API call or use local engine
- [ ] Add pretty-printing for JSON output

### 2.3 Add Fuzz Testing Command
**File**: `src/langnet/cli.py`
**Success Criteria**: Can generate test fixtures from live queries

**Checklist**:
- [ ] Add `tool fuzz-test` command
- [ ] Accept word lists via `--wordfile` or `--words` comma-separated list
- [ ] Support `--tool` and `--action` filters
- [ ] Save outputs to `tests/fixtures/raw_tool_outputs/`
- [ ] Generate summary report of successes/failures
- [ ] Option to compare with cached fixtures

---

## PHASE 3: Fuzz Testing Infrastructure (Est: 3 days)

### 3.1 Create Fixture Directory Structure
**Location**: `tests/fixtures/raw_tool_outputs/`
**Success Criteria**: Organized fixture storage for all tools

**Checklist**:
- [ ] Create directory structure:
  ```
  tests/fixtures/raw_tool_outputs/
  ├── diogenes/
  │   ├── lat_lupus_search.json
  │   ├── grc_logos_search.json
  │   └── schema_diogenes.json
  ├── whitakers/
  │   ├── lupus_analyze.json
  │   └── schema_whitakers.json
  ├── heritage/
  │   ├── agni_morphology.json
  │   ├── agni_search.json
  │   └── schema_heritage.json
  ├── cdsl/
  │   ├── mw_agni_lookup.json
  │   ├── ap90_agni_lookup.json
  │   └── schema_cdsl.json
  └── cltk/
      ├── lat_lupus_morphology.json
      ├── grc_logos_morphology.json
      └── schema_cltk.json
  ```
- [ ] Add `.gitignore` patterns for large fixture files
- [ ] Create README explaining fixture format

### 3.2 Build Fuzz Testing Module
**File**: `tests/fuzz_tool_outputs.py`
**Success Criteria**: Automated fixture generation and validation

**Checklist**:
- [ ] Create `ToolFuzzer` class with methods:
  - `generate_fixtures(tool, action, word_list)`
  - `validate_fixtures(tool, action)` 
  - `compare_with_schema(tool, action)`
- [ ] Add test word lists per language:
  - Latin: `lupus`, `arma`, `vir`, `rosa`
  - Greek: `logos`, `anthropos`, `polis`
  - Sanskrit: `agni`, `yoga`, `karma`, `dharma`
- [ ] Add schema validation using `jsonschema`
- [ ] Generate HTML/JSON reports of fixture health

### 3.3 Create Schema Comparison Tools
**File**: `tools/compare_tool_outputs.py`
**Success Criteria**: Can detect schema changes and suggest adapter fixes

**Checklist**:
- [ ] Create `ToolOutputComparator` class
- [ ] Method: `compare_raw_to_unified(raw_data, unified_entry)` → diff report
- [ ] Method: `detect_schema_drift(old_fixture, new_fixture)` → change report
- [ ] Method: `generate_adapter_fixes(tool, schema_changes)` → code suggestions
- [ ] Add `--generate-report` option for HTML output
- [ ] Integrate with pytest for automated testing

---

## PHASE 4: Update Broken Tests (Est: 3 days)

### 4.1 Fix Test Infrastructure
**File**: `tests/testconf.py`
**Success Criteria**: Tests can use real fixture data instead of mocks

**Checklist**:
- [ ] Add `RAW_TEST_MODE` environment variable support
- [ ] Create `ToolFixtureMixin` base test class
- [ ] Add `@pytest.fixture` for loading tool fixtures
- [ ] Add `skip_if_no_fixture(tool, action, word)` decorator
- [ ] Update test configuration to use fixtures when available

### 4.2 Update Key Broken Tests
**Priority Order**:
1. **First**: `tests/test_heritage_integration.py` (most critical)
2. **Second**: `tests/test_cdsl.py` (Sanskrit dictionary)
3. **Third**: `tests/test_api_integration.py` (API endpoints)
4. **Fourth**: Other integration tests

**Checklist per test file**:
- [ ] Replace hardcoded mock data with fixture loading
- [ ] Add `test_raw_tool_output()` method that tests `/api/tool/` endpoint
- [ ] Add `test_unified_schema_conversion()` that compares raw vs unified
- [ ] Generate fixtures for all test cases using CLI tool commands
- [ ] Verify adapter conversion works with real data

### 4.3 Create Test Helper Functions
**File**: `tests/helpers/tool_fixtures.py`
**Success Criteria**: Easy fixture loading across all tests

**Checklist**:
- [ ] `load_tool_fixture(tool, action, lang, query)` → loads JSON fixture
- [ ] `assert_tool_schema(raw_output, expected_schema)` → validates structure
- [ ] `generate_fixture_from_live(tool, action, lang, query)` → captures live data
- [ ] `compare_adapter_output(raw_data, unified_data)` → diffs conversion
- [ ] `save_fixture(tool, action, lang, query, data)` → saves to fixture dir

---

## PHASE 5: Documentation & Developer Workflow (Est: 1 day)

### 5.1 Create Debugging Workflow Guide
**File**: `docs/DEBUGGING_TOOL_OUTPUTS.md`
**Success Criteria**: Clear workflow for using new debug tools

**Checklist**:
- [ ] Section: "Using Tool-Specific Endpoints"
- [ ] Section: "CLI Debug Commands Reference"
- [ ] Section: "Generating Test Fixtures"
- [ ] Section: "Fixing Adapter Conversion Issues"
- [ ] Section: "Schema Evolution Workflow"
- [ ] Examples for common debugging scenarios

### 5.2 Update Developer Documentation
**File**: `docs/DEVELOPER.md`
**Success Criteria**: Updated with new debugging capabilities

**Checklist**:
- [ ] Add "Debugging Backend Issues" section
- [ ] Add "Working with Tool Fixtures" section
- [ ] Add "Schema Evolution Guide" section
- [ ] Update "Testing Guide" with new fixture approach
- [ ] Add troubleshooting FAQ for common issues

---

## Success Criteria Checklist

### Phase 1 Completion:
- [ ] `/api/tool/{tool}/{action}` endpoints return valid JSON for all tools
- [ ] All required parameters validated (lang for diogenes/cltk, query for all)
- [ ] Error responses clear and helpful (400 for bad params, 404 for unknown tool)
- [ ] API documentation available at `/api/docs` (if adding OpenAPI)

### Phase 2 Completion:
- [ ] `langnet-cli tool diogenes search --lang lat --query lupus` works
- [ ] `langnet-cli tool whitakers analyze --query lupus` works
- [ ] `langnet-cli tool heritage morphology --query agni` works
- [ ] `langnet-cli tool cdsl lookup --dict mw --query agni` works
- [ ] `langnet-cli tool cltk morphology --lang grc --query logos` works
- [ ] `--save` option saves fixtures to correct location
- [ ] `--output json|pretty|yaml` formats correctly

### Phase 3 Completion:
- [ ] Fixture directory structure exists
- [ ] `tests/fuzz_tool_outputs.py` can generate fixtures for all tools
- [ ] `tools/compare_tool_outputs.py` produces useful diff reports
- [ ] Schema validation catches common adapter issues
- [ ] HTML reports generated for fixture comparisons

### Phase 4 Completion:
- [ ] `tests/test_heritage_integration.py` uses real fixtures
- [ ] `tests/test_cdsl.py` uses real fixtures
- [ ] `tests/test_api_integration.py` tests both raw and unified endpoints
- [ ] All existing tests pass with new fixture system
- [ ] Test helper functions available and documented

### Phase 5 Completion:
- [ ] `docs/DEBUGGING_TOOL_OUTPUTS.md` complete
- [ ] `docs/DEVELOPER.md` updated with new workflows
- [ ] Example commands documented for common debugging tasks
- [ ] Schema evolution workflow documented

---

## Implementation Details

### API Endpoint Structure
```python
# In src/langnet/asgi.py
@Route("/api/tool/{tool}/{action}", tool_api, methods=["GET"])
async def tool_api(request: Request, tool: str, action: str):
    lang = request.query_params.get("lang")
    query = request.query_params.get("query")
    dict_name = request.query_params.get("dict")
    
    # Tool-specific parameter validation
    if tool == "diogenes":
        if not lang or not query:
            return ORJsonResponse({"error": "Missing lang or query parameter"}, status_code=400)
    elif tool == "whitakers":
        if not query:
            return ORJsonResponse({"error": "Missing query parameter"}, status_code=400)
    # ... etc
    
    try:
        wiring = request.app.state.wiring
        raw_data = wiring.engine.get_tool_data(tool, action, lang, query, dict_name)
        return ORJsonResponse(raw_data)
    except ValueError as e:
        return ORJsonResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error(f"Tool API error: {e}")
        return ORJsonResponse({"error": "Internal server error"}, status_code=500)
```

### CLI Command Structure
```python
# In src/langnet/cli.py
@click.group()
def tool():
    """Debug individual backend tools."""
    pass

@tool.command()
@click.option("--lang", required=True, help="Language code (lat, grc, san)")
@click.option("--query", required=True, help="Word to query")
@click.option("--action", default="search", help="Action: search, parse")
@click.option("--output", default="json", help="Output format: json, pretty, yaml")
@click.option("--save", help="Save output to fixture file")
def diogenes(lang, query, action, output, save):
    """Query Diogenes backend directly."""
    # Implementation...
```

### LanguageEngine Extension
```python
# In src/langnet/engine/core.py
class LanguageEngine:
    # ... existing methods ...
    
    def get_tool_data(self, tool: str, action: str, lang: str = None, 
                     query: str = None, dict_name: str = None) -> dict:
        """Get raw tool data for debugging."""
        if tool == "diogenes":
            if action == "search":
                result = self.diogenes.parse_word(query, lang)
                return self._cattrs_converter.unstructure(result)
        elif tool == "whitakers":
            if action == "analyze":
                result = self.whitakers.words([query])
                return self._cattrs_converter.unstructure(result)
        # ... etc
```

---

## Risk Assessment & Mitigation

### High Risk Areas:
1. **Tool parameter validation**: Different tools require different parameters
   - **Mitigation**: Clear error messages, comprehensive validation
2. **Backend availability**: Tools may not be installed/configured
   - **Mitigation**: Graceful degradation, helpful error messages
3. **Large response sizes**: Some tools return large data structures
   - **Mitigation**: Response streaming, pagination options

### Medium Risk Areas:
1. **Schema changes breaking adapters**: Raw outputs may change
   - **Mitigation**: Versioned fixtures, schema validation
2. **Performance impact**: Extra endpoints may affect performance
   - **Mitigation**: Caching, rate limiting if needed

### Low Risk Areas:
1. **CLI command complexity**: Many options and parameters
   - **Mitigation**: Clear help text, examples, validation

---

## Timeline & Dependencies

**Total**: 9-12 days
- **Week 1**: Phases 1-2 (API + CLI) - 5 days
- **Week 2**: Phases 3-4 (Fuzz testing + Test updates) - 4 days
- **Week 3**: Phase 5 (Documentation) - 1 day

**Dependencies**:
1. Existing backend adapters must work (✅ COMPLETE)
2. LanguageEngine must be initialized (✅ COMPLETE)
3. Tests must be runnable (✅ COMPLETE)

---

## Handoff Notes for Junior Developers

### Key Files to Modify:
1. `src/langnet/asgi.py` - Add tool API endpoint
2. `src/langnet/engine/core.py` - Add tool data methods
3. `src/langnet/cli.py` - Add tool CLI commands
4. `tests/fuzz_tool_outputs.py` - New fuzz testing module
5. `tools/compare_tool_outputs.py` - New comparison tool

### Testing Strategy:
1. **Start with Diogenes**: Simplest tool, good for prototype
2. **Test via CLI**: Use `langnet-cli tool diogenes search --lang lat --query lupus`
3. **Verify API**: Use curl `curl "http://localhost:8000/api/tool/diogenes/search?lang=lat&query=lupus"`
4. **Generate fixtures**: Save outputs for regression testing
5. **Update tests**: Replace mocks with real fixtures

### Common Pitfalls:
1. **Missing parameters**: Each tool has different requirements
2. **Error handling**: Backends may be unavailable
3. **Response formatting**: Keep raw structure, don't adapt
4. **Fixture management**: Don't commit large binary files

### Getting Help:
- Check existing adapter code in `src/langnet/backend_adapter.py`
- Look at `tests/test_*.py` for examples of tool usage
- Use `langnet-cli query` to see current unified output
- Examine `LanguageEngine._query_*` methods for raw data flow