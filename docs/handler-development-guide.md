# Handler Development Guide

## Overview

Handlers are the core processing units in langnet's V2 architecture. They transform data through three sequential stages:

1. **Extract** - Parse raw responses from external services into structured data
2. **Derive** - Transform extractions into semantic facts and relationships
3. **Claim** - Emit universal triples (subject-predicate-value) for knowledge graph integration

Each handler is versioned to enable cache invalidation when logic changes.

## Architecture

### Three-Stage Pipeline

```
Raw Response (fetch) → Extraction (extract) → Derivation (derive) → Claims (claim)
     ↓                      ↓                      ↓                    ↓
  HTTP body          Structured data         Semantic facts      Universal triples
  (bytes/HTML)       (JSON payload)          (enriched data)     (S-P-V format)
```

### Effect Types

Each stage produces a specific effect type:

- **ExtractionEffect**: Structured data extracted from raw responses
  - `extraction_id`: Unique identifier
  - `response_id`: Link to raw response
  - `kind`: Type of extraction (e.g., "html", "json", "xml")
  - `canonical`: Primary canonical form extracted
  - `payload`: Structured data (dict or list)
  - `handler_version`: Version for cache invalidation

- **DerivationEffect**: Semantic facts derived from extractions
  - `derivation_id`: Unique identifier
  - `extraction_id`: Link to extraction
  - `kind`: Type of derivation (e.g., "morph", "sense")
  - `canonical`: Canonical lemma/form
  - `payload`: Derived facts and relationships
  - `provenance_chain`: Full lineage from fetch through extract

- **ClaimEffect**: Universal triples for knowledge graph
  - `claim_id`: Unique identifier
  - `derivation_id`: Link to derivation
  - `subject`: Subject of the triple (usually a lemma)
  - `predicate`: Relationship type (e.g., "has_pos", "has_case")
  - `value`: JSON value (can be primitive or complex)
  - `provenance_chain`: Complete audit trail

## Handler Versioning

### The @versioned Decorator

All handlers MUST use the `@versioned` decorator to enable cache invalidation:

```python
from langnet.execution.versioning import versioned

@versioned("v1")
def extract_html(call: ToolCallSpec, raw: RawResponseEffect) -> ExtractionEffect:
    """Extract structured data from HTML response."""
    # Implementation
```

### Version String Guidelines

**Semantic versioning pattern**: `v{major}.{minor}`

- **v1**: Initial implementation
- **v1.1**: Bug fix or minor enhancement (no schema change)
- **v1.2**: Additional fields added (backward compatible)
- **v2**: Breaking change (incompatible schema or logic change)

**When to increment versions:**

1. **Bug fixes** that don't change output structure → Same version or patch (v1.0 → v1.0)
2. **New fields added** to payload → Minor bump (v1 → v1.1)
3. **Fields removed or renamed** → Major bump (v1 → v2)
4. **Changed extraction logic** significantly → Major bump (v1 → v2)

**Example progression:**
```python
# Initial release
@versioned("v1")
def extract_html(call, raw):
    return ExtractionEffect(..., payload={"lemma": "lupus"})

# Added pos field (backward compatible)
@versioned("v1.1")
def extract_html(call, raw):
    return ExtractionEffect(..., payload={"lemma": "lupus", "pos": "noun"})

# Changed payload structure (breaking)
@versioned("v2")
def extract_html(call, raw):
    return ExtractionEffect(..., payload={"forms": [{"lemma": "lupus", "pos": "noun"}]})
```

### Cache Invalidation

When you increment a handler version, all cached extractions/derivations/claims from the old version are automatically ignored. The system will re-execute the handler with the new version.

## Writing Handlers

### 1. Extract Handlers

Extract handlers parse raw responses into structured data.

**Function signature:**
```python
def extract_{name}(call: ToolCallSpec, raw: RawResponseEffect) -> ExtractionEffect
```

