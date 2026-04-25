# Contextual Word Meaning Lookup for Classical Texts
## Feature Plan: Enabling Word-by-Word Analysis of Complete Passages

**Feature Area**: Pedagogy  
**Status**: ⏳ PENDING  
**Priority**: High  
**Estimated Effort**: 3-4 weeks  
**AI Personas**: @architect @coder @artisan  

## 1. Overview

### 1.1 Problem Statement
Students reading classical texts like the Bhagavad Gītā need to understand words in context, not just isolated dictionary entries. Current tools provide individual word lookups but lack integrated passage analysis that:
1. Processes complete sentences/phrases
2. Preserves word order and grammatical relationships  
3. Shows contextual meaning selection from multiple dictionary senses
4. Provides cumulative translation with morphological analysis

### 1.2 Example Use Case: Bhagavad Gītā 1.1
**Input**: `dhṛitarāśhtra uvācha dharma-kṣhetre kuru-kṣhetre...`

**Desired Output**:
```
dhṛitarāśhtra: dhṛita-rāṣṭra ("holding the kingdom")
  • Proper noun: Dhritarashtra (king of the Kurus)
  • Morphology: Nominative singular, masculine
  
uvācha: √vac (to speak)
  • Perfect active, 3rd person singular: "he said"
  • Contextual: Introduces direct speech
  
dharma-kṣhetre: dharma- ("duty/law") + kṣetra ("field")
  • Compound: Locative singular neuter
  • Translation: "in the field of duty"
  
kuru-kṣhetre: kuru- (Kuru dynasty) + kṣetra ("field")
  • Compound: Locative singular neuter  
  • Translation: "in the field of the Kurus"
  
Cumulative: "Dhritarashtra said: In the field of duty, in the field of the Kurus..."
```

## 2. Core Requirements

### 2.1 Input Processing
- **Multi-word input**: Handle 5-50 word passages
- **Language detection**: Auto-detect Sanskrit vs Greek vs Latin
- **Sentence boundary detection**: Split on punctuation
- **Tokenization**: Handle sandhi, compounds, enclitics
- **Encoding support**: IAST, Devanagari, SLP1, Velthuis

### 2.2 Analysis Pipeline
```
Text Input → Tokenization → Normalization → 
Parallel Lookup (Morph + Lexicon) → 
Contextual Sense Selection → 
Grammatical Analysis → 
Output Formatting
```

### 2.3 Output Requirements
- **Word-level details**: Lemma, morphology, selected meaning
- **Contextual sense selection**: Algorithm to pick most relevant dictionary sense
- **Grammatical relationships**: Case, number, gender, syntax
- **Cumulative translation**: Build natural language output
- **Educational annotations**: Notes on compounds, etymology, cultural context

## 3. Technical Architecture

### 3.1 Data Structures

#### 3.1.1 PassageAnalysis (Pydantic Model)
```python
class PassageAnalysis(BaseModel):
    original_text: str
    language: Literal["san", "grc", "lat"]
    tokens: list[TokenAnalysis]
    cumulative_translation: str
    metadata: PassageMetadata

class TokenAnalysis(BaseModel):
    surface_form: str
    normalized_form: str
    lemma: str
    lemma_confidence: float
    morphology: Morphology
    dictionary_entries: list[DictionaryEntry]
    selected_sense: SelectedSense
    position: int
    grammatical_role: Optional[str]
    
class SelectedSense(BaseModel):
    sense_id: str
    gloss: str
    confidence_score: float
    contextual_reason: str  # "compound_context", "syntactic_role", "frequency"
```

#### 3.1.2 Contextual Sense Selector
```python
class ContextualSenseSelector:
    def select_sense(
        self, 
        token: TokenAnalysis, 
        context_window: list[TokenAnalysis],
        passage_themes: list[str]
    ) -> SelectedSense:
        # Weighted scoring:
        # 1. Syntactic compatibility (40%)
        # 2. Semantic coherence with neighbors (30%)
        # 3. Frequency in corpus (20%)
        # 4. Educational priority (10%)
```

### 3.2 Service Integration

#### 3.2.1 Existing Services to Leverage
1. **Sanskrit Heritage Platform** (`localhost:48080`)
   - Morphological parsing
   - Sandhi resolution  
   - Compound analysis

