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
- `has_root`
- `has_domain`
- `has_register`

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
  "source_tool": "whitaker|diogenes|cltk|cdsl|heritage|spacy|dico|gaffiot|bailly|lewis_1890|cts_index|translation",
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

Current source-tool values:

| Source tool | Role |
| --- | --- |
| `whitaker` / `whitakers` | Latin morphology and compact senses |
| `diogenes` | Latin/Greek dictionary, morphology, citations, and inflection data |
| `cltk` | supplemental lexicon/IPA data |
| `cdsl` | Sanskrit MW/AP90 dictionary rows |
| `heritage` | Sanskrit morphology and segmentation |
| `spacy` | supplemental Greek morphology |
| `dico` | Sanskrit-French dictionary rows |
| `gaffiot` | Latin-French dictionary rows |
| `bailly` | Greek-French dictionary rows |
| `lewis_1890` | Lewis 1890 Latin-English dictionary rows |
| `cts_index` | CTS citation/reader metadata |
| `translation` | derived English translation-cache witness |

## Rules

- Provenance belongs in `metadata.evidence`, not in anchor IDs.
- Forms link to interpretations when ambiguity exists.
- Senses attach to lexemes/sense nodes, not directly to ambiguous surface forms.
- `has_feature` is acceptable for preserving detail, but stable repeated fields should graduate to canonical predicates.
- Tests should assert evidence IDs whenever fixture data makes them available.
- Translation-derived triples should identify the translated source with fields
  such as `derived_from_tool`, `derived_from_source_ref`, or
  `derived_from_sense` in evidence/payload metadata rather than overwriting the
  original source witness.