**Example: HTML extraction**
```python
from bs4 import BeautifulSoup
from langnet.execution.versioning import versioned
from langnet.execution.effects import ExtractionEffect, stable_effect_id

@versioned("v1")
def extract_html(call: ToolCallSpec, raw: RawResponseEffect) -> ExtractionEffect:
    """Parse HTML response from Diogenes into structured lemmas."""
    html = raw.body.decode("utf-8", errors="ignore")
    soup = BeautifulSoup(html, "lxml")

    # Extract structured data
    lemmas = []
    for entry in soup.find_all("div", class_="entry"):
        lemmas.append({
            "lemma": entry.find("span", class_="lemma").text.strip(),
            "pos": entry.find("span", class_="pos").text.strip(),
            "definition": entry.find("div", class_="definition").text.strip(),
        })

    # Generate stable ID
    extraction_id = stable_effect_id("ext", call.call_id, raw.response_id)

    return ExtractionEffect(
        extraction_id=extraction_id,
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=raw.call_id,
        response_id=raw.response_id,
        kind="html",
        canonical=lemmas[0]["lemma"] if lemmas else None,
        payload={"lemmas": lemmas},
        handler_version="v1",
    )
```

**Best practices:**
- Always decode bytes with error handling (`errors="ignore"` or `errors="replace"`)
- Use `stable_effect_id()` for deterministic IDs
- Set `canonical` to the primary/preferred form
- Store rich structured data in `payload`
- Handle empty/malformed responses gracefully

### 2. Derive Handlers

Derive handlers transform extractions into semantic facts.

**Function signature:**
```python
def derive_{name}(call: ToolCallSpec, extraction: ExtractionEffect) -> DerivationEffect
```

**Example: Morphological derivation**
```python
@versioned("v1")
def derive_morph(call: ToolCallSpec, extraction: ExtractionEffect) -> DerivationEffect:
    """Derive morphological facts from extracted lemmas."""
    # Build provenance chain
    prov = [
        ProvenanceLink(
            stage="extract",
            tool=extraction.tool,
            reference_id=extraction.extraction_id,
            metadata={"response_id": extraction.response_id},
        )
    ]

    # Extract payload
    payload = extraction.payload or {}
    lemmas = payload.get("lemmas", [])

    # Derive facts
    facts = []
    for lemma_data in lemmas:
        facts.append({
            "lemma": lemma_data["lemma"],
            "pos": lemma_data["pos"],
            "inflections": _analyze_inflection(lemma_data),
            "stems": _extract_stems(lemma_data),
        })

    derivation_id = stable_effect_id("drv", call.call_id, extraction.extraction_id)

    return DerivationEffect(
        derivation_id=derivation_id,
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        extraction_id=extraction.extraction_id,
        kind="morph",
        canonical=extraction.canonical,
        payload={"facts": facts},
        provenance_chain=prov,
        handler_version="v1",
    )
```

**Best practices:**
- Always build provenance chain from previous stages
- Validate input payload structure
- Enrich data with semantic information
- Keep canonical form consistent with extraction
- Use helper functions for complex transformations

### 3. Claim Handlers

Claim handlers emit universal subject-predicate-value triples.

**Function signature:**
```python
def claim_{name}(call: ToolCallSpec, derivation: DerivationEffect) -> ClaimEffect
```

**Example: Morphological claims**
```python
from langnet.execution import predicates

@versioned("v1")
def claim_morph(call: ToolCallSpec, derivation: DerivationEffect) -> ClaimEffect:
    """Emit claims for morphological facts."""
    # Extend provenance chain
    prov = derivation.provenance_chain[:] if derivation.provenance_chain else []
    prov.append(
        ProvenanceLink(
            stage="derive",
            tool=derivation.tool,
            reference_id=derivation.derivation_id,
            metadata={"extraction_id": derivation.extraction_id},
        )
    )

    # Extract first fact as primary claim
    payload = derivation.payload or {}
    facts = payload.get("facts", [])
    if not facts:
        # Return empty claim if no facts
        return ClaimEffect(
            claim_id=stable_effect_id("clm", call.call_id, derivation.derivation_id),
            tool=call.tool,
            call_id=call.call_id,
            source_call_id=call.params.get("source_call_id", ""),
            derivation_id=derivation.derivation_id,
            subject="unknown",
            predicate="has_error",
            value={"error": "no_facts"},
            provenance_chain=prov,
            handler_version="v1",
        )

    fact = facts[0]

    claim_id = stable_effect_id("clm", call.call_id, derivation.derivation_id)

    return ClaimEffect(
        claim_id=claim_id,
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        derivation_id=derivation.derivation_id,
        subject=fact["lemma"],
        predicate=predicates.HAS_POS,  # Use standard predicates
        value={"pos": fact["pos"], "lemma": fact["lemma"]},
        provenance_chain=prov,
        handler_version="v1",
    )
```

