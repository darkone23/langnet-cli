# Next Steps Roadmap: V2 Implementation

**Date**: 2026-04-11
**Status**: ACTIVE
**Foundation**: ✅ COMPLETE (Tasks 1-6)
**Current Phase**: Ready for core pipeline expansion

---

## Executive Summary

**Where We Are**:
The V2 foundation is **production-ready** with excellent architecture:
- ✅ Staged execution pipeline (fetch→extract→derive→claim)
- ✅ Persistent storage with DuckDB (handler versioning working)
- ✅ CLI tools for cache management
- ✅ Comprehensive documentation (1500+ lines)
- ✅ Performance validated (38x cache speedup, all targets met)
- ✅ Testing infrastructure (61 tests passing)

**What We've Built**:
```
Current V2 Implementation (src/langnet/):
├── storage/           ✅ Complete - 7 indexes, versioned handlers
├── execution/         ✅ Complete - staged executor, handler registry
├── normalizer/        ✅ Complete - query normalization
├── planner/           ✅ Complete - tool plan generation
├── clients/           ✅ Complete - HTTP clients for tools
├── cli.py             ✅ Complete - full CLI with index management
└── handlers/          ✅ Working - diogenes, whitakers, heritage, cdsl, cltk

What's Working End-to-End:
Query "lupus" → Plan → Fetch → Extract → Derive → Claim → Output
              (all stages functional with real handlers)
```

**Gap Analysis** (Design vs Implementation):

| Component | Design Status | Implementation Status | Gap |
|-----------|---------------|----------------------|-----|
| **Core Pipeline (Stages 1-5)** | 📄 Designed | ✅ **~80% Implemented** | Need more handlers |
| **Query Planning (Stage 0)** | 📄 Designed | ✅ **100% Implemented** | None |
| **Storage Layer** | 📄 Designed | ✅ **100% Implemented** | None |
| **Handler System** | 📄 Designed | ✅ **100% Implemented** | None |
| **Entry Parsing** | 📄 Designed | ⚠️ **30% Implemented** | Need Lark grammars |
| **Semantic Reduction (Stage 6)** | 📄 Designed | ❌ **0% Implemented** | Major work needed |
| **Hydration (Stage 4.5)** | 📄 Designed | ❌ **0% Implemented** | CTS index integration |

**What This Means**:
You have a **solid, production-ready foundation** (Stages 0-5) with ~80% implementation. The main gaps are:
1. **Entry Parsing** - Raw text → structured data (Lark grammars)
2. **Semantic Reduction** - Claims → Buckets → Constants (clustering)
3. **Hydration** - CTS URN expansion (cts_index tool integration)

---

## Core Functions: Do I Have a Solid Grasp?

### ✅ Yes - Here's What I Understand

**1. The V2 Pipeline Architecture** (Fully Implemented)
```
User Query "lupus" (Latin)
    ↓
Stage 0: Query Planning ✅
    NormalizedQuery(original="lupus", language=LATIN)
    ToolPlan(tools=[diogenes, whitakers], dependencies=[...])
    ↓
Stage 0.5: Plan Execution ✅
    Execute plan with clients
    ↓
Stage 1: Tool Calls ✅
    HTTP → Diogenes ("/Diogenes.cgi?q=lupus")
    Binary → Whitakers ("lupus")
    ↓
Stage 2: Raw Responses ✅
    Store HTML/text exactly as received
    RawResponseIndex (immutable, re-parseable)
    ↓
Stage 3: Extractions ✅
    Format parsing: HTML → blocks, text → lines
    ExtractionIndex (handler_version="v1")
    ↓
Stage 4: Derivations ✅
    Content parsing: Extract tool-specific facts
    DerivationIndex (DiogenesDictFact, WhitakersAnalysisFact)
    ↓
Stage 5: Claims ✅
    Transform to universal triples (S-P-V)
    ClaimIndex (has_gloss, has_morphology, has_citation)
    provenance_chain = [fetch→extract→derive→claim]
```

