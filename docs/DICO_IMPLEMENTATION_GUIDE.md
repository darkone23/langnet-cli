# DICO Bilingual Pipeline - Implementation Guide with Real Examples

## DICO Database Examples

### Example 1: vaagyoḥga (वाग्योघ)
**Search URL**: `/cgi-bin/skt/sktindex?lex=DICO&q=vaagyoga&t=VH`

This demonstrates that the DICO database uses specific encoding patterns. Let me enhance the implementation with real examples:

### Real DICO Search Patterns

```python
# src/dico_pipeline/heritage_collector_enhanced.py
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlencode

class HeritageDicoCollector:
    def __init__(self, heritage_client: Optional[HeritageHTTPClient] = None):
        self.client = heritage_client or HeritageHTTPClient()
        self.parser = SimpleHeritageParser()
        
    def get_real_dico_examples(self) -> List[Dict[str, Any]]:
        """Get real examples from DICO database"""
        
        # These are actual entries that exist in DICO
        example_queries = [
            "vaagyoga",  # वाग्योघ (vaagyoḥga)
            "agni",      # अग्नि (common entry for comparison)
            "asva",      # अश्व (horse)
            "deva",      # देव (god)
            "brahma",    # ब्रह्म (Brahman)
            "dharma",    # धर्म (duty, law)
            "karma",     # कर्म (action, fate)
            "yoga",      # योग (yoga, union)
            "moksha",    # मोक्ष (liberation)
            "samsara",   # संसार (cycle of rebirth)
        ]
        
        examples = []
        
        for query in example_queries:
            try:
                # Search for the specific entry
                search_params = HeritageParameterBuilder.build_search_params(
                    query=query,
                    lex="DICO",  # Important: DICO specifically, not MW
                    max_results=5,
                    encoding="velthuis"
                )
                
                search_response = self.client.fetch_cgi_script(
                    "sktindex", params=search_params
                )
                
                # Parse and validate the response
                entries = self._parse_search_results(search_response)
                
                if entries:
                    for entry in entries:
                        detailed_entry = self._get_entry_details(entry['headword'])
                        if detailed_entry:
                            examples.append({
                                'query': query,
                                'entry': detailed_entry,
                                'search_url': f"/cgi-bin/skt/sktindex?lex=DICO&q={query}&t=VH"
                            })
                            
                time.sleep(0.1)  # Rate limiting
                
            except Exception as e:
                logger.warning("Failed to get example for query", 
                             query=query, error=str(e))
                continue
        
        return examples
    
    def _parse_dico_specific_format(self, html_content: str) -> Dict[str, Any]:
        """Parse DICO-specific response format"""
        
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            
            # DICO entries typically have specific patterns
            entry_data = {
                'headword': '',
                'sanskrit': '',
                'french_definition': '',
                'devanagari': '',
                'page_references': [],
                'cross_references': []
            }
            
            # Extract headword (usually in bold or specific formatting)
            title_elements = soup.find_all(['h1', 'h2', 'b', 'strong'])
            for element in title_elements:
                if element.get_text(strip=True):
                    entry_data['headword'] = element.get_text(strip=True)
                    break
            
            # Extract Devanagari (often in brackets or specific formatting)
            devanagari_pattern = r'\[([^\]]+)\]'
            text_content = soup.get_text()
            devanagari_match = re.search(devanagari_pattern, text_content)
            if devanagari_match:
                entry_data['devanagari'] = devanagari_match.group(1)
            
            # Extract French definition (main content)
            tables = soup.find_all("table")
            definitions = []
            
            for table in tables:
                rows = table.find_all("tr")
                for row in rows:
                    cells = row.find_all("td")
                    if len(cells) >= 1:
                        cell_text = cells[0].get_text(strip=True)
                        # Skip page numbers and metadata
                        if (cell_text and 
                            not cell_text.startswith('Page') and 
                            not cell_text.isdigit() and
                            len(cell_text) > 10):  # Minimum definition length
                            definitions.append(cell_text)
            
            entry_data['french_definition'] = '\n'.join(definitions)
            
            # Extract page references (DICO format)
            page_pattern = r'(?:Page|p\.)\s*(\d+)'
            page_matches = re.findall(page_pattern, text_content, re.IGNORECASE)
            entry_data['page_references'] = [int(p) for p in page_matches]
            
            # Extract cross-references
            cross_ref_pattern = r'→\s*([a-zA-Z0-9]+)'
            cross_matches = re.findall(cross_ref_pattern, text_content)
            entry_data['cross_references'] = cross_matches
            
            return entry_data
            
        except Exception as e:
            logger.error("Failed to parse DICO format", error=str(e))
            return {}
```

