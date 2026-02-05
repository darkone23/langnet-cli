# Tests

This directory contains the comprehensive test suite for the langnet-cli project, organized by component and functionality.

## Test Categories

### Core Infrastructure Tests
| File | Purpose | Coverage |
|------|---------|----------|
| `test_api_integration.py` | API integration tests | Greek Spacy integration, backend responses |
| `test_canonical_lookup_importance.py` | Canonical query importance | Query normalization, lookup validation |
| `test_cts_urn_basic.py` | CTS URN parsing and indexing | Citation system, URN parsing, index building |
| `test_fuzz_backend_adapters.py` | Backend adapter fuzz testing | Adapter validation with real fixtures |
| `test_fuzz_universal_schema.py` | Universal schema fuzz testing | Schema compliance, cross-backend consistency |
| `test_universal_schema_integration.py` | Universal schema integration | Schema validation, adapter integration |

### Language Backend Tests
| File | Purpose | Coverage |
|------|---------|----------|
| `test_cdsl.py` | CDSL backend integration | Sanskrit dictionary lookup, encoding support |
| `test_classics_toolkit.py` | Classics Toolkit integration | Latin query handling, property access |
| `test_cltk_playground.py` | CLTK functionality | Lemmatizer, lexicon, transcriber, replacer |
| `test_diogenes_scraper.py` | Diogenes web scraper | Chunk classification, Latin/Greek parsing |
| `test_whitakers_words.py` | Whitaker's Words parser | Senses, codes, facts extraction |
| `test_whitakers_codes_parser.py` | Whitaker's codes parser | Morphological code parsing |
| `test_whitakers_facts_parser.py` | Whitaker's facts parser | Word fact parsing |
| `test_whitakers_senses_parser.py` | Whitaker's senses parser | Dictionary sense parsing |

### Sanskrit Integration Tests
| File | Purpose | Coverage |
|------|---------|----------|
| `test_heritage_cdsl_integration.py` | Heritage-CDSL integration | Sanskrit platform connectivity |
| `test_heritage_connectivity.py` | Heritage platform connectivity | Network connectivity, service health |
| `test_heritage_encoding_bridge.py` | Heritage encoding bridge | Devanagari, IAST, Velthuis, SLP1 conversion |
| `test_heritage_engine_integration.py` | Heritage engine integration | Query routing, result aggregation |
| `test_heritage_integration.py` | Heritage integration | Basic platform functionality |
| `test_heritage_integration_unittest.py` | Heritage unit tests | Detailed platform testing |
| `test_heritage_morphology_parsing.py` | Heritage morphology parsing | Morphological analysis parsing |
| `test_heritage_morphology.py` | Heritage morphology | Full morphological analysis |
| `test_heritage_platform_integration.py` | Heritage platform integration | Complete platform workflow |
| `test_heritage_pos_parsing.py` | Heritage POS parsing | Part-of-speech analysis |
| `test_heritage_real_integration.py` | Heritage real integration | Production environment testing |
| `test_real_heritage_fixtures.py` | Real heritage fixtures | Fixture validation and management |
| `test_sanskrit_encoding_improvements.py` | Sanskrit encoding improvements | Encoding system enhancements |
| `test_sanskrit_features.py` | Sanskrit features | Language-specific functionality |
| `test_sanskrit_normalization.py` | Sanskrit normalization | Input normalization |
| `test_sanskrit_normalization_unittest.py` | Sanskrit normalization unit tests | Detailed normalization testing |

### Foster Functional Grammar Tests
| File | Purpose | Coverage |
|------|---------|----------|
| `test_foster_apply.py` | Foster grammar application | Grammar function application |
| `test_foster_enums.py` | Foster enums validation | Enum definitions and mapping |
| `test_foster_grammar_integration.py` | Foster grammar integration | Complete grammar integration |
| `test_foster_lexicon.py` | Foster lexicon | Grammar lexicon validation |
| `test_foster_mappings.py` | Foster mappings | Grammar mapping validation |
| `test_foster_rendering.py` | Foster rendering | Grammar display formatting |

### Normalization Tests
| File | Purpose | Coverage |
|------|---------|----------|
| `test_morphology_parsers.py` | Morphology parsers | Parser functionality |
| `test_normalization.py` | Normalization system | Query normalization pipeline |
| `test_normalization_standalone.py` | Standalone normalization | Independent normalization testing |

## Test Fixtures

The `fixtures/` directory contains test data used for validation:

### Raw Tool Outputs (`fixtures/raw_tool_outputs/`)
| Directory | Purpose |
|-----------|---------|
| `cdsl/` | CDSL backend raw outputs |
| `cltk/` | CLTK backend raw outputs |
| `diogenes/` | Diogenes backend raw outputs |
| `heritage/` | Heritage Platform raw outputs |
| `whitakers/` | Whitaker's Words raw outputs |

### Heritage Fixtures (`fixtures/heritage/`)
| Directory | Purpose |
|-----------|---------|
| `morphology/` | Heritage morphology test data |
| `search/` | Heritage search test data |

### Whitaker's Fixtures (`fixtures/whitakers/`)
| Directory | Purpose |
|-----------|---------|
| `senses/` | Dictionary sense test data |
| `term_codes/` | Morphological code test data |
| `term_facts/` | Word fact test data |

## Running Tests

```bash
# Run all tests
just test

# Run specific test category
nose2 -s tests test_foster_grammar_integration
nose2 -s tests test_heritage_integration
nose2 -s tests test_normalization

# Run with verbose output
nose2 -s tests --config tests/nose2.cfg -v

# Run with debug logging
LANGNET_LOG_LEVEL=DEBUG nose2 -s tests --config tests/nose2.cfg

# Run fuzz testing
python -m tests.fuzz_tool_outputs --validate --compare
```

## Test Configuration

- **Test Runner**: `nose2` with configuration in `nose2.cfg`
- **Test Discovery**: Pattern `test_*.py` in `tests/` directory
- **Fixture Location**: `tests/fixtures/` for test data
- **Helpers**: `tests/helpers/` for shared test utilities

## Test Coverage Goals

1. **Unit Tests**: Individual component testing (80%+ coverage)
2. **Integration Tests**: Backend service integration
3. **Fuzz Tests**: Adapter validation with real data
4. **Schema Tests**: Universal schema compliance
5. **Performance Tests**: Query response times and caching

## Test Development

When adding new tests:
1. Follow existing patterns in similar test files
2. Use appropriate fixtures from `tests/fixtures/`
3. Include comprehensive docstrings explaining test purpose
4. Use `unittest.TestCase` as base class
5. Add to appropriate category in this README

## Test Data Management

- Raw backend outputs stored as JSON fixtures
- Fixtures validated against schemas
- Real-world examples preferred over synthetic data
- Fixtures updated when backends change
