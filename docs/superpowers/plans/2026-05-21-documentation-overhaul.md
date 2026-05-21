# Documentation Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate LangNet documentation so the current reading path is accurate, much smaller, and action-oriented while preserving historical information in archive/completed records.

**Architecture:** Treat docs as a maintained information system with a small canonical path, scoped operational guides, current technical references, and archived historical material. Work is split by non-overlapping file ownership so subagents can edit safely: canonical docs, reader/web/data docs, plan triage, technical docs, and final verification.

**Tech Stack:** Markdown, Git file moves, repository-local `rg`, `find`, `just` help commands, Click CLI help, SvelteKit route docs, no live external services.

---

## Reduction Targets

- Current maintained reading path: about 30-40 Markdown files across root docs, `docs/`, `webapp/docs/`, and data docs, excluding archive and upstream reference files.
- `docs/plans/active`: reduce to about 3-5 genuinely active plans.
- `docs/plans/todo`: keep only scoped future plans that can be resumed.
- `docs/plans/completed`: retain implementation records that are still useful.
- `docs/archive`: preserve superseded snapshots, broad status docs, old handoffs, and stale design notes.

## Subagent Ownership

- **Worker A, Canonical Docs:** `README.md`, `GETTING_STARTED.md`, `AGENTS.md`, `docs/README.md`, `docs/VISION.md`, `docs/GOALS.md`, `docs/ROADMAP.md`, `docs/EXECUTION_PLAN.md`, and top-level status/audit files that get merged or archived.
- **Worker B, Reader/Web/Data Docs:** `docs/READER_*`, `webapp/README.md`, `webapp/docs/*.md`, `data/README.md`, `data/curated/reader_attributions/README.md`.
- **Worker C, Plan Triage:** all files under `docs/plans/`.
- **Worker D, Technical Docs:** `docs/technical/**`, `docs/handler-development-guide.md`, `docs/storage-schema.md`, `docs/CITATIONS.md`, `docs/schemas/` documentation references.
- **Coordinator:** `docs/DOCUMENTATION_AUDIT.md`, final cross-link/stale-reference checks, conflict resolution, final commit grouping.

Workers are not alone in the codebase. They must not revert edits made by others, and they must adjust their implementation to accommodate changes made by others. Workers must not edit outside their assigned ownership without explicit coordination.

---

### Task 1: Create The Audit Ledger And Count Baseline

**Files:**
- Create: `docs/DOCUMENTATION_AUDIT.md`
- Modify: `docs/superpowers/specs/2026-05-21-documentation-overhaul-design.md`

- [ ] **Step 1: Record baseline counts**

Run:

```bash
find docs -type f -name '*.md' | wc -l
find webapp -type f -name '*.md' | wc -l
find docs/plans/active -type f -name '*.md' | wc -l
find docs/plans/todo -type f -name '*.md' | wc -l
```

Expected current baseline from the planning scan:

```text
docs Markdown files: 140
webapp Markdown files: 113
active plan files: 24
todo plan files: 9
```

- [ ] **Step 2: Create `docs/DOCUMENTATION_AUDIT.md`**

Use this exact structure and populate it from the five completed read-only audit reports:

```markdown
# Documentation Audit

**Date:** 2026-05-21

This ledger tracks the documentation overhaul. It distinguishes current docs
from retained history so useful information is preserved without leaving stale
material in the maintained reading path.

## Targets

- Current maintained reading path: about 30-40 Markdown files, excluding
  archive and upstream reference files.
- Active plans: about 3-5 genuinely active plans.
- Historical docs: retained under `docs/archive/` or `docs/plans/completed/`
  with clear labels.

## Baseline Counts

| Area | Baseline | Target |
| --- | ---: | ---: |
| `docs/**/*.md` | 140 | current path clarified; archive/reference excluded |
| `webapp/**/*.md` | 113 | 4 current webapp docs plus archived/generated docs excluded from the current path |
| `docs/plans/active/**/*.md` | 24 | 3-5 |
| `docs/plans/todo/**/*.md` | 9 | scoped future plans only |

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

| Path | Role | Action | Successor / Notes |
| --- | --- | --- | --- |
```

