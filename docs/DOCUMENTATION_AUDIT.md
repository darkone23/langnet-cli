# Documentation Audit

**Date:** 2026-05-21

This ledger tracks the documentation overhaul. It distinguishes current docs
from retained history so useful information is preserved without leaving stale
material in the maintained reading path.

## 2026-06-17 Follow-Up

The root docs and public copy have been tightened around the current product
state: CLI JSON is the reliable contract, the webapp is a SvelteKit adapter, and
the main forward work is reader quality, learner encounter quality, source
structuring, acquisition QA, translation-cache discipline, and public route
boundaries. Selected-word context is now treated as a completed shared
CLI/API/UI payload that still needs normal regression coverage as surrounding
reader work changes.

Plan hygiene was refreshed:

- dated reader status and close-out records were moved to
  `docs/archive/2026-06-reader-expansion/`;
- `local-lexicon-witness-handoff.md` was moved out of `docs/plans/active/`;
- `docs/plans/README.md` now distinguishes active drivers from supporting
  active implementation plans;
- `docs/EXECUTION_PLAN.md` now carries the compact "what is good / what is
  risky / what comes next" overview.

The active plan tree is still larger than the original 3-5 target because the
reader/library/source-acquisition stack now has several scoped implementation
plans. The coordination rule is: use `docs/EXECUTION_PLAN.md` to choose work.

## Targets

- Current maintained reading path: about 30-40 Markdown files, excluding
  archive and upstream reference files.
- Active plans: about 3-5 genuinely active plans.
- Historical docs: retained under `docs/archive/` or `docs/plans/completed/`
  with clear labels.

## Baseline Counts

Measured after adding the overhaul design and implementation plan.

| Area | Baseline | Target |
| --- | ---: | --- |
| `docs/**/*.md` | 141 | Current path clarified; archive/reference excluded |
| `webapp/**/*.md` | 113 | 4 current webapp docs plus generated/history excluded from the current path |
| Current non-archive/non-upstream docs | 99 | 30-40 |
| `docs/plans/active/**/*.md` | 25 | 3-5 |
| `docs/plans/todo/**/*.md` | 10 | Scoped future plans only |

## Canonical Reading Path

| Path | Role | Action |
| --- | --- | --- |
| `README.md` | Root overview | Update |
| `docs/README.md` | Documentation map | Update |
| `docs/GETTING_STARTED.md` | Operator quick start | Keep/update |
| `docs/OUTPUT_GUIDE.md` | CLI/JSON guide | Keep/update |
| `docs/DEVELOPER.md` | Development workflow | Keep/update |
| `docs/ROADMAP.md` | Canonical milestone roadmap | Keep/update |
| `docs/EXECUTION_PLAN.md` | Compact active queue | Keep/update |
| `docs/technical/ARCHITECTURE.md` | Runtime architecture | Keep/update |
| `webapp/README.md` | Webapp operation | Keep/update |

## Action Ledger

### Canonical And Status Docs

| Path | Role | Action | Successor / Notes |
| --- | --- | --- | --- |
| `README.md` | Root overview | Update | Add Bailly/Lewis/current SvelteKit adapter pointers; shorten doc list. |
| `GETTING_STARTED.md` | Root quick start | Keep/update | Keep as terse pointer; avoid overlapping roadmap/status links. |
| `AGENTS.md` | Agent instructions | Update urgently | Remove stale Starlette ASGI, `/api/q`, `LanguageEngine`, `query`, `cache-clear`, and broken OpenCode link. |
| `docs/README.md` | Docs map | Update | Make it the map, not another status page; point planning to `docs/plans/README.md`. |
| `docs/VISION.md` | Product vision | Keep/update | Acknowledge implemented SvelteKit adapter and reader/word-index surfaces. |
| `docs/GOALS.md` | Product goals | Keep/update | Update “future tools” wording for Bailly/Lewis and clarify API status. |
| `docs/ROADMAP.md` | Canonical roadmap | Keep/update | Merge durable status facts; clarify SvelteKit adapter exists while Python ASGI product API is deferred. |
| `docs/EXECUTION_PLAN.md` | Active queue | Keep/update | Keep compact; distinguish deferred product API from existing web adapter. |
| `docs/PROJECT_STATUS.md` | Dated status | Merge/archive | Successors: `docs/ROADMAP.md`, `docs/EXECUTION_PLAN.md`. |
| `docs/BASELINE_AND_ROADMAP.md` | Baseline/status | Merge/archive | Successors: `docs/ROADMAP.md`, `docs/EXECUTION_PLAN.md`. |
| `docs/REFINEMENT_AUDIT.md` | Dated audit | Archive | Extract remaining gaps into `docs/EXECUTION_PLAN.md` or `docs/SEMANTIC_READINESS.md`. |
| `docs/SEMANTIC_READINESS.md` | Readiness gates | Keep/update | Add Bailly translation/cache scope and tighten stale gaps. |
| `docs/TRANSLATION_CACHE_PLAN.md` | Translation cache plan | Merge/update | Convert to current operation/reference or merge into `docs/OUTPUT_GUIDE.md`; include Bailly. |
| `docs/JUST_RECIPE_HEALTH.md` | Dated recipe audit | Archive | Successor: `docs/DEVELOPER.md` and `just --list`. |

