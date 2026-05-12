# Project Status

**Date:** 2026-05-12
**Overall grade:** B / 85%

## Summary

LangNet has crossed the foundation threshold. The CLI, planner, staged executor, storage indexes, core backend handlers, exact WSU reduction, and first `encounter` output exist. Sanskrit follows a clearer Heritage-first model: Heritage is the preferred morphology/analysis source, while CDSL and DICO supplement meaning/gloss evidence. DICO/Gaffiot now support cache-backed English translation projection, plus explicit cache-miss population through `--translation-mode auto`. DICO/Gaffiot claim triples now carry compact learner-gloss metadata, and `encounter` keeps full dictionary evidence available underneath the short display line. Header, analysis-row, meaning-row, source-detail, Foster-label, ranking, and translation-cache summaries now flow through encounter helper modules instead of CLI-local string scraping. Learner recommendation commands now expose schema-backed `word-of-day` and `recommend-words` output with encounter probe summaries.

The current source-backed V1 paradigm and word-index ordering slices are stable:
`paradigm` and `paradigm-resolve` expose Heritage/Diogenes-backed tables and
resolution metadata, while `word-index` exposes explicit order metadata plus
native section rails. Sanskrit now has a 52-item varnamala section rail with
CDSL SLP1 anchors that preserve phoneme distinctions such as ण/न, श/ष/स, and
क्ष/ज्ञ. Integrated `word-index nearby --source all` neighborhoods now use
language-native lexeme ordering by default while retaining source windows as
provenance.
Latin integrated word-index neighborhoods now include the local Whitaker's
Words dictionary index alongside Gaffiot and Diogenes when
`data/build/lex_whitakers.duckdb` has been built.

The main project risk is no longer "can the system run?" It is "can we put the right evidence first for a reader without hiding or damaging the sources?"

## Health Card

| Area | Grade | Status |
| --- | --- | --- |
| Build and validation | A | Current closure verification passes: focused word-index/paradigm tests, live Sanskrit smoke checks, `just lint-all`, and `just test-fast`; current fast suite is 493 tests. |
| CLI surface | B+ | Commands exist; `encounter` is the current learner-facing path. DICO/Gaffiot translation modes are wired. Compact gloss display and source-detail toggles have started, but the interface is still an MVP. |
| Planner/executor | B+ | Tool plans and staged execution are implemented. |
| Claims/evidence | A- | Core handlers have fixture-backed claim contract coverage; CDSL/DICO/Gaffiot evidence paths are stronger. |
| Semantic reduction | C+ | Exact claim-to-WSU extraction and bucket display exist; headword ranking and compact display are improving, while semantic merging remains deferred. |
| Documentation | B+ | Active docs are classified by purpose; README, getting-started, output guide, roadmap, and status docs are aligned with the current CLI-first surface. |
| Release hygiene | B- | Completed plans are moving out of `active/`; uncommitted stabilization/docs changes should still be checkpointed before larger work. |

## Implemented Runtime

- CLI commands: `lookup`, `parse`, `normalize`, `plan`, `plan-exec`, `triples-dump`, `encounter`, `word-of-day`, `recommend-words`, `reader-eval`, `translation-warm`, `translation-cache`, `word-index`, `entry-analyze`, `doctor`, `langs`, `tools`, `databuild`, and `index`.
- Language coverage:
  - Latin: Whitaker, Diogenes, CLTK, local Gaffiot source entries.
  - Greek: Diogenes, CLTK/spaCy where configured.
  - Sanskrit: Heritage-first morphology/analysis, CDSL dictionary source entries, local DICO source entries from Heritage dictionary links.
- Pipeline: fetch → extract → derive → claim.
- Storage: raw responses, extraction indexes, derivation indexes, claims, provenance, and plan indexes.
- Tests: service-free claim contract fixtures for Whitaker, CDSL, Diogenes, CLTK, Heritage, DICO, and Gaffiot.
- Reduction: service-free WSU extraction, exact gloss buckets, and `encounter` terminal output.
- Inspection: `triples-dump --output json` exposes structured claims/triples without scraping text output; `plan-exec --output json` summarizes cache status, stage counts, skipped calls, handler versions, and claims.
- Learner output tests: snapshot-style coverage exists for representative Sanskrit CDSL, Sanskrit Heritage analysis, Latin Gaffiot, Greek Diogenes, DICO/Gaffiot translated-cache output, stale-normalization recovery, and multi-witness ranking in `encounter`.
- Compact learner display: `encounter` prefers parsed cached glosses,
  source-provided learner glosses, translated segment display text, and then
  conservative source-entry compaction. DICO and Gaffiot now emit
  `learner_gloss` and typed `learner_segments` at claim time. When the compact
  line differs from the full dictionary text, the full evidence remains visible
  below it.
