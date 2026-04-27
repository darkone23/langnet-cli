# Stabilization Planning Session

**Status:** active planning artifact  
**Date:** 2026-04-27  
**Feature Area:** infra / pedagogy / semantic-reduction  

## Purpose

This document is the working planning-session view for LangNet's current phase.
It answers:

- Where are we now?
- What is working?
- What are we trying to reach?
- What gaps block that target?
- What tasks should we do next?
- What should stay deferred?

The current answer is not "the project is done." The better answer is:

> LangNet has a working word-level evidence engine and a first learner-facing
> `encounter` path. The next phase is stabilization: make the path reliable,
> inspectable, fixture-backed, and source-faithful before broad semantic
> inference, compounds, passages, or API/UI expansion.

## Product Target

LangNet should help a reader move from a classical word to an accountable
educational explanation:

1. What form or headword might this be?
2. What morphology or analysis supports that reading?
3. What meanings are supported by dictionaries or analyzers?
4. Which sources support each meaning?
5. Where are sources incomplete, translated, provisional, or disagreeing?

The learner-facing answer should be clear first and auditable second. Raw
backend evidence must remain inspectable through claims, triples, source refs,
and cache provenance.

## Current Runtime State

Working now:

- CLI commands exist for `normalize`, `parse`, `lookup`, `plan`, `plan-exec`,
  `triples-dump`, `encounter`, `databuild`, and `index`.
- The staged pipeline exists: fetch -> extract -> derive -> claim.
- Core handlers emit claim triples for Latin, Greek, and Sanskrit sources.
- Exact Witness Sense Unit extraction and exact bucket reduction are wired into
  `encounter`.
- `encounter` is the current learner-facing CLI path.
- Sanskrit follows the intended Heritage-first model: Heritage supplies
  morphology/analysis; CDSL and DICO supply dictionary meaning evidence.
- DICO and Gaffiot French source entries can project cache-backed English
  translations as derived evidence.
- `triples-dump --output json` and `plan-exec --output json` provide structured
  inspection.
- Accepted-output snapshots cover representative `encounter` behavior,
  translated-cache hits, and multi-witness ranking.
- Validation is healthy: `just lint-all` and `just test-fast` pass.

## What Is Working Well

### Evidence Architecture

The project has a coherent path from backend tools into claims/triples. This is
the right foundation for semantic reduction because reducer code can consume
cross-backend triples instead of backend-specific raw payloads.

### Source Fidelity

Recent work has moved the project toward high-fidelity source handling:

- CDSL preserves raw gloss text and source keys while adding display-safe IAST.
- CDSL exposes `source_entry`, `source_segments`, and conservative
  `source_notes`.
- DICO/Gaffiot preserve French source evidence.
- Cached translations are marked as derived evidence rather than source facts.
- WSU evidence now carries source/display metadata forward.

### Learner Path Exists

`encounter` is no longer just a proposal. It can display reduced meaning
buckets, Sanskrit Heritage analysis rows, source languages, source refs, and
translation provenance.

### Tests And Inspection

Core behavior is increasingly fixture-backed. This is critical because live
Diogenes, Heritage, CLTK, and local dictionary data can vary by environment.

## Main Gaps

### 1. CDSL Entries Are Still Too Flat

CDSL source text can mix headwords, grammar, citations, abbreviations, compounds,
and gloss text in one string. Current segmentation is source-complete and
conservative, but not yet enough to reliably separate learner meaning from source
notes for harder entries.

Risk: Sanskrit learner output can still feel like a dictionary blob.

### 2. Evidence Inspection Needs More Narrative Examples

The tooling exists, but developers still need clear examples showing how a
displayed meaning maps back to `triples-dump --output json`, source refs, and
claim metadata.

Risk: the system is inspectable in principle but not obvious in practice.

### 3. Translation Cache Coverage Is Small

The DICO/Gaffiot cache system is correct in shape, but fixture coverage is still
limited. Network translation remains explicitly opt-in and should stay that way.

Risk: translated learner output exists but is thinly sampled.

### 4. Ranking Policy Is Early

The current ranking policy is intentionally simple:

1. cache-backed English translations first
2. stronger witness count next
3. deterministic gloss ordering as fallback

Risk: the first displayed meaning is not always the pedagogically best meaning,
especially for large or noisy source entries.

### 5. Predicate And Claim Shapes Still Need Cleanup

The reducer correctly consumes triples/evidence rather than backend payloads, but
not all handlers consistently use canonical predicate constants, and claim value
shapes still vary by backend.

Risk: subtle drift across handlers as features grow.

## Active Task Queue

These are the current foundation tasks. They are deliberately stabilization
tasks, not expansion tasks.

