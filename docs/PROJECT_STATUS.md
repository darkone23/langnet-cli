# Project Status

**Date:** 2026-04-28  
**Overall grade:** B / 85%

## Summary

LangNet has crossed the foundation threshold. The CLI, planner, staged executor, storage indexes, core backend handlers, exact WSU reduction, and first `encounter` output exist. Sanskrit follows a clearer Heritage-first model: Heritage is the preferred morphology/analysis source, while CDSL and DICO supplement meaning/gloss evidence. DICO/Gaffiot now support cache-backed English translation projection, plus explicit cache-miss population through `--translation-mode auto`.

The main project risk is no longer "can the system run?" It is "can we put the right evidence first for a reader without hiding or damaging the sources?"

## Health Card

| Area | Grade | Status |
| --- | --- | --- |
| Build and validation | A | `just lint-all` and `just test-fast` pass; current fast suite is over 220 tests. |
| CLI surface | B+ | Commands exist; `encounter` is the current learner-facing path. DICO/Gaffiot translation modes are wired. Default output is still too source-first for learners. |
| Planner/executor | B+ | Tool plans and staged execution are implemented. |
| Claims/evidence | A- | Core handlers have fixture-backed claim contract coverage; CDSL/DICO/Gaffiot evidence paths are stronger. |
| Semantic reduction | C+ | Exact claim-to-WSU extraction and bucket display exist; semantic merging, headword ranking, and compact learner display are still early. |
| Documentation | B+ | Active docs are classified by purpose; archive retained for old reports/plans. |
| Release hygiene | C+ | Many changes are still uncommitted and should be checkpointed. |

## Implemented Runtime

- CLI commands: `lookup`, `parse`, `normalize`, `plan`, `plan-exec`, `triples-dump`, `encounter`, `databuild`, `index`.
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
- Translation cache: schema/key helpers, demo cache writes, cache-hit projection into derived translation triples, explicit `encounter --translation-mode auto` cache-miss population, Gaffiot/DICO golden rows, and accepted `encounter` output for translated-cache hits.
- Diagnostic fuzz audit: 50 words per language currently show 100% any-evidence coverage for Latin, Greek, and Sanskrit; Sanskrit Heritage is 50/50 for morphology evidence and 43/50 for gloss evidence.
- Real-input fuzz probes saved under `examples/debug/fuzz_real_inputs_2026_04_28*`
  show 100% tool-level hits for the sampled Latin, Greek, and Sanskrit classic
  reader forms. These are diagnostic evidence, not release gates.
- Sanskrit Heritage morphology now preserves segment-level lemmas in compound
  rows, improving learner display and provenance inspection for Sanskrit
  compounds.

## Current Gaps

- `lookup` output is still backend-keyed; `encounter` is better but not yet a release-quality learner interface.
- Current `encounter` samples expose concrete learner-experience failures:
  Sanskrit can still leak CDSL source notation; Latin can show unrelated
  normalized candidates (`virumque` -> `virus`); Greek can still expose large
  LSJ sections without a concise learner summary. Fresh reader-eval now reaches
  13/13 meaning hits and 13/13 strict hits on the seed classic-opening fixture.
  The last two strict misses were morphology-only gaps for Latin `Troiae` and
  Greek `Ἀχιλῆος`; encounter now covers them with conservative local fallback
  morphology rows when the lexical reduction has already resolved the lemma.
- The first corpus-expansion fixture covers Vulgate John 1:1, Greek New
  Testament John 1:1, the Taittiriya Upanishad invocation, and Taittiriya
  Samhita 1.1.1. It currently passes 14/14 strict and 14/14 meaning checks with
  `--translation-mode off`, exercising raw Gaffiot/DICO/CDSL/Diogenes evidence.
  The latest learner-display pass uses ordered morphology lemmas to rank
  meanings, improving cases such as `principio -> principium` while preserving
  competing analyses for inspection.
- Semantic reduction is exact-match only; no synonym merging, mature sense ranking, or structured learner-display gloss parsing yet.
- Evidence inspection works in text and JSON; `OUTPUT_GUIDE.md` now includes Sanskrit CDSL and DICO/Gaffiot translation-cache walkthroughs.
- Fuzz recipes are diagnostic only; query/compare modes still reflect older API assumptions. The current 50-word audit under `examples/debug/fuzz_audit_2026_04_27/` is useful evidence coverage, not a release gate.
- CLTK may fail cleanly when model data is absent.
- Active planning needs discipline: one canonical roadmap, scoped task files, archive old reports.
- External services remain required for live lookup.
- CDSL learner display is improved and fixture-backed, but CDSL entries are still flat strings with source abbreviations and citations mixed into gloss text.

## Immediate Priorities

1. Use `docs/BASELINE_AND_ROADMAP.md` for the current working checkpoint and next concrete steps.
2. Use `reader-eval` to measure the seed classic-opening fixture and capture
   hit-rate changes as fixes land.
3. Replace local morphology fallback rows with source-backed morphology where
   possible, and improve `virumque` component display/ranking.
4. Add a compact learner-gloss layer over full translated DICO/Gaffiot evidence.
5. Run `just validate-stabilization` for each source/evidence/display slice before taking the next one.

## Decision Log

- CLI is the reliable interface for now.
- HTTP/API work is deferred until runtime semantics stabilize.
- Deterministic reduction comes before embeddings or semantic constants.
- Passage/compound work must reuse word-level claims and buckets, not bypass them.
- Stabilization work has priority over new learner-facing features until the baseline is committed and inspectable.

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
