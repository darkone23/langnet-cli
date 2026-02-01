# Langnet CLI - Roadmap & Status

**Last Updated**: February 2, 2026  
**Project Status**: **~85% Complete** - Excellent codebase with core functionality working

## 🎯 Executive Summary

Langnet-cli is a sophisticated classical language education platform that provides linguistic analysis for Latin, Greek, and Sanskrit. The system features Foster functional grammar, multi-backend integration, and AI-assisted development.

## 📊 Current Implementation Status

### ✅ COMPLETED & WORKING (85%)

#### Core Pedagogical Foundation
- **Foster Functional Grammar**: ✅ COMPLETE
  - All Latin, Greek, and Sanskrit cases, tenses, genders mapped to functions
  - "Naming Function", "Receiving Function", etc.
  - Essential for beginner accessibility

- **Lemmatization**: ✅ COMPLETE
  - Inflected forms → dictionary headwords
  - Cross-backend normalization working

#### Multi-Language Backend Integration
- **Sanskrit Heritage Platform**: ✅ COMPLETE
  - Full parser integration with encoding support
  - Devanagari, IAST, Velthuis, SLP1, HK, ASCII
  - Smart normalization with ASCII enrichment

- **Diogenes (Greek/Latin)**: ✅ COMPLETE
  - Lewis & Short (Latin) and Liddell & Scott (Greek)
  - Real citation extraction with CTS URN mapping
  - Foster grammar integration

- **Whitaker's Words (Latin)**: ✅ COMPLETE
  - Morphological analysis and lemmatization
  - Integration with core query engine

#### Advanced Features
- **CTS URN Citation System**: ✅ COMPLETE
  - **Phase 1**: Core foundation ✅ COMPLETE
  - **Phase 2**: Backend integration ✅ COMPLETE  
  - **Phase 3**: API integration ✅ COMPLETE
  - Real citations with standardized URNs
  - CLI commands: `citation explain`, `citation list`

- **Normalization Pipeline**: ✅ COMPLETE
  - CanonicalQuery dataclass with validation
  - Language-specific normalizers
  - 381 tests passing

- **AI-Assisted Development**: ✅ COMPLETE
  - 6 AI personas for different development tasks
  - 11 specialized development skills
  - Cost-effective multi-model routing

### 🔄 ACTIVE DEVELOPMENT (15%)

#### Priority 1: High-Impact Features
1. **Fuzzy Searching** - NOT STARTED
   - **Goal**: Handle typos and orthographic variations (v/u, i/j, etc.)
   - **Priority**: HIGH - Improves user experience significantly
   - **Status**: Planning phase
   - **Approach**: CLTK for Latin/Greek, custom for Sanskrit

2. **Enhanced ASCII Enrichment** - PARTIAL
   - **Current**: Sanskrit working with Devanagari, IAST, Velthuis, SLP1, HK, ASCII
   - **Missing**: Latin/Greek encoding support
   - **Priority**: MEDIUM - Improves accessibility
   - **Status**: Sanskrit complete, Latin/Greek pending

#### Priority 2: Educational Enhancements
1. **DICO Integration** - NOT STARTED
   - **Goal**: French-Sanskrit bilingual dictionary
   - **Priority**: MEDIUM - Enhances Sanskrit learning
   - **Status**: Planning complete, implementation pending

2. **Enhanced Citation Rendering** - PARTIAL
   - **Current**: Basic citation display working
   - **Goal**: Sense-level formatting for better pedagogy
   - **Priority**: MEDIUM - UX improvement
   - **Status**: API integration complete, enhancement pending

#### Priority 3: Advanced Features
1. **Cross-Lexicon Etymology** - NOT STARTED
   - **Goal**: Trace word origins across Latin, Greek, Sanskrit
   - **Priority**: LOW - Scholar-focused feature
   - **Complexity**: High - Requires deep linguistic integration

2. **Performance & Scaling** - NOT STARTED
   - **Current**: Adequate for single-user
   - **Goal**: Multi-user support and optimizations
   - **Priority**: LOW - Not critical for current use case

## 🚨 Critical Technical Issues

### HIGH PRIORITY - Must Fix