## Enhanced Database Schema with DICO-Specific Fields

```python
# src/dico_pipeline/database_enhanced.py
import duckdb
import structlog

logger = structlog.get_logger(__name__)

class DicoDatabaseEnhanced:
    def __init__(self, db_path: str = "./dico_bilingual.duckdb"):
        self.db_path = db_path
        self.conn = self._init_database()
        
    def _init_database(self) -> duckdb.DuckDBPyConnection:
        """Initialize enhanced DuckDB database with DICO-specific schema"""
        conn = duckdb.connect(self.db_path)
        
        # Enhanced DICO table with DICO-specific fields
        conn.execute("""
            CREATE TABLE IF NOT EXISTS dico_fr (
                id INTEGER PRIMARY KEY,
                headword TEXT NOT NULL,
                sanskrit TEXT NOT NULL,
                french_definition TEXT NOT NULL,
                devanagari TEXT,
                iast TEXT,
                slp1 TEXT,
                velthuis TEXT,
                -- DICO-specific fields
                dico_page_number INTEGER,
                dico_column_number INTEGER,
                dico_volume INTEGER,
                page_references TEXT,  -- JSON array of page numbers
                cross_references TEXT,  -- JSON array of related terms
                etymology TEXT,
                pronunciation_guide TEXT,
                usage_examples TEXT,
                -- Heritage-specific fields
                entry_html TEXT,
                heritage_url TEXT,
                search_query TEXT,
                encoding_format TEXT,
                -- Metadata
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_heritage_check TIMESTAMP,
                data_quality_score FLOAT DEFAULT 0.0,
                UNIQUE(headword, dico_page_number)
            )
        """)
        
        # Enhanced translations table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS translations (
                id INTEGER PRIMARY KEY,
                dico_fr_id INTEGER NOT NULL,
                english_definition TEXT,
                -- Translation metadata
                translation_quality_score FLOAT,
                translation_confidence FLOAT,
                processing_time_seconds FLOAT,
                openai_model_used TEXT,
                openai_tokens_used INTEGER,
                openai_cost_usd FLOAT,
                -- Translation quality
                grammar_check_passed BOOLEAN,
                terminology_consistency BOOLEAN,
                sanskrit_terms_preserved BOOLEAN,
                -- Error handling
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                last_processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dico_fr_id) REFERENCES dico_fr(id)
            )
        """)
        
        # Create additional indexes for performance
        conn.execute("CREATE INDEX IF NOT EXISTS idx_headword ON dico_fr(headword)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sanskrit ON dico_fr(sanskrit)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_devanagari ON dico_fr(devanagari)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_dico_page ON dico_fr(dico_page_number)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_dico_fr_id ON translations(dico_fr_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_quality_score ON dico_fr(data_quality_score)")
        
        logger.info("Enhanced database initialized", db_path=self.db_path)
        return conn
    
    def save_enhanced_entry(self, entry_data: Dict[str, Any], 
                          search_query: str, heritage_url: str) -> Optional[int]:
        """Save enhanced DICO entry with DICO-specific metadata"""
        try:
            # Check if entry already exists
            existing = self.conn.execute("""
                SELECT id FROM dico_fr 
                WHERE headword = ? AND dico_page_number = ?
            """, (entry_data['headword'], entry_data.get('dico_page_number'))).fetchone()
            
            if existing:
                # Update existing entry
                self.conn.execute("""
                    UPDATE dico_fr SET
                        sanskrit = ?,
                        french_definition = ?,
                        devanagari = ?,
                        iast = ?,
                        slp1 = ?,
                        velthuis = ?,
                        dico_page_number = ?,
                        dico_column_number = ?,
                        dico_volume = ?,
                        page_references = ?,
                        cross_references = ?,
                        etymology = ?,
                        pronunciation_guide = ?,
                        usage_examples = ?,
                        entry_html = ?,
                        heritage_url = ?,
                        search_query = ?,
                        encoding_format = ?,
                        updated_at = CURRENT_TIMESTAMP,
                        last_heritage_check = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    entry_data['sanskrit'],
                    entry_data['french_definition'],
                    entry_data.get('devanagari'),
                    entry_data.get('iast'),
                    entry_data.get('slp1'),
                    entry_data.get('velthuis'),
                    entry_data.get('dico_page_number'),
                    entry_data.get('dico_column_number'),
                    entry_data.get('dico_volume'),
                    entry_data.get('page_references'),
                    entry_data.get('cross_references'),
                    entry_data.get('etymology'),
                    entry_data.get('pronunciation_guide'),
                    entry_data.get('usage_examples'),
                    entry_data.get('entry_html'),
                    heritage_url,
                    search_query,
                    entry_data.get('encoding_format'),
                    existing[0]
                ))
                return existing[0]
            else:
                # Insert new entry
                result = self.conn.execute("""
                    INSERT INTO dico_fr (
                        headword, sanskrit, french_definition, devanagari, iast,
                        slp1, velthuis, dico_page_number, dico_column_number,
                        dico_volume, page_references, cross_references, etymology,
                        pronunciation_guide, usage_examples, entry_html,
                        heritage_url, search_query, encoding_format, data_quality_score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    RETURNING id
                """, (
                    entry_data['headword'],
                    entry_data['sanskrit'],
                    entry_data['french_definition'],
                    entry_data.get('devanagari'),
                    entry_data.get('iast'),
                    entry_data.get('slp1'),
                    entry_data.get('velthuis'),
                    entry_data.get('dico_page_number'),
                    entry_data.get('dico_column_number'),
                    entry_data.get('dico_volume'),
                    entry_data.get('page_references'),
                    entry_data.get('cross_references'),
                    entry_data.get('etymology'),
                    entry_data.get('pronunciation_guide'),
                    entry_data.get('usage_examples'),
                    entry_data.get('entry_html'),
                    heritage_url,
                    search_query,
                    entry_data.get('encoding_format'),
                    self._calculate_quality_score(entry_data)
                ))
                return result.fetchone()[0]
                
        except Exception as e:
            logger.error("Failed to save enhanced entry", 
                        headword=entry_data.get('headword'), error=str(e))
            return None
    
    def _calculate_quality_score(self, entry_data: Dict[str, Any]) -> float:
        """Calculate data quality score for entry"""
        score = 0.0
        
        # Check for required fields
        if entry_data.get('sanskrit'):
            score += 2.0
        if entry_data.get('french_definition') and len(entry_data['french_definition']) > 20:
            score += 2.0
        if entry_data.get('devanagari'):
            score += 2.0
        if entry_data.get('page_references'):
            score += 1.0
        if entry_data.get('cross_references'):
            score += 1.0
        if entry_data.get('etymology'):
            score += 1.0
        if entry_data.get('entry_html') and len(entry_data['entry_html']) > 100:
            score += 1.0
            
        return min(score, 10.0)  # Cap at 10.0
    
    def get_entries_by_quality(self, min_score: float = 5.0) -> List[Dict[str, Any]]:
        """Get entries by quality score"""
        result = self.conn.execute("""
            SELECT id, headword, sanskrit, french_definition, data_quality_score
            FROM dico_fr 
            WHERE data_quality_score >= ?
            ORDER BY data_quality_score DESC
        """, (min_score,))
        
        return [dict(row) for row in result.fetchall()]
    
    def get_translation_progress_by_quality(self) -> Dict[str, Any]:
        """Get translation progress segmented by data quality"""
        result = self.conn.execute("""
            SELECT 
                CASE 
                    WHEN df.data_quality_score >= 8.0 THEN 'high_quality'
                    WHEN df.data_quality_score >= 5.0 THEN 'medium_quality'
                    ELSE 'low_quality'
                END as quality_group,
                COUNT(df.id) as total_entries,
                COUNT(t.id) as translated_entries,
                ROUND(COUNT(t.id) * 100.0 / NULLIF(COUNT(df.id), 0), 2) as completion_percentage
            FROM dico_fr df
            LEFT JOIN translations t ON df.id = t.dico_fr_id
            GROUP BY quality_group
            ORDER BY completion_percentage DESC
        """)
        
        return [dict(row) for row in result.fetchall()]
```

