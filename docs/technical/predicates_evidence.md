# Predicate and Evidence Reference

This is the canonical documentation contract for claim triples. Keep it aligned with `src/langnet/execution/predicates.py` and handler tests.

## Anchor Forms

| Anchor | Meaning |
| --- | --- |
| `form:<surface>` | observed or normalized surface form |
| `interp:<form>→<lexeme>` | scoped interpretation of an ambiguous form |
| `lex:<lemma>` | normalized lexeme |
| `lex:<lemma>#<pos>` | normalized lexeme scoped by part of speech |
| `sense:<lex>#<hash>` | source-backed sense node |

## Canonical Predicates

### Linking

- `has_interpretation`
- `realizes_lexeme`
- `inflection_of`
- `has_form`

### Lexical

- `has_sense`
- `gloss`
- `variant_form`
- `variant_of`
- `has_pronunciation`
- `has_citation`
- `has_frequency`

### Morphology

- `has_morphology`
- `has_pos`
- `has_gender`
- `has_case`
- `has_number`
- `has_person`
- `has_tense`
- `has_voice`
- `has_mood`
- `has_degree`
- `has_declension`
- `has_conjugation`

### Escape Hatch

- `has_feature` — use for tool-specific structured attributes that do not yet have a stable cross-language predicate.

## Evidence Block

Every evidence-backed triple should use:

```json
{
  "source_tool": "whitaker|diogenes|cltk|cdsl|heritage|spacy",
  "call_id": "...",
  "response_id": "...",
  "extraction_id": "...",
  "derivation_id": "...",
  "claim_id": "...",
  "raw_ref": "...",
  "raw_blob_ref": "raw_text|raw_html|raw_json",
  "source_ref": "mw:123"
}
```

Optional fields should be omitted when unavailable, not filled with empty strings.

## Rules

- Provenance belongs in `metadata.evidence`, not in anchor IDs.
- Forms link to interpretations when ambiguity exists.
- Senses attach to lexemes/sense nodes, not directly to ambiguous surface forms.
- `has_feature` is acceptable for preserving detail, but stable repeated fields should graduate to canonical predicates.
- Tests should assert evidence IDs whenever fixture data makes them available.
