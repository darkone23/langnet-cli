# Tool Fact Flow Diagrams

Mermaid diagrams for the tool fact extraction and indexing architecture.

## 1. Two-Layer Proto Architecture

```mermaid
flowchart TB
    subgraph Tools["Tool Layer"]
        CD[CDSL Adapter]
        DG[Diogenes Adapter]
        WW[Whitakers Adapter]
        HV[Heritage Adapter]
        CK[CLTK Adapter]
    end
    
    subgraph ToolSpecs["Tool-Specific Proto Schemas"]
        CSP[cdsl_spec.proto<br/>CDSLSenseFact, CDSLEntryFact]
        DSP[diogenes_spec.proto<br/>DiogenesMorphFact, DiogenesDictFact, DiogenesCitationFact]
        WSP[whitakers_spec.proto<br/>WhitakersAnalysisFact, WhitakersTermFact]
        HVP[heritage_spec.proto<br/>HeritageMorphFact, HeritageDictFact, HeritageColorFact]
        CKP[cltk_spec.proto<br/>CLTKMorphFact, CLTKLewisFact]
    end
    
    subgraph Storage["Raw Response Storage"]
        RS[Raw Responses<br/>DuckDB BLOB]
    end
    
    subgraph Index["Fact Index (DuckDB)"]
        FI[Indexed Facts<br/>+ Provenance]
    end
    
    subgraph Transform["Transformation Layer"]
        TX[Fact to Claim<br/>Transform]
    end
    
    subgraph Universal["Universal Layer"]
        LS[langnet_spec.proto<br/>QueryResponse]
    end
    
    CD --> CSP
    DG --> DSP
    WW --> WSP
    HV --> HVP
    CK --> CKP
    
    CSP --> RS
    DSP --> RS
    WSP --> RS
    HVP --> RS
    CKP --> RS
    
    RS --> FI
    FI --> TX
    TX --> LS
```

## 2. Index-First Query Flow

```mermaid
sequenceDiagram
    participant U as User
    participant CLI as CLI/API
    participant QH as QueryHandler
    participant IDX as FactIndex
    participant ADP as ToolAdapter
    participant RAW as RawStorage
    participant EXT as FactExtractor
    participant TX as Transformer
    participant RED as Reducer
    
    U->>CLI: query(lemma, mode, view)
    CLI->>QH: handle_query(lemma)
    
    QH->>IDX: lookup(lemma)
    
    alt Index Hit (facts exist)
        IDX-->>QH: facts[] + provenance[]
        Note over QH: Skip tool fetch
    else Index Miss (no facts)
        QH->>ADP: fetch(lemma)
        ADP->>ADP: build_url(lemma)
        ADP->>RAW: http_get(url)
        RAW-->>ADP: response (HTML/JSON)
        ADP->>RAW: store_raw(response)
        RAW-->>ADP: raw_ref
        ADP->>EXT: extract_facts(response, raw_ref)
        EXT-->>ADP: tool_facts[] + provenance
        ADP->>IDX: index(tool_facts, provenance)
        IDX-->>QH: facts[] + provenance[]
    end
    
    QH->>TX: transform_to_claims(facts[])
    TX-->>QH: claims[]
    
    QH->>RED: reduce(claims[], mode)
    RED-->>QH: buckets + constants
    
    QH-->>CLI: QueryResponse
    CLI-->>U: formatted output
```

## 3. Provenance Chain Detail

```mermaid
flowchart LR
    subgraph Request["HTTP Request"]
        R1["request_url<br/>/Perseus.cgi?do=parse&lang=lat&q=lupus"]
        R2["request_timestamp<br/>2026-02-15T10:30:00Z"]
        R3["tool_version<br/>diogenes-3.2"]
    end
    
    subgraph Storage["Raw Response Storage"]
        S1["raw_response<br/>HTML stored as BLOB"]
        S2["raw_ref<br/>sha256:a1b2c3..."]
        S3["stored_at<br/>2026-02-15T10:30:01Z"]
    end
    
    subgraph Extraction["Fact Extraction"]
        E1["Lark Parser<br/>Diogenes Grammar"]
    end
    
    subgraph Prov["Provenance Record"]
        P1["provenance_id: uuid-1234"]
        P2["source: diogenes"]
        P3["source_ref: dg:55038347"]
        P4["request_url: /Perseus.cgi?..."]
        P5["raw_ref: sha256:a1b2c3..."]
        P6["extracted_at: 2026-02-15T10:30:02Z"]
        P7["tool_version: diogenes-3.2"]
        P8["metadata: {is_fuzzy: false}"]
    end
    
    subgraph Facts["Derived Facts"]
        F1["MorphFact<br/>fact_id: f1<br/>subject: lupus"]
        F2["DictFact<br/>fact_id: f2<br/>subject: lupus"]
        F3["CitationFact<br/>fact_id: f3<br/>subject: lupus"]
    end
    
    R1 --> S1
    R2 --> P6
    S1 --> S2
    S2 --> P5
    S1 --> E1
    E1 --> F1
    E1 --> F2
    E1 --> F3
    P1 --> F1
    P1 --> F2
    P1 --> F3
```

