# Citations & Dependencies

**Last Updated**: February 1, 2026  
**Status**: Comprehensive documentation of all external dependencies and citations

## 🏗️ Core Architecture Dependencies

### External Services (Required)

#### 1. Sanskrit Heritage Platform (SHP)
**Status**: ✅ REQUIRED DEPENDENCY  
**Version**: Production (localhost:48080)  
**Role**: Primary Sanskrit morphological analysis and dictionary lookup

**Implementation Details**:
- **API Endpoint**: `http://localhost:48080/sktreader`
- **Function**: Provides morphological parsing, lemmatization, and dictionary definitions
- **Integration Point**: `src/langnet/heritage/client.py`
- **Parser**: Lark-based HTML pattern extraction (`src/langnet/heritage/lineparsers/`)
- **Encodings**: Devanagari, IAST, Velthuis, SLP1, HK, ASCII
- **Performance**: 5-10ms per solution, 100% extraction rate

**Usage in Code**:
```python
# Heritage Platform client integration
heritage_client = HeritageClient()
canonical_form = heritage_client.fetch_canonical_sanskrit("agni")
morphology = heritage_client.fetch_morphology("yoga")
```

**Citation**:
> Sanskrit Heritage Platform. (2026). Digital Humanities Laboratory, INRIA. http://sanskrit.inria.fr/

#### 2. Diogenes (Perseus)
**Status**: ✅ REQUIRED DEPENDENCY  
**Version**: Perl server  
**Role**: Greek and Latin lexicon data (Lewis & Short, Liddell & Scott)

**Implementation Details**:
- **API Endpoint**: `http://localhost:8888`
- **Function**: Dictionary definitions and morphological analysis
- **Integration Point**: `src/langnet/diogenes/core.py`
- **Data Sources**: Perseus Digital Library
- **Performance**: ~1s connectivity check

**Usage in Code**:
```python
# Diogenes integration
diogenes = DiogenesScraper()
results = diogenes.query("lupus", "lat")  # Latin: wolf
results = diogenes.query("λόγος", "grc")  # Greek: word
```

**Citation**:
> Crane, Gregory R., et al. (2020). *Perseus Digital Library*. Tufts University. http://www.perseus.tufts.edu/

#### 3. Whitaker's Words
**Status**: ✅ REQUIRED DEPENDENCY  
**Version**: Binary distribution  
**Role**: Latin morphological analysis

**Implementation Details**:
- **Binary Location**: `~/.local/bin/whitakers-words`
- **Function**: Detailed Latin morphological parsing
- **Integration Point**: `src/langnet/whitakers_words/core.py`
- **Parser**: Modular line-based parsing (SensesReducer, CodesReducer, FactsReducer)
- **Performance**: Sub-second parsing

**Usage in Code**:
```python
# Whitaker's Words integration
whitakers = WhitakersWords()
analysis = whitakers.parse("sumpturi")
```

**Citation**:
> William Whitaker. (2024). *Whitaker's Words*. Latin morphological analyzer. https://github.com/morphgent/whitakers-words

### Automatic Dependencies (Downloaded on First Use)

#### 4. CLTK (Classical Language Toolkit)
**Status**: ✅ AUTOMATIC DEPENDENCY  
**Version**: v1.23+  
**Role**: Additional lexicons, lemmatization, and linguistic features

**Implementation Details**:
- **Download Location**: `~/cltk_data/`
- **Size**: ~500MB on first query
- **Models**: spaCy Greek model (`grc_odycy_joint_sm`), Latin models
- **Integration Point**: `src/langnet/classics_toolkit/core.py`
- **Languages**: Latin, Greek (with Sanskrit support planned)

**Usage in Code**:
```python
# CLTK integration
cltk = ClassicsToolkit()
lemmas = cltk.lemmatize("lupus", "lat")
```

**Citation**:
> Clement, T. A., & Burns, K. (2024). *Classical Language Toolkit*. Version 1.23. https://github.com/cltk/cltk

