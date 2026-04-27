# Learner Encounter Roadmap

**Status:** active  
**Date:** 2026-04-27  
**Feature Area:** pedagogy / semantic-reduction  

## Purpose

This plan takes stock of the current `encounter` command across Sanskrit, Latin,
and Greek, then turns the gap between current output and reasonable learner
encounters into implementable, validated tasks.

The core finding is direct:

> `encounter` has useful source plumbing, but it is not yet a good learner
> experience. It still exposes source order, source notation, and backend
> candidate noise too directly.

The next phase should refine the existing framework rather than expand the
surface area. The goal is a source-backed learner display layer over claims and
WSUs, not a replacement for the evidence model.

## Current Snapshot

Sample commands reviewed:

```bash
devenv shell -- bash -c 'langnet-cli encounter san nirudha --max-buckets 8'
devenv shell -- bash -c 'langnet-cli encounter san dharma --max-buckets 8'
devenv shell -- bash -c 'langnet-cli encounter lat lupus --max-buckets 8'
devenv shell -- bash -c 'langnet-cli encounter grc logos --max-buckets 8'
```

### Sanskrit

What works:

- Heritage morphology reaches the encounter output.
- CDSL and DICO claims are available for Sanskrit meaning evidence.
- CDSL entries carry `display_iast`, `display_slp1`, source refs, source
  entries, segments, and notes where recognized.
- Stale normalization cache fallback now recovers `nirudha` into `nirūḍha`
  evidence instead of stopping at unknown Heritage morphology.

Current learner failures:

- `nirudha` ranks obscure or technical CDSL senses before more readable learner
  meanings.
- CDSL source notation leaks into learner text: `nir—UQa`, `ni-°rUQa`, source
  numbering, abbreviations, and dictionary editorial marks appear as primary
  meanings.
- Some display conversion is still wrong or over-aggressive, such as `BhP.`
  becoming `bhhph.` in display text.
- DICO can contain helpful learner material, but untranslated French source
  buckets are hidden behind the default bucket limit unless translation cache
  rows exist and are requested.
- Debug/runtime recovery warnings are useful to developers but inappropriate as
  default learner-facing text.

### Latin

What works:

- Whitaker and Diogenes both emit evidence that can become WSU buckets.
- Gaffiot local entries and cache-backed translations can project derived
  English witnesses when matching cache rows exist.
- The reducer can rank translated buckets and multi-witness buckets in tests.

Current learner failures:

- `lupus` shows unrelated normalized candidates in `Forms`, such as `id#noun`,
  `age#interjection`, and `ago#verb`.
- The first displayed meaning can be unrelated to the user word, such as
  calendar or demonstrative entries from noisy analyzer candidates.
- Diogenes dictionary sections are long source excerpts rather than concise
  learner senses.
- Gaffiot translations are not automatically used unless the caller requests the
  translation cache.

### Greek

What works:

- Diogenes/LSJ evidence reaches encounter output.
- Greek source citations and examples remain source-visible.
- Greek input can produce many evidence-backed sense buckets.

Current learner failures:

- `logos` produces a very large LSJ-style list with no compact primary summary.
- Ordering follows source/backend structure rather than learner usefulness.
- Long examples, citations, and Greek source phrases crowd out the English
  meaning head.
- There is no distinction between "top learner senses" and "full source
  evidence".

## Reasonable Learner Encounter Bar

A reasonable word encounter should answer these questions in this order:

1. What word/headword did LangNet resolve?
2. What form could the surface token be?
3. What are the most useful learner meanings?
4. Which sources support each meaning?
5. What source details or ambiguities should an advanced user inspect?

For terminal output, the default view should satisfy these rules:

- Lead with a compact learner summary, not raw dictionary blobs.
- Show source-backed morphology before meanings when it helps interpret the
  form.
- Prefer readable English meanings when they are evidence-backed.
- Keep raw source text inspectable through JSON/triples, but do not make raw
  notation the primary learner prose.
- Label provisional, translated, source-only, or single-witness results clearly.
- Never silently omit source content; move complex material into structured
  source fields or advanced output.
- Hide developer recovery diagnostics unless `--debug` or JSON output is
  requested.

