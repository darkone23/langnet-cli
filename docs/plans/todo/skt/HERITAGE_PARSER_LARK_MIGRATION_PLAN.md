# Heritage Platform Parser Migration to Lark

## Executive Summary

Migrate the Heritage Platform HTML parser from regex/BeautifulSoup to a robust Lark-based parser, using the Whitaker's Words parser as reference implementation. This migration addresses fragility in the current regex approach and enables reliable Sanskrit morphology extraction.

**Current Issue**: The `SimpleHeritageParser` uses fragile regex patterns (`r"\[(.+?)\]\{(.+?)\}"`) that fail for many Sanskrit words, leaving `solutions` arrays empty despite `total_available` metadata showing available solutions.

## 1. Fuzz Testing Strategy

### Input Categories
- **Devanagari** (Unicode): अग्नि, योग, देव, आसन
- **IAST**: agni, yoga, deva, āsana  
- **Velthuis**: agni, yoga, deva, aasana
- **SLP1**: agni, yoga, deva, Asana

### Test Word Lists

**Core Test Set (50 words):**
```
# Basic nouns
agni, yoga, deva, asana, gaja, kavi, veda, rāja

# Verb forms
bhavati, karoti, gacchati, paśyati, tiṣṭhati

# Compounds
devaḥ, devāḥ, devasya, deve, devān, devaiḥ
yogaḥ, yogāt, yogena, yogaṃ, yogāya, yogāt

# Edge cases
ḥ (visarga), ṁ (anusvāra), ś (retroflex sibilant)
ṛ (vowel), ṝ (long vowel), ḷ (vowel)

# Sandhi forms
devaḥ + āgacchati = devo'gacchati
gajaḥ + tiṣṭhati = gajo'ṣṭhati
```

**Expected Output Patterns:**
```
[agni]{N1msn} → noun, masculine, singular, nominative
yogena]{N3nsa} → noun, neuter, singular, instrumental
bhavati]{V1spr} → verb, 1st conjugation, singular, present, active
```

### Validation Metrics
- **Extraction Rate**: Solutions found / solutions available in metadata
- **Field Completeness**: Word, lemma, POS, grammatical features extracted
- **Edge Case Handling**: Unicode, encoding variants, punctuation

## 2. EBNF Grammar for Heritage Platform Patterns

### Core Grammar Structure
```ebnf
start: solution_section+

solution_section: "Solution" INT (table_section | inline_analysis)+

table_section: "<table" ATTR* ">" analysis_row+ "</table>"

analysis_row: "<tr>" (td_cell | pattern_section)+ "</tr>"

td_cell: "<td" ATTR* ">" (text | pattern)* "</td>"

pattern_section: "[<b>"? WORD "</b>"? "]{" ANALYSIS "}"

WORD: /[^\]\}]+/       # Sanskrit word in any encoding
ANALYSIS: /[^\}]+/     # Morphological analysis codes
INT: /[0-9]+/
ATTR: /[^\>]+/
text: /[^<]+/
```

### Analysis Pattern Grammar
```ebnf
analysis: pos_code gender? number? case? person? tense? voice? mood?

pos_code: "N" | "V" | "A" | "P" | "C" | "I"
gender: "m" | "f" | "n" | "d" (dual)
number: "s" | "d" | "p"
case: "1".."8" | "n" (nominative) | "a" (accusative)
person: "1" | "2" | "3"
tense: "p" (present) | "i" (imperfect) | "f" (future)
voice: "a" (active) | "m" (middle) | "p" (passive)
mood: "i" (imperative) | "o" (optative) | "s" (subjunctive)
```

### Example Parses
```
[agni]{N1msn} → {pos: "noun", case: 1, gender: "m", number: "s"}
[yogena]{N3nsa} → {pos: "noun", case: 3, gender: "n", number: "s"}
[bhavati]{V1spr} → {pos: "verb", person: 1, number: "s", tense: "p", voice: "a"}
```

## 3. Implementation Steps

### Phase 1: Grammar Development (1 week)
@coder "Analyze HTML structure from live Heritage Platform responses and extract [word]{analysis} patterns"
@sleuth "Debug why current regex parser fails for words like 'yoga', 'deva', 'asana' while 'agni' works"
@architect "Design Lark grammar modularity for different Heritage Platform output patterns"
@coder "Define Lark grammar in `src/langnet/heritage/grammar/heritage_morphology.lark`"
@coder "Create test harness with sample HTML fixtures from real Heritage responses"
@auditor "Validate grammar against core test set of 100+ Sanskrit words"

**Deliverables:**
- `heritage_morphology.lark` - Complete grammar
- `test_grammar_samples.py` - Validation tests
- 50+ sample HTML responses for testing

