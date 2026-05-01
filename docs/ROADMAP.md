# Roadmap

This is the canonical milestone roadmap. For the current baseline and concrete
next steps, read `docs/BASELINE_AND_ROADMAP.md`. For day-to-day task selection,
read `docs/EXECUTION_PLAN.md`.

## Current Status

LangNet has a working CLI-first word-level evidence engine:

- normalize -> plan -> fetch -> extract -> derive -> claim;
- claim triples -> Witness Sense Units -> exact buckets -> `encounter`;
- source inspection through `plan-exec` and `triples-dump`;
- Latin, Greek, and Sanskrit backend coverage;
- DICO/Gaffiot source evidence plus cache-backed English translation evidence.

The project remains in stabilization. The next work is learner-quality
refinement, not broad product expansion.

## Milestone 0: Stabilization Baseline

**Goal:** keep the repo factual, validated, and reviewable.

Current state:

- `just ruff-check` and `just typecheck` pass.
- Focused `encounter` and translation projection tests pass.
- CLI recipes route through the maintained `langnet-cli` surface.
- Stale root quick-start content has been replaced with current pointers.

Remaining:

- keep `just lint-all` and `just test-fast` passing before larger changes land;
- keep active docs aligned with implemented commands and translation modes;
- avoid new roadmap documents unless an older one is retired or linked clearly.

## Milestone 1: Evidence Contracts

**Goal:** every displayed fact can be traced to source evidence.

Implemented:

- staged effects and handler versioning;
- claim/triple projection for core handlers;
- fixture-backed claim contract tests;
- DICO/Gaffiot translation records as derived evidence.

Remaining:

- continue moving ad hoc predicate strings to canonical constants;
- keep reducers consuming triples/evidence, not backend-specific claim payloads;
- add fixtures when handler output semantics change.

## Milestone 2: Evidence Inspection

**Goal:** a developer can answer "where did this meaning come from?" without
scraping pretty output.

Implemented:

- `plan-exec --output json`;
- `triples-dump --output json`;
- predicate/subject/max-count filters for evidence inspection;
- DICO/Gaffiot source and translation provenance in `encounter`.

Remaining:

- add narrative examples for a Latin Gaffiot translation and Sanskrit DICO
  translation;
- expose translation cache hit/miss diagnostics in JSON/debug output.

## Milestone 3: Reader-Form Reliability

**Goal:** the system picks the right headword/form before ranking meanings.

Priority accepted-output targets:

- `virumque -> vir + -que`, not `virus`, now leads with `vir` while preserving
  tackon evidence below the content word;
- `μῆνιν -> μῆνις`, not `μήνιον`, now works for meaning and morphology checks and should stay covered;
- `θεὰ -> θεά`, not `θέα`, now works for meaning checks and should stay covered;
- `Troiae -> Troia` now works for meaning checks through a general Latin
  `-ae -> -a` reader-form candidate, with a conservative local `-ae`
  morphology fallback when source parsers have no row;
- `Ἀχιλῆος -> Ἀχιλλεύς` now works through validated Greek epic `-ῆος -> -εύς`
  candidate generation. Stale cache rows for this pattern are detected and
  recomputed instead of silently preserving the older `Ἀχίλλειος` route;
- `karma -> karman` is now handled when clear Heritage morphology supports the
  concept headword, and should stay covered by reader-eval.
- Sanskrit compound morphology now preserves segment-level lemmas in Heritage
  rows, so compounds such as `dharmakṣetre` can display `dharma -> dharma` and
  `kṣetra -> kṣetra`.
- Latin morphology display now reads Whitaker interpretation triples; Greek
  `ἄειδε`, `θεὰ`, and `μῆνιν` show Diogenes form-feature rows.
- local morphology fallbacks now cover the previous strict seed misses for
  Latin `Troiae` and Greek `Ἀχιλῆος`; source-backed morphology remains the
  higher-fidelity target.

This milestone should use `reader-eval` fixtures and reports, not hardcoded
exceptions for famous texts.

Current gate:

- `tests/fixtures/reader_eval_classics.json` is the stabilization fixture and
  should remain 13/13 on strict/top-answer checks.
- `tests/fixtures/reader_eval_corpus_expansion.json` is the forward-ranking
  fixture. It intentionally exposes remaining top-answer misses in Vulgate,
  Greek NT, and Vedic material.

## Milestone 4: Learner Encounter Quality

**Goal:** make `encounter` answer the reader before showing full source detail.

Implemented:

- exact buckets;
- translation-first ranking;
- DICO/Gaffiot source preference when present;
- Sanskrit Heritage analysis rows.
- reader-eval reports separate overall, meaning, and top-answer hit rates.

Remaining:

- fix corpus-expansion top-answer misses (`principio`, `Deum`, `λόγος`, `śam`,
  `iṣe`, `ūrje`, `tvā`);
- compact learner gloss layer above full source entries;
- source-aware display controls for long LSJ/Lewis/Gaffiot/DICO/CDSL entries;
- better hiding of unrelated candidate noise in default terminal output.

## Milestone 5: Translation Cache Operations

**Goal:** make DICO/Gaffiot translation useful at scale without hidden network
dependencies.

Implemented:

- `--translation-mode cache`;
- `--translation-mode auto`;
- exact cache keys;
- cache-backed projection into derived English witnesses.
- default `encounter` cache-hit enrichment when the cache DB exists, without
  live translation.
- `translation-warm` for explicit word-list cache warming.
- JSON translation cache diagnostics for `encounter --output json`.

Remaining:

- passage-vocabulary cache warming ergonomics;
- timeout/chunking policy for long entries;
- optional pretty/debug cache diagnostics;

## Milestone 6: Source Structuring And Ranking

**Goal:** refine source blobs into display-safe learner units while preserving
raw text.

Started:

- CDSL source-note segments can appear as compact `source notes` below source
  refs in `encounter`, while raw CDSL gloss text remains visible as evidence.
- Diogenes definition triples now carry learner gloss and learner segment
  metadata for LSJ/Lewis-style dictionary entries.

Scope:

- CDSL source segments and notes;
- translated DICO/Gaffiot parsed glosses;
- long Diogenes/LSJ and Lewis & Short sections;
- ranking rules backed by accepted-output tests.

Do not add embeddings or LLM semantic merging in this milestone.

## Milestone 7: Hydration

**Goal:** add labels and links without changing claim, WSU, or bucket identity.

Examples:

- CTS URN labels;
- dictionary entry URLs;
- author/work display labels.

Hydration must be optional and rebuildable.

## Milestone 8: Compounds And Passages

**Goal:** extend stable word-level evidence into multi-token reading workflows.

Dependencies:

- reader-form reliability;
- compact learner glosses;
- fixture-backed encounter output;
- stable provenance inspection.

Passage-level interpretation should consume word-level claims and buckets. It
should not bypass the evidence graph.

## Deprioritized Until The Above Is Stable

- first-class ASGI/API product contract;
- embeddings or broad semantic similarity;
- opaque generated explanations;
- UI-heavy formatting;
- passage interpretation before word-level hit quality is reliable.
