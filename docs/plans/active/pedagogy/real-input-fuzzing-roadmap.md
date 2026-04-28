# Real-Input Fuzzing Roadmap

**Status:** ACTIVE  
**Date:** 2026-04-28  
**Feature Area:** pedagogy / skt / reader-eval  
**Owner Roles:** @architect for sequencing, @sleuth for failure analysis, @coder for implementation, @auditor for acceptance review

## Purpose

Use real reader inputs to drive small, verified improvements across Latin,
Greek, and Sanskrit. The goal is not broad random fuzzing. The goal is a
repeatable loop:

1. run diagnostic probes on real forms;
2. identify evidence gaps or ranking/display failures;
3. implement one general source-backed improvement;
4. verify with focused tests, `reader-eval`, and `just validate-stabilization`.

## Current Evidence

Saved diagnostic runs:

- `examples/debug/fuzz_real_inputs_2026_04_28/`
- `examples/debug/fuzz_real_inputs_2026_04_28_latin_diogenes/`
- `examples/debug/fuzz_real_inputs_2026_04_28_greek_diogenes/`
- `examples/debug/fuzz_real_inputs_2026_04_28_sanskrit_heritage/`
- `examples/debug/fuzz_real_inputs_2026_04_28_sanskrit_cdsl/`

Current live fixture checkpoint:

- `just cli reader-eval --no-cache --translation-mode cache --output json`
- strict hit rate: 13/13
- meaning hit rate: 13/13
- Sanskrit seed tokens: 5/5 strict, 5/5 meaning

Corpus expansion checkpoint:

- `just cli reader-eval --fixture tests/fixtures/reader_eval_corpus_expansion.json --db-path examples/debug/corpus-probes/corpus-reader-eval-4.duckdb --translation-mode off --output json`
- strict hit rate: 14/14
- meaning hit rate: 14/14
- coverage: Jerome/Vulgate John 1:1, Greek New Testament John 1:1,
  Taittiriya Upanishad invocation, and Taittiriya Samhita 1.1.1.

The fuzz probes show strong tool-level evidence availability:

- Latin Diogenes classic forms: 8/8 tool hits.
- Greek Diogenes classic forms: 7/7 tool hits.
- Sanskrit Heritage reader forms: 8/8 tool hits.
- Sanskrit CDSL headword lookups: 8/8 tool hits.

These numbers are diagnostic. They show that source evidence exists, not that
the default learner display is already good.

## Completed In This Iteration

- Greek planning now keeps the canonical Diogenes lookup for dictionary senses
  and adds an optional morphology-only surface-form parse when normalization
  changes the token.
- The surface-form claim path excludes Diogenes dictionary definitions, so fuzzy
  surface lookups can add morphology without polluting meaning buckets.
- `μῆνιν` now reaches a Diogenes morphology row (`fem acc sg`) while meaning
  evidence still comes from the canonical `μῆνις` entry.
- Sanskrit compound display remains protected: Heritage segment lemmas are
  visible, while compound component lemmas do not become whole-token meaning
  fallbacks.
- Greek-script reader inputs now bypass the heavy normalizer and go directly to
  Diogenes, which keeps `ἀρχῇ` fast while preserving morphology and meaning
  evidence.
- Diogenes and Gaffiot source references now influence learner-display ranking,
  so primary senses like Greek `ἀρχῇ` "beginning" and Latin `erat` under
  `sum/esse` are preferred over alphabetically earlier sub-senses or adjacent
  entries.
- Sanskrit morphology fallback terms now act as preferred learner lemmas when
  sorting encounter buckets, so `tvā` leads with `yuṣmad` pronoun evidence
  instead of unrelated `tva` material.
- Morphology rows now provide ordered preferred lemmas for learner-display
  ranking. This lets analyzed forms such as Latin `principio` lead with the
  noun `principium` while preserving the visible alternate verb analysis.
- Preferred-lemma matching is transliteration-tolerant for common Sanskrit
  display variants, so DICO remains preferred for same-headword cases such as
  `varuṇaḥ` / `varu.na` and `ūrje` / `uurja`.

## Active Work Queue

### 1. Sanskrit Compound And Collection Expansion

Goal: give Sanskrit equal implementation attention while keeping runtime logic
general.

Tasks:

- Expand the Sanskrit real-input fuzz list with `agnim`, `jñānam`,
  `dharmasya`, `ātman`, `yogena`, and two transparent compounds.
- Keep the new Taittiriya corpus fixture active as a Vedic stress test for
  common particles, pronouns, and deity names.
- Add fixture-backed expected behavior for one compound where component evidence
  should be displayed but not treated as the whole-token meaning.
- Add no-network DICO/CDSL golden rows for common Sanskrit terms such as
  `agni`, `yoga`, `ātman`, and `jñāna` before relying on translated display.

Validation:

```bash
just test test_claim_contracts test_cli_encounter_output test_reader_eval
just cli reader-eval --language san --no-cache --translation-mode cache --output json
just validate-stabilization
```

### 2. Remaining Greek Strict Miss

Goal: close or explicitly classify the `Ἀχιλῆος` morphology gap.

Tasks:

- Confirm whether any configured source can produce structured morphology for
  epic proper-name genitives like `Ἀχιλῆος`.
- If a source can provide it, project the evidence through the existing
  `inflection_of` / `has_feature` graph contract.
- If no source can provide it, mark it as a known morphology-source gap in the
  fixture rather than inventing a word-specific runtime branch.

Validation:

```bash
just cli reader-eval --language grc --no-cache --translation-mode cache --output json
just test test_planner_core test_greek_anchor_normalization test_reader_eval
```

### 3. Latin Enclitic And Candidate Hygiene

Goal: improve `virumque` display without hiding evidence.

Tasks:

- Keep `vir + -que` visible as the reader-facing split.
- Keep unrelated analyzer candidates inspectable in JSON/triples, but lower
  their prominence in terminal display.
- Add an accepted-output test for the display order.

Validation:

```bash
just cli reader-eval --language lat --no-cache --translation-mode cache --output json
just test test_cli_encounter_output test_reader_eval
```

### 4. Fuzz Harness Alignment

Goal: make fuzz reports answer learner-quality questions.

Tasks:

- Add a small gold-list fixture per language with expected evidence,
  morphology, and display-quality checks.
- Add an `encounter`-oriented fuzz mode or helper that records reduction
  summaries, not only backend parser success.
- Keep query/compare modes diagnostic until they use the maintained CLI surface.

Validation:

```bash
just autobot fuzz list
just fuzz-tools
just validate-stabilization
```

## Guardrails

- Runtime code should not branch on famous surface words.
- Specific classical forms are appropriate in tests and fixtures.
- Prefer source-backed general rules: morphology projection, candidate ranking,
  suffix classes, compound/component contracts, and cache-backed translation
  evidence.
- Every implementation slice must leave Sanskrit, Latin, and Greek reader
  baselines visible through `reader-eval`.
