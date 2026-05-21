> Archived during the 2026-05 documentation overhaul. Retained for historical context; current guidance lives in `docs/ROADMAP.md`, `docs/EXECUTION_PLAN.md`, and `docs/README.md`.

# Just Recipe Health

**Last checked:** 2026-05-05  
**Purpose:** distinguish recipe wiring problems from expected external-service/dependency failures.

## Summary

The primary development recipes are wired when run sequentially. CLI wrappers
now preserve `langnet-cli` argv by routing through
`.justscripts/run-langnet-cli`, which prefers the already-built devenv
entrypoint and falls back to `devenv shell -- langnet-cli` only when needed.
Non-CLI development recipes route through `.justscripts/run-dev-tool`, which
sources the generated devenv exports and then runs the venv/profile executable
directly when possible.

Do not audit `devenv shell` or variadic Just recipes in parallel. Parallel
recipe probes can cross-contaminate positional arguments and produce misleading
failures. Run recipe health checks one at a time, especially recipes that pass
`"$@"` through `devenv shell -- ...`.

The main remaining gap is that some fuzz recipes still reflect an older
unified-query/API worldview and should be treated as diagnostic, not as a release
gate.

For CLI commands, prefer the maintained wrapper:

```bash
just cli <command> ...
```

Use `devenv shell -- <command>` directly only for non-CLI tools or explicit
debugging. External services are owned by the user's process-compose session;
routine LangNet recipes act as clients and readiness probes.

## Healthy Recipes

These were probed successfully:

- `just default`
- `just cli --help`
- `just cli-normalize --help`
- `just cli-plan --help`
- `just cli-plan-exec --help`
- `just cli-databuild --help`
- `just cli langs --output json`
- `just cli tools san --output json`
- `just cli doctor --output json`
- `just cli doctor --require-openai-key --output json`
- `just cli word-index --help`
- `just cli word-index sources --output json`
- `just cli translation-cache --help`
- `just cli translation-cache status --output json`
- `just cli entry-analyze --help`
- `just cli lookup --help`
- `just parse cdsl san agni mw`
- `just triples-dump lat lupi gaffiot`
- `just triples-dump san kṛṣṇa dico`
- `just cli index --help`
- `just cli index status`
- `just diogenes-parse --help lupus`
- `just triples-dump --help lupus`
- `just cli triples-dump lat lupus gaffiot --no-cache --predicate gloss --max-triples 1`
- `just cli triples-dump san dharma dico --no-cache --predicate gloss --max-triples 1`
- `just parse --help lat lupus`
- `just autobot --help`
- `just autobot fuzz list`
- `just autobot fuzz run --help`
- `just autobot fuzz run --tool cdsl --action lookup --lang san --words agni --validate --mode tool --save examples/debug/fuzz_results_audit`
- `just translate-lex --help`
- `just translate-lex --dry-run --limit 1 --mode latin`
- `just translate-lex --dry-run --limit 1 --mode sanskrit`
- `just benchmark`
- Legacy sketch-reading recipes were removed during the `codesketch/`
  retirement audit. Runtime and verification recipes now target `src/`
  implementations directly.
- Routine CLI and dev-tool recipes now use wrapper scripts instead of variadic
  `devenv shell` forwarding.
- `just lint-all`
- `just test-all`
- `just test-fast`

## Not Routine Gates

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

The wrappers now use `.justscripts/run-langnet-cli`, which runs the devenv
entrypoint directly when available. This keeps `--help`, subcommands, Unicode
queries, and positional arguments unchanged.

### Fixed: Routine Dev Recipe Argument Routing

Routine test, lint, typecheck, benchmark, autobot, translation dry-run, parse,
and triples-dump recipes no longer pass variadic arguments directly through
`devenv shell -- ... "$@"`. Test and tooling recipes use
`.justscripts/run-dev-tool`; CLI helper recipes use `.justscripts/run-langnet-cli`.
This keeps process-compose service ownership separate from CLI/client checks.

### Operational Caveat: Sequential Devenv Recipe Checks

Recipes that invoke `devenv shell -- ... "$@"` work as isolated commands, but
they should not be launched concurrently during audits. A parallel probe can
make one recipe appear to receive another recipe's positional arguments, which
turns recipe-health output into noise. This is a tooling/recipe-audit caveat,
not evidence that the isolated recipe is broken.

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

Translated DICO/Gaffiot entries are projected through `encounter` when
translation cache rows match. Source French evidence remains visible through
`triples-dump`; derived English translation witnesses are part of the reduction
path, not replacements for source triples.

Source-language DICO/Gaffiot entries are now locally resolvable in
`triples-dump`; cache-backed translations are projected through `encounter`.

`encounter --translation-mode auto` can explicitly populate missing
DICO/Gaffiot translations through OpenRouter and then display them. This is
networked and should stay opt-in; cache-only mode is the routine inspection
path. The default translation model is `openai:google/gemini-2.5-flash`, with
`openai:deepseek/deepseek-v4-flash` as the default fallback.

`triples-dump` now supports `--predicate`, `--subject-prefix`, and `--max-triples` so evidence inspection can focus on reducer-relevant triples.

### Remaining: Fuzz Harness Semantics

`just fuzz-tools` is useful for parser smoke checks when local tool dependencies are available. `fuzz-query` and `fuzz-compare` are legacy until the project has a supported unified query surface again.

## Recommendation

Keep `just lint-all`, `just test-fast`, CLI help smoke tests, and fixture-backed claim tests as the stabilization gate. Treat fuzz recipes as manual diagnostics until their target model is updated to CLI-first semantics.