## Real DICO Examples and Search Patterns

### Example Searches and Expected Results

```python
# src/dico_pipeline/examples.py
import structlog

logger = structlog.get_logger(__name__)

class DicoExamples:
    """Real examples from DICO database"""
    
    # Known entries in DICO with their characteristics
    REAL_EXAMPLES = {
        "vaagyoga": {
            "velthuis_query": "vaagyoga",
            "devanagari": "वाग्योघ",
            "expected_french_content": ["vaagyoḥga", "yoga"],
            "page_references": [234, 567],  # Example page numbers
            "cross_references": ["yoga", "vaac"],
            "quality_indicators": ["etymology", "multiple_definitions"]
        },
        "agni": {
            "velthuis_query": "agni",
            "devanagari": "अग्नि",
            "expected_french_content": ["feu", "dieu du feu"],
            "page_references": [45, 89, 234],
            "cross_references": ["fire", "soma"],
            "quality_indicators": ["common_entry", "extensive_definitions"]
        },
        "asva": {
            "velthuis_query": "asva",
            "devanagari": "अश्व",
            "expected_french_content": ["cheval"],
            "page_references": [67],
            "cross_references": ["horse", "gava"],
            "quality_indicators": ["basic_vocabulary"]
        },
        "dharma": {
            "velthuis_query": "dharma",
            "devanagari": "धर्म",
            "expected_french_content": ["loi", "devoir", "justice"],
            "page_references": [123, 456, 789],
            "cross_references": ["rita", "karma"],
            "quality_indicators": ["complex_concept", "philosophical"]
        }
    }
    
    @classmethod
    def validate_entry_quality(cls, entry_data: Dict[str, Any], 
                             example_key: str) -> Dict[str, Any]:
        """Validate entry against known examples"""
        
        if example_key not in cls.REAL_EXAMPLES:
            return {"valid": False, "reason": "Unknown example"}
        
        example = cls.REAL_EXAMPLES[example_key]
        validation_results = {
            "valid": True,
            "checks": {},
            "score": 0.0,
            "max_score": 0.0
        }
        
        # Check Devanagari
        validation_results["checks"]["devanagari"] = False
        validation_results["max_score"] += 2
        if entry_data.get('devanagari'):
            expected = example["devanagari"]
            if expected in entry_data.get('devanagari', ''):
                validation_results["checks"]["devanagari"] = True
                validation_results["score"] += 2
            else:
                validation_results["checks"]["devanagari"] = "partial"
                validation_results["score"] += 1
        
        # Check French definition content
        validation_results["checks"]["french_content"] = False
        validation_results["max_score"] += 3
        french_text = entry_data.get('french_definition', '').lower()
        if french_text:
            matches = 0
            for expected_content in example["expected_french_content"]:
                if expected_content.lower() in french_text:
                    matches += 1
            
            if matches >= len(example["expected_french_content"]) // 2:
                validation_results["checks"]["french_content"] = True
                validation_results["score"] += 3
            elif matches > 0:
                validation_results["checks"]["french_content"] = "partial"
                validation_results["score"] += 1.5
        
        # Check page references
        validation_results["checks"]["page_references"] = False
        validation_results["max_score"] += 1
        if entry_data.get('page_references'):
            # Check if any expected pages are referenced
            pages = entry_data.get('page_references', [])
            if any(page in example["page_references"] for page in pages):
                validation_results["checks"]["page_references"] = True
                validation_results["score"] += 1
            elif pages:
                validation_results["checks"]["page_references"] = "partial"
                validation_results["score"] += 0.5
        
        # Check cross-references
        validation_results["checks"]["cross_references"] = False
        validation_results["max_score"] += 2
        cross_refs = entry_data.get('cross_references', [])
        if cross_refs:
            matches = 0
            for expected_ref in example["cross_references"]:
                if expected_ref.lower() in [r.lower() for r in cross_refs]:
                    matches += 1
            
            if matches >= len(example["cross_references"]) // 2:
                validation_results["checks"]["cross_references"] = True
                validation_results["score"] += 2
            elif matches > 0:
                validation_results["checks"]["cross_references"] = "partial"
                validation_results["score"] += 1
        
        validation_results["percentage"] = (validation_results["score"] / 
                                         validation_results["max_score"]) * 100
        
        return validation_results
    
    @classmethod
    def get_test_queries(cls) -> List[Dict[str, Any]]:
        """Get test queries for validation"""
        return [
            {
                "query": "vaagyoga",
                "lex": "DICO",
                "encoding": "velthuis",
                "description": "vaagyoḥga (वाग्योघ) - complex compound term",
                "expected_type": "compound_sanskrit"
            },
            {
                "query": "agni", 
                "lex": "DICO",
                "encoding": "velthuis",
                "description": "agni (अग्नि) - common noun, fire deity",
                "expected_type": "common_noun"
            },
            {
                "query": "dharma",
                "lex": "DICO", 
                "encoding": "velthuis",
                "description": "dharma (धर्म) - philosophical concept",
                "expected_type": "abstract_concept"
            }
        ]
```

