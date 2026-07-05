# Roadmap

This is the canonical milestone roadmap. For the current operating queue, read
`docs/EXECUTION_PLAN.md`. For plan lifecycle details, read
`docs/plans/README.md`.

## Current Status

LangNet has a working CLI-first word-level evidence engine:

- normalize -> plan -> fetch -> extract -> derive -> claim;
- claim triples -> Witness Sense Units -> exact buckets -> `encounter`;
- source inspection through `plan-exec` and `triples-dump`;
- Latin, Greek, and Sanskrit backend coverage;
- DICO, Gaffiot, Bailly, and Lewis local data/index surfaces where their local
  databases are built;
- cache-backed English translation projection for French DICO/Gaffiot/Bailly
  evidence when exact cache rows exist or explicit population is requested;
- reader corpus, word index, paradigm, translation-cache, recommendation, and
  evidence-inspection CLI commands;
- SvelteKit webapp adapter routes for search, reader texts, word-index
  browsing, paradigms, MOTD, and translation-cache inspection.

The project remains in stabilization. The next work is learner-quality
refinement, reader provenance quality, source structuring, acquisition QA, and
reader/web contract discipline, not broad semantic inference or opaque generated
answers.

## Milestone 0: Stabilization Baseline

**Goal:** keep the repo factual, validated, and reviewable.

Current state:

- CLI recipes route through the maintained `langnet-cli` surface via `just cli`.
- Focused encounter, translation projection, word-index, and paradigm tests
  cover important behavior without requiring live services.
- `doctor`, `langs`, `tools`, `word-index`, and `translation-cache` provide
  machine-readable readiness, catalog, index, and cache-maintenance surfaces.
- SvelteKit web routes adapt CLI/data contracts rather than defining a separate
  semantic runtime.
- The reader coordination layer lives in `docs/EXECUTION_PLAN.md` (Reader And
  Library section); dated status handoffs live in `docs/archive/`.

Remaining:

- keep `just lint-all` and `just test-fast` passing before larger changes land;
- keep active docs aligned with implemented commands and translation modes;
- keep completed plans and dated handoffs out of `docs/plans/active/`;
- avoid new roadmap/status documents unless an older one is retired or clearly
  linked as historical.

## Milestone 1: Evidence Contracts

**Goal:** every displayed fact can be traced to source evidence.

Implemented:

- staged effects and handler versioning;
- claim/triple projection for core handlers;
- fixture-backed claim contract tests;
- DICO/Gaffiot/Bailly translation records as derived evidence;
- JSON evidence inspection through `plan-exec` and `triples-dump`.

Remaining:

- continue moving ad hoc predicate strings to canonical constants;
- keep reducers consuming triples/evidence, not backend-specific claim payloads;
- add fixtures when handler output semantics change.

## Milestone 2: Reader-Form Reliability

**Goal:** the system picks the right headword/form before ranking meanings.

Reader-form work should remain fixture-backed and reusable. Current accepted
targets include Latin enclitics and first-declension/proper-name forms, Greek
accent and epic-genitive routing, Sanskrit headword aliases such as `karma ->
karman`, and Sanskrit compound morphology with segment-level lemmas.

Remaining:

- keep reader-eval fixtures green as new forms are added;
- replace local fallback rows with source-backed morphology where possible;
- avoid word-specific runtime branches for famous text examples.

## Milestone 3: Learner Encounter Quality

**Goal:** make `encounter` answer the reader before showing full source detail.

Implemented:

- exact buckets;
- translation-first ranking when derived translation evidence is present;
- DICO/Gaffiot source preference when present;
- Sanskrit Heritage analysis rows;
- display-layer header, analysis, meaning, source-detail, Foster-label,
  ranking, and translation-cache helpers;
- compact learner glosses over source-backed or cache-backed entries while
  preserving full evidence below;
- CDSL plain-text entry grammar diagnostics for source references, cross
  references, grammar markers, and first definition text;
- JSON metadata suitable for downstream renderers;
- Foster TOC summary pipeline: 105-entry run with experience rollups,
  `experience:*` refs in essentials, `--retry-only` CLI for invalid-row
  regeneration, and `foster_bridge` field in reader word-context payload.

Remaining:

- broaden compact learner gloss coverage without hiding provenance;
- expand typed source-segment fixtures for long LSJ/Lewis/Gaffiot/DICO/CDSL and
  Bailly entries;
- improve default terminal noise hiding for unrelated candidates;
- keep JSON contract snapshots broad enough for reader and web clients.

## Milestone 4: Reader And Web Adapter

**Goal:** keep web behavior thin, inspectable, and aligned with CLI/data
contracts while making reader provenance visible enough for real use.

Implemented:

- SvelteKit route handlers under `webapp/src/routes/api/`;
- routes for `/api/search`, `/api/reader`, `/api/word-index`,
  `/api/paradigm`, `/api/motd`, and `/api/translation-cache`;
- reader/web contract documentation for current API modes.
- `/library` source-index and acquisition-watchlist browsing over existing
  catalog/source-index data.
- selected-word reader context as a CLI/API/UI payload with deterministic
  lexical evidence, morphology evidence, reader hits, caveats, and route tests.
- checked-in source-index snapshots and reader quality-audit rows for corpus
  expansion.

Remaining:

- keep web routes read-only unless an operation is explicitly cache-maintenance
  scoped;
- treat `encounter --output json`, reader catalog/search outputs, word-index
  JSON, and paradigm JSON as the backend contracts;
- keep live translation population explicit and out of ordinary page loads.
- keep selected-word reader context grounded in deterministic lexical,
  morphology, reader-hit, and caveat fields before any generated sidebar text.
- keep imported works visually and structurally distinct from wanted, staged,
  planned, or deferred acquisition targets.

## Milestone 5: Translation Cache Operations

**Goal:** make French lexicon translation useful at scale without hidden network
dependencies.

Implemented:

- cache-only and explicit population modes;
- exact cache keys and source-text hashes;
- projection of cache hits into derived English witnesses;
- `translation-warm` and `translation-cache` CLI surfaces;
- JSON diagnostics for cache availability, hits, misses, and writes.

Remaining:

- passage-vocabulary cache warming ergonomics;
- timeout/chunking policy for long entries;
- optional pretty/debug cache diagnostics;
- broader Bailly cache fixtures and documentation once the source/index slice
  is stable.

## Milestone 6: Source Structuring And Ranking

**Goal:** refine source blobs into display-safe learner units while preserving
raw text.

Scope:

- CDSL source segments and notes;
- translated DICO/Gaffiot/Bailly parsed glosses;
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

- first-class Python product API beyond the current SvelteKit adapter;
- embeddings or broad semantic similarity;
- opaque generated explanations;
- passage interpretation before word-level hit quality is reliable.