2. **CDSL Dictionary** (Monier-Williams/AP90)
   - Full dictionary entries
   - Sense hierarchy
   - Citation examples

3. **Diogenes** (`localhost:8888`) - for Greek/Latin
4. **Whitaker's Words** - for Latin morphology

#### 3.2.2 New Components Needed
1. **PassageTokenizer**
   - Language-specific tokenization rules
   - Sandhi splitting for Sanskrit
   - Compound word detection

2. **ContextualSenseResolver**
   - Bayesian sense selection
   - Theme detection from passage
   - Cross-reference with similar passages

3. **TranslationBuilder**
   - Natural language generation
   - Grammatical agreement handling
   - Style preservation

## 4. Implementation Phases

### Phase 1: Foundation (Week 1)
**Goal**: Basic passage tokenization and parallel lookup
- [ ] Create `PassageTokenizer` for Sanskrit
- [ ] Implement `batch_normalize` in normalizer
- [ ] Add `parallel_lookup` to execution engine
- [ ] Create basic `PassageAnalysis` data model
- [ ] Tests: Gītā 1.1, simple compounds

**Deliverables**:
- `langnet/pedagogy/passage_analyzer.py`
- `langnet/pedagogy/tokenizer.py`
- CLI command: `langnet-cli analyze-passage "dhṛitarāśhtra uvācha..."`

### Phase 2: Contextual Analysis (Week 2)
**Goal**: Smart sense selection and grammatical analysis
- [ ] Implement `ContextualSenseSelector`
- [ ] Add theme detection from passage keywords
- [ ] Integrate with existing semantic reduction
- [ ] Add grammatical role labeling
- [ ] Create translation builder

**Deliverables**:
- `langnet/pedagogy/context_resolver.py`
- `langnet/pedagogy/translation_builder.py`
- Enhanced CLI output with contextual notes

### Phase 3: Educational Features (Week 3)
**Goal**: Pedagogical enhancements and user experience
- [ ] Add compound word explanations
- [ ] Include etymological notes
- [ ] Add cultural/historical context
- [ ] Implement difficulty scoring
- [ ] Create progressive disclosure (simple → advanced)

**Deliverables**:
- `langnet/pedagogy/educational_annotator.py`
- `langnet/pedagogy/difficulty_scorer.py`
- Multiple output formats (simple, detailed, scholarly)

### Phase 4: Greek & Latin Support (Week 4)
**Goal**: Extend to all supported languages
- [ ] Adapt tokenizer for Greek (sandhi, enclitics)
- [ ] Adapt for Latin (elision, poetic devices)
- [ ] Language-specific sense selection rules
- [ ] Cross-language consistency checks

**Deliverables**:
- Language-agnostic pipeline
- Unified output schema
- Comparative analysis capability

## 5. API Design

### 5.1 CLI Interface
```bash
# Basic analysis
langnet-cli analyze-passage \
  --text "dhṛitarāśhtra uvācha dharma-kṣhetre kuru-kṣhetre" \
  --language san \
  --output detailed

# With educational annotations
langnet-cli analyze-passage \
  --text "dhṛitarāśhtra uvācha..." \
  --annotate compounds,etymology,culture \
  --difficulty intermediate

# Batch processing
langnet-cli analyze-file \
  --file gita_chapter1.txt \
  --format jsonl
```

### 5.2 HTTP API
```python
POST /api/v1/analyze/passage
{
  "text": "dhṛitarāśhtra uvācha...",
  "language": "san",
  "detail_level": "intermediate",
  "include": ["morphology", "etymology", "citations"]
}
```

### 5.3 Output Formats
1. **Simple**: Just translation and key vocabulary
2. **Detailed**: Word-by-word with morphology
3. **Scholarly**: Full dictionary entries, citations, variants
4. **Educational**: Annotated with learning aids

## 6. Pedagogical Considerations

### 6.1 Learning Progression
- **Beginners**: Focus on core vocabulary, simple translations
- **Intermediate**: Add morphology, compound analysis  
- **Advanced**: Full philological apparatus, textual variants

### 6.2 Error Handling
- **Unknown words**: Suggest similar forms, root families
- **Ambiguous parses**: Show all possibilities with confidence scores
- **Encoding issues**: Auto-detect and convert between schemes

### 6.3 Assessment Features
- **Vocabulary tracking**: Track words encountered
- **Difficulty metrics**: Word frequency, morphological complexity
- **Progress reports**: Most challenging words, improvement areas

