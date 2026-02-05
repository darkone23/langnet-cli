# Langnet CLI - Architecture & Technical Reference

This document provides a comprehensive technical overview of the langnet-cli architecture, implementation details, and system design.

## 🏗️ System Architecture

### High-Level Architecture
```
                        ┌─────────────────────┐
                        │   langnet-cli        │
                        │ (src/langnet/cli)   │
                        └──────────┬──────────┘
                                   │
                        ┌──────────▼──────────┐
                        │   langnet/asgi.py    │  ← Starlette ASGI app
                        │   /api/q endpoint    │
                        └──────────┬──────────┘
                                   │
                        ┌──────────▼──────────┐
                        │ LanguageEngine      │
                        │ (query routing)     │
                        └──────────┬──────────┘
                ┌────────────┬────┴────┬────────────┐
                │            │         │            │
     ┌──────────▼───┐ ┌──────▼──┐ ┌────▼────┐ ┌─────▼──────┐
     │ DiogenesScraper│ │Whitakers│ │Classics │ │Cologne    │
     │ (Greek/Latin) │ │ Words   │ │Toolkit  │ │(Sanskrit) │
     └───────────────┘ └─────────┘ └─────────┘ └───────────┘
            │              │          │            │
     ┌──────▼─────┐  ┌──────▼──┐ ┌────▼────┐ ┌────▼────┐
     │ DuckDB     │  │ whitakers│ │ CLTK    │ │ CDSL    │
     │ cache      │  │ -words   │ │ models  │ │ data    │
     └────────────┘  └─────────┘ └─────────┘ └─────────┘
```

### Core Components

#### 1. CLI Interface (`src/langnet/cli.py`)
- **Purpose**: Command-line interface and query routing
- **Key Functions**: 
  - `query()`: Main entry point for language queries
  - `citation_commands()`: Citation-related subcommands
  - `verify()`: Backend service health checks
- **Architecture**: Click-based CLI with argument parsing

#### 2. ASGI API (`src/langnet/asgi.py`)
- **Purpose**: Web API server for programmatic access
- **Framework**: Starlette with ORJSON for fast JSON serialization
- **Endpoint**: `/api?q=<query>&l=<lang>&s=<search>`
- **Features**: 
  - Response caching
  - Citation extraction and CTS URN mapping
  - Cross-backend result aggregation

#### 3. Language Engine (`src/langnet/engine/core.py`)
- **Purpose**: Central query coordinator and routing
- **Key Classes**:
  - `LanguageEngine`: Main query processor
  - `LanguageEngineConfig`: Backend configuration
  - `NormalizationPipeline`: Input preprocessing
- **Features**: 
  - Multi-backend aggregation
  - Error handling and fallbacks
  - Caching integration

#### 4. Backend Services

##### Diogenes (`src/langnet/diogenes/`)
- **Purpose**: Greek and Latin lexicon access
- **Source**: Perseus Digital Library data
- **API**: `http://localhost:8888`
- **Features**:
  - Lewis & Short (Latin)
  - Liddell & Scott (Greek)
  - Citation extraction with Perseus URNs
  - Foster functional grammar integration

##### Cologne Sanskrit (`src/langnet/cologne/`)
- **Purpose**: Sanskrit dictionary and morphology
- **Source**: CDSL (Cologne Digital Sanskrit Lexicon)
- **API**: `http://localhost:48080/sktreader`
- **Features**:
  - Multi-encoding support (Devanagari, IAST, Velthuis, etc.)
  - Morphological parsing
  - Root-based cross-references

##### Whitaker's Words (`src/langnet/whitakers_words/`)
- **Purpose**: Latin morphology and lemmatization
- **Binary**: `~/.local/bin/whitakers-words`
- **Features**:
  - Advanced morphological analysis
  - Dictionary headword lookup
  - Inflection pattern recognition

##### Classics Toolkit (`src/langnet/classics_toolkit/`)
- **Purpose**: Additional classical language utilities
- **Features**:
  - CLTK integration for Greek/Latin
  - Text processing utilities
  - Additional linguistic features

## 🔧 Data Models

### Core Query Model
```python
@dataclass
class CanonicalQuery:
    """Normalized query with validation"""
    raw_input: str
    normalized_input: str
    language: str
    is_bare: bool = False
    citations: List[Citation] = field(default_factory=list)
    # ... additional fields for processing metadata
```

### Citation System
```python
@dataclass
class Citation:
    """Standardized citation across all backends"""
    references: List[TextReference]
    short_title: Optional[str]
    full_name: Optional[str]
    description: Optional[str]
    created_at: datetime

@dataclass
class TextReference:
    """Individual text reference with location"""
    type: CitationType
    text: str
    work: Optional[str]
    author: Optional[str]
    book: Optional[str]
    line: Optional[str]
    cts_urn: Optional[str]
```

### Foster Functional Grammar
```python
class CitationType(str, Enum):
    """Comprehensive citation types with educational focus"""
    BOOK_REFERENCE = "book_reference"
    LINE_REFERENCE = "line_reference"
    DICTIONARY_ABBREV = "dictionary_abbreviation"
    # ... additional types for educational contexts
```

## 🔄 Data Flow

### Query Processing Pipeline
```
User Input → Normalization → Backend Routing → Result Aggregation → Response
    ↓            ↓              ↓              ↓              ↓
Raw Text   CanonicalQuery   Multi-backend   Combined      JSON/CLI
           Validation      Queries        Results       Output
```

### Citation Extraction Pipeline
```
Diogenes Response → Citation Extraction → CTS URN Mapping → API Response
     ↓                   ↓                      ↓              ↓
Perseus Format   Standardized Citations   Mapped URNs   Structured JSON
```

