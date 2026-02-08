# Langnet CLI - Roadmap & Status

This roadmap is a snapshot of work in progress. Known gaps are tracked in `docs/TODO.md` (Diogenes sense extraction/CTS URNs, Sanskrit canonicalization + DICO integration, CDSL SLP1 artifacts, universal schema). External services (Heritage, Diogenes, Whitaker's Words) remain required for most functionality and for running tests.


#### Core Pedagogical Foundation
- **Foster Functional Grammar**: basic
  - All Latin, Greek, and Sanskrit cases, tenses, genders mapped to functions
  - "Naming Function", "Receiving Function", etc.
  - Essential for beginner accessibility

- **Lemmatization**: not yet unified
  - Inflected forms → dictionary headwords
  - Cross-backend normalization working

#### Multi-Language Backend Integration
- **Sanskrit Heritage Platform**: basic reader / search functionality
  - Full parser integration with encoding support
  - Devanagari, IAST, Velthuis, SLP1, HK, ASCII
  - Smart normalization with ASCII enrichment

- **Diogenes (Greek/Latin)**: basic search result parsing
  - Lewis & Short (Latin) and Liddell & Scott (Greek)
  - Real citation extraction with CTS URN mapping
  - Foster grammar integration

- **Whitaker's Words (Latin)**: text output parsing
  - Morphological analysis and lemmatization
  - Integration with core query engine


#### Educational Enhancements

1. **DICO Integration** - NOT STARTED
   - **Goal**: French-Sanskrit bilingual dictionary
   - **Priority**: MEDIUM - Enhances Sanskrit learning
   - **Status**: Planning complete, implementation pending

2. **Enhanced Citation Rendering** - PARTIAL
   - **Current**: Basic citation display working
   - **Goal**: Sense-level formatting for better pedagogy
   - **Priority**: MEDIUM - UX improvement
   - **Status**: API integration complete, enhancement pending

#### Technical & Advanced
1. **Cross-Lexicon Etymology** - NOT STARTED
   - **Goal**: Trace word origins across Latin, Greek, Sanskrit
   - **Priority**: LOW - Scholar-focused feature
   - **Complexity**: High - Requires deep linguistic integration

2. **Performance & Scaling** - NOT STARTED
   - **Current**: Adequate for single-user
   - **Goal**: Multi-user support and optimizations
   - **Priority**: LOW - Not critical for current use case

### Educational Metrics
- **Accessibility**: Multi-encoding support for all languages
- **Pedagogy**: Clear functional grammar explanations
- **Context**: Real citations for major vocabulary words
- **Onboarding**: 5-minute setup time for new users

### User Experience Metrics
- **Search**: Fuzzy search handles common misspellings
- **Interface**: Intuitive CLI with helpful error messages
- **Reliability**: Robust backend service integration
- **Cross-Platform**: Works across different environments
