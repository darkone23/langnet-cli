-- CDSL DuckDB Schema

-- Main entries table with parsed components
CREATE TABLE IF NOT EXISTS entries (
    dict_id VARCHAR(20) NOT NULL,
    key VARCHAR(200) NOT NULL,
    key_normalized VARCHAR(200) NOT NULL,
    key2 VARCHAR(200),
    key2_normalized VARCHAR(200),
    lnum DECIMAL(10,2) NOT NULL,
    data TEXT NOT NULL,
    body TEXT,
    page_ref VARCHAR(20),
    PRIMARY KEY (dict_id, lnum)
);

-- Headword index for fast lookup
CREATE TABLE IF NOT EXISTS headwords (
    dict_id VARCHAR(20) NOT NULL,
    key VARCHAR(200) NOT NULL,
    key_normalized VARCHAR(200) NOT NULL,
    lnum DECIMAL(10,2) NOT NULL,
    is_primary BOOLEAN NOT NULL DEFAULT true,
    FOREIGN KEY (dict_id, lnum) REFERENCES entries(dict_id, lnum)
);

-- Dictionary metadata from TEI headers
CREATE TABLE IF NOT EXISTS dict_metadata (
    dict_id VARCHAR(20) PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    short_title VARCHAR(200),
    author VARCHAR(500),
    publisher VARCHAR(500),
    pub_place VARCHAR(200),
    year INTEGER,
    description TEXT,
    source_url VARCHAR(500),
    encoding_date VARCHAR(50),
    license TEXT
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_headwords_dict_key ON headwords(dict_id, key_normalized);
CREATE INDEX IF NOT EXISTS idx_entries_dict_lnum ON entries(dict_id, lnum);
