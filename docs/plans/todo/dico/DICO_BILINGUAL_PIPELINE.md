# DICO Bilingual Pipeline Documentation

## Overview

This pipeline aims to create a comprehensive bilingual Sanskrit dictionary by:

1. **Importing DICO data** from Sanskrit Heritage Platform into a local DuckDB index
2. **Creating OpenAI-powered views** to translate French definitions to English
3. **Generating twin databases**: `DICO_fr` (original French) and `DICO_en` (English translation)

## Pipeline Architecture

```
Sanskrit Heritage DICO
         ↓
   Import & Index (DuckDB)
         ↓
   French Definitions View
         ↓
   OpenAI Translation
         ↓
   English Definitions View
         ↓
   Twin Database Output
   ├── DICO_fr (French)
   └── DICO_en (English)
```

## Phase 1: DICO Data Import Pipeline

### 1.1 Heritage Platform Integration

**Target**: Sanskrit Heritage DICO database via CGI scripts
**Base URL**: `http://localhost:48080/cgi-bin/skt/sktindex`
**Parameters**: 
- `lex`: DICO
- `q`: search term
- `t`: encoding (velthuis)

**End Points**:
- Search: `/cgi-bin/skt/sktindex?lex=DICO&q={term}&t=VH`
- Entry: `/cgi-bin/skt/sktreader?text={term}&lex=DICO&t=VH`

### 1.2 Data Schema Design

```sql
-- Main DICO table (French)
CREATE TABLE dico_fr (
    id INTEGER PRIMARY KEY,
    headword TEXT NOT NULL,
    sanskrit TEXT NOT NULL,
    french_definition TEXT NOT NULL,
    devanagari TEXT,
    iast TEXT,
    slp1 TEXT,
    velthuis TEXT,
    page_number INTEGER,
    column_number INTEGER,
    source_references TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- English translation table
CREATE TABLE dico_en (
    id INTEGER PRIMARY KEY,
    headword TEXT NOT NULL,
    sanskrit TEXT NOT NULL,
    english_definition TEXT NOT NULL,
    french_definition TEXT NOT NULL, -- Reference to original
    devanagari TEXT,
    iast TEXT,
    slp1 TEXT,
    velthuis TEXT,
    page_number INTEGER,
    column_number INTEGER,
    source_references TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 1.3 Import Strategy

**Approach**: Batch processing with incremental updates

```python
class DicoImporter:
    def __init__(self, heritage_client, duckdb_connection):
        self.heritage_client = heritage_client
        self.db_conn = duckdb_connection
        
    def import_all_entries(self, batch_size=1000):
        """Import all DICO entries from Heritage Platform"""
        
    def import_by_headword_range(self, start_letter, end_letter):
        """Import entries by alphabetical range"""
        
    def import_entry_details(self, headword):
        """Import detailed entry information"""
        
    def save_to_duckdb(self, entries):
        """Save batch to DuckDB with conflict resolution"""
```

## Phase 2: OpenAI Translation Pipeline

### 2.1 OpenAI Integration Strategy

**Model**: GPT-4 or GPT-3.5-turbo for translation
**Prompt Engineering**: Context-aware translation preserving technical Sanskrit terms

```python
class OpenAITranslator:
    def __init__(self, api_key, model="gpt-4"):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        
    def translate_definition(self, french_text, sanskrit_context):
        """
        Translate French definition to English with Sanskrit context
        
        Args:
            french_text: French definition from DICO
            sanskrit_context: Sanskrit headword and related terms
            
        Returns:
            English translation
        """
        
    def batch_translate(self, definitions, batch_size=10):
        """Translate multiple definitions efficiently"""
        
    def validate_translation(self, original, translation):
        """Validate translation quality"""
```

### 2.2 Translation Prompt Template

```python
TRANSLATION_PROMPT = """
You are a Sanskrit scholar specializing in translating French DICO dictionary entries to English.

SANSKRIT CONTEXT: {sanskrit_context}
FRENCH DEFINITION: {french_text}

INSTRUCTIONS:
1. Translate the French definition to natural, scholarly English
2. Preserve all Sanskrit terms in their original form
3. Maintain technical accuracy and scholarly tone
4. Keep the structure and meaning intact
5. Add brief clarifications only if essential for understanding

RESPONSE FORMAT:
- Provide only the English translation
- No additional commentary or explanation
- Preserve formatting and structure

ENGLISH TRANSLATION:
"""
```

## Phase 3: Database Pipeline Implementation

### 3.1 Pipeline Orchestration

```python
class DicoBilingualPipeline:
    def __init__(self, config):
        self.config = config
        self.heritage_client = HeritageHTTPClient()
        self.db_conn = self._init_duckdb()
        self.translator = OpenAITranslator(config.openai_api_key)
        
    def run_full_pipeline(self):
        """Execute complete pipeline: import → translate → index"""
        
    def run_incremental_update(self, since_date):
        """Run incremental updates since specified date"""
        
    def create_views(self):
        """Create materialized views for common queries"""
        
    def export_databases(self, format="parquet"):
        """Export twin databases for distribution"""