- Source-detail display: typed `source_notes` and `source_segments` are
  summarized as cross-references, source references, and examples through
  `encounter_display.SourceDetailSummary`; header forms/source keys are
  assembled as `EncounterHeaderView`; morphology analysis display is assembled
  as `EncounterAnalysisView`; meaning row metadata is assembled as
  `EncounterMeaningView`; Foster labels are display-layer helpers;
  `--no-source-details` hides source summaries without removing JSON/triples
  evidence.
- Ranking cleanup: preferred-lemma comparison, morphology lemma preference,
  reduction-derived preferred lemmas, source-order ranking, learner-quality
  ordering, and final bucket sort-key assembly now live in `encounter_ranking`,
  with compatibility wrappers left in the CLI.
- Source-headword ranking now considers source entry headword metadata, so exact
  Sanskrit DICO headwords such as `पुराण` can outrank near forms such as
  `पुरण` without regressing morphology-supported cases such as `karma ->
  karman`.
- Long DICO entries now use DICO-aware learner-gloss compaction that preserves
  later useful sense sections before falling back to full source inspection.
  Upstream source text can still end with ellipses, but JSON exposes source
  length and evidence notes so callers can distinguish upstream clipping from
  display summarization.
- JSON contract: `encounter --output json` now includes schema/request metadata,
  display-ready header/analysis/meaning rows, and ranking explanations aligned
  to sorted buckets, giving future web/API renderers structured fields instead
  of requiring pretty-output scraping. Meaning rows now include per-entry
  witness metadata summaries for common source fields, and success/error shapes
  have JSON Schema documents. Runtime failures after command dispatch now return
  structured JSON errors on stdout with a nonzero exit code.
- Translation cache: schema/key helpers, demo cache writes, cache-hit
  projection into derived translation triples, explicit `encounter
  --translation-mode auto` cache-miss population, Gaffiot/DICO golden rows,
  accepted `encounter` output for translated-cache hits, and reusable
  `encounter_translation` orchestration for mode resolution, hit/miss
  diagnostics, and projection/population batches.
- Diagnostic fuzz audit: 50 words per language currently show 100% any-evidence coverage for Latin, Greek, and Sanskrit; Sanskrit Heritage is 50/50 for morphology evidence and 43/50 for gloss evidence.
- Real-input fuzz probes saved under `examples/debug/fuzz_real_inputs_2026_04_28*`
  show 100% tool-level hits for the sampled Latin, Greek, and Sanskrit classic
  reader forms. These are diagnostic evidence, not release gates.
- Sanskrit Heritage morphology now preserves segment-level lemmas in compound
  rows, improving learner display and provenance inspection for Sanskrit
  compounds.
- `word-of-day` and `recommend-words` emit `langnet.word_of_day.v1` JSON,
  enforce an LLM subprocess deadline, and verify recommendations against
  encounter probes when available.
- `word-index` JSON exposes explicit `order` objects for source-local rows,
  collapsed lexeme cards, integrated language-native neighborhoods, grouped
  source windows, and seeded discovery wheels. This keeps durable keys such as
  `lexeme_key`, `wheel_order_key`, `native_order_key`, and `source_order_key`
  from being mistaken for one another.
- `word-index sections` exposes native browsing rails. Sanskrit uses a 52-item
  varnamala rail with learner-facing labels and source-native CDSL SLP1 anchors
  for correct dictionary neighborhoods.
- `word-index browse` exposes a grouped source-native browse mode for UI
  clients. Top-level `items[]` now contains learner-facing homograph cards that
  can group matching rows across dictionaries, while `groups[]` preserves each
  source/dictionary browse window. Use `--homographs raw` to inspect exact
  source rows. `word-index list --source all` remains the collapsed canonical
  lexeme-card view.
- Latin word-index sources include Gaffiot, Whitaker's Words, and Diogenes when
  their local DuckDB indexes exist. The Whitaker index is built from
  `DICTLINE.GEN`, derives learner citation forms from stems and grammatical
  codes for browsing/merging, and keeps the original source stem in metadata.
- `word-index nearby --source all` defaults to
  `policy = "integrated_language_native"` and `order.policy =
  "language-native"`. Sanskrit uses `order.collation = "sa-varga"` so vowels,
  anusvara/visarga, consonants, and supported conjuncts no longer inherit odd
  ASCII/source-window ordering. Sanskrit lexeme grouping now uses lossless
  `lexeme_key` identity so forms such as `gaṃ` and `gam` do not collapse into
  one learner card.
- `paradigm` and `paradigm-resolve` expose source-backed inflectional table
  support. Sanskrit noun declensions and verb conjugations are fetched from
  Heritage; Latin and Greek tables are fetched from Diogenes. Resolution keeps
  native grammar features separate from shared functional relations and avoids
  guessing when required metadata is missing.
- `encounter --output json` now includes lazy follow-up actions for UI clients:
  view an available paradigm, open a word-index neighborhood, or inspect a
  source entry without inlining those secondary payloads into the primary
  encounter response.

