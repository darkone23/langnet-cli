# Encounter Action Contract V1 Implementation Plan

> **For agentic workers:** Use test-driven development. Track progress with checkbox (`- [ ]`) syntax. Do not use git commands in this session unless explicitly requested.

**Status:** ✅ DONE - completed 2026-05-11

**Goal:** Make `encounter --output json` the first-class bridge from a lookup result to paradigm tables, word-index neighborhoods, and source-entry inspection.

**Architecture:** Add small, UI-ready action objects to the existing encounter JSON payload instead of creating a new command. Actions are derived from existing `word_index` anchors, `paradigm_resolution` candidates, and display entries, so the lookup path remains source-backed and table fetching stays lazy.

**Tech Stack:** Python dataclasses/dicts, Click CLI JSON output, existing `langnet.encounter.v1`, `langnet.paradigm_resolution.v1`, and `langnet.word_index.v1` contracts, nose2 tests through `just test`.

---

### Task 1: Encounter Actions Helper

**Files:**
- Modify: `src/langnet/cli.py`
- Test: `tests/test_cli_encounter_output.py`

- [x] **Step 1: Write failing tests**
  - Add a unit-style test for a helper that receives a `word_index` context and a `paradigm_resolution` payload and returns actions:
    - `view_paradigm` when a candidate has `paradigm_request`
    - `open_word_index_neighborhood` when a word-index anchor exists
    - `inspect_source_entry` when an anchor has `index_entry_id` or `source_ref`
  - Assert each action has `kind`, `label`, `status`, `request`, and `source`.

- [x] **Step 2: Verify red**
  - Run `just test test_cli_encounter_output`
  - Expected: fails because the action helper or payload field is missing.

- [x] **Step 3: Implement helper**
  - Add `_encounter_actions(...) -> list[dict[str, object]]`.
  - Keep it pure and side-effect free.
  - Do not fetch paradigms or inline word-index neighborhoods.
  - For unresolved paradigm candidates, emit no action unless it helps explain degraded state in a later task.

- [x] **Step 4: Verify green**
  - Run `just test test_cli_encounter_output`
  - Expected: new helper tests pass.

### Task 2: Attach Actions To JSON Payload

**Files:**
- Modify: `src/langnet/cli.py`
- Modify: `docs/schemas/encounter.v1.schema.json`
- Test: `tests/test_cli_encounter_output.py`

- [x] **Step 1: Write failing integration test**
  - Extend the Sanskrit `encounter --include-paradigm-resolution --output json` fixture to assert `payload["display"]["actions"]` includes a `view_paradigm` action whose request matches the resolved Heritage declension request.
  - Assert top-level `payload["actions"]` mirrors the same list for non-display consumers.

- [x] **Step 2: Verify red**
  - Run `just test test_cli_encounter_output`
  - Expected: fails because `actions` is absent.

- [x] **Step 3: Attach actions**
  - Build `paradigm_resolution` before display finalization when requested.
  - Build actions after `word_index` and optional `paradigm_resolution` are available.
  - Store actions at top-level `actions` and `display.actions`.

- [x] **Step 4: Update schema**
  - Add optional `actions` to the top-level payload and `display`.
  - Add a permissive `encounterAction` definition requiring `kind`, `label`, `status`, and `request`.

- [x] **Step 5: Verify green**
  - Run `just test test_cli_encounter_output`
  - Expected: schema and integration tests pass.

### Task 3: Documentation And Verification

**Files:**
- Modify: `docs/OUTPUT_GUIDE.md`
- Modify: `docs/PROJECT_STATUS.md`

- [x] **Step 1: Document the action contract**
  - Explain that `actions` are lazy follow-up targets, not fetched content.
  - Show example action kinds: `view_paradigm`, `open_word_index_neighborhood`, `inspect_source_entry`.

- [x] **Step 2: Run focused tests**
  - Run `just test test_cli_encounter_output test_paradigm_resolver test_word_index_sections`.

- [x] **Step 3: Run closure checks**
  - Run `just lint-all`.
  - Run `just test-fast`.

## Success Marks

- Encounter JSON exposes UI-ready lazy actions without changing existing bucket ranking semantics.
- Sanskrit `putraa.naam` can point from encounter morphology to a Heritage declension request.
- Word-index actions expose the request shape needed to open a source-local neighborhood without inlining rows.
- Source inspection actions preserve source refs/entry IDs for provenance-first UI.
- Focused tests, lint, and fast tests pass.

## Verification Evidence

```bash
just test test_cli_encounter_output
just test test_cli_encounter_output test_paradigm_resolver test_word_index_sections
just cli encounter san putraa.naam heritage --include-paradigm-resolution --output json --translation-mode off
just cli encounter san dharma all --output json --translation-mode off --max-buckets 2
just lint-all
just test-fast
```

`just test-fast` passed with 494 tests.
