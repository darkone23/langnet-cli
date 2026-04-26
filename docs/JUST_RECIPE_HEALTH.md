# Just Recipe Health

**Last checked:** 2026-04-26  
**Purpose:** distinguish recipe wiring problems from expected external-service/dependency failures.

## Summary

The primary development recipes are wired. The latest audit found and fixed stale
CLI wrapper plumbing in the justfile: recipes now preserve `langnet-cli` argv by
running through a small `bash -c 'langnet-cli ... "$@"'` shim inside `devenv`.

The main remaining gap is that some fuzz recipes still reflect an older
unified-query/API worldview and should be treated as diagnostic, not as a release
gate.

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
- `just parse cdsl san agni mw`
- `just triples-dump lat lupi gaffiot`
- `just triples-dump san kṛṣṇa dico`
- `just cli index --help`
- `just cli index status`
- `just diogenes-parse --help lupus`
- `just triples-dump --help lupus`
- `devenv shell -- bash -c 'langnet-cli triples-dump lat lupus gaffiot --no-cache --predicate gloss --max-triples 1'`
- `devenv shell -- bash -c 'langnet-cli triples-dump san dharma dico --no-cache --predicate gloss --max-triples 1'`
- `just parse --help lat lupus`
- `just autobot --help`
- `just autobot fuzz list`
- `just autobot fuzz run --help`
- `just autobot fuzz run --tool cdsl --action lookup --lang san --words agni --validate --mode tool --save examples/debug/fuzz_results_audit`
- `devenv shell -- bash -c 'python3 .justscripts/autobot.py fuzz run --tool cltk --action dictionary --lang lat --words lupus --mode tool --validate --save examples/debug/fuzz_probe_recheck_json'`
- `devenv shell -- bash -c 'python3 .justscripts/lex_translation_demo.py --help'`
- `devenv shell -- bash -c 'python3 .justscripts/lex_translation_demo.py --dry-run --limit 1 --mode sanskrit'`
- `devenv shell -- bash -c 'python3 .justscripts/lex_translation_demo.py --dry-run --limit 1 --mode latin'`
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

### Fixed: Just CLI Wrapper Argument Routing

The old CLI wrappers used `devenv shell langnet-cli -- ...`, which can misroute
Click arguments and produce misleading command help. For example, a plan wrapper
could show a different subcommand's help.

The wrappers now use `devenv shell -- bash -c 'langnet-cli <subcommand> "$@"' _ ...`
so `--help`, subcommands, and positional arguments are passed unchanged.

### Fixed: Stale Helper Script Bypass

`parse`, `diogenes-parse`, and `triples-dump` recipes now route through the
maintained `langnet-cli` commands instead of older `.justscripts` helper
entrypoints. The helper scripts remain available as implementation/debug assets,
but recipe-level behavior now exercises the supported CLI surface.

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

### Improved: Translation Recipe Dry Run

`just translate-lex` remains a networked recipe for real translation, but the helper now supports `--dry-run`. This verifies DuckDB row access, mode selection, hint selection, and chunking without `OPENAI_API_KEY` or a model call.

The helper is currently strongest for Gaffiot/Latin entries. Sanskrit/DICO support exists, but should be promoted only after fixture-backed examples prove the prompt behavior.

Translated DICO/Gaffiot entries are still not part of `triples-dump`; see `docs/TRANSLATION_CACHE_PLAN.md` for the cache-first path needed before semantic reduction consumes them.

Source-language DICO/Gaffiot entries are now locally resolvable in `triples-dump`; translation remains the missing cache-backed layer.

`triples-dump` now supports `--predicate`, `--subject-prefix`, and `--max-triples` so evidence inspection can focus on reducer-relevant triples.

### Remaining: Fuzz Harness Semantics

`just fuzz-tools` is useful for parser smoke checks when local tool dependencies are available. `fuzz-query` and `fuzz-compare` are legacy until the project has a supported unified query surface again.

## Recommendation

Keep `just lint-all`, `just test-fast`, CLI help smoke tests, and fixture-backed claim tests as the stabilization gate. Treat fuzz recipes as manual diagnostics until their target model is updated to CLI-first semantics.