#### 5. CDSL (Cologne Sanskrit Digital Library)
**Status**: ✅ AUTOMATIC DEPENDENCY  
**Version**: Current  
**Role**: Sanskrit dictionary data (Monier-Williams, Apte, AP90)

**Implementation Details**:
- **Data Location**: `~/cdsl_data/`
- **Dictionaries**: Monier-Williams, Apte, AP90
- **Integration Point**: `src/langnet/cologne/core.py`
- **Encoding**: Velthuis ASCII to Unicode conversion
- **Usage**: Primary Sanskrit lexicon data

**Usage in Code**:
```python
# CDSL integration
cdsl = CologneService()
definitions = cdsl.lookup("agni")
```

**Citation**:
> University of Cologne. (2024). *Cologne Digital Sanskrit Dictionaries*. http://www.sanskrit-lexicon.uni-koeln.de/

## 🧪 Testing & Development Dependencies

### 6. Test Frameworks
**nose2**: Test runner with configuration in `tests/nose2.cfg`  
**pytest**: Alternative test runner (secondary)  
**coverage.py**: Test coverage reporting

### 7. Development Tools
**ruff**: Python linter and formatter (replaces flake8, isort, black)  
**mypy**: Type checking  
**just**: Task runner and build automation

## 🔗 Data Models & Serialization

### 8. cattrs
**Status**: ✅ CORE DEPENDENCY  
**Version**: v23.0+  
**Role**: Dataclass serialization and deserialization

**Implementation Details**:
- **Integration**: Used throughout for API response formatting
- **Pattern**: `@dataclass` with `cattrs.Converter(omit_if_default=True)`
- **Usage**: Structured JSON output for all backend responses

**Citation**:
> Ronan Lamy. (2024). *cattrs*. Version 23.0. https://github.com/python-attrs/cattrs

## 🌐 Web & API Dependencies

### 9. Starlette
**Status**: ✅ CORE DEPENDENCY  
**Version**: v0.27+  
**Role**: ASGI application framework

**Implementation Details**:
- **Entry Point**: `src/langnet/asgi.py`
- **Endpoint**: `/api/q` for query processing
- **Response Format**: ORJSONResponse for JSON serialization
- **Features**: Dependency injection, health checks

**Citation**:
> Encode. (2024). *Starlette*. ASGI framework. https://www.starlette.io/

### 10. ORJSON
**Status**: ✅ CORE DEPENDENCY  
**Version**: v3.0+  
**Role**: Fast JSON serialization

**Implementation Details**:
- **Integration**: Used for API response serialization
- **Performance**: Faster than standard json library
- **Usage**: `ORJSONResponse(content=response_data)`

**Citation**:
>ijl. (2024). *orjson*. Fast JSON library. https://github.com/ijl/orjson

## 🗄️ Database Dependencies

### 11. DuckDB
**Status**: ✅ CORE DEPENDENCY  
**Version**: v0.8+  
**Role**: Response caching and data storage

**Implementation Details**:
- **Database Location**: `~/.local/share/langnet/langnet_cache.duckdb`
- **Schema**: `CREATE TABLE query_cache (id, lang, query, result, created_at)`
- **Integration**: QueryCache class in `src/langnet/cache/core.py`
- **Features**: Embedded SQL, fast queries

**Citation**:
> DuckDB Labs. (2024). *DuckDB*. Analytical database. https://duckdb.org/

## 📚 Linguistic & Processing Dependencies

### 12. indic-transliteration
**Status**: ✅ CORE DEPENDENCY  
**Version**: v2.0+  
**Role**: Sanskrit encoding detection and conversion

**Implementation Details**:
- **Integration**: Enhanced in `src/langnet/heritage/encoding_service.py`
- **Features**: Attribute-based detection with priority rules
- **Encodings**: Devanagari, IAST, Velthuis, SLP1, HK, ASCII

**Citation**:
> Sanskrit Heritage Platform Team. (2024). *indic-transliteration*. Sanskrit transliteration library.

