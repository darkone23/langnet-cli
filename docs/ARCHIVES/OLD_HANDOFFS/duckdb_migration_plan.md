# DuckDB Migration for CTS URN Database

**Date**: 2026-01-01  
**Status**: Migration planning completed  
**Priority**: High - Improve performance and scalability

## Overview

This document outlines the migration from SQLite to DuckDB for the CTS URN reference database. DuckDB offers significant performance improvements for analytical queries and better integration with modern data processing workflows.

## Benefits of DuckDB Migration

### Performance Advantages
- **Columnar storage**: Better for analytical queries and aggregation
- **Vectorized execution**: Faster processing of large datasets
- **Memory efficiency**: Better cache utilization and reduced disk I/O
- **Parallel processing**: Multi-core query execution

### Integration Benefits
- **Pandas compatibility**: Direct DataFrame integration
- **Polars support**: Native support for Polars DataFrame
- **Arrow format**: Native Apache Arrow support
- **Python ecosystem**: Better integration with modern Python tools

### Operational Benefits
- **No separate server**: Embedded database like SQLite
- **Concurrent reads**: Better read concurrency than SQLite
- **Compression**: Built-in compression for smaller storage

## Migration Strategy

### Phase 1: Proof of Concept
1. **Create DuckDB database**
   - Migrate existing SQLite schema to DuckDB
   - Test basic functionality
   - Benchmark performance

2. **Schema Migration**
   - Convert SQLite tables to DuckDB
   - Optimize data types for DuckDB
   - Add DuckDB-specific optimizations

### Phase 2: Integration Update
1. **Update CTSUrnMapper**
   - Modify database connection logic
   - Add DuckDB-specific query optimizations
   - Maintain backward compatibility

2. **Testing and Validation**
   - Comprehensive testing of all functionality
   - Performance benchmarking
   - Data validation against SQLite version

### Phase 3: Production Deployment
1. **Database Migration Script**
   - Automated migration from SQLite to DuckDB
   - Data integrity validation
   - Rollback procedures

2. **Documentation Update**
   - Update configuration documentation
   - Add performance benchmarks
   - Migration guide

## Technical Implementation

### Database Schema (DuckDB)
```sql
-- Authors table
CREATE TABLE authors (
    author_id VARCHAR PRIMARY KEY,
    author_name VARCHAR NOT NULL,
    alternate_name VARCHAR,
    genre VARCHAR,
    language VARCHAR,
    source VARCHAR,
    cts_namespace VARCHAR
);

-- Works table  
CREATE TABLE works (
    canon_id VARCHAR,
    author_name VARCHAR,
    work_title VARCHAR,
    reference VARCHAR,
    word_count VARCHAR,
    work_type VARCHAR,
    source VARCHAR,
    cts_urn VARCHAR,
    UNIQUE(canon_id, reference)
);

-- Unified index table
CREATE TABLE unified_index (
    id VARCHAR NOT NULL,
    type VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    author VARCHAR,
    work_title VARCHAR,
    language VARCHAR,
    source VARCHAR,
    cts_urn VARCHAR,
    PRIMARY KEY (id, type)
);
```

### Migration Script
```python
import sqlite3
import duckdb
import pandas as pd
from pathlib import Path

def migrate_sqlite_to_duckdb(sqlite_path: str, duckdb_path: str):
    """Migrate SQLite database to DuckDB"""
    
    # Connect to SQLite
    sqlite_conn = sqlite3.connect(sqlite_path)
    
    # Connect to DuckDB
    duckdb_conn = duckdb.connect(duckdb_path)
    
    # Get all tables from SQLite
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    for table in tables:
        table_name = table[0]
        print(f"Migrating table: {table_name}")
        
        # Read data from SQLite using pandas
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", sqlite_conn)
        
        # Write to DuckDB
        duckdb_conn.register(f'temp_{table_name}', df)
        duckdb_conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM temp_{table_name}")
        duckdb_conn.execute(f"DROP VIEW temp_{table_name}")
    
    # Close connections
    sqlite_conn.close()
    duckdb_conn.close()
    print("Migration completed successfully!")
```

