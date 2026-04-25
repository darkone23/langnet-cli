# Storage Schema Documentation

## Overview

Langnet V2 uses DuckDB for persistent storage with a staged execution model. The schema supports:

- **Query caching** - Avoid redundant lookups
- **Response caching** - Cache HTTP responses from external services
- **Handler versioning** - Invalidate cache when handler logic changes
- **Provenance tracking** - Full audit trail from fetch through claims
- **Performance monitoring** - Track execution time at each stage

All tables use `VARCHAR` primary keys for deterministic, content-addressable IDs.

## Database Organization

### Storage Paths

- **Main database**: `~/.local/share/langnet/cache/langnet.duckdb`
  - Cross-tool indexes (normalization, plans)
  - Shared response cache

- **Tool-specific databases**: `~/.local/share/langnet/cache/tools/{tool}.duckdb`
  - Tool-specific extractions, derivations, claims
  - Isolated per external service

Environment override: Set `LANGNET_DATA_DIR` to use custom path.

## Schema Tables

### 1. query_normalization_index

**Purpose**: Cache normalized query results to avoid redundant normalization

**Columns**:
- `query_hash` (VARCHAR, PK) - SHA256 of (raw_query, language)
- `raw_query` (VARCHAR) - Original user input (e.g., "lupus")
- `language` (VARCHAR) - Language hint ("lat", "grc", "san")
- `normalized_json` (JSON) - Full `NormalizedQuery` protobuf as JSON
- `canonical_forms` (JSON) - Extracted canonical forms for quick lookup
- `source_response_ids` (JSON) - Links to `raw_response_index` entries used
- `created_at` (TIMESTAMP) - When normalized
- `last_accessed` (TIMESTAMP) - Last query time (for LRU eviction)

**Indexes**:
- PRIMARY KEY: `query_hash`
- `idx_query_norm_raw_lang`: (raw_query, language) - Fast lookup by input

**Usage Example**:
```sql
SELECT normalized_json
FROM query_normalization_index
WHERE raw_query = 'lupus' AND language = 'lat';
```

**Cache Key**: `SHA256(f"{raw_query}:{language}")`

---

### 2. query_plan_index

**Purpose**: Cache query execution plans (which tools to call, in what order)

**Columns**:
- `query_hash` (VARCHAR, PK) - SHA256 of (query, language)
- `query` (VARCHAR) - Normalized query text
- `language` (VARCHAR) - Language hint
- `plan_id` (VARCHAR) - Unique plan identifier
- `plan_hash` (VARCHAR) - Content hash of plan structure
- `plan_data` (JSON) - Full `ToolPlan` protobuf as JSON
- `created_at` (TIMESTAMP) - When plan created
- `last_accessed` (TIMESTAMP) - Last execution time

**Indexes**:
- PRIMARY KEY: `query_hash`
- `idx_query_plan_lookup`: (query, language) - Fast lookup
- `idx_query_plan_hash`: (plan_hash) - Find identical plans

**Usage Example**:
```sql
SELECT plan_data
FROM query_plan_index
WHERE query = 'lupus' AND language = 'lat';
```

**Cache Key**: `SHA256(f"{normalized_query}:{language}")`

---

### 3. plan_response_index

**Purpose**: Map plan hashes to response IDs (which cached responses fulfill this plan)

**Columns**:
- `plan_hash` (VARCHAR, PK) - Content hash of `ToolPlan`
- `plan_id` (VARCHAR) - Plan identifier
- `tool_response_ids` (JSON) - Map of tool → response_id
  - Format: `{"fetch.diogenes": "resp-abc123", "fetch.whitakers": "resp-def456"}`
- `created_at` (TIMESTAMP) - When plan executed
- `last_accessed` (TIMESTAMP) - Last cache hit time

**Indexes**:
- PRIMARY KEY: `plan_hash`
- `idx_plan_response_accessed`: (last_accessed) - LRU eviction

**Usage Example**:
```sql
SELECT tool_response_ids
FROM plan_response_index
WHERE plan_hash = 'abc123def...';
```

**Cache Flow**:
1. Plan generated → `plan_hash` computed
2. Check if `plan_response_index` has entry
3. If yes, load responses from `raw_response_index`
4. If no, execute plan and store responses