## 4. Tool Fact Types ER Diagram

```mermaid
erDiagram
    CDSLSenseFact {
        string lemma PK
        string gloss
        string pos
        string gender
        string root
        string source_ref "mw:217497"
        string[] sense_lines
        string[] domains
        string[] register
        string provenance_id FK
    }
    
    DiogenesMorphFact {
        string surface PK
        string[] lemmas
        string[] tags
        string[] defs
        string reference_id
        string logeion_link
        bool is_fuzzy_match
        string provenance_id FK
    }
    
    DiogenesDictFact {
        string entry_id PK
        string entry_text
        string term
        string reference_id
        string provenance_id FK
    }
    
    HeritageMorphFact {
        string word PK
        string lemma
        string root
        string pos
        string color
        string color_meaning
        string stem
        string provenance_id FK
    }
    
    WhitakersAnalysisFact {
        string surface PK
        string lemma
        string pos
        json features
        string[] senses
        string provenance_id FK
    }
    
    ProvenanceRecord {
        string provenance_id PK
        string source
        string source_ref
        string request_url
        string raw_ref FK
        timestamp extracted_at
        string tool_version
    }
    
    RawResponse {
        string raw_ref PK
        string source
        blob response_data
        timestamp fetched_at
    }
    
    CDSLSenseFact ||--|| ProvenanceRecord : has
    DiogenesMorphFact ||--|| ProvenanceRecord : has
    DiogenesDictFact ||--|| ProvenanceRecord : has
    HeritageMorphFact ||--|| ProvenanceRecord : has
    WhitakersAnalysisFact ||--|| ProvenanceRecord : has
    ProvenanceRecord ||--|| RawResponse : references
```

## 5. Index Schema ER Diagram

```mermaid
erDiagram
    raw_responses {
        varchar raw_ref PK
        varchar source
        varchar request_url
        blob response_data
        timestamp fetched_at
        varchar response_hash
    }
    
    tool_facts {
        varchar fact_id PK
        varchar tool
        varchar fact_type
        varchar subject
        varchar predicate
        blob fact_data
        varchar provenance_id FK
    }
    
    provenance_records {
        varchar provenance_id PK
        varchar source
        varchar source_ref
        varchar request_url
        varchar raw_ref FK
        timestamp extracted_at
        varchar tool_version
        json metadata
    }
    
    fact_index {
        varchar subject PK
        varchar predicate PK
        varchar tool PK
        varchar fact_id FK
        varchar provenance_id FK
    }
    
    index_metadata {
        varchar tool PK
        timestamp last_built
        integer fact_count
        varchar tool_version
        integer build_duration_ms
    }
    
    raw_responses ||--o{ provenance_records : "has many"
    provenance_records ||--o{ tool_facts : "has many"
    tool_facts ||--o{ fact_index : "indexed in"
    provenance_records ||--o{ fact_index : "provenance for"
```

## 6. Fact to Claim Transformation

