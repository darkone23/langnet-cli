# Langnet CLI - Pedagogical Philosophy & Goals

**Last Updated**: February 1, 2026  
**Status**: Core pedagogical transformation **ACTIVE** - Our north star guiding further development

## 🎯 Mission Statement

Langnet-cli is a **pedagogical engine** designed to help students and scholars study Latin, Greek, and Sanskrit through comprehensive linguistic analysis. The tool provides instant access to dictionary definitions, morphological parsing, and grammatical information to supplement language learning and text comprehension.

**Primary Users**: Classical language students, researchers, and enthusiasts  
**Primary Use Case**: Quick reference while reading classical texts  
**Key Features**: Multi-source lexicon lookup, morphological analysis, vocabulary building, Foster functional grammar

## 🌟 Foster Functional Grammar Approach

### Core Principle
Always show what words *do* in sentences, not just technical categories. This applies to **Greek, Latin, and Sanskrit**.

### Display Format
**Technical Term + Foster Function** (e.g., "Nominative (Naming Function)")

### Current Status: ✅ ACTIVE
- All Latin cases, tenses, genders, numbers mapped to Foster functions
- All Greek cases, tenses, genders, numbers, moods, voices mapped  
- All Sanskrit cases (1-8), genders, numbers mapped
- Automatically applied to all query results
- **North Star achieved**: langnet-cli now functions as a pedagogical engine

## 📊 Pedagogical Priorities Matrix

### P0 - Core Foundation (✅ COMPLETE)
| Priority | Feature | Status | Pedagogical Impact | Why it matters |
|----------|---------|--------|-------------------|----------------|
| **P0** | **Lemmatization** | ✅ **COMPLETE** | **Huge** | Beginners can use dictionary |
| **P0** | **Foster Functional Grammar** | ✅ **COMPLETE** | **Huge** | Learn grammar by function |

### P1 - High-Impact Features (🔄 PARTIAL)
| Priority | Feature | Status | Pedagogical Impact | Why it matters |
|----------|---------|--------|-------------------|----------------|
| **P1** | **Citation Display** | 🔄 **Partial** | **Huge** | "See the word in the wild" |
| **P1** | **Fuzzy Searching** | ⏳ **Pending** | High | Handles typos/variants |

### P2 - Enhanced Features (⏳ PENDING)
| Priority | Feature | Status | Pedagogical Impact | Why it matters |
|----------|---------|--------|-------------------|----------------|
| **P2** | **CDSL Reference Enhancement** | ⏳ **Pending** | High | Cross-dictionary exploration |
| **P2** | **Enhanced Citation Formatting** | ⏳ **Pending** | Medium | Learner-friendly format |

### P3 - Advanced Features (⏳ PENDING)
| Priority | Feature | Status | Pedagogical Impact | Why it matters |
|----------|---------|--------|-------------------|----------------|
| **P3** | **Cross-Lexicon Etymology** | ⏳ **Pending** | Medium | Philology research |
| **P3** | **Performance / Scaling** | ⏳ **Pending** | **Low** | Single-user performance adequate |

## 📚 Language-Specific Pedagogy

### Sanskrit Pedagogy

#### Key Pedagogical Features Now Active ✅

1. **Root-Focused Learning**
   - Sanskrit verb/noun roots displayed prominently
   - Format: `√ag (to move, go)`
   - Connects words to etymological foundations

2. **Lemmatization for Inflected Forms**
   - `योगेन` (instrumental) → lemma `yoga` → dictionary lookup
   - Essential for beginners encountering inflected forms
   - Transparent tracking of transformation

3. **Multiple Encoding Support**
   - Devanagari, IAST, SLP1, Velthuis
   - Learners can use preferred transliteration
   - Automatic conversion for dictionary lookup

#### Pedagogical Value
- **Beginners**: Can look up inflected forms without knowing lemma
- **Intermediate**: See connections between words via roots
- **Advanced**: Research etymology and word families

#### Implementation Examples
```
Query: योगेन
Root: √yuj (to join, unite)
Definition: yoga, union, connection
Morphology: Case 3 (By-With Function), Instrumental case, Singular
```

### Latin & Greek Pedagogy

#### Foster Function Implementation Now Active ✅

