# Semantic Structures

Current and target structures for semantic reduction. The exact-bucket path is
implemented for `encounter`; broader semantic matching remains future work.

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
- optional source-entry and translated-segment display metadata

## SenseBucket

Represents a deterministic group of related WSUs.

Fields:

- `bucket_id`
- `normalized_gloss`
- `display_gloss`
- `witnesses`
- `confidence_label`
- `notes`
- ranking/display helpers derived from witness count, source order, translation
  status, and learner-quality policy

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
- Reader, word-index, paradigm, and translation-cache schemas remain separate
  CLI JSON contracts unless they are explicitly projected into claims/triples.
