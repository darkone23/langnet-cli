# V2 Implementation Master Plan

**Status**: Active
**Date**: 2026-02-15
**Priority**: CRITICAL
**Owner**: Architecture Team

## Overview

This document is the single source of truth for V2 implementation. A new developer should be able to read this and understand:
1. What we're building
2. Why we're building it this way
3. How the pieces fit together
4. Where to start

## Codebase Organization

The V1 codebase is preserved as a **working sketch** in `codesketch/` at project root:

```
langnet-cli/
├── codesketch/                # V1 "working sketch" - reference only
│   ├── src/langnet/           # Existing adapters, parsers, etc.
│   ├── examples/
│   └── tests/
├── src/langnet/               # Clean implementation
│   ├── storage/               # DuckDB storage layer
│   ├── normalizer/            # Query normalization (port from codesketch)
│   ├── registry/              # Tool registry
│   ├── planner/               # Query planner
│   ├── executor/              # Plan executor
│   ├── processor/             # Response processor
│   ├── extractors/            # Per-tool extractors
│   ├── derivators/            # Per-tool derivators
│   ├── hydration/             # Reference hydration
│   ├── transform/             # Claim transformation
│   └── pipeline/              # Pipeline orchestrator
└── ...
```

**Key principle**: Build fresh in `src/langnet/`. Study `codesketch/` to understand what worked, then implement with the new architecture. Some code (normalization, clustering) will be ported; most will be rewritten.

## Executive Summary

V2 introduces a **layered pipeline architecture** where a query produces **effects** that are parsed, reduced, and distilled:

```
Query → Effects → Parse → Reduce → Distill → Output
          │
          ├── Tool calls (cdsl, diogenes, heritage, ...)
          ├── Raw responses stored
          ├── Extractions derived
          └── Claims transformed
```

**Effects**: The observable consequences of executing a query - tool calls made, responses received, facts extracted, claims derived. Each effect is traceable through the full provenance chain.

**Pipeline stages process effects**:
- **Parse**: Extract structure from raw effects (HTML → blocks, XML → entries)
- **Reduce**: Collapse similar effects into buckets (10 glosses → 3 clusters)
- **Distill**: Produce final output with semantic constants

**Key improvements over V1**:
- Query planning is decoupled from execution
- Raw responses are stored (enables re-parsing)
- Extraction and derivation are separate stages
- Hydration (expanding refs) is separate from reduction (condensing)
- Caches are transparent and disposable
- Full provenance chain from query to claim

## Architecture Documents

| Document | Purpose | Read Order |
|----------|---------|------------|
| `v2-architecture-overview.md` | High-level summary, pipeline diagram | 1st |
| `query-planning.md` | Stages -1, 0: Query normalization, planning, caching | 2nd |
| `tool-response-pipeline.md` | Stages 1-5: Tool calls through claims | 3rd |
| `hydration-reduction.md` | Stages 4.5, 6: Hydration and reduction | 4th |
| `tool-fact-architecture.md` | Tool-specific fact types | Reference |
| `entry-parsing.md` | Lark grammars for extraction/derivation | Reference |

## Core Concepts

### 1. Effects

A **query produces effects** - the observable consequences of execution:

| Effect Type | Description | Example |
|-------------|-------------|---------|
| ToolCallEffect | HTTP request to a tool | `GET /sktreader?q=agni` |
| RawResponseEffect | Response received and stored | XML blob with entry_id=217497 |
| ExtractionEffect | Format-parsed structure | `{headword: "agni", sense_lines: [...]}` |
| DerivationEffect | Content-parsed fact | `CDSLSenseFact(gloss="fire")` |
| ClaimEffect | Universal claim | `Claim(predicate=has_gloss, value={...})` |

**Effect chain for query "agni" (Sanskrit)**:

```
Query: "agni"
  │
  ├── ToolCallEffect: cdsl GET /sktreader?q=agni
  │     └── RawResponseEffect: XML <entry id="217497">...</entry>
  │           └── ExtractionEffect: {headword: "agni", sense_lines: [...]}
  │                 └── DerivationEffect: CDSLSenseFact(gloss="fire", pos="noun")
  │                       └── ClaimEffect: Claim(subject="agni", predicate=has_gloss)
  │
  ├── ToolCallEffect: heritage GET /morph?q=agni
  │     └── RawResponseEffect: JSON {analyses: [...]}
  │           └── ExtractionEffect: {lemma: "agni", stem: "agni"}
  │                 └── DerivationEffect: HeritageMorphFact(pos="noun", gender="masc")
  │                       └── ClaimEffect: Claim(subject="agni", predicate=has_morphology)
  │
  └── [Effects collected and reduced]
        └── Buckets: [{gloss: "fire, sacrificial fire", witnesses: [mw, heritage]}]
```

**Effect properties**:
- **Traceable**: Each effect has a unique ID and provenance chain
- **Immutable**: Once recorded, effects don't change
- **Cacheable**: Effects can be looked up by ID
- **Disposable**: Cached effects can be wiped and recomputed

**Lexicon Artifacts**: Extractions produce tool-specific artifacts:

| Tool | Artifact Type | Content |
|------|---------------|---------|
| cdsl | CDSLArtifact | XML entries with headword, sense_lines, grammar_refs |
| diogenes | DiogenesArtifact | HTML blocks with entry_text, citations |
| heritage | HeritageArtifact | JSON analyses with lemma, pos, morphology |
| whitakers | WhitakersArtifact | Parsed lines with surface, lemma, features |
| cltk | CLTKArtifact | Morphology results with lemma, gloss |
| cts_index | CitationArtifact | URN lookups with text, author, work |

### 2. Pipeline Stages

The pipeline processes effects through three phases: Parse, Reduce, Distill.

