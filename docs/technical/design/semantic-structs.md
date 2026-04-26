# Semantic Structures

Planned structures for the semantic reduction MVP.

## WitnessSenseUnit

Represents one source-backed sense witness.

Fields:

- `wsu_id`
- `lexeme_anchor`
- `sense_anchor`
- `gloss`
- `source_tool`
- `claim_id`
- `evidence`

## SenseBucket

Represents a deterministic group of related WSUs.

Fields:

- `bucket_id`
- `normalized_gloss`
- `display_gloss`
- `witnesses`
- `confidence_label`
- `notes`

## ReductionResult

Represents all buckets for one lookup target.

Fields:

- `query`
- `language`
- `lexeme_anchors`
- `buckets`
- `unbucketed_witnesses`
- `warnings`

## Design Rules

- IDs must be deterministic.
- Evidence must survive reduction.
- Display glosses are not source facts unless marked as generated.
- Reducer input is claims/triples, not backend-specific payloads.
