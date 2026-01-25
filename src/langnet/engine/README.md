# Language Engine

Orchestration layer that routes queries to appropriate backend lexicons and aggregates results.

## Purpose

The `LanguageEngine` is the core orchestrator:
1. Receives validated (language, word) pairs
2. Routes to available backends for that language
3. Aggregates results into unified response
4. Handles missing backends gracefully

## Architecture

```
LanguageEngine
├── diogenes: DiogenesScraper  → Perseus lexicon (Greek/Latin)
├── whitakers: WhitakersWords  → Latin morphology
├── cltk: ClassicsToolkit      → CLTK Latin lexicon
└── cdsl: SanskritCologneLexicon → Sanskrit dictionary
```

### Backend Selection by Language

| Language | diogenes | whitakers | CLTK | CDSL |
|----------:|:--------:|:---------:|:----:|:----:|
| Latin     | ✓        | ✓         | ✓    | -    |
| Greek     | ✓        | -         | -    | -    |
| Sanskrit  | -        | -         | ✓    | ✓    |

## Query Flow

```
handle_query(lang: str, word: str)
    ↓
validate language via LangnetLanguageCodes.get_for_input()
    ↓
route by language:
    ├─ Latin:   diogenes + whitakers + CLTK (parallel)
    ├─ Greek:   diogenes only
    └─ Sanskrit: CDSL (placeholder)
    ↓
aggregate results (model_dump → dict)
    ↓
return dict (JSON-serializable)
```

## Language Codes

Uses ISO 639-3 codes internally:
- `lat` - Latin
- `grc` - Ancient Greek
- `san` - Sanskrit

These map to `ClassicsToolkit` language enums for CLTK compatibility.

## Data Aggregation

Results from multiple backends are merged:
- Each backend returns its own Pydantic model
- Models are dumped to dicts with `exclude_none=True`
- Dicts are combined into single response dict
- Keys are backend names: `diogenes`, `whitakers`, `cltk`, `cdsl`

## Integration Points

### Input
- `lang`: ISO 639-3 language code string
- `word`: UTF-8 word to look up

### Output
Dict with backend-specific keys, e.g.:
```python
{
    "diogenes": {...},      # DiogenesResultT
    "whitakers": {...},     # WhitakersWordsResult
    "cltk": {...},          # LatinQueryResult
}
```

### Called By
- `langnet/asgi.py` - ASGI request handler
- Tests - Direct engine instantiation

## Configuration

Engine is instantiated via `LangnetWiring` (dependency injection):
```python
from langnet.core import LangnetWiring

wiring = LangnetWiring()
engine = wiring.engine  # LanguageEngine instance
```

This ensures all backends are initialized consistently.

## Error Handling

- `ValueError`: Invalid language code
- `NotImplementedError`: Language without backend support

## Grammar Abbreviations

`GrammarAbbreviations.cassells_terms_` is a dictionary of Latin grammatical abbreviations (from Cassells 1854). Used for debugging output, not currently integrated into results.