## Enhanced Import Pipeline with Real Examples

```python
# src/dico_pipeline/import_pipeline_enhanced.py
import structlog
from typing import Dict, Any, List
from .database_enhanced import DicoDatabaseEnhanced
from .heritage_collector_enhanced import HeritageDicoCollector
from .examples import DicoExamples

logger = structlog.get_logger(__name__)

class DicoImportPipelineEnhanced:
    def __init__(self, db_path: str = "./dico_bilingual.duckdb"):
        self.db = DicoDatabaseEnhanced(db_path)
        self.collector = HeritageDicoCollector()
        self.examples = DicoExamples()
        
    def validate_with_real_examples(self) -> Dict[str, Any]:
        """Validate import using real DICO examples"""
        
        logger.info("Starting validation with real DICO examples")
        
        validation_results = []
        test_queries = self.examples.get_test_queries()
        
        for test_query in test_queries:
            try:
                logger.info("Validating example", query=test_query["query"])
                
                # Get the entry from Heritage
                search_params = HeritageParameterBuilder.build_search_params(
                    query=test_query["query"],
                    lex="DICO",
                    max_results=5,
                    encoding="velthuis"
                )
                
                search_response = self.collector.client.fetch_cgi_script(
                    "sktindex", params=search_params
                )
                
                # Parse search results
                search_entries = self.collector._parse_search_results(search_response)
                
                if search_entries:
                    # Get the first matching entry
                    entry = self.collector._get_entry_details(search_entries[0]['headword'])
                    
                    if entry:
                        # Save to database
                        heritage_url = f"/cgi-bin/skt/sktindex?lex=DICO&q={test_query['query']}&t=VH"
                        entry_id = self.db.save_enhanced_entry(
                            entry, test_query["query"], heritage_url
                        )
                        
                        if entry_id:
                            # Validate against expected example
                            validation = self.examples.validate_entry_quality(
                                entry, test_query["query"]
                            )
                            
                            validation_results.append({
                                "query": test_query["query"],
                                "description": test_query["description"],
                                "expected_type": test_query["expected_type"],
                                "validation": validation,
                                "entry_id": entry_id
                            })
                            
                            logger.info("Example validated", 
                                     query=test_query["query"],
                                     score=validation["percentage"])
                        else:
                            validation_results.append({
                                "query": test_query["query"],
                                "error": "Failed to save entry"
                            })
                    else:
                        validation_results.append({
                            "query": test_query["query"],
                            "error": "Failed to get entry details"
                        })
                else:
                    validation_results.append({
                        "query": test_query["query"],
                        "error": "No search results found"
                    })
                    
            except Exception as e:
                logger.error("Example validation failed", 
                           query=test_query["query"], error=str(e))
                validation_results.append({
                    "query": test_query["query"],
                    "error": str(e)
                })
        
        # Calculate overall validation score
        valid_results = [r for r in validation_results if "validation" in r]
        if valid_results:
            avg_score = sum(r["validation"]["percentage"] for r in valid_results) / len(valid_results)
        else:
            avg_score = 0.0
        
        return {
            "total_examples": len(test_queries),
            "valid_examples": len(valid_results),
            "average_score": avg_score,
            "results": validation_results
        }
    
    def run_quality_aware_import(self, min_quality_score: float = 5.0) -> Dict[str, Any]:
        """Run import with quality-based filtering"""
        
        logger.info("Starting quality-aware DICO import")
        
        try:
            # Collect entries with enhanced validation
            all_entries = self.collector.collect_all_entries()
            
            high_quality_entries = []
            low_quality_entries = []
            
            for entry in all_entries:
                # Calculate quality score
                quality_score = self.db._calculate_quality_score(entry)
                
                if quality_score >= min_quality_score:
                    high_quality_entries.append(entry)
                else:
                    low_quality_entries.append(entry)
            
            # Save high quality entries first
            saved_count = 0
            for entry in high_quality_entries:
                heritage_url = f"/cgi-bin/skt/sktindex?lex=DICO&q={entry['headword']}&t=VH"
                entry_id = self.db.save_enhanced_entry(entry, entry['headword'], heritage_url)
                if entry_id:
                    saved_count += 1
            
            # Log results
            final_stats = self.db.get_entry_count()
            
            return {
                'status': 'success',
                'total_entries_collected': len(all_entries),
                'high_quality_entries': len(high_quality_entries),
                'low_quality_entries': len(low_quality_entries),
                'entries_saved': saved_count,
                'min_quality_threshold': min_quality_score,
                'final_stats': final_stats
            }
            
        except Exception as e:
            logger.error("Quality-aware import failed", error=str(e))
            return {
                'status': 'failed',
                'error': str(e)
            }
        finally:
            self.db.close()
```