```
Stage -1: User Input        "shiva", "lupus", "λόγος"
Stage  0: Query Planning    → ToolPlan (which effects to produce)
Stage  0.5: Plan Execution  → Execute plan → Produce effects
          ─────────────────────────────────────────────
          PARSE PHASE (extract structure from effects)
          ─────────────────────────────────────────────
Stage  1: Tool Calls        → ToolCallEffect
Stage  2: Raw Responses     → RawResponseEffect (stored)
Stage  3: Extractions       → ExtractionEffect (format parsing)
Stage  4: Derivations       → DerivationEffect (content parsing)
          ─────────────────────────────────────────────
          REDUCE PHASE (collapse similar effects)
          ─────────────────────────────────────────────
Stage  5: Claims            → ClaimEffect (universal layer)
Stage  6: Buckets           → Clustered claims
          ─────────────────────────────────────────────
          DISTILL PHASE (produce final output)
          ─────────────────────────────────────────────
Output: QueryResponse with senses, citations, provenance
```

### 3. Cache Layers

| Layer | Maps | Disposable? |
|-------|------|-------------|
| Query Cache | Query string → ToolPlan | Yes (re-plan) |
| Plan Cache | Plan hash → Response IDs | Yes (re-execute) |
| Derivation Cache | Response ID → Derivations | Yes (re-parse) |
| Claim Cache | Derivation IDs → Claims | Yes (re-transform) |

**Key invariant**: Wiping any cache is safe. Only cost is recomputation time.

### 3. Storage vs Cache

| Storage (Keep) | Cache (Disposable) |
|----------------|-------------------|
| Raw responses | Query → Plan |
| Tool calls (audit) | Plan → Response IDs |
| Provenance records | Derivations |
| | Claims |

### 4. Hydration vs Reduction

| Operation | Direction | Example |
|-----------|-----------|---------|
| Hydration | Expand | CTS URN → citation text (via cts_index tool) |
| Reduction | Condense | 10 glosses → 3 buckets |

**Hydration is just a tool call**: The CTS index is a tool like any other. It takes a URN as input and produces citation data. The distinction is conceptual:
- Most tools (cdsl, diogenes, heritage) take a lemma and produce glosses/morphology
- The cts_index tool takes a URN and produces citation text/author/work

Both follow the same pipeline: Tool Call → Raw Response → Extraction → Derivation → Claims.

## Design Principles

### 1. Schema-Driven Design

**Schemas before code.** Every component is defined by its data contract first:

```
Proto Schema → Code Generation → Implementation
```

**Workflow**:
1. Define the schema (proto, JSON Schema, or dataclass)
2. Generate types if needed (`just codegen`)
3. Write tests against the schema
4. Implement code to satisfy the schema

**Why**:
- Schemas are the contract between components
- Schemas enable independent development
- Schemas make integration explicit
- Schemas are documentation that stays in sync

**Example**:
```
1. Define: query_spec.proto with NormalizedQuery, ToolPlan
2. Generate: Python classes from proto
3. Test: Write tests that construct ToolPlan objects
4. Implement: QueryPlanner that produces ToolPlan
```

**Schema Files**:
```
vendor/langnet-spec/schema/
├── langnet_spec.proto      # Universal layer (exists)
├── provenance.proto        # ProvenanceRecord, ProvenanceChain
├── query_spec.proto        # NormalizedQuery, ToolPlan, ToolCallSpec
├── response.proto          # RawResponse, ToolResponseRef
├── extraction.proto        # Extraction, ExtractionMetadata
└── tools/
    ├── cdsl_spec.proto
    ├── diogenes_spec.proto
    ├── heritage_spec.proto
    ├── whitakers_spec.proto
    └── cltk_spec.proto
```

### 2. Cache Transparency

Caches are lazy-loaded and disposable. See `query-planning.md` for details.

### 3. Separation of Concerns

Each stage has a single responsibility:
- Planner: Decide what to call
- Executor: Call tools, store responses
- Processor: Parse responses into facts
- Hydrator: Expand references
- Reducer: Cluster into buckets

### 4. DuckDB Index Architecture

Multiple DuckDB files, not a single monolithic database:

```
~/.local/share/langnet/
├── langnet.duckdb              # Cross-tool indexes
│   ├── query_cache             # Query → Plan
│   ├── plan_cache              # Plan → Response IDs
│   ├── claims                  # Universal claims
│   ├── provenance              # Full provenance chains
│   └── buckets                 # Reduced buckets (cached)
│
└── tools/
    ├── cdsl.duckdb             # CDSL-specific data
    │   ├── raw_responses       # XML responses
    │   ├── extractions         # Parsed entries
    │   └── derivations         # CDSLSenseFact, etc.
    │
    ├── diogenes.duckdb         # Diogenes-specific data
    │   ├── raw_responses       # HTML responses
    │   ├── extractions         # Parsed blocks
    │   └── derivations         # DiogenesDictFact, etc.
    │
    ├── heritage.duckdb         # Heritage-specific data
    │   ├── raw_responses       # JSON responses
    │   ├── extractions         # Parsed analyses
    │   └── derivations         # HeritageMorphFact, etc.
    │
    ├── whitakers.duckdb        # Whitakers-specific data
    │   ├── raw_responses       # Text responses
    │   ├── extractions         # Parsed lines
    │   └── derivations         # WhitakersAnalysisFact
    │
    ├── cltk.duckdb             # CLTK-specific data
    │   ├── raw_responses       # JSON responses
    │   ├── extractions         # Parsed objects
    │   └── derivations         # CLTKMorphFact
    │
    └── cts_index.duckdb        # CTS URN tool (hydrator)
        ├── raw_responses       # URN lookup results
        ├── extractions         # Parsed citation data
        └── derivations         # CitationFact (urn, text, author, work)
```

**CTS index is a tool**: It follows the same pipeline as other tools. Input is a URN, output is citation data. The term "hydration" is just shorthand for "calling the cts_index tool to expand a URN reference."

**Why separate databases**:

| Benefit | Description |
|---------|-------------|
| **Isolation** | Wipe one tool's data without affecting others |
| **Independence** | Each tool can grow at its own rate |
| **Portability** | Can copy/move a tool's DB independently |
| **Parallelism** | Multiple writers don't block each other |
| **Freshness** | Refresh a tool by deleting its DB |

