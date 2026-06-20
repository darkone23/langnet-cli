# Learner Encounter Roadmap

**Status:** completed 2026-06-19  
**Date:** 2026-04-28  
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
just cli encounter san nirudha --max-buckets 8
just cli encounter san dharma --max-buckets 8
just cli encounter lat lupus --max-buckets 8
just cli encounter grc logos --max-buckets 8
```

### Sanskrit

What works:

- Heritage morphology reaches the encounter output.
- CDSL and DICO claims are available for Sanskrit meaning evidence.
- CDSL entries carry `display_iast`, `display_slp1`, source refs, source
  entries, source chunks, and notes where recognized.
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
- `--translation-mode auto` can explicitly populate missing Gaffiot translation
  rows and then display the projected English evidence.

Current learner failures:

- `lupus` shows unrelated normalized candidates in `Forms`, such as `id#noun`,
  `age#interjection`, and `ago#verb`.
- The first displayed meaning can be unrelated to the user word, such as
  calendar or demonstrative entries from noisy analyzer candidates.
- Diogenes dictionary sections are long source excerpts rather than concise
  learner senses.
- Gaffiot translations are used when the caller requests `--translation-mode
  cache` or `--translation-mode auto`; default lookup remains network-free and
  source-first.
- Reader-form routing has improved for `virumque`: the content word `vir` now
  leads while `-que` remains visible as tackon evidence. Latin contextual
  homographs such as `cano` still need better learner-first ranking.

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

### Phase 1: Encounter Audit Fixtures - Completed 2026-06-18

**Owner persona:** @auditor for expected-output review, @scribe for fixture
word notes.

Representative accepted-output fixtures now cover `san nirudha`, `san dharma`,
`lat lupus`, and `grc logos` through `tests/test_cli_encounter_output.py`.
Related reader-eval fixtures also cover the broader classic and corpus-expansion
forms used by learner-quality checks.

Verified:

```bash
just test test_cli_encounter_output test_reader_eval test_reader_eval_fixtures test_reader_eval_corpus_fixtures
```

### Phase 2: Candidate And Form Hygiene - Completed 2026-06-18

**Owner persona:** @sleuth for root-cause tracing, @coder for scoped fixes.

Candidate and form hygiene now has accepted-output coverage for Latin `lupus`,
Latin enclitic `virumque`, Sanskrit `nirudha`/`nirūḍha`, Sanskrit morphology
fallbacks, and Greek surface/headword display. Debugging data remains available
through JSON, while default text output keeps backend keys secondary.

Verified:

```bash
just test test_normalization_pipeline test_cli_encounter_output test_encounter_ranking test_planner_core
```

### Phase 3: Source-Aware Gloss Structuring - Completed 2026-06-19

**Owner persona:** @architect for data shape, @coder for implementation, @auditor
for source-fidelity review.

Goal: turn source blobs into displayable learner sense units without losing
source content.

Status: completed for the current learner-encounter closeout. CDSL source-note chunks and generic typed source-detail
metadata are surfaced as compact `source notes` in `encounter`.
`--no-source-details` hides that summary for a quieter first screen. Header rows
analysis rows, Foster labels, and meaning rows are now assembled as
`EncounterHeaderView`, `EncounterAnalysisView`, and `EncounterMeaningView`
display objects before CLI rendering. Diogenes definition triples now carry
learner-gloss/learner-segment metadata.
Preferred-lemma ranking helpers, source-order ranking, learner-quality ordering,
and final bucket sort-key assembly now live in `encounter_ranking`.

2026-06-18 slice update: Diogenes/LSJ-style entry analysis now derives concise
learner sense heads before examples and citation abbreviations. The source
analysis test for `λόγος` verifies that the learner gloss keeps `the word`,
`account, tale, story`, and `reason, argument` while stripping the Greek
headword preamble, Roman sense markers, and short trailing citation labels such
as `Hom.`.

2026-06-18 CDSL source-label update: `BhP.` is now preserved as a source
abbreviation and classified as a source-reference segment instead of being
converted as ordinary SLP1 text. The CDSL source-note test keeps `BhP.` grouped
with `MBh.` and related abbreviation notes while leaving adjacent meaning
segments unclassified.

2026-06-19 Whitaker source-structure update: Whitaker sense gloss triples now
carry `display_gloss`, `learner_gloss`, `source_segments`, and `source_entry`
metadata, while morphology triples remain separate interpretation evidence.
This gives `encounter` and JSON display payloads the same source/reader layer
shape used by other dictionary handlers without changing Whitaker parsing.

Accepted evidence:

- Display-layer structure now exists for current WSU display needs:
  - `learner_gloss`
  - `source_layer_text` / evidence glosses
  - morphology analysis labels and Foster display labels
  - compact citation, cross-reference, source-reference, and example summaries
  - display warnings through reduction warnings and request diagnostics
