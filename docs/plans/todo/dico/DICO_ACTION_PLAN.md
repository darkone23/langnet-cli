# DICO Integration Plan

**Status:** ⏳ TODO  
**Feature Area:** dico  
**Owner Roles:** @architect for scope, @coder for implementation

## Goal

Add bilingual dictionary evidence only after the claim/evidence contract and semantic reduction MVP are stable.

## Intended Value

DICO-style bilingual data can improve learner-facing glosses and cross-language sense grouping, especially for Sanskrit and classical-language dictionary entries with French or English glosses.

## Dependencies

- Stable claim predicates.
- Claim-to-WSU extraction.
- Sense bucket output that can accept additional witnesses.

## Non-Goals For Now

- Adding another backend before semantic reduction exists.
- Mixing translated glosses into source claims without provenance.
- Hiding whether a gloss is original, translated, or generated.

## First Task

Draft a fixture showing one original gloss, one translated gloss, and the provenance/evidence fields needed to keep them separate.
