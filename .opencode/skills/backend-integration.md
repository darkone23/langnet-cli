# Data Provider Integration

Add a new data provider (dictionary/morphology resource) to langnet-cli.

## What is a "Data Provider"?

A data provider is a linguistic resource that can be queried for word information to support language learning. Examples:
- **Diogenes**: Lexicon + morphology for Latin/Greek (Perseus databases)
- **Whitaker's Words**: Morphology analyzer for Latin (academic tool)
- **CLTK**: Lexicon + lemmatization (Classical Language Toolkit)
- **CDSL**: Sanskrit dictionary (Monier-Williams, Apte, AP90)

Data providers can be:
- HTTP APIs (like Diogenes/Perseus)
- CLI binaries (like Whitaker's)
- Python libraries (like CLTK)
- Indexed databases (like CDSL)

## Educational Considerations

When integrating a new provider, consider:
- **Clarity for learners**: Present information in an accessible format
- **Authoritative sources**: Use recognized academic references
- **Complete morphology**: Include grammatical details (case, number, gender, voice, etc.)
- **Encoding support**: Handle UTF-8, Betacode, SLP1, Devanagari as needed
- **Citations**: Reference dictionary entries and sources

## Steps

1. Create module directory in `src/langnet/<provider>/`
2. Implement core class with query method following existing patterns
3. Create dataclass models using `@dataclass` decorator
4. Use cattrs for serialization (NOT pydantic)
5. Add tests in `tests/test_<provider>.py`
6. Wire into `LanguageEngine.handle_query()` in `src/langnet/engine/core.py`
7. Add health check in `HealthChecker` class in `src/langnet/asgi.py`

## Code Patterns

### Dataclass Model Template
```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class MyBackendResult:
    field1: str
    field2: list[str] = field(default_factory=list)
    optional_field: str | None = field(default=None)
```

### Core Class Template
```python
import structlog
import langnet.logging  # noqa: F401

logger = structlog.get_logger(__name__)

class MyBackend:
    def query(self, word: str) -> MyBackendResult:
        logger.debug("query_started", word=word)
        # implementation
        return result
```

### Wiring in LanguageEngine
```python
from langnet.my_backend.core import MyBackend

class LanguageEngine:
    def __init__(self, ...):
        self.my_backend = MyBackend()

    def handle_query(self, lang, word):
        if lang == "xyz":
            try:
                result = self.my_backend.query(word)
                return _cattrs_converter.unstructure(result)
            except Exception as e:
                logger.error("backend_failed", backend="my_backend", error=str(e))
                return {"error": f"MyBackend unavailable: {str(e)}"}
```

## Multi-Model AI Persona

**Recommended Persona**: The Architect (`openrouter/deepseek/deepseek-v3.2:architect`)

Use this persona for:
- Designing new backend architecture
- Planning data provider integration
- Schema design for new language models
- System-level integration planning

Example:
```bash
/model openrouter/deepseek/deepseek-v3.2:architect
/plan "Design an Old Norse dictionary backend with proper morphological analysis"
```

## Examples

Existing data providers demonstrating different integration patterns:
- `src/langnet/diogenes/core.py` - HTTP client + HTML parsing (Perseus databases)
- `src/langnet/whitakers_words/core.py` - CLI wrapper + line parsing (academic tool)
- `src/langnet/cologne/core.py` - DuckDB index lookup (Sanskrit dictionaries)
- `src/langnet/classics_toolkit/core.py` - Python library wrapper (CLTK)
