-- Project Orion core schema for DuckDB

-- Index: raw user query → normalized query result
CREATE TABLE IF NOT EXISTS query_normalization_index (
    query_hash VARCHAR PRIMARY KEY,
    raw_query VARCHAR NOT NULL,
    language VARCHAR NOT NULL,
    normalized_json JSON NOT NULL,
    canonical_forms JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_query_norm_raw_lang ON query_normalization_index(raw_query, language);

-- Index: raw query → tool plan (stage 0)
CREATE TABLE IF NOT EXISTS query_plan_index (
    query_hash VARCHAR PRIMARY KEY,
    query VARCHAR NOT NULL,
    language VARCHAR NOT NULL,
    plan_id VARCHAR NOT NULL,
    plan_hash VARCHAR NOT NULL,
    plan_data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_query_plan_lookup ON query_plan_index(query, language);
CREATE INDEX IF NOT EXISTS idx_query_plan_hash ON query_plan_index(plan_hash);

-- Index: plan hash → response IDs (stage 0.5)
CREATE TABLE IF NOT EXISTS plan_response_index (
    plan_hash VARCHAR PRIMARY KEY,
    plan_id VARCHAR NOT NULL,
    tool_response_ids JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_plan_response_accessed ON plan_response_index(last_accessed);

-- Raw response index for transport effects
CREATE TABLE IF NOT EXISTS raw_response_index (
    response_id VARCHAR PRIMARY KEY,
    tool VARCHAR NOT NULL,
    call_id VARCHAR NOT NULL,
    endpoint VARCHAR NOT NULL,
    status_code INTEGER NOT NULL,
    content_type VARCHAR,
    headers JSON,
    body BLOB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_raw_response_tool ON raw_response_index(tool, created_at);

-- Parsed extractions derived from raw responses
CREATE TABLE IF NOT EXISTS extraction_index (
    extraction_id VARCHAR PRIMARY KEY,
    response_id VARCHAR NOT NULL,
    tool VARCHAR NOT NULL,
    kind VARCHAR NOT NULL,
    canonical TEXT,
    payload JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_extraction_tool ON extraction_index(tool, created_at);
CREATE INDEX IF NOT EXISTS idx_extraction_canonical ON extraction_index(canonical);

-- Universal claims emitted after derivation/transform
CREATE TABLE IF NOT EXISTS claims (
    claim_id VARCHAR PRIMARY KEY,
    derivation_id VARCHAR NOT NULL,
    subject VARCHAR NOT NULL,
    predicate VARCHAR NOT NULL,
    value JSON,
    provenance_chain JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_claims_subject ON claims(subject);
CREATE INDEX IF NOT EXISTS idx_claims_predicate ON claims(predicate);

-- Provenance records for auditing stages
CREATE TABLE IF NOT EXISTS provenance (
    provenance_id VARCHAR PRIMARY KEY,
    claim_id VARCHAR NOT NULL,
    stage VARCHAR NOT NULL,
    tool VARCHAR,
    reference_id VARCHAR,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_provenance_claim ON provenance(claim_id);
