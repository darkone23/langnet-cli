# Testing Workflow

Run tests for langnet-cli project.

## Usage

Run all tests:
```bash
just test-all
```

Run single test with full dotted path:
```bash
just test tests.test_api_integration.TestGreekSpacyIntegration.test_greek_query_includes_spacy_response
```

Run tests with verbose logging:
```bash
LANGNET_LOG_LEVEL=INFO nose2 -s tests --config tests/nose2.cfg
LANGNET_LOG_LEVEL=DEBUG nose2 -s tests --config tests/nose2.cfg
```

## Key Test Files

- `tests/test_api_integration.py` - Integration tests for Greek/Latin queries
- `tests/test_cache.py` - Cache functionality tests
- `tests/test_diogenes_scraper.py` - Diogenes backend tests
- `tests/test_whitakers_words.py` - Whitaker's Words parser tests
- `tests/test_cdsl.py` - CDSL Sanskrit dictionary tests
- `tests/test_classics_toolkit.py` - CLTK integration tests

## Important Notes

- Tests require `devenv shell` environment active
- Diogenes server must be running on localhost:8888 for backend tests
- CDSL db must be available for many tests
- CLTK models (~500MB) download on first test run
- Tests disable urllib3 connection logging to reduce noise