Then add rows for every file called out in the five audit reports. Use `archive`,
`merge`, `update`, `keep`, `move to completed`, `move to todo`, or
`reference-only` as the action labels.

- [ ] **Step 3: Add numeric reduction target to the design spec**

Ensure `docs/superpowers/specs/2026-05-21-documentation-overhaul-design.md`
contains the target of 30-40 current docs and 3-5 active plans.

- [ ] **Step 4: Verify the ledger exists and is readable**

Run:

```bash
sed -n '1,220p' docs/DOCUMENTATION_AUDIT.md
```

Expected: the file starts with `# Documentation Audit` and includes target counts plus the initial action ledger.

---

### Task 2: Canonical Docs Consolidation

**Files:**
- Modify: `README.md`
- Modify: `GETTING_STARTED.md`
- Modify: `AGENTS.md`
- Modify: `docs/README.md`
- Modify: `docs/VISION.md`
- Modify: `docs/GOALS.md`
- Modify: `docs/ROADMAP.md`
- Modify: `docs/EXECUTION_PLAN.md`
- Modify: `docs/SEMANTIC_READINESS.md`
- Move/archive or merge: `docs/PROJECT_STATUS.md`
- Move/archive or merge: `docs/BASELINE_AND_ROADMAP.md`
- Move/archive: `docs/REFINEMENT_AUDIT.md`
- Move/archive: `docs/JUST_RECIPE_HEALTH.md`
- Update: `docs/DOCUMENTATION_AUDIT.md`

- [ ] **Step 1: Fix high-risk stale AGENTS guidance**

Replace the Starlette ASGI section in `AGENTS.md` with current entry points:

```markdown
### Runtime Entry Points

- CLI entry: `langnet-cli` from `langnet.cli:main`
- Root CLI wrapper: `just cli <command>`
- Data builders: `just cli-databuild <builder> ...`
- Web adapter: SvelteKit routes under `webapp/src/routes/api/`
- Current web routes: `/api/search`, `/api/reader`, `/api/word-index`,
  `/api/paradigm`, `/api/motd`, and `/api/translation-cache`

There is no current Python ASGI `/api/q` product surface in this checkout.
Use CLI JSON as the backend contract and the SvelteKit API routes as the web
adapter.
```

Also replace stale examples:

```bash
just cli lookup lat lupus --output json
just cli encounter san agni all --output json
just cli translation-cache status --output json
```

Retarget the OpenCode provider guide link to:

```markdown
docs/technical/opencode/LLM_PROVIDER_GUIDE.md
```

- [ ] **Step 2: Shrink the root README doc list**

In `README.md`, keep only the primary reading path:

```markdown
- `docs/README.md` - documentation map
- `docs/GETTING_STARTED.md` - setup and first commands
- `docs/OUTPUT_GUIDE.md` - CLI and JSON output guide
- `docs/DEVELOPER.md` - development workflow
- `docs/ROADMAP.md` - milestone roadmap
- `docs/EXECUTION_PLAN.md` - current active queue
- `docs/READER_CLI_BEGINNER_GUIDE.md` - reader corpus operation
- `docs/READER_WEB_CONTRACT.md` - reader/web integration contract
- `webapp/README.md` - SvelteKit webapp operation
- `AGENTS.md` - AI-agent workflow notes
```

Add Bailly/Lewis/current webapp language-surface notes from the audit without turning the README into a full reference.

- [ ] **Step 3: Make `docs/README.md` the map, not another status doc**

Update `docs/README.md` so “Start Here” contains 6-8 links, not every status document. Add sections:

```markdown
## Current Path
## Reader And Web
## Developer References
## Technical References
## Planning
## Archive And Upstream References
```

Point planning readers to `docs/plans/README.md`, not a manually maintained list of many active files.

- [ ] **Step 4: Merge status docs into canonical docs**

Extract durable content from:

- `docs/PROJECT_STATUS.md`
- `docs/BASELINE_AND_ROADMAP.md`
- `docs/REFINEMENT_AUDIT.md`
- `docs/JUST_RECIPE_HEALTH.md`

into:

- `docs/ROADMAP.md` for durable milestone/status facts;
- `docs/EXECUTION_PLAN.md` for current active queue;
- `docs/DEVELOPER.md` for just/validation workflow;
- `docs/SEMANTIC_READINESS.md` for semantic readiness gates.

After merging, move superseded sources to:

```text
docs/archive/2026-05-doc-overhaul/status/
```

Add a one-line archive header at the top of each moved file:

```markdown
> Archived during the 2026-05 documentation overhaul. Retained for historical context; current guidance lives in `docs/ROADMAP.md`, `docs/EXECUTION_PLAN.md`, and `docs/README.md`.
```

- [ ] **Step 5: Update `docs/DOCUMENTATION_AUDIT.md`**

Record the final action for every canonical/status file touched by this task, including archive paths.

- [ ] **Step 6: Run scoped stale checks**

Run:

```bash
rg -n "/api/q|LanguageEngine|Starlette ASGI|cache-clear|docs/reference/opencode|devenv shell langnet-cli -- query" README.md GETTING_STARTED.md AGENTS.md docs/README.md docs/ROADMAP.md docs/EXECUTION_PLAN.md docs/DEVELOPER.md docs/SEMANTIC_READINESS.md
```

Expected: no matches in current docs. Matches inside `docs/archive/` are allowed only if the archive header is present.

---

### Task 3: Reader, Web, And Data Documentation Consolidation

**Files:**
- Modify: `docs/READER_CLI_BEGINNER_GUIDE.md`
- Modify: `docs/READER_CORPUS_STATUS.md`
- Modify: `docs/READER_DATA_BUILD.md`
- Modify: `docs/READER_WEB_CONTRACT.md`
- Move/archive: `docs/READER_CLI_HANDOFF.md`
- Modify: `webapp/README.md`
- Modify: `webapp/docs/BACKEND.md`
- Modify: `webapp/docs/OPERATIONS.md`
- Modify: `webapp/docs/REGRESSION_CASES.md`
- Modify: `webapp/docs/UI.md`
- Modify: `data/README.md`
- Modify: `data/curated/reader_attributions/README.md`
- Update: `docs/DOCUMENTATION_AUDIT.md`

- [ ] **Step 1: Merge `READER_CLI_HANDOFF` and archive it**

Extract any still-current operational notes into:

- `docs/READER_CLI_BEGINNER_GUIDE.md`
- `docs/READER_CORPUS_STATUS.md`
- `docs/READER_DATA_BUILD.md`

Then move:

```bash
mkdir -p docs/archive/2026-05-doc-overhaul/reader
git mv docs/READER_CLI_HANDOFF.md docs/archive/2026-05-doc-overhaul/reader/READER_CLI_HANDOFF.md
```

Add the archive header naming the three successor docs.

- [ ] **Step 2: Update reader docs to current catalog and command surfaces**

Apply these current facts:

- Default reader catalog path: `data/build/reader/catalog.duckdb`
- `default` and `development` may point to the same local path in this checkout.
- Current reader commands include discovery and search surfaces:
  `facets`, `groups`, `tags`, `shelves`, `author-facets`, `search`,
  `search-index`.
- Use `--language`, not old `--lang`.
- Use `reader contents`, `reader show`, and `reader resolve-address` for text access.

Remove debug-only paths such as `examples/debug/reader_full_curated_current` from the normal path unless clearly labeled historical/debug.

- [ ] **Step 3: Update webapp docs**

Update `webapp/README.md` and `webapp/docs/BACKEND.md` to include current endpoints:

```text
/api/search
/api/reader
/api/word-index
/api/paradigm
/api/motd
/api/translation-cache
```

Update recipe lists from `webapp/justfile`, including:

```text
install
dev
dev-open
preview
preview-logs
start
search
search-live
verify
```