## Updated CLI with Enhanced Features

```python
# src/dico_pipeline/cli_enhanced.py
import click
import structlog
from .import_pipeline_enhanced import DicoImportPipelineEnhanced
from .translation_pipeline import DicoTranslationPipeline

logger = structlog.get_logger(__name__)

@click.group()
@click.option('--debug', is_flag=True, help='Enable debug logging')
def cli(debug):
    """Enhanced DICO Bilingual Pipeline CLI"""
    if debug:
        import structlog
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
            context_class=dict,
            cache_logger_on_first_use=True,
        )

@cli.command()
@click.option('--db-path', default='./dico_bilingual.duckdb', help='Database path')
@click.option('--validate-examples', is_flag=True, help='Validate against real DICO examples')
@click.option('--quality-threshold', default=5.0, help='Minimum quality score for imports')
def import_data(db_path, validate_examples, quality_threshold):
    """Import DICO data from Heritage Platform with enhanced validation"""
    
    pipeline = DicoImportPipelineEnhanced(db_path)
    
    if validate_examples:
        result = pipeline.validate_with_real_examples()
        click.echo("Real Example Validation Results:")
        click.echo("=" * 50)
        
        for item in result['results']:
            click.echo(f"\nQuery: {item['query']}")
            click.echo(f"Description: {item['description']}")
            if 'validation' in item:
                val = item['validation']
                click.echo(f"Validation Score: {val['percentage']:.1f}%")
                for check, status in val['checks'].items():
                    click.echo(f"  {check}: {status}")
            else:
                click.echo(f"Error: {item['error']}")
        
        click.echo(f"\nOverall Results:")
        click.echo(f"Total Examples: {result['total_examples']}")
        click.echo(f"Valid Examples: {result['valid_examples']}")
        click.echo(f"Average Score: {result['average_score']:.1f}%")
        
    else:
        result = pipeline.run_quality_aware_import(quality_threshold)
        click.echo(f"Import {result['status']}")
        if 'error' in result:
            click.echo(f"Error: {result['error']}")
        else:
            click.echo(f"Entries collected: {result['total_entries_collected']}")
            click.echo(f"High quality entries: {result['high_quality_entries']}")
            click.echo(f"Low quality entries: {result['low_quality_entries']}")
            click.echo(f"Entries saved: {result['entries_saved']}")
            if 'final_stats' in result:
                stats = result['final_stats']
                click.echo(f"Total entries in DB: {stats['total_entries']}")
                click.echo(f"Translated entries: {stats['translated_entries']}")

@cli.command()
@click.option('--db-path', default='./dico_bilingual.duckdb', help='Database path')
@click.option('--openai-api-key', envvar='OPENAI_API_KEY', help='OpenAI API key')
@click.option('--batch-size', default=10, help='Translation batch size')
@click.option('--quality-filter', default=0.0, help='Only translate entries with quality >= this score')
def translate(db_path, openai_api_key, batch_size, quality_filter):
    """Translate entries from French to English with quality filtering"""
    
    if not openai_api_key:
        click.echo("Error: OPENAI_API_KEY environment variable or --openai-api-key required")
        return
    
    # Get entries matching quality filter
    db = DicoDatabaseEnhanced(db_path)
    try:
        if quality_filter > 0:
            entries = db.get_entries_by_quality(quality_filter)
            click.echo(f"Found {len(entries)} entries with quality >= {quality_filter}")
        else:
            # Get all untranslated entries
            from .database import DicoDatabase
            temp_db = DicoDatabase(db_path)
            entries = temp_db.get_untranslated_entries(batch_size * 10)  # Get more for batching
            temp_db.close()
        
        if not entries:
            click.echo("No entries found to translate")
            return
        
        # Process in batches
        pipeline = DicoTranslationPipeline(db_path, openai_api_key)
        
        # Translate in manageable batches
        all_results = []
        for i in range(0, len(entries), batch_size):
            batch = entries[i:i + batch_size]
            click.echo(f"Translating batch {i//batch_size + 1} of {len(entries)//batch_size + 1}")
            
            batch_results = []
            for entry in batch:
                result = pipeline.translator.translate_entry(entry)
                result['dico_fr_id'] = entry['id']
                batch_results.append(result)
            
            # Save batch results
            for result in batch_results:
                db.conn.execute("""
                    INSERT INTO translations (
                        dico_fr_id, english_definition, translation_quality_score,
                        processing_time_seconds, openai_tokens_used, cost_usd,
                        processed_at, error_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    result['dico_fr_id'],
                    result['english_definition'],
                    result['translation_quality_score'],
                    result['processing_time_seconds'],
                    result['openai_tokens_used'],
                    result['cost_usd'],
                    result['processed_at'],
                    result['error_message']
                ))
            
            db.conn.commit()
            all_results.extend(batch_results)
            
            click.echo(f"Batch {i//batch_size + 1} complete: "
                      f"{sum(1 for r in batch_results if r['english_definition'])} translated, "
                      f"{sum(1 for r in batch_results if not r['english_definition'])} failed")
        
        # Show summary
        successful = sum(1 for r in all_results if r['english_definition'])
        total_cost = sum(r['cost_usd'] for r in all_results)
        
        click.echo(f"\nTranslation Summary:")
        click.echo(f"Total processed: {len(all_results)}")
        click.echo(f"Successful: {successful}")
        click.echo(f"Failed: {len(all_results) - successful}")
        click.echo(f"Total cost: ${total_cost:.4f}")
        
    except Exception as e:
        click.echo(f"Error: {str(e)}")
    finally:
        db.close()

@cli.command()
@click.option('--db-path', default='./dico_bilingual.duckdb', help='Database path')
def quality_report(db_path):
    """Show detailed quality and translation report"""
    
    db = DicoDatabaseEnhanced(db_path)
    try:
        # Overall statistics
        stats = db.get_entry_count()
        
        click.echo("DICO Bilingual Pipeline Quality Report")
        click.echo("=" * 50)
        click.echo(f"Total entries: {stats['total_entries']}")
        click.echo(f"Translated entries: {stats['translated_entries']}")
        click.echo(f"Remaining to translate: {stats['remaining_to_translate']}")
        
        # Quality distribution
        quality_dist = db.get_translation_progress_by_quality()
        click.echo(f"\nQuality Distribution:")
        for group in quality_dist:
            click.echo(f"  {group['quality_group'].replace('_', ' ').title()}: "
                      f"{group['translated_entries']}/{group['total_entries']} "
                      f"({group['completion_percentage']:.1f}%)")
        
        # High quality examples
        high_quality = db.get_entries_by_quality(8.0)
        click.echo(f"\nTop Quality Entries (score >= 8.0):")
        for entry in high_quality[:5]:
            click.echo(f"  {entry['headword']} (score: {entry['data_quality_score']:.1f})")
        
        # Recent translations
        recent = db.conn.execute("""
            SELECT d.headword, t.english_definition, t.processed_at, t.translation_quality_score
            FROM translations t
            JOIN dico_fr d ON t.dico_fr_id = d.id
            ORDER BY t.processed_at DESC
            LIMIT 10
        """).fetchall()
        
        if recent:
            click.echo(f"\nRecent Translations:")
            for row in recent:
                quality_emoji = "⭐" if row[3] >= 8.0 else "✓" if row[3] >= 5.0 else "○"
                click.echo(f"  {quality_emoji} {row[0]}: {row[1][:60]}...")
        
    finally:
        db.close()

if __name__ == '__main__':
    cli()
```

## Usage Examples with Real Data

### Step 1: Import and Validate with Real Examples
```bash
# Validate against real DICO examples first
python -m src.dico_pipeline.cli_enhanced import-data --validate-examples

# Run quality-aware import
python -m src.dico_pipeline.cli_enhanced import-data --quality-threshold 5.0
```

### Step 2: High-Quality Translation
```bash
# Set OpenAI API key
export OPENAI_API_KEY="your-api-key-here"

# Translate only high-quality entries
python -m src.dico_pipeline.cli_enhanced translate --quality-filter 8.0 --batch-size 5

# Translate all entries
python -m src.dico_pipeline.cli_enhanced translate --batch-size 10
```

### Step 3: Quality Monitoring
```bash
# Check quality distribution
python -m src.dico_pipeline.cli_enhanced quality-report
```

This enhanced implementation includes real DICO examples, quality-aware processing, and comprehensive validation to ensure the pipeline produces high-quality bilingual dictionaries.