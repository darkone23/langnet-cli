# Tool Fact Indexing: Implementation Roadmap

**Status**: Active Plan
**Date**: 2026-02-15
**Priority**: HIGH
**Related**: `tool-fact-architecture.md`, `tool-response-pipeline.md`, `tool-fact-flow.md`

## Note

This roadmap should be read alongside `tool-response-pipeline.md`, which defines the 5-stage pipeline:

```
Tool Call → Raw Response → Extractions → Derivations → Claims
```

The phases below map to these stages:
- Phase 1-2: Define proto schemas for all 5 stages
- Phase 3: Implement extraction and derivation stages
- Phase 4: Wire pipeline to query flow
- Phase 5: Build transformation layer (Derivation → Claim)
- Phase 6: Integration testing

## Goal

Implement an index-first query architecture where each tool emits canonical facts that are indexed with full provenance. Queries hit the index first, only fetching from tools on cache miss or explicit refresh.

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Raw response storage | Yes (optional) | Enables parser iteration, re-extraction |
| Provenance granularity | Request-level | One URL produces many facts |
| Index strategy | Lazy + manual refresh | No upfront cost, `--refresh` for stale data |
| Tool-specific fields | Stay in tool-spec | Not promoted to universal layer |

## Prerequisites

- [x] Architecture documented (`tool-fact-architecture.md`)
- [x] Mermaid diagrams created (`tool-fact-flow.md`)
- [ ] Proto build system verified (`just codegen` works)
- [ ] Entry parsing layer designed (`entry-parsing.md`)

## Phase 1: Proto Schema Definition (2-3 days)

### 1.1 Create Provenance Proto

Create `vendor/langnet-spec/schema/provenance.proto`:

```protobuf
syntax = "proto3";
package langnet_spec;

message ProvenanceRecord {
  string provenance_id = 1;
  string source = 2;
  string source_ref = 3;
  string request_url = 4;
  string raw_ref = 5;
  string extracted_at = 6;
  string tool_version = 7;
  map<string, string> metadata = 8;
}

message RawResponse {
  string raw_ref = 1;
  string source = 2;
  string request_url = 3;
  bytes response_data = 4;
  string fetched_at = 5;
  string response_hash = 6;
}
```

### 1.2 Create Tool-Specific Proto Schemas

Create `vendor/langnet-spec/schema/tools/` directory:

**cdsl_spec.proto**:
```protobuf
syntax = "proto3";
package langnet_spec;

message CDSLSenseFact {
  string fact_id = 1;
  string lemma = 2;
  string gloss = 3;
  string pos = 4;
  string gender = 5;
  string root = 6;
  string source_ref = 7;
  repeated string sense_lines = 8;
  repeated string domains = 9;
  repeated string register = 10;
  string provenance_id = 11;
}
```

**diogenes_spec.proto**:
```protobuf
syntax = "proto3";
package langnet_spec;

message DiogenesMorphFact {
  string fact_id = 1;
  string surface = 2;
  repeated string lemmas = 3;
  repeated string tags = 4;
  repeated string defs = 5;
  string reference_id = 6;
  string logeion_link = 7;
  bool is_fuzzy_match = 8;
  string provenance_id = 9;
}

message DiogenesDictFact {
  string fact_id = 1;
  string entry_id = 2;
  string entry_text = 3;
  string term = 4;
  string reference_id = 5;
  string provenance_id = 6;
}

message DiogenesCitationFact {
  string fact_id = 1;
  string entry_id = 2;
  string cts_urn = 3;
  string text = 4;
  string author = 5;
  string work = 6;
  string provenance_id = 7;
}
```

### 1.3 Deliverables

- [ ] `provenance.proto` created
- [ ] `tools/cdsl_spec.proto` created
- [ ] `tools/diogenes_spec.proto` created
- [ ] `tools/heritage_spec.proto` created
- [ ] `tools/whitakers_spec.proto` created
- [ ] `tools/cltk_spec.proto` created
- [ ] `just codegen` produces Python packages
- [ ] Tests: proto serialization/deserialization

---

## Phase 2: Fact Indexer Implementation (3-4 days)

### 2.1 Create Indexer Module

```
src/langnet/fact_index/
├── __init__.py
├── types.py           # Fact, Provenance dataclasses
├── indexer.py         # FactIndexer class
├── storage.py         # DuckDB storage layer
├── raw_store.py       # Raw response storage
└── lookup.py          # Index lookup functions
```

### 2.2 DuckDB Schema

```sql
CREATE TABLE raw_responses (
    raw_ref VARCHAR PRIMARY KEY,
    source VARCHAR NOT NULL,
    request_url VARCHAR NOT NULL,
    response_data BLOB,
    fetched_at TIMESTAMP,
    response_hash VARCHAR
);

CREATE TABLE tool_facts (
    fact_id VARCHAR PRIMARY KEY,
    tool VARCHAR NOT NULL,
    fact_type VARCHAR NOT NULL,
    subject VARCHAR NOT NULL,
    predicate VARCHAR NOT NULL,
    fact_data BLOB,
    provenance_id VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE provenance_records (
    provenance_id VARCHAR PRIMARY KEY,
    source VARCHAR NOT NULL,
    source_ref VARCHAR,
    request_url VARCHAR,
    raw_ref VARCHAR,
    extracted_at TIMESTAMP,
    tool_version VARCHAR,
    metadata JSON
);

CREATE TABLE fact_index (
    subject VARCHAR,
    predicate VARCHAR,
    tool VARCHAR,
    fact_id VARCHAR,
    provenance_id VARCHAR,
    PRIMARY KEY (subject, predicate, tool)
);
```

### 2.3 Deliverables

