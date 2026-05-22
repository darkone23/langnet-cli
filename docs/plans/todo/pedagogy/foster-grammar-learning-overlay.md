# Foster Grammar Learning Overlay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a source-backed learning overlay that uses Foster functional grammar as the gateway into traditional Greek, Latin, and Sanskrit grammar.

**Architecture:** Add a curated grammar concept registry, map source-backed morphology candidates to concept IDs, then expose those concepts through CLI JSON and the web Forms panel. The overlay reads existing morphology evidence; it does not replace source parsers or invent grammar when evidence is missing.

**Tech Stack:** Python dataclasses/JSON serialization, existing morphology candidate and paradigm resolution contracts, static YAML or JSON concept data, Click CLI commands, SvelteKit web UI, `just` verification.

---

## Phase 1: Concept Registry

**Files:**
- Create: `src/langnet/learning/grammar_concepts.py`
- Create: `src/langnet/learning/grammar_concepts.json`
- Create: `tests/test_grammar_concepts.py`

- [x] Define a `GrammarConcept` dataclass with `id`, `kind`, `foster_gateway`, `plain_english`, `traditional`, `applies_to`, `processes`, `source_basis`, `examples`, and `skills`.
- [x] Expand the source-backed core slice with vocative, ablative,
  instrumental, locative, dual, neuter, and passive concepts.
- [ ] Add concepts for the remaining core case, number, gender, tense, mood, voice, declension, conjugation, inflection, stem, and ending families.
- [x] Add tests that load the registry and assert `case.genitive`, `process.declension`, and `process.conjugation` exist.
- [x] Verify with `just test test_grammar_concepts`.

## Phase 2: Morphology-To-Concept Mapper

**Files:**
- Create: `src/langnet/learning/concept_mapper.py`
- Create: `tests/test_grammar_concept_mapper.py`
- Modify: `src/langnet/paradigm/grammar.py`
- Modify: `docs/schemas/paradigm_resolution.v1.schema.json`

- [x] Map candidate features to concept IDs for the first case/number/gender/person/tense/mood/voice slice.
- [x] Attach concept IDs to paradigm resolution candidates.
- [ ] Preserve ambiguity by emitting multiple concept IDs when a form has multiple native analyses.
- [ ] Verify `λόγου`, `puellae`, and `putrāṇām` produce expected case/process concepts from live source-backed encounter payloads.
- [x] Verify with `just test test_grammar_concept_mapper test_paradigm_resolution_contract`.

## Phase 3: CLI Learning Surface

**Files:**
- Modify: `src/langnet/cli.py`
- Create: `tests/test_cli_learning_overlay.py`
- Modify: `docs/OUTPUT_GUIDE.md`

- [x] Add `learn concepts`, `learn concept <concept-id>`, and `learn map --feature key=value --output json`.
- [x] Add `--include-learning/--no-include-learning` to `encounter`.
- [x] Include concept summaries under candidate-local `learning_overlay` payloads.
- [x] Keep human-readable output compact by limiting this slice to JSON output.
- [x] Verify the first CLI surface with `just test test_cli_learn`.
- [x] Verify encounter integration with `just test test_cli_encounter_output`.

## Phase 3B: Reader Annotation Goals

**Files:**
- Modify: `docs/GRAMMAR_LEARNING_OVERLAY.md`
- Modify: future reader annotation module and tests when implementation starts.

- [x] Capture the sentence-markup education target: subjects, objects, verbs, clauses, distant connections, and connectives.
- [ ] Design a CLI JSON shape for sentence annotations before any web UI work.
- [ ] Map annotation roles to existing or new concept IDs.
- [ ] Keep annotation layers toggleable in downstream UI.
- [ ] Preserve caveats when sentence-level relations are parser guesses rather than source-backed facts.

## Phase 3C: Grammar Source Works

