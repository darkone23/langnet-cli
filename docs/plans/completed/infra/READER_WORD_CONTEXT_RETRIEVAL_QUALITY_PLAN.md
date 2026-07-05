# Reader Word Context Retrieval Quality Plan

> **For agentic workers:** Implement this as a quality-gated reader feature, not as a decorative UI pass. The CLI contract, web API contract, UI sidebar, retrieval performance, and correctness fixtures must advance together.

**Goal:** Make selected-word reader marginalia fast, accurate, source-backed, and reusable across CLI and UI, so a request like `give me a sidebar for corpore` returns morphology, lexical evidence, corpus hits, passage context, and provenance without silent retrieval failures.

**Architecture:** Add a unified reader word-context payload in the CLI/service layer, expose it through `/api/reader`, and render it in the reader sidebar. Keep deterministic evidence separate from generated interpretation. Add small golden-query fixtures and retrieval-quality audit gates so correctness and performance regressions are visible before future expansion work resumes.

**Tech Stack:** Python reader service and CLI, DuckDB reader catalog, existing reader search index path, SvelteKit `/api/reader`, Svelte reader components, active reader quality audit TSVs.

---

## Why This Plan Exists

The reader already has useful primitives:

- selected-word marginalia UI
- encounter briefing data
- reader text search
- work contents and structure
- source-index provenance
- work dossiers
- API caching and server timing

The gap is integration. A selected word currently depends on multiple surfaces that can disagree, be slow, or fail independently. The next quality target is a single evidence bundle that is accurate enough for learners and researchers, fast enough for repeated reader use, and explicit when a source/index/cache is unavailable.

## Success Criteria

A reader clicking `corpore` in a Latin passage should see, without ambiguity about source status:

- the selected surface form
- normalized lookup candidates
- lemma and morphology candidates where available
- dictionary or lexical evidence with source labels
- exact reader-corpus hits when the corpus index is available
- nearby/current-work hits where possible
- the current passage and citation context
- work/source provenance for the passage
- caveats when forms are ambiguous or evidence is incomplete
- timing and cache/index status sufficient for debugging slow retrieval

The same payload should be available through CLI JSON and `/api/reader`, so UI behavior is not a one-off frontend assembly.

## Scope

In scope:

- CLI reader command for word-context retrieval
- reader service payload composition
- web API mode for word-context
- selected-word sidebar integration
- correctness fixtures for common forms
- retrieval-performance instrumentation
- search-index status exposure in the payload
- source/provenance fields needed by the sidebar
- quality-audit tracking for retrieval defects

Out of scope for this plan:

- broad `search.lance` rebuild campaigns
- new corpus imports
- generated prose as the primary answer
- author/work expansion beyond metadata required for word context
- full persistent caching infrastructure if short-term in-memory caching is sufficient

## Proposed User-Facing Contract

### CLI

Add a command shaped like:

```bash
just cli reader word-context corpore \
  --language lat \
  --work urn:ctsv2:lat:example-work \
  --segment 1.1 \
  --output json
```

Minimum JSON shape:

```json
{
  "schema_version": "langnet.reader.word_context.v1",
  "mode": "word-context",
  "request": {
    "language": "lat",
    "query": "corpore",
    "work_ref": "urn:ctsv2:lat:example-work",
    "segment_ref": "1.1",
    "catalog_path": "data/build/reader/catalog.duckdb"
  },
  "normalization": {
    "surface": "corpore",
    "candidates": ["corpore"]
  },
  "lexical_evidence": {
    "status": "available",
    "items": []
  },
  "morphology": {
    "status": "available",
    "items": []
  },
  "reader_hits": {
    "status": "available",
    "index_status": {},
    "items": []
  },
  "passage_context": {
    "status": "available",
    "work": {},
    "segment": {},
    "source": {}
  },
  "provenance": {
    "work_id": null,
    "collection_id": null,
    "source_id": null,
    "source_path": null,
    "file_status": null,
    "quality_status": null
  },
  "caveats": [],
  "timing": {
    "total_ms": 0,
    "steps": []
  }
}
```

### Web API

Add:

```text
/api/reader?mode=word-context&language=lat&q=corpore&work=<workRef>&segment=<segmentRef>
```

Rules:

- `language` and `q` are required.
- `work` and `segment` are optional but should be used when available.
- The API must distinguish `no_hits` from `index_unavailable`.
- The response should be cacheable when it contains no active generation request.