---

### 4. raw_response_index

**Purpose**: Cache raw HTTP responses from external services (Diogenes, Heritage, etc.)

**Columns**:
- `response_id` (VARCHAR, PK) - Stable ID: `SHA256(tool:call_id:endpoint:params)`
- `tool` (VARCHAR) - Tool identifier (e.g., "fetch.diogenes")
- `call_id` (VARCHAR) - Unique call identifier from plan
- `endpoint` (VARCHAR) - HTTP endpoint URL
- `status_code` (INTEGER) - HTTP status code (200, 404, 500, etc.)
- `content_type` (VARCHAR) - MIME type ("text/html", "application/json")
- `headers` (JSON) - HTTP response headers
- `body` (BLOB) - Raw response body (HTML, JSON, XML, etc.)
- `fetch_duration_ms` (INTEGER) - Network round-trip time
- `created_at` (TIMESTAMP) - When fetched

**Indexes**:
- PRIMARY KEY: `response_id`
- `idx_raw_response_tool`: (tool, created_at) - Tool-specific queries

**Usage Example**:
```sql
SELECT body, content_type
FROM raw_response_index
WHERE response_id = 'resp-abc123';
```

**Cache Benefits**:
- Avoid redundant HTTP requests
- Enable offline development/testing
- Performance: ~50ms network → ~1ms database lookup

---

### 5. extraction_index

**Purpose**: Store structured data extracted from raw responses (stage: extract)

**Columns**:
- `extraction_id` (VARCHAR, PK) - Stable ID: `stable_effect_id("ext", call_id, response_id)`
- `response_id` (VARCHAR) - Foreign key to `raw_response_index`
- `tool` (VARCHAR) - Extract handler tool (e.g., "extract.diogenes.html")
- `kind` (VARCHAR) - Extraction type ("html", "json", "xml", "lines")
- `canonical` (TEXT) - Primary canonical form (lemma, headword)
- `payload` (JSON) - Structured extraction data
  - Example: `{"lemmas": [{"lemma": "lupus", "pos": "noun", "definition": "wolf"}]}`
- `handler_version` (VARCHAR) - Handler version (e.g., "v1", "v1.1", "v2")
- `load_duration_ms` (INTEGER) - Parsing/extraction time
- `created_at` (TIMESTAMP) - When extracted

**Indexes**:
- PRIMARY KEY: `extraction_id`
- `idx_extraction_tool`: (tool, created_at) - Tool-specific queries
- `idx_extraction_canonical`: (canonical) - Lemma lookups

**Usage Example**:
```sql
SELECT payload
FROM extraction_index
WHERE response_id = 'resp-abc123'
  AND handler_version = 'v1';
```

**Cache Invalidation**:
When handler version changes (v1 → v2), cached extractions are ignored and re-executed.

**Payload Structure Examples**:
```json
// Diogenes HTML extraction
{
  "lemmas": [
    {"lemma": "lupus", "pos": "noun", "definition": "wolf"},
    {"lemma": "lupo", "pos": "verb", "definition": "to behave like a wolf"}
  ],
  "chunks": [...]
}

// Whitakers lines extraction
{
  "words": [
    {"terms": [...], "codeline": {...}, "senses": [...]}
  ],
  "raw_lines": ["lupus, lupi  N (2nd) M   [XXXAX]", ...]
}
```

---

### 6. derivation_index

**Purpose**: Store semantic facts derived from extractions (stage: derive)

**Columns**:
- `derivation_id` (VARCHAR, PK) - Stable ID: `stable_effect_id("drv", call_id, extraction_id)`
- `extraction_id` (VARCHAR) - Foreign key to `extraction_index`
- `tool` (VARCHAR) - Derive handler tool (e.g., "derive.diogenes.morph")
- `kind` (VARCHAR) - Derivation type ("morph", "sense", "ipa")
- `canonical` (TEXT) - Canonical lemma
- `payload` (JSON) - Derived semantic facts
  - Example: `{"facts": [{"lemma": "lupus", "pos": "noun", "declension": "2", "gender": "M"}]}`