Canonical/status slice completed:

| Path | Final action | Notes |
| --- | --- | --- |
| `README.md` | Updated | Primary reading path shortened; current Bailly/Lewis and SvelteKit adapter surfaces named. |
| `GETTING_STARTED.md` | Updated | Removed redundant status-doc steering and kept setup path concise. |
| `AGENTS.md` | Updated | Stale ASGI `/api/q`, `LanguageEngine`, `query`, `cache-clear`, and broken OpenCode link removed. |
| `docs/README.md` | Updated | Converted into the current documentation map. |
| `docs/DEVELOPER.md` | Updated | Documentation workflow now points to `ROADMAP`, `EXECUTION_PLAN`, and this audit ledger instead of archived `PROJECT_STATUS`. |
| `docs/VISION.md` | Updated | Added SvelteKit adapter and local lexicon/translation-cache framing. |
| `docs/GOALS.md` | Updated | Clarified current local dictionary/API surface. |
| `docs/ROADMAP.md` | Updated | Durable status merged; web adapter moved from future work to current adapter milestone. |
| `docs/EXECUTION_PLAN.md` | Updated | Active queue now covers reader/web readiness and Bailly translation-cache scope. |
| `docs/SEMANTIC_READINESS.md` | Updated | Bailly translation-cache scope added. |
| `docs/archive/2026-05-doc-overhaul/status/PROJECT_STATUS.md` | Archived | Successor: `docs/ROADMAP.md` and `docs/EXECUTION_PLAN.md`. |
| `docs/archive/2026-05-doc-overhaul/status/BASELINE_AND_ROADMAP.md` | Archived | Successor: `docs/ROADMAP.md` and `docs/EXECUTION_PLAN.md`. |
| `docs/archive/2026-05-doc-overhaul/status/REFINEMENT_AUDIT.md` | Archived | Successor: `docs/EXECUTION_PLAN.md` and `docs/SEMANTIC_READINESS.md`. |
| `docs/archive/2026-05-doc-overhaul/status/JUST_RECIPE_HEALTH.md` | Archived | Successor: `docs/DEVELOPER.md` and `just --list`. |

### Reader, Web, And Data Docs

| Path | Role | Action | Successor / Notes |
| --- | --- | --- | --- |
| `docs/READER_CLI_BEGINNER_GUIDE.md` | Reader operator guide | Keep/update | Use current catalog path and command forms; link to build/search docs. |
| `docs/READER_CLI_HANDOFF.md` | Dated handoff | Merge/archive | Successors: beginner guide, corpus status, data build. |
| `docs/READER_CORPUS_STATUS.md` | Reader status | Keep/update | Refresh catalog/discovery/search surfaces and avoid stale debug paths. |
| `docs/READER_DATA_BUILD.md` | Reader build guide | Keep/update | Add post-build validation and current catalog/search-index checks. |
| `docs/READER_WEB_CONTRACT.md` | Reader/web contract | Keep/update | Add current `/api/reader` modes and `/api/translation-cache` contract. |
| `webapp/README.md` | Webapp guide | Keep/update | Add current recipes, host, reader modes, route state, and root contract link. |
| `webapp/docs/BACKEND.md` | Web backend notes | Keep/update | Add translation-cache route, reader mode map, and MessagePack note. |
| `webapp/docs/OPERATIONS.md` | Web operations | Keep/update | Add reader search/discovery and translation-cache probes. |
| `webapp/docs/REGRESSION_CASES.md` | Web regressions | Keep/update | Use `just` recipes and add Reader Desk search/discovery cases. |
| `webapp/docs/UI.md` | Web UI notes | Keep/update | Add Bailly translation capability and current Reader Desk views. |
| `data/README.md` | Data map | Keep/update | Replace stale `just databuild`; link canonical reader build guide. |
| `data/curated/reader_attributions/README.md` | Attribution data note | Keep/update | Add sync/query commands and relation vocabulary. |

