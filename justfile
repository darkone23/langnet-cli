set positional-arguments

# List available just commands
default:
    just -l

# run langnet-cli tool
cli *args:
    bash ./.justscripts/run-langnet-cli "$@"

# Convenience wrappers for click subcommands
cli-normalize *args:
    bash ./.justscripts/run-langnet-cli normalize "$@"

cli-plan *args:
    bash ./.justscripts/run-langnet-cli plan "$@"

cli-plan-exec *args:
    bash ./.justscripts/run-langnet-cli plan-exec "$@"

cli-databuild *args:
    bash ./.justscripts/run-langnet-cli databuild "$@"

# Generate Python protobuf code from langnet-spec
codegen:
    cd vendor/langnet-spec && devenv shell -- just generate-python

# ⚠ DESTRUCTIVE: Kill zombie diogenes processes (loops indefinitely until stopped)
langnet-dg-reaper:
    just autobot diogenes reap

# ⚠ DESTRUCTIVE: Restart uvicorn server (kills existing server processes)
restart-server:
    just autobot server restart
    just autobot server verify

# run ruff & ty
lint-all:
    just ruff-format --check
    just ruff-check
    just typecheck

# ⚠ DESTRUCTIVE: One-shot zombie reap (kills stale diogenes processes)
reap:
    just autobot diogenes reap --once

# Run the test suite
test-all:
    bash ./.justscripts/run-dev-tool nose2 -s tests --config tests/nose2.cfg

# Stabilization loop for current learner/evidence work: focused tests, then full gates.
validate-stabilization:
    just test test_cdsl_triples test_wsu_extraction test_translation_projection test_cli_encounter_output
    just lint-all
    just test-fast

# nose2 -s tests --config tests/nose2.cfg <...>
test *args:
    bash ./.justscripts/run-dev-tool nose2 -s tests --config tests/nose2.cfg "$@"

# Run the fast nose2 suite. Use 'benchmark' for performance tests.
test-fast:
    bash ./.justscripts/run-dev-tool nose2 -s tests --config tests/nose2.cfg

# Restore tracked generated reader metadata into a rebuilt reader catalog.
reader-restore-generated-metadata catalog="data/build/reader/catalog.duckdb":
    just cli reader --catalog "{{catalog}}" sync-classifications --classification-csv data/generated/reader_classifications/2026-05-17/discovery/greek-generated-discovery-b50.csv --output json
    just cli reader --catalog "{{catalog}}" sync-classifications --classification-csv data/generated/reader_classifications/2026-05-17/discovery/latin-generated-discovery-b50.csv --merge --output json
    just cli reader --catalog "{{catalog}}" sync-classifications --classification-csv data/generated/reader_classifications/2026-05-17/discovery/sanskrit-generated-discovery.csv --merge --output json
    just cli reader --catalog "{{catalog}}" sync-classifications --classification-csv data/generated/reader_classifications/2026-06-01/discovery/sanskrit-pro-audit-generated.csv --merge --output json
    just cli reader --catalog "{{catalog}}" sync-classifications --classification-csv data/generated/reader_classifications/2026-05-17/discovery/audit-corrections-2026-05-17.csv --merge --output json
    just cli reader --catalog "{{catalog}}" prune-stale-classifications --output json
    just cli reader --catalog "{{catalog}}" sync-author-classifications --classification-csv data/generated/reader_classifications/2026-05-17/authors/full/grc-author-full-generated-v2-b10.csv --output json
    just cli reader --catalog "{{catalog}}" sync-author-classifications --classification-csv data/generated/reader_classifications/2026-05-17/authors/full/lat-author-full-generated-v2.csv --merge --output json
    just cli reader --catalog "{{catalog}}" sync-author-classifications --classification-csv data/generated/reader_classifications/2026-05-17/authors/full/san-author-full-generated-merged-b10.csv --merge --output json

# Run performance benchmarks only
benchmark:
    bash ./.justscripts/run-dev-tool python -m unittest tests.benchmarks.test_performance -v

# ⚠ DESTRUCTIVE: Remove runtime caches (deletes all files in data/cache)
clean-cache:
    rm -rf data/cache
    mkdir -p data/cache

# Format code with ruff (supports --check, --diff, etc.)
ruff-format *args:
    bash ./.justscripts/run-dev-tool ruff format src/ tests/ ./.justscripts/ "$@"

# Lint code with ruff
ruff-check *args:
    bash ./.justscripts/run-dev-tool ruff check src/ tests/ ./.justscripts "$@"

# Type check with ty
typecheck *args:
    bash ./.justscripts/run-dev-tool ty check src/ tests/ ./.justscripts "$@"

# project level automation tool
autobot *args:
    bash ./.justscripts/run-dev-tool python3 .justscripts/autobot.py "$@"

# Probe backend parser commands through the fuzz harness; requires local tool dependencies
fuzz-tools:
    just autobot fuzz run --mode tool --validate --save examples/debug/fuzz_results

# Legacy unified-query fuzz mode; currently expected to report unsupported query CLI
fuzz-query:
    just autobot fuzz run --mode query --validate --save examples/debug/fuzz_results_query

# Legacy comparison mode; useful only after a supported unified query surface exists
fuzz-compare:
    just autobot fuzz run --mode compare --validate --save examples/debug/fuzz_results_compare

# Legacy alias for tool fuzzing
fuzz-all:
    just fuzz-tools

# Parse Diogenes HTML and dump the raw parsed JSON (pre-triples). Optional endpoint override.
diogenes-parse lang word endpoint="":
    bash ./.justscripts/run-langnet-cli parse diogenes "$1" "$2" --opt "$3" --no-normalize --format json

# Generic parser helper: tool = diogenes|whitakers. Fourth arg = endpoint (dio) or binary (whitakers).
parse tool lang word opt="":
    bash ./.justscripts/run-langnet-cli parse "$1" "$2" "$3" --opt "$4" --no-normalize --format json

# Dump tool claims/triples for a word (Latin) with no stubs/no cache. Optional tool filter (exact prefix), use "all" to run everything.
triples-dump lang word tool="all":
    bash ./.justscripts/run-langnet-cli triples-dump "$1" "$2" "$3" --no-cache

# Translate sample lexicon rows (French -> English) using aisuite/OpenRouter.
translate-lex *opts:
    bash ./.justscripts/run-dev-tool python3 ./.justscripts/lex_translation_demo.py "$@"
