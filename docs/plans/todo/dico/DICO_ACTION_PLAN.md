# DICO Integration Plan

**Status:** ⏳ TODO  
**Feature Area:** dico  
**Owner Roles:** @architect for scope, @coder for implementation

## Goal

Add bilingual dictionary evidence without hiding whether a gloss is original French, translated English, or generated.

## Intended Value

DICO-style bilingual data can improve learner-facing glosses and cross-language sense grouping, especially for Sanskrit dictionary entries whose source glosses are in French.

## Dependencies

- Stable claim predicates.
- Local DICO DuckDB index from Sanskrit Heritage `DICO/*.html`.
- Claim-to-WSU extraction before translated DICO glosses influence reduction.
- Sense bucket output that can accept additional witnesses.

## Non-Goals For Now

- Mixing translated glosses into source claims without provenance.
- Hiding whether a gloss is original, translated, or generated.

## Current State

- `langnet-cli databuild dico` builds `data/build/lex_dico.duckdb` from local DICO HTML.
- Heritage morphology claims expose `/skt/DICO/*.html#anchor` dictionary URLs.
- `triples-dump` resolves planned Sanskrit headwords through staged local DICO effects and emits French `has_sense`/`gloss` triples with DICO evidence.
- Heritage dictionary URL resolution remains as a fallback for exact anchor cases.
- DICO French → English translation is not cached or wired into triples yet.

## Next Task

Draft a fixture showing one original French DICO gloss, one translated English gloss, and the provenance/evidence fields needed to keep them separate.