### Phase 2: Parser Implementation (1 week)
@coder "Create `LarkHeritageParser` class following Whitaker's parser pattern"
@coder "Implement transformer to convert parse tree to structured `HeritageMorphologyResult` dataclass"
@sleuth "Add detailed logging for debugging failed parses and edge cases"
@coder "Integrate with existing `MorphologyParser` interface maintaining backward compatibility"
@artisan "Optimize parser performance for <50ms parse time per solution"

**Deliverables:**
- `lark_parser.py` - New parser implementation
- `transformer.py` - Parse tree to dict transformer
- Updated `parsers.py` with fallback strategy

### Phase 3: Integration & Testing (1 week)
1. **Add feature flag** to switch between parsers
2. **Run fuzz tests** against real Heritage Platform
3. **Benchmark performance** vs regex parser
4. **Update tests** to use new parser

**Deliverables:**
- Feature flag system (`USE_LARK_PARSER=true`)
- Performance benchmarks
- Updated integration tests
- Migration readiness report

### Phase 4: Production Migration (1 week)
1. **Deploy new parser** as default
2. **Monitor for regressions** via health checks
3. **Remove old parser** after validation
4. **Update documentation** with new parser details

**Deliverables:**
- Production deployment
- Health check monitoring
- Updated `IMPLEMENTATION_STATUS.md`
- Archive of old parser code

## 4. Testing Requirements

### Success Criteria
1. **Extraction Rate > 95%**: Parser extracts solutions for 95%+ of words with `total_available > 0`
2. **Field Completeness**: All required fields (word, lemma, POS, features) populated
3. **Encoding Support**: Works with Devanagari, IAST, Velthuis, SLP1
4. **Performance**: < 50ms parse time per solution
5. **Reliability**: No crashes on malformed HTML

### Edge Cases to Test
- **Empty solutions**: HTML with `0 solutions kept`
- **Multiple solutions**: 5+ solutions in one response
- **Complex compounds**: Multi-word analyses
- **Unicode boundaries**: Characters at encoding boundaries
- **Malformed HTML**: Missing closing tags, nested tables
- **Special characters**: Sanskrit punctuation (ḥ, ṁ, ṛ)

### Validation Approach
1. **Unit Tests**: Grammar parsing, transformer logic
2. **Integration Tests**: Real Heritage Platform responses
3. **Fuzz Tests**: Random input generation
4. **Golden Tests**: Known-good outputs for 100+ words

## 5. Lark Parser Reference Implementation

### Whitaker's Words Pattern
Reference the existing Whitaker's parser structure:
```
src/langnet/whitakers_words/lineparsers/
├── grammars/
│   ├── senses.ebnf      # EBNF grammar
│   ├── term_codes.ebnf
│   └── term_facts.ebnf
├── parse_senses.py      # Lark parser implementation
├── parse_term_codes.py
└── parse_term_facts.py
```

### Key Design Patterns to Reuse
1. **Grammar modularity**: Separate grammars for different patterns
2. **Transformer classes**: `TreeToDictTransformer` pattern
3. **Error handling**: Graceful fallback with logging
4. **Caching**: Lark parser instance reuse

## 6. Risk Mitigation

### Technical Risks
- **Grammar complexity**: Heritage HTML may have variations
- **Performance overhead**: Lark may be slower than regex
- **Memory usage**: Parse tree memory footprint

**Mitigation**:
- Start with simplified grammar, expand gradually
- Profile and optimize hot paths
- Implement parser instance caching

### Integration Risks
- **Breaking changes**: Existing tests may fail
- **Data format changes**: Output structure differences

**Mitigation**:
- Maintain backward compatibility during migration
- Use feature flag for gradual rollout
- Comprehensive test suite updates

## 7. Timeline

**Total**: 4 weeks
```
Week 1: Grammar development & testing
Week 2: Parser implementation & unit tests
Week 3: Integration & performance testing
Week 4: Production migration & monitoring
```

## 8. Success Metrics

1. **Code Health**: 95%+ test coverage for parser module
2. **Reliability**: Zero parser crashes in production
3. **Performance**: < 100ms 95th percentile parse time
4. **Extraction Rate**: > 95% solutions extracted
5. **User Impact**: Sanskrit queries return consistent morphology

## 9. Rollback Plan

If issues arise:
1. **Immediate**: Revert to regex parser via feature flag
2. **Hotfix**: Patch specific grammar rules
3. **Investigation**: Log parse failures for analysis
4. **Recovery**: Deploy corrected grammar within 24 hours

---

*This migration plan follows the successful Whitaker's Words parser pattern, replacing fragile regex with robust grammatical analysis for reliable Sanskrit morphology extraction.*