**Cross-tool queries**:

The `langnet.duckdb` stores the integration layer:
- `query_cache` maps queries to plans (which reference multiple tools)
- `plan_cache` maps plans to response IDs across tools
- `claims` are the universal layer after transformation
- `provenance` chains span multiple tools

**Provenance chain example**:

```
Claim in langnet.duckdb:
  claim_id: "claim-001"
  subject: "agni"
  predicate: "has_gloss"
  provenance_chain: {
    derivation_id: "deriv-cdsl-123",  # Points to cdsl.duckdb
    response_id: "resp-cdsl-456",     # Points to cdsl.duckdb
    tool: "cdsl"
  }
```

**CLI commands**:

```bash
# Status of all indexes
langnet index status

# Status of specific tool
langnet index status --tool=cdsl

# Wipe a tool's data (safe, just re-parse)
langnet index clear --tool=diogenes

# Wipe langnet integration layer (re-run pipeline)
langnet index clear --langnet

# Full refresh (wipe everything)
langnet index clear --all
```

---

## Implementation Roadmap

**Each phase follows schema-driven design: define schemas → generate types → write tests → implement.**

### Phase 1: Foundation (Week 1-2)

**Goal**: Define all schemas, set up storage layer

**Schema-driven approach**: Define every proto before writing any implementation code.

#### 1.1 Proto Schemas

Create proto files in `vendor/langnet-spec/schema/`:

```
schema/
├── langnet_spec.proto      # Universal layer (exists)
├── provenance.proto        # ProvenanceRecord, ProvenanceChain
├── query_spec.proto        # NormalizedQuery, ToolPlan, ToolCallSpec
├── response.proto          # RawResponse, ToolResponseRef
├── extraction.proto        # Extraction, ExtractionMetadata
└── tools/
    ├── cdsl_spec.proto
    ├── diogenes_spec.proto
    ├── heritage_spec.proto
    ├── whitakers_spec.proto
    ├── cltk_spec.proto
    └── cts_index_spec.proto    # CTS URN tool
```

**Deliverables**:
- [ ] `query_spec.proto` with NormalizedQuery, ToolPlan, ToolCallSpec
- [ ] `response.proto` with RawResponse, ToolResponseRef
- [ ] `extraction.proto` with Extraction types
- [ ] `provenance.proto` with ProvenanceChain
- [ ] Tool-specific proto files for each tool (including cts_index)
- [ ] `just codegen` produces Python packages

#### 1.2 Storage Layer

Create `src/langnet/storage/` with multiple database classes:

```python
# storage/base.py
from filelock import FileLock

class BaseDB:
    """Base class for DuckDB storage with file-based locking."""
    
    def __init__(self, path: Path, read_only: bool = False):
        self.path = path
        self.read_only = read_only
        self.lock_path = path.with_suffix(path.suffix + ".lock")
        self.lock = FileLock(self.lock_path) if not read_only else None
        self.db = duckdb.connect(str(path), read_only=read_only)
        if not read_only:
            self._init_schema()
    
    def _init_schema(self) -> None: ...
    
    def close(self) -> None:
        self.db.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()

# storage/langnet_db.py
class LangnetDB(BaseDB):
    """Cross-tool indexes: query cache, plan cache, claims, provenance."""
    
    # Query cache (write needs lock)
    def get_cached_plan(self, query_hash: str) -> ToolPlan | None:
        # Read-only, no lock needed
        ...
    
    def cache_plan(self, query_hash: str, plan: ToolPlan) -> None:
        with self.lock:
            ...
    
    # Plan cache
    def get_cached_response_ids(self, plan_hash: str) -> dict[str, str] | None: ...
    def cache_response_ids(self, plan_hash: str, ids: dict[str, str]) -> None:
        with self.lock:
            ...
    
    # Claims (universal layer)
    def store_claims(self, claims: list[Claim]) -> None:
        with self.lock:
            ...
    
    def get_claims(self, subject: str) -> list[Claim]:
        # Read-only, no lock needed
        ...
    
    # Provenance
    def store_provenance(self, provenance: ProvenanceChain) -> None:
        with self.lock:
            ...

# storage/tool_db.py
class ToolDB(BaseDB):
    """Per-tool storage: raw responses, extractions, derivations."""
    
    def __init__(self, tool: str, path: Path, read_only: bool = False):
        self.tool = tool
        super().__init__(path, read_only=read_only)
    
    # Raw responses (storage, not cache) - writes need lock
    def store_raw_response(self, response: RawResponse) -> str:
        with self.lock:
            ...
    
    def get_raw_response(self, response_id: str) -> RawResponse | None:
        # Read-only, no lock needed
        ...
    
    # Extractions (cache) - writes need lock
    def get_extractions(self, response_id: str) -> list[Extraction] | None:
        # Read-only, no lock needed
        ...
    
    def store_extractions(self, response_id: str, extractions: list[Extraction]) -> None:
        with self.lock:
            ...
    
    # Derivations (cache) - writes need lock
    def get_derivations(self, response_id: str) -> list[Derivation] | None:
        # Read-only, no lock needed
        ...
    
    def store_derivations(self, response_id: str, derivations: list[Derivation]) -> None:
        with self.lock:
            ...

# storage/registry.py
class StorageRegistry:
    """Manages all database connections."""
    
    def __init__(self, base_path: Path, read_only: bool = False):
        self.langnet = LangnetDB(base_path / "langnet.duckdb", read_only=read_only)
        self.tools = {
            "cdsl": ToolDB("cdsl", base_path / "tools" / "cdsl.duckdb", read_only=read_only),
            "diogenes": ToolDB("diogenes", base_path / "tools" / "diogenes.duckdb", read_only=read_only),
            "heritage": ToolDB("heritage", base_path / "tools" / "heritage.duckdb", read_only=read_only),
            "whitakers": ToolDB("whitakers", base_path / "tools" / "whitakers.duckdb", read_only=read_only),
            "cltk": ToolDB("cltk", base_path / "tools" / "cltk.duckdb", read_only=read_only),
            "cts_index": ToolDB("cts_index", base_path / "tools" / "cts_index.duckdb", read_only=read_only),
        }
    
    def tool(self, name: str) -> ToolDB:
        return self.tools[name]
    
    def read_only_registry(self) -> "StorageRegistry":
        """Create a read-only view of the same databases."""
        return StorageRegistry(self.base_path, read_only=True)
```