Update Reader Desk route/API notes to include text search, shelves, facets,
groups, tags, author facets, and route state such as `view`, `address`,
`text_q`, `search_mode`, `group`, `tag`, `sort`, and `page_cursor`.

- [ ] **Step 4: Update data docs**

Replace stale data build examples:

```bash
just databuild cts ...
just databuild cdsl ...
```

with current examples:

```bash
just cli-databuild cts --help
just cli-databuild cdsl --help
just cli-databuild reader --help
```

Add current reader data directories:

```text
data/build/reader/
data/build/reader/search.lance
data/curated/reader_contained_works/
data/curated/reader_work_maps/
data/curated/reader_attributions/
```

- [ ] **Step 5: Run scoped verification**

Run:

```bash
just cli reader --help
just cli reader search-index --help
just cli-databuild reader --help
cd webapp && just --list
```

Then run:

```bash
rg -n "reader_full_curated_current|reader_attributions_seed_verify|--lang|just databuild|langnet-cli word-of-day" docs/READER_*.md webapp/README.md webapp/docs data/README.md
```

Expected: any remaining matches are explicitly marked as historical/debug examples or replaced.

---

### Task 4: Plan Triage And Active Backlog Reduction

**Files:**
- Modify: `docs/plans/README.md`
- Move/update files under: `docs/plans/active/`
- Move/update files under: `docs/plans/todo/`
- Move/update files under: `docs/plans/completed/`
- Create archive directory: `docs/archive/2026-05-doc-overhaul/plans/`
- Update: `docs/DOCUMENTATION_AUDIT.md`

- [ ] **Step 1: Move completed active plans to completed**

Use `git mv` for these moves:

```text
docs/plans/active/dico/bailly-provider-integration-plan.md -> docs/plans/completed/dico/bailly-provider-integration-plan.md
docs/plans/active/dico/bailly-structural-extraction-iteration.md -> docs/plans/completed/dico/bailly-structural-extraction-iteration.md
docs/plans/active/dico/lewis-1890-provider-integration-plan.md -> docs/plans/completed/dico/lewis-1890-provider-integration-plan.md
docs/plans/active/infra/CLI_CONCURRENCY_STABILIZATION.md -> docs/plans/completed/infra/CLI_CONCURRENCY_STABILIZATION.md
docs/plans/active/infra/ctsv2-first1k-implementation.md -> docs/plans/completed/infra/ctsv2-first1k-implementation.md
docs/plans/active/infra/reader-attribution-claims-implementation.md -> docs/plans/completed/infra/reader-attribution-claims-implementation.md
docs/plans/active/infra/reader-author-classification.md -> docs/plans/completed/infra/reader-author-classification.md
docs/plans/active/infra/reader-corpus-index-implementation.md -> docs/plans/completed/infra/reader-corpus-index-implementation.md
docs/plans/active/infra/reader-corpus-metrics-and-work-maps.md -> docs/plans/completed/infra/reader-corpus-metrics-and-work-maps.md
docs/plans/active/infra/reader-discovery-taxonomy.md -> docs/plans/completed/infra/reader-discovery-taxonomy.md
docs/plans/active/infra/reader-generated-classification-popularity.md -> docs/plans/completed/infra/reader-generated-classification-popularity.md
docs/plans/active/infra/reader-global-text-search.md -> docs/plans/completed/infra/reader-global-text-search.md
docs/plans/active/infra/reader-library-discovery-work-stack.md -> docs/plans/completed/infra/reader-library-discovery-work-stack.md
docs/plans/active/infra/reader-metadata-overlay-plan.md -> docs/plans/completed/infra/reader-metadata-overlay-plan.md
docs/plans/active/pedagogy/foster-display-vocabulary.md -> docs/plans/completed/pedagogy/foster-display-vocabulary.md
```

Add a short completion note at the top of each moved file:

```markdown
> Completed implementation record. Moved out of `active/` during the 2026-05 documentation overhaul after code/tests confirmed the core slice exists.
```

- [ ] **Step 2: Move broad status/handoff active plans to archive or todo**