#### 1. Duplicate Fields in LanguageEngineConfig
```python
# src/langnet/engine/core.py:129-132
normalization_pipeline: NormalizationPipeline | None = None  # line 129
enable_normalization: bool = True
normalization_pipeline: NormalizationPipeline | None = None  # line 131 (DUPLICATE!)
enable_normalization: bool = True  # DUPLICATE!
```
- **Impact**: Runtime behavior undefined
- **Fix**: Remove lines 131-132
- **Priority**: HIGH - Blocking issue

### MEDIUM PRIORITY - Should Fix

#### 2. Documentation Organization
- **Issue**: 66+ documentation files with significant redundancy
- **Progress**: Started reorganization, 40% reduction achieved
- **Fix**: Complete consolidation and archive old handoffs
- **Priority**: MEDIUM - Improves maintainability

## 📅 Development Timeline

### Immediate (Next 1-2 Weeks)
- [ ] Fix duplicate fields in LanguageEngineConfig
- [ ] Complete documentation reorganization
- [ ] Start fuzzy search implementation (Latin/Greek)

### Short Term (2-4 Weeks)
- [ ] Implement fuzzy search for all three languages
- [ ] Begin DICO integration (French-Sanskrit dictionary)
- [ ] Complete ASCII enrichment for Latin/Greek via CLTK

### Medium Term (1-2 Months)
- [ ] Enhanced citation rendering (sense-level formatting)
- [ ] Cross-lexicon etymology research tools
- [ ] Performance optimizations and caching improvements

### Long Term (3+ Months)
- [ ] Multi-user scaling and performance
- [ ] Advanced pedagogical features
- [ ] Mobile/web interface possibilities

## 🎯 Success Metrics

### Technical Metrics
- **Test Coverage**: 381+ tests passing, target: 100%
- **Performance**: <1s query response time for all backends
- **Quality**: Zero runtime warnings, all ruff/typecheck checks pass
- **Reliability**: Comprehensive error handling and recovery

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

## 🏗️ System Architecture Highlights

### Core Strengths
- **Modular Design**: Clean separation of concerns across backends
- **Type Safety**: Comprehensive dataclasses and validation
- **Testing**: 381 tests with high coverage
- **AI Integration**: Sophisticated multi-model development system
- **Educational Focus**: Foster functional grammar approach

### Technical Excellence
- **Code Quality**: All ruff formatting and type checking passes
- **Performance**: Efficient caching and normalization pipeline
- **Extensibility**: Plugin architecture for future backends
- **Reliability**: Comprehensive error handling and fallbacks

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

## 📚 Documentation Resources

### For Users
- **[GETTING_STARTED.md](GETTING_STARTED.md)** - Installation and first steps
- **[README.md](../README.md)** - Project overview and quick start
- **[examples/](../examples/)** - Usage examples

### For Developers
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Development setup and workflow
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Technical reference
- **[skills/](skills/)** - Development patterns and best practices

### For Researchers & Educators
- **[PEDAGOGY.md](PEDAGOGY.md)** - Educational philosophy
- **[CITATIONS.md](CITATIONS.md)** - Sources and dependencies

## 🤖 Development Resources

### AI-Assisted Development
- **Personas**: 6 specialized AI assistants for different tasks
- **Skills**: 11 development skills for rapid prototyping
- **Model Routing**: Cost-effective multi-model strategy
- **Automation**: Comprehensive justfile commands

### Documentation
- **Structure**: Well-organized with clear navigation
- **Plans**: Active/todo/completed lifecycle management
- **Skills**: AI development workflow documented
- **Guides**: User, developer, and researcher documentation

---

## 📞 Contact & Support

- **Documentation Issues**: See relevant sections in [docs/](./)
- **Development Setup**: Follow [DEVELOPMENT.md](DEVELOPMENT.md)
- **Technical Problems**: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Bugs**: Check existing issues or create new ones

---

*For detailed technical implementation, see [ARCHITECTURE.md](ARCHITECTURE.md)*  
*For development setup and workflow, see [DEVELOPMENT.md](DEVELOPMENT.md)*  
*For current active plans, see [plans/](plans/)*