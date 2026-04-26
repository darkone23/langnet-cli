# Junior Engineer Start Packet

**Status:** active handoff  
**Date:** 2026-04-26  
**Feature Area:** infra / semantic-reduction-readiness

## Repo State

The repo is in stabilization mode. The current goal is not broad new functionality; it is making word-level lookup facts reliable enough for semantic reduction.

Known-good validation commands:

```bash
just lint-all
just test-fast
```

Current expected state:

- `just lint-all` passes.
- `just test-fast` passes.
- The suite currently has 156 tests.
- `just triples-dump lat lupi gaffiot` resolves local Gaffiot source evidence.
- `just triples-dump san kṛṣṇa dico` resolves local DICO source evidence.

## Development Rules

- Use `just` recipes rather than ad-hoc commands.
- Prefer service-free tests.
- Do not add live network calls or OpenRouter calls in tests.
- Do not change public CLI behavior unless the task explicitly says to.
- Keep French source evidence separate from future English translation evidence.
- Preserve raw backend encodings when adding display-friendly fields.

## Recommended First Assignments

### 1. JT-016: WSU Dataclasses Only

Start here if the engineer is comfortable editing Python.

- Task: `docs/plans/todo/infra/junior-task-backlog.md`
- Goal: add typed containers for semantic reduction without extraction or clustering.
- Validation: targeted test plus `just lint-all`.

### 2. JT-018: Triples Dump JSON Shape Spec

Start here if the engineer is stronger with docs/specs.

- Task: `docs/plans/todo/infra/junior-task-backlog.md`
- Goal: define structured JSON inspection output before implementation.
- Validation: `just lint-all`.

### 3. JT-014: CDSL IAST Display Fixtures

Use this if the engineer is ready for test-first work around Sanskrit display.

- Task: `docs/plans/todo/infra/junior-task-backlog.md`
- Goal: fixture expectations for readable IAST while preserving raw CDSL source forms.
- Validation: targeted CDSL test plus `just lint-all`.

## Avoid For Now

- Semantic clustering implementation before WSU extraction is specified.
- Translation cache writes before cache identity fixtures exist.
- Embeddings or LLM-based grouping.
- Passage-level interpretation.
- Broad `cli.py` rewrites.

## Review Checklist

Before handing work back:

1. Run the task-specific validation command.
2. Run `just lint-all`.
3. Note any skipped tests or unavailable local services.
4. Summarize changed files and any behavior assumptions.
