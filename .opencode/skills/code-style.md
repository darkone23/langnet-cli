# Code Style Tools

Format, lint, and typecheck code following project conventions.

## Tools

- **Formatter**: `ruff format`
- **Type checker**: `ty check` (or `mypy` via devenv)
- **Linter**: `ruff check`

## Running Tools

```bash
# Format code
just ruff
# or
ruff format src/ tests/

# Type check
just typecheck
# or
ty check

# Lint
ruff check src/ tests/
```

## Pre-commit Workflow

After making changes, always run:
```bash
just ruff      # Format
just typecheck # Type check
just test      # Run tests
```

## Code Conventions

### Naming

- Functions: `snake_case` (e.g., `handle_query`, `parse_word`)
- Classes: `PascalCase` (e.g., `LanguageEngine`, `DiogenesScraper`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `DG_PARSED`, `GREEK`)
- Variables: `snake_case` (e.g., `word_list`, `result_dict`)

### Type Hints

```python
# Required
def query(self, word: str) -> MyResult:
    pass

# Optional (use | union, NOT Optional[])
def parse(self, data: str | None) -> dict:
    pass

# Generics (use lowercase builtins)
def process(self, items: list[str]) -> dict[str, int]:
    pass
```

### Import Order

1. Standard library
2. Third-party packages
3. Local modules (relative before absolute)

```python
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

import langnet.logging
from langnet.core import LangnetWiring
```

### Comments

- NEVER comment obvious code
- ALWAYS comment non-obvious logic (algorithm choices, workarounds)
- Format: lowercase, no trailing period

```python
# BAD
# Increment the counter
count += 1

# GOOD
# fixup() requires sorted wordlist for deduplication to work
wordlist.sort()
```

### Error Handling

```python
# ValueError - invalid input
if lang not in valid_languages:
    raise ValueError(f"Unsupported language: {lang}")

# NotImplementedError - missing features
if lang == "xyz":
    raise NotImplementedError(f"Support for {lang} not implemented")

# AssertionError - invariant violations
assert len(word) > 0, "Word cannot be empty"

# print() - expected failures (e.g., missing binary)
if not whitakers_path.exists():
    print(f"Whitakers binary not found: {whitakers_path}")
```

### Module Organization

Prefer `@staticmethod` methods on classes:
```python
# GOOD - prevents namespace pollution
class HealthChecker:
    @staticmethod
    def diogenes(base_url: str) -> dict:
        return {...}

# AVOID - pollutes namespace
def check_diogenes(base_url: str) -> dict:
    return {...}
```

## Python Version

Project requires Python 3.10-3.11 (matching CLTK):
```toml
python = "<3.12,>=3.10"
```

## Test File Names

- `tests/test_<module>.py` for module tests
- Example: `tests/test_diogenes_scraper.py`, `tests/test_cache.py`

## Test Class Names

- `Test<Feature>` for test classes
- `test_<scenario>` for test methods
```python
class TestGreekSpacyIntegration(unittest.TestCase):
    def test_greek_query_includes_spacy_response(self):
        pass
```