## Current Gaps

- `lookup` output is still backend-keyed; `encounter` is better but not yet a release-quality learner interface.
- Sanskrit word-index source rows still preserve each source/index sequence and
  label it as `collation = "source"`; integrated cross-source neighborhoods use
  `native_order_key` for a learner-facing varnamala order.
- Paradigm support is source-backed V1, not a complete local morphology engine.
  Arbitrary reverse analysis, local template generation, Sanskrit compound
  decomposition, cross-language aligned paradigm views, and highlight rendering
  remain future work.
- The Whitaker word index is best-effort citation-form projection over
  dictionary stems. It improves Latin index coverage and cross-dictionary
  grouping, but it does not replace Whitaker runtime parsing or generated-form
  analysis.
- Current `encounter` samples expose concrete learner-experience failures:
  Sanskrit CDSL can still leak source notation, Latin/Gaffiot and Greek/LSJ
  still need broader typed source segmentation, and some long source entries
  require better example/citation handling. Fresh reader-eval with
  `--no-cache --translation-mode off` now reaches 13/13 meaning hits, 13/13
  top-answer hits, and 13/13 strict hits on the seed classic-opening fixture.
  Latin `cano` now leads with the singing/chanting verb, and `virumque` leads
  with `vir` while preserving `-que` tackon evidence below the content word.
- The first corpus-expansion fixture covers Vulgate John 1:1, Greek New
  Testament John 1:1, the Taittiriya Upanishad invocation, and Taittiriya
  Samhita 1.1.1. With the stricter reader-eval split it now shows 15/15 strict,
  15/15 broad meaning, and 15/15 top-answer hits.
- Semantic reduction is exact-match only; no synonym merging, mature sense ranking, or structured learner-display gloss parsing yet.
- Evidence inspection works in text and JSON; `OUTPUT_GUIDE.md` now includes Sanskrit CDSL and DICO/Gaffiot translation-cache walkthroughs.
- Fuzz recipes are diagnostic only; query/compare modes still reflect older API assumptions. The current 50-word audit under `examples/debug/fuzz_audit_2026_04_27/` is useful evidence coverage, not a release gate.
- CLTK may fail cleanly when model data is absent.
- Active planning needs discipline: one canonical roadmap, scoped task files, and completed plans kept out of `docs/plans/active/`.
- External services remain required for live lookup.
- CDSL learner display is improved and fixture-backed, but CDSL entries are still flat strings with source abbreviations and citations mixed into gloss text.

## Immediate Priorities

1. Use `docs/BASELINE_AND_ROADMAP.md` for the current working checkpoint and next concrete steps.
2. Treat `reader-eval` as two tiers: the classic-opening fixture is now a
   stabilization gate, while the corpus-expansion fixture is the next ranking
   backlog.
3. Replace local morphology fallback rows with source-backed morphology where
   possible, and keep expanding strict reader fixtures with real inflected
   Latin and Sanskrit forms.
4. Keep shrinking `cli.py` by moving the remaining encounter command flow into
   dedicated helpers after each slice has fixture coverage.
5. Treat web interface work as a thin renderer over `encounter --output json`
   first; see `docs/plans/todo/infra/web-interface-enablement.md`.
6. Run `just validate-stabilization` for each source/evidence/display slice before taking the next one.

## Decision Log

- CLI is the reliable interface for now.
- HTTP/API work is deferred until runtime semantics stabilize.
- Deterministic reduction comes before embeddings or semantic constants.
- Passage/compound work must reuse word-level claims and buckets, not bypass them.
- Stabilization work has priority over new learner-facing features until the baseline is committed and inspectable.
- Run Just/devenv recipe probes sequentially; parallel recipe audits can produce misleading positional-argument failures.

## Canonical References

- Vision: `docs/VISION.md`
- Baseline and concrete roadmap: `docs/BASELINE_AND_ROADMAP.md`
- Execution plan: `docs/EXECUTION_PLAN.md`
- Roadmap: `docs/ROADMAP.md`
- Active implementation plan: `docs/plans/active/infra/design-to-runtime-roadmap.md`
- Stabilization planning session: `docs/plans/active/infra/stabilization-planning-session.md`
- Learner encounter roadmap: `docs/plans/active/pedagogy/learner-encounter-roadmap.md`
- Real-input fuzzing plan: `docs/plans/active/pedagogy/real-input-fuzzing-roadmap.md`
- Goals: `docs/GOALS.md`
- Pedagogical philosophy: `docs/PEDAGOGICAL_PHILOSOPHY.md`
- Architecture: `docs/technical/ARCHITECTURE.md`
- Technical design vision: `docs/technical/design/TECHNICAL_VISION.md`
- Predicate/evidence contract: `docs/technical/predicates_evidence.md`
- Recipe health: `docs/JUST_RECIPE_HEALTH.md`
- Semantic readiness: `docs/SEMANTIC_READINESS.md`