**Latin Examples:**
- `nom` → "Naming Function"
- `acc` → "Receiving Function"  
- `gen` → "Possessing Function"
- `dat` → "To-For Function"
- `abl` → "By-With-From-In Function"

**Greek Examples:**
- `nom` → "Naming Function"
- `gen` → "Possessing Function"
- `dat` → "To-For Function"
- `acc` → "Receiving Function"
- `voc` → "Calling Function"

#### Implementation Examples
**Latin Query**  
```
Query: sumpturi
Morphology:
  - Future (Time-Later Function)
  - Participle (Participle Function)
  - Active (Doing Function)
  - Masculine (Male Function)
  - Nominative (Naming Function)
  - Plural (Group Function)
```

**Greek Query**
```
Query: λόγος
Morphology:
  - Masculine (Male Function)
  - Nominative (Naming Function)
  - Singular (Single Function)
```

### Contextual Learning
- Citations from classical texts (Diogenes integration)
- Real usage examples from literature
- Foster's method: "See the word in the wild"

## 🎨 Design Principles

### 1. Function Over Form
Traditional grammatical categories (nominative, accusative, genitive) are translated into functional descriptions that explain what the word is *doing* in the sentence.

### 2. Learner-Centric
- **Beginners**: Focus on function and meaning
- **Intermediate**: Add technical terminology alongside function
- **Advanced**: Full technical details available

### 3. Progressive Disclosure
- Show most pedagogically useful information first
- Technical details available on demand
- Never overwhelm with jargon

### 4. Cross-Language Consistency
- Same pedagogical approach for all three languages
- Consistent terminology where applicable
- Language-specific adaptations where needed

## 🔧 Implementation Architecture

### Foster Functional Grammar Integration
- **Location**: `src/langnet/foster/`
- **Implementation**: Language-specific modules for Latin, Greek, Sanskrit
- **Integration**: Applied automatically to all query results
- **Status**: ✅ Complete for all three languages

### Educational Data Models
- **Location**: `src/langnet/heritage/models.py`, `src/langnet/whitakers_words/core.py`
- **Features**: Structured output with pedagogical enhancements
- **Integration**: Foster functions embedded in morphological analysis
- **Status**: ✅ Complete and active

### Multi-Encoding Support
- **Sanskrit**: Devanagari, IAST, Velthuis, SLP1, HK, ASCII
- **Greek**: Unicode, Betacode
- **Latin**: Unicode, Betacode
- **Status**: ✅ Sanskrit complete, Greek/Latin basic support

## 🚀 Future Pedagogical Development

### High-Impact Future Features

#### 1. Enhanced Citation Display (P1)
- **Goal**: Foster's "see the word in the wild"
- **Features**: Sense-level citation formatting, authentic text examples
- **Impact**: Reinforces vocabulary in context
- **Status**: 🔄 Basic integration exists, needs enhancement

#### 2. Fuzzy Search (P1)
- **Goal**: Help learners despite orthographic variations
- **Features**: Handle common misspellings (v/u, etc.)
- **Impact**: Improves accessibility for beginners
- **Status**: ⏳ Not started

#### 3. Cross-Reference Navigation (P2)
- **Goal**: Explore word families and relationships
- **Features**: Etymology connections, root-based exploration
- **Impact**: Advanced research capabilities
- **Status**: ⏳ Not started

#### 4. CDSL Reference Enhancement (P2)
- **Goal**: Cross-dictionary exploration for Sanskrit
- **Features**: `<ls>` lexicon references, related entries
- **Impact**: Enhanced scholarly research
- **Status**: ⏳ Not started

## 📈 Educational Impact Metrics

### Current Achievements
- **Beginner Accessibility**: ✅ Inflected forms → dictionary headwords
- **Grammar Learning**: ✅ Functional explanations across all languages
- **Encoding Flexibility**: ✅ Multiple input formats supported
- **Citation Integration**: 🔄 Basic contextual examples

### Target Metrics
- **Beginner Onboarding**: 5-minute setup to first successful query
- **Grammar Understanding**: Functional explanations for 100% of morphological features
- **Vocabulary Retention**: Contextual citations for major vocabulary words
- **User Experience**: Fuzzy search handles common misspellings

