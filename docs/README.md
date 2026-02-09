# Langnet CLI Documentation

Welcome to the comprehensive documentation for **langnet-cli** - a classical language education tool designed to help students and scholars study Latin, Greek, and Sanskrit through comprehensive linguistic analysis.

## 📚 Documentation Structure

This directory contains the complete documentation for langnet-cli, organized by audience and purpose.

### 🚀 Quick Start
- **[GETTING_STARTED.md](GETTING_STARTED.md)** - Installation and first steps
- **[../README.md](../README.md)** - Project overview and quick start guide
- **[examples/](../examples/)** - Usage examples

### 👨‍💻 Development
- **[DEVELOPER.md](DEVELOPER.md)** - Development setup, conventions, and AI workflow
- **[technical/ARCHITECTURE.md](technical/ARCHITECTURE.md)** - Technical reference and system design
- **[technical/opencode/](technical/opencode/)** - AI development patterns and multi-model workflows

### 📊 Project Status
- **[plans/](plans/)** - Active, completed, and future development plans (roadmap consolidated there)

### 🎓 Educational Approach
- **[PEDAGOGICAL_PHILOSOPHY.md](PEDAGOGICAL_PHILOSOPHY.md)** - Educational philosophy and Foster functional grammar
- **[CITATIONS.md](CITATIONS.md)** - Sources, dependencies, and citations

### 🔧 Reference & Support
- **[technical/](technical/)** - Component documentation and technical references
- **[GETTING_STARTED.md](GETTING_STARTED.md)** - Installation and troubleshooting guide
- **[DEVELOPER.md](DEVELOPER.md)** - Development troubleshooting and common issues

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
devenv shell langnet-cli

# Run a single command with environment activated
devenv shell langnet-cli -- langnet-cli query lat lupus --output json

# Start the API server (requires external services running)
devenv shell langnet-cli -- uvicorn-run --reload

# Query classical languages
devenv shell langnet-cli -- langnet-cli query lat lupus        # Latin: wolf
devenv shell langnet-cli -- langnet-cli query grc λόγος      # Greek: word
devenv shell langnet-cli -- langnet-cli query san agni        # Sanskrit: fire

# Check backend health (Heritage, Diogenes, Whitaker's Words)
devenv shell langnet-cli -- langnet-cli verify
```

## 📖 Documentation Navigation

### For New Users
- Start with **[GETTING_STARTED.md](GETTING_STARTED.md)** for installation and basic usage
- Read **[../README.md](../README.md)** for project overview
- Explore **[examples/](../examples/)** for practical usage examples

### For Developers
- **[DEVELOPER.md](DEVELOPER.md)** - Complete development guide with AI workflow
- **[technical/ARCHITECTURE.md](technical/ARCHITECTURE.md)** - Technical implementation details
- **[technical/opencode/](technical/opencode/)** - AI-assisted development patterns
- **[plans/](plans/)** - Current development plans and status

### For Researchers & Educators
- **[PEDAGOGICAL_PHILOSOPHY.md](PEDAGOGICAL_PHILOSOPHY.md)** - Educational philosophy and goals
- **[CITATIONS.md](CITATIONS.md)** - Sources and dependencies
- **[technical/](technical/)** - Detailed component information and technical references

### For API Users
- **[GETTING_STARTED.md](GETTING_STARTED.md)** - API usage and examples
- **[examples/](../examples/)** - API usage examples and demonstrations

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
- **Opencode Configuration**: Model routing and persona selection
- **Automated Testing**: Comprehensive test coverage with AI assistance

See **[../AGENTS.md](../AGENTS.md)** and **[technical/opencode/](technical/opencode/)** for complete AI development documentation.

## 📊 Project Status

- **State**: Actively developed; requires local Heritage, Diogenes, and Whitaker's Words services for most features.
- **Known gaps**: Diogenes sense extraction and CTS URN enrichment are flaky, Sanskrit canonicalization/DICO integration are incomplete, CDSL definitions often include SLP1 artifacts, and universal schema + fuzzy search are still in design (see `docs/plans/active/roadmap/TODO.md`).
- **Validation**: Tests and linting were not run during this audit; many suites depend on the external services above. Use `devenv shell langnet-cli -- just test` and `devenv shell langnet-cli -- just lint-all` once dependencies are available.
- **Planning**: Active plans live under `docs/plans/active/` with backlog items in `docs/plans/todo/`; roadmap/TODO are consolidated there (legacy files archived).

## 🆘 Getting Help

1. **Installation Issues**: Follow [GETTING_STARTED.md](GETTING_STARTED.md)
2. **Development Setup**: Follow [DEVELOPER.md](DEVELOPER.md)
3. **Technical Problems**: See [DEVELOPER.md](DEVELOPER.md) and [technical/ARCHITECTURE.md](technical/ARCHITECTURE.md)
4. **API Usage**: See [GETTING_STARTED.md](GETTING_STARTED.md)
5. **AI Development**: See [technical/opencode/](technical/opencode/) and [../AGENTS.md](../AGENTS.md)

## 📄 License

This project is licensed under the MIT License. See **[../LICENSE](../LICENSE)** for details.