```

### 3.2 View Creation Strategy

```sql
-- French definitions view
CREATE MATERIALIZED VIEW dico_fr_view AS
SELECT 
    id,
    headword,
    sanskrit,
    french_definition,
    devanagari,
    iast,
    slp1,
    page_number,
    source_references
FROM dico_fr
ORDER BY headword;

-- English translations view (dynamically generated)
CREATE MATERIALIZED VIEW dico_en_view AS
SELECT 
    d.id,
    d.headword,
    d.sanskrit,
    t.english_definition,
    d.french_definition,
    d.devanagari,
    d.iast,
    d.slp1,
    d.page_number,
    d.source_references,
    t.translation_quality,
    t.processed_at
FROM dico_fr d
LEFT JOIN translations t ON d.id = t.dico_id
ORDER BY d.headword;
```

## Phase 4: Quality Assurance & Monitoring

### 4.1 Data Validation

```python
class PipelineValidator:
    def validate_heritage_response(self, response):
        """Validate Heritage Platform response structure"""
        
    def validate_translation_quality(self, original, translation):
        """Assess translation quality metrics"""
        
    def validate_database_integrity(self):
        """Ensure referential integrity between databases"""
        
    def generate_quality_report(self):
        """Generate comprehensive quality assessment"""
```

### 4.2 Monitoring & Logging

```python
class PipelineMonitor:
    def track_import_progress(self, total_entries, processed):
        """Track import progress"""
        
    def track_translation_costs(self, total_tokens, cost):
        """Track OpenAI API costs"""
        
    def monitor_error_rates(self, error_count, total_operations):
        """Monitor pipeline error rates"""
        
    def generate_usage_report(self):
        """Generate pipeline usage statistics"""
```

## Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
- [ ] Set up DuckDB database schema
- [ ] Implement Heritage Platform client
- [ ] Create basic import functionality
- [ ] Test with sample DICO entries

### Phase 2: Translation Engine (Week 3-4)
- [ ] Implement OpenAI integration
- [ ] Develop translation prompt engineering
- [ ] Create batch processing system
- [ ] Validate translation quality

### Phase 3: Pipeline Integration (Week 5-6)
- [ ] Orchestrate complete pipeline
- [ ] Implement error handling and retries
- [ ] Create monitoring and logging
- [ ] Set up automated scheduling

### Phase 4: Production Ready (Week 7-8)
- [ ] Performance optimization
- [ ] Quality assurance testing
- [ ] Documentation and deployment
- [ ] User interface for management

## Technical Specifications

### Dependencies
- `duckdb` - Local database
- `openai` - Translation service
- `requests` - Heritage Platform API
- `pandas` - Data processing
- `structlog` - Logging
- `pydantic` - Data validation

### Configuration
```python
PipelineConfig = {
    "heritage": {
        "base_url": "http://localhost:48080",
        "timeout": 30,
        "max_retries": 3
    },
    "openai": {
        "model": "gpt-4",
        "batch_size": 10,
        "temperature": 0.1
    },
    "database": {
        "path": "./dico_bilingual.duckdb",
        "batch_size": 1000
    },
    "monitoring": {
        "log_level": "INFO",
        "enable_cost_tracking": True
    }
}
```

## Expected Outcomes

### Databases
- **DICO_fr**: Complete French dictionary with ~15,000+ entries
- **DICO_en**: English translation dictionary with matching entries

### Features
- Bilingual search capabilities
- Cross-referenced entries
- Quality scoring for translations
- Incremental update support
- Export functionality

### Benefits
- Offline access to complete bilingual dictionary
- Preserves original French scholarship
- Provides English accessibility
- Structured data for applications
- Cost-effective local storage

## Risk Assessment

### Technical Risks
- **Heritage Platform downtime**: Implement retry logic and caching
- **OpenAI API limits**: Implement batching and cost monitoring
- **Data quality**: Implement validation and monitoring

### Quality Risks
- **Translation accuracy**: Implement validation and review process
- **Data completeness**: Implement comprehensive logging and verification
- **Performance**: Implement batch processing and optimization

This pipeline will create a valuable bilingual resource for Sanskrit scholars while maintaining data integrity and providing robust functionality for research and applications.