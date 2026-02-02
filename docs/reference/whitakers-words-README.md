# Whitaker's Words Parser

Wrapper and line parser for [Whitaker's Words](https://latin-words.com) - a Latin morphological analyzer written in Ada.

## Background

Whitaker's Words analyzes Latin words and returns:
- **Part of speech**: Noun, verb, adjective, etc.
- **Inflection details**: Case, number, gender, tense, mood, etc.
- **Dictionary form**: Headword (lemma)
- **Etymology**: Word origin and age

The original program is a standalone executable. This module:
1. Executes the binary with word input
2. Parses structured output into dataclass models
3. Provides clean Python API

## Usage

```python
from langnet.whitakers_words.core import WhitakersWords

whitakers = WhitakersWords()

# Returns structured Latin analysis
result = whitakers.words(["amabat"])
# WhitakersWordsResult(wordlist=[WhitakersWordsT(...)])
```

## Architecture

### Line Classification

Output lines are classified by pattern:

| Pattern | Type | Description |
|---------|------|-------------|
| Contains `;` | `sense` | Dictionary sense definitions |
| Contains `]` | `term-code` | Morphological code line |
| Matches `[a-z.]+ [A-Z]+` | `term-facts` | Term data line |
| Empty/UI control | `skip` | Not parsed |

### Line Parsers (lineparsers/)

Modular parsers handle each line type:

- **FactsReducer** (`parse_term_facts.py`): Parses "word STAMP info" lines
- **CodesReducer** (`parse_term_codes.py`): Parses `[code:explanation]` lines
- **SensesReducer** (`parse_senses.py`): Parses "1. definition; 2. definition" lines

### Parsing Pipeline

```
whitakers-words CLI output
    ↓
WhitakersWordsChunker.__init__(): Execute command
    ↓
splitlines(): Break into lines
    ↓
classify_line(): Assign type to each line
    ↓
get_next_word(): Aggregate lines into word chunks
    (Groups lines until new word starts)
    ↓
analyze_chunk(): Extract txts/types, discard UI lines
    ↓
WhitakersWords.words(): Parse each chunk
    ├─ term-facts → WhitakerWordData
    ├─ term-code → CodelineData/CodelineName
    └─ sense → SensesReducer result
    ↓
smart_merge(): Merge partial results
fixup(): Post-process (fill missing term in codeline)
    ↓
WhitakersWordsResult
```

## Data Models

### WhitakerWordData
Complete morphological analysis for one word form:
- `term`: The analyzed word
- `part_of_speech`: POS category
- `declension`/`conjugation`: Inflection class
- `case`/`number`/`gender`: Nominal features
- `tense`/`mood`/`voice`: Verbal features
- `term_analysis`: Stem + ending decomposition

### CodelineData
Morphological code from Whitaker's `[code:explanation]` format:
- `term`: Headword
- `pos_code`: Part of speech code (N, V, ADJ, etc.)
- `age`/`source`/`freq`: Etymological info

### SensesReducer Output
Dictionary sense information (lines with `;`):
- `senses`: List of sense strings
- `raw_lines`: Original lines for debugging

## Integration Points

- **Input**: List of words (executes once per batch)
- **Output**: `WhitakersWordsResult` dataclass model
- **Called by**: `LanguageEngine.handle_query()` for Latin

## Binary Discovery

The module searches for the whitakers-words binary in order:
1. `~/.local/bin/whitakers-words` (user install)
2. `deps/whitakers-words/bin/words` (development)
3. Fallback: Returns dummy command that fails (graceful degradation)

## Dependencies

- `sh` - subprocess abstraction for executing binary
- `re` - regex for term pattern matching
- cattrs for dataclass serialization

## Known Issues

1. **ARM not supported**: Prebuilt Ada binary only for x86_64. ARM users: build from source following upstream instructions.
2. **Batch execution**: Single CLI call for all words; partial failures affect all
3. **Line parsing brittleness**: Relies on exact output format
4. **Unicode handling**: Assumes Latin-1 compatible output