## 🎓 Educational Philosophy in Practice

### Foster's Method Implementation
Langnet-cli implements Reginald Foster's teaching philosophy:

1. **Function Over Form**: Instead of "nominative case," say "Naming Function"
2. **Contextual Learning**: Show words as they appear in real texts
3. **Beginner-Friendly**: Make dictionary lookup accessible to all levels
4. **Scholarly Accuracy**: Maintain linguistic precision while being pedagogical

### Progressive Learning Path
- **Stage 1 (Beginner)**: Focus on meaning and basic function
- **Stage 2 (Intermediate)**: Add technical terminology alongside function
- **Stage 3 (Advanced)**: Full technical details and scholarly references

## 🔍 Technical Implementation Details

### Foster Function Mapping
- **Latin**: Complete mapping of cases, tenses, genders, numbers
- **Greek**: Complete mapping including moods and voices
- **Sanskrit**: Complete mapping of cases 1-8, genders, numbers
- **Integration**: Automatic application to all query results

### Data Model Enhancements
- **WordResult**: Includes Foster function descriptions
- **MorphologyAnalysis**: Functional grammar explanations
- **CitationData**: Contextual usage examples
- **RootInformation**: Etymological connections for Sanskrit

### Multi-Language Consistency
- **Consistent Terminology**: Same functional terms across languages
- **Language-Specific Adaptations**: Cultural and linguistic nuances
- **Progressive Disclosure**: Layered information presentation

## 🎯 Success Criteria

### Educational Effectiveness
- [ ] Beginners can successfully query inflected forms
- [ ] Functional grammar explanations are clear and intuitive
- [ ] Contextual citations reinforce vocabulary learning
- [ ] Multiple encoding options support diverse learning styles

### Technical Excellence
- [ ] Foster functions applied to 100% of morphological analysis
- [ ] Multi-encoding support works seamlessly for all languages
- [ ] Performance remains responsive for educational use
- [ ] Error messages are helpful and pedagogical

### User Experience
- [ ] 5-minute onboarding for new users
- [ ] Intuitive CLI interface for quick reference
- [ ] Cross-platform compatibility for learning environments
- [ ] Comprehensive error handling and recovery

## 🤝 Community & Contribution

### Educational Resources
- **Documentation**: Comprehensive guides for educators and students
- **Examples**: Real-world usage scenarios and case studies
- **Workflows**: Integration with common language learning practices

### Development Participation
- **Educator Feedback**: Welcome input from language teachers
- **Student Testing**: Real-world testing with language learners
- **Scholarly Review**: Expert validation of linguistic content

## 📚 Related Documentation

### Technical Implementation
- **[REFERENCE.md](REFERENCE.md)** - Technical architecture and implementation details
- **[DEVELOPER.md](DEVELOPER.md)** - Development setup and workflow
- **[TODO.md](TODO.md)** - Current roadmap and priorities

### Educational Resources
- **[PEDAGOGICAL_PHILOSOPHY.md](PEDAGOGICAL_PHILOSOPHY.md)** - Detailed philosophy explanation
- **[plans/](../plans/)** - Educational feature development plans
- **[examples/](../../examples/)** - Usage examples and demonstrations

## 🎉 Conclusion

The langnet-cli implements a **pedagogical-first approach** to classical language learning. By prioritizing function over form and making dictionary lookup accessible to beginners, it supports learners at all levels while maintaining scholarly accuracy.

The core pedagogical vision—Foster functional grammar across all three languages—is now **active and operational**, providing a solid foundation for ongoing transformation into a comprehensive pedagogical engine.

**Key Achievements**:
- ✅ Foster functional grammar complete for all three languages
- ✅ Comprehensive lemmatization system
- ✅ Multi-encoding support for accessibility
- ✅ Integration of scholarly and educational approaches

**Future Focus**:
- 🔄 Enhanced citation display and formatting
- 🔄 Fuzzy search for improved user experience
- 🔄 Advanced cross-lexicon features for research
- 🔄 Continued refinement of educational workflows

---

*For current implementation status and roadmap, see [TODO.md](TODO.md)*  
*For technical implementation details, see [REFERENCE.md](REFERENCE.md)*  
*For development setup, see [DEVELOPER.md](DEVELOPER.md)*