**2. Handler Versioning System** ✅
```python
@versioned("v1")
def extract_html(call, raw):
    # Extract structured data from HTML
    return ExtractionEffect(handler_version="v1", ...)

# When handler changes:
@versioned("v2")  # Increment version
def extract_html(call, raw):
    # New extraction logic
    return ExtractionEffect(handler_version="v2", ...)

# Result: Old cache ignored, re-executes with v2
```

**3. Storage Architecture** ✅
```
DuckDB Databases:
├── main: langnet.duckdb
│   ├── query_normalization_index
│   ├── query_plan_index
│   ├── plan_response_index
│   ├── raw_response_index       (immutable HTTP responses)
│   ├── extraction_index          (handler_version tracking)
│   ├── derivation_index          (handler_version tracking)
│   ├── claims                    (provenance_chain)
│   └── provenance                (audit trail)
└── tools/
    ├── diogenes.duckdb           (tool-specific caches)
    ├── whitakers.duckdb
    └── ...

Paths: ~/.local/share/langnet/cache/
Override: LANGNET_DATA_DIR env var
```

**4. Effect Chain & Provenance** ✅
```
Every claim traces back to origin:
Claim(claim_id="clm-abc")
  └─ provenance_chain:
      [0] fetch: tool=fetch.diogenes, ref=resp-xyz
      [1] extract: tool=extract.diogenes.html, ref=ext-def
      [2] derive: tool=derive.diogenes.morph, ref=drv-ghi
      [3] claim: tool=claim.diogenes.morph, ref=clm-abc

This enables: "Show me the Diogenes HTML we used to derive 'wolf'"
```

**5. Current Tool Support** ✅
```
Implemented Handlers:
├── diogenes       ✅ extract_html, derive_morph, claim_morph
├── whitakers      ✅ extract_lines, derive_facts, claim_whitakers
├── heritage       ✅ extract_html, derive_morph, claim_morph
├── cdsl           ✅ extract_xml, derive_sense, claim_sense
└── cltk           ✅ extract_cltk, derive_cltk, claim_cltk

Registry Pattern:
default_registry() → ToolRegistry
    extract_handlers = {
        "extract.diogenes.html": extract_html,
        "extract.whitakers.lines": extract_lines,
        ...
    }
```

**6. Performance Characteristics** ✅
```
Benchmarked Performance:
├── DB insert (raw):        13.7ms  (target: <50ms) ✅
├── DB query (cache hit):   1.4ms   (target: <5ms)  ✅
├── Extract handler:        1.2ms   (target: <100ms)✅
├── Derive handler:         0.02ms  (target: <50ms) ✅
├── Claim handler:          0.02ms  (target: <50ms) ✅
└── Cache speedup:          38x vs network          ✅

End-to-End Latency:
├── Cold query (miss):      ~91ms   (target: <200ms)✅
└── Warm query (hit):       ~3.4ms  (target: <10ms) ✅
```

**7. Code Organization** ✅
```
src/langnet/
├── storage/              ✅ DuckDB indexes (7 classes)
├── execution/
│   ├── executor.py       ✅ Staged execution engine
│   ├── registry.py       ✅ Handler registry (default_registry)
│   ├── effects.py        ✅ Effect types (Raw, Extract, Derive, Claim)
│   ├── versioning.py     ✅ @versioned decorator
│   └── handlers/         ✅ Tool-specific handlers
│       ├── diogenes.py   ✅ Extract/Derive/Claim
│       ├── whitakers.py  ✅ Extract/Derive/Claim
│       ├── heritage.py   ✅ Extract/Derive/Claim
│       ├── cdsl.py       ✅ Extract/Derive/Claim
│       └── cltk.py       ✅ Extract/Derive/Claim
├── planner/
│   └── core.py           ✅ ToolPlanner, PlannerConfig
├── normalizer/
│   └── service.py        ✅ NormalizationService
├── clients/
│   ├── base.py           ✅ ToolClient protocol
│   └── http.py           ✅ HttpToolClient
└── cli.py                ✅ Full CLI (parse, plan, plan-exec, index)
```

---

## What Needs to Happen Next

### Phase 1: Entry Parsing (Weeks 1-4) 🎯 HIGH PRIORITY

**Status**: 📄 Designed, ⚠️ 30% Implemented