```mermaid
flowchart TB
    subgraph ToolFacts["Tool-Specific Facts"]
        TF1["CDSLSenseFact<br/>lemma=agni<br/>gloss=fire<br/>source_ref=mw:217497"]
        TF2["DiogenesDictFact<br/>entry_id=00:01<br/>entry_text=wolf...<br/>reference_id=55038347"]
        TF3["HeritageMorphFact<br/>word=ziva<br/>lemma=ziva<br/>color=blue"]
        TF4["DiogenesCitationFact<br/>cts_urn=urn:cts:...<br/>text=..."]
    end
    
    subgraph Rules["Transformation Rules"]
        R1["has_gloss<br/>gloss, domains, register"]
        R2["has_gloss<br/>gloss, sense_id"]
        R3["has_morphology<br/>lemma, pos, features"]
        R4["has_citation<br/>cts_urn, text, author"]
    end
    
    subgraph Claims["Universal Claims"]
        C1["Claim<br/>subject=agni<br/>predicate=has_gloss<br/>value={gloss: 'fire'}<br/>provenance=mw:217497"]
        C2["Claim<br/>subject=lupus<br/>predicate=has_gloss<br/>value={gloss: 'wolf'}<br/>provenance=dg:55038347"]
        C3["Claim<br/>subject=ziva<br/>predicate=has_morphology<br/>value={lemma: 'ziva', pos: 'noun'}<br/>provenance=heritage:..."]
        C4["Claim<br/>subject=lupus<br/>predicate=has_citation<br/>value={cts_urn: '...'}<br/>provenance=dg:55038347"]
    end
    
    TF1 --> R1 --> C1
    TF2 --> R2 --> C2
    TF3 --> R3 --> C3
    TF4 --> R4 --> C4
```

## 7. Refresh Flow

```mermaid
flowchart TD
    U[User] -->|query --refresh| CLI[CLI/API]
    CLI --> QH[QueryHandler]
    
    QH -->|force skip| IDX{Index Lookup}
    
    IDX -->|always miss| ADP[ToolAdapter]
    
    ADP -->|fetch| URL[HTTP Request]
    URL -->|response| RAW[Raw Response]
    
    RAW -->|store| STO[RawStorage]
    STO -->|raw_ref| PROV[Create Provenance]
    
    RAW -->|parse| EXT[FactExtractor]
    EXT -->|facts| PROV
    
    PROV -->|delete old| DEL[Delete Old Index]
    DEL -->|write new| WRITE[Write New Index]
    
    WRITE -->|facts + provenance| TX[Transformer]
    TX -->|claims| RED[Reducer]
    RED -->|response| U
```

## 8. Pre-Build (Warm) Flow

```mermaid
flowchart TD
    subgraph Offline["Offline Pre-Build"]
        LIST[lemma_list.txt] --> JUST[just index-warm]
        JUST --> READ[Read List]
        READ --> LOOP{For Each Lemma}
    end
    
    subgraph Online["Online Fetch"]
        LOOP -->|next| FETCH[ToolAdapter.fetch]
        FETCH --> STORE[Store Raw]
        STORE --> EXTRACT[Extract Facts]
        EXTRACT --> INDEX[Index Write]
        INDEX --> LOOP
    end
    
    subgraph Output["Build Output"]
        LOOP -->|done| META[Update Metadata]
        META --> STATS[Log Statistics]
        STATS --> DONE[Index Ready]
    end
```

## 9. Parser Iteration Flow

One of the key benefits of storing raw responses is the ability to iterate on parsers without re-fetching:

```mermaid
flowchart TD
    subgraph Problem["Parser Improvement"]
        BUG[Bug Found in Parser]
        FIX[Fix Parser Code]
        TEST[Test on Sample]
    end
    
    subgraph ReExtraction["Re-Extraction"]
        FIX -->|ready| RE[Re-Extract Command]
        RE --> RAW[Load Raw Responses]
        RAW --> NEW[New Fact Extractor]
        NEW --> COMP{Compare Facts}
    end
    
    subgraph Validation["Validation"]
        COMP -->|diff| DIFF[Show Differences]
        DIFF -->|accept| UPDATE[Update Index]
        DIFF -->|reject| ROLLBACK[Keep Old Facts]
    end
    
    UPDATE --> DONE[Parser Iteration Complete]
```

## 10. Multi-Tool Query Flow

When a query requires multiple tools (e.g., Latin word needs both Diogenes and Whitakers):

```mermaid
sequenceDiagram
    participant QH as QueryHandler
    participant IDX as FactIndex
    participant DG as Diogenes
    participant WW as Whitakers
    participant TX as Transformer
    participant RED as Reducer
    
    QH->>IDX: lookup(lupus)
    IDX-->>QH: partial hit (DG only)
    
    Note over QH: Need Whitakers morphology
    
    par Parallel Fetch
        QH->>DG: skip (already indexed)
        QH->>WW: fetch(lupus)
    end
    
    WW-->>QH: raw_response
    QH->>WW: extract_facts
    WW-->>QH: morph_facts[]
    QH->>IDX: index(morph_facts)
    
    IDX-->>QH: all_facts[] + provenance[]
    
    QH->>TX: transform(all_facts)
    TX-->>QH: claims[]
    QH->>RED: reduce(claims[])
    RED-->>QH: buckets + constants
```
