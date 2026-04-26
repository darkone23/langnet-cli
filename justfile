# List available just commands
default:
    just -l

# run langnet-cli tool
cli *args:
    devenv shell -- bash -c 'langnet-cli "$@"' _ {{ args }}

# Convenience wrappers for click subcommands
cli-normalize *args:
    devenv shell -- bash -c 'langnet-cli normalize "$@"' _ {{ args }}

cli-plan *args:
    devenv shell -- bash -c 'langnet-cli plan "$@"' _ {{ args }}

cli-plan-exec *args:
    devenv shell -- bash -c 'langnet-cli plan-exec "$@"' _ {{ args }}

cli-databuild *args:
    devenv shell -- bash -c 'langnet-cli databuild "$@"' _ {{ args }}

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
    devenv shell -- nose2 -s tests --config tests/nose2.cfg

# nose2 -s tests --config tests/nose2.cfg <...>
test *args:
    devenv shell -- nose2 -s tests --config tests/nose2.cfg {{ args }}

# Run all tests including benchmarks (use 'benchmark' for benchmarks only)
test-fast:
    devenv shell -- nose2 -s tests --config tests/nose2.cfg

# Run performance benchmarks only
benchmark:
    devenv shell -- python -m unittest tests.benchmarks.test_performance -v

# ⚠ DESTRUCTIVE: Remove runtime caches (deletes all files in data/cache)
clean-cache:
    rm -rf data/cache
    mkdir -p data/cache

# Format code with ruff (supports --check, --diff, etc.)
ruff-format *args:
    devenv shell -- ruff format src/ tests/ ./.justscripts/ {{ args }}

# Lint code with ruff
ruff-check *args:
    devenv shell -- ruff check src/ tests/ ./.justscripts {{ args }}

# Type check with ty
typecheck *args:
    devenv shell -- ty check src/ tests/ ./.justscripts {{ args }}

# project level automation tool
autobot *args:
    devenv shell -- python3 .justscripts/autobot.py {{ args }}

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

# Read V1 codesketch implementations
read-codesketch-diogenes:
    cat ./codesketch/src/langnet/diogenes/core.py

read-codesketch-whitakers:
    cat ./codesketch/src/langnet/whitakers_words/core.py

read-codesketch-cltk:
    cat ./codesketch/src/langnet/classics_toolkit/core.py

# Parse Diogenes HTML and dump the raw parsed JSON (pre-triples). Optional endpoint override.
diogenes-parse lang word endpoint="":
    devenv shell -- bash -c 'langnet-cli parse diogenes "$@"' _ "{{lang}}" "{{word}}" --opt "{{endpoint}}" --no-normalize --format json

# Generic parser helper: tool = diogenes|whitakers. Fourth arg = endpoint (dio) or binary (whitakers).
parse tool lang word opt="":
    devenv shell -- bash -c 'langnet-cli parse "$@"' _ "{{tool}}" "{{lang}}" "{{word}}" --opt "{{opt}}" --no-normalize --format json

# Dump tool claims/triples for a word (Latin) with no stubs/no cache. Optional tool filter (exact prefix), use "all" to run everything.
triples-dump lang word tool="all":
    devenv shell -- bash -c 'langnet-cli triples-dump "$@"' _ "{{lang}}" "{{word}}" "{{tool}}" --no-cache

# Translate sample lexicon rows (French -> English) using aisuite/OpenRouter.
translate-lex *opts:
    devenv shell -- python3 ./.justscripts/lex_translation_demo.py {{ opts }}