Reader/web/data slice completed:

| Path | Final action | Notes |
| --- | --- | --- |
| `docs/READER_CLI_BEGINNER_GUIDE.md` | Updated | Default catalog path, current reader commands, discovery/search, and debug-path labeling refreshed. |
| `docs/READER_CORPUS_STATUS.md` | Updated | Current unified catalog, discovery surfaces, and reader search-index status clarified. |
| `docs/READER_DATA_BUILD.md` | Updated | Current `cli-databuild reader` options, curated defaults, and search-index validation clarified. |
| `docs/READER_WEB_CONTRACT.md` | Updated | Current `/api/reader` modes, `fuzzy` search mode, and `/api/translation-cache` contract added. |
| `docs/archive/2026-05-doc-overhaul/reader/READER_CLI_HANDOFF.md` | Archived | Successors: reader beginner guide, corpus status, and data build guide. |
| `webapp/README.md` | Updated | Current recipes, endpoints, reader modes, and route state documented. |
| `webapp/docs/BACKEND.md` | Updated | Current SvelteKit endpoints, reader mode map, MessagePack behavior, and translation-cache route documented. |
| `webapp/docs/OPERATIONS.md` | Updated | Current recipe set and reader/search/translation-cache probes documented. |
| `webapp/docs/REGRESSION_CASES.md` | Updated | `just verify` and Reader Desk discovery/text-search cases added. |
| `webapp/docs/UI.md` | Updated | Bailly translation layer and current Reader Desk discovery/search state documented. |
| `data/README.md` | Updated | Current reader data directories and `cli-databuild` examples documented. |
| `data/curated/reader_attributions/README.md` | Updated | Relation vocabulary, evidence expectations, and sync/query commands added. |

### Plan Triage

