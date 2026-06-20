# Real-Input Fuzzing Roadmap

**Status:** COMPLETED 2026-06-19  
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
- top-answer hit rate: 13/13
- Sanskrit seed tokens: 5/5 strict, 5/5 meaning

Corpus expansion checkpoint:

- `just cli reader-eval --fixture tests/fixtures/reader_eval_corpus_expansion.json --db-path examples/debug/corpus-probes/corpus-reader-eval-4.duckdb --translation-mode off --output json`
- strict hit rate: 15/15
- meaning hit rate: 15/15
- top-answer hit rate: 15/15
- coverage: Jerome/Vulgate John 1:1, Greek New Testament John 1:1,
  Taittiriya Upanishad invocation, and Taittiriya Samhita 1.1.1.

Latest live corpus smoke check, 2026-06-19:

- `just cli reader-eval --fixture tests/fixtures/reader_eval_corpus_expansion.json --db-path examples/debug/corpus-probes/corpus-reader-eval-4.duckdb --translation-mode off --output json`
- strict hit rate: 22/22
- meaning hit rate: 22/22
- top-answer hit rate: 22/22
- Closeout fixes restored the expanded live corpus checkpoint after resolving
  Latin finite-verb/noun ranking, Sanskrit morphology fallback selection,
  reader-eval normalization/component parity, CDSL bare-reference ranking, and
  off-mode source-language fixture terms.

The fuzz probes show strong tool-level evidence availability:

- Latin Diogenes classic forms: 8/8 tool hits.
- Greek Diogenes classic forms: 7/7 tool hits.
- Sanskrit Heritage reader forms: 8/8 tool hits.
- Sanskrit CDSL headword lookups: 8/8 tool hits.

These numbers are diagnostic. They show that source evidence exists, not that
the default learner display is already good.

## Recent Baseline Context

The current fuzz loop already has source-backed fixes for Greek surface-form
morphology, Sanskrit compound-display protection, preferred-lemma ranking,
compact learner glosses, and generic source segmentation. The active queue below
keeps only the remaining work needed to expand and harden that loop.

## Active Work Queue

### 1. Sanskrit Compound And Collection Expansion - Completed 2026-06-18

This slice is no longer active. The corpus-expansion fixture now includes
`agnim`, `jñānam`, `dharmasya`, `ātman`, `yogena`, and two transparent compound
probes, `agnikṣetre` and `jñānayogena`. Taittiriya fixture coverage remains in
the same corpus-expansion file. Component expectations are explicit for the
compound probes so component evidence remains visible without being treated as
the whole-token meaning.

No-network source evidence was also expanded:

- DICO translation-cache golden rows now cover `agni`, `yoga`, `ātman`, and
  `jñāna`.
- DICO and CDSL source-entry fuzz rows now cover the same seed terms.

Verified:

```bash
just test test_reader_eval_corpus_fixtures test_translation_projection test_source_text_analysis
```

### 2. Greek Epic-Genitive Check - Completed 2026-06-18

The `Ἀχιλῆος` strict-miss slice is no longer active. The form is covered in the
classic reader-eval fixture with tolerant expected lemmas, Greek normalization
tests, and encounter-output tests. Runtime logic remains general: accepted
behavior comes through anchor normalization and fixture-backed ranking, not a
word-specific display branch.

Verified:

```bash
just test test_normalizer_cache test_normalization_pipeline test_reader_eval test_reader_eval_fixtures test_cli_encounter_output
```

Live `reader-eval --output json` was attempted during this closeout pass but
was stopped after producing no output for about two minutes; keep using focused
tests for this slice unless the live lookup path is the explicit target.

### 3. Latin Enclitic And Candidate Hygiene - Completed 2026-06-18

The `virumque` display/ranking slice is no longer active. The classic
reader-eval fixture covers the reader form, encounter-output tests cover the
base/tackon component relationship, and ranking tests keep tackon candidates
below the content word without hiding inspectable evidence.

Verified:

```bash
just test test_cli_encounter_output test_encounter_ranking test_reader_eval test_reader_eval_fixtures test_planner_core
```

### 4. Fuzz Harness Alignment - Completed 2026-06-19

This slice is no longer active. Learner-quality checks are covered by the
`reader-eval` fixtures, while `.justscripts/fuzz_tool_outputs.py` remains a
backend parser diagnostic harness.

Accepted evidence:

- `tests/fixtures/reader_eval_classics.json` covers Latin, Greek, and Sanskrit
  classic reader inputs with expected lemmas, gloss terms, morphology flags,
  known-bad checks, and component expectations.
- `tests/fixtures/reader_eval_corpus_expansion.json` extends the loop with
  Vulgate, Greek New Testament, Taittiriya, Sanskrit seed, and compound probes.
- `reader-eval` is the encounter-oriented helper for learner reduction
  summaries; the older fuzz harness is intentionally limited to maintained
  parser CLI checks.
- Query and compare fuzz modes are explicitly documented as legacy diagnostic
  placeholders until a maintained unified query CLI exists again.

Verified:

```bash
just test test_reader_eval test_reader_eval_fixtures test_reader_eval_corpus_fixtures
just autobot fuzz list
```

### 5. Compact Gloss Source Structuring - Completed 2026-06-19

Goal: move from conservative display compaction to typed learner chunks while
preserving source accountability.

Progress:

- DICO, Gaffiot, CDSL, Diogenes, Whitaker's Words, CLTK/Lewis, Bailly, Strong's,
  and encounter-display paths now have focused tests for display gloss/source
  segment metadata.
- `entry-analyze` now uses CDSL learner-gloss/source-segment helpers for long
  CDSL entries instead of treating the full raw source as the learner gloss.
- `entry-analyze` now exposes Diogenes sense-head segments with citation/source
  references while preserving the raw segment text.
- Compact display remains the fallback for unstructured entries.

Focused verification:

```bash
just test test_source_text_analysis test_cdsl_triples test_claim_contracts test_cli_encounter_output
bash ./.justscripts/run-dev-tool ruff check src/langnet/execution/source_text.py src/langnet/execution/handlers/cdsl.py tests/test_source_text_analysis.py
```

Live corpus validation is green again through the closeout in section 6.

### 6. Live Corpus Regression Closeout - Completed 2026-06-19

This slice is no longer active. The corpus-expansion live reader-eval checkpoint
has been restored after recent fixture expansion.

Closed failures:

- `principio`: expected noun `principium`; live top candidate is verb
  `principio`. Fixed by demoting exact finite verb morphology when an oblique
  nominal analysis exists for the same surface.
- `agnim`: morphology sees `agni`, but live meaning buckets are empty.
  Fixed by preferring compact inflectional base fallback terms over longer
  generated Heritage forms.
- `dharmasya`: lemma ranking reaches `dharma`, but top gloss is long French DICO
  source text while the fixture expected only English learner terms. Fixed by
  accepting source-language terms for the `--translation-mode off` fixture.
- `yogena`: live top candidate is the adverb `yogena`, not instrumental `yoga`.
  Fixed by allowing singleton non-component morphology fallback solutions even
  when Heritage also reports component splits, and by demoting CDSL bare `See
  pp.` reference buckets below definition buckets.
- `agnikṣetre`: morphology exposes `agni` + `kṣetra`, but component evidence is
  not surfaced as the fixture expects. Fixed by giving `reader-eval` the same
  normalization-fallback and component-payload parity as `encounter`.

Verified:

```bash
just test test_reader_eval_corpus_fixtures test_reader_eval test_encounter_ranking test_cli_encounter_output
just cli reader-eval --fixture tests/fixtures/reader_eval_corpus_expansion.json --db-path examples/debug/corpus-probes/corpus-reader-eval-4.duckdb --translation-mode off --output json
```

### 7. Dictionary Entry Grammar Fuzzing - Completed 2026-06-19

Goal: treat dictionary-entry parsing as a grammar-and-classification program,
not as a pile of one-off string rules.

Current status:

- `entry-analyze` now exposes a diagnostic entry-analysis surface for raw
  dictionary entries.
- DICO, Gaffiot, and CDSL have initial Lark entry-shell grammars.
- Diogenes/Lewis entry analysis reuses the existing `diogenes_entry.lark`
  parser.
- `tests/fixtures/source_entry_analysis_fuzz.json` is a deterministic corpus
  covering DICO, Gaffiot, Diogenes/Lewis, and common CDSL Sanskrit entries.
- CDSL entry analysis now exposes `lark:cdsl_entry` parse status, grammar
  markers, definition text, cross references, and source references while
  preserving raw source text.

Dictionary tracks:

- **DICO / Sanskrit-French:** parse headword, bracketed form, grammar markers,
  first definition, continuations, cross-references, and bracketed source
  references. Keep French prose classification separate from the entry shell.
- **Gaffiot / Latin-French:** parse morphology preamble, numbered senses,
  example tails, author citations, and parallel example separators. Expect high
  ambiguity and use Earley where needed.
- **Diogenes / Lewis & Short / LSJ:** reuse and extend existing Lark grammar;
  fuzz Latin and Greek entries separately because citation and morphology
  conventions differ.
- **CDSL / Sanskrit dictionaries:** use the dedicated shell grammar for
  source-note suffixes and grammar prefixes while continuing to preserve the
  existing XML/HTML source structure. Longer historical-entry refinements should
  extend the grammar only with deterministic fixture rows.
- **Whitaker's Words:** keep current line reducers as the source of truth for
  now; consider grammar-backed analysis only after the dictionary/facts/senses
  reducers have fixture fuzz coverage.
- **Heritage DICO links:** parse linked DICO dictionary entries through the DICO
  track. Keep Heritage morphology and dictionary-entry parsing as separate
  evidence classes.

Fuzzing policy:

- Prefer deterministic corpus fuzzing first: real entry strings, source labels,
  and minimum invariants such as "must parse", "must preserve raw text", "must
  extract this source reference", or "must not treat this source note as a
  learner gloss".
- Add live/backend fuzzing only as diagnostic output under `examples/debug/`.
  Live variation should not gate the test suite.
- Every corpus case should preserve raw evidence even when grammar parsing
  fails.
- New grammars must expose parse status and parser name in diagnostic output so
  failures are measurable.

Validation:

```bash
just test test_source_text_analysis test_diogenes_parser test_french_parser test_cdsl_triples
just cli entry-analyze --source-tool gaffiot --output json \
  "'ĭī, n. (princeps), 1 commencement : principio Cic. Off. 1, 11'"
just cli entry-analyze --source-tool cdsl --output json \
  "1. mokza m. moksha, liberation; release from worldly existence; cf. MBh. ; PadmaP. ; RV."
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
