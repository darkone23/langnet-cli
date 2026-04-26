# Junior Task Backlog

**Status:** 🔄 ACTIVE  
**Feature Area:** infra  
**Purpose:** small, clearly scoped tasks that a junior engineer can pick up intermittently.

## Assignment Rules

- Each task should fit in roughly 30–120 minutes.
- Prefer service-free tests and docs.
- Include exact files to read/edit.
- Include validation commands.
- Do not assign architecture decisions without a short design note first.

## Recently Completed

- CLI command documentation.
- CLI help smoke tests.
- Destructive `just` recipe comments.
- Helper script `--help` behavior.
- Pretty-output fixture tests.
- Primary-doc stale reference cleanup.
- Claim contract helper.
- Whitaker claim fixture coverage.
- CDSL claim fixture coverage.
- Predicate contract drift test.
- WSU fixture contract test.
- Translation recipe dry-run mode.
- Just CLI wrapper argument routing fix.
- Local DICO/Gaffiot content-addressed raw response IDs.
- DICO/Gaffiot deterministic-ID regression tests.

## Task Catalog

Use tasks marked `⏳ READY` for new assignments. Completed entries are retained briefly to prevent duplicate work.

### JT-010: Draft Claim-to-WSU Fixture

**Status:** ✅ DONE  
**Roadmap Milestone:** Semantic Reduction MVP  
**Suggested Owner:** junior engineer + @scribe/@coder

**Goal:** create a small, hand-written fixture that represents the input semantic reduction should consume.

**Files**

- Read: `docs/technical/design/classifier-and-reducer.md`
- Read: `docs/plans/todo/semantic-reduction/semantic-reduction-mvp.md`
- Edit: new fixture under `tests/fixtures/` or a short markdown spec under `docs/technical/`

**Steps**

1. Define 3–5 claim triples for one word, preferably `lupus`.
2. Include at least two glosses that should cluster together and one that should not.
3. Include evidence IDs in the fixture.
4. Do not implement the reducer.

**Acceptance Criteria**

- Fixture distinguishes witness, gloss, source, and evidence.
- Future reducer test can consume the fixture with minimal translation.
- `just lint-all` passes.

**Validation**

```bash
just lint-all
```

---

### JT-016: Implement WSU Dataclasses Only

**Status:** ⏳ READY  
**Roadmap Milestone:** Semantic Reduction MVP  
**Suggested Owner:** junior engineer + @coder/@auditor

**Goal:** add minimal semantic-reduction data containers without implementing clustering.

**Files**

- Read: `docs/plans/todo/semantic-reduction/semantic-reduction-mvp.md`
- Read: `tests/fixtures/lupus_claims_wsu.json`
- Edit: new module under `src/langnet/reduction/` or `src/langnet/semantic/`
- Edit: new test under `tests/`

**Steps**

1. Create dataclasses for `WitnessSenseUnit`, `SenseBucket`, and `ReductionResult`.
2. Include fields for stable IDs, normalized gloss text, source claim ID, source triple subject, and evidence metadata.
3. Add a tiny import/serialization test.
4. Do not implement extraction or clustering yet.

**Acceptance Criteria**

- Dataclasses are typed and service-free.
- Tests prove objects can be constructed from simple fixture-shaped values.
- `just test <new_test_module>` and `just lint-all` pass.

**Validation**

```bash
just test <new_test_module>
just lint-all
```

---

### JT-017: WSU Extraction Fixture Test

**Status:** ⏳ READY  
**Roadmap Milestone:** Semantic Reduction MVP  
**Suggested Owner:** junior engineer + @coder/@auditor

**Goal:** specify extraction behavior from existing claim triples before implementing clustering.

**Files**

- Read: `tests/fixtures/lupus_claims_wsu.json`
- Read: `tests/test_semantic_fixture_contract.py`
- Read: `docs/SEMANTIC_READINESS.md`
- Edit: new or existing semantic/reduction test under `tests/`

**Steps**

1. Load `tests/fixtures/lupus_claims_wsu.json`.
2. Define expected WSU count from paired `has_sense` + `gloss` triples.
3. Assert each expected WSU has `claim_id`, `sense_id`, `gloss`, and evidence.
4. Do not implement semantic grouping in this task.

**Acceptance Criteria**

- Test is service-free.
- Expected behavior is clear enough for the next implementer to write the extractor.
- `just test <new_test_module>` and `just lint-all` pass after implementation or an explicit skipped/spec-only test is agreed.

**Validation**

```bash
just test <new_test_module>
just lint-all
```

---

### JT-018: Triples Dump JSON Shape Spec

**Status:** ⏳ READY  
**Roadmap Milestone:** Evidence Inspection  
**Suggested Owner:** junior engineer + @scribe/@auditor

**Goal:** define the JSON output shape needed for structured claim/triple inspection.

**Files**

- Read: `src/langnet/cli_triples.py`
- Read: `docs/OUTPUT_GUIDE.md`
- Edit: `docs/OUTPUT_GUIDE.md` or a new small fixture under `tests/fixtures/`

**Steps**

1. Propose a JSON shape with `claims`, `triples`, and `filters`.
2. Include one sample claim with one `has_sense` triple and one `gloss` triple.
3. Include evidence metadata in the sample.
4. Do not implement the CLI flag unless explicitly assigned after review.

**Acceptance Criteria**

- The shape can be tested without scraping text output.
- The sample distinguishes claim metadata from triple metadata.
- `just lint-all` passes.

**Validation**

```bash
just lint-all
```

---

### JT-019: CDSL IAST Display Implementation Slice

**Status:** ⏳ READY  
**Roadmap Milestone:** Claim Contract Hardening  
**Suggested Owner:** junior engineer + @coder/@auditor

