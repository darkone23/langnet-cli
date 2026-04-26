# Witness Contracts

A witness is a source-backed assertion used by semantic reduction.

## Minimum Witness Requirements

For a sense witness:

- lexeme anchor
- sense anchor or source-local sense key
- gloss text
- source tool
- claim ID
- evidence block

## Evidence Requirements

Where available:

- `call_id`
- `response_id`
- `extraction_id`
- `derivation_id`
- `claim_id`
- `source_ref`
- `raw_blob_ref`

Optional fields may be absent. They should not be empty strings.

## Reducer Requirements

The reducer must:

- preserve witness evidence
- avoid assigning one witness to multiple buckets
- mark generated display text separately from source glosses
- expose source disagreements instead of hiding them

## Test Requirements

Use hand-written fixtures first. Live backends are not required to test witness contracts.