## Target Output Shape

The desired default CLI shape is:

```text
nirudha [san]
=============
Resolved: nirūḍha

Analysis
- form: nirūḍha
  possible reading: past participle/adjective; source: Heritage

Meanings
1. grown up, mature; conventionally accepted
   sources: CDSL/AP90, DICO translation
   notes: grammatical/rhetorical sense also attested
2. drawn out, removed, purged
   sources: CDSL/MW, DICO translation
3. unmarried
   sources: CDSL/MW, DICO translation

Source Details
- 5 additional source notes and citations hidden; use --show-source or triples-dump.
```

The exact wording can change, but the structure should not: resolved form,
analysis, ranked learner meanings, provenance, then optional source details.

## Implementation Roadmap

### Phase 1: Encounter Audit Fixtures

**Owner persona:** @auditor for expected-output review, @scribe for fixture
word notes.

Goal: establish representative accepted outputs before changing ranking and
display.

Tasks:

- Add fixture cases for `san nirudha`, `san dharma`, `lat lupus`, and
  `grc logos`.
- Capture both current JSON reduction shape and desired learner-facing text
  expectations.
- Mark known-bad current behavior explicitly so improvements are measurable.
- Add a small audit helper or documented command that runs the representative
  encounters with fixed options.

Acceptance:

- Tests or fixtures identify the top learner output expected for each term.
- Current problems are named in fixture comments or docs, not left implicit.
- `just test test_cli_encounter_output` runs the encounter snapshot set.

Validation:

```bash
just test test_cli_encounter_output
just validate-stabilization
```

### Phase 2: Candidate And Form Hygiene

**Owner persona:** @sleuth for root-cause tracing, @coder for scoped fixes.

Goal: stop unrelated candidates from polluting the learner encounter.

Tasks:

- Separate "selected learner target" from all normalized candidates.
- For Latin, keep alternate analyzer candidates inspectable but do not show
  unrelated forms like `id#noun` or `ago#verb` as the resolved forms for
  `lupus`.
- For Sanskrit, show Heritage numbered variants as display alternatives without
  letting suffixes or dictionary anchors confuse lexeme display.
- For Greek, show the user surface and selected headword without flooding the
  header with backend internals.

Acceptance:

- `encounter lat lupus` header shows `lupus`, not unrelated candidate forms.
- `encounter san nirudha` resolves to `nirūḍha` and keeps source keys secondary.
- JSON still exposes all candidate/evidence data needed for debugging.

Validation:

```bash
just test test_normalization_pipeline test_cli_encounter_output
just validate-stabilization
```

### Phase 3: Source-Aware Gloss Structuring

**Owner persona:** @architect for data shape, @coder for implementation, @auditor
for source-fidelity review.

Goal: turn source blobs into displayable learner sense units without losing
source content.

Tasks:

- Add a display-layer structure for each WSU:
  - `learner_gloss`
  - `source_gloss`
  - `grammar_label`
  - `citation_notes`
  - `cross_refs`
  - `source_refs`
  - `display_warnings`
- For CDSL, split confidently recognized headword/grammar/citation material
  away from learner gloss text while preserving raw segments.
- Fix Sanskrit display conversion bugs that affect abbreviations and source
  labels, especially cases like `BhP.`.
- For Diogenes/LSJ, identify the concise English sense head before examples and
  citations where a reliable rule exists.
- For Whitaker, separate dictionary sense evidence from unrelated morphology or
  analyzer expansions.

Acceptance:

- `nirudha` no longer displays `nir—UQa` or `ni-°rUQa` as the learner gloss head
  when a cleaner IAST/source-backed form exists.
- `dharma` retains source content but leads with meanings like law, duty,
  practice, merit/religion where supported.
- `logos` buckets show concise sense heads before long LSJ examples.
- Raw source text remains available in `triples-dump --output json`.

Validation:

```bash
just test test_cdsl_triples test_wsu_extraction test_cli_encounter_output
just validate-stabilization
```

### Phase 4: Translation Cache As Default Enrichment

**Owner persona:** @architect for policy, @coder for CLI behavior, @auditor for
provenance.

Goal: make existing cached DICO/Gaffiot translations help learners without
creating hidden network dependency.

