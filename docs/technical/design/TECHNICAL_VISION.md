# Technical Design Vision

This document connects LangNet's product vision to the implementation design. It describes the target shape of the system, the current boundary, and the rules that keep future semantic output auditable.

## Design Goal

LangNet should turn backend-specific language tools into a single evidence graph that can support learner-facing explanations.

The technical promise is:

```text
local tools and dictionaries
  -> staged effects
  -> claims and triples
  -> witness sense units
  -> deterministic sense buckets
  -> learner-facing display
```

Each layer should be inspectable on its own. Later layers may summarize earlier layers, but they must not erase provenance.

## Current Boundary

Implemented today:

- CLI lookup, parse, normalize, plan, plan-exec, triples-dump, encounter, databuild, and index commands.
- Query normalization and deterministic tool planning.
- Staged execution through fetch, extract, derive, and claim.
- DuckDB-backed storage indexes for raw responses and staged effects.
- Claim/triple projection for core Latin, Greek, and Sanskrit handlers.
- Runtime Witness Sense Unit extraction and exact sense-bucket reduction for the `encounter` command.
- Sanskrit `encounter` output that shows Heritage morphology/analysis rows alongside CDSL/DICO meaning evidence where available.
- Structured `triples-dump --output json` for claim/triple inspection.
- Translation-cache projection for cache-backed DICO/Gaffiot English gloss evidence.
- Fixture-backed tests for core claim contracts.

Not implemented yet:

- Broad semantic reduction beyond exact buckets.
- Mature display ranking, accepted-output coverage, and source-specific structuring across all representative examples.
- Hydration as a separate optional enrichment layer.
- Passage-level interpretation.

## Pipeline Layers

### 1. Normalize

Normalize the user's language and query into a canonical request. This is the first place where encoding differences should be made explicit.

Design reference: `query-planning.md`.

### 2. Plan

Build a deterministic tool-plan DAG for the normalized request. Tool calls should have stable IDs and explicit dependency edges.

Design reference: `query-planning.md`.

### 3. Fetch

Call local tools, services, or data stores and capture raw responses. Raw effects preserve the source payload and enough metadata to reproduce or inspect the call.

Design reference: `tool-response-pipeline.md`.

### 4. Extract

Parse raw responses into structured extraction payloads. Parsers may be backend-specific; the important contract is that raw references survive extraction.

Design reference: `entry-parsing.md`.

### 5. Derive

Normalize extraction payloads into handler-specific derivations. Backend quirks belong here, not in semantic reduction.

Design reference: `tool-response-pipeline.md`.

### 6. Claim

Project derivations into stable claims and triples. Claims are the first cross-backend contract and the current reliable input for downstream work.

Canonical reference: `../predicates_evidence.md`.

### 7. Witness

Extract source-backed Witness Sense Units from claim triples, especially `has_sense` plus `gloss` with evidence metadata.

Design references: `witness-contracts.md`, `semantic-structs.md`.

### 8. Reduce

Group WSUs into deterministic sense buckets. Start with exact normalized gloss grouping, then add narrowly tested near-match rules.

Design reference: `classifier-and-reducer.md`.

### 9. Hydrate

Add optional metadata such as CTS labels, dictionary URLs, and display source names. Hydration must not change base claim, witness, or bucket IDs.

Design reference: `hydration-reduction.md`.

### 10. Display

Render learner-facing output from buckets, morphology, citations, and disagreements. Display can be clearer than the source payload, but generated phrasing must be marked and evidence must remain available.

Product reference: `../../PEDAGOGICAL_PHILOSOPHY.md`.

## Core Contracts

### Claims Are The Integration Boundary

Semantic reduction should consume claims/triples, not backend parser internals. This keeps Diogenes, Whitaker, Heritage, CDSL, CLTK, and future tools independently replaceable.

### Evidence Travels Forward

Every source-backed triple should carry evidence metadata where available:

- source tool
- call ID
- response ID
- extraction ID
- derivation ID
- claim ID
- source reference
- raw blob reference

Optional fields may be absent, but they should not be fabricated.

### IDs Must Be Stable

Stable IDs are required for caching, tests, evidence inspection, and user trust. Do not include volatile runtime details in anchor IDs.

### Hydration Cannot Affect Reduction

Hydrated labels and links are useful display metadata. They must not alter witness extraction or sense-bucket identity.

### Generated Text Is Not Source Evidence

Generated summaries may help learners, but source glosses, morphology, and citations remain the evidence-bearing facts.

## Implementation Order

The technical roadmap originally followed this order:

1. Harden claim/evidence contracts. **In progress and fixture-backed for the core handlers.**
2. Improve evidence inspection. **Partly implemented through `triples-dump --output json` and `plan-exec --output json`; narrative trace examples still need refinement.**
3. Implement WSU extraction from fixture claims. **Implemented for the exact-bucket path.**
4. Add deterministic exact-match sense buckets. **Runtime-wired through `encounter`.**
5. Add learner-facing semantic output behind an explicit command or flag. **Started as `encounter`; not release-quality yet.**
6. Add hydration as optional enrichment. **Still future work.**
7. Expand to compounds and passages after word-level behavior is stable. **Still future work.**

This order is intentionally conservative. It keeps the system useful while preventing semantic output from becoming opaque.
