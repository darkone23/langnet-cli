# Data Model Creation

Create dataclass models using Python dataclasses and cattrs for serialization.

## Multi-Model AI Persona

**Recommended Persona**: The Architect (`openrouter/deepseek/deepseek-v3.2:architect`)

Use this persona for:
- Designing complex data models
- Schema design for new data types
- Serialization/deserialization patterns
- Type system design

Example:
```bash
/model openrouter/deepseek/deepseek-v3.2:architect
"Design a comprehensive data model for Sanskrit morphological analysis results"
```

## Pattern

Always use `@dataclass` decorator with cattrs, NOT pydantic.

### Basic Model
```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class MyModel:
    required_field: str
    optional_field: str | None = field(default=None)
    list_field: list[str] = field(default_factory=list)
```

### Nested Models
```python
@dataclass
class NestedModel:
    value: str

@dataclass
class ParentModel:
    nested: NestedModel
    items: list[NestedModel] = field(default_factory=list)
```

## Serialization with cattrs

```python
import cattrs

converter = cattrs.Converter(omit_if_default=True)

# Convert dataclass to dict (for JSON response)
result_dict = converter.unstructure(my_instance)

# Convert dict back to dataclass
instance = converter.structure(data_dict, MyModel)
```

## Gotchas

1. Use `|` for unions: `str | None` NOT `Optional[str]`
2. Use `field(default=None)` for optional fields
3. Use `field(default_factory=list)` for mutable defaults
4. Generic types: `list[str]`, `dict[str, int]`
5. Converter should be initialized with `omit_if_default=True` to avoid sending nulls

## Language Engine Integration

```python
class LanguageEngine:
    def __init__(self, ...):
        self._cattrs_converter = cattrs.Converter(omit_if_default=True)

    def handle_query(self, lang, word):
        result = self.backend.query(word)
        return self._cattrs_converter.unstructure(result)
```

## See Examples

- `src/langnet/diogenes/core.py` - 9 dataclass models
- `src/langnet/whitakers_words/core.py` - 6 dataclass models
- `src/langnet/engine/core.py` - GrammarAbbreviations class with dataclass usage