**Locking semantics**:
- `filelock` provides cross-process synchronization via `.lock` files
- Readers never block (DuckDB supports concurrent reads)
- Writers acquire exclusive lock before write
- Read-only mode: no lock file created, no synchronization overhead

**Deliverables**:
- [ ] `BaseDB` class with filelock-based write synchronization
- [ ] `LangnetDB` class for cross-tool indexes
- [ ] `ToolDB` class for per-tool storage
- [ ] `StorageRegistry` to manage all connections
- [ ] Tests: store, retrieve, concurrent read, write locking

---

### Phase 2: Query Planning (Week 3-4)

**Goal**: Build query normalizer, planner, and executor

#### 2.1 Query Normalizer

Create `src/langnet/normalizer/`:

```python
# normalizer/core.py
class QueryNormalizer:
    """Normalize user queries to canonical forms."""
    
    def __init__(self):
        self.sanskrit = SanskritNormalizer()  # Use existing code
        self.greek = GreekNormalizer()
        self.latin = LatinNormalizer()
    
    def normalize(self, query: str, language: LanguageHint) -> NormalizedQuery:
        normalizer = self._get_normalizer(language)
        canonical = normalizer.normalize(query)
        return NormalizedQuery(
            original=query,
            language=language,
            canonical_forms=canonical.forms,
            normalizations=normalizer.steps
        )
```

**Reuse existing code**:
- `src/langnet/normalization/sanskrit.py` - SLP1, IAST, Velthuis conversions
- `src/langnet/heritage/velthuis_converter.py`
- `src/langnet/normalization/greek.py` - Betacode

**Deliverables**:
- [ ] `QueryNormalizer` class
- [ ] NormalizedQuery proto type
- [ ] Tests: "shiva" → ["śiva"], "λόγος" → ["λόγος", "λογοσ"]

#### 2.2 Tool Registry

Create `src/langnet/registry/`:

```python
# registry/tools.py
@dataclass
class ToolRegistryEntry:
    tool: str
    languages: list[str]
    query_format: str           # "slp1", "velthuis", "betacode", "ascii"
    endpoint_template: str
    response_format: str        # "xml", "html", "json", "text"
    priority: int
    optional: bool

TOOL_REGISTRY = {
    "cdsl": ToolRegistryEntry(
        tool="cdsl",
        languages=["san"],
        query_format="slp1",
        endpoint_template="http://localhost:48080/sktreader?q={query}",
        response_format="xml",
        priority=1,
        optional=False
    ),
    "heritage": ToolRegistryEntry(
        tool="heritage",
        languages=["san"],
        query_format="velthuis",
        endpoint_template="http://localhost:8080/morph?q={query}",
        response_format="json",
        priority=1,
        optional=False
    ),
    # ... diogenes, whitakers, cltk, cts_index
}
```

**Deliverables**:
- [ ] `ToolRegistryEntry` dataclass
- [ ] Registry for all 6 tools
- [ ] Query format transformers (IAST → SLP1, IAST → Velthuis, etc.)

#### 2.3 Query Planner

Create `src/langnet/planner/`:

```python
# planner/core.py
class QueryPlanner:
    """Build a declarative plan for tool execution."""
    
    def __init__(self, registry: dict[str, ToolRegistryEntry], normalizer: QueryNormalizer):
        self.registry = registry
        self.normalizer = normalizer
    
    def plan(self, query: str, language: LanguageHint) -> ToolPlan:
        # 1. Normalize
        normalized = self.normalizer.normalize(query, language)
        
        # 2. Find applicable tools
        tools = [t for t in self.registry.values() 
                 if language.value in t.languages or "*" in t.languages]
        
        # 3. Build call specs with transformed queries
        calls = []
        for tool in tools:
            tool_query = self._transform_query(normalized, tool)
            calls.append(ToolCallSpec(
                tool=tool.tool,
                call_id=str(uuid4()),
                endpoint=tool.endpoint_template.format(query=tool_query),
                params={"q": tool_query},
                expected_response_type=tool.response_format,
                priority=tool.priority,
                optional=tool.optional
            ))
        
        return ToolPlan(
            plan_id=str(uuid4()),
            query=normalized,
            tool_calls=calls,
            dependencies=[],
            created_at=datetime.now()
        )
```

**Deliverables**:
- [ ] `QueryPlanner` class
- [ ] Query format transformers
- [ ] Tests: "shiva" → plan with cdsl(Siva) + heritage(ziva)

#### 2.4 Plan Executor

Create `src/langnet/executor/`:

```python
# executor/core.py
class PlanExecutor:
    """Execute a tool plan, storing raw responses and yielding IDs."""
    
    def __init__(self, db: V2Database, http_client: httpx.Client):
        self.db = db
        self.http = http_client
    
    def execute(self, plan: ToolPlan, force_refresh: bool = False) -> ExecutedPlan:
        plan_hash = self._hash_plan(plan)
        
        # Check cache
        if not force_refresh:
            cached = self.db.get_cached_plan_responses(plan_hash)
            if cached:
                return ExecutedPlan(
                    plan_id=plan.plan_id,
                    plan_hash=plan_hash,
                    tool_response_ids=cached,
                    from_cache=True
                )
        
        # Execute tool calls
        response_ids = {}
        for spec in plan.tool_calls:
            response_id = self._execute_and_store(spec)
            response_ids[spec.tool] = response_id
        
        # Cache plan → response mapping
        self.db.cache_plan_responses(plan_hash, response_ids)
        
        return ExecutedPlan(
            plan_id=plan.plan_id,
            plan_hash=plan_hash,
            tool_response_ids=response_ids,
            from_cache=False
        )
    
    def _execute_and_store(self, spec: ToolCallSpec) -> str:
        # Make HTTP call
        response = self.http.get(spec.endpoint)
        
        # Store raw response
        raw = RawResponse(
            response_id=str(uuid4()),
            tool=spec.tool,
            request_url=spec.endpoint,
            response_data=response.content,
            content_type=response.headers.get("content-type"),
            status_code=response.status_code,
            fetched_at=datetime.now()
        )
        self.db.store_raw_response(raw)
        
        return raw.response_id
```