### UI

The selected-word panel should render deterministic evidence first:

- form and normalization
- morphology candidates
- lexicon evidence
- corpus/passages hits
- provenance/source witness
- caveats

Generated briefing should remain secondary. If generation is slow or disabled, the sidebar still needs to be useful.

## Quality Gates

### Accuracy Gates

Add golden-query fixtures for forms that are common, ambiguous, or pedagogically useful:

```text
lat: corpore, amor, arma, virum, est, dixit
```

Future extension:

```text
grc: logos-style forms, common article/preposition forms, high-frequency verb forms
san: agni, dharma-style examples, common inflected noun/verb forms
```

Each fixture should specify:

- language
- query
- expected normalized candidates
- expected lemma candidate labels when available
- acceptable morphology summaries when available
- whether corpus hits are expected only when the reader search index is available
- caveats that must appear for genuinely ambiguous forms

### Retrieval Gates

The payload must report:

- whether reader search index exists
- catalog path associated with the index
- indexed segment count
- normalizer version
- whether query results came from indexed search, fallback lookup, cache, or unavailable source

No UI may silently present an unavailable index as zero results.

### Performance Gates

Initial target budgets:

- cached word-context request: under 250 ms server-side where dictionary/index data is already warm
- indexed deterministic word-context request: under 1000 ms server-side for common forms
- generated briefing: may exceed this budget, but must not block deterministic evidence rendering

Record timings in the payload and `server-timing` headers.

### Project Gates

Before this plan can be marked complete:

- CLI JSON command exists and returns the unified payload
- `/api/reader` exposes the same payload
- selected-word sidebar uses the payload
- deterministic evidence renders without generated prose
- golden-query fixtures exist for Latin starter forms
- retrieval-quality audit rows are resolved or explicitly deferred
- existing reader/library quality gates remain satisfied

## Implementation Tasks

### Task 1: Add retrieval-quality audit rows

Files:

- Modify: `data/reference/reader_quality_audit/current_known_issues.tsv`

Add rows for:

- `reader_word_context_payload_missing`
- `reader_word_context_no_golden_queries`
- `reader_word_context_index_status_not_visible`
- `reader_selected_word_sidebar_generation_dependent`

Acceptance:

- Retrieval-quality defects are tracked alongside corpus/import defects.
- Rows clearly state next action and acceptance conditions.

### Task 2: Add reader service word-context payload

Files:

- Modify: `src/langnet/reader/service.py`
- Possibly modify: `src/langnet/reader/storage.py`

Implementation notes:

- Add `word_context_payload(...)` to `ReaderService`.
- Reuse existing normalizers and search-index status/search helpers.
- Reuse segment/work/source lookup functions when `work` and `segment` are supplied.
- Include timing by step.
- Return explicit statuses: `available`, `unavailable`, `no_hits`, `error`, or `not_requested`.

Acceptance:

- Payload can be produced without web code.
- Missing search index produces a caveat and `index_unavailable`, not a false zero-hit result.

### Task 3: Add CLI command

Files:

- Modify: `src/langnet/cli.py`

Command shape:

```bash
just cli reader word-context corpore --language lat --output json
```

Optional arguments:

```text
--work
--segment
--index
--reader-search-limit
--reader-search-context
```

Acceptance:

- CLI JSON exposes the same schema as the service payload.
- The command is usable for manual QA of selected-word sidebar behavior.

### Task 4: Add API mode

Files:

- Modify: `webapp/src/routes/api/reader/+server.ts`
- Modify: `webapp/src/lib/server/reader-cli.ts`
- Modify: `webapp/src/lib/reader/reader-api.ts`
- Modify: `webapp/src/lib/reader/index.ts` if shared types are needed there

Implementation notes:

- Add `word-context` to valid reader API modes.
- Add a server CLI wrapper that calls `reader word-context`.
- Add URL builder and typed fetch helper.
- Preserve request cancellation via `AbortSignal`.
- Cache deterministic payloads using existing reader response cache behavior where safe.

Acceptance:

- `/api/reader?mode=word-context&language=lat&q=corpore` returns the CLI-backed payload.
- API response includes timing/caveat/index-status fields.

### Task 5: Integrate selected-word sidebar

Files:

- Modify: `webapp/src/lib/reader/ReaderSelectedWordPanel.svelte`
- Modify likely state/loading files under `webapp/src/lib/reader/reader-route-content-loaders.ts` or the route controller components

Implementation notes:

- Load word-context when `selectedWord` changes.
- Pass current `language`, `catalog`, `work`, and `segment` when available.
- Render deterministic evidence first.
- Keep generated encounter briefing secondary.
- Show caveats and index/source availability clearly.

Acceptance:

- Sidebar remains useful without generated briefing.
- `corpore` has visible lexical/morphological/corpus/provenance sections where data is available.
- Slow generated prose does not block deterministic evidence.

### Task 6: Add golden-query fixtures and tests/checks

Files:

- Create: `tests/fixtures/reader_word_context_golden/latin.json`
- Add or modify a focused test file under `tests/`

Starter fixture entries:

```json
[
  {
    "language": "lat",
    "query": "corpore",
    "expected_normalized_candidates": ["corpore"],
    "expected_caveat_policy": "ambiguity_allowed",
    "reader_hits_policy": "index_dependent"
  },
  {
    "language": "lat",
    "query": "arma",
    "expected_normalized_candidates": ["arma"],
    "expected_caveat_policy": "ambiguity_allowed",
    "reader_hits_policy": "index_dependent"
  },
  {
    "language": "lat",
    "query": "virum",
    "expected_normalized_candidates": ["virum"],
    "expected_caveat_policy": "ambiguity_allowed",
    "reader_hits_policy": "index_dependent"
  }
]
```

Acceptance:

- Fixtures assert structural correctness and caveat behavior without overclaiming exact parses where local tools vary.
- Tests distinguish unavailable evidence from incorrect evidence.

### Task 7: Add performance instrumentation

Files:

- Modify: `src/langnet/reader/service.py`
- Modify: `webapp/src/routes/api/reader/+server.ts` if additional `server-timing` labels are needed

Timing steps should include:

- catalog/work/segment resolution
- normalization
- lexical lookup
- morphology lookup
- reader search
- source/provenance assembly
- cache state where available

Acceptance:

- Payload timing explains slow word-context requests.
- Server timing remains visible in API responses.

### Task 8: Add search-index health to the reader/library surfaces

Files:

- Modify: `webapp/src/lib/reader/ReaderSelectedWordPanel.svelte`
- Possibly modify: library or reader header components if a compact index-health chip is useful

Acceptance:

- Users can distinguish no hits from unavailable/stale index.
- Retrieval health does not require reading logs.

### Task 9: Update active coordination docs after implementation

Files:

- Modify: `docs/EXECUTION_PLAN.md`
- Modify: `data/reference/reader_quality_audit/current_known_issues.tsv`
- If a dated handoff is needed, create it under `docs/archive/2026-06-reader-expansion/` or a newer dated archive folder rather than under `docs/plans/active/`.

Acceptance:

- The plan status is clear.
- Remaining retrieval-quality defects are either fixed, verified, or explicitly deferred.
- Corpus expansion remains paused until retrieval quality gates are stable.

## Execution Order

1. Add quality-audit rows so defects are tracked before implementation starts.
2. Implement service payload.
3. Add CLI command.
4. Add API mode and URL builder.
5. Integrate UI sidebar.
6. Add golden-query fixtures.
7. Add performance/index-health display.
8. Update coordination/handoff docs.

## Verification Commands

Run only when implementation work is ready for verification:

```bash
just cli reader word-context corpore --language lat --output json
```

Expected:

- schema version is `langnet.reader.word_context.v1`
- deterministic evidence sections exist
- unavailable evidence is explicit
- timing fields exist

```bash
curl -fsS 'http://127.0.0.1:43210/api/reader?mode=word-context&language=lat&q=corpore'
```

Expected:

- API returns the same high-level payload shape as CLI
- response is not blocked by generated prose

```bash
cd webapp && bun run check
```

Expected:

- Svelte typecheck passes

```bash
just test
```

Expected:

- Existing project tests and new golden-query structural tests pass

## Risks

- Dictionary/morphology tools may be slower than reader search. Mitigation: deterministic sections should have independent statuses and timing.
- Exact morphology for ambiguous forms can overfit tests. Mitigation: fixtures should assert acceptable candidate/caveat behavior, not one false-perfect parse.
- Search-index absence can be mistaken for no corpus matches. Mitigation: index health is mandatory in payload and UI.
- Generated briefing can hide weak deterministic evidence. Mitigation: render evidence first and generated interpretation second.

