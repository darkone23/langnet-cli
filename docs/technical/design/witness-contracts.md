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

## Source Text Requirements

Dictionary-entry witnesses should keep source text traceable instead of reducing it
to an opaque display string. When a handler has dictionary-entry text, attach:

- `display_gloss`: display-safe text for learner output
- `source_entry`: row or parser identity, including source reference and original text when available
- `source_segments`: conservative ordered segments with `raw_text`, `display_text`, `segment_type`, and `labels`
- `source_notes`: optional summary of confidently typed note/reference segments

For translated DICO/Gaffiot output, cached English translations are derived
witnesses. They should carry translation evidence plus parsed display helpers:

- `parsed_glosses`: individual English gloss candidates parsed from the translated text
- `translated_segments`: ordered translated-output segments

These parsed fields support learner display and future reduction experiments. They
do not replace source glosses, and they must not be treated as unproven original
dictionary facts.

## Reducer Requirements

The reducer must:

- preserve witness evidence
- avoid assigning one witness to multiple buckets
- mark generated display text separately from source glosses
- expose source disagreements instead of hiding them

## Test Requirements

Use hand-written fixtures first. Live backends are not required to test witness contracts.