**Deliverables**:
- [ ] `PlanExecutor` class
- [ ] Cache resolution logic
- [ ] Tests: execute plan, cache hit on re-execute

---

### Phase 3: Response Processing (Week 5-7)

**Goal**: Extract and derive facts from raw responses

#### 3.1 Response Processor

Create `src/langnet/processor/`:

```python
# processor/core.py
class ResponseProcessor:
    """Process raw response IDs through extraction → derivation."""
    
    def __init__(self, db: V2Database, extractors: dict[str, Extractor], derivators: dict[str, Derivator]):
        self.db = db
        self.extractors = extractors
        self.derivators = derivators
    
    def process(self, response_refs: list[ToolResponseRef]) -> list[Derivation]:
        derivations = []
        
        for ref in response_refs:
            # Check cache
            cached = self.db.get_cached_derivations(ref.response_id)
            if cached:
                derivations.extend(cached)
                continue
            
            # Get raw response
            raw = self.db.get_raw_response(ref.response_id)
            
            # Extract (format parsing)
            extractor = self.extractors[raw.tool]
            extractions = extractor.extract(raw)
            
            # Derive (content parsing)
            derivator = self.derivators[raw.tool]
            new_derivations = derivator.derive(extractions)
            
            # Cache
            self.db.cache_derivations(ref.response_id, new_derivations)
            derivations.extend(new_derivations)
        
        return derivations
```

**Deliverables**:
- [ ] `ResponseProcessor` class
- [ ] Cache resolution at derivation level
- [ ] Tests: process response IDs, cache hit on re-process

#### 3.2 Per-Tool Extractors

Create `src/langnet/extractors/`:

```python
# extractors/base.py
class Extractor(ABC):
    @abstractmethod
    def extract(self, raw: RawResponse) -> list[Extraction]:
        """Parse raw response format into structured chunks."""
        pass

# extractors/cdsl.py
class CDSLExtractor(Extractor):
    def extract(self, raw: RawResponse) -> list[Extraction]:
        tree = ET.fromstring(raw.response_data)
        entries = tree.findall(".//entry")
        
        return [
            Extraction(
                extraction_id=str(uuid4()),
                response_id=raw.response_id,
                tool="cdsl",
                extraction_type="xml_entry",
                extracted_data={
                    "entry_id": entry.get("id"),
                    "headword": entry.findtext("h"),
                    "sense_lines": [s.text for s in entry.findall("sense")],
                }
            )
            for entry in entries
        ]

# extractors/diogenes.py
class DiogenesExtractor(Extractor):
    def extract(self, raw: RawResponse) -> list[Extraction]:
        soup = BeautifulSoup(raw.response_data, "html.parser")
        blocks = soup.find_all("div", id="sense")
        
        return [
            Extraction(
                extraction_id=str(uuid4()),
                response_id=raw.response_id,
                tool="diogenes",
                extraction_type="html_block",
                extracted_data={
                    "entry_id": self._compute_entry_id(block),
                    "entry_text": block.get_text(),
                    "citations": self._extract_citations(block),
                }
            )
            for block in blocks
        ]
```

**Deliverables**:
- [ ] `CDSLExtractor` (XML parsing)
- [ ] `DiogenesExtractor` (HTML parsing)
- [ ] `HeritageExtractor` (JSON parsing)
- [ ] `WhitakersExtractor` (text parsing)
- [ ] Tests: extract from sample responses

#### 3.3 Per-Tool Derivators

Create `src/langnet/derivators/`:

```python
# derivators/base.py
class Derivator(ABC):
    @abstractmethod
    def derive(self, extractions: list[Extraction]) -> list[Derivation]:
        """Parse extracted chunks into tool-specific facts."""
        pass

# derivators/cdsl.py
class CDSLDerivator(Derivator):
    def derive(self, extractions: list[Extraction]) -> list[Derivation]:
        derivations = []
        
        for ext in extractions:
            data = ext.extracted_data
            
            # Parse each sense line
            for i, sense_line in enumerate(data["sense_lines"]):
                parsed = self._parse_sense(sense_line)
                derivations.append(Derivation(
                    derivation_id=str(uuid4()),
                    extraction_id=ext.extraction_id,
                    tool="cdsl",
                    derivation_type="CDSLSenseFact",
                    derived_data={
                        "lemma": data["headword"],
                        "gloss": parsed.gloss,
                        "pos": parsed.pos,
                        "gender": parsed.gender,
                        "domains": parsed.domains,
                        "source_ref": f"mw:{data['entry_id']}:{i}",
                    }
                ))
        
        return derivations
```

**Deliverables**:
- [ ] `CDSLDerivator` (sense parsing, grammar stripping)
- [ ] `DiogenesDerivator` (dict blocks, citations)
- [ ] `HeritageDerivator` (morphology, dictionary)
- [ ] `WhitakersDerivator` (analysis lines)
- [ ] Tests: derive from sample extractions

---

### Phase 4: Hydration (Week 8)

**Goal**: Expand references (CTS URNs) into full data

#### 4.1 Hydration Service

Create `src/langnet/hydration/`:

```python
# hydration/core.py
class HydrationService:
    """Expand references into full data."""
    
    def __init__(self, db: V2Database, hydrators: dict[str, Hydrator]):
        self.db = db
        self.hydrators = hydrators
    
    def hydrate(self, derivations: list[Derivation], config: HydrationConfig) -> list[HydratedDerivation]:
        result = []
        
        for deriv in derivations:
            # Check for references that need hydration
            refs = self._find_references(deriv)
            
            if not refs:
                result.append(HydratedDerivation(derivation=deriv, hydrated_data={}))
                continue
            
            # Hydrate each reference
            hydrated = {}
            for ref_type, ref_value in refs.items():
                if ref_type == "cts_urn":
                    hydrator = self.hydrators["cts_index"]
                    hydrated[ref_value] = hydrator.fetch(ref_value)
            
            result.append(HydratedDerivation(
                derivation=deriv,
                hydrated_data=hydrated
            ))
        
        return result
```

**Deliverables**:
- [ ] `HydrationService` class
- [ ] `CTSIndexHydrator` (local DuckDB lookup)
- [ ] Configurable hydration depth
- [ ] Tests: hydrate CTS URN references

---

### Phase 5: Claims and Reduction (Week 9-10)

**Goal**: Transform derivations to claims, cluster into buckets

#### 5.1 Claim Transformer

Create `src/langnet/transform/`:

```python
# transform/core.py
TRANSFORM_RULES = {
    "CDSLSenseFact": {
        "predicate": "has_gloss",
        "value_fields": ["gloss", "domains", "register"],
    },
    "DiogenesDictFact": {
        "predicate": "has_gloss",
        "value_fields": ["entry_text", "entry_id"],
    },
    "DiogenesCitationFact": {
        "predicate": "has_citation",
        "value_fields": ["cts_urn", "text", "author", "work"],
    },
    "HeritageMorphFact": {
        "predicate": "has_morphology",
        "value_fields": ["lemma", "pos", "stem"],
    },
}

def transform_to_claims(derivations: list[Derivation]) -> list[Claim]:
    claims = []
    for deriv in derivations:
        rule = TRANSFORM_RULES.get(deriv.derivation_type)
        if rule:
            claims.append(Claim(
                claim_id=str(uuid4()),
                derivation_id=deriv.derivation_id,
                subject=deriv.derived_data.get("lemma") or deriv.derived_data.get("surface"),
                predicate=rule["predicate"],
                value={f: deriv.derived_data.get(f) for f in rule["value_fields"]},
                provenance_chain=deriv.provenance_chain,
            ))
    return claims
```

**Deliverables**:
- [ ] Transform rules for all fact types
- [ ] `transform_to_claims()` function
- [ ] Tests: transform derivations to claims

#### 5.2 Semantic Reducer (Wire Existing)

Wire existing `src/langnet/semantic_reducer/` to accept Claims:

```python
# semantic_reducer/wsu_extractor.py (modified)
def extract_wsus_from_claims(claims: list[Claim]) -> list[WitnessSenseUnit]:
    wsus = []
    for claim in claims:
        if claim.predicate == "has_gloss":
            wsus.append(WitnessSenseUnit(
                source=claim.provenance_chain.source,
                sense_ref=claim.provenance_chain.source_ref,
                gloss_raw=claim.value.get("gloss", ""),
                gloss_normalized=normalize_gloss(claim.value.get("gloss", "")),
            ))
    return wsus
```

**Deliverables**:
- [ ] Modified WSU extractor from Claims
- [ ] Integration with existing clustering pipeline
- [ ] Tests: claims → WSUs → buckets

---

### Phase 6: Pipeline Integration (Week 11-12)

**Goal**: Wire all stages together

#### 6.1 V2 Pipeline

Create `src/langnet/pipeline.py`:

```python
# pipeline/core.py
class V2Pipeline:
    """Complete V2 query pipeline."""
    
    def __init__(
        self,
        db: V2Database,
        normalizer: QueryNormalizer,
        planner: QueryPlanner,
        executor: PlanExecutor,
        processor: ResponseProcessor,
        hydrator: HydrationService,
        reducer: SemanticReducer,
    ):
        self.db = db
        self.normalizer = normalizer
        self.planner = planner
        self.executor = executor
        self.processor = processor
        self.hydrator = hydrator
        self.reducer = reducer
    
    def query(
        self, 
        query: str, 
        language: LanguageHint,
        mode: str = "open",
        view: str = "didactic",
        force_refresh: bool = False
    ) -> QueryResponse:
        # Stage 0: Check query cache
        query_hash = self._hash_query(query, language)
        cached_plan = self.db.get_cached_plan(query_hash)
        
        if cached_plan and not force_refresh:
            plan = cached_plan
        else:
            # Stage 0: Plan
            plan = self.planner.plan(query, language)
            self.db.cache_plan(query_hash, plan)
        
        # Stage 0.5: Execute
        executed = self.executor.execute(plan, force_refresh)
        
        # Stage 3-4: Process
        refs = [ToolResponseRef(tool=t, response_id=rid, cached=executed.from_cache)
                for t, rid in executed.tool_response_ids.items()]
        derivations = self.processor.process(refs)
        
        # Stage 4.5: Hydrate
        hydrated = self.hydrator.hydrate(derivations, HydrationConfig())
        
        # Stage 5: Transform
        claims = transform_to_claims(hydrated)
        
        # Stage 6: Reduce
        buckets = self.reducer.reduce(claims, mode=mode)
        
        # Build response
        return QueryResponse(
            schema_version="2.0.0",
            query=plan.query,
            lemmas=self._extract_lemmas(claims),
            senses=buckets,
            provenance=self._build_provenance(executed),
        )
```

**Deliverables**:
- [ ] `V2Pipeline` class
- [ ] Integration tests: end-to-end query
- [ ] Performance benchmarks

#### 6.2 CLI Integration

Add V2 command:

```python
# cli.py
@cli.command()
@click.option('--v2', is_flag=True, help='Use V2 pipeline')
@click.option('--refresh', is_flag=True, help='Force refresh cache')
@click.option('--view', type=click.Choice(['didactic', 'research']), default='didactic')
def query(word: str, language: str, v2: bool, refresh: bool, view: str):
    if v2:
        pipeline = get_v2_pipeline()
        result = pipeline.query(word, LanguageHint(language), force_refresh=refresh, view=view)
    else:
        # V1 path (existing)
        result = legacy_query(word, language)
    
    click.echo(format_output(result))
```

