# Schema Consolidation & Claims Migration Plan

**Area**: infra/semantic-reduction  
**Source of truth**: proto (`vendor/langnet-spec`) + codegen  
**Goal**: Eliminate parallel schemas, introduce a structured Claim/Witness layer, and make tool expectations explicit for semantic distillation.

## Current State (Feb 2026)
- Adapters emit `DictionaryEntry` dataclasses (`src/langnet/schema.py`) as the working “universal” shape.
- Proto (`vendor/langnet-spec`) exists; `semantic_converter.py` maps `DictionaryEntry` → proto for `?format=semantic`, but adapters do not emit proto-generated types directly.
- Semantic reducer operates on the dataclass shape (not the proto) and does not output claims; provenance is limited to `source`/`source_ref`.
- No JSON Schema is committed; validation is via types + tests/fuzz.

## Target End State
- **Single authoritative contract**: proto definitions in `vendor/langnet-spec`; generated Python is the only schema used in code (no dual legacy/semantic formats).
- **Claims/Witness layer**: structured statements (subject, predicate, value, provenance, citations) emitted by adapters; reducer consumes claims and emits bucket-level claims.
- **Zoom levels**: prefer “research” (full claims/witnesses/raw facts) vs “didactic” (bucketed/curated for learners) as first-class modes, instead of maintaining separate legacy/semantic formats. Epistemic modes remain “open/skeptic” (aka open/closed) for merge strictness; keep naming consistent across docs when implemented.
- **Tool capability docs**: one page per tool describing “trusted for,” “not trusted for,” and expected claims/witness fields.

## Migration Steps

1) **Lock the proto and regenerate**
   - Review/align `vendor/langnet-spec/schema/langnet_spec.proto` with needed fields (definitions, morphology, provenance, claims/witnesses).
   - Run `just codegen` to regenerate Python; commit the generated package.

2) **Adopt proto-generated types as the working model**
   - Replace `DictionaryEntry` dataclasses with proto-generated equivalents in adapters and API/CLI responses.
   - Remove/retire `semantic_converter.py` or slim it to a no-op wrapper once adapters emit proto types directly.
   - Update cattrs/unstructure to handle proto types (or use `.to_dict()` from generated classes consistently).

3) **Introduce Claim/Witness model and emit from adapters**
   - Add a Claims/Witnesses section to the proto (if not present): subject (lemma/sense_ref), predicate (POS, gloss, morphology feature, citation), value, provenance (source/source_ref/timing), citations.
   - Update each adapter to emit claims alongside definitions/morphology:
     - Diogenes: senses + citations → witness/claim per sense_ref.
     - CDSL/Heritage: definitions + source_ref → claim per sense.
     - Whitaker’s/CLTK: morphology claims with provenance.
   - Add minimal tests per adapter asserting presence of claims for a small fixture set (lupus/logos/agni).

4) **Wire semantic reducer to claims and surface zoom levels**
   - Accept claims as input; emit bucket-level claims/constants with provenance.
   - Expose a single proto-based format with mode/zoom: `exhaustive` (all claims/witnesses/raw facts) vs `reduced` (bucketed/curated for didactic display).
   - Add snapshots for reducer output (small fixtures).

5) **Indexing for reuse**
   - Add an indexing layer (DuckDB/SQLite) that stores extracted claims/witnesses per lemma/source_ref to avoid re-querying backends on every request.
   - Provide `just` tasks to build/update indexes after backend data changes.
   - Resolver: API/CLI should hit indexes for cached claims when available, and refresh/populate on cache miss.

6) **Drift control and cleanup**
   - Add a check that proto-generated code is up to date (`just codegen` + diff).
   - Remove legacy dataclass schema usage after adapters are migrated.
   - Keep only one “Data Contracts & Claims” doc; update design docs to reference the proto as the contract.

## Tool Capability Documentation (deliverable)
- Create `docs/technical/backend/tool-capabilities.md` with per-tool sections:
  - Trusted for (e.g., Diogenes: lexicon senses + CTS citations; not morphology fidelity).
  - Not trusted for.
  - Expected claims/witness fields (source_ref, citations, gloss, pos, morphology).
  - Sample output references (link to fixtures).
- Link this doc from `docs/technical/backend/README.md`.

## Milestones
- M1: Proto reviewed + regenerated; adapters can import generated types (even if not fully migrated).
- M2: Adapters emit proto types; legacy dataclasses deprecated.
- M3: Claims emitted per adapter; small tests asserting claims present.
- M4: Reducer consumes claims and semantic format includes buckets/claims/constants.
- M5: Drift checks in CI; legacy converter removed.

## Risks / Mitigations
- **Drift between proto and code**: enforce codegen check in CI.
- **Adapter churn**: migrate one adapter at a time, keep legacy path for a short window.
- **Reducer integration**: gate semantic format exposure behind a flag until buckets/claims are stable.

## Commands (current)
- `just codegen` (run in repo root) — regenerates from proto.
- `devenv shell just -- test tests.test_semantic_reduction_clustering` — semantic reducer tests (needs deps).
- `devenv shell just -- cli query lat lupus --output json` — current legacy path.
