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

## Ready Tasks

### JT-010: Draft Claim-to-WSU Fixture

**Status:** ⏳ READY  
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