**Deliverables**:
- [ ] `--v2` flag for new pipeline
- [ ] Side-by-side with V1
- [ ] Cache management commands

---

### Phase 7: Migration and Cleanup (Week 13-14)

**Goal**: Deprecate V1, clean up

#### 7.1 Feature Parity

- [ ] All languages work (LAT, GRC, SAN)
- [ ] All tools work (cdsl, diogenes, heritage, whitakers, cltk)
- [ ] All output formats work (json, text, didactic, research)
- [ ] Performance acceptable (cache hit < 10ms, cache miss < 500ms)

#### 7.2 Deprecation

- [ ] Add deprecation warnings to V1 code paths
- [ ] Update documentation to reference V2
- [ ] Remove V1 code after transition period

#### 7.3 Documentation

- [ ] Update `docs/technical/design/` with final architecture
- [ ] Update `README.md` with V2 usage
- [ ] Add migration guide for V1 users

---

## Verification Checklist

### End of Each Phase

- [ ] All tests pass: `just test`
- [ ] Type check clean: `just typecheck`
- [ ] Documentation updated
- [ ] Code reviewed

### End of Project

- [ ] All 6 tools working in V2
- [ ] Cache layers working (transparent, disposable)
- [ ] Provenance chain complete
- [ ] Performance acceptable
- [ ] V1 deprecated
- [ ] Documentation complete

---

## Directory Structure

### Project Layout

```
langnet-cli/
├── codesketch/                    # V1 working sketch (reference)
│   ├── src/langnet/               # Existing implementation
│   │   ├── adapters/
│   │   ├── diogenes/
│   │   ├── heritage/
│   │   ├── normalization/         # PORT: transliteration
│   │   ├── semantic_reducer/      # PORT: clustering
│   │   └── ...
│   ├── examples/
│   └── tests/
│
├── src/langnet/                   # NEW: Clean implementation
│   ├── __init__.py
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── base.py                # BaseDB class
│   │   ├── langnet_db.py          # LangnetDB (cross-tool indexes)
│   │   ├── tool_db.py             # ToolDB (per-tool storage)
│   │   ├── registry.py            # StorageRegistry
│   │   └── schemas/
│   │       ├── langnet.sql        # Schema for langnet.duckdb
│   │       ├── cdsl.sql           # Schema for cdsl.duckdb
│   │       └── ...                # Other tool schemas
│   ├── normalizer/
│   │   ├── __init__.py
│   │   └── core.py                # QueryNormalizer (port from codesketch)
│   ├── registry/
│   │   ├── __init__.py
│   │   └── tools.py               # ToolRegistryEntry, TOOL_REGISTRY
│   ├── planner/
│   │   ├── __init__.py
│   │   └── core.py                # QueryPlanner, ToolPlan
│   ├── executor/
│   │   ├── __init__.py
│   │   └── core.py                # PlanExecutor
│   ├── processor/
│   │   ├── __init__.py
│   │   └── core.py                # ResponseProcessor
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── base.py                # Extractor ABC
│   │   ├── cdsl.py
│   │   ├── diogenes.py
│   │   ├── heritage.py
│   │   └── whitakers.py
│   ├── derivators/
│   │   ├── __init__.py
│   │   ├── base.py                # Derivator ABC
│   │   ├── cdsl.py
│   │   ├── diogenes.py
│   │   ├── heritage.py
│   │   └── whitakers.py
│   ├── hydration/
│   │   ├── __init__.py
│   │   └── core.py                # HydrationService, CTSIndexHydrator
│   ├── transform/
│   │   ├── __init__.py
│   │   └── core.py                # transform_to_claims
│   └── pipeline/
│       ├── __init__.py
│       └── core.py                # Pipeline orchestrator
│
└── ...
```

### Code to Port from codesketch/

| Source | Destination | Notes |
|--------|-------------|-------|
| `codesketch/normalization/sanskrit.py` | `v2/normalizer/sanskrit.py` | SLP1, IAST, Velthuis conversions |
| `codesketch/normalization/greek.py` | `v2/normalizer/greek.py` | Betacode conversion |
| `codesketch/heritage/velthuis_converter.py` | `v2/normalizer/velthuis.py` | Velthuis ↔ IAST |
| `codesketch/semantic_reducer/` | `v2/reducer/` | Clustering pipeline (adapt for Claims) |
| `codesketch/foster/` | `v2/foster/` | Functional grammar labels |

### Code to Study, Not Port

| Source | Why Study | V2 Approach |
|--------|-----------|-------------|
| `codesketch/adapters/` | Understand tool APIs | Build extractors + derivators |
| `codesketch/diogenes/core.py` | HTML parsing patterns | Build DiogenesExtractor |
| `codesketch/heritage/morphology.py` | JSON response handling | Build HeritageExtractor |
| `codesketch/whitakers_words/` | Line parsing patterns | Build WhitakersExtractor |
| `codesketch/cologne/` | CDSL XML handling | Build CDSLExtractor |

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Parser regressions | Snapshot tests for each tool |
| Performance degradation | Benchmarks at each phase |
| Cache invalidation bugs | Clear semantics, explicit tests |
| Provenance gaps | Provenance required at each stage |
| V1/V1 divergence | Side-by-side comparison tests |

---

## Questions?

Start with `docs/technical/design/v2-architecture-overview.md` for the big picture, then read the specific design docs for each stage.

For implementation, start with Phase 1 (proto schemas and storage layer).

---

## Getting Started (For New Developers)

### First Day Reading

1. **This document** - Read top to bottom
2. **codesketch/README.md** - Understand what reference code exists
3. **v2-architecture-overview.md** - See the big picture
4. **query-planning.md** - Understand the cache layers

### First Task: Define a Proto Schema

**Goal**: Define `query_spec.proto` with NormalizedQuery and ToolPlan types.

