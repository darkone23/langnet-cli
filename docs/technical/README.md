# Component Documentation

This directory contains README files for individual components within the langnet-cli codebase. Each component README provides detailed information about a specific module or service.

## Available Components

### Language Processing Backends
- **[backend/README.md](backend/README.md)** - Index for backend docs (engine, Diogenes, Cologne, Whitaker's Words)
- **[MAINTAINABILITY_STATUS.md](MAINTAINABILITY_STATUS.md)** - Consolidated status for maintainability/decoupling

## Component Overview

### Language Processing Pipeline
The langnet-cli system processes queries through a multi-backend pipeline:

1. **Language Detection**: Determines the target language (Latin, Greek, Sanskrit)
2. **Backend Selection**: Routes to appropriate language-specific processors
3. **Query Processing**: Each backend handles morphological analysis and dictionary lookup
4. **Result Aggregation**: Combines results from multiple backends
5. **Educational Rendering**: Applies Foster functional grammar and formatting

### Backend Responsibilities
- **Classics Toolkit (CLTK)**: Computational linguistics, lemmatization, phonetic transcription
- **Cologne**: Sanskrit dictionary lookup and lexical analysis
- **Diogenes**: Classical text citations and Perseus integration
- **Engine**: Core routing, normalization, and result aggregation
- **Whitaker's Words**: Latin morphological parsing and dictionary definitions

## Integration Points

### Core System Integration
- **LanguageEngine**: Central router that coordinates all backends
- **Normalization**: Standardizes input queries across languages
- **Caching**: DuckDB-based response caching for performance
- **API**: Starlette ASGI API provides web interface

### Cross-Component Dependencies
- **Input**: Raw user queries (words or phrases)
- **Output**: Structured results with morphological analysis, definitions, and educational context
- **Shared Models**: Dataclass models ensure consistent data structures across components

## Development Guidelines

### When Working with Components
1. **Read the component README** first to understand capabilities and limitations
2. **Check integration points** for how the component fits into the larger system
3. **Follow existing patterns** for data models and error handling
4. **Update documentation** when making changes to component behavior
5. **Test thoroughly** with real language examples

### Adding New Components
1. **Create a new README** in this directory following the existing format
2. **Define clear interfaces** for input/output data structures
3. **Implement proper error handling** and logging
4. **Add integration tests** to verify component functionality
5. **Update the main architecture documentation** if needed

## Related Documentation

- **[README.md](../README.md)** - Main project documentation hub
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture and component relationships
- **[../DEVELOPER.md](../DEVELOPER.md)** - Developer guide and setup instructions
- **[../GETTING_STARTED.md](../GETTING_STARTED.md)** - Getting started guide

## Quick Reference

For developers working with components:
- **Backend Integration**: See [DEVELOPER.md](../DEVELOPER.md) section on adding new backends
- **Data Models**: Check `src/langnet/schema.py` for core dataclasses
- **Testing**: See [../tests/README.md](../tests/README.md) for test structure
- **API Development**: See [ARCHITECTURE.md](ARCHITECTURE.md) for API design
