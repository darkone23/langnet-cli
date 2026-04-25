# List available just commands
default:
    just -l

# run langnet-cli tool
cli *args:
    # Use devenv shell to ensure langnet-cli env is active.
    devenv shell langnet-cli -- {{ args }}

# Convenience wrappers for click subcommands
cli-normalize *args:
    devenv shell langnet-cli -- normalize {{ args }}

cli-plan *args:
    devenv shell langnet-cli -- plan {{ args }}

cli-plan-exec *args:
    devenv shell langnet-cli -- plan-exec {{ args }}

cli-databuild *args:
    devenv shell langnet-cli -- databuild {{ args }}

# cache-clear:
#     just cli cache-clear
codegen:
    cd vendor/langnet-spec && devenv shell just -- generate-python
    
# Kill zombie diogenes processes (loop mode)
langnet-dg-reaper:
    just autobot diogenes reap

# restart uvicorn server
restart-server:
    just autobot server restart
    just autobot server verify
    # just cli cache-clear
    
# run ruff & ty
lint-all:
    just ruff-format
    just ruff-check
    just typecheck

# One-shot zombie reap
reap:
    just autobot diogenes reap --once

# Run the test suite
test-all:
    nose2 -s tests --config tests/nose2.cfg

# nose2 -s tests --config tests/nose2.cfg <...>
test *args:
    nose2 -s tests --config tests/nose2.cfg {{ args }}

# Fast unit/contract tests (runs all tests - nose2 doesn't support attribute filtering)
test-fast:
    nose2 -s tests --config tests/nose2.cfg

# Remove runtime caches (safe to delete)
clean-cache:
    rm -rf data/cache
    mkdir -p data/cache

# Format code with ruff
ruff-format:
    ruff format src/ tests/ ./.justscripts/

# Lint code with ruff
ruff-check *args:
    ruff check src/ tests/ ./.justscripts {{ args }}

# Type check with ty
typecheck *args:
    ty check src/ tests/ ./.justscripts {{ args }}

# # Run arbitrary command in devenv shell
# devenv-bash +ARGS:
#     devenv shell bash -- -c '{{ ARGS }}'

# Build CDSL dictionary (dict should be AP90 or MW)
# build_cdsl dict batch_size="1000":
#     LANGNET_LOG_LEVEL=INFO python3 -m langnet.cologne.load_cdsl --batch-size {{ batch_size }} --force --workers 4 {{ dict }}

# project level automation tool
autobot *args:
    python3 .justscripts/autobot.py {{ args }}

# Run backend tool fuzzing (only /api/tool/* endpoints)
fuzz-tools:
    just autobot fuzz run --mode tool --validate --save examples/debug/fuzz_results

# Run unified query fuzzing (only /api/q endpoint)
fuzz-query:
    just autobot fuzz run --mode query --validate --save examples/debug/fuzz_results_query

# Run tool + query comparison (hits both endpoints)
fuzz-compare:
    just autobot fuzz run --mode compare --validate --save examples/debug/fuzz_results_compare

# Legacy alias for tool fuzzing
fuzz-all:
    just fuzz-tools

read-codesketch-diogenes:
    cat ./codesketch/src/langnet/diogenes/core.py
    
read-codesketch-whitakers:
    cat ./codesketch/src/langnet/whitakers_words/core.py

read-codesketch-cltk:
    cat ./codesketch/src/langnet/classics_toolkit/core.py

# Parse Diogenes HTML and dump the raw parsed JSON (pre-triples). Optional endpoint override.
diogenes-parse lang word endpoint="":
    python3 ./.justscripts/diogenes_parse.py "{{lang}}" "{{word}}" "{{endpoint}}"

# Generic parser helper: tool = diogenes|whitakers. Fourth arg = endpoint (dio) or binary (whitakers).
parse tool lang word opt="":
    python3 ./.justscripts/tool_parse.py "{{tool}}" "{{lang}}" "{{word}}" --opt "{{opt}}" --no-normalize

# Dump tool claims/triples for a word (Latin) with no stubs/no cache. Optional tool filter (exact prefix), use "all" to run everything.
triples-dump lang word tool="all":
    python3 ./.justscripts/triples_dump.py "{{lang}}" "{{word}}" "{{tool}}"

# Translate sample lexicon rows (French -> English) using aisuite/OpenRouter.
translate-lex *opts:
    #!/usr/bin/env bash
    #
    source $HOME/.bashrc
    # Example: just translate-lex --db data/build/lex_gaffiot.duckdb --table entries_fr --limit 1 --headword agni
    python3 ./.justscripts/lex_translation_demo.py {{ opts }}