**Problem**: Current handlers parse raw HTML/XML into somewhat structured data, but:
- Diogenes HTML has root symbols (√), citations, abbreviations mixed in
- CDSL XML has sense lines that need hierarchical parsing
- Raw glosses contain noise: "lupus, i, m. kindred with λύκος; Sanscr. vrika..."

**Design**: `docs/technical/design/entry-parsing.md`

**Goal**: Clean extraction using Lark grammars

**Tasks**:

1. **Create Lark Grammars** (2-3 weeks)
   ```
   docs/technical/design/entry-parsing.md → Implementation

   Grammars to create:
   ├── cdsl_sense.lark        Parse MW/AP90 sense lines
   ├── diogenes_entry.lark    Parse Lewis & Short entries
   ├── whitakers_line.lark    Parse Whitakers output
   └── citation.lark          Parse citation abbreviations

   Test with existing entries:
   - "agni" (Sanskrit) → Clean sense extraction
   - "lupus" (Latin) → Root extraction, sense separation
   - "λόγος" (Greek) → Citation parsing
   ```

2. **Integrate Parsers into Handlers** (1 week)
   ```python
   # Current:
   def extract_html(call, raw):
       soup = BeautifulSoup(raw.body)
       # ... ad-hoc parsing
       return ExtractionEffect(payload=parsed_data)

   # After:
   from langnet.parsing.diogenes import DiogenesEntryParser

   @versioned("v2")  # Bump version
   def extract_html(call, raw):
       parser = DiogenesEntryParser()
       parsed_entry = parser.parse(raw.body)
       return ExtractionEffect(
           payload={
               "headword": parsed_entry.headword,
               "senses": [s.to_dict() for s in parsed_entry.senses],
               "citations": [c.to_dict() for c in parsed_entry.citations],
               "roots": parsed_entry.roots,
           },
           handler_version="v2",
       )
   ```

3. **Create ParsedEntry TypedDicts** (1 week)
   ```python
   # In src/langnet/parsing/types.py
   class ParsedSense(TypedDict):
       sense_id: str
       gloss_raw: str
       gloss_clean: str
       domains: list[str]
       register: list[str]
       sub_senses: list[ParsedSense]

   class ParsedCitation(TypedDict):
       citation_text: str
       cts_urn: str | None
       author: str | None
       work: str | None

   class ParsedEntry(TypedDict):
       headword: str
       pos: str | None
       senses: list[ParsedSense]
       citations: list[ParsedCitation]
       roots: list[str]
       grammar_codes: dict[str, str]
   ```

**Deliverables**:
- ✅ Lark grammars for all major tools (CDSL, Diogenes, Whitakers)
- ✅ ParsedEntry types in `src/langnet/parsing/types.py`
- ✅ Integration into handlers with version bump (v1 → v2)
- ✅ Tests for parsers (`tests/test_parsing_*.py`)
- ✅ Update handler development guide with parsing patterns

**Impact**: Clean structured data enables Stage 6 (semantic reduction)

---

### Phase 2: Hydration - CTS Index Integration (Weeks 5-7) 🎯 MEDIUM PRIORITY

**Status**: 📄 Designed, ❌ 0% Implemented

**Problem**: Citations like "Verg. E. 2, 63" need expansion to full text

**Design**: `docs/technical/design/v2-architecture-overview.md` (Stage 4.5)

**Goal**: Treat CTS index as a tool that takes URNs and returns citation data

**Tasks**:

1. **Create CTS Index Client** (1 week)
   ```python
   # In src/langnet/clients/cts_index.py
   class CTSIndexClient(ToolClient):
       def execute(self, call_id: str, endpoint: str, params: dict):
           urn = params["urn"]  # e.g., "urn:cts:latinLit:phi0690.phi001:2.63"
           # Query CTS index (local or API)
           citation_data = self._query_cts(urn)
           return RawResponseEffect(
               response_id=...,
               body=json.dumps(citation_data).encode(),
               ...
           )
   ```

