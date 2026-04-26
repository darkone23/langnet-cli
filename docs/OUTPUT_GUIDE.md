# Output Guide

LangNet currently exposes two useful output layers:

1. **Backend lookup output** from `lookup`.
2. **Evidence-backed claim/triple output** from `plan-exec` and `triples-dump`.

The learner-facing semantic layer is planned but not implemented yet.

## `lookup`

`lookup` is useful for quick inspection. Its JSON is backend-keyed.

```bash
just cli lookup lat lupus --output json
```

Typical shape:

```json
{
  "whitakers": [...],
  "diogenes": {...},
  "cltk": {...}
}
```

`lookup --output pretty` is a terminal summary. It is intentionally compact and should not be treated as the final semantic schema.

## `plan-exec`

`plan-exec` runs the staged runtime:

```text
normalize → plan → fetch → extract → derive → claim
```

Use it when you need to know which tools were selected and what claim effects were produced.

```bash
just cli plan-exec lat lupus --output json
```

## `triples-dump`

`triples-dump` is the best current evidence-inspection command.

```bash
just triples-dump lat lupus whitakers
just triples-dump san agni cdsl
```

Use the third argument to narrow the tool family. Examples:

- `whitakers`
- `diogenes`
- `cdsl`
- `all`

Triples use this shape:

```json
{
  "subject": "lex:lupus#noun",
  "predicate": "has_sense",
  "object": "sense:lex:lupus#noun#...",
  "metadata": {
    "evidence": {
      "source_tool": "whitaker",
      "call_id": "...",
      "response_id": "...",
      "extraction_id": "...",
      "derivation_id": "...",
      "claim_id": "...",
      "raw_blob_ref": "raw_text"
    }
  }
}
```

## Reading Triples

| Anchor | Meaning |
| --- | --- |
| `form:<surface>` | observed input or inflected surface form |
| `interp:...` | one scoped interpretation of a form |
| `lex:<lemma>` | normalized lexical item |
| `sense:<lex>#...` | source-backed sense node |

Common predicates:

- `has_interpretation`
- `realizes_lexeme`
- `has_sense`
- `gloss`
- `has_citation`
- `has_morphology`
- `has_pos`, `has_case`, `has_number`, `has_gender`, `has_tense`, `has_voice`, `has_mood`
- `has_feature` for tool-specific details

The canonical predicate/evidence reference is `docs/technical/predicates_evidence.md`.

## Evidence Fields

| Field | Meaning |
| --- | --- |
| `source_tool` | backend or source family that produced the assertion |
| `call_id` | planned tool call that led to the claim |
| `response_id` | raw response used by extraction, when available |
| `extraction_id` | structured extraction effect |
| `derivation_id` | normalized derivation effect |
| `claim_id` | claim projection that emitted the triple |
| `source_ref` | stable dictionary/source entry reference, when available |
| `raw_blob_ref` | raw payload field such as `raw_text`, `raw_html`, or `raw_json` |

## Display Policy

Future learner-facing output should order information this way:

1. Headword/form.
2. Grouped meanings.
3. Morphology.
4. Citations and source evidence.
5. Source disagreements or caveats.

Until semantic reduction exists, backend-keyed output remains the honest representation.
