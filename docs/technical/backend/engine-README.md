# Runtime Engine Notes

The active runtime is CLI-first and staged. The current web bridge is the
SvelteKit adapter in `webapp/src/routes/api/*`, which shells through repository
wrappers to CLI JSON and local files. There is no supported Python HTTP product
contract in this checkout.

## Current Runtime

- Planner: `src/langnet/planner/core.py`
- Executor: `src/langnet/execution/executor.py`
- Effects: `src/langnet/execution/effects.py`
- Handlers: `src/langnet/execution/handlers/`
- CLI: `src/langnet/cli.py`
- Web adapter: `webapp/src/routes/api/`

## Flow

```text
normalize → plan → fetch → extract → derive → claim
```

Use:

```bash
just cli plan lat lupus
just cli plan-exec lat lupus
just cli triples-dump lat lupus whitakers
```

## Web Bridge

The SvelteKit adapter currently exposes `/api/search`, `/api/reader`,
`/api/word-index`, `/api/paradigm`, `/api/motd`, and
`/api/translation-cache`. Treat those routes as UI adapter code around CLI JSON,
not as a separate backend engine.