| Path | Role | Action | Successor / Notes |
| --- | --- | --- | --- |
| `docs/plans/README.md` | Plan map | Update | List only real active plans and scoped todo categories. |
| `docs/plans/active/dico/bailly-provider-integration-plan.md` | Completed implementation | Move to completed | Code/tests exist. |
| `docs/plans/active/dico/bailly-structural-extraction-iteration.md` | Completed implementation | Move to completed | Parser/extract/databuild tests exist. |
| `docs/plans/active/dico/lewis-1890-provider-integration-plan.md` | Completed implementation | Move to completed | Provider/databuild/word-index tests exist. |
| `docs/plans/active/infra/CLI_CONCURRENCY_STABILIZATION.md` | Completed implementation | Move to completed | Busy errors/cache policy/web adapter tests exist. |
| `docs/plans/todo/infra/citation-resolution-plan.md` | Future work | Todo/update | First resolver slice done; staged CTS hydration remains. |
| `docs/plans/active/infra/ctsv2-first1k-implementation.md` | Completed implementation | Move to completed | CTSv2/First1K work exists. |
| `docs/plans/active/infra/ctsv2-reader-addressing.md` | Design/status | Archive/merge | Successor: roadmap/status plus CTS todo. |
| `docs/plans/active/infra/design-to-runtime-roadmap.md` | Broad roadmap | Archive/merge | Successor: `docs/ROADMAP.md`. |
| `docs/archive/2026-06-reader-expansion/local-lexicon-witness-handoff.md` | Handoff/status | Archived | Successor: roadmap/status. |
| `docs/plans/active/infra/reader-attribution-claims-implementation.md` | Completed implementation | Move to completed | Core implementation exists. |
| `docs/plans/active/infra/reader-author-classification.md` | Completed implementation | Move to completed | CLI/tests exist. |
| `docs/plans/active/infra/reader-corpus-index-implementation.md` | Completed implementation | Move to completed | Foundational reader corpus code/tests exist. |
| `docs/plans/active/infra/reader-corpus-metrics-and-work-maps.md` | Completed implementation | Move to completed | Work maps/counts/tests exist. |
| `docs/plans/active/infra/reader-corpus-quality-roadmap.md` | Status/roadmap | Archive/merge | Successor: reader corpus status and execution plan. |
| `docs/plans/active/infra/reader-discovery-taxonomy.md` | Completed implementation | Move to completed | Groups/tags/classifications exist. |
| `docs/plans/active/infra/reader-generated-classification-popularity.md` | Completed implementation | Move to completed | Classification/popularity CLI exists. |
| `docs/plans/active/infra/reader-global-text-search.md` | Completed implementation | Move to completed | Search index and encounter integration exist. |
| `docs/plans/active/infra/reader-library-discovery-work-stack.md` | Completed implementation | Move to completed | Priority stack is checked off. |
| `docs/plans/active/infra/reader-metadata-overlay-plan.md` | Completed implementation | Move to completed | Overlay loader/review/tests exist. |
| `docs/plans/completed/infra/reader-source-backed-enrichment.md` | Completed implementation | Completed | Overlay candidates, DCS chapter candidates, catalog sync, and spot checks closed for the deterministic slice. |
| `docs/plans/active/infra/stabilization-planning-session.md` | Planning session | Archive/merge | Successor: execution plan. |
| `docs/plans/active/pedagogy/foster-display-vocabulary.md` | Completed implementation | Move to completed | Foster labels wired and tested. |
| `docs/plans/completed/pedagogy/learner-encounter-roadmap.md` | Completed roadmap | Completed | Current learner encounter stabilization loop closed. |
| `docs/plans/completed/pedagogy/real-input-fuzzing-roadmap.md` | Completed evaluation loop | Completed | Live corpus checkpoint and entry grammar fuzzing closed. |
| `docs/plans/completed/skt/cdsl-entry-grammar-plan.md` | Completed Sanskrit parser work | Completed | CDSL fuzz rows, body grammar, and learner-display snapshots accepted. |
| `docs/plans/completed/infra/reader-citation-reference-resolution.md` | Completed implementation | Completed | Citation reference model, DCS generation, catalog lookup, builder wiring, and resolve-address payload verified. |
| `docs/plans/todo/dico/DICO_ACTION_PLAN.md` | Future DICO refinement | Update | Remove done items and fix status. |
| `docs/plans/todo/dico/cltk-latin-lexicon-integration.md` | Superseded future idea | Archive | Superseded by Lewis 1890 provider. |
| `docs/plans/todo/infra/fixing-types.md` | Placeholder | Archive | Not actionable while lint/typecheck pass. |
| `docs/plans/todo/infra/web-interface-enablement.md` | Superseded plan | Archive/completed | Webapp exists. |
| `docs/plans/todo/pedagogy/compound-term-lookup.md` | Future pedagogy | Keep/update | Full compound explanation remains future. |
| `docs/plans/todo/pedagogy/contextual-word-meaning-lookup.md` | Future pedagogy | Keep | Still scoped. |
| `docs/plans/todo/pedagogy/inflectional-paradigm-generation.md` | Future paradigm work | Update | V1 done; keep reverse/local/UI/cross-language scope. |
| `docs/plans/todo/pedagogy/word-index-wheel-roadmap.md` | Future word-index UX | Update | V1 done; keep UX/quality work. |
| `docs/plans/todo/semantic-reduction/semantic-reduction-mvp.md` | Future semantic refinement | Update | Split completed exact MVP from similarity refinement. |
| `docs/plans/todo/skt/sanskrit-tokenization-compound-plan.md` | Future Sanskrit compounds | Keep/update | Primitive splitter exists; evidence pipeline remains. |

Plan triage slice completed:

| Path | Final action | Notes |
| --- | --- | --- |
| `docs/plans/README.md` | Updated | Lists four active plans, scoped todo categories, completed-record policy, and archive rule. |
| `docs/plans/completed/infra/reader-source-backed-enrichment.md` | Moved to completed | Deterministic enrichment and catalog sync slice closed; provider-backed rerun split to todo. |
| `docs/plans/completed/infra/reader-citation-reference-resolution.md` | Moved to completed | Multi-segment citation reference lookup and compact Latin alias resolution verified. |
| `docs/plans/completed/pedagogy/learner-encounter-roadmap.md` | Moved to completed | Current learner encounter stabilization loop closed. |
| `docs/plans/completed/pedagogy/real-input-fuzzing-roadmap.md` | Moved to completed | Live/fixture quality loop closed for the current slice. |
| `docs/plans/completed/skt/cdsl-entry-grammar-plan.md` | Moved to completed | CDSL body grammar and learner-display snapshot slice closed. |
| `docs/plans/completed/dico/bailly-provider-integration-plan.md` | Moved to completed | Completed implementation record. |
| `docs/plans/completed/dico/bailly-structural-extraction-iteration.md` | Moved to completed | Completed implementation record. |
| `docs/plans/completed/dico/lewis-1890-provider-integration-plan.md` | Moved to completed | Completed implementation record. |
| `docs/plans/completed/infra/CLI_CONCURRENCY_STABILIZATION.md` | Moved to completed | Completed implementation record. |
| `docs/plans/completed/infra/ctsv2-first1k-implementation.md` | Moved to completed | Completed implementation record. |
| `docs/plans/completed/infra/reader-attribution-claims-implementation.md` | Moved to completed | Completed implementation record. |
| `docs/plans/completed/infra/reader-author-classification.md` | Moved to completed | Completed implementation record. |
| `docs/plans/completed/infra/reader-corpus-index-implementation.md` | Moved to completed | Completed implementation record. |
| `docs/plans/completed/infra/reader-corpus-metrics-and-work-maps.md` | Moved to completed | Completed implementation record. |
| `docs/plans/completed/infra/reader-discovery-taxonomy.md` | Moved to completed | Completed implementation record. |
| `docs/plans/completed/infra/reader-generated-classification-popularity.md` | Moved to completed | Completed implementation record. |
| `docs/plans/completed/infra/reader-global-text-search.md` | Moved to completed | Completed implementation record. |
| `docs/plans/completed/infra/reader-library-discovery-work-stack.md` | Moved to completed | Completed implementation record. |
| `docs/plans/completed/infra/reader-metadata-overlay-plan.md` | Moved to completed | Completed implementation record. |
| `docs/plans/completed/pedagogy/foster-display-vocabulary.md` | Moved to completed | Completed implementation record. |
| `docs/plans/todo/infra/citation-resolution-plan.md` | Moved to todo | Remaining CTS staged hydration/abbreviation work. |
| `docs/archive/2026-05-doc-overhaul/plans/ctsv2-reader-addressing.md` | Archived | Broad design/status note. |
| `docs/archive/2026-05-doc-overhaul/plans/design-to-runtime-roadmap.md` | Archived | Superseded by `docs/ROADMAP.md` and `docs/EXECUTION_PLAN.md`. |
| `docs/archive/2026-05-doc-overhaul/plans/local-lexicon-witness-handoff.md` | Archived | Historical handoff. |
| `docs/archive/2026-05-doc-overhaul/plans/reader-corpus-quality-roadmap.md` | Archived | Superseded by reader status and execution plan. |
| `docs/archive/2026-05-doc-overhaul/plans/stabilization-planning-session.md` | Archived | Historical planning session. |
| `docs/archive/2026-05-doc-overhaul/plans/cltk-latin-lexicon-integration.md` | Archived | Superseded by Lewis 1890 provider work. |
| `docs/archive/2026-05-doc-overhaul/plans/fixing-types.md` | Archived | Placeholder, not actionable. |
| `docs/archive/2026-05-doc-overhaul/plans/web-interface-enablement.md` | Archived | Superseded by current SvelteKit webapp. |
| `docs/plans/todo/dico/DICO_ACTION_PLAN.md` | Updated | Remaining DICO refinement only. |
| `docs/plans/todo/pedagogy/compound-term-lookup.md` | Updated | Future compound explanation retained. |
| `docs/plans/todo/pedagogy/contextual-word-meaning-lookup.md` | Kept | Still scoped future work. |
| `docs/plans/todo/pedagogy/inflectional-paradigm-generation.md` | Updated | V1 separated from remaining reverse/local/UI work. |
| `docs/plans/todo/pedagogy/word-index-wheel-roadmap.md` | Updated | V1 separated from remaining UX/quality work. |
| `docs/plans/todo/semantic-reduction/semantic-reduction-mvp.md` | Updated | Exact MVP separated from similarity refinement. |
| `docs/plans/todo/skt/sanskrit-tokenization-compound-plan.md` | Updated | Evidence-backed compound pipeline remains future. |

