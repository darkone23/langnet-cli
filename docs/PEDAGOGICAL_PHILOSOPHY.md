# Pedagogical Philosophy

**Last Updated:** January 29, 2026  
**Status:** Core pedagogical transformation **ACTIVE** - Our north star guiding further development

## Foster Functional Grammar Approach

### Core Principle
Always show what words *do* in sentences, not just technical categories. This applies to **Greek, Latin, and Sanskrit**.

### Display Format
**Technical Term + Foster Function** (e.g., "Nominative (Naming Function)")

### Current Status: ✅ ACTIVE
- All Latin cases, tenses, genders, numbers mapped to Foster functions
- All Greek cases, tenses, genders, numbers, moods, voices mapped  
- All Sanskrit cases (1-8), genders, numbers mapped
- Automatically applied to all query results
- **North Star achieved:** langnet-cli now functions as a pedagogical engine

## The "Bang for the Buck" Matrix (Updated)

| Priority | Feature | Status | Pedagogical Impact | Why it matters |
|----------|---------|--------|-------------------|----------------|
| **P0** | **Lemmatization** | ✅ **COMPLETE** | **Huge** | Beginners can use dictionary |
| **P0** | **Foster Functional Grammar** | ✅ **COMPLETE** | **Huge** | Learn grammar by function |
| **P1** | **Citation Display** | 🔄 **Partial** | **Huge** | "See the word in the wild" |
| **P1** | **Fuzzy Searching** | ⏳ **Pending** | High | Handles typos/variants |
| **P2** | **CDSL Reference Enhancement** | ⏳ **Pending** | High | Cross-dictionary exploration |
| **P2** | **Enhanced Citation Formatting** | ⏳ **Pending** | Medium | Learner-friendly format |
| **P3** | **Cross-Lexicon Etymology** | ⏳ **Pending** | Medium | Philology research |

## Sanskrit Pedagogy

### Key Pedagogical Features Now Active ✅

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

### Pedagogical Value
- **Beginners**: Can look up inflected forms without knowing lemma
- **Intermediate**: See connections between words via roots
- **Advanced**: Research etymology and word families

## Latin & Greek Pedagogy

### Foster Function Implementation Now Active ✅

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

### Contextual Learning
- Citations from classical texts (Diogenes integration)
- Real usage examples from literature
- Foster's method: "See the word in the wild"

## Design Principles

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

## Implementation Examples

### Sanskrit Query
```
Query: योगेन
Root: √yuj (to join, unite)
Definition: yoga, union, connection
Morphology: Case 3 (By-With Function), Instrumental case, Singular
```

### Latin Query  
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

### Greek Query
```
Query: λόγος
Morphology:
  - Masculine (Male Function)
  - Nominative (Naming Function)
  - Singular (Single Function)
```

## Future Pedagogical Development

See [FUTURE_WORK.md](FUTURE_WORK.md) for prioritized features that will further enhance the learning experience.

### High-Impact Future Features
1. **Enhanced Citation Display** - Foster's "see the word in the wild"
2. **Fuzzy Search** - Help learners despite orthographic variations
3. **Cross-Reference Navigation** - Explore word families and relationships

## Conclusion

The langnet-cli implements a **pedagogical-first approach** to classical language learning. By prioritizing function over form and making dictionary lookup accessible to beginners, it supports learners at all levels while maintaining scholarly accuracy.

The core pedagogical vision—Foster functional grammar across all three languages—is now **active and operational**, providing a solid foundation for ongoing transformation into a comprehensive pedagogical engine.