## Completion Definition

This plan is complete when a selected Latin word such as `corpore` can be retrieved through CLI, API, and UI as one source-backed word-context bundle, with accuracy fixtures, timing metadata, visible index/source status, and no unresolved project quality-gate regressions.

## Implementation Status - 2026-06-07

Completed in the first implementation slice:

- Added retrieval-quality audit rows to `data/reference/reader_quality_audit/current_known_issues.tsv`.
- Added `ReaderService.word_context_payload(...)` with normalization, optional passage context, source-index provenance, reader search-index status, indexed corpus hits, caveats, and timing.
- Added CLI command shape: `just cli reader word-context corpore --language lat --output json`.
- Added `/api/reader?mode=word-context&language=lat&q=corpore`.
- Added web reader URL builder and shared `ReaderWordContextResponse` type.
- Added starter Latin golden-query fixture at `tests/fixtures/reader_word_context_golden/latin.json`.
- Wired selected-word reader marginalia to request deterministic word context and render it before generated encounter briefing.

Still open:

- Validate lexical and morphology evidence against live Latin/Greek/Sanskrit
  cache/read-only lookup data and expand fixtures only where source evidence is
  stable.
- Add structural tests around the golden-query fixture. Completed on 2026-06-17
  with `tests/test_reader_word_context_golden.py`.
- Add UI polish for source/index health display after validation.
- Run CLI/API/web verification once explicit validation is approved for this stack.

## Verification Update - 2026-06-07

Verified after implementation:

- `python -m py_compile src/langnet/reader/service.py src/langnet/cli.py` passed before the cache-only evidence patch; `python -m py_compile src/langnet/reader/service.py` passed after the final service patch.
- `just cli reader word-context corpore --language lat --output json` returns `langnet.reader.word_context.v1`.
- The initial CLI run exposed a performance defect: the current search index has no Latin slice and a doomed Latin search took about 43 seconds.
- The service now detects that condition from `index_status.language_counts` and returns `reader_hits.status = index_unavailable` with an explicit caveat.
- The corrected CLI run returned in about 487 ms for `corpore`.
- `cd webapp && bun run check` passed with 0 errors and 0 warnings.
- `cd webapp && bun run build` passed after the final changes.
- The old `43210` listener was killed and process-compose restarted the web server with a new node process.
- Live API check passed: `/api/reader?mode=word-context&language=lat&q=corpore&limit=3` returned the word-context payload from the running server in about 480 ms server timing.

Current caveat:

- The existing `data/build/reader/search.lance` index has `grc`, `eng`, and `cop` rows but no `lat` slice, so Latin corpus hits are correctly reported as unavailable until a reader search-index rebuild includes Latin.

## Latin Search-Index Verification Update - 2026-06-07

Completed after the initial word-context endpoint work:

- Ran `just cli reader search-index build --language lat --output json`.
- Build completed with `1,122,431` Latin segments and `3,021` Latin works indexed.
- `just cli reader search-index status --output json` now reports language counts including `lat: 1122431` and FTS indexes `search_text_folded_idx`, `search_text_idx`, and `token_text_idx`.
- `just cli reader word-context corpore --language lat --reader-search-limit 3 --output json` now returns `reader_hits.status = available` with Latin hits from CSEL, PHI, and Perseus Ovid.
- Live API `/api/reader?mode=word-context&language=lat&q=corpore&limit=3` also returns available Latin corpus hits.

Remaining limitation:

- Lexical and morphology evidence still rely only on cache-only normalizer evidence in this endpoint. Full dictionary/paradigm integration remains the next word-context task.

## Next Implementation Slice - 2026-06-17

The next slice should stay narrow: make `lexical_evidence` useful before
attempting full morphology. Do not make generated briefing compensate for weak
deterministic evidence.

Recommended order:

1. Add a focused service test for `ReaderService.word_context_payload(...)` using
   one Latin golden row such as `corpore` or `arma`.
2. Reuse the existing encounter/lookup evidence path in read-only/cache mode to
   populate `lexical_evidence.items` with source labels, lemmas/headwords, short
   gloss text where available, and source refs.