**Best practices:**
- Always extend provenance chain from derivation
- Use standard predicates from `langnet.execution.predicates`
- Subject should be the canonical lemma/term
- Value can be simple (string) or complex (dict)
- Handle empty derivations gracefully

## Handler Registration

After creating handlers, register them in the `default_registry()`:

**File: `src/langnet/execution/registry.py`**

```python
from langnet.execution.handlers import mytool as mytool_handlers

def default_registry(use_stubs: bool = False) -> ToolRegistry:
    extract = {}
    derive = {}
    claim = {}

    # ... existing handlers ...

    # Register your new handlers
    extract["extract.mytool.html"] = mytool_handlers.extract_html
    derive["derive.mytool.morph"] = mytool_handlers.derive_morph
    claim["claim.mytool.morph"] = mytool_handlers.claim_morph

    if use_stubs:
        extract = defaultdict(lambda: handlers_stub.stub_extract, extract)
        derive = defaultdict(lambda: handlers_stub.stub_derive, derive)
        claim = defaultdict(lambda: handlers_stub.stub_claim, claim)

    return ToolRegistry(
        extract_handlers=extract,
        derive_handlers=derive,
        claim_handlers=claim,
    )
```

**Naming convention:**
- Extract: `extract.{tool}.{format}` (e.g., `extract.diogenes.html`)
- Derive: `derive.{tool}.{semantic_type}` (e.g., `derive.diogenes.morph`)
- Claim: `claim.{tool}.{semantic_type}` or `claim.{tool}` (e.g., `claim.diogenes.morph`)

## Testing Handlers

### Unit Testing Pattern

Create unit tests for each handler in `tests/`:

```python
import unittest
from langnet.clients.base import RawResponseEffect
from langnet.execution.handlers.mytool import extract_html, derive_morph, claim_morph
from query_spec import ToolCallSpec, ToolStage

class TestMyToolHandlers(unittest.TestCase):
    def test_extract_html_parses_lemmas(self):
        """Test HTML extraction produces correct structure."""
        # Arrange
        raw_html = b'<div class="entry"><span class="lemma">lupus</span></div>'
        call = ToolCallSpec(
            tool="extract.mytool.html",
            call_id="test-call-1",
            endpoint="http://example.com",
            params={},
            stage=ToolStage.TOOL_STAGE_EXTRACT,
        )
        raw = RawResponseEffect(
            response_id="test-resp-1",
            tool="fetch.mytool",
            call_id="fetch-call-1",
            endpoint="http://example.com",
            status_code=200,
            content_type="text/html",
            headers={},
            body=raw_html,
        )

        # Act
        result = extract_html(call, raw)

        # Assert
        self.assertEqual(result.kind, "html")
        self.assertIsNotNone(result.canonical)
        self.assertIn("lemmas", result.payload)
        self.assertEqual(result.handler_version, "v1")

    def test_derive_morph_builds_provenance(self):
        """Test derivation maintains provenance chain."""
        # ... similar pattern

    def test_claim_morph_uses_standard_predicates(self):
        """Test claims use standard predicate vocabulary."""
        # ... similar pattern
```

### Integration Testing

Test the full pipeline in `tests/integration/`:

```python
def test_mytool_full_pipeline(self):
    """Test complete fetch→extract→derive→claim pipeline."""
    with connect_duckdb(":memory:") as conn:
        apply_schema(conn)

        # Set up indexes
        raw_index = RawResponseIndex(conn)
        extraction_index = ExtractionIndex(conn)
        derivation_index = DerivationIndex(conn)
        claim_index = ClaimIndex(conn)

        # Build plan
        plan = _build_mytool_plan()

        # Execute with real handlers
        registry = default_registry(use_stubs=False)
        result = execute_plan_staged(
            plan=plan,
            clients=clients,
            registry=registry,
            raw_index=raw_index,
            extraction_index=extraction_index,
            derivation_index=derivation_index,
            claim_index=claim_index,
            plan_response_index=plan_index,
            allow_cache=True,
        )

        # Verify complete chain
        self.assertTrue(result.claims)
        self.assertTrue(result.raw_effects)
```