- `handler_version` (VARCHAR) - Handler version for cache invalidation
- `derive_duration_ms` (INTEGER) - Derivation processing time
- `created_at` (TIMESTAMP) - When derived

**Indexes**:
- PRIMARY KEY: `derivation_id`
- `idx_derivation_tool`: (tool, created_at)
- `idx_derivation_canonical`: (canonical)

**Usage Example**:
```sql
SELECT payload
FROM derivation_index
WHERE extraction_id = 'ext-abc123'
  AND handler_version = 'v1';
```

**Payload Structure Examples**:
```json
// Morphological derivation
{
  "facts": [
    {
      "lemma": "lupus",
      "pos": "noun",
      "declension": "2",
      "gender": "masculine",
      "stems": ["lup-"],
      "inflections": [
        {"form": "lupus", "case": "nominative", "number": "singular"},
        {"form": "lupi", "case": "genitive", "number": "singular"}
      ]
    }
  ]
}

// IPA derivation
{
  "ipa": "ˈlʊpʊs",
  "syllables": ["lu", "pus"],
  "stress": 0
}
```

---

### 7. claims

**Purpose**: Universal subject-predicate-value triples for knowledge graph (stage: claim)

**Columns**:
- `claim_id` (VARCHAR, PK) - Stable ID: `stable_effect_id("clm", call_id, derivation_id)`
- `derivation_id` (VARCHAR) - Foreign key to `derivation_index`
- `subject` (VARCHAR) - Subject of triple (usually canonical lemma)
- `predicate` (VARCHAR) - Relationship type
  - Standard predicates: `has_pos`, `has_lemma`, `has_case`, `has_gender`, etc.
- `value` (JSON) - Object of triple (can be primitive or complex)
- `provenance_chain` (JSON) - Full audit trail from fetch through derive
  - Format: `[{"stage": "fetch", "tool": "...", "reference_id": "..."}, ...]`
- `handler_version` (VARCHAR) - Handler version for cache invalidation
- `load_duration_ms` (INTEGER) - Claim generation time
- `created_at` (TIMESTAMP) - When created

**Indexes**:
- PRIMARY KEY: `claim_id`
- `idx_claims_subject`: (subject) - Query by lemma
- `idx_claims_predicate`: (predicate) - Query by relationship type

**Usage Example**:
```sql
-- Find all part-of-speech claims for "lupus"
SELECT subject, predicate, value
FROM claims
WHERE subject = 'lupus'
  AND predicate = 'has_pos';
```

**Triple Examples**:
```json
// Simple triple
{
  "subject": "lupus",
  "predicate": "has_pos",
  "value": "noun"
}

// Complex triple
{
  "subject": "lupus",
  "predicate": "has_morphology",
  "value": {
    "pos": "noun",
    "declension": "2",
    "gender": "masculine",
    "lemma": "lupus"
  }
}
```

**Provenance Chain Example**:
```json
[
  {
    "stage": "fetch",
    "tool": "fetch.diogenes",
    "reference_id": "resp-abc123",
    "metadata": {"endpoint": "http://..."}
  },
  {
    "stage": "extract",
    "tool": "extract.diogenes.html",
    "reference_id": "ext-def456",
    "metadata": {"response_id": "resp-abc123"}
  },
  {
    "stage": "derive",
    "tool": "derive.diogenes.morph",
    "reference_id": "drv-ghi789",
    "metadata": {"extraction_id": "ext-def456"}
  }
]
```

---

### 8. provenance

**Purpose**: Separate provenance records for auditing (alternative to inline chains)

**Columns**:
- `provenance_id` (VARCHAR, PK) - Unique identifier
- `claim_id` (VARCHAR) - Foreign key to `claims`
- `stage` (VARCHAR) - Pipeline stage ("fetch", "extract", "derive", "claim")
- `tool` (VARCHAR) - Tool that created this stage
- `reference_id` (VARCHAR) - ID of the effect at this stage
- `metadata` (JSON) - Additional context
- `created_at` (TIMESTAMP) - When created

**Indexes**:
- PRIMARY KEY: `provenance_id`
- `idx_provenance_claim`: (claim_id) - Find all provenance for a claim

