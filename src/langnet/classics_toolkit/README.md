# Classics Toolkit (CLTK) Wrapper

Provides Python interface to [Classical Languages Toolkit](https://github.com/cltk/cltk) for Latin, Greek, and Sanskrit computational linguistics.

## Capabilities

### Latin
- **Lemmatization**: `LatinBackoffLemmatizer` finds headwords from inflected forms
- **Lexicon lookup**: `LatinLewisLexicon` (Lewis & Short, 1879)
- **Phonetics**: IPA transcription via `Transcriber`

### Greek
- Language detection and corpus loading

### Sanskrit
- Language detection and corpus loading

## Usage

```python
from langnet.classics_toolkit.core import ClassicsToolkit

cltk = ClassicsToolkit()

# Latin query returns structured results
result = cltk.latin_query("amabat")
# LatinQueryResult(headword='amo', ipa='aːmaːbɑt', lewis_1890_lines=['...'])
```

## Implementation Details

### Model Management
On initialization, `ClassicsToolkit` checks for required CLTK models:
- `lat_models_cltk` - required for Latin lemmatization and lexicon

Models are downloaded to `~/cltk_data/` via `cltk_fetch.FetchCorpus.import_corpus()`. This is a one-time download (~500MB) triggered automatically on first use.

### Data Flow (latin_query)

```
input: "amabat"
    ↓
lemmatize: ["amabat"] → ["amo"] (headword)
    ↓
lookup: "amabat" → dictionary entries
    ↓
transcribe: "amabat" → IPA string
    ↓
merge: combine lookup results, format Lewis lexicon lines
    ↓
output: LatinQueryResult(headword, ipa, lewis_1890_lines)
```

## Integration Points

- **Input**: Raw Latin word (inflected or headword)
- **Output**: `LatinQueryResult` Pydantic model
- **Called by**: `LanguageEngine.handle_query()` for Latin

## Dependencies

- `cltk` package (installed via poetry)
- `lat_models_cltk` data (downloaded on first run)
- `re` for regex processing
- `cltk.phonology.lat.transcription` for IPA

## Gotchas

1. **Cold download**: First `latin_query()` call downloads CLTK models; may take several minutes
2. **Lemmatizer fallback**: If word not found, attempts lemmatized form
3. **IPA stripping**: Transcriber returns quotes; code strips them `[1:-1]`
4. **Empty results**: Returns empty `lewis_1890_lines` list if lookup fails