2. **Create CTS Handlers** (1 week)
   ```python
   # In src/langnet/execution/handlers/cts_index.py
   @versioned("v1")
   def extract_json(call, raw):
       data = json.loads(raw.body)
       return ExtractionEffect(
           payload={
               "urn": data["urn"],
               "text": data["text"],
               "author": data["author"],
               "work": data["work"],
           }
       )

   @versioned("v1")
   def derive_citation(call, extraction):
       return DerivationEffect(
           payload={
               "citation_urn": extraction.payload["urn"],
               "citation_text": extraction.payload["text"],
               "author": extraction.payload["author"],
           }
       )

   @versioned("v1")
   def claim_citation(call, derivation):
       return ClaimEffect(
           subject=derivation.payload["citation_urn"],
           predicate="has_text",
           value={"text": derivation.payload["citation_text"]},
       )
   ```

3. **Wire into Planner** (1 week)
   ```python
   # In planner/core.py
   def build(self, query, candidate):
       plan = ToolPlan(...)

       # Add primary tools (diogenes, whitakers, etc.)
       for tool in primary_tools:
           plan.add_call(...)

       # Add hydration dependency
       if self.config.enable_hydration:
           for call in plan.calls:
               if call.stage == ToolStage.DERIVE:
                   # If derivation contains URNs, add CTS lookup
                   cts_call = self._build_cts_call(call)
                   plan.add_call(cts_call)
                   plan.add_dependency(call.call_id, cts_call.call_id)

       return plan
   ```

**Deliverables**:
- ✅ CTS index client in `src/langnet/clients/cts_index.py`
- ✅ CTS handlers in `src/langnet/execution/handlers/cts_index.py`
- ✅ Planner integration for automatic hydration
- ✅ Tests for CTS pipeline
- ✅ Config flag: `enable_hydration=True/False`

**Impact**: Rich citation data in responses (author, work, full text)

---

### Phase 3: Semantic Reduction (Weeks 8-14) 🎯 HIGH PRIORITY

**Status**: 📄 Designed, ❌ 0% Implemented (V1 code exists in codesketch/)

**Problem**: Multiple tools produce overlapping claims - need clustering

**Example**:
```
Query "agni" produces:
- MW: "fire", "sacrificial fire", "fire-god"
- Heritage: "fire", "flame"
- CDSL: "fire", "Agni (deity)"

Need to cluster → Buckets:
[1] {gloss: "fire", witnesses: [mw, heritage, cdsl]}
[2] {gloss: "sacrificial fire", witnesses: [mw]}
[3] {gloss: "deity/fire-god", witnesses: [mw, cdsl]}
```

**Design**: `docs/technical/design/classifier-and-reducer.md`

**V1 Code** (can port): `codesketch/src/langnet/semantic_reducer/`

**Goal**: Cluster similar claims into buckets for display

**Tasks**:

1. **Define WSU (Witness Sense Unit)** (1 week)
   ```python
   # In src/langnet/reduction/types.py
   class WSU(TypedDict):
       wsu_type: str  # "sense" | "citation"
       source: str    # "MW", "diogenes", etc.
       sense_ref: str # "mw:217497"
       gloss_raw: str
       gloss_normalized: str
       domains: list[str]
       register: list[str]
       claim_id: str  # Link to ClaimIndex
   ```

2. **WSU Extractor from Claims** (1 week)
   ```python
   # In src/langnet/reduction/extractor.py
   def extract_wsus(claims: list[ClaimEffect]) -> list[WSU]:
       wsus = []
       for claim in claims:
           if claim.predicate == "has_gloss":
               wsus.append(WSU(
                   wsu_type="sense",
                   source=claim.tool,
                   gloss_raw=claim.value["gloss"],
                   gloss_normalized=normalize_gloss(claim.value["gloss"]),
                   claim_id=claim.claim_id,
               ))
       return wsus
   ```

3. **Clustering Pipeline** (2-3 weeks)
   ```python
   # In src/langnet/reduction/clusterer.py
   from sklearn.cluster import DBSCAN
   from sentence_transformers import SentenceTransformer

   class SemanticClusterer:
       def cluster_wsus(self, wsus: list[WSU]) -> list[Bucket]:
           # 1. Normalize glosses
           normalized = [w["gloss_normalized"] for w in wsus]

           # 2. Generate embeddings
           embeddings = self.model.encode(normalized)

           # 3. Cluster similar glosses
           labels = DBSCAN(eps=0.3, min_samples=2).fit_predict(embeddings)

           # 4. Group into buckets
           buckets = []
           for label in set(labels):
               bucket_wsus = [w for w, l in zip(wsus, labels) if l == label]
               buckets.append(Bucket(
                   bucket_id=...,
                   canonical_gloss=self._pick_canonical(bucket_wsus),
                   witnesses=bucket_wsus,
                   similarity_score=self._compute_similarity(bucket_wsus),
               ))

           return buckets
   ```