**Files:**
- Modify: `docs/technical/grammar-concept-registry.md`
- Create: `docs/technical/grammar-source-anchors.md`
- Future: extend `GrammarConcept` with structured evidence links.

- [x] Identify local grammar source anchors:
  `Aṣṭādhyāyī`, `Nirukta`, Varro's `De Lingua Latina`, Dionysius Thrax,
  and Apollonius Dyscolus.
- [x] Add a maintained source-anchor map with local CTS/CTSv2 reader addresses
  and external research grounding.
- [x] Add structured concept evidence fields for reader work/segment links.
- [x] Add `learn evidence-report` to summarize work-level and segment-level
  evidence coverage.
- [x] Promote verified Sanskrit reader segment citations for nominative,
  genitive, singular, plural, guṇa, vṛddhi, and savarṇa.
- [x] Promote verified Sanskrit reader segment citations for dative,
  accusative, vocative, ablative, instrumental, locative, neuter, and passive.
- [x] Promote verified Greek Dionysius Thrax reader segment citations for
  case, number, gender, tense, mood, voice, person, and conjugation.
- [x] Promote verified Latin Donatus/Dositheus/Priscian reader segment
  citations for case, number, gender, tense, mood, voice, person, and
  conjugation.
- [ ] Find a clean segment-level source for `process.declension`; do not use
  weaker lines that merely contain the word unless they support the teaching
  claim directly.

## Phase 4: Web Learn This Form Panel

**Files:**
- Modify: `webapp/src/lib/paradigm-resolution.ts`
- Create: `webapp/src/lib/grammar-learning.ts`
- Create: `webapp/src/lib/grammar-learning.test.ts`
- Modify: `webapp/src/routes/+page.svelte`
- Modify: `webapp/docs/UI.md`

- [ ] Normalize learning overlay fields from CLI/API payloads.
- [ ] Add a compact "Learn this form" section under Forms.
- [ ] Show Foster gateway, native morphology, traditional names, process rule, and examples.
- [ ] Keep the panel collapsible or visually compact.
- [ ] Verify with `cd webapp && just verify`.

## Phase 5: Advanced Grammar Processes

**Files:**
- Modify: concept registry and mapper files from earlier phases.
- Modify: dictionary parser tests as new dictionary parsing work lands.

- [ ] Add Sanskrit sandhi concepts.
- [ ] Add compound concepts.
- [ ] Add principal part concepts.
- [x] Add first Sanskrit sound-change/relation concepts, `sound_change.guna`,
  `sound_change.vrddhi`, and `sound_relation.savarna`, with verified
  Aṣṭādhyāyī segment citations.
- [ ] Add Sanskrit vibhakti, tiṅ, and lakāra concepts.
- [ ] Add Greek augment/reduplication concepts.
- [ ] Add Latin declension/conjugation class teaching.

## Phase 6: Audit And Validation

**Files:**
- Modify: `docs/technical/grammar-concept-registry.md`
- Modify: `docs/technical/morphology-projection-audit.md`
- Create or extend focused audit tests.

- [ ] Add source-backed fixtures for each concept family.
- [x] Add accepted-output fixtures for `learn concept case.genitive`,
  `learn map` for genitive plural masculine, and the `putrāṇām` encounter
  learning overlay.
- [x] Verify exposed concepts carry Foster labels, traditional terms, examples,
  skills, source basis, and structured work-level evidence.
- [ ] Verify concepts do not appear without source-backed morphology or explicit registry evidence.
- [x] Run `just lint-all`.
- [x] Run `just test-fast`.
- [ ] Run `cd webapp && just verify`.

## Success Definition

- A learner can look up `λόγου`, `puellae`, or `putrāṇām` and see a Foster gateway plus traditional grammar names.
- CLI JSON exposes the same concept IDs the web app displays.
- Ambiguous forms preserve ambiguity instead of forcing one teaching answer.
- Dictionary parsing work can add new concepts by emitting canonical grammar facts and registry mappings.