Use these classifications:

```text
docs/plans/active/infra/citation-resolution-plan.md -> docs/plans/todo/infra/citation-resolution-plan.md
docs/plans/active/infra/ctsv2-reader-addressing.md -> docs/archive/2026-05-doc-overhaul/plans/ctsv2-reader-addressing.md
docs/plans/active/infra/design-to-runtime-roadmap.md -> docs/archive/2026-05-doc-overhaul/plans/design-to-runtime-roadmap.md
docs/plans/active/infra/local-lexicon-witness-handoff.md -> docs/archive/2026-05-doc-overhaul/plans/local-lexicon-witness-handoff.md
docs/plans/active/infra/reader-corpus-quality-roadmap.md -> docs/archive/2026-05-doc-overhaul/plans/reader-corpus-quality-roadmap.md
docs/plans/active/infra/stabilization-planning-session.md -> docs/archive/2026-05-doc-overhaul/plans/stabilization-planning-session.md
```

Add archive headers that point to `docs/ROADMAP.md`, `docs/EXECUTION_PLAN.md`,
and the current active plans.

- [ ] **Step 3: Keep only real active plans**

After moves, `docs/plans/active/` should retain:

```text
docs/plans/active/infra/reader-source-backed-enrichment.md
docs/plans/active/pedagogy/learner-encounter-roadmap.md
docs/plans/active/pedagogy/real-input-fuzzing-roadmap.md
docs/plans/active/skt/cdsl-entry-grammar-plan.md
```

Update those four files to remove completed claims from their active checklist and leave only remaining work.

- [ ] **Step 4: Clean todo plans**

Apply these classifications:

```text
archive: docs/plans/todo/dico/cltk-latin-lexicon-integration.md
archive: docs/plans/todo/infra/fixing-types.md
archive or completed: docs/plans/todo/infra/web-interface-enablement.md
update: docs/plans/todo/dico/DICO_ACTION_PLAN.md
update: docs/plans/todo/pedagogy/compound-term-lookup.md
keep: docs/plans/todo/pedagogy/contextual-word-meaning-lookup.md
update: docs/plans/todo/pedagogy/inflectional-paradigm-generation.md
update: docs/plans/todo/pedagogy/word-index-wheel-roadmap.md
update: docs/plans/todo/semantic-reduction/semantic-reduction-mvp.md
update: docs/plans/todo/skt/sanskrit-tokenization-compound-plan.md
```

When updating todo files, separate completed V1 work from remaining future work.
For paradigm examples, remove unsupported `--source` and `--show-paradigm`.

- [ ] **Step 5: Update `docs/plans/README.md`**

Make it list only:

- the four active plans;
- the remaining scoped todo categories;
- completed records as archive-like history;
- the rule that status docs belong in `docs/ROADMAP.md` or archive, not `active/`.

- [ ] **Step 6: Verify active-plan count and stale plan tokens**

Run:

```bash
find docs/plans/active -type f -name '*.md' | sort
find docs/plans/active -type f -name '*.md' | wc -l
rg -n "codesketch|--show-paradigm|--source heritage|--source diogenes|reader build|build-book|segments|--lang" docs/plans docs/superpowers/specs
```

Expected: active plan count is 4. Any remaining stale-token matches are in archive/completed records with clear historical labels, or are current references to the absence of `codesketch`.

---

### Task 5: Technical Documentation Consolidation

