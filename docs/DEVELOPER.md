# Developer Guide

## Project Mission

langnet-cli is a classical language education tool designed to help students and scholars study Latin, Greek, and Sanskrit through comprehensive linguistic analysis. The tool provides instant access to dictionary definitions, morphological parsing, and grammatical information to supplement language learning and text comprehension.

**Primary Users**: Classical language students, researchers, and enthusiasts
**Primary Use Case**: Quick reference while reading classical texts
**Key Features**: Multi-source lexicon lookup, morphological analysis, vocabulary building

## Development Environment

```sh
# Enter development shell (loads Python venv, sets env vars)
devenv shell langnet-cli

# One-off commands with the environment activated
devenv shell langnet-cli -- langnet-cli verify
devenv shell langnet-cli -- langnet-cli query lat lupus --output json

# Start API server with auto-reload (requires external services running)
devenv shell langnet-cli -- uvicorn-run --reload

# Start zombie process reaper (runs continuously)
devenv shell langnet-cli -- just langnet-dg-reaper
```

Long-running API/server processes cache imported modules; restart `uvicorn-run` after code changes before re-validating.

## Testing

Most tests expect Heritage, Diogenes, and Whitaker's Words to be reachable locally.

```sh
# Run all tests (preferred)
devenv shell langnet-cli -- just test

# Run single test (full dotted path required)
devenv shell langnet-cli -- nose2 -s tests <TestClass>.<test_method> --config tests/nose2.cfg

# Run tests with verbose logging
devenv shell langnet-cli -- LANGNET_LOG_LEVEL=INFO nose2 -s tests --config tests/nose2.cfg
devenv shell langnet-cli -- LANGNET_LOG_LEVEL=DEBUG nose2 -s tests --config tests/nose2.cfg
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PYTHONPATH` | Python module search path | `src:$PYTHONPATH` |
| `LANGNET_LOG_LEVEL` | Logging level (DEBUG/INFO/WARNING/ERROR) | `WARNING` |
| `LANGNET_CACHE_ENABLED` | Enable response caching | `true` |
| `LANGNET_CACHE_PATH` | Custom cache database path | auto |
| `RAW_TEST_MODE` | Enable raw backend testing | `false` |
| `LANGNET_API_URL` | Custom API server URL | `http://localhost:8000` |

## Debugging Infrastructure

The project now includes comprehensive debugging tools for backend integration and schema evolution:

### Tool-Specific Debug Endpoints

Access individual backend tools directly via API endpoints:

```bash
# Diogenes (Latin/Greek)
curl "http://localhost:8000/api/tool/diogenes/search?lang=lat&query=lupus"
curl "http://localhost:8000/api/tool/diogenes/parse?lang=grc&query=logos"

# Whitaker's Words (Latin)
curl "http://localhost:8000/api/tool/whitakers/analyze?query=lupus"

# Heritage Platform (Sanskrit)
curl "http://localhost:8000/api/tool/heritage/morphology?query=agni"
curl "http://localhost:8000/api/tool/heritage/dictionary?query=yoga&dict=mw"

# CDSL (Sanskrit)
curl "http://localhost:8000/api/tool/cdsl/lookup?dict=mw&query=agni"

# CLTK (Multi-language)
curl "http://localhost:8000/api/tool/cltk/morphology?lang=lat&query=lupus"
```

### CLI Debug Commands

Use `langnet-cli tool` for command-line debugging:

```bash
# Tool-specific commands
devenv shell langnet-cli -- langnet-cli tool diogenes search --lang lat --query lupus --save
devenv shell langnet-cli -- langnet-cli tool heritage morphology --query agni --output pretty
devenv shell langnet-cli -- langnet-cli tool cdsl lookup --dict mw --query yoga --save

# Generic query interface
devenv shell langnet-cli -- langnet-cli tool query --tool whitakers --action analyze --query lupus

# Output formats: json (default), pretty, yaml
devenv shell langnet-cli -- langnet-cli tool diogenes search --lang lat --query lupus --output pretty
```

### Fuzz Testing and Validation

Automated testing for backend tools:

```bash
# Generate fixtures for multiple words
devenv shell langnet-cli -- just autobot fuzz run --tool diogenes --action search --words "lupus,arma,vir" --validate

# Validate existing fixtures
devenv shell langnet-cli -- just autobot fuzz run --tool heritage --action morphology --validate

# Compare raw vs unified outputs
devenv shell langnet-cli -- just autobot fuzz run --tool cdsl --action lookup --compare
```

### Fixtures Management

Raw backend outputs can be generated on-demand:

```
devenv shell langnet-cli -- just autobot fuzz run \
  --tool diogenes \
  --action search \
  --words "lupus,amo" \
  --save                # defaults to examples/debug/fuzz_results.json

devenv shell langnet-cli -- just autobot fuzz list
devenv shell langnet-cli -- just autobot fuzz run --tool diogenes --action search --validate --compare
```

Save individual outputs manually when needed:

```bash
curl "http://localhost:8000/api/tool/diogenes/search?lang=lat&query=lupus" \
  | jq . > examples/debug/fuzz_outputs/diogenes_search_lat_lupus.json
```

### Schema Evolution

Monitor and manage schema changes:

```bash
# Compare raw vs unified outputs
devenv shell langnet-cli -- python examples/compare_tool_outputs.py \
  --tool diogenes \
  --action search \
  --word lupus \
  --generate-fixes

# Detect schema drift
devenv shell langnet-cli -- python examples/compare_tool_outputs.py \
  --tool heritage \
  --action morphology \
  --generate-fixes

# Save comparison results
devenv shell langnet-cli -- python examples/compare_tool_outputs.py \
  --tool cdsl \
  --action lookup \
  --word agni \
  --output comparison_results.json
```

### Test Integration

Use the `ToolFixtureMixin` in tests:

```python
from tests.helpers.tool_fixtures import ToolFixtureMixin

class TestMyFeature(ToolFixtureMixin):
    def test_raw_data_access(self):
        # Skip if no fixture available
        self.skip_if_no_fixture("diogenes", "search", "lat", "lupus")
        
        # Load fixture
        data = self.load_tool_fixture("diogenes", "search", "lat", "lupus")
        
        # Validate schema
        self.assert_tool_schema(data)
        
        # Compare with adapter output
        comparison = self.compare_adapter_output(raw_data, unified_data)
        
        # Generate live fixture
        live_data = self.generate_fixture_from_live(
            "heritage", "morphology", "san", "agni"
        )
```

## CTS URN Index (Perseus + legacy gaps)

- Primary source: Perseus corpora at `~/perseus` (`canonical-latinLit`, `canonical-greekLit`).
- Optional gap-fill: legacy Classics-Data (`~/langnet-tools/diogenes/Classics-Data`) for works not present in Perseus (e.g., some stoa URNs).
- Build (default merges Perseus + legacy gaps, wipes old DB):
  ```sh
  devenv shell langnet-cli -- just cli indexer build-cts --perseus-dir ~/perseus --wipe
  ```
- Pure-Perseus build (no legacy supplements):
  ```sh
  devenv shell langnet-cli -- just cli indexer build-cts --perseus-dir ~/perseus --wipe --no-legacy
  ```
- Output: `~/.local/share/langnet/cts_urn.duckdb`. CTS regression tests:
  ```sh
  devenv shell langnet-cli -- just test tests.test_cts_urn_basic
  ```

## Testing Strategy

### 1. Unit Testing

Test individual components in isolation:

```bash
# Test specific modules
devenv shell langnet-cli -- just test tests.test_heritage_integration
devenv shell langnet-cli -- just test tests.test_cdsl
devenv shell langnet-cli -- just test tests.test_api_integration

# Run with raw test mode
devenv shell langnet-cli -- RAW_TEST_MODE=true nose2 -s tests tests.test_heritage_integration --config tests/nose2.cfg -v
```

### 2. Integration Testing

Test tool-specific endpoints and CLI commands:

```bash
# Test API endpoints
curl "http://localhost:8000/api/tool/diogenes/search?lang=lat&query=lupus"
curl "http://localhost:8000/api/tool/heritage/morphology?query=agni"

# Test CLI commands
devenv shell langnet-cli -- langnet-cli tool diogenes search --lang lat --query lupus
devenv shell langnet-cli -- langnet-cli tool heritage morphology --query agni
```

### 3. Fuzz Testing

Comprehensive automated testing:

```bash
# Test all tools with default word lists (langnet-cli will hit the running API)
devenv shell langnet-cli -- just autobot fuzz run --validate --compare

# Test specific scenarios
devenv shell langnet-cli -- just autobot fuzz run \
  --tool diogenes \
  --action search \
  --words "lupus,arma,vir,rosa,amicus" \
  --validate

# Exhaustive defaults across all backends (hits localhost:8000, saves per-target files)
devenv shell langnet-cli -- just autobot fuzz run --validate --compare --save examples/debug/fuzz_results
```

### 4. Schema Validation

Ensure fixtures and outputs match expected schemas:

```bash
# Validate individual fixtures
python -c "
import json, jsonschema
with open('tests/fixtures/raw_tool_outputs/diogenes/schema_diogenes.json') as f:
    schema = json.load(f)
with open('tests/fixtures/raw_tool_outputs/diogenes/search_lat_lupus.json') as f:
    data = json.load(f)
jsonschema.validate(data, schema)
print('✓ Schema validation passed')
"

# Batch validation
just autobot fuzz run --validate
```

## Development Workflow

### 1. Adding New Backend Tools

1. **Implement backend integration** in `src/langnet/backend_adapter.py`
2. **Add tool methods** to `LanguageEngine` in `src/langnet/engine/core.py`
3. **Create API endpoint** in `src/langnet/asgi.py`
4. **Add CLI commands** in `src/langnet/cli.py`
5. **Create schema file** in `tests/fixtures/raw_tool_outputs/{tool}/schema_{tool}.json`
6. **Generate fixtures** using CLI commands
7. **Write tests** using `ToolFixtureMixin`

### 2. Debugging Adapter Issues

1. **Access raw data** via API endpoints or CLI
2. **Compare with unified output** using comparison tool
3. **Identify missing fields** or conversion errors
4. **Update adapter logic** in backend adapter
5. **Regenerate fixtures** and revalidate

### 3. Schema Evolution

1. **Monitor schema drift** with comparison tools
2. **Update schemas** when backends change
3. **Generate adapter fixes** for breaking changes
4. **Update tests** to use new schema
5. **Validate compatibility** with existing consumers

## Performance Considerations

- **Tool endpoints** may be slower than unified API due to direct backend calls
- **Large fixtures** should not be committed to version control
- **Schema validation** adds overhead during testing
- **Cache responses** when testing the same queries repeatedly

## Troubleshooting

### Common Issues

1. **Backend not responding**: Check `/api/health` endpoint
2. **Wrong parameters**: Use CLI help to validate required parameters
3. **Schema validation failures**: Update schema definitions
4. **Adapter conversion issues**: Use comparison tool to identify problems

### Debug Commands

```bash
# Check backend health
curl http://localhost:8000/api/health

# Test individual tools
devenv shell langnet-cli -- langnet-cli tool diogenes parse --lang lat --query lupus --output pretty

# Validate all fixtures
devenv shell langnet-cli -- just autobot fuzz run --validate

# Compare outputs
devenv shell langnet-cli -- python examples/compare_tool_outputs.py --tool diogenes --action search --word lupus
```

### Tool Matrix (backend → actions → defaults)

| Tool | Actions | Langs | Default samples | Notes |
|------|---------|-------|-----------------|-------|
| diogenes | parse | lat, grc | lat: lupus/arma/vir/amo/sum/video; grc: logos/anthropos/agathos/lego | Lexicon + morphology |
| whitakers | search | lat | amo/bellum/lupus | Whitaker's Words parser |
| heritage | morphology, canonical, lemmatize | san | morph: agni/yoga; canonical: agnii/agnim/agnina/agni/veda; lemma: agnim/yogena/agnina | Sanskrit Heritage stack |
| cdsl | lookup | san | agni/yoga/deva | Monier-Williams/AP90 via CDSL |
| cltk | morphology, dictionary | lat, grc, san (dictionary: lat) | morph: amo/sum/logos/anthropos/agni; dict: lupus/arma/amo | CLTK wrappers |

