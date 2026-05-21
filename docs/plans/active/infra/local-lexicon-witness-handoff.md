# Local Lexicon Witness Handoff

**Status:** active  
**Feature Area:** infra  
**Current owner:** maintainers

## Purpose

Keep local lexical witness tooling reliable enough for learner-facing encounter,
word-index, and paradigm work. A local witness is useful only when it can be
run through maintained `just` recipes and its output can be compared against
source-backed claims.

## Maintained Commands

Use the current wrappers:

```bash
just cli tools lat
just cli tools grc
just cli tools san
just triples-dump lat puella whitakers
just triples-dump grc logos diogenes
just triples-dump san putra heritage
```

## Current Action Items

- Keep helper examples routed through `just cli`, `just parse`, or
  `just triples-dump`.
- Do not document direct backend shell invocations as the normal path.
- When a witness feeds learner output, add or update a fixture-backed contract
  test for the emitted triples.
- Prefer source-backed morphology predicates over generic feature bags when a
  tool exposes stable grammar facts.

## Foster-Friendly Morphology Link

The current morphology work depends on this handoff: Heritage, Whitaker, and
Diogenes/Morpheus should all promote stable facts into predicates such as
`has_case`, `has_number`, `has_gender`, `has_person`, `has_tense`, `has_voice`,
and `has_mood`. Generic `has_feature` payloads are acceptable for preserving
raw source details, but they should not be the only representation of repeated
grammar facts.
