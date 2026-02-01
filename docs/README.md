# Langnet CLI Documentation

Welcome to the comprehensive documentation for **langnet-cli** - a classical language education tool designed to help students and scholars study Latin, Greek, and Sanskrit through comprehensive linguistic analysis.

## 📚 Documentation Structure

This directory contains the complete documentation for langnet-cli. Navigate to the section that best fits your needs:

### 🚀 Getting Started
- **[README.md](../README.md)** - Project overview and quick start guide
- **[PEDAGOGICAL_PHILOSOPHY.md](PEDAGOGICAL_PHILOSOPHY.md)** - Core educational approach and Foster functional grammar
- **[PEDAGOGY.md](PEDAGOGY.md)** - Pedagogical goals and priorities

### 👨‍💻 Development
- **[DEVELOPER.md](DEVELOPER.md)** - Development setup, conventions, and AI-assisted workflow
- **[REFERENCE.md](REFERENCE.md)** - Technical reference, architecture, and implementation details

### 📋 Project Planning
- **[plans/README.md](plans/README.md)** - Overview of project plans (active, completed, todo)
- **[plans/ACTIVE_WORK_SUMMARY.md](plans/ACTIVE_WORK_SUMMARY.md)** - Current implementation status
- **[TODO.md](TODO.md)** - Current roadmap and active development priorities

### 🤖 AI & Development
- **[opencode/](opencode/)** - AI-assisted development guides and skills
  - **[LLM_PROVIDER_GUIDE.md](opencode/LLM_PROVIDER_GUIDE.md)** - Multi-model AI strategy
  - **[MULTI_MODEL_GUIDE.md](opencode/MULTI_MODEL_GUIDE.md)** - AI persona system

## 🌟 Key Features

### Language Support
| Language | Dictionary Sources | Morphological Analysis | Encodings Supported |
|----------|-------------------|----------------------|-------------------|
| **Latin** | Diogenes (Lewis & Short), Whitaker's Words | ✓ | Latin, Betacode |
| **Greek** | Diogenes (Liddell & Scott), CLTK | ✓ | Greek, Betacode |
| **Sanskrit** | Sanskrit Heritage Platform, CDSL | ✓ | Devanagari, IAST, Velthuis, SLP1, HK, ASCII |

### Core Dependencies
- **Sanskrit Heritage Platform**: Primary Sanskrit analysis (localhost:48080)
- **Diogenes**: Greek/Latin lexicons (localhost:8888)
- **Whitaker's Words**: Latin morphology (~/.local/bin/whitakers-words)
- **CLTK**: Additional linguistic features (automatic download)
- **CDSL**: Sanskrit dictionaries (automatic download)

### Educational Features
- **Foster Functional Grammar**: Shows what words *do* in sentences, not just technical labels
- **Lemmatization**: Inflected forms → dictionary headwords
- **Multiple Encodings**: Support for various transliteration systems
- **Contextual Citations**: "See the word in the wild" from classical texts
- **Cross-References**: Root-based learning for Sanskrit

## 🎯 Quick Start

```bash
# Enter development environment
devenv shell

# Start the API server
uvicorn-run

# Query classical languages
langnet-cli query lat lupus        # Latin: wolf
langnet-cli query grc λόγος      # Greek: word
langnet-cli query san agni        # Sanskrit: fire

# Check backend health
langnet-cli verify
```

## 📖 Documentation Navigation

### For Users
- Start with the main **[README.md](../README.md)** for installation and basic usage
- Read **[PEDAGOGICAL_PHILOSOPHY.md](PEDAGOGICAL_PHILOSOPHY.md)** to understand the educational approach
- Check **[TODO.md](TODO.md)** for upcoming features and roadmap

### For Developers
- **[DEVELOPER.md](DEVELOPER.md)** - Complete development guide with AI workflow
- **[REFERENCE.md](REFERENCE.md)** - Technical implementation details
- **[plans/](plans/)** - Current and planned development work
- **[.opencode/skills/](../.opencode/skills/)** - AI-assisted development skills

### For Researchers & Educators
- **[PEDAGOGY.md](PEDAGOGY.md)** - Educational philosophy and goals
- **[REFERENCE.md](REFERENCE.md)** - Technical architecture and data models
- **[plans/ACTIVE_WORK_SUMMARY.md](plans/ACTIVE_WORK_SUMMARY.md)** - Current implementation status

## 🛠️ External Dependencies

This tool requires three external services to be installed separately:

1. **Sanskrit Heritage Platform** - Primary Sanskrit morphological analysis
   - API Server: `http://localhost:48080/sktreader`
   - Repository: http://sanskrit.inria.fr/
   - Required for Sanskrit dictionary and morphology queries
   - Provides advanced parsing, lemmatization, and encoding support

2. **diogenes** - Perl server for Perseus lexicon data
   - Repository: https://github.com/pjheslin/diogenes
   - Run at `http://localhost:8888`
   - Required for Greek/Latin dictionary queries

3. **whitakers-words** - Latin morphological analyzer
   - Binary: `~/.local/bin/whitakers-words`
   - Prebuilt x86_64 binaries available

### Automatic Dependencies
- **CLTK models**: Installed to `~/cltk_data/` (~500MB on first use)
- **CDSL data**: Sanskrit dictionaries in `~/cdsl_data/`

For complete dependency documentation, see [CITATIONS.md](CITATIONS.md).

## 🤖 AI-Assisted Development

This project uses a sophisticated multi-model AI development system:

- **6 AI Personas**: Architect, Sleuth, Artisan, Coder, Scribe, Auditor
- **OpenRouter Integration**: Cost-effective model routing
- **Opencode Skills**: 11 specialized development skills
- **Automated Testing**: Comprehensive test coverage with AI assistance

See **[.opencode/skills/README.md](../.opencode/skills/README.md)** for complete AI development documentation.

## 📊 Project Status

- **Implementation**: ~75% complete
- **Code Quality**: Excellent (all ruff/typecheck checks pass)
- **Test Coverage**: 381 tests passing
- **Documentation**: Comprehensive and well-organized
- **Architecture**: Well-designed modular system

## 🆘 Getting Help

1. **Documentation Issues**: Check the relevant sections above
2. **Development Setup**: Follow **[DEVELOPER.md](DEVELOPER.md)**
3. **Technical Problems**: See **[REFERENCE.md](REFERENCE.md)** for debugging
4. **AI Development**: Use the opencode skills system
5. **Bugs**: Check existing issues or create new ones

## 📄 License

This project is licensed under the MIT License. See **[../LICENSE](../LICENSE)** for details.

---

*Last Updated: January 29, 2026*  
*For the latest updates and roadmap, see **[TODO.md](TODO.md)** and **[plans/ACTIVE_WORK_SUMMARY.md](plans/ACTIVE_WORK_SUMMARY.md)**