## Common Patterns

### Error Handling

```python
@versioned("v1")
def extract_html(call: ToolCallSpec, raw: RawResponseEffect) -> ExtractionEffect:
    try:
        html = raw.body.decode("utf-8", errors="replace")
        soup = BeautifulSoup(html, "lxml")
        # ... extraction logic ...
    except Exception as e:
        # Return error extraction
        return ExtractionEffect(
            extraction_id=stable_effect_id("ext", call.call_id, raw.response_id),
            tool=call.tool,
            call_id=call.call_id,
            source_call_id=raw.call_id,
            response_id=raw.response_id,
            kind="error",
            canonical=None,
            payload={"error": str(e), "error_type": type(e).__name__},
            handler_version="v1",
        )
```

### Handling Multiple Results

```python
@versioned("v1")
def claim_morph(call: ToolCallSpec, derivation: DerivationEffect) -> ClaimEffect:
    """Emit claim for primary result (first fact)."""
    facts = derivation.payload.get("facts", [])

    # Take first as canonical, store rest in metadata
    primary = facts[0] if facts else None
    alternatives = facts[1:] if len(facts) > 1 else []

    return ClaimEffect(
        claim_id=stable_effect_id("clm", call.call_id, derivation.derivation_id),
        # ...
        subject=primary["lemma"],
        predicate="has_pos",
        value={
            "pos": primary["pos"],
            "alternatives": [f["lemma"] for f in alternatives],
        },
        # ...
    )
```

### Using TypedDicts for Payloads

```python
from typing import TypedDict

class LemmaData(TypedDict, total=False):
    """Structured lemma data."""
    lemma: str
    pos: str
    definition: str
    citations: list[str]

@versioned("v1")
def extract_html(call: ToolCallSpec, raw: RawResponseEffect) -> ExtractionEffect:
    # ... parsing ...

    lemma: LemmaData = {
        "lemma": "lupus",
        "pos": "noun",
        "definition": "wolf",
    }

    return ExtractionEffect(
        # ...
        payload={"lemmas": [lemma]},
    )
```

## Debugging Handlers

### View Handler Versions

```bash
langnet-cli index status
# Shows handler_version column in extraction_index, derivation_index, claims
```

### Force Re-execution

```bash
# Clear cache for specific tool
langnet-cli index clear --tool diogenes

# Then run query again - will re-fetch and re-execute handlers
langnet-cli parse lat lupus
```

### Inspect Provenance Chains

```python
# In your handler
import json
print(json.dumps(prov, indent=2))
```

## Standard Predicates

Use predicates from `langnet.execution.predicates`:

- `HAS_POS` - Part of speech
- `HAS_LEMMA` - Canonical lemma
- `HAS_CASE` - Grammatical case
- `HAS_NUMBER` - Grammatical number (singular/plural)
- `HAS_GENDER` - Grammatical gender
- `HAS_TENSE` - Verb tense
- `HAS_VOICE` - Verb voice (active/passive)
- `HAS_MOOD` - Verb mood
- `HAS_PERSON` - Grammatical person (1st/2nd/3rd)
- `HAS_DECLENSION` - Noun/adjective declension
- `HAS_CONJUGATION` - Verb conjugation
- `HAS_DEGREE` - Comparison degree (positive/comparative/superlative)

For anchors, use `langnet.execution.anchors`.

## Checklist for New Handlers

- [ ] Extract handler with `@versioned("v1")`
- [ ] Derive handler with provenance chain
- [ ] Claim handler with standard predicates
- [ ] Registered in `default_registry()`
- [ ] Unit tests for each stage
- [ ] Integration test for full pipeline
- [ ] Error handling for malformed input
- [ ] TypedDicts for payload structure
- [ ] Documentation comments with examples

## Next Steps

- See `docs/storage-schema.md` for database schema details
- See `tests/test_execution_executor.py` for testing patterns
- See `src/langnet/execution/handlers/` for reference implementations
