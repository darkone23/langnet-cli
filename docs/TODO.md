# Langnet CLI - Roadmap & TODO

**Last Updated**: February 1, 2026  
**Project Status**: ~75% Complete - Well-architected codebase with core functionality working

## 🎯 Current Active Development

### P0 - Core Pedagogical Foundation (✅ COMPLETE)
- **Foster Functional Grammar**: ✅ IMPLEMENTED
  - All Latin, Greek, and Sanskrit cases, tenses, genders mapped to functions
  - "Naming Function", "Receiving Function", etc.
- **Lemmatization**: ✅ IMPLEMENTED
  - Inflected forms → dictionary headwords
  - Essential for beginner accessibility

### P1 - High-Impact Features (🔄 PARTIAL)

#### 1. Citation Display (🔄 PARTIAL)
- **Status**: Basic integration exists, needs enhancement
- **Goal**: Foster's "see the word in the wild" approach
- **Planned**: Sense-level citation formatting from classical texts
- **Priority**: High - Huge pedagogical impact
- **Files**: `docs/plans/active/CITATION_SYSTEM.md`

#### 2. Fuzzy Searching (⏳ PENDING)
- **Status**: Not started
- **Goal**: Handle typos and orthographic variations (v/u, etc.)
- **Priority**: High - Improves user experience
- **Planned**: CLTK integration for Latin/Greek, custom for Sanskrit

#### 3. CDSL Reference Enhancement (⏳ PENDING)
- **Status**: Not started
- **Goal**: Cross-dictionary exploration links
- **Priority**: Medium - Good for advanced users
- **Planned**: Enhanced `<ls>` reference handling

### P2 - Enhanced Features (⏳ PENDING)

#### 1. ASCII Enrichment (🔄 PARTIAL)
- **Status**: Sanskrit working, Latin/Greek pending
- **Goal**: Smart encoding detection and conversion
- **Progress**: 
  - ✅ Sanskrit: Devanagari, IAST, Velthuis, SLP1, HK, ASCII
  - 🔄 Latin/Greek: Need CLTK integration
- **Priority**: Medium - Improves accessibility

#### 2. Enhanced Citation Formatting (⏳ PENDING)
- **Status**: Not started
- **Goal**: Learner-friendly citation presentation
- **Priority**: Medium - UX improvement

### P3 - Advanced Features (⏳ PENDING)

#### 1. Cross-Lexicon Etymology (⏳ PENDING)
- **Status**: Not started
- **Goal**: Trace word origins across Latin, Greek, Sanskrit
- **Priority**: Low - Scholar-focused
- **Complexity**: High - Requires deep linguistic integration

#### 2. Performance & Scaling (⏳ PENDING)
- **Status**: Current performance is adequate for single-user
- **Goal**: Multi-user support and optimizations
- **Priority**: Low - Not critical for current use case

## 🚀 Major Initiatives

### 1. Universal Schema (🔄 MINIMAL PROGRESS)
- **Status**: Plan exists, no implementation
- **Goal**: Language-agnostic JSON data model with citation support
- **Priority**: Medium - Foundation for future features
- **Files**: `docs/plans/active/UNIVERSAL_SCHEMA_PLAN.md`

### 2. DICO Integration (⏳ NOT STARTED)
- **Status**: Only exists in plan documents
- **Goal**: French-Sanskrit bilingual dictionary support
- **Priority**: Medium - Enhances Sanskrit learning
- **Files**: `docs/plans/todo/dico/`
  - `DICO_INTEGRATION_PLAN.md`
  - `DICO_IMPLEMENTATION_GUIDE.md`
  - `DICO_BILINGUAL_PIPELINE.md`

### 3. CTS URN System (⏳ NOT STARTED)
- **Status**: Plan exists
- **Goal**: Canonical Text Standard reference system
- **Priority**: Low - Scholarly feature
- **Files**: `docs/plans/active/CTS_URN_SYSTEM.md`

## 🚨 Critical Technical Issues

### Immediate Fixes Required

1. **Duplicate Fields in LanguageEngineConfig**
   ```python
   # src/langnet/engine/core.py:129-132
   normalization_pipeline: NormalizationPipeline | None = None  # line 129
   enable_normalization: bool = True
   normalization_pipeline: NormalizationPipeline | None = None  # line 131 (DUPLICATE!)
   enable_normalization: bool = True  # DUPLICATE!
   ```
   - **Impact**: Runtime behavior undefined
   - **Fix**: Remove lines 131-132
   - **Priority**: HIGH - Must fix