- [ ] `fact_index/types.py` with Fact, Provenance dataclasses
- [ ] `fact_index/storage.py` with DuckDB schema
- [ ] `fact_index/raw_store.py` with compression
- [ ] `fact_index/indexer.py` with FactIndexer class
- [ ] Tests: index, lookup, delete, raw storage

---

## Phase 3: Adapter Fact Extraction (4-5 days)

### 3.1 Update Diogenes Adapter

```python
class DiogenesAdapter:
    def extract_facts(self, raw_response: bytes, provenance: ProvenanceRecord) -> list[Fact]:
        facts = []
        parsed = self._parse_response(raw_response)
        
        for chunk in parsed.chunks:
            if isinstance(chunk, PerseusAnalysisHeader):
                for morph in chunk.morphology.morphs:
                    facts.append(self._make_morph_fact(morph, provenance))
            elif isinstance(chunk, DiogenesMatchingReference):
                for block in chunk.definitions.blocks:
                    facts.append(self._make_dict_fact(block, provenance))
                    facts.extend(self._make_citation_facts(block, provenance))
        
        return facts
```

### 3.2 Deliverables

- [ ] Diogenes adapter emits DiogenesMorphFact, DiogenesDictFact, DiogenesCitationFact
- [ ] CDSL adapter emits CDSLSenseFact, CDSLEntryFact
- [ ] Heritage adapter emits HeritageMorphFact, HeritageDictFact
- [ ] Whitakers adapter emits WhitakersAnalysisFact
- [ ] CLTK adapter emits CLTKMorphFact, CLTKLewisFact
- [ ] Tests: per-adapter fact extraction with fixtures

---

## Phase 4: Query Flow Integration (2-3 days)

### 4.1 Update LanguageEngine

```python
class LanguageEngine:
    def handle_query(self, language: str, query: str, refresh: bool = False) -> QueryResponse:
        normalized = self.normalize(query, language)
        
        if not refresh:
            facts = self.fact_indexer.lookup(normalized)
            if facts:
                return self._build_response(facts)
        
        all_facts = []
        for adapter in self._get_adapters(language):
            raw_response = adapter.fetch(normalized)
            provenance = self._create_provenance(adapter, normalized)
            facts = adapter.extract_facts(raw_response, provenance)
            self.fact_indexer.index(facts, provenance, raw_response)
            all_facts.extend(facts)
        
        return self._build_response(all_facts)
```

### 4.2 CLI Commands

| Command | Description |
|---------|-------------|
| `langnet query <word>` | Query with index lookup |
| `langnet query <word> --refresh` | Force re-fetch and re-index |
| `langnet index warm <file>` | Pre-build index for lemma list |
| `langnet index refresh <lemma>` | Refresh single lemma |
| `langnet index stats` | Show index statistics |

### 4.3 Deliverables

- [ ] LanguageEngine uses FactIndexer
- [ ] `--refresh` flag forces re-fetch
- [ ] `langnet index warm` command
- [ ] `langnet index stats` command
- [ ] Tests: index hit path, index miss path, refresh flag

---

## Phase 5: Transformation Layer (2-3 days)

### 5.1 Fact-to-Claim Transformer

```python
TRANSFORM_RULES = {
    'CDSLSenseFact': {
        'predicate': 'has_gloss',
        'value_fields': ['gloss', 'domains', 'register'],
    },
    'DiogenesDictFact': {
        'predicate': 'has_gloss',
        'value_fields': ['entry_text', 'entry_id'],
    },
    'DiogenesCitationFact': {
        'predicate': 'has_citation',
        'value_fields': ['cts_urn', 'text', 'author', 'work'],
    },
    'HeritageMorphFact': {
        'predicate': 'has_morphology',
        'value_fields': ['lemma', 'pos', 'stem'],
        # Note: color, color_meaning NOT promoted (tool-specific)
    },
}
```

### 5.2 Deliverables

- [ ] Transformation rules for all fact types
- [ ] `transform_to_claims()` function
- [ ] Semantic reducer accepts Claims
- [ ] Tests: fact-to-claim transformation

---

## Phase 6: Integration Testing (2-3 days)

### 6.1 Test Scenarios

1. **Index hit path**: Query for already-indexed lemma
2. **Index miss path**: Query triggers fetch + extract + index
3. **Refresh flow**: `--refresh` deletes and re-fetches
4. **Raw response reparse**: Stored raw can be re-parsed with improved parser
5. **Snapshot tests**: Fact extraction is deterministic

### 6.2 Deliverables

- [ ] End-to-end tests for each adapter
- [ ] Refresh flow test
- [ ] Raw response reparse test
- [ ] Snapshot tests for fact extraction
- [ ] Performance benchmarks

---

## Verification Checklist

- [ ] Proto files in `vendor/langnet-spec/schema/`
- [ ] `just codegen` produces valid Python
- [ ] DuckDB schema created and migrated
- [ ] All adapters emit typed facts
- [ ] Index lookup works (hit path)
- [ ] Index miss triggers fetch + extract + index
- [ ] `--refresh` flag deletes and re-fetches
- [ ] Transformation layer produces Claims
- [ ] Semantic reducer consumes Claims
- [ ] Raw responses stored and re-parseable
- [ ] Tests pass: unit, integration, snapshot

---

## Configuration Summary

| Setting | Development | Production |
|---------|-------------|------------|
| `store_raw_responses` | `true` | `false` (optional) |
| `index_path` | `~/.local/share/langnet/fact-index.duckdb` | same |
| `compression` | `zstd` | `zstd` |

---

## Related Documents

- `docs/technical/design/tool-fact-architecture.md` - Architecture overview
- `docs/technical/design/mermaid/tool-fact-flow.md` - Diagrams
- `docs/technical/design/entry-parsing.md` - Entry parsing (prerequisite)
- `docs/technical/backend/tool-capabilities.md` - Per-tool expectations