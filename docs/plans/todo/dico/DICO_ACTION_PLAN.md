# DICO Refinement Plan

**Status:** TODO refinement
**Feature Area:** dico
**Owner Roles:** @architect for scope, @coder for implementation

## Goal

Refine already-integrated DICO evidence so it is useful for learners without
hiding whether a gloss is original French, cache-backed English translation, or
generated display metadata.

## Intended Value

DICO-style bilingual data can improve learner-facing glosses and cross-language sense grouping, especially for Sanskrit dictionary entries whose source glosses are in French.

## Non-Goals For Now

- Mixing translated glosses into source claims without provenance.
- Hiding whether a gloss is original, translated, or generated.
- Making live translation part of default lookup.

## Completed Baseline

- `langnet-cli databuild dico` builds `data/build/lex_dico.duckdb` from local DICO HTML.
- Heritage morphology claims expose `/skt/DICO/*.html#anchor` dictionary URLs.
- `triples-dump` resolves planned Sanskrit headwords through staged local DICO effects and emits French `has_sense`/`gloss` triples with DICO evidence.
- Heritage dictionary URL resolution remains as a fallback for exact anchor cases.
- DICO French-to-English translation is cache-backed and can be projected into
  `encounter` as derived English evidence.
- `encounter --translation-mode cache` reads exact translation cache hits.
- `encounter --translation-mode auto` explicitly populates missing DICO
  translation rows through OpenRouter, then displays the projected evidence.

## Remaining Tasks

1. Add compact learner glosses over full translated DICO entries.
2. Add reader-form/headword fixtures for common aliases such as `karma` and
   `karman`.
3. Add more no-network DICO golden rows for common terms such as `agni`, `yoga`,
   `karman`, and `ātman`.
4. Keep source French and derived English evidence separate in every display and
   JSON path.