Use `devenv shell langnet-cli -- just autobot fuzz list` to see this matrix in the CLI and `devenv shell langnet-cli -- just autobot fuzz run` to exercise it. All fuzzing shells out to `langnet-cli tool ...` against `http://localhost:8000`.

Fuzz saves now default to a directory (`examples/debug/fuzz_results/`) with one JSON per target plus `summary.json`, which avoids extremely large aggregate files.

## Code Conventions

### Naming

- Functions: `snake_case` (e.g., `handle_query`)
- Classes: `PascalCase` (e.g., `LanguageEngine`)
- Constants: `UPPER_SNAKE_CASE`

### Type Hints

- Required for all function signatures
- Use `|` for unions: `str | None` not `Optional[str]`
- Generics: `list[str]`, `dict[str, int]`

### Import Order

1. Standard library
2. Third-party packages
3. Local modules (relative before absolute)

### Module Organization

- Prefer `@staticmethod` methods on classes
- Classes prevent namespace pollution and import-time side effects
- Example: `HealthChecker.diogenes()` over `check_diogenes()`

### Error Handling

- `ValueError(msg)` - invalid input
- `NotImplementedError(msg)` - missing features
- `AssertionError(msg)` - invariant violations
- `print()` - expected failures (e.g., missing binary)

### Comments

- Never comment obvious code
- Always comment non-obvious logic (algorithm choices, workarounds)
- Format: lowercase, no trailing period

## Project Structure

```
src/langnet/
├── asgi.py                  # Starlette ASGI application
├── cache/
│   └── core.py              # QueryCache (DuckDB) and NoOpCache
├── cli.py                   # Click-based CLI
├── core.py                  # Dependency injection container
├── engine/
│   └── core.py              # Query routing and aggregation
├── diogenes/
│   ├── core.py              # HTTP client + HTML parsing
│   ├── cli_util.py          # Zombie process reaper
│   └── README.md            # Diogenes integration docs
├── whitakers_words/
│   ├── core.py              # CLI wrapper + line parsing
│   ├── lineparsers/         # Modular line parsers
│   └── README.md            # Whitaker's integration docs
├── classics_toolkit/
│   └── core.py              # CLTK wrapper
├── cologne/
│   └── core.py              # CDSL wrapper
├── heritage/
│   ├── core.py              # Sanskrit Heritage Platform integration
│   ├── lineparsers/         # Lark-based parsers
│   └── README.md            # Heritage integration docs
├── normalization/
│   ├── core.py              # Canonical query normalization
│   ├── sanskrit.py          # Sanskrit-specific normalization
│   ├── latin.py              # Latin-specific normalization
│   └── greek.py              # Greek-specific normalization
├── foster/
│   ├── core.py              # Foster functional grammar implementation
│   ├── latin.py              # Latin Foster functions
│   ├── greek.py              # Greek Foster functions
│   └── sanskrit.py          # Sanskrit Foster functions
└── logging.py               # structlog configuration
```

## Adding a New Data Provider

When adding support for new dictionaries, morphological analyzers, or lexicon sources:

1. Create module in `src/langnet/<provider>/`
2. Implement core class with query method
3. Create dataclass models for structured output (use `@dataclass` + cattrs)
4. Wire into `LanguageEngine.handle_query()` in `engine/core.py`
5. Add health check in `HealthChecker` (asgi.py)
6. Add tests in `tests/test_<provider>.py`
7. Document in module README

**Considerations for Educational Use**:
- Keep responses focused and clear for learners
- Include relevant grammatical information (case, number, gender, etc.)
- Provide definitions from authoritative sources
- Handle encoding variations (UTF-8, Betacode, SLP1, Devanagari)

## Code Style Tools

- **Formatter**: `ruff format`
- **Type checker**: `ty check`
- **Linter**: `ruff check`

See [ROADMAP.md](../ROADMAP.md) for detailed roadmap and current priorities.