**Files:**
- Modify: `docs/technical/README.md`
- Modify: `docs/technical/ARCHITECTURE.md`
- Modify: `docs/technical/backend/README.md`
- Modify: `docs/technical/backend/engine-README.md`
- Modify: `docs/technical/backend/tool-capabilities.md`
- Modify: `docs/technical/backend/cologne-README.md`
- Modify: `docs/technical/backend/diogenes-README.md`
- Modify: `docs/technical/backend/whitakers-words-README.md`
- Modify: `docs/technical/backend/paradigm-generation-limitations.md`
- Modify: `docs/technical/design/README.md`
- Modify: `docs/technical/design/TECHNICAL_VISION.md`
- Modify: `docs/technical/design/tool-response-pipeline.md`
- Modify: `docs/technical/design/query-planning.md`
- Modify: `docs/technical/design/classifier-and-reducer.md`
- Modify: `docs/technical/design/witness-contracts.md`
- Modify: `docs/technical/design/entry-parsing.md`
- Modify: `docs/technical/design/semantic-structs.md`
- Move/archive or label reference-only: `docs/technical/design/v2-architecture-overview.md`
- Move/archive or label reference-only: `docs/technical/triples_txt.md`
- Modify: `docs/technical/semantic_triples.md`
- Modify: `docs/technical/predicates_evidence.md`
- Modify: `docs/technical/predicates_evidence.json`
- Modify: `docs/technical/opencode/MULTI_MODEL_GUIDE.md`
- Modify: `docs/technical/opencode/LLM_PROVIDER_GUIDE.md`
- Modify: `docs/handler-development-guide.md`
- Modify: `docs/storage-schema.md`
- Modify: `docs/CITATIONS.md`
- Update: `docs/DOCUMENTATION_AUDIT.md`

- [ ] **Step 1: Update architecture surface**

In `docs/technical/ARCHITECTURE.md`, document current surfaces:

```text
CLI: lookup, parse, normalize, plan, plan-exec, triples-dump, encounter,
reader, reader-eval, word-index, word-of-day, recommend-words, paradigm,
paradigm-resolve, translation-warm, translation-cache, doctor, langs, tools,
databuild, index, entry-analyze, Bailly/Lewis inspection commands.

Web adapter: SvelteKit routes in webapp/src/routes/api/* delegate to CLI JSON.

Not current: Python ASGI /api/q product contract.
```

Update backend/source matrices to include Bailly, Lewis 1890, DICO, Gaffiot,
CTS index, reader catalog/search data, and translation cache.

- [ ] **Step 2: Update backend/design docs or mark reference-only**

Apply audit recommendations:

- Update backend README/tool-capabilities for current tool catalog.
- Update Diogenes/Whitaker/CDSL notes with databuild, word-index, and paradigm roles.
- Mark `abbr-latin.md` as source/reference material if not used directly by code.
- Update design docs that say implemented dataclasses/features are only planned.
- Move duplicate `v2-architecture-overview.md` to archive or mark it as superseded by `ARCHITECTURE.md`.
- Move or mark `triples_txt.md` as historical/reference-only, with successors `predicates_evidence.md`, `semantic_triples.md`, and `storage-schema.md`.

- [ ] **Step 3: Update predicate/evidence docs**

Add predicates present in `src/langnet/execution/predicates.py`, including:

```text
has_root
has_domain
has_register
```

Add current source examples:

```text
dico
gaffiot
bailly
lewis_1890
cts_index
```

Ensure `docs/technical/predicates_evidence.json` stays in sync with the Markdown.

- [ ] **Step 4: Update handler/storage/citation docs**

In `docs/handler-development-guide.md`, clarify that not every current handler is versioned yet and add examples for Bailly, DICO, Gaffiot, and Lewis 1890 tests.

In `docs/storage-schema.md`, add separate storage notes for:

```text
translation cache
reader catalog/book stores
reader search index
databuild DuckDB files
```

In `docs/CITATIONS.md`, add current source/dependency families:

```text
Bailly
Gaffiot
Lewis 1890
local DICO
CTS/reader corpora
OpenRouter/aisuite
SvelteKit/Bun webapp
```

- [ ] **Step 5: Run scoped verification**

Run:

```bash
just cli tools --output json
just cli doctor --output json
rg -n "Native web/API entrypoint.*not implemented|planned|V2|one-table DuckDB|GrammarAbbreviations|/api/q|LanguageEngine" docs/technical docs/handler-development-guide.md docs/storage-schema.md docs/CITATIONS.md
```

Expected: matches are either removed, updated, or explicitly labeled historical/reference-only.

---

### Task 6: Final Link, Stale-Token, And Count Verification