- CDSL splits confidently recognized source notes while preserving raw source
  chunks and source keys.
- Sanskrit abbreviation/source-label coverage includes the current real-row
  `BhP.` case without corrupting display text.
- Diogenes/LSJ concise sense-head extraction is covered by source-analysis tests
  and Greek encounter snapshots.
- For Whitaker, separate dictionary sense evidence from unrelated morphology or
  analyzer expansions. Completed for sense-gloss source/display metadata; keep
  extending only if real Whitaker rows expose additional structure worth
  preserving.

Acceptance:

- `nirudha` no longer displays `nir—UQa` or `ni-°rUQa` as the learner gloss head
  when a cleaner IAST/source-backed form exists.
- `dharma` retains source content but leads with meanings like law, duty,
  practice, merit/religion where supported.
- `logos` buckets show concise sense heads before long LSJ examples.
- Raw source text remains available in `triples-dump --output json`.

Validation:

```bash
just test test_whitakers_triples test_cli_encounter_output test_encounter_ranking test_source_text_analysis
```

### Phase 4: Learner Ranking Policy - Completed 2026-06-19

**Owner persona:** @architect for ranking design, @auditor for edge cases,
@coder for implementation.

Goal: rank meanings by learner usefulness while staying deterministic and
source-auditable.

Initial ranking factors:

- translated English derived witnesses before untranslated French source
  witnesses
- exact selected lemma/headword matches before loose related entries
- concise definition chunks before cross-reference-only or citation-only chunks
- multi-source agreement before single-source evidence
- morphology-compatible senses before unrelated analyzer candidates
- deterministic source order as final fallback

2026-06-19 slice update: bucket ranking explanations are available in JSON and
pretty-output debug mode. `encounter --show-ranking` now prints a compact
`Ranking` section with preferred-lemma rank, effective rank, learner-quality
order, source order, source tools, and explanation reasons without changing the
default learner screen.

Accepted evidence:

- `nirudha` has a snapshot proving the stale-normalization retry reaches
  `nirūḍha` display and a readable first meaning.
- `dharma` has CDSL snapshots proving `law, duty` display while retaining raw
  evidence and source notes.
- `lupus` has Latin snapshots and translation-cache coverage proving wolf/loup
  evidence appears before unrelated candidate noise, with source language and
  provenance visible.
- `λόγος` has a Greek learner-output snapshot proving concise word/speech,
  account, and reason senses before long source detail.
- Single-witness confidence remains visible in the accepted-output strings.
- `docs/OUTPUT_GUIDE.md` documents JSON ranking explanations and the
  pretty-output `--show-ranking` audit view.

Validation:

```bash
just test test_cli_encounter_output test_encounter_ranking
```

### Phase 5: Progressive Disclosure CLI - Completed 2026-06-19

**Owner persona:** @scribe for command documentation, @coder for CLI flags.

Goal: make the default output learner-facing and move source-heavy material to
explicit inspection modes.

2026-06-18 slice update: `encounter --show-candidates` now exposes normalized
lexeme candidates in pretty output under a compact `Candidates` section while
leaving default learner output quiet. JSON request metadata records
`show_candidates`, and `docs/OUTPUT_GUIDE.md` documents the flag.

2026-06-19 slice update: `encounter --show-ranking` exposes ranking factors in
pretty output for audits while default pretty output remains learner-facing.
JSON request metadata records `show_ranking`, and `docs/OUTPUT_GUIDE.md`
documents the flag.

2026-06-19 source-disclosure update: `encounter --show-source` exposes
source-layer text and source-entry identity for visible buckets in pretty
output. Default pretty output still hides long source entries; JSON request
metadata records `show_source`, and `docs/OUTPUT_GUIDE.md` documents the flag.

2026-06-19 debug-disclosure update: `encounter --debug` now enables candidate,
source, and ranking diagnostic sections together for terminal audits. Default
pretty output remains learner-facing; JSON request metadata records `debug`,
and `docs/OUTPUT_GUIDE.md` documents the flag.

Accepted evidence:

- Flags:
  - `--source-details/--no-source-details`
  - `--show-candidates` (completed for pretty candidate disclosure)
  - `--show-ranking` (completed for pretty ranking disclosure)
  - `--show-source` (completed for pretty source disclosure)
  - `--debug` (completed as diagnostic shorthand)
  - `--output json`
- Move cache-retry and cache-miss diagnostics out of default text output. Current
  default output only shows learner-relevant retry warnings; cache hit/miss
  counts live in JSON `translation_cache` and explicit cache commands.
- Keep source refs visible by default, summarize typed source details behind
  `--source-details`, and place long source entries behind `--show-source`.
- Update `docs/OUTPUT_GUIDE.md` with before/after examples. Completed for
  candidate, ranking, source, and debug disclosure flags.

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