**Usage Example**:
```sql
-- Trace full lineage of a claim
SELECT stage, tool, reference_id, metadata
FROM provenance
WHERE claim_id = 'clm-abc123'
ORDER BY created_at ASC;
```

**Note**: Currently provenance is stored inline in `claims.provenance_chain`. This table exists for future audit requirements.

---

## Staged Execution Flow

### Query Flow Diagram

```
User Query "lupus"
    ↓
[query_normalization_index] ← Cache normalized query
    ↓
[query_plan_index] ← Cache execution plan
    ↓
[plan_response_index] ← Map plan → response IDs
    ↓
[raw_response_index] ← Cache HTTP responses
    ↓
[extraction_index] ← Parse structured data (handler v1)
    ↓
[derivation_index] ← Derive semantic facts (handler v1)
    ↓
[claims] ← Emit universal triples (handler v1)
```

### Cache Lookup Sequence

1. **Normalization**: Check `query_normalization_index` for (raw_query, language)
   - Hit: Return cached `normalized_json`
   - Miss: Normalize and store

2. **Planning**: Check `query_plan_index` for (normalized_query, language)
   - Hit: Return cached `plan_data`
   - Miss: Generate plan and store

3. **Fetch**: Check `plan_response_index` for `plan_hash`
   - Hit: Load `tool_response_ids`, then fetch from `raw_response_index`
   - Miss: Execute HTTP requests, store in `raw_response_index`

4. **Extract**: Check `extraction_index` for (response_id, handler_version)
   - Hit: Return cached extraction
   - Miss: Run extract handler, store result

5. **Derive**: Check `derivation_index` for (extraction_id, handler_version)
   - Hit: Return cached derivation
   - Miss: Run derive handler, store result

6. **Claim**: Check `claims` for (derivation_id, handler_version)
   - Hit: Return cached claim
   - Miss: Run claim handler, store result

---

## Handler Version Cache Invalidation

### How It Works

Each handler is decorated with `@versioned("v1")`. The version is stored in:
- `extraction_index.handler_version`
- `derivation_index.handler_version`
- `claims.handler_version`

When looking up cached results, the system checks:
```python
cached_extraction = extraction_index.find(
    response_id=response_id,
    handler_version=handler.__handler_version__
)
```

If no match found (wrong version), the handler re-executes.

### Version Change Scenarios

**Scenario 1: Bug fix (no schema change)**
```python
# Before
@versioned("v1")
def extract_html(call, raw):
    return ExtractionEffect(..., payload={"lemmas": parse_html(raw.body)})

# After - bug fix, same schema
@versioned("v1")  # Keep same version
def extract_html(call, raw):
    return ExtractionEffect(..., payload={"lemmas": parse_html_fixed(raw.body)})
```
**Result**: Cache preserved (version unchanged)

**Scenario 2: New field added**
```python
# Before
@versioned("v1")
def extract_html(call, raw):
    return ExtractionEffect(..., payload={"lemmas": [...]})

# After - added POS field
@versioned("v1.1")  # Minor version bump
def extract_html(call, raw):
    return ExtractionEffect(..., payload={"lemmas": [...], "pos_tags": [...]})
```
**Result**: Cache invalidated for v1, re-extracts with v1.1

**Scenario 3: Breaking change**
```python
# Before
@versioned("v1")
def extract_html(call, raw):
    return ExtractionEffect(..., payload={"lemmas": ["lupus", "lupi"]})

# After - changed payload structure
@versioned("v2")  # Major version bump
def extract_html(call, raw):
    return ExtractionEffect(..., payload={"entries": [{"lemma": "lupus", ...}]})
```
**Result**: Cache invalidated for v1, re-extracts with v2

### Manual Cache Clearing

```bash
# Clear all caches (forces re-execution)
langnet-cli index clear --all

# Clear specific tool cache
langnet-cli index clear --tool diogenes

# View cache status
langnet-cli index status
```

---

## Performance Monitoring

Each table tracks execution time:

- `raw_response_index.fetch_duration_ms` - Network round-trip time
- `extraction_index.load_duration_ms` - Parsing time
- `derivation_index.derive_duration_ms` - Derivation time
- `claims.load_duration_ms` - Claim generation time

