# Root Directory Cleanup Plan

## Files to Organize

### Debug Files → Convert to Tests
These debug files contain valuable implementation insights and should be converted to proper tests:

**CDSL Debug Files:**
- `debug_cdsl_dict.py` → `tests/test_cdsl_debug.py` (CDSL dictionary debugging)
- `debug_cdsl_index.py` → `tests/test_cdsl_index_debug.py` (CDSL index debugging)
- `debug_cdsl_keys.py` → `tests/test_cdsl_keys_debug.py` (CDSL key debugging)

**Heritage Debug Files:**
- `debug_heritage.py` → `tests/test_heritage_debug.py` (Heritage platform debugging)
- `debug_heritage_connectivity.py` → `tests/test_heritage_connectivity.py` (already exists, verify)
- `debug_heritage_parsing.py` → `tests/test_heritage_parsing_debug.py` (Heritage parsing debugging)

**POS Parsing Debug Files:**
- `debug_pos_parsing.py` → `tests/test_pos_parsing_debug.py` (POS parsing debugging)
- `debug_pos_parsing_fixed.py` → `tests/test_pos_parsing_fixed.py` (fixed POS parsing)

**General Debug Files:**
- `debug_dict_search.py` → `tests/test_dict_search_debug.py` (dictionary search debugging)
- `debug_dict_search2.py` → `tests/test_dict_search2_debug.py` (dictionary search debugging 2)
- `debug_encoding_demo.py` → `tests/test_encoding_demo.py` (encoding demonstration)
- `debug_full_html.py` → `tests/test_html_parsing_debug.py` (HTML parsing debugging)

### Test Files → Move to Tests Directory
These are already test files but in the wrong location:

**Heritage Test Files:**
- `test_heritage_connectivity.py` → `tests/test_heritage_connectivity.py` (verify if duplicate)
- `test_heritage_dict_integration.py` → `tests/test_heritage_dict_integration.py`
- `test_heritage_direct.py` → `tests/test_heritage_direct.py`
- `test_heritage_direct2.py` → `tests/test_heritage_direct2.py`
- `test_heritage_direct3.py` → `tests/test_heritage_direct3.py`
- `test_heritage_direct4.py` → `tests/test_heritage_direct4.py`
- `test_heritage_encoding_bridge.py` → `tests/test_heritage_encoding_bridge.py`
- `test_heritage_encodings.py` → `tests/test_heritage_encodings.py`
- `test_heritage_infrastructure.py` → `tests/test_heritage_infrastructure.py`
- `test_heritage_integration.py` → `tests/test_heritage_integration.py` (duplicate?)
- `test_heritage_words.py` → `tests/test_heritage_words.py`
- `test_simple_morphology.py` → `tests/test_simple_morphology.py`

### Utility Files → Move to src/utils/
These are utility scripts that should be organized:

- `simple_heritage_parser.py` → `src/langnet/heritage/simple_parser.py` or `src/utils/simple_heritage_parser.py`

## Implementation Steps

1. **Backup current root directory** (git status first)
2. **Create organized test files** from debug files
3. **Move existing test files** to tests/ directory
4. **Update IN-PROGRESS.md** with cleanup status
5. **Verify all tests run** via `just test`
6. **Clean up root directory**

## Key Insights from Debug Files

Based on the debug files examination:

### Heritage Platform Integration
- Successfully tested CGI connectivity with `localhost:48080`
- Velthuis encoding (`t=VH`) properly implemented
- HTML parsing working for morphology analysis
- Dictionary search functional

### POS Parsing
- Heritage format: `headword [ POS ] definition`
- POS extraction working: `agni [ N. ]` → extract "N."
- SLP1 conversion functional for CDSL lookup
- Encoding bridge between Heritage and CDSL complete

### Foster Grammar
- Already implemented and integrated in `engine/core.py`
- Foster mappings complete for all languages
- Applied via `apply_foster_view()` function

### CDSL Integration
- Dictionary lookup functional
- Key normalization working
- Entry parsing successful

## Files to Keep in Root
- Configuration files: `.envrc`, `pyproject.toml`, `justfile`, etc.
- Documentation: `README.md`, `DEVELOPER.md`, etc.
- Build files: `poetry.lock`, `devenv.yaml`, etc.

## Success Metrics
- All debug functionality preserved as proper tests
- No debug files left in root directory
- All tests run successfully via `just test`
- IN-PROGRESS.md updated with cleanup status
- Project structure clean and organized