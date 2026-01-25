# Cologne Sanskrit Lexicon

Sanskrit dictionary lookup from [Cologne Digital Sanskrit Lexicon](https://www.sanskrit-lexicon.uni-koeln.de/) (CDSL).

## Background

The Cologne Digital Sanskrit Lexicon provides scanned and TEI-encoded Sanskrit-English dictionaries:
- **MW**: Monier-Williams Sanskrit-English Dictionary (1899)
- **AP90**: V.S. Apte Practical Sanskrit-English Dictionary (1957-1959)
- Additional dictionaries available

This module provides transliteration and dictionary lookup interfaces.

## Capabilities

- **Transliteration**: Convert between multiple Sanskrit scripts/schemes:
  - HK (Harvard-Kyoto)
  - IAST (International Alphabet of Sanskrit Transliteration)
  - Devanagari
  - ITRANS
- **ASCII input**: Accepts HK transliteration
- **Devanagari conversion**: Automatic conversion for dictionary lookup

## Usage

```python
from langnet.cologne.core import SanskritCologneLexicon

cdsl = SanskritCologneLexicon()

# Lookup with HK transliteration
result = cdsl.lookup_ascii("sa.msk.rta")
# Returns structured dictionary entries
```

## Architecture

### Transliteration Pipeline

```
input: "sa.msk.rta" (HK)
    ↓
detect(): Guess input scheme
    ↓
transliterate(): Convert to Devanagari
    ↓
lookup: Search Devanagari in CDSL data
    ↓
serialize_results(): Parse entries into structured format
    ↓
output: CologneSanskritQueryResult
```

### Transliteration Schemes (indic-transliteration)

Uses `indic-transliteration` package for conversions:
- `sanscript.HK` → `sanscript.DEVANAGARI`
- `sanscript.IAST` → `sansscript.DEVANAGARI`
- Custom scheme support via `SchemeMap`

## Data Models

### SanskritDictionaryEntry
Single dictionary definition:
- `id`: Entry identifier
- `subid`: Sub-entry for multiple senses
- `meaning`: English definition

### SanskritDictionaryLookup
Grouped entries for one headword:
- `term`: Headword in Devanagari
- `iast`: IAST transliteration
- `hk`: HK transliteration
- `entries`: List of SanskritDictionaryEntry

### CologneSanskritQueryResult
Top-level response container:
- `mw`: Monier-Williams results
- `ap90`: Apte results

## Integration Points

- **Input**: ASCII/HK transliteration string
- **Output**: `CologneSanskritQueryResult` dataclass model
- **Called by**: `LanguageEngine.handle_query()` for Sanskrit

## Current Status

### Implemented
- Transliteration (HK → Devanagari) via `indic-transliteration`
- Placeholder responses when CDSL unavailable

### Not Implemented (Blocked)

The `pycdsl` library depends on `libcdso.so` from Cologne University, which is no longer distributed or available. This blocks local CDSL integration.

## Future Work: Native CDSL Parser

Once Greek/Latin functionality is complete, implement a custom CDSL parser in this project:

1. Parse TEI XML files directly from `~/cdsl_data/` (MW, AP90)
2. Implement entry grouping by headword ID
3. Integrate with existing transliteration via `indic-transliteration`
4. Replace `pycdsl` dependency entirely

This removes the blocked external dependency and enables full Sanskrit support.

## Dependencies

- `indic-transliteration` - Transliteration conversion
- `pycdsl` - Non-functional, will be replaced with native parser

## Known Issues

1. **Placeholders only**: `lookup_ascii()` returns string placeholders, not real data
2. **Blocked dependency**: `pycdsl.CDSLCorpus.setup()` requires libcdso.so which is unavailable
