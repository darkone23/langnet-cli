# Tests

This directory contains the test suite for the langnet-cli project.

## Test Files

| File | Purpose |
|------|---------|
| `test_classics_toolkit.py` | Tests for `ClassicsToolkit.latin_query()` and property access |
| `test_cltk_playground.py` | CLTK Latin functionality: lemmatizer, lexicon, transcriber, replacer |
| `test_diogenes_scraper.py` | Diogenes web scraper: chunk classification, Latin/Greek parsing |
| `test_whitakers_words.py` | Whitaker's Words parser: senses, codes, facts extraction |

## Running Tests

```bash
just test
```

Or directly:

```bash
nose2 -s tests --config tests/nose2.cfg
```

## Test Data

The `data/` subdirectory contains debug/sample data used during parser development:

- `whitakers-lines/senses.txt` - Raw dictionary sense definitions
- `whitakers-lines/term-codes.txt` - Morphological code lines  
- `whitakers-lines/term-facts.txt` - Word fact/definition lines

These files contain sample output from Whitaker's Words used to develop and test the line parsers in `langnet/whitakers_words/lineparsers/`.