### Technical Docs

| Path | Role | Action | Successor / Notes |
| --- | --- | --- | --- |
| `docs/technical/README.md` | Technical map | Update | Add reader, word-index, paradigm, translation-cache, SvelteKit adapter. |
| `docs/technical/ARCHITECTURE.md` | Architecture | Update | Add current CLI commands, backend matrix, and web adapter. |
| `docs/technical/backend/README.md` | Backend map | Update | Add DICO, Gaffiot, Bailly, Lewis 1890, CTS, reader/word-index stores. |
| `docs/technical/backend/engine-README.md` | Old engine note | Keep/update | Point to SvelteKit adapter docs. |
| `docs/technical/backend/tool-capabilities.md` | Tool catalog | Update | Planner/catalog exposes more tools than listed. |
| `docs/technical/backend/abbr-latin.md` | Source/reference | Reference/archive | No current `GrammarAbbreviations` code surface. |
| `docs/technical/backend/cologne-README.md` | CDSL backend | Update | Add MW/AP90 and word-index/databuild roles. |
| `docs/technical/backend/diogenes-README.md` | Diogenes backend | Update | Add index/databuild and paradigm role. |
| `docs/technical/backend/whitakers-words-README.md` | Whitaker backend | Update | Add binary discovery and word-index build. |
| `docs/technical/backend/paradigm-generation-limitations.md` | Paradigm limitations | Keep/update | Add SvelteKit `/api/paradigm` consumer note. |
| `docs/technical/design/README.md` | Design map | Update | Mark implemented vs future surfaces. |
| `docs/technical/design/TECHNICAL_VISION.md` | Technical vision | Update | Clarify SvelteKit adapter vs native backend API. |
| `docs/technical/design/tool-response-pipeline.md` | Pipeline design | Update | Add local JSON/DuckDB sources. |
| `docs/technical/design/query-planning.md` | Planner design | Update | Add local lexicon appenders and concurrency/skips. |
| `docs/technical/design/classifier-and-reducer.md` | Reduction design | Update | Point to current reducer models/tests. |
| `docs/technical/design/witness-contracts.md` | Witness contract | Update | Add current action surfaces. |
| `docs/technical/design/entry-parsing.md` | Entry parsing | Update | Add Bailly/Gaffiot/DICO/Lewis/source-entry analysis. |
| `docs/technical/design/hydration-reduction.md` | Future hydration | Keep/reference | Current successor: citation resolver and CTS plans. |
| `docs/technical/design/semantic-structs.md` | Semantic structs | Update | Dataclasses now exist. |
| `docs/technical/design/tool-fact-architecture.md` | Concept reference | Keep/reference | Still conceptually useful. |
| `docs/technical/design/v2-architecture-overview.md` | Duplicate architecture | Archive/merge | Successor: `docs/technical/ARCHITECTURE.md`. |
| `docs/technical/triples_txt.md` | Historical triples design | Reference/archive | Successors: predicate/evidence, semantic triples, storage schema. |
| `docs/technical/semantic_triples.md` | Triple reference | Update | Add newer predicates/sources. |
| `docs/technical/predicates_evidence.md` | Predicate/evidence reference | Update | Add `has_root`, `has_domain`, `has_register`, current sources. |
| `docs/technical/predicates_evidence.json` | Predicate/evidence data | Update | Keep synced with Markdown. |
| `docs/technical/opencode/MULTI_MODEL_GUIDE.md` | OpenCode guide | Update/merge | Skills filenames are stale; keep as process reference or merge stable parts. |
| `docs/technical/opencode/LLM_PROVIDER_GUIDE.md` | OpenCode provider guide | Update | Fix `detective` vs `sleuth` drift. |
| `docs/handler-development-guide.md` | Handler guide | Update | Versioning guidance overstates current handler coverage. |
| `docs/storage-schema.md` | Storage reference | Update | Add translation cache, reader catalog/search, databuild schemas. |
| `docs/CITATIONS.md` | Citation/source credits | Update | Add Bailly, Gaffiot, Lewis, DICO, CTS/reader corpora, OpenRouter, webapp. |

Technical docs slice completed:

| Path | Final action | Notes |
| --- | --- | --- |
| `docs/technical/README.md` | Updated | Current technical map now points to CLI, reader, word-index, paradigm, translation-cache, and SvelteKit adapter surfaces. |
| `docs/technical/ARCHITECTURE.md` | Updated | Runtime architecture now distinguishes current Typer/Click CLI plus SvelteKit adapter from deferred native Python ASGI product API. |
| `docs/technical/backend/README.md` | Updated | Backend catalog now covers DICO, Gaffiot, Bailly, Lewis 1890, CDSL, Diogenes, reader, word-index, and translation-cache roles. |
| `docs/technical/backend/*.md` | Updated | Backend notes now use current `just cli ...` command forms and identify reference-only historical surfaces. |
| `docs/technical/design/*.md` | Updated | Design docs now mark implemented local data flows separately from future hydration/native API work. |
| `docs/technical/opencode/*.md` | Updated | Persona names aligned with current `architect`, `sleuth`, `artisan`, `coder`, `scribe`, and `auditor` configuration. |
| `docs/technical/predicates_evidence.md` | Updated | Predicate/evidence reference now includes current domain/register/root and source coverage. |
| `docs/technical/predicates_evidence.json` | Updated | JSON data synced with the predicate/evidence Markdown reference. |
| `docs/technical/semantic_triples.md` | Updated | Triple reference now covers newer lexicon and reader predicates. |
| `docs/handler-development-guide.md` | Updated | Handler guidance now describes current registry/query-plan behavior and extension boundaries. |
| `docs/storage-schema.md` | Updated | Storage reference now covers reader catalogs/search, word indexes, translation cache, and pronunciation cache. |
| `docs/CITATIONS.md` | Updated | Citation/source list now includes current dictionary, corpus, web, and AI-provider dependencies. |
| `docs/archive/2026-05-doc-overhaul/technical/v2-architecture-overview.md` | Archived | Successor: `docs/technical/ARCHITECTURE.md`. |
| `docs/archive/2026-05-doc-overhaul/technical/triples_txt.md` | Archived | Successors: predicate/evidence, semantic triples, and storage schema references. |

## Verification Notes

- Audit agent plan triage ran focused tests and reported: `84 tests`, `OK`.
- Technical-slice verification passed:
  - `just cli tools --output json` returned 13 accepted tool filters.
  - `just cli doctor --output json` returned `ok: true` with 15 checks,
    0 failures, and 0 warnings.
  - `just --list`, `just cli --help`, `just cli reader --help`,
    `just cli reader search-index --help`, and
    `just cli-databuild reader --help` all resolved.
  - `just cli translation-cache status --output json` returned a live
    translation-cache summary.
  - `git diff --check` passed.
- Live Diogenes, Heritage, Whitaker, OpenRouter, and full reader data builds are
  not required for this documentation pass.
- Archive and upstream-reference files may retain stale command names if clearly
  labeled historical/reference-only.
- Maintained-doc stale-reference scans found no remaining current guidance for
  old `query`/`cache-clear`, native `/api/q` product API, `LanguageEngine`,
  `just databuild`, `--show-paradigm`, `build-book`, or `authors --lang` /
  `works --lang` command forms. Remaining literal mentions are audit notes or
  ordinary prose such as "reader build".

## Final Measurements

Measured after the documentation overhaul implementation.

| Area | Baseline | Final | Notes |
| --- | ---: | ---: | --- |
| Current non-archive/non-upstream docs | 99 | 85 | Reduced and clarified, but still above the long-term 30-40 target. Remaining reduction candidates are completed records, superpowers implementation records, and generated/history web docs. |
| `docs/plans/active/**/*.md` | 25 | 4 | Active backlog now matches the 3-5 target. |
| `docs/plans/todo/**/*.md` | 10 | 8 | Todo backlog now contains scoped future work only. |
| Current `webapp` docs outside dependencies | Not isolated | 7 | Current webapp docs are `README.md` plus backend, operations, regression, and UI notes; two superpowers plan records remain historical. |
