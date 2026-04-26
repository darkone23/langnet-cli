# Query Planning

Query planning converts a normalized lookup request into a tool-plan DAG.

## Current Runtime

`src/langnet/planner/core.py` builds plans for supported languages. `src/langnet/execution/executor.py` executes the staged plan.

## Flow

```text
input language + query
  → normalization
  → tool selection
  → fetch calls
  → extract calls
  → derive calls
  → claim calls
```

## Requirements

- Plans should be deterministic for the same normalized query.
- Tool calls should include stable IDs.
- Stages should preserve dependency edges.
- Missing optional tools should produce explicit errors or skipped calls, not silent success.
- Tests should not require live services unless marked as integration tests.

## Inspection

Use:

```bash
just cli plan lat lupus
just cli plan-exec lat lupus
```

Future work should improve `plan-exec` with cache hit/miss status, skipped-call reasons, stage counts, and handler versions.
