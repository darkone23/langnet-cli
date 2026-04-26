# Just Recipe Health

**Last checked:** 2026-04-26  
**Purpose:** distinguish recipe wiring problems from expected external-service/dependency failures.

## Summary

The primary development recipes are wired. The main gap is that fuzz recipes still reflect an older unified-query/API worldview and should be treated as diagnostic, not as a release gate.

All runtime probes should be invoked through the project environment, preferably:

```bash
devenv shell -- bash -c '<command>'
```

## Healthy Recipes

These were probed successfully:

- `just default`
- `just cli --help`
- `just cli-normalize --help`
- `just cli-plan --help`
- `just cli-plan-exec --help`
- `just cli-databuild --help`
- `just cli index --help`
- `just cli index status`
- `just diogenes-parse --help lupus`
- `just triples-dump --help lupus`
- `just parse --help lat lupus`
- `just autobot --help`
- `just autobot fuzz list`
- `just autobot fuzz run --help`
- `devenv shell -- bash -c 'python3 .justscripts/autobot.py fuzz run --tool cltk --action dictionary --lang lat --words lupus --mode tool --validate --save examples/debug/fuzz_probe_recheck_json'`
- `just read-codesketch-diogenes`
- `just read-codesketch-whitakers`
- `just read-codesketch-cltk`
- `just lint-all`
- `just test-fast`

## Dry-Run Only

These are intentionally not run during routine stabilization because they are destructive, long-running, networked, or require external services:

- `just clean-cache`
- `just restart-server`
- `just reap`
- `just langnet-dg-reaper`
- `just codegen`
- `just translate-lex`
- `just fuzz-query`
- `just fuzz-compare`

## Findings

### Fixed: `plan --output json`

`just cli plan lat lupus --no-cache --output json` previously crashed because protobuf map containers were passed directly to `orjson`. The plan printer now converts params to plain dicts before serialization.

### Corrected: CLTK Data Path Handling

CLTK opens `cltk.log` during import. The client now prefers an existing writable `~/cltk_data` so installed model data is used. If that directory is absent or not writable, it falls back to `data/cache/cltk_data`.

If CLTK model data is absent, the parser fails cleanly:

```text
CLTK client unavailable. Ensure CLTK model data is installed and CLTK_DATA points to a writable directory.
```

This is a dependency/readiness issue, not a traceback or wiring issue.

### Fixed: Fuzz Parser JSON Mode

The fuzz harness was calling `langnet-cli parse` without `--format json`, then trying to parse pretty output as JSON. It now requests JSON explicitly.

### Remaining: Fuzz Harness Semantics

`just fuzz-tools` is useful for parser smoke checks when local tool dependencies are available. `fuzz-query` and `fuzz-compare` are legacy until the project has a supported unified query surface again.

## Recommendation

Keep `just lint-all`, `just test-fast`, CLI help smoke tests, and fixture-backed claim tests as the stabilization gate. Treat fuzz recipes as manual diagnostics until their target model is updated to CLI-first semantics.