**Steps**:
1. Read `vendor/langnet-spec/schema/langnet_spec.proto` to understand existing style
2. Create `vendor/langnet-spec/schema/query_spec.proto`
3. Define NormalizedQuery with fields: original, language, canonical_forms, normalizations
4. Define ToolPlan with fields: plan_id, query, tool_calls, dependencies
5. Run `just codegen` to generate Python
6. Write a test that constructs a ToolPlan object

**Done when**: `just codegen` succeeds and you can import the generated types in Python.

### Second Task: Define Storage Schema

**Goal**: Write the SQL schema for `langnet.duckdb`.

**Steps**:
1. Create `src/langnet/storage/schemas/langnet.sql`
2. Define tables: query_cache, plan_cache, claims, provenance
3. Write a test that creates a DuckDB in-memory database with your schema

**Done when**: Test passes with schema applied to in-memory DuckDB.

### How to Ask for Help

1. Check `codesketch/` for reference implementations
2. Read the relevant design doc in `docs/technical/design/`
3. Look at existing tests in `codesketch/tests/` for patterns

### Key Commands

```bash
# Generate code from proto schemas
just codegen

# Run tests
just test

# Type check
just typecheck

# Run linter
just ruff-check

# Query a tool (from codesketch, for reference)
devenv shell langnet-cli -- query san agni --output json
```

---

## Data Flow Example

A complete example showing data at each stage for query "agni" (Sanskrit):

### Stage 0: Query Planning

```python
# NormalizedQuery
{
    "original": "agni",
    "language": "SAN",
    "canonical_forms": ["agni"],
    "normalizations": []
}

# ToolPlan
{
    "plan_id": "plan-001",
    "plan_hash": "a1b2c3d4",
    "query": {...},
    "tool_calls": [
        {
            "tool": "cdsl",
            "call_id": "call-001",
            "endpoint": "http://localhost:48080/sktreader?q=agni",
            "params": {"q": "agni"},
            "expected_response_type": "xml"
        },
        {
            "tool": "heritage",
            "call_id": "call-002",
            "endpoint": "http://localhost:8080/morph?q=agni",
            "params": {"q": "agni"},
            "expected_response_type": "json"
        }
    ]
}
```

### Stage 1-2: Tool Calls and Raw Responses

```python
# ToolCallEffect (cdsl)
{
    "effect_id": "effect-001",
    "tool": "cdsl",
    "url": "http://localhost:48080/sktreader?q=agni",
    "called_at": "2026-02-15T12:00:00Z"
}

# RawResponseEffect (cdsl)
{
    "effect_id": "effect-002",
    "response_id": "resp-cdsl-001",
    "tool": "cdsl",
    "content_type": "application/xml",
    "response_data": "<xml><entry id='217497'><h>agni</h>...</entry></xml>"
}
```

### Stage 3: Extractions

```python
# ExtractionEffect produces a LexiconArtifact (tool-specific)
# Each tool has its own artifact format:

# DiogenesArtifact (HTML blocks)
{
    "artifact_id": "artifact-dg-001",
    "tool": "diogenes",
    "artifact_type": "html_block",
    "data": {
        "entry_id": "00:01",
        "entry_text": "I. Lit.: ...",
        "citations": {"urn:cts:...": "Verg. E. 2, 63"}
    }
}

# HeritageArtifact (JSON analysis)
{
    "artifact_id": "artifact-hv-001",
    "tool": "heritage",
    "artifact_type": "morph_analysis",
    "data": {
        "lemma": "agni",
        "pos": "noun",
        "gender": "masculine",
        "stem": "agni"
    }
}

# WhitakersArtifact (parsed lines)
{
    "artifact_id": "artifact-ww-001",
    "tool": "whitakers",
    "artifact_type": "analysis",
    "data": {
        "surface": "lupus",
        "lemma": "lupus",
        "pos": "N",
        "features": {"case": "NOM", "number": "SING", "gender": "MASC"}
    }
}

# CDSLArtifact (XML entry)
{
    "artifact_id": "artifact-cdsl-001",
    "tool": "cdsl",
    "artifact_type": "xml_entry",
    "data": {
        "entry_id": "217497",
        "headword": "agni",
        "sense_lines": ["fire, sacrificial fire", "the god of fire"]
    }
}
```

### Stage 4: Derivations

```python
# DerivationEffect (cdsl)
{
    "effect_id": "effect-004",
    "derivation_id": "deriv-cdsl-001",
    "extraction_id": "ext-cdsl-001",
    "tool": "cdsl",
    "derivation_type": "CDSLSenseFact",
    "derived_data": {
        "lemma": "agni",
        "gloss": "fire, sacrificial fire",
        "pos": "noun",
        "gender": "masculine",
        "source_ref": "mw:217497:0"
    }
}
```

### Stage 5: Claims

```python
# ClaimEffect
{
    "effect_id": "effect-005",
    "claim_id": "claim-001",
    "derivation_id": "deriv-cdsl-001",
    "subject": "agni",
    "predicate": "has_gloss",
    "value": {
        "gloss": "fire, sacrificial fire"
    },
    "provenance_chain": {
        "derivation_id": "deriv-cdsl-001",
        "extraction_id": "ext-cdsl-001",
        "response_id": "resp-cdsl-001",
        "tool": "cdsl",
        "source_ref": "mw:217497:0"
    }
}
```

### Stage 6: Reduction

```python
# Bucket (after clustering)
{
    "bucket_id": "bucket-001",
    "semantic_constant": "FIRE",
    "display_gloss": "fire, sacrificial fire",
    "witnesses": [
        {"source": "cdsl", "source_ref": "mw:217497:0"},
        {"source": "heritage", "source_ref": "heritage:agni"}
    ]
}
```

### Output

```python
# QueryResponse
{
    "schema_version": "2.0.0",
    "query": {
        "surface": "agni",
        "language": "SAN",
        "normalized": "agni"
    },
    "lemmas": [
        {"lemma_id": "san:agni", "display": "agni", "language": "SAN"}
    ],
    "senses": [
        {
            "sense_id": "bucket-001",
            "semantic_constant": "FIRE",
            "display_gloss": "fire, sacrificial fire",
            "witnesses": [...]
        }
    ]
}
```