2. **Documentation Cleanup**
   - **Issue**: 8 active plan files with outdated/completed status
   - **Issue**: Some plans claim "in progress" but are fully implemented
   - **Fix**: Consolidate and archive completed work
   - **Priority**: MEDIUM - Impro maintainability

## 📅 Development Timeline

### Immediate (Next 1-2 Weeks)
- [ ] Fix duplicate fields in LanguageEngineConfig
- [ ] Complete ASCII enrichment for Latin/Greek via CLTK
- [ ] Archive completed plans and update documentation
- [ ] Start basic fuzzy search implementation

### Short Term (2-4 Weeks)
- [ ] Implement enhanced citation display (sense-level formatting)
- [ ] Begin DICO integration (French-Sanskrit dictionary)
- [ ] Complete Universal Schema design foundation
- [ ] Add fuzzy search for all three languages

### Medium Term (1-2 Months)
- [ ] Implement Universal Schema JSON data model
- [ ] Enhanced CDSL reference features
- [ ] Cross-lexicon etymology research tools
- [ ] Performance optimizations and caching improvements

### Long Term (3+ Months)
- [ ] CTS URN system integration
- [ ] Multi-user scaling and performance
- [ ] Advanced pedagogical features
- [ ] Mobile/web interface possibilities

## 🎯 Success Metrics

### Technical Metrics
- [ ] 100% test coverage (currently 381 tests passing)
- [ ] Zero runtime warnings or errors
- [ ] <1s query response time for all backends
- [ ] Comprehensive error handling and recovery

### Educational Metrics
- [ ] Beginner-friendly onboarding (5-minute setup)
- [ ] Clear functional grammar explanations
- [ ] Contextual citations for major vocabulary words
- [ ] Multi-encoding accessibility

### User Experience Metrics
- [ ] Fuzzy search handles common misspellings
- [ ] Intuitive CLI interface
- [ ] Comprehensive error messages
- [ ] Cross-platform compatibility

## 📊 Current Implementation Status

### ✅ Fully Implemented & Working
- **Core Query Engine**: Multi-language routing and aggregation
- **Sanskrit Heritage Integration**: Full parser and encoding support
- **Velthuis System**: Smart normalization with long vowel sensitivity
- **Normalization Pipeline**: 381 tests passing, robust validation
- **Foster Functional Grammar**: All three languages complete
- **Lemmatization**: Basic to advanced forms
- **Response Caching**: DuckDB-based caching system
- **AI-Assisted Development**: Multi-model persona system

### 🔄 Partially Implemented
- **ASCII Enrichment**: Sanskrit only, Latin/Greek pending
- **Citation Display**: Basic integration, needs enhancement
- **Universal Schema**: Design complete, implementation pending

### ⏳ Not Started
- **Fuzzy Search**: Critical for user experience
- **DICO Integration**: French-Sanskrit dictionary
- **CTS URN System**: Scholarly text references
- **Cross-Lexicon Etymology**: Advanced research feature

## 🤖 Development Resources

### AI-Assisted Development
- **Personas**: 6 specialized AI assistants for different tasks
- **Skills**: 11 development skills for rapid prototyping
- **Model Routing**: Cost-effective multi-model strategy
- **Automation**: Comprehensive justfile commands

### Documentation
- **Structure**: Well-organized docs with clear navigation
- **Plans**: Active/todo/completed lifecycle management
- **Skills**: AI development workflow documented
- **Guides**: User, developer, and researcher documentation

## 🔄 Known Dependencies & Gotchas

### External Services
- **Diogenes**: Must run at `http://localhost:8888`
- **Whitakers-words**: Binary at `~/.local/bin/whitakers-words`
- **CLTK**: ~500MB download on first use
- **CDSL**: Sanskrit dictionaries in `~/cdsl_data/`

### Technical Gotchas
- **Process Restart**: Server caches Python modules - restart after code changes
- **Diogenes Threads**: Run `just langnet-dg-reaper` for cleanup
- **Cache Management**: Use `langnet-cli cache-clear` for testing
- **Encoding Support**: Multiple input formats supported per language

---

*For detailed technical implementation, see [REFERENCE.md](REFERENCE.md)*  
*For development setup and workflow, see [DEVELOPER.md](DEVELOPER.md)*  
*For current active plans, see [plans/ACTIVE_WORK_SUMMARY.md](plans/ACTIVE_WORK_SUMMARY.md)*