| Rank | Task | Outcome | Acceptance |
| --- | --- | --- | --- |
| 1 | CDSL source structure follow-through | CDSL entries expose typed source-note/citation/grammar fields where reliable | raw text preserved; display source-complete; focused CDSL tests pass |
| 2 | Evidence-inspection walkthroughs | Developers can trace a displayed meaning back to triples and source refs | Latin and Sanskrit examples in docs; examples match CLI behavior |
| 3 | Translation cache fixture expansion | More DICO/Gaffiot translated examples without network calls | golden rows project; stale-cache behavior remains tested |
| 4 | Ranking policy hardening | Display order is explicit and regression-tested | encounter snapshots explain translation/witness-count ordering |
| 5 | Predicate/claim cleanup | Lower drift risk across handlers | low-risk predicates moved to constants; claim contract tests pass |

## Test And Validation Loop

Every stabilization slice should close the loop before moving on:

1. Identify the smallest source/evidence behavior being changed.
2. Add or update a fixture-backed test for that behavior.
3. Run the focused tests for the touched path.
4. Run the full stabilization gate.
5. Update the planning/status docs only after validation is green.

Use:

```bash
just validate-stabilization
```

That recipe runs the focused learner/evidence tests first, then `just lint-all`,
then `just test-fast`. If it fails, stop and fix the failing layer before adding
new functionality.

## Concrete Next Work

### Next Slice A: CDSL Fixture Set

Add or extend focused CDSL fixtures for:

- `dharma`: common learner word with source keys and gloss evidence
- `agni`: simpler entry that should remain clean and unclassified where no source
  note exists
- one citation-heavy entry such as `mokṣa`/`mokza`: cross-reference and source
  abbreviation segments should be typed without dropping text

Do not attempt broad CDSL parsing yet. Add typed fields only where the fixture
evidence makes the rule defensible.

### Next Slice B: Evidence Inspection Walkthroughs

Add concise, runnable examples for:

- Latin `lupus`: `encounter` -> `triples-dump --output json` -> source refs
- Sanskrit `dharma`: Heritage analysis plus CDSL/DICO meaning evidence

Each walkthrough should identify:

- bucket/display text
- gloss triple object
- source tool
- source ref
- claim id / claim tool
- translation provenance when present

### Next Slice C: Translation Fixture Coverage

Expand no-network golden rows for:

- Latin Gaffiot: at least one more common noun/adjective/verb entry
- Sanskrit DICO: at least one more common learner word beyond `dharma`

Keep exact cache identity strict: source text hash, model, prompt hash, hint hash,
lexicon, entry, and occurrence must all match.

### Next Slice D: Ranking Policy

Keep ranking simple until harder examples prove the need for more:

1. translated English evidence before untranslated French evidence
2. multi-witness buckets before single-witness buckets
3. deterministic fallback ordering

Any new ranking factor needs an accepted-output test and a short explanation in
the design docs.

### Next Slice E: Predicate Constants

Move predicate string usage to `langnet.execution.predicates` gradually:

- reducer extraction predicates
- handler `has_sense` / `gloss` / `has_feature`
- morphology/citation predicates in handlers already under active tests

Avoid broad mechanical rewrites unless tests cover the touched path.

## Decision Gates

### Before Semantic Reduction Beyond Exact Buckets

Proceed only when:

- CDSL source structure is reliable enough that long source-note strings do not
  dominate learner meaning.
- `encounter` snapshots cover representative Sanskrit, Latin, and Greek cases.
- Every displayed bucket can be traced through `triples-dump --output json`.
- Translation-derived evidence remains clearly distinct from source evidence.

### Before Compound Or Passage Work

Proceed only when:

- word-level claims and buckets are stable
- component lookups reuse the same claim/reduction path
- the first compound fixtures do not bypass evidence contracts

### Before API/UI Product Work

Proceed only when:

- CLI semantics are stable enough to be a product contract
- evidence inspection and learner output have accepted examples
- runtime failures are easy to classify

## Explicit Non-Goals For This Phase

- Embedding-backed semantic similarity.
- LLM-based sense merging.
- Passage interpretation.
- Broad ASGI/API rebuild.
- UI/product polish.
- Implicit network translation during learner lookup.
- Dropping or hiding source data because it is hard to parse.

## Planning Session Questions

Use these questions to drive the next human/agent planning session:

1. Which Sanskrit entries are the best CDSL fixtures for source-structure work?
2. Which Latin and Sanskrit words should become the next translation golden rows?
3. What is the minimum evidence walkthrough that a new contributor can follow in
   five minutes?
4. What ranking behavior do we want to promise now, and what should remain
   explicitly provisional?
5. Which predicate cleanup slice gives the most stability for the least churn?

## Recommended Next Move

Start with **Next Slice A** and **Next Slice B** together:

- Add CDSL fixtures for one simple entry and one citation-heavy entry.
- Update the evidence walkthrough so those same entries can be traced from
  `encounter` to `triples-dump --output json`.

That keeps the work close to the project vision: learner clarity backed by
source-complete, inspectable evidence.