**Query total pipeline time:**
```sql
SELECT
    r.fetch_duration_ms,
    e.load_duration_ms AS extract_ms,
    d.derive_duration_ms AS derive_ms,
    c.load_duration_ms AS claim_ms,
    (r.fetch_duration_ms + e.load_duration_ms +
     d.derive_duration_ms + c.load_duration_ms) AS total_ms
FROM raw_response_index r
JOIN extraction_index e ON e.response_id = r.response_id
JOIN derivation_index d ON d.extraction_id = e.extraction_id
JOIN claims c ON c.derivation_id = d.derivation_id
WHERE r.response_id = 'resp-abc123';
```

---

## Schema Migration Guide

### Adding a New Column

1. **Add column to SQL schema:**
```sql
-- In src/langnet/storage/schemas/langnet.sql
ALTER TABLE extraction_index ADD COLUMN confidence_score FLOAT;
```

2. **Update index class:**
```python
# In src/langnet/storage/extraction_index.py
def store(self, response, kind, canonical, payload, confidence_score=None):
    self.conn.execute("""
        INSERT INTO extraction_index
        (extraction_id, response_id, tool, kind, canonical, payload,
         confidence_score, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, [extraction_id, response_id, tool, kind, canonical,
          orjson.dumps(payload), confidence_score])
```

3. **Handle migration:**
```python
# Existing databases won't have the column
# Use IF NOT EXISTS or add migration script
self.conn.execute("""
    ALTER TABLE extraction_index
    ADD COLUMN IF NOT EXISTS confidence_score FLOAT
""")
```

### Adding a New Table

1. **Create table in schema file**
2. **Add to `apply_schema()` function**
3. **Create index class** in `src/langnet/storage/`
4. **Wire into executor** if needed

### Versioning the Schema

Future work: Add schema versioning to handle migrations automatically.

**Proposed approach:**
```sql
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Best Practices

1. **Use stable IDs**: Always use `stable_effect_id()` for deterministic cache keys
2. **Version handlers**: Always use `@versioned()` decorator
3. **Index strategically**: Add indexes for columns used in WHERE clauses
4. **Monitor durations**: Track `*_duration_ms` fields for performance
5. **Clean old cache**: Implement LRU eviction based on `last_accessed`
6. **Backup databases**: DuckDB files are portable - copy for backups
7. **Test migrations**: Test schema changes with existing databases

---

## Troubleshooting

### Cache not hitting

**Symptom**: Repeated queries always re-fetch from network

**Diagnosis**:
```sql
-- Check if response is cached
SELECT response_id, created_at
FROM raw_response_index
WHERE tool = 'fetch.diogenes'
ORDER BY created_at DESC LIMIT 10;

-- Check handler versions
SELECT handler_version, COUNT(*)
FROM extraction_index
GROUP BY handler_version;
```

**Solution**: Verify handler version matches, check response_id generation

### Database locked

**Symptom**: `database is locked` error

**Diagnosis**: Multiple processes accessing same database

**Solution**:
- Use `read_only=True` for read-only connections
- Implement connection pooling
- Use separate databases per tool

### Slow queries

**Symptom**: Queries taking >100ms

**Diagnosis**:
```sql
EXPLAIN SELECT * FROM claims WHERE subject = 'lupus';
```

**Solution**: Add indexes on frequently queried columns

---

## Related Documentation

- [Handler Development Guide](./handler-development-guide.md) - Creating new handlers
- [V2 Foundation Plan](./plans/active/v2-foundation-establishment.md) - Implementation roadmap
- [Testing Guide](../tests/README.md) - Testing patterns (if exists)

---

## Schema File Location

**Primary schema**: `src/langnet/storage/schemas/langnet.sql`

**Index implementations**:
- `src/langnet/storage/effects_index.py` - RawResponseIndex
- `src/langnet/storage/extraction_index.py` - ExtractionIndex
- `src/langnet/storage/derivation_index.py` - DerivationIndex
- `src/langnet/storage/claim_index.py` - ClaimIndex
- `src/langnet/storage/plan_index.py` - PlanResponseIndex
