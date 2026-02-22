# Predicate & Evidence Reference

Single source of truth for predicates and evidence fields used by tool handlers, claim emitters, and tests. Use these constants for memoization and validation.

## Anchors
- `form:<surface>`
- `interp:form:<surface>→lex:<lemma>#<pos>`
- `lex:<lemma>#<pos>`
- `sense:<lex>#<sense-key>`

## Predicates (canonical)
- Linking: `has_interpretation` (form→interp), `realizes_lexeme` (interp→lex)
- Lexical: `has_sense`, `gloss`, `variant_form`, `variant_of`, `has_pronunciation`, `has_citation`, `has_frequency`
- Morphology: `has_pos`, `has_gender`, `has_case`, `has_number`, `has_person`, `has_tense`, `has_voice`, `has_mood`, `has_degree`, `has_declension`, `has_conjugation`
- Extras: `has_feature` (map for tool-specific attributes), `has_form` literal when opaque form IDs are minted

## Evidence block (per triple/claim)
```json
{
  "source_tool": "whitaker|diogenes|cltk|cdsl|heritage",
  "call_id": "...",
  "response_id": "...",
  "extraction_id": "...",
  "derivation_id": "...",
  "claim_id": "...",
  "raw_ref": "...",          // optional line snippet/offset
  "raw_blob_ref": "raw_text|raw_html", // optional
  "source_ref": "mw:217497"  // optional stable entry id
}
```

## Usage Notes
- Do not bake provenance into IDs; keep it in evidence/provenance_chain.
- Forms only link to interpretations; POS lives on interpretations (and optionally lex).
- Senses/glosses attach to lex/sense nodes, not forms.
- Variants attach to lex; expose surface forms via `has_form` when using opaque IDs.

Machine-readable export available at `docs/technical/predicates_evidence.json` (for handler/test imports).
