# Project Status

**Date:** 2026-04-29  
**Overall grade:** B / 85%

## Summary

LangNet has crossed the foundation threshold. The CLI, planner, staged executor, storage indexes, core backend handlers, exact WSU reduction, and first `encounter` output exist. Sanskrit follows a clearer Heritage-first model: Heritage is the preferred morphology/analysis source, while CDSL and DICO supplement meaning/gloss evidence. DICO/Gaffiot now support cache-backed English translation projection, plus explicit cache-miss population through `--translation-mode auto`. DICO/Gaffiot claim triples now carry compact learner-gloss metadata, and `encounter` keeps full dictionary evidence available underneath the short display line.

The main project risk is no longer "can the system run?" It is "can we put the right evidence first for a reader without hiding or damaging the sources?"

## Health Card

| Area | Grade | Status |
| --- | --- | --- |
| Build and validation | A | `just lint-all` and `just test-fast` pass; current fast suite is over 220 tests. |
| CLI surface | B+ | Commands exist; `encounter` is the current learner-facing path. DICO/Gaffiot translation modes are wired. Compact gloss display has started, but source structuring is still early. |
| Planner/executor | B+ | Tool plans and staged execution are implemented. |
| Claims/evidence | A- | Core handlers have fixture-backed claim contract coverage; CDSL/DICO/Gaffiot evidence paths are stronger. |
| Semantic reduction | C+ | Exact claim-to-WSU extraction and bucket display exist; headword ranking and compact display are improving, while semantic merging remains deferred. |
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
- Compact learner display: `encounter` prefers parsed cached glosses,
  source-provided learner glosses, translated segment display text, and then
  conservative source-entry compaction. DICO and Gaffiot now emit
  `learner_gloss` and typed `learner_segments` at claim time. When the compact
  line differs from the full dictionary text, the full evidence remains visible
  below it.
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
  Sanskrit can still leak CDSL source notation, Latin/Gaffiot can still expose
  long source entries before compact learner prose, and Greek can still expose
  large LSJ sections without a concise learner summary. Fresh reader-eval with
  `--no-cache --translation-mode off` now reaches 13/13 meaning hits and 13/13
  top-answer hits on the seed classic-opening fixture. Latin `cano` now leads
  with the singing/chanting verb, and `virumque` leads with `vir` while
  preserving `-que` tackon evidence below the content word.
- The first corpus-expansion fixture covers Vulgate John 1:1, Greek New
  Testament John 1:1, the Taittiriya Upanishad invocation, and Taittiriya
  Samhita 1.1.1. With the stricter top-answer checks it is no longer a completed
  gate: it still exposes ranking/normalization work such as `principio`,
  `Deum`, `λόγος`, `śam`, `iṣe`, `ūrje`, and `tvā`. This is useful forward
  pressure rather than a regression in evidence coverage; the expected evidence
  still appears, but not always in the first learner-facing bucket.
- Semantic reduction is exact-match only; no synonym merging, mature sense ranking, or structured learner-display gloss parsing yet.
- Evidence inspection works in text and JSON; `OUTPUT_GUIDE.md` now includes Sanskrit CDSL and DICO/Gaffiot translation-cache walkthroughs.
- Fuzz recipes are diagnostic only; query/compare modes still reflect older API assumptions. The current 50-word audit under `examples/debug/fuzz_audit_2026_04_27/` is useful evidence coverage, not a release gate.
- CLTK may fail cleanly when model data is absent.
- Active planning needs discipline: one canonical roadmap, scoped task files, archive old reports.
- External services remain required for live lookup.
- CDSL learner display is improved and fixture-backed, but CDSL entries are still flat strings with source abbreviations and citations mixed into gloss text.

## Immediate Priorities

1. Use `docs/BASELINE_AND_ROADMAP.md` for the current working checkpoint and next concrete steps.
2. Treat `reader-eval` as two tiers: the classic-opening fixture is now a
   stabilization gate, while the corpus-expansion fixture is the next ranking
   backlog.
3. Replace local morphology fallback rows with source-backed morphology where
   possible, and continue improving corpus-expansion top-answer misses such as
   `principio`, `λόγος`, and Vedic dative/pronoun forms.
4. Harden compact learner glosses by adding typed source segments for
   DICO/Gaffiot/CDSL/Diogenes instead of relying on broad source-string
   compaction.
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
