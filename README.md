# langnet-cli

A command-line tool for querying classical language lexicons and morphology to supplement your language study practice.

## Language Resources

| Source | Latin | Greek | Sanskrit | What It Provides |
|--------|-------|-------|----------|------------------|
| Diogenes (Perseus) | ✓ | ✓ | - | Lexicon entries + morphological analysis from Lewis & Short, Liddell & Scott |
| Whitaker's Words | ✓ | - | - | Detailed morphological parsing for Latin words |
| CLTK | ✓ | - | ✓ | Additional lexicons, lemmatization, and linguistic features |
| CDSL (Cologne) | - | - | ✓ | Sanskrit dictionaries: Monier-Williams, Apte, AP90 |

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

This tool requires two external services to be installed separately:

1. **diogenes** - Perl server for Perseus lexicon data
   - Repository: https://github.com/pjheslin/diogenes
   - Run at `http://localhost:8888`
   - Required for Greek/Latin dictionary queries

2. **whitakers-words** - Latin morphological analyzer
   - Binary: `~/.local/bin/whitakers-words`
   - Prebuilt x86_64 binaries available

### Automatic Dependencies

These are downloaded/installed automatically when needed:
- **CLTK models**: Installed to `~/cltk_data/` (~500MB on first use)
- **CDSL data**: Sanskrit dictionaries in `~/cdsl_data/`

## Further Reading

- [DEVELOPER.md](DEVELOPER.md) - Development setup and code conventions
- [AGENTS.md](AGENTS.md) - AI agent instructions and opencode skills
- [.opencode/skills/](.opencode/skills/) - Opencode development skills for contributors

## Opencode Support

This project includes opencode skills for AI-assisted development. See [DEVELOPER.md](DEVELOPER.md#using-opencode) for usage instructions and [`.opencode/skills/README.md`](.opencode/skills/README.md) for available skills.

For LLM provider configuration, see [LLM_PROVIDER_GUIDE.md](LLM_PROVIDER_GUIDE.md).