4. **Mode Variations** (1 week)
   ```python
   # In src/langnet/reduction/modes.py
   class ReductionMode:
       OPEN = "open"      # Accept all witnesses
       SKEPTIC = "skeptic" # Require 2+ witnesses per bucket

   def apply_mode(buckets: list[Bucket], mode: ReductionMode):
       if mode == ReductionMode.SKEPTIC:
           # Filter out single-witness buckets
           return [b for b in buckets if len(b.witnesses) >= 2]
       return buckets
   ```

5. **Integration into Pipeline** (1 week)
   ```python
   # In src/langnet/pipeline/reducer.py
   def reduce_claims(claims: list[ClaimEffect], mode: str) -> list[Bucket]:
       # Extract WSUs
       wsus = extract_wsus(claims)

       # Cluster
       clusterer = SemanticClusterer()
       buckets = clusterer.cluster_wsus(wsus)

       # Apply mode
       mode_enum = ReductionMode(mode)
       filtered_buckets = apply_mode(buckets, mode_enum)

       return filtered_buckets
   ```

**Deliverables**:
- ✅ WSU extraction from claims
- ✅ Semantic clustering with embeddings
- ✅ Mode variations (open/skeptic)
- ✅ Integration into pipeline
- ✅ Tests for clustering accuracy
- ✅ Performance benchmarks (should be <500ms)

**Dependencies**:
- Entry parsing (Phase 1) - need clean glosses
- Possibly sentence-transformers or gensim (V1 uses gensim)

**Port from V1**:
- `codesketch/src/langnet/semantic_reducer/core.py`
- `codesketch/src/langnet/semantic_reducer/clustering.py`

**Impact**: User-facing output is clean, clustered, evidence-backed

---

### Phase 4: Additional Handlers (Weeks 8-12) 🔧 ONGOING

**Status**: ⚠️ Partially Implemented

**Goal**: Complete handler coverage for all tools

**Current Coverage**:
- ✅ Diogenes (Latin/Greek dictionary)
- ✅ Whitakers (Latin morphology)
- ✅ Heritage (Sanskrit morphology)
- ✅ CDSL (Sanskrit dictionary)
- ✅ CLTK (Greek/Latin utilities)

**Missing/Incomplete**:
- ⚠️ spaCy integration (Greek morphology fallback)
- ❌ Additional CDSL dictionaries (AP90, etc.)
- ❌ Specialized tools (if any)

**Tasks per new tool**:
1. Create client in `src/langnet/clients/{tool}.py`
2. Create handlers in `src/langnet/execution/handlers/{tool}.py`
   - `extract_{format}` - Parse raw response
   - `derive_{semantic_type}` - Extract facts
   - `claim_{semantic_type}` - Produce triples
3. Register in `src/langnet/execution/registry.py`
4. Add tests in `tests/test_{tool}_handlers.py`
5. Update handler development guide with examples

**Estimate**: 1-2 weeks per tool (depending on complexity)

---

## Recommended Priorities

### 🔴 Critical Path (Do First)

**1. Entry Parsing (Phase 1)** - Weeks 1-4
- **Why**: Unblocks semantic reduction
- **Impact**: Clean data enables clustering
- **Complexity**: Medium (Lark grammars + integration)
- **Risk**: Low (well-designed, clear spec)

**2. Semantic Reduction (Phase 3)** - Weeks 8-14
- **Why**: Core user-facing feature
- **Impact**: Produces clean, clustered output
- **Complexity**: High (ML/clustering)
- **Risk**: Medium (V1 code exists to port)

### 🟡 High Value (Do Soon)

**3. Hydration (Phase 2)** - Weeks 5-7
- **Why**: Rich citation data enhances user experience
- **Impact**: Full citation text in responses
- **Complexity**: Medium (new tool integration)
- **Risk**: Low (follows existing patterns)