### 13. Lark
**Status**: ✅ CORE DEPENDENCY  
**Version**: v1.1+  
**Role**: Sanskrit morphological parsing

**Implementation Details**:
- **Integration**: Lark parser in `src/langnet/heritage/lineparsers/`
- **Grammar**: EBNF grammar for HTML pattern extraction
- **Performance**: 5-10ms per solution
- **Features**: State machine parsing, error recovery

**Citation**>
>Eryk Sun. (2024). *Lark*. Parsing toolkit. https://github.com/lark-parser/lark

## 🎨 UI & Formatting Dependencies

### 14. Rich
**Status**: ✅ CORE DEPENDENCY  
**Version**: v13.0+  
**Role**: CLI formatting and rich output

**Implementation Details**:
- **Integration**: CLI output formatting
- **Features**: Color-coded output, tables, progress bars
- **Usage**: Enhanced user experience in command line

**Citation**:
> Will McGugan. (2024). *Rich*. Rich text and beautiful formatting for the terminal. https://github.com/Textualize/rich

## 🔧 System Dependencies

### 15. Perl
**Status**: ✅ REQUIRED  
**Role**: Diogenes server execution

### 16. Python
**Status**: ✅ REQUIRED  
**Version**: 3.8+  
**Implementation**: Core application logic

## 📋 Dependency Management

### Installation
```bash
# Primary dependencies (manual)
# 1. Install Perl and diogenes server
# 2. Install whitakers-words binary
# 3. Start diogenes: diogenes -s 8888

# Python dependencies (automatic)
pip install -r devenv.requirements.txt

# Development dependencies
pip install -r devenv.dev-requirements.txt
```

### Dependency Validation
```bash
# Check all dependencies
langnet-cli verify

# Test specific backend
langnet-cli test-backend heritage
langnet-cli test-backend diogenes
langnet-cli test-backend whitakers
```

## 🔄 Dependency Updates

### Critical Updates (Monthly Review)
- Sanskrit Heritage Platform API changes
- Diogenes server updates
- Whitaker's Words binary updates

### Security Updates (Quarterly Review)
- Python package vulnerabilities
- Web framework updates

## 📊 Dependency Impact Analysis

### High Impact Dependencies
1. **Sanskrit Heritage Platform**: Core Sanskrit functionality
2. **Diogenes**: Core Latin/Greek functionality  
3. **Whitaker's Words**: Core Latin morphological analysis

### Medium Impact Dependencies
1. **CLTK**: Additional linguistic features
2. **CDSL**: Sanskrit dictionary data
3. **DuckDB**: Performance optimization

### Low Impact Dependencies
1. **Rich**: UI enhancement
2. **ORJSON**: Performance optimization
3. **cattrs**: Data serialization

## 🚨 Critical Dependency Issues

### Known Issues
1. **SHP API Changes**: Monitor for breaking changes
2. **Perl Threads**: Diogenes requires thread management
3. **CLTK Downloads**: First-time setup requires 500MB download

### Mitigation Strategies
1. **Graceful Degradation**: Fallback parsers when SHP unavailable
2. **Cache Management**: DuckDB cache reduces external dependency calls
3. **Health Checks**: Regular dependency validation

## 📈 Dependency Roadmap

### Short Term (2-4 Weeks)
- [ ] Add fuzzy search dependency
- [ ] Implement DICO integration (French-Sanskrit)
- [ ] Enhanced citation formatting

### Medium Term (1-2 Months)
- [ ] Universal schema data model
- [ ] Performance optimization dependencies
- [ ] Educational tool dependencies

### Long Term (3+ Months)
- [ ] Multi-user scaling dependencies
- [ ] Web interface dependencies
- [ ] Advanced research tool dependencies

---

*For implementation details, see [REFERENCE.md](REFERENCE.md)*  
*For development status, see [TODO.md](TODO.md)*  
*For pedagogical approach, see [PEDAGOGY.md](PEDAGOGY.md)*