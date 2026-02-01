# langnet-cli

A command-line tool for querying classical language lexicons and morphology to supplement your language study practice.

## Language Resources

| Source | Latin | Greek | Sanskrit | What It Provides |
|--------|-------|-------|----------|------------------|
| **Sanskrit Heritage Platform** | - | - | ✓ | Advanced morphological analysis, lemmatization, dictionary definitions |
| **Diogenes (Perseus)** | ✓ | ✓ | - | Lexicon entries + morphological analysis from Lewis & Short, Liddell & Scott |
| **Whitaker's Words** | ✓ | - | - | Detailed morphological parsing for Latin words |
| **CLTK** | ✓ | - | ✓ | Additional lexicons, lemmatization, and linguistic features |
| **CDSL (Cologne)** | - | - | ✓ | Sanskrit dictionaries: Monier-Williams, Apte, AP90 |

## Quick Start

```sh
# Enter development environment
devenv shell

# Start the API server
uvicorn-run

# Look up a Latin word
langnet-cli query lat lupus

# Look up a Greek word
langnet-cli query grc λόγος

# Look up a Sanskrit word
langnet-cli query san agni

# Check which backends are available
langnet-cli verify
```

## Technical Notes

### External Dependencies

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

These are downloaded/installed automatically when needed:
- **CLTK models**: Installed to `~/cltk_data/` (~500MB on first use)
- **CDSL data**: Sanskrit dictionaries in `~/cdsl_data/`

## Further Reading

### 📚 Complete Documentation

For comprehensive documentation, see the **[docs/](docs/)** directory:

- **[docs/README.md](docs/README.md)** - Complete documentation hub and navigation guide
- **[docs/TODO.md](docs/TODO.md)** - Current roadmap, active development, and priorities
- **[docs/DEVELOPER.md](docs/DEVELOPER.md)** - Development setup, conventions, and AI workflow
- **[docs/REFERENCE.md](docs/REFERENCE.md)** - Technical reference, architecture, and implementation details
- **[docs/PEDAGOGICAL_PHILOSOPHY.md](docs/PEDAGOGICAL_PHILOSOPHY.md)** - Core educational approach and Foster functional grammar
- **[docs/PEDAGOGY.md](docs/PEDAGOGY.md)** - Pedagogical goals and priorities

### Quick Links

- **[AGENTS.md](AGENTS.md)** - AI agent instructions and opencode skills
- **[docs/plans/](docs/plans/)** - Project plans (active, completed, todo)
- **[.opencode/skills/](.opencode/skills/)** - Opencode development skills for contributors

## Opencode Support

This project includes opencode skills for AI-assisted development. See [docs/DEVELOPER.md](docs/DEVELOPER.md#using-opencode) for usage instructions and [`.opencode/skills/README.md`](.opencode/skills/README.md) for available skills.

For LLM provider configuration, see [./docs/opencode/LLM_PROVIDER_GUIDE.md](docs/opencode/LLM_PROVIDER_GUIDE.md).

## 📋 Development Status

**Current Status**: ~75% Complete - Well-architected codebase with core functionality working

**Key Achievements**:
- ✅ Foster Functional Grammar across all three languages
- ✅ Comprehensive lemmatization system
- ✅ Multi-encoding support (Sanskrit: Devanagaria, IAST, Velthuis, SLP1; Greek: Betacode)
- ✅ Robust caching and normalization pipeline
- ✅ AI-assisted development workflow with 6 personas
- ✅ **Sanskrit Heritage Platform Integration** - Complete with Lark parser

**Core Dependencies**:
- **Sanskrit Heritage Platform**: Required for Sanskrit functionality (localhost:48080)
- **Diogenes**: Required for Greek/Latin functionality (localhost:8888)
- **Whitaker's Words**: Required for Latin morphology
- **CLTK/CDSL**: Automatic downloads for additional features

**Active Development**:
- Enhanced citation display and formatting
- Fuzzy search for user experience
- DICO French-Sanskrit dictionary integration
- Universal schema data model

See [docs/TODO.md](docs/TODO.md) for detailed roadmap and current priorities.

## 🏗️ Technical Architecture

```
langnet-cli
├── Sanskrit Heritage Platform (external)
│   ├── Morphological analysis
│   ├── Dictionary lookup  
│   └── Encoding detection
├── Diogenes (external)
│   ├── Greek/Latin lexicons
│   └── Morphological parsing
├── Whitaker's Words (external)
│   └── Latin morphology
├── Internal Modules
│   ├── Foster Functional Grammar
│   ├── Normalization Pipeline
│   ├── Query Engine
│   └── Response Caching
└── AI-Assisted Development
    └── Multi-model personas
```

For comprehensive technical documentation, see [docs/CITATIONS.md](docs/CITATIONS.md).