## 🌐 Encoding Support

### Greek (Betacode)
| Char | Example | Meaning |
|-----|---------|---------|
| `*` | `*a` | rough breathing |
| `\` | `a\` | smooth breathing |
| `/` | `a/` | iota subscript |
| `+` | `a+` | acute accent |
| `=` | `a=` | circumflex accent |
| `|` | `a|` | grave accent |

```bash
# Examples
langnet-cli query grc *ou=sia   # οὐσία (being)
langnet-cli query grc *qw=s     # πῶς (how?)
```

### Sanskrit (Multiple Encodings)
- **Devanagari**: `अग्नि` (agni - fire)
- **IAST**: `agni` (Romanized)
- **Velthuis**: `agni` (ASCII-friendly)
- **SLP1**: `Agfi` (Machine-readable)
- **HK**: `aG` (Harvard-Kyoto)
- **WX**: `a` (ITrans-II)

```bash
# Examples
langnet-cli query san agni        # IAST
langnet-cli query san अग्नि      # Devanagari
langnet-cli query san aGfi       # SLP1
```

### Latin (Standard)
- **Direct Latin**: `lupus`, `amor`, `arma`
- **Betacode Support**: For Greek borrowings

## 🗄️ Caching System

### DuckDB Integration
- **Location**: `~/.local/share/langnet/langnet-cache.duckdb`
- **Purpose**: Fast response caching with compression
- **Features**:
  - Automatic cache invalidation
  - Compressed storage
  - SQLite-compatible interface

### Cache Strategy
```python
# Cache key generation
cache_key = f"{language}:{normalized_input}:{hash(backend_config)}"

# Cache structure
CREATE TABLE responses (
    key TEXT PRIMARY KEY,
    response BLOB,
    created_at TIMESTAMP,
    access_count INTEGER
);
```

## 🔒 Error Handling

### Backend Fallback Strategy
```
Primary Backend → Fallback Backend → Local Processing → Error Response
     ↓              ↓                  ↓              ↓
   Diogenes     Whitaker's        CLTK Models    Clear Message
   Heritage      Words             (Greek/Latin)  with Suggestions
```

### Error Categories
1. **Service Unavailable**: Graceful degradation
2. **Network Timeout**: Retry with exponential backoff
3. **Data Corruption**: Fallback to alternative sources
4. **Invalid Input**: Clear error messages with suggestions

## 📊 Performance Optimization

### Caching Strategy
- **Response Caching**: DuckDB with compression
- **Backend Connection Pooling**: Reuse HTTP connections
- **Lazy Loading**: Load data only when needed
- **Parallel Processing**: Concurrent backend queries

### Memory Management
- **Stream Processing**: Large responses handled in chunks
- **Object Pooling**: Reuse dataclass instances
- **Garbage Collection**: Explicit cleanup for large operations

## 🧪 Testing Architecture

### Test Structure
```
tests/
├── unit/                    # Unit tests
├── integration/             # Integration tests  
├── fixtures/               # Test data
└── nose2.cfg               # Test configuration
```

### Test Categories
1. **Unit Tests**: Individual component testing
2. **Integration Tests**: Backend service integration
3. **End-to-End Tests**: Complete query flow
4. **Performance Tests**: Benchmarking and optimization

## 🤖 AI-Assisted Development

### Multi-Model Architecture
- **Personas**: 6 specialized AI assistants
  - Architect: System design and planning
  - Sleuth: Debugging and root cause analysis
  - Artisan: Code optimization and style
  - Coder: Feature implementation
  - Scribe: Documentation and comments
  - Auditor: Code review and security

### Development Workflow
1. **Planning**: Architect persona for high-level design
2. **Implementation**: Coder persona for feature development
3. **Debugging**: Sleuth persona for complex issues
4. **Review**: Auditor persona for quality assurance

## 🔧 Configuration

### Environment Variables
```bash
# Backend Services
DIOGENES_URL=http://localhost:8888
HERITAGE_URL=http://localhost:48080/sktreader
WHITAKERS_WORDS=~/.local/bin/whitakers-words

# Development
LANGNET_LOG_LEVEL=DEBUG
LANGNET_CACHE_DIR=~/.local/share/langnet
```

### Configuration Files
- **Project**: `pyproject.toml` (dependencies and scripts)
- **Development**: `.devenv/` (development environment)
- **Runtime**: Environment variables and defaults

## 📈 Monitoring & Observability

### Logging
```python
import structlog
logger = structlog.get_logger(__name__)

# Usage
logger.debug("Processing query", query=query, language=language)
logger.error("Backend timeout", backend="diogenes", error=error)
```

### Metrics
- **Query Processing Time**: Per-backend performance
- **Cache Hit Rate**: Optimization effectiveness
- **Error Rates**: Service reliability
- **User Activity**: Feature usage patterns

## 🔮 Future Enhancements

### Planned Architectural Improvements
1. **Microservices**: Containerized backend services
2. **GraphQL API**: More flexible query interface
3. **Real-time Updates**: WebSocket support for live data
4. **Horizontal Scaling**: Multi-instance deployment

### Performance Targets
- **Query Time**: <500ms for 95% of queries
- **Cache Hit Rate**: >80% for common queries
- **Memory Usage**: <100MB baseline, <1GB peak
- **Throughput**: 100+ queries per second

---

*For development setup and workflow, see [DEVELOPER.md](../DEVELOPER.md)*  
*For current status and roadmap, see [ROADMAP.md](../ROADMAP.md)*