3. Keep lexical lookup independently timed and independently failed. If lookup is
   unavailable, return `lexical_evidence.status = "unavailable"` or `"error"`
   with a caveat; do not block reader hits.
4. Add CLI verification for:

   ```bash
   just cli reader word-context corpore --language lat --reader-search-limit 3 --output json
   ```

   Expected: `schema_version = langnet.reader.word_context.v1`,
   `reader_hits.status` remains truthful, and `lexical_evidence.status` is no
   longer just the cache-only normalizer status when dictionary evidence is
   available.

5. After lexical evidence is stable, add morphology evidence from the parser or
   paradigm path as a separate slice with its own tests and timing step.

Current guardrails:

- The golden starter fixture is now structurally tested.
- `amor` is included in the Latin starter set alongside `corpore`, `arma`,
  `virum`, `est`, and `dixit`.
- The selected-word sidebar must keep deterministic word context above generated
  briefing.

## Implementation Update - 2026-06-18

Completed the next deterministic evidence slice:

- `ReaderService.word_context_payload(...)` now accepts independent optional
  providers for lexical evidence and morphology evidence.
- `reader word-context` wires both providers from the CLI layer.
- Lexical evidence reuses encounter reduction in read-only/cache mode and
  formats source-backed rows with lemma, source, gloss, source ref, bucket, and
  witness metadata.
- Morphology evidence reuses `_encounter_morphology_rows(...)` in read-only/cache
  mode and returns compact parser-derived rows when `has_morphology` claims are
  available.
- Lexical and morphology lookup failures remain non-fatal and independently
  timed; reader hits and passage context still return with explicit caveats.
- Added focused service and CLI tests for provider wiring and provider output.

Remaining work:

- None for this plan. Future reader-side refinements should open narrower
  follow-up plans instead of extending this retrieval-quality slice.

## Live Validation Update - 2026-06-18

Ran live CLI checks with:

```bash
just cli reader word-context <query> --language <language> --reader-search-limit 3 --output json
```

Latin starter forms validated:

- `corpore`, `amor`, `arma`, `virum`, `est`, and `dixit` all returned
  `schema_version = langnet.reader.word_context.v1`.
- Each Latin starter returned `lexical_evidence.status = available`,
  `morphology.status = available`, `reader_hits.status = available`, and no
  caveats in the current local cache/index state.
- Stable lexical and morphology expectations were promoted into
  `tests/fixtures/reader_word_context_golden/latin.json` as conservative policy
  fields: status, minimum item counts, accepted lemma sets, and accepted source
  sets. The fixture intentionally does not assert exact first-row order for
  ambiguous forms.

Cross-language spot checks:

- Greek `λόγος` returned available lexical evidence, available morphology, and
  available reader hits.
- Sanskrit `agni` returned available lexical evidence and morphology, but
  `reader_hits.status = index_unavailable` because the current reader search
  index has no `san` slice. Keep Sanskrit out of strict golden-hit expectations
  until the Sanskrit reader index state is deliberate.
- Added `greek.json` and `sanskrit.json` golden fixtures with conservative
  lexical, morphology, caveat, and reader-hit policies. Greek rows require
  available reader hits; Sanskrit rows explicitly expect the current
  `index_unavailable` reader-hit policy.

## UI Evidence Display Update - 2026-06-18

Completed reader-sidebar display polish for the validated deterministic payload:

- Added concrete web types for lexical evidence rows and morphology rows.
- Added shared display helpers for word-context status labels, evidence row
  labels, morphology row labels, and source labels.
- Updated the selected-word marginalia panel to show top lexical and morphology
  rows before generated briefing, including compact sources and notes when rows
  are unavailable.
- Kept corpus-hit status, timing, provenance chips, caveats, and generated
  briefing visually separate so deterministic evidence remains first.

## Closeout - 2026-06-18

This plan is complete.

Verified:

- `reader word-context` has deterministic CLI/API payload support for
  normalization, lexical evidence, morphology, reader hits, passage context,
  caveats, and timing.
- Latin, Greek, and Sanskrit golden fixture files define source-backed policy
  expectations without overfitting row order for ambiguous forms.
- The selected-word reader sidebar renders deterministic lexical and morphology
  evidence before optional generated briefing.
- Remaining Sanskrit reader-hit work is an index/acquisition decision, not a
  word-context retrieval-quality blocker.
