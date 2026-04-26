# Contextual Word Meaning Lookup

**Status:** ⏳ TODO  
**Feature Area:** pedagogy  
**Owner Roles:** @architect for sequencing, @coder for implementation, @auditor for evaluation

## Goal

Use surrounding passage context to rank or explain possible meanings of a word.

## Dependency

Do not implement this before the semantic reduction MVP. Contextual ranking should consume sense buckets, not raw backend payloads.

## Proposed Input

- word-level claims
- sense buckets
- tokenized passage context
- optional citations/hydration metadata

## Proposed Output

- likely sense bucket
- alternative buckets
- explanation of evidence
- caveat when context is insufficient

## First Safe Task

Create a fixture with:

- one ambiguous Latin word
- two possible sense buckets
- one short passage context
- expected ranking rationale

No model calls or embeddings in the first task.
