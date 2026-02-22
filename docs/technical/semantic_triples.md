# Semantic Triples: Cross-Language Design (LAT/GRC/SAN)

Goal: represent tool outputs as evidence-backed triples so downstream reducers can answer “tell me about X” with clear provenance. Keep raw payloads intact; triples are a projection, not a lossy replacement. Subjects/objects must stay clean graph nodes; provenance is attached alongside, not embedded. See also `docs/technical/triples_txt.md` for the flat-fact anchor/predicate rules this document aligns with, and `docs/technical/predicates_evidence.md` for the canonical predicate/evidence list.

## Core model
- **Node identity**
  - `headword`: normalized lemma (e.g., `eo`). Keep display forms separately as literals (e.g., `eo, eare, evi, etus`).
  - `form`: surface/inflected form (e.g., `ea`, `lupus`, `ἀνήρ`). Internally mint stable ids (hash of form + headword + tool + features) but do **not** encode provenance in the id.
  - `sense`: literal gloss text from the tool.
  - Tool/source info belongs in provenance metadata, not in the node id.
- **Predicates (language-agnostic)** — canonical set to use across tools
  - Lexical: `has_interpretation` (form→interp), `realizes_lexeme` (interp→lex), `variant_of`, `variant_form`, `has_sense`, `gloss`, `has_pronunciation`, `has_citation`, `has_frequency`.
  - Morph bundle: `has_pos`, `has_gender`, `has_case`, `has_number`, `has_person`, `has_tense`, `has_voice`, `has_mood`, `has_degree`, `has_declension`, `has_conjugation`; use `has_feature` with a map for tool-specific extras to avoid losing information.
  - Evidence linkage is separate metadata (see Provenance); do not overload subject/object.

### Quick predicate/evidence reference

See `docs/technical/predicates_evidence.md` for the canonical list and evidence schema. Handlers/tests should import those constants to keep memoization stable.
- **Objects**
  - Prefer normalized codes that work across LAT/GRC/SAN (`noun`, `verb`, `pronoun`, `ADJ`, cases like `NOM/ACC`, numbers `S/P`, genders `M/F/N/C`, persons `1/2/3`, tenses `PRES/IMP/PERF/FUT/FUTP/PLUP`, voices `ACTIVE/PASSIVE/MIDDLE`, moods `IND/SUB/IMP/INF/PPL`, degrees `POS/COMP/SUPER`).
  - If a tool emits a value outside the universal set, place it in `has_feature` as a literal and keep the raw string.

## Provenance and Evidence (standard schema)
- Each claim carries a `provenance_chain` (effect chain). For triples, attach an `evidence` block alongside (not in subject/object):
  - `source_tool` (e.g., `whitaker`, `diogenes`, `cltk`)
  - `call_id`, `response_id`, `extraction_id`, `derivation_id`, `claim_id`
  - `raw_ref` (line snippet/offset) and/or `raw_blob_ref` (`raw_text`/`raw_html` key)
  - `source_ref` when tools expose stable entry IDs (e.g., `mw:217497`)
- The claim payload keeps `raw_text`/`raw_html` and parsed structures; triples are stored alongside with their `evidence`.

## Whitaker projection (example: “ea”)
Input chunk = [inflection lines] + [codeline/headword] + [senses].
- Headword node: `eo` (display `eo, eare, evi, etus`)
  - Triples on headword: `(eo, has_pos, verb)`, `(eo, has_frequency, veryrare)`, `(eo, has_sense, "go, walk")`, etc.
  - Additional headwords per chunk: `is`, `idem`, etc. (display forms kept separately).
- Form nodes (one per inflection line):
  - `(ea_form_1, inflection_of, eo)`, `(ea_form_1, has_pos, verb)`, `(ea_form_1, has_tense, PRES)`, `(ea_form_1, has_mood, IMP)`, `(ea_form_1, has_person, 2)`, `(ea_form_1, has_number, S)`, `(ea_form_1, has_voice, ACTIVE)`.
  - Pronoun chunk: `(ea_form_2, inflection_of, is)`, `(ea_form_2, has_pos, pronoun)`, `(ea_form_2, has_case, NOM)`, `(ea_form_2, has_number, S)`, `(ea_form_2, has_gender, F)`, etc.
- Variants:
  - If a codeline lists multiple lemmas, pick the first as headword; add `(alt_lemma, variant_of, headword)` for the rest.
- Evidence:
  - Each triple includes an `evidence` record (tool, response_id, call_id, optional raw_line). Subjects/objects remain clean (no provenance baked in).

## Diogenes projection (outline)
- Headword: dictionary term from definition blocks; morph stems as forms.
- Forms: Perseus morph entries → `(form, inflection_of, headword)` plus morph tags.
- Senses: dictionary blocks → `(headword, has_sense, <entry text>)`.
- Citations: `(headword, has_citation, <URN or ref text>)` with evidence to the block.
- Keep `raw_html` in payload; parsed chunks map to triples with external `evidence`.

## CLTK projection (outline)
- Headword: lemma from lemmatizer.
- Form: original query form with `inflection_of -> lemma` if different.
- Pronunciation: `(lemma, has_pronunciation, <IPA string>)`.
- Lewis lines: `(lemma, has_sense, <line text>)` (or a dedicated `has_lexical_entry` literal).
- Keep `raw` JSON payload; attach `evidence` to triples.

## API/Claim payload shape (triple + metadata)
Represent triples as a list of `{subject, predicate, object, metadata}` where `metadata` carries evidence and optional qualifiers. Provenance stays out of subject/object.

```json
{
  "lemmas": [...],
  "wordlist": [...],   // or parsed blocks for diogenes
  "raw_text": "...",   // or raw_html
  "triples": [
    {"subject": "ea", "predicate": "inflection_of", "object": "eo", "metadata": {"evidence": {...}}},
    {"subject": "ea", "predicate": "has_form", "object": "ea", "metadata": {"evidence": {...}}},
    {"subject": "ea", "predicate": "has_pos", "object": "verb", "metadata": {"evidence": {...}}},
    {"subject": "eo", "predicate": "has_sense", "object": "go, walk", "metadata": {"evidence": {...}}},
    ...
  ]
}
```

Notes:
- `subject`, `predicate`, `object` are the triple; `metadata` carries `evidence` (tool, response_id, call_id, raw_ref) and optional qualifiers.
- When multiple inflection lines share the same surface form, you may mint internal opaque ids but still expose the surface form via a `has_form` triple. Do not encode provenance in ids.

## Queries enabled
- “Tell me about ea” → find triples where `subject` is an inflected form node for “ea”, follow `inflection_of` to headwords, read headword senses/pos.
- “Show pronoun uses of ea” → filter `has_pos` pronoun on form nodes, or headwords reached via `inflection_of`.
- “Give evidence for ea meaning ‘go, walk’” → return the `supported_by` metadata and `raw_text` slice for the sense triple on headword `eo`.