Tasks:

- Use resolved translation cache rows by default when the cache DB exists.
- Keep live translation explicit, e.g. a separate cache-population command or
  `--translate-missing`, not default encounter behavior.
- Prefer translated English witnesses over untranslated French witnesses in
  learner display.
- Always show that translated text is derived from DICO/Gaffiot source evidence.
- Add cache-miss diagnostics only in debug/JSON output.

Acceptance:

- `encounter lat lupus` uses a cached Gaffiot translation if the exact cache key
  exists.
- `encounter san dharma` uses a cached DICO translation if the exact cache key
  exists.
- Source French evidence remains inspectable and is not replaced.
- No network call happens during default encounter.

Validation:

```bash
just test test_translation_projection test_cli_encounter_output
just validate-stabilization
```

### Phase 5: Learner Ranking Policy

**Owner persona:** @architect for ranking design, @auditor for edge cases,
@coder for implementation.

Goal: rank meanings by learner usefulness while staying deterministic and
source-auditable.

Initial ranking factors:

- translated English derived witnesses before untranslated French source
  witnesses
- exact selected lemma/headword matches before loose related entries
- concise definition segments before cross-reference-only or citation-only
  segments
- multi-source agreement before single-source evidence
- morphology-compatible senses before unrelated analyzer candidates
- deterministic source order as final fallback

Tasks:

- Implement a scored sort key with named components and JSON/debug visibility.
- Add accepted-output tests for `nirudha`, `dharma`, `lupus`, and `logos`.
- Document why each ranking factor exists and what it must not hide.

Acceptance:

- `nirudha` top meanings are readable learner senses, not obscure logic/source
  notation first.
- `lupus` top meaning is wolf/wolf-related, not unrelated calendar or pronoun
  evidence.
- `logos` top meanings are concise major senses such as account, word/speech,
  reason, story/report, with long LSJ detail behind source details.
- Single-witness status remains visible.

Validation:

```bash
just test test_cli_encounter_output test_reducer
just validate-stabilization
```

### Phase 6: Progressive Disclosure CLI

**Owner persona:** @scribe for command documentation, @coder for CLI flags.

Goal: make the default output learner-facing and move source-heavy material to
explicit inspection modes.

Tasks:

- Add or refine flags:
  - `--show-source`
  - `--show-candidates`
  - `--debug`
  - `--output json`
- Move cache-retry and cache-miss diagnostics out of default text output.
- Keep source refs visible by default, but place long source entries behind
  `--show-source`.
- Update `docs/OUTPUT_GUIDE.md` with before/after examples.

Acceptance:

- Default encounter is readable for a student.
- Developer diagnostics are still available without scraping logs.
- JSON output contains enough data to audit ranking and provenance.

Validation:

```bash
just test test_cli_encounter_output
just validate-stabilization
```

## Cross-Language Acceptance Matrix

| Term | Current Issue | Target Behavior | Gate |
| --- | --- | --- | --- |
| `san nirudha` | bad ranking; source notation leak; debug warning | top senses are readable and source-backed; raw CDSL/DICO inspectable | snapshot + triples JSON check |
| `san dharma` | too many flat CDSL entries; source details dominate | top senses summarize law/duty/practice/etc. with evidence refs | snapshot + CDSL segment tests |
| `lat lupus` | unrelated candidates outrank wolf | wolf/wolf-related meaning first; candidate noise hidden by default | snapshot + candidate hygiene test |
| `grc logos` | huge LSJ list without summary | concise major senses first; examples/citations behind source detail | snapshot + Diogenes sense-head test |

## Validation Loop

Every phase must follow the same loop:

1. Add or update an accepted-output fixture first.
2. Implement the smallest source/display change needed.
3. Verify focused tests.
4. Verify the full stabilization gate.
5. Update docs only after behavior and tests agree.

Baseline command:

```bash
just validate-stabilization
```

## Deferred

- Embedding or LLM semantic similarity.
- Passage-level interpretation.
- UI/API work that bypasses the CLI contract.
- Live translation during default encounter.
- Broad source-data deletion or "noise removal" that drops evidence instead of
  transforming, labeling, or explaining it.

