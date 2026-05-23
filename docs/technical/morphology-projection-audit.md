# Morphology Projection Audit

This page records which sources can project morphology into LangNet's shared
candidate path. The goal is to keep dictionary parsing work honest: source
handlers may keep raw source payloads, but stable grammar facts should also be
available as canonical predicates or `has_morphology` objects.

## Coverage Matrix

| Source | Runtime role | Projection shape | Candidate path status |
| --- | --- | --- | --- |
| Heritage | Primary Sanskrit morphology | `form:* has_morphology {lemma, form, features, analysis}` | Covered by `langnet.morphology.candidates`; pipe-separated legacy analyses are split into separate resolver candidates |
| Whitaker | Primary Latin morphology facts | `form:* has_interpretation interp:*`; `interp:* realizes_lexeme lex:*`; canonical `has_case`, `has_number`, `has_gender`, `has_person`, `has_tense`, `has_voice`, `has_mood`; lexeme-level `has_declension` and `has_conjugation` | Covered, including lexeme-level morphology inherited by form candidates |
| Diogenes/Morpheus | Primary Greek/Latin source-backed morphology and table bridge | `form:* inflection_of lex:*`; `form:* has_form`; canonical form-level morphology predicates promoted from Morpheus tags | Covered, including Greek learner-key bridge for known lemmas such as `logos -> lo/gos` |
| spaCy | Optional supplemental Greek fallback | `form:* inflection_of lex:*`; canonical form-level morphology predicates | Covered when spaCy is available; not a required production source |
| CLTK | Lexicon/pronunciation/sense support | `form:* inflection_of lex:*`, pronunciation, senses | Not treated as a morphology source because it does not currently emit stable grammar features |

## Required Contract

For a source to participate in didactic morphology, it must provide enough
evidence for the shared candidate layer to produce:

- `lemma`
- `observed_form`
- `features` with exact native grammar where available
- Foster display text derived from those features
- source provenance
- ranking reasons that distinguish strongly determined analyses

Dictionary parsing should preserve source-specific details, but repeated facts
such as declension, conjugation, case, number, gender, person, tense, mood, and
voice should graduate to canonical predicates when possible.

## Current Resolver Behavior

- Heritage analysis strings with alternates, such as `m. sg. voc. | n. sg.
  voc.`, are preserved as separate candidates instead of being collapsed into a
  single feature map.
- Candidate sets with multiple concrete analyses for the same observed form are
  marked with `ambiguous-analysis` and demoted from `high` to `medium`
  confidence.
- Exact observed-form matches are preferred when several fetchable Sanskrit
  candidates are returned for nearby lemmas.
- Dictionary meanings are not yet used to challenge or rerank morphology. Cases
  such as `sambuddhi`, where DICO/CDSL describe a grammar term for vocative
  address while Heritage offers nominal morphology, remain a planned
  dictionary-entry parsing/reranking task.

## Verification

Focused morphology checks:

```bash
just test test_morphology_candidates test_diogenes_morpheus_morphology test_spacy_morphology_projection test_whitakers_triples test_cli_encounter_output test_paradigm_resolver
```

Full backend gate:

```bash
just lint-all
just test-fast
```

Web gate:

```bash
cd webapp && just verify
```
