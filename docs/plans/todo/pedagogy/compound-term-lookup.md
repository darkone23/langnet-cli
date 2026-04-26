# Compound Term Lookup

**Status:** ⏳ TODO  
**Feature Area:** pedagogy  
**Owner Roles:** @architect for scope, @coder for implementation

## Goal

Explain compound terms, especially Sanskrit compounds, using the same word-level claim and semantic reduction pipeline.

## Dependency

This should follow stable word-level claims and semantic buckets. Compound support must not create a parallel lookup path that bypasses evidence.

## Intended Flow

```text
compound input
  → tokenize / split candidate components
  → run component lookup
  → reduce component senses
  → display compound explanation with evidence
```

## First Task

Create a service-free fixture for one Sanskrit compound with:

- original input
- candidate split
- component lexeme anchors
- expected component claims
- expected learner explanation

## Non-Goals

- Full passage interpretation.
- LLM-only compound explanation.
- Untested Sanskrit sandhi expansion.