## 7. Integration Points

### 7.1 With Existing Systems
- **Semantic Reduction**: Use sense buckets for meaning disambiguation
- **CTS URN Index**: Link words to canonical text locations
- **User Feedback**: Incorporate corrections into sense selection

### 7.2 Data Sources
- **Corpus frequencies**: From Perseus/Heritage corpora
- **Pedagogical word lists**: Common textbook vocabulary
- **Cultural references**: Mythology, history, philosophy

### 7.3 Caching Strategy
- **Passage-level cache**: Store complete analyses
- **Word-context cache**: Store sense selections in specific contexts
- **User-specific cache**: Learn from individual correction patterns

## 8. Testing Strategy

### 8.1 Test Corpus
- **Sanskrit**: Bhagavad Gītā 1.1-10, Rāmāyaṇa excerpts
- **Greek**: Iliad 1.1-10, Plato Apology excerpts  
- **Latin**: Aeneid 1.1-10, Cicero speeches

### 8.2 Validation Metrics
- **Accuracy**: Manual review by Sanskrit/Greek/Latin scholars
- **Consistency**: Same word in similar contexts gets same sense
- **Performance**: < 2 seconds for 20-word passage
- **Educational value**: User testing with language students

### 8.3 Edge Cases
- **Poetic devices**: Meter, alliteration, word play
- **Textual variants**: Multiple manuscript traditions
- **Fragmentary texts**: Incomplete or corrupted passages
- **Neologisms**: Modern compositions in classical languages

## 9. Success Criteria

### 9.1 Minimum Viable Product
- [ ] Process 10-word Sanskrit passage in < 5 seconds
- [ ] Correctly identify 80% of word senses in test corpus
- [ ] Provide understandable translation for beginners
- [ ] Handle basic sandhi and compounds

### 9.2 Complete Implementation  
- [ ] Support all three languages (Sanskrit, Greek, Latin)
- [ ] Process 50-word passages in < 3 seconds
- [ ] 90% sense selection accuracy
- [ ] Full educational annotations
- [ ] API stable and documented

### 9.3 Stretch Goals
- [ ] Real-time analysis as user types
- [ ] Comparative analysis across languages
- [ ] Integration with reading platforms
- [ ] Mobile app interface

## 10. Dependencies and Risks

### 10.1 Dependencies
- ✅ Sanskrit Heritage Platform running
- ✅ CDSL dictionary data available  
- ✅ Diogenes/Whitaker's running for Greek/Latin
- ⚠️ Semantic reduction system for sense clustering
- ⚠️ Corpus frequency data for word statistics

### 10.2 Risks and Mitigation
| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Heritage Platform API changes | Medium | High | Abstract client, mock for tests |
| Performance with long passages | High | Medium | Implement streaming, incremental analysis |
| Sense selection accuracy | High | High | Start simple (frequency-based), iterate |
| Educational usefulness | Medium | High | User testing early, pedagogical review |

## 11. Next Steps

### Immediate (Week 0)
1. **@architect**: Review and refine technical design
2. **@coder**: Set up project structure and basic models
3. **@artisan**: Establish code patterns and testing framework

### Short-term (Week 1-2)
1. Implement Phase 1: Tokenization and parallel lookup
2. Create integration tests with Gītā 1.1
3. Get feedback from Sanskrit scholars

### Medium-term (Week 3-4)
1. Complete contextual analysis system
2. Extend to Greek and Latin
3. Performance optimization

## 12. References

### Technical References
- [Sanskrit Heritage Platform API](http://localhost:48080/cgi-bin/skt/sktreader)
- [CDSL Dictionary Structure](docs/technical/design/cdsl_integration.md)
- [Semantic Reduction System](docs/plans/active/semantic-reduction/)

### Pedagogical References  
- [LangNet Educational Philosophy](docs/GOALS.md)
- [Foster Grammar Framework](docs/technical/design/foster_grammar.md)
- [Classical Language Pedagogy Research](docs/upstream-docs/pedagogy/)

### Example Texts
- Bhagavad Gītā (Critical Edition)
- Homeric Greek corpus
- Latin Aeneid with commentary

---

**Maintained by**: @architect @coder  
**Last Updated**: 2025-04-12  
**Next Review**: 2025-04-19