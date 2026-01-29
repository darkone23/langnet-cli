## Detailed Prompt for Continuing Heritage Platform Backend Development

### **Current Work Summary**
We are implementing a Heritage Platform backend for the langnet-cli project, which integrates with Sanskrit Heritage Platform CGI functions running at `localhost:48080`. The implementation is currently in **Phase 2: Morphological Analysis Service** and has been progressing well.

### **What We've Accomplished**
1. **Phase 1: Foundation & Core API - COMPLETED** ✅
   - Created HTTP client for localhost:48080 CGI calls (`src/langnet/heritage/client.py`)
   - Implemented request parameter builder with text encoding support (`src/langnet/heritage/parameters.py`)
   - Created base HTML parser for common response patterns (`src/langnet/heritage/parsers.py`)
   - Added configuration management (`src/langnet/heritage/config.py`)
   - Set up data models using dataclasses (`src/langnet/heritage/models.py`)
   - All infrastructure tests pass successfully

2. **Phase 2: Morphological Analysis Service - IN PROGRESS** 🔄
   - Implemented `HeritageMorphologyService` class (`src/langnet/heritage/morphology.py`)
   - Created `MorphologyParser` for HTML response parsing
   - Fixed import issues and context manager problems
   - **Key Discovery**: Found that CGI scripts require proper encoding parameters (`t=VH` for Velthuis)
   - **Current Issue**: Parameter building needs to use `indic_transliteration` library for proper text encoding

### **Current Technical Implementation**
- **Architecture**: Synchronous HTTP requests with rate limiting
- **Configuration**: Flexible config with environment variable support
- **Data Models**: Structured classes like `HeritageMorphologyResult`, `HeritageSolution`, `HeritageWordAnalysis`
- **Key Files Being Modified**:
  - `src/langnet/heritage/parameters.py` (critical - needs encoding fix)
  - `src/langnet/heritage/morphology.py` (working, needs parameter integration)
  - `src/langnet/heritage/parsers.py` (has type errors but functional)

### **Key Technical Decisions Made**
- Use synchronous requests instead of async for simplicity
- Implement rate limiting to avoid overwhelming CGI server
- Support multiple text encodings (velthuis, itrans, slp1) using `indic_transliteration` library
- Use BeautifulSoup for HTML parsing
- Structured data models using dataclasses
- Context managers for resource cleanup

### **Current Issue and Next Steps**
**Problem**: The parameter builder needs to properly encode text using the `indic_transliteration` library and pass the correct CGI encoding parameters (like `t=VH` for Velthuis format).

**Specific Issues**:
1. Import errors in `parameters.py` when trying to use `indic_transliteration` library
2. Need to encode text before passing to CGI scripts, not just pass encoding parameter
3. Type checking errors in the parser files (non-blocking functionality)

**Immediate Next Steps**:
1. **Fix parameter encoding**: Complete the integration of `indic_transliteration` library in `src/langnet/heritage/parameters.py`
2. **Test with correct format**: Use the example `/cgi-bin/skt/sktindex?lex=MW&q=yoga&t=VH` format from the documentation
3. **Update all parameter builders**: Ensure `build_morphology_params`, `build_search_params`, etc. use proper encoding
4. **Test connectivity**: Verify the corrected encoding works with actual CGI endpoints
5. **Complete morphology service**: Ensure the parsed data extraction works correctly

### **Progress Status**
- **Phase 1**: 100% Complete ✅
- **Phase 2**: 75% Complete 🔄 (encoding fix needed)
- **Phase 3**: 0% Complete ⏳ (dictionary services)
- **Phase 4**: 0% Complete ⏳ (grammar services)

### **Environment Setup**
- Heritage Platform running at `localhost:48080`
- CGI scripts available at `/cgi-bin/skt/`
- Dependencies needed: `requests`, `beautifulsoup4`, `structlog`, `indic_transliteration`
- Foster Sanskrit grammar system integrated for case mappings

### **Integration Requirements**
- Wire parsed output to `LatinQueryResult` (from TODO.md requirements)
- Add comprehensive test coverage for morphology service
- Integration with langnet engine core will require modifications to `engine/core.py`

### **Testing Infrastructure**
- `test_heritage_infrastructure.py` ✅ (all tests pass)
- `test_heritage_connectivity.py` ✅ (connectivity works)
- Debugging scripts show CGI server responds but needs correct encoding

**Focus for Next Session**: Complete the encoding integration in `parameters.py` and test with proper Velthuis-encoded text using `t=VH` parameter format.