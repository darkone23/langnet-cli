# Working Baseline And Roadmap

**Date:** 2026-04-28  
**Mode:** stabilization before expansion

This document is the current checkpoint for continuing LangNet development. It
summarizes what exists, compares that feature set to the product vision, and
names the concrete next steps.

## Vision Check

LangNet exists to help a reader move from a word in a classical text to an
accountable explanation of:

1. possible headwords,
2. grammatical form,
3. source-backed meanings,
4. provenance for each claim,
5. source agreement, disagreement, or incompleteness.

The implementation now matches the evidence side of that vision. The remaining
gap is learner quality: the first screen must become more reliably useful for a
reader who asks, "what does this word mean here?"

## Current Feature Set

### Runtime

- CLI-first product surface.
- Commands: `lookup`, `parse`, `normalize`, `plan`, `plan-exec`,
  `triples-dump`, `encounter`, `reader-eval`, `databuild`, and `index`.
- Deterministic planning over normalized queries.
- Staged execution: fetch -> extract -> derive -> claim.
- DuckDB-backed caches and indexes for normalization, staged effects, claims,
  plans, and translation rows.
- Handler versioning for cache invalidation.

### Evidence Sources

- Latin: Whitaker's Words, Diogenes/Lewis & Short, CLTK, local Gaffiot.
- Greek: Diogenes/LSJ, with CLTK/spaCy support where configured.
- Sanskrit: Heritage morphology/analysis, CDSL, local DICO.

External services and local data remain environment-dependent. Unit tests should
continue to use fixtures rather than live services.

### Reduction And Display

- Claim triples are the cross-backend integration boundary.
- Witness Sense Units are extracted from `has_sense` + `gloss` triples.
- Exact deterministic sense buckets are wired into `langnet-cli encounter`.
- `encounter` displays source-backed meanings, source refs, source language,
  translation provenance, and Sanskrit Heritage analysis rows.
- `triples-dump --output json` and `plan-exec --output json` are the inspection
  surfaces for claims, triples, cache status, skipped calls, and handler stages.

### DICO And Gaffiot Translation

- DICO/Gaffiot French source entries are source evidence.
- Cache-backed English translations are derived evidence, not replacement
  facts.
- `--translation-mode cache` reads exact cache hits.
- `--translation-mode auto` explicitly populates missing DICO/Gaffiot
  translations through OpenRouter, writes cache rows, then projects the cached
  English evidence.
- `--use-translation-cache` remains supported as the older cache-only spelling.
- Translation cache identity includes source lexicon, entry, occurrence,
  headword, source text hash, source/target language, model, prompt hash, and
  hint hash.

Observed quality is strong for source-faithful dictionary translation:

- Gaffiot: `arma`, `cano`, `vir`, `lupus`.
- DICO: `dharma`, `agni`, `yoga`, `karman`.

Observed limitations:

- live cache population can be slow for long entries;
- translations are full dictionary entries, not compact learner glosses;
- headword routing still matters, e.g. `virumque` can route to `virus`, and
  `karma` is less useful than `karman` for the DICO concept entry.

## Current Gaps Against The Vision

### 1. Correct First Hit

The system often has the right evidence, but the first bucket is not always the
right learner answer.

Examples:

- `virumque` should lead with `vir + -que`; it can currently surface `virus`.
- Greek `μῆνιν` should prefer `μῆνις`, not `μήνιον`.
- Greek `θεὰ` should prefer `θεά`, not `θέα`.
- Sanskrit `karma` should route to `karman` when the intended DICO concept
  entry is needed.

### 2. Compact Learner Glosses

DICO/Gaffiot translations are high quality, but they remain full-entry evidence.
The learner display needs a short gloss layer above the full translated source
entry.

Examples:

- `arma`: arms; weapons; war; troops
- `cano`: sing; sing of; celebrate
- `dharma`: law; duty; virtue; proper nature
- `karman`: act; action; rite; duty; accumulated karma

### 3. Source Structuring

CDSL, LSJ, Lewis & Short, DICO, and Gaffiot entries can contain headwords,
grammar, citations, abbreviations, examples, and glosses in one source string.
The system preserves the evidence, but learner display still needs safer typed
segments before broad ranking or semantic merging can be trusted.

### 4. Reader Evaluation

Coverage audits show whether evidence exists. They do not yet measure whether
the first screen answers a reader's question. The project needs reader-oriented
fixtures with tolerant assertions, not brittle full-output snapshots only.

### 5. Passage And Context

Passage-level interpretation remains deferred. It should consume stable
word-level claims, buckets, and compact glosses rather than bypassing them.

## Roadmap From This Baseline

### Phase 1: Documentation And Baseline Hygiene

Goal: keep the current state factual and easy to resume.

Acceptance:

- canonical docs agree about implemented commands and translation modes;
- stale TODOs that describe implemented features are updated or archived;
- `just ruff-check`, focused docs-adjacent tests, and typecheck pass.

### Phase 2: Reader Eval Fixtures And Report

Goal: measure hit quality against real reading use cases without overfitting to
famous lines.

Seed fixture passages:

- Aeneid 1.1-7
- Iliad 1.1-7
- Bhagavad Gita 1.1-2

Seed fixture:

- `tests/fixtures/reader_eval_classics.json`

Report command:

- `langnet-cli reader-eval --fixture tests/fixtures/reader_eval_classics.json`
- default report mode is non-gating; add `--fail-on-miss` when a suite is ready
  to become an acceptance gate.

Current live checkpoint:

- `just cli reader-eval --no-cache --translation-mode cache --output json`
- strict grammar+meaning hit rate: 5/13
- meaning-only hit rate: 13/13
- Sanskrit now passes all five seed tokens after display-form matching,
  no-bucket morphology fallback, and `karma -> karman` enrichment from clear
  Heritage morphology. Latin has good meaning hits but lacks displayed
  morphology; `Troiae` now reaches `troia` through a general Latin `-ae -> -a`
  reader-form candidate. Greek `μῆνιν` and `θεὰ` now land on the intended
  entries for meaning checks. Greek epic proper-name genitives such as
  `Ἀχιλῆος` now reach validated `-εύς` headwords such as `Ἀχιλλεύς` when
  Diogenes confirms the generated headword. Latin and Greek still lack
  displayed morphology rows in the reader-eval fixture.

Cache caveat:

- Latin `-ae -> -a` enrichment is deterministic and can be added to old cached
  normalization rows.
- Greek epic `-ῆος -> -εύς` enrichment is backend-validated, so stale cached
  normalization rows may still miss `Ἀχιλλεύς` until the cache is refreshed or
  the report is run with `--no-cache`. This avoids unvalidated generated Greek
  headwords entering normal cached reads.

Assertions should check:

- expected lemma appears top-1 or top-3;
- expected rough gloss words appear;
- known bad lemmas are not top-ranked;
- morphology or analysis exists where available;
- compounds and enclitics are visibly split.

### Phase 3: Candidate And Headword Hygiene

Goal: make the selected learner target reliable.

Priority fixes:

- Latin enclitic/form routing: `virumque -> vir + -que`.
- Latin finite verb/noun ambiguity where exact form favors the reader sense.
- Latin first-declension/proper-name forms: `Troiae -> Troia` through general
  form candidates, not text-specific exceptions.
- Greek accent-sensitive ranking: `θεὰ -> θεά`, `μῆνιν -> μῆνις`.
- Greek epic proper-name genitives: validated `-ῆος -> -εύς` candidates, as in
  `Ἀχιλῆος -> Ἀχιλλεύς`, only when source lookup and parse evidence confirm the
  generated headword.
- Sanskrit headword aliases and stems: `karma -> karman` where supported by
  source evidence.

Started:

- Gaffiot lookup now receives the full ordered Latin normalization candidate
  list, so a non-selected but relevant lemma such as `vir` can still reach the
  local bilingual dictionary. The remaining `virumque` work is explicit
  enclitic/component display and ranking the reader target above unrelated
  candidates.
- Sanskrit reader forms with Heritage morphology but no surface-form meaning
  buckets now follow the morphology lemma for meaning evidence, as with
  `yuyutsavaḥ -> yuyutsu`.
- Sanskrit surface entries with one clear non-compound morphology lemma can now
  enrich existing weak surface buckets, as with `karma -> karman`.
- Latin cached and fresh normalization now add a general `-ae -> -a`
  reader-form candidate, letting Gaffiot resolve `Troiae -> troia`.
- Greek reranking now prefers lexical sigma candidates over surface accusative
  nu forms and converts final grave surface accents to acute lemma candidates,
  so `μῆνιν` and `θεὰ` score as meaning hits in reader-eval.
- Greek normalization now adds validated epic `-εύς` headword candidates for
  `-ῆος` genitives, so `Ἀχιλῆος` can reach the Achilles entry without a
  word-specific runtime branch.

Sanskrit collection note: collection expansion should use the same discipline:
add reusable alias/stem/compound rules backed by fixtures from the collection,
then let DICO/CDSL/Heritage evidence decide. Avoid word-specific runtime
branches even when tests use named classic examples.

### Phase 4: Compact Gloss Layer

Goal: put a short learner gloss above the full source-backed entry.

Rules:

- compact glosses are display helpers, not replacement source facts;
- they must point back to a source or translated witness;
- full source text remains inspectable through JSON/triples;
- tests should use cache-backed or fixture-backed translated entries, not live
  translation.

### Phase 5: Translation Cache Operations

Goal: make DICO/Gaffiot translation practical at scale without hidden network
calls.

Tasks:

- add batch/cache-warming commands for headword lists and passage word lists;
- add cache hit/miss diagnostics in JSON/debug output;
- add timeout/chunking policy for long entries;
- keep default encounter network-free.

### Phase 6: Source-Aware Ranking

Goal: improve ordering only where fixtures justify the rule.

Allowed ranking inputs:

- translation vs source language;
- DICO/Gaffiot source preference when present;
- witness count;
- exact headword/form match;
- compact gloss quality and length;
- source-specific typed fields.

Do not add embeddings, LLM similarity, or passage-context ranking until this
phase is fixture-stable.

### Phase 7: Hydration

Goal: enrich stable claims and buckets without changing identity.

Examples:

- CTS URN labels;
- dictionary entry URLs;
- author/work display labels.

Hydration must not alter claim IDs, WSU IDs, bucket IDs, or grouping.

### Phase 8: Compounds And Passages

Goal: extend the stable word-level system to multi-token reading.

Dependencies:

- reader eval fixtures are passing;
- compact glosses exist for representative entries;
- candidate/headword hygiene is reliable for common reader forms;
- source provenance remains inspectable.

## Current Recommended Queue

1. Add reader-eval fixtures for the three classic openings.
2. Fix `virumque`, `μῆνιν`, `θεὰ`, and `karma/karman` routing with accepted
   tests.
3. Implement compact gloss derivation/display for translated DICO/Gaffiot
   witnesses.
4. Make cache-backed translations default enrichment when exact rows already
   exist, while keeping live population explicit.
5. Add translation cache warming for a word list.
6. Update source-structuring fixtures for CDSL and long LSJ/Gaffiot entries.
7. Reassess passage-level work only after the above passes.