**Goal:** add the smallest service-free code change that exposes readable IAST display text while preserving raw CDSL source encoding.

**Files**

- Read: `src/langnet/execution/handlers/cdsl.py`
- Read: `tests/test_cdsl_triples.py`
- Edit: `src/langnet/execution/handlers/cdsl.py`
- Edit: `tests/test_cdsl_triples.py`

**Steps**

1. Find where CDSL triples include raw Sanskrit/source forms.
2. Add a `display_iast` field only where a reliable conversion already exists.
3. Preserve the raw source field unchanged.
4. Add service-free fixture assertions for `Darma`, `agni`, and one retroflex/vowel-heavy form.

**Acceptance Criteria**

- Learner-facing display can use IAST without losing raw CDSL evidence.
- Existing CDSL tests still pass.
- `just test test_cdsl_triples` and `just lint-all` pass.

**Validation**

```bash
just test test_cdsl_triples
just lint-all
```

---

### JT-011: Add Predicate Constants Smoke Test

**Status:** ✅ DONE  
**Roadmap Milestone:** Claim Contract Hardening  
**Suggested Owner:** junior engineer + @auditor

**Goal:** catch accidental drift between documented predicates and code constants.

**Files**

- Read: `docs/technical/predicates_evidence.md`
- Read: `src/langnet/execution/predicates.py`
- Edit: new or existing test under `tests/`

**Steps**

1. Inspect current predicate constants.
2. Add a test that asserts known core predicates exist.
3. Do not require live services.

**Acceptance Criteria**

- Test fails if a core predicate is removed or renamed without an intentional update.
- `just test <new_test_module>` and `just lint-all` pass.

---

### JT-012: Evidence Inspection Example

**Status:** ⏳ READY  
**Roadmap Milestone:** Evidence Inspection  
**Suggested Owner:** junior engineer + @scribe

**Goal:** add one concise docs example showing how to trace a claim to evidence.

**Files**

- Read: `docs/OUTPUT_GUIDE.md`
- Read: `tests/test_whitakers_triples.py`
- Edit: `docs/OUTPUT_GUIDE.md`

**Steps**

1. Use the Whitaker fixture shape as the example.
2. Show one triple and its evidence block.
3. Explain what each evidence ID means in one sentence.

**Acceptance Criteria**

- No live backend required.
- Example matches current claim contract.
- `just lint-all` passes.

**Validation**

```bash
just lint-all
```

---

### JT-013: Translation Cache Fixture Spec

**Status:** ⏳ READY  
**Roadmap Milestone:** Semantic Reduction Readiness  
**Suggested Owner:** junior engineer + @scribe/@auditor

**Goal:** define no-network fixture rows for cached Gaffiot-first French → English translation.

**Files**

- Read: `docs/TRANSLATION_CACHE_PLAN.md`
- Read: `.justscripts/lex_translation_demo.py`
- Edit: new fixture under `tests/fixtures/` or a short spec under `docs/technical/`

**Steps**

1. Define one Gaffiot row with `entry_id`, `occurrence`, `headword_norm`, and `plain_text`.
2. Add expected cache identity fields, including `source_text_hash`, `model`, `prompt_hash`, and `hint_hash`.
3. Add one translated English text value for the row.
4. Optionally add one DICO row only if the Sanskrit example is manually reviewed.
5. Do not call OpenRouter or implement cache writes.

**Acceptance Criteria**

- Fixture is deterministic and contains no secrets.
- Fixture reflects Gaffiot paragraph/citation behavior.
- Fixture makes stale source text or stale prompt hashes easy to test.
- Future tests can consume it without live network or local DuckDB data.

**Validation**

```bash
just lint-all
```

---

### JT-014: CDSL IAST Display Fixtures

**Status:** ⏳ READY  
**Roadmap Milestone:** Claim Contract Hardening  
**Suggested Owner:** junior engineer + @coder/@auditor

**Goal:** define service-free examples for readable CDSL Sanskrit forms while preserving raw source encoding.

**Files**

- Read: `src/langnet/execution/handlers/cdsl.py`
- Read: `docs/plans/active/infra/local-lexicon-witness-handoff.md`
- Edit: new or existing CDSL tests under `tests/`

**Steps**

1. Add fixture examples for raw CDSL forms such as `Darma`, `agni`, and one form with retroflex/vowel markers.
2. Assert the future display field should be IAST UTF-8.
3. Assert raw source form remains available in evidence or grammar metadata.
4. Do not change live CDSL data files.

**Acceptance Criteria**

- Tests are service-free and deterministic.
- The expected contract distinguishes raw source encoding from display IAST.
- `just test <new_test_module>` and `just lint-all` pass.

**Validation**

```bash
just lint-all
```

---

### JT-015: Triples Dump Inspection Example

**Status:** ⏳ READY  
**Roadmap Milestone:** Evidence Inspection  
**Suggested Owner:** junior engineer + @scribe

**Goal:** document focused `triples-dump` inspection using the new filter flags.

**Files**

- Read: `docs/OUTPUT_GUIDE.md`
- Read: `docs/JUST_RECIPE_HEALTH.md`
- Edit: `docs/OUTPUT_GUIDE.md`

**Steps**

1. Add one Latin example using `--predicate gloss --max-triples 1`.
2. Add one Sanskrit example using `--predicate gloss --max-triples 1`.
3. Explain that Gaffiot/DICO glosses are original French source evidence.

**Acceptance Criteria**

- Examples use current command names.
- The doc does not imply translation is already cached or emitted.
- `just lint-all` passes.

**Validation**

```bash
just lint-all
```