**4. Additional Handlers (Phase 4)** - Ongoing
- **Why**: Expand language/tool coverage
- **Impact**: More comprehensive results
- **Complexity**: Low-Medium (per tool)
- **Risk**: Low (clear patterns established)

### 🟢 Nice to Have (Later)

**5. Performance Optimization**
- Batch inserts for bulk imports
- Connection pooling
- Query result streaming

**6. Advanced Features**
- GraphQL API
- WebSocket support
- Multi-query batching

---

## Implementation Timeline (16 Weeks)

```
Weeks 1-4:   Entry Parsing (Lark grammars + integration)
Weeks 5-7:   Hydration (CTS index as tool)
Weeks 8-14:  Semantic Reduction (WSU → Buckets → Constants)
Weeks 12-16: Additional Handlers + Polish

Parallel tracks:
- Testing throughout (add tests for each phase)
- Documentation updates (handler guide, schema docs)
- Performance monitoring (benchmarks after each phase)
```

**Milestones**:
- **Week 4**: Clean entry parsing working for all tools
- **Week 7**: Citation hydration functional
- **Week 14**: Semantic reduction producing clustered output
- **Week 16**: V2 feature-complete, ready for production

---

## Success Criteria

**Phase 1 Complete** (Entry Parsing):
```
✅ Lark grammars parse sample entries without errors
✅ ParsedEntry objects have clean, separated data
✅ Handlers bump to v2 with new parsing logic
✅ Tests validate parser accuracy (>95% correct)
✅ Documentation updated with parsing patterns
```

**Phase 2 Complete** (Hydration):
```
✅ CTS index integrated as a tool
✅ Citations expand to full text
✅ Planner automatically adds hydration calls
✅ Config flag enables/disables hydration
✅ Performance impact <100ms per citation
```

**Phase 3 Complete** (Semantic Reduction):
```
✅ WSUs extracted from claims accurately
✅ Clustering produces meaningful buckets
✅ Mode variations work (open/skeptic)
✅ Output is clean and evidence-backed
✅ Performance: <500ms for typical query
✅ Accuracy: >90% user-validated clustering
```

**V2 Feature Complete**:
```
✅ All design stages (0-6) implemented
✅ Documentation complete and current
✅ Tests comprehensive (>80% coverage)
✅ Performance targets met
✅ Production deployment successful
✅ V1 deprecated and archived
```

---

## Open Questions / Decisions Needed

1. **Entry Parsing**: Which Lark grammar variant? (LALR vs Earley)
   - Recommendation: Start with LALR (faster), fallback to Earley for ambiguous grammars

2. **Semantic Reduction**: Which embedding model?
   - Options: sentence-transformers (modern), gensim (V1 uses this)
   - Recommendation: sentence-transformers (better accuracy, easier to use)

3. **Hydration**: Local CTS index or API?
   - Options: Build local index from Perseus data, use external API
   - Recommendation: Start with local index (faster, no network dependency)

4. **Additional Handlers**: Which tools to prioritize?
   - Recommendation: Focus on completing existing tools first, add new ones based on user demand

5. **Production Rollout**: V1/V2 side-by-side or cutover?
   - Recommendation: Side-by-side with feature flag (gradual rollout)

---

## Related Documents

- **Foundation Work**: `docs/plans/active/v2-foundation-establishment.md` ✅ COMPLETE
- **Design Docs**: `docs/technical/design/v2-architecture-overview.md`
- **Entry Parsing**: `docs/technical/design/entry-parsing.md`
- **Semantic Reduction**: `docs/technical/design/classifier-and-reducer.md`
- **Tool Pipeline**: `docs/technical/design/tool-response-pipeline.md`
- **Handler Guide**: `docs/handler-development-guide.md` ✅ NEW
- **Storage Schema**: `docs/storage-schema.md` ✅ NEW
- **Performance**: `docs/performance-benchmarks.md` ✅ NEW

---

**Next Action**: Choose Phase 1 (Entry Parsing) or Phase 3 (Semantic Reduction) to start implementation. Both are critical path items with clear specifications.
