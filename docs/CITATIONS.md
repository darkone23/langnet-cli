# Citations & Dependencies

## Core Dependencies

### Sanskrit Heritage Platform
> Gérard Huet. *Sanskrit Heritage Platform*. Digital Humanities Laboratory, INRIA. http://sanskrit.inria.fr/

**Purpose**: Primary Sanskrit morphological analyzer and dictionary  
**Integration**: HTTP API at `localhost:48080/sktreader`  
**Features**: Devanagari, IAST, Velthuis, SLP1, HK, ASCII encoding support

### Diogenes
> Peter Heslin. *Diogenes*. Department of Classics and Ancient History Durham University. https://d.iogen.es/d/

**Purpose**: Greek and Latin lexicon access (Perseus data)  
**Integration**: HTTP server at `localhost:8888`  
**Sources**: Lewis & Short (Latin), Liddell & Scott (Greek)  
**Features**: Citation extraction, CTS URN mapping, Foster grammar integration

### Whitaker's Words
> William Whitaker, Martin Keegan. *Whitaker's Words*. Latin morphological analyzer. https://mk270.github.io/whitakers-words/

**Purpose**: Latin morphological analysis and lemmatization  
**Integration**: Local binary at `~/.local/bin/whitakers-words`  
**Features**: Advanced Latin parsing, dictionary lookup, inflection recognition

### Classical Language Toolkit (CLTK)
> Kyle Johnson, Patrick Burns, Clément Besnier, et al.. *Classical Language Toolkit*. Version 1.23. https://github.com/cltk/cltk/

**Purpose**: Additional classical language utilities  
**Integration**: Automatic download to `~/cltk_data/` (~500MB)  
**Features**: Greek/Latin lemmatization, phonetic transcription, text processing

### Cologne Digital Sanskrit Dictionaries (CDSL)
> University of Cologne. *Cologne Digital Sanskrit Dictionaries*. http://www.sanskrit-lexicon.uni-koeln.de/

**Purpose**: Sanskrit dictionary data  
**Integration**: Automatic download to `~/cdsl_data/`  
**Sources**: Monier-Williams (MW), Apte (AP90), and other Sanskrit dictionaries

## Perseus Digital Library
> Crane, Gregory R., et al. *Perseus Digital Library*. Tufts University. http://www.perseus.tufts.edu/

**Purpose**: Source texts and citation data for Diogenes integration  
**Usage**: Citation extraction, text references, educational context

## Project Dependencies

### Runtime Dependencies
- **Starlette**: ASGI web framework for API server
- **Click**: CLI framework for command-line interface
- **duckdb**: Fast in-process analytical database for caching
- **structlog**: Structured logging for observability
- **cattrs**: Structured data serialization/deserialization

### Development Dependencies
- **ruff**: Fast Python linter and formatter
- **mypy**: Static type checking
- **nose2**: Test runner
- **requests**: HTTP client for backend integrations

## Installation Requirements

### External Services (Manual Installation Required)
1. **Sanskrit Heritage Platform**: Must be running at `localhost:48080`
2. **Diogenes**: Must be running at `localhost:8888`  
3. **Whitaker's Words**: Binary must be at `~/.local/bin/whitakers-words`

### Lexicon Downloads
1. **CLTK Models**: ~500MB downloaded on first use to `~/cltk_data/`
2. **CDSL Data**: Sanskrit dictionaries downloaded to `~/cdsl_data/`

## Configuration

See [GETTING_STARTED.md](GETTING_STARTED.md) for installation and setup instructions.

## License Compliance

All external dependencies are used in compliance with their respective licenses:
- Sanskrit Heritage Platform: GNU GPL v3
- Diogenes: GNU GPL v3
- Whitaker's Words: GNU GPL v3
- CLTK: MIT License
- CDSL: Various open licenses (see individual dictionary licenses)

This project is licensed under MIT License - see [../LICENSE](../LICENSE).

### A note on data provenance

This project employs a **distillation architecture**.

While the source code of this repository is original and licensed under the permissive **MIT License**, the linguistic data and analytical "facts" contained herein were generated or verified using the following foundational tools:

* **Sanskrit Heritage System:** Used for morphological analysis (GPL v2+).
* **Whitaker’s Words:** Used for Latin lexical verification (Public Domain).
* **Diogenes:** Used for source text browsing and verification (GPL v2+).
* **CLTK (Classical Language Toolkit):** Used for NLP processing (MIT).

The data produced by this project consists of linguistic facts (morphology, syntax, and lexical definitions) which are not subject to copyright and are made explicitly available for public education.

This project does not include, bundle, or modify the source code of the GPL-licensed tools listed above.

---