### Updated CTSUrnMapper
```python
class CTSUrnMapper:
    def __init__(self, db_path: Optional[str] = None, use_duckdb: bool = True):
        self.db_path = db_path
        self.use_duckdb = use_duckdb
        self._db_conn: Optional[Union[sqlite3.Connection, duckdb.DuckDBPyConnection]] = None
        self._author_cache: Optional[Dict[str, Tuple[str, str]]] = None
        self._work_cache: Optional[Dict[str, Tuple[str, str, str]]] = None
        
    def _get_connection(self) -> Optional[Union[sqlite3.Connection, duckdb.DuckDBPyConnection]]:
        """Get database connection, supporting both SQLite and DuckDB"""
        if self._db_conn:
            return self._db_conn
            
        db_path = self._get_db_path()
        if not db_path or not os.path.exists(db_path):
            return None
            
        try:
            if self.use_duckdb:
                self._db_conn = duckdb.connect(db_path)
            else:
                self._db_conn = sqlite3.connect(db_path)
            return self._db_conn
        except Exception:
            return None
    
    def _load_author_cache(self) -> Dict[str, Tuple[str, str]]:
        """Load author mappings from database into cache with DuckDB optimization"""
        if self._author_cache is not None:
            return self._author_cache
            
        self._author_cache = {}
        conn = self._get_connection()
        
        if not conn:
            return self._author_cache
            
        try:
            if self.use_duckdb:
                # Use DuckDB's optimized query
                query = """
                SELECT author_id, author_name, cts_namespace 
                FROM author_index 
                WHERE cts_namespace IS NOT NULL
                """
                df = conn.execute(query).fetchdf()
                
                for _, row in df.iterrows():
                    author_id, author_name, cts_ns = row
                    normalized = author_name.lower().replace(" ", "")
                    self._author_cache[normalized] = (author_id, cts_ns)
                    
                    if len(author_name) > 3:
                        short = author_name.split()[-1][:4].lower()
                        if short and short not in self._author_cache:
                            self._author_cache[short] = (author_id, cts_ns)
            else:
                # SQLite fallback
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT author_id, author_name, cts_namespace 
                    FROM author_index 
                    WHERE cts_namespace IS NOT NULL
                """)
                for row in cursor.fetchall():
                    author_id, author_name, cts_ns = row
                    normalized = author_name.lower().replace(" ", "")
                    self._author_cache[normalized] = (author_id, cts_ns)
                    
                    if len(author_name) > 3:
                        short = author_name.split()[-1][:4].lower()
                        if short and short not in self._author_cache:
                            self._author_cache[short] = (author_id, cts_ns)
                            
        except Exception:
            pass
            
        return self._author_cache
```

## Performance Expectations

### Query Performance Improvements
- **Author lookups**: 2-3x faster due to columnar storage
- **Work searches**: 3-5x faster for complex queries
- **Batch operations**: 5-10x faster for bulk operations
- **Memory usage**: 30-50% reduction in memory footprint

### Storage Improvements
- **Compression**: 40-60% reduction in database size
- **Indexing**: Better index performance for analytical queries

## Testing Plan

### Functional Testing
1. **Basic functionality**
   - All existing tests should pass
   - Citation mapping should work identically
   - URN generation should be consistent

2. **Performance testing**
   - Query time benchmarks
   - Memory usage comparison
   - Concurrency testing

3. **Edge case testing**
   - Large citation batches
   - Complex work titles
   - Multi-location references

### Migration Testing
1. **Data integrity**
   - Row count verification
   - Content validation
   - Index consistency

2. **Rollback testing**
   - SQLite restore functionality
   - Data consistency after rollback

## Rollback Strategy

### Automatic Fallback
```python
def safe_database_operation(operation):
    """Execute database operation with automatic fallback to SQLite"""
    try:
        if use_duckdb:
            return operation(duckdb_connection)
        else:
            return operation(sqlite_connection)
    except Exception as e:
        # Log error and fallback
        logger.warning(f"DuckDB operation failed: {e}, falling back to SQLite")
        return operation(sqlite_connection)
```

### Manual Rollback Procedure
1. Backup current DuckDB database
2. Restore from SQLite backup
3. Update configuration to use SQLite
4. Verify functionality

## Configuration

### Environment Variables
```bash
# Database configuration
LANGNET_DB_TYPE=duckdb  # or sqlite
LANGNET_DB_PATH=/path/to/database.duckdb
LANGNET_DUCKDB_MEMORY_LIMIT=1GB
```

### Configuration File
```python
# config.py
DATABASE_CONFIG = {
    "type": "duckdb",  # "duckdb" or "sqlite"
    "path": "/tmp/classical_refs.duckdb",
    "memory_limit": "1GB",
    "threads": 4,
    "compression": True
}
```

## Timeline

### Week 1: Proof of Concept
- [ ] Create DuckDB database schema
- [ ] Implement basic migration script
- [ ] Test core functionality

### Week 2: Integration Update
- [ ] Update CTSUrnMapper for DuckDB
- [ ] Add performance optimizations
- [ ] Comprehensive testing

### Week 3: Production Deployment
- [ ] Create production migration script
- [ ] Documentation updates
- [ ] Performance benchmarking

## Success Criteria

### Functional Criteria
- [ ] All existing tests pass with DuckDB
- [ ] Performance meets or exceeds SQLite version
- [ ] Data integrity maintained 100%

### Performance Criteria
- [ ] Query performance improved by 2x or better
- [ ] Memory usage reduced by 30% or better
- [ ] Storage size reduced by 40% or better

### Operational Criteria
- [ ] Migration script works reliably
- [ ] Rollback procedure tested and documented
- [ ] Documentation updated and accurate

## Risk Assessment

### Technical Risks
- **Data corruption**: Low risk with proper validation
- **Performance regression**: Low risk with thorough testing
- **Compatibility issues**: Low risk with fallback mechanism

### Operational Risks
- **Downtime**: Minimal risk with proper migration strategy
- **Data loss**: Eliminated with backup procedures
- **User impact**: Low risk with gradual rollout

## Conclusion

The DuckDB migration offers significant performance and operational benefits for the CTS URN database. With proper planning and testing, this migration will improve the overall performance and scalability of the citation system while maintaining full compatibility with existing functionality.