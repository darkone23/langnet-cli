# Runtime Engine Notes

The old engine/HTTP path is not the current product contract. The active runtime is CLI-first and staged.

## Current Runtime

- Planner: `src/langnet/planner/core.py`
- Executor: `src/langnet/execution/executor.py`
- Effects: `src/langnet/execution/effects.py`
- Handlers: `src/langnet/execution/handlers/`
- CLI: `src/langnet/cli.py`

## Flow

```text
normalize → plan → fetch → extract → derive → claim
```

Use:

```bash
just cli plan lat lupus
just cli plan-exec lat lupus
just triples-dump lat lupus whitakers
```

## API Note

Some local setups may still run HTTP process-manager helpers. Do not document those as the canonical interface unless the repo grows a first-class supported API entrypoint again.
