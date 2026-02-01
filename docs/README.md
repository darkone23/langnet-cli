# Langnet CLI Documentation

Welcome to the comprehensive documentation for **langnet-cli** - a classical language education tool designed to help students and scholars study Latin, Greek, and Sanskrit through comprehensive linguistic analysis.

## 📚 Documentation Structure

This directory contains the complete documentation for langnet-cli, organized by audience and purpose.

### 🚀 Quick Start
- **[GETTING_STARTED.md](GETTING_STARTED.md)** - Installation and first steps
- **[README.md](../README.md)** - Project overview and quick start guide
- **[examples/](../examples/)** - Usage examples

### 👨‍💻 Development
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Development setup, conventions, and AI workflow
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Technical reference and system design
- **[skills/](skills/)** - Development patterns and best practices

### 📊 Project Status
- **[ROADMAP.md](ROADMAP.md)** - Current implementation status and roadmap
- **[plans/](plans/)** - Active, completed, and future development plans

### 🎓 Educational Approach
- **[PEDAGOGY.md](PEDAGOGY.md)** - Educational philosophy and Foster functional grammar
- **[CITATIONS.md](CITATIONS.md)** - Sources, dependencies, and citations

### 🔧 Reference & Support
- **[API.md](API.md)** - Complete API reference
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues and solutions
- **[component-readmes/](component-readmes/)** - Module-specific documentation

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

### For New Users
- Start with **[GETTING_STARTED.md](GETTING_STARTED.md)** for installation and basic usage
- Read **[README.md](../README.md)** for project overview
- Explore **[examples/](../examples/)** for practical usage examples

### For Developers
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Complete development guide with AI workflow
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Technical implementation details
- **[skills/](skills/)** - AI-assisted development patterns
- **[plans/](plans/)** - Current development plans and status

### For Researchers & Educators
- **[PEDAGOGY.md](PEDAGOGY.md)** - Educational philosophy and goals
- **[CITATIONS.md](CITATIONS.md)** - Sources and dependencies
- **[component-readmes/](component-readmes/)** - Detailed module information

### For API Users
- **[API.md](API.md)** - Complete API reference
- **[examples/](../examples/)** - API usage examples

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

See **[AGENTS.md](../AGENTS.md)** and **[skills/](skills/)** for complete AI development documentation.

## 📊 Project Status

- **Implementation**: ~85% complete (citation system fully functional)
- **Code Quality**: Excellent (all ruff/typecheck checks pass)
- **Test Coverage**: 381+ tests passing
- **Documentation**: Comprehensive and well-organized
- **Architecture**: Well-designed modular system

## 🆘 Getting Help

1. **Installation Issues**: Follow [GETTING_STARTED.md](GETTING_STARTED.md)
2. **Development Setup**: Follow [DEVELOPMENT.md](DEVELOPMENT.md)
3. **Technical Problems**: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) and [ARCHITECTURE.md](ARCHITECTURE.md)
4. **API Usage**: See [API.md](API.md)
5. **AI Development**: Use the skills system in [skills/](skills/)

## 📄 License

This project is licensed under the MIT License. See **[../LICENSE](../LICENSE)** for details.

---

*Last Updated: February 2, 2026*  
*For the latest updates and roadmap, see [ROADMAP.md](ROADMAP.md) and [plans/](/)*