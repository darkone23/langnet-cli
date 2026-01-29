# POS Parsing Test Cases and Patterns

This file captures the intended behavior for POS parsing that was being tested in `test_heritage_pos_parsing.py`. These test cases should be implemented in a proper parser once regex is replaced.

## Expected POS Parsing Behavior

### Basic POS Extraction
The parser should extract headword and POS pairs from Heritage Platform responses in the format:
`headword [ POS ] definition`

#### Test Cases
| Input | Expected Output (headword, POS) |
|-------|----------------------------------|
| `agni [ m. ] fire` | (`agni`, `m.`) |
| `jātu [ Ind. ]` | (`jātu`, `Ind.`) |
| `deva [ m. ] god` | (`deva`, `m.`) |
| `mitra [ m. ] friend` | (`mitra`, `m.`) |
| `soma [ m. ] juice` | (`soma`, `m.`) |
| `varuna [ m. ] god` | (`varuna`, `m.`) |
| `jyotiṣ [ f. ] astronomy` | (`jyotiṣ`, `f.`) |
| `agniḥ [ m. ] fire` | (`agniḥ`, `m.`) |

#### Complex Definitions with Multiple Senses
| Input | Expected Behavior |
|-------|-------------------|
| `agni [ m. ] fire; god of fire` | Extract `("agni", "m.")` |
| `deva [ m. ] god; deity` | Extract `("deva", "m.")` |
| `mitra [ m. ] friend` | Extract `("mitra", "m.")` |

### Multiple Headword Support
The parser should handle responses with multiple headword-POS pairs:

| Input | Expected Output |
|-------|----------------|
| `agni [ m. ] fire deva [ m. ] god mitra [ m. ] friend` | Extract 3 pairs: `[("agni", "m."), ("deva", "m."), ("mitra", "m.")]` |

### POS Code Meanings Reference
The parser should recognize these common POS codes:

| POS Code | Meaning | Example Usage |
|----------|---------|---------------|
| `Ind.` | Indeclinable | `jātu [ Ind. ]` |
| `N.` | Noun | `agni [ N. ] fire` |
| `m.` | Masculine | `deva [ m. ] god` |
| `f.` | Feminine | `jyotiṣ [ f. ] astronomy` |
| `n.` | Neuter | (test case needed) |
| `adj.` | Adjective | (test case needed) |
| `v.` | Verb | (test case needed) |

### Edge Cases to Handle
| Edge Case | Example | Expected Behavior |
|-----------|---------|-------------------|
| Headwords with numbers | `agni1 [ m. ] fire` | Extract `("agni1", "m.")` |
| Headwords with hyphens | `mahā-rāja [ m. ] great king` | Extract `("mahā-rāja", "m.")` |
| POS code variations | `deva [ masc. ] god` | Extract `("deva", "masc.")` or normalize to `m.` |
| Malformed responses | `agni [ N. fire` | Handle gracefully, return error |
| Empty responses | `` | Return empty result or error |

### Output Structure
The `process_heritage_response_for_cdsl` function should return a dictionary with:

```python
{
    "extracted_headwords_pos": [("headword1", "pos1"), ("headword2", "pos2")],
    "headwords_only": ["headword1", "headword2"],
    "pos_info": {"headword1": "pos1", "headword2": "pos2"},
    "cdsl_lookups": [
        {
            "iast": "headword1",
            "slp1": "slp1_version",
            "cdsl_key": "normalized_key",
            "cdsl_query": "SELECT ...",
            "pos": "pos1"
        }
    ]
}
```

### Implementation Notes
1. **Do not use regex** - This is captured as technical debt in TODO.md
2. Use proper parser combinators or structured text parsing
3. Handle encoding conversions (IAST to SLP1) properly
4. Maintain compatibility with existing CDSL lookup workflow
5. Add comprehensive error handling for malformed responses

## Migration Strategy
1. ✅ **Current**: Test cases captured here for reference
2. 🔄 **Next**: Implement proper parser using parser combinators
3. ✅ **Then**: Replace regex-based implementation
4. ✅ **Final**: Update tests to use new parser implementation