**Files:**
- Modify: `docs/DOCUMENTATION_AUDIT.md`
- Modify any current docs needed to fix final broken links or stale current claims.

- [ ] **Step 1: Run global stale-token scan**

Run:

```bash
rg -n "/api/q|LanguageEngine|Starlette ASGI|cache-clear|devenv shell langnet-cli -- query|docs/reference/opencode|just databuild|--show-paradigm|reader build|build-book|authors --lang|works --lang" README.md GETTING_STARTED.md AGENTS.md docs webapp data --glob '*.md'
```

Expected:

- no matches in current non-archive docs;
- any matches in `docs/archive/`, `docs/upstream-docs/`, or `docs/plans/completed/` have a historical/reference label or are explicitly noted in `docs/DOCUMENTATION_AUDIT.md`.

- [ ] **Step 2: Run local Markdown link scan**

Use `rg` to find Markdown links and verify local file targets exist. If using an ad hoc script, put it under `examples/debug/` only if it is saved; otherwise use one-off shell checks.

Minimum manual check:

```bash
rg -n "\\[[^]]+\\]\\(([^)#][^)]+\\.md)(#[^)]+)?\\)" README.md GETTING_STARTED.md AGENTS.md docs webapp data --glob '*.md'
```

Fix broken current-doc links. Archive/upstream broken links can remain only if the audit ledger notes they are historical/vendor text.

- [ ] **Step 3: Verify current command examples**

Run:

```bash
just --list
just cli --help
just cli reader --help
just cli word-index --help
just cli translation-cache --help
just cli paradigm --help
cd webapp && just --list
```

Then scan examples:

```bash
rg -n "just cli|just cli-databuild|just [a-z-]+|langnet-cli" README.md GETTING_STARTED.md AGENTS.md docs webapp/README.md webapp/docs data/README.md --glob '*.md'
```

Fix current-doc command examples that do not match help output.

- [ ] **Step 4: Verify reduction counts**

Run:

```bash
find docs/plans/active -type f -name '*.md' | sort
find docs/plans/active -type f -name '*.md' | wc -l
find docs -path 'docs/archive' -prune -o -path 'docs/upstream-docs' -prune -o -type f -name '*.md' -print | wc -l
```

Expected: active plan count is exactly 4. Record the measured current
non-archive/non-upstream docs count in `docs/DOCUMENTATION_AUDIT.md` and note
whether it lands inside the 30-40 target band.

- [ ] **Step 5: Final documentation audit summary**

Append a final section to `docs/DOCUMENTATION_AUDIT.md`. Use the actual
measured values from Step 4 in the `After` column:

```markdown
## Final Summary

| Metric | Before | After |
| --- | ---: | ---: |
| Active plans | 24 | 4 |
| Todo plans | 9 | measured after cleanup |
| Current non-archive/non-upstream docs | measured before cleanup | measured after cleanup |

## Canonical Successors

- Roadmap/status: `docs/ROADMAP.md`, `docs/EXECUTION_PLAN.md`
- Reader/web: `docs/READER_CLI_BEGINNER_GUIDE.md`, `docs/READER_CORPUS_STATUS.md`, `docs/READER_DATA_BUILD.md`, `docs/READER_WEB_CONTRACT.md`, `webapp/README.md`
- Technical: `docs/technical/ARCHITECTURE.md`, `docs/technical/README.md`
- Historical material: `docs/archive/2026-05-doc-overhaul/`
```

- [ ] **Step 6: Run final git review**

Run:

```bash
git status --short
git diff --stat
```

Expected: only documentation file edits/moves.

---

## Execution Notes For Subagents

- Use `apply_patch` for manual edits. Use `git mv` for file moves.
- Do not edit files outside assigned ownership.
- Do not remove historical information outright; merge useful content or archive it.
- Keep current docs concise. Do not migrate every old paragraph into the canonical path.
- Prefer links to canonical successors over duplicate explanations.
- Do not run live-service verification. Use help output, tests already reported by the audit agent, and repository-local scans.
