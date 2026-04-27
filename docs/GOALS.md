# LangNet Goals

This document is the short goals card. The fuller product vision is `docs/VISION.md`; learner-facing grammar policy is `docs/PEDAGOGICAL_PHILOSOPHY.md`.

LangNet is a classical-language learning tool for Latin, Greek, and Sanskrit. Its purpose is to help readers move from an inflected word in a text to a clear, evidence-backed explanation of form, meaning, and source support.

## Product Goal

LangNet should answer:

> “What can this word mean here, what form is it, and which sources support that answer?”

The project is not only a backend aggregator. It is an educational layer over dictionaries, morphology analyzers, citations, and semantic grouping.

## Primary Users

- Students reading classical texts.
- Teachers preparing lexical or grammatical explanations.
- Researchers checking dictionary and morphology evidence quickly.
- Developers building structured classical-language datasets.

## Core Principles

1. **Evidence first** — every displayed fact should trace back to a tool response, source entry, citation, or explicit derivation.
2. **Learner clarity** — output should lead with useful meaning and morphology, not backend implementation details.
3. **Progressive disclosure** — beginners see concise explanations; advanced users can inspect raw claims, triples, and provenance.
4. **Cross-language consistency** — Latin, Greek, and Sanskrit should share a claim/evidence model even when their tools differ.
5. **Determinism before intelligence** — stable exact rules and tests come before embeddings, fuzzy grouping, or broad semantic inference.

## Semantic Direction

LangNet is moving toward this layered model:

1. **Tool evidence** — raw responses from Diogenes, Whitaker, CLTK, Heritage, CDSL, and future tools.
2. **Claims/triples** — normalized assertions such as `lex:lupus has_sense sense:...` with evidence metadata.
3. **Witness Sense Units** — source-backed gloss witnesses extracted from claims.
4. **Sense buckets** — deterministic clusters of equivalent or near-equivalent meanings.
5. **Learner display** — ordered summaries that explain meaning, morphology, references, and disagreements.

The current runtime has a first version of this path: staged tool evidence becomes claims/triples, exact Witness Sense Units become deterministic buckets, and `langnet-cli encounter` displays the first learner-facing word encounter. That is an MVP, not the finished semantic layer. The next major product work is to make the `encounter` output stable, source-clean, well-ranked, and accepted-output tested before adding broader semantic inference.

## Non-Goals For Now

- Replacing source dictionaries with opaque generated answers.
- Building passage-level interpretation before word-level claims and sense buckets are stable.
- Adding embedding similarity before deterministic semantic reduction exists.
- Treating HTTP/API work as more important than CLI correctness and evidence inspection.

## Current North Star

Build a reliable word-level evidence engine first. Then reduce evidence into learner-facing semantic explanations.