## AI-Assisted Development

This project uses a sophisticated multi-model AI development system. For complete AI development documentation, see:
- [AGENTS.md](../AGENTS.md) - AI persona instructions and workflows
- [technical/opencode/MULTI_MODEL_GUIDE.md](technical/opencode/MULTI_MODEL_GUIDE.md) - AI-assisted development workflow
- [technical/opencode/LLM_PROVIDER_GUIDE.md](technical/opencode/LLM_PROVIDER_GUIDE.md) - Model selection strategies

## Using Opencode

### Prerequisites

Before using opencode for development, configure your opencode client:

1. **Consider your LLM provider guide:**
   - Model selection strategies for different tasks
   - Cost optimization techniques
   - Free-tier options for experimentation
   - See [technical/opencode/LLM_PROVIDER_GUIDE.md](technical/opencode/LLM_PROVIDER_GUIDE.md)

2. **Choose and configure a provider:**
   ```bash
   # inside of opencode run:
   /connect 
   ```

3. **Configure model routing:**
   - Use cheaper models for code generation
   - Use larger models for complex planning/debugging
   - Enable prompt caching to reduce costs

### Quick Start for Contributors

Once your provider is configured, leverage opencode for development tasks by referencing the available skills:

```bash
# Ask opencode to run tests
/opencode Using the testing.md skill, run the test suite and report any failures.

# Add a new backend
/opencode Following the backend-integration.md skill, create a new backend for [language].

# Debug an issue
/opencode Using the debugging.md skill, help troubleshoot why [backend] is not responding.

# Create a data model
/opencode Following the data-models.md skill, create a dataclass model for [feature].

# Add a CLI command
/opencode Using the cli-development.md skill, add a new command [name].
```

### Available AI Personas

Configured in `.opencode/opencode.json`:

| Persona | Task Category | Primary Model | Use For |
|---------|--------------|--------------|---------|
| **The Architect** | System Design, Planning | `deepseek/deepseek-v3.2` | High-level design, complex logic |
| **The Sleuth** | Debugging, Root Cause | `z-ai/glm-4.7` | Troubleshooting, problem analysis |
| **The Artisan** | Optimization, Style | `minimax/minimax-m2.1` | Code refinement, performance tuning |
| **The Coder** | Feature Build, Tests | `z-ai/glm-4.5-air` | Implementation, testing |
| **The Scribe** | Docs, Comments | `xiaomi/mimo-v2-flash` | Documentation, code comments |
| **The Auditor** | Code Review, Security | `openai/gpt-oss-120b` | Quality assurance, edge cases |

### Opencode Workflow

1. **Describe your task** with reference to the relevant skill
2. **Review the changes** opencode proposes
3. **Run validation** (format, typecheck, tests)
4. **Commit** when satisfied with the results

### Best Practices

- Always reference the specific skill when asking opencode to perform a task
- Review code changes carefully before accepting
- Run `just ruff-format`, `just ruff-check`, `just typecheck`, and `just test` after opencode makes changes
- Use `LANGNET_LOG_LEVEL=DEBUG` for detailed logging when debugging
- Clear cache with `devenv shell langnet-cli -- langnet-cli cache-clear` when testing backend changes
- Restart the uvicorn server after code changes (modules are cached)

### Example Session

```
User: /opencode Using the backend-integration.md skill, create a new backend for Gothic language
Opencode: I'll create a new backend for Gothic following the project patterns...

[Performs file creation, adds models, wires into engine]

User: /opencode Using the testing.md skill, run the test suite
Opencode: Running nose2 -s tests --config tests/nose2.cfg...

[Reports test results]

User: /opencode Using the debugging.md skill, help me troubleshoot why Gothic queries fail
Opencode: Let me check the health status and enable debug logging...

[Diagnoses issue, proposes fix]
```

### Persona Usage Reference

- **New contributors**: Use @coder for implementation, @artisan for code style
- **Adding backends**: Use @architect for design, @coder for implementation
- **Debugging issues**: Use @sleuth for root cause analysis
- **Documentation**: Use @scribe for documentation tasks
- **Code review**: Use @auditor for quality assurance
