# List available just commands
default:
    just -l

# run langnet-cli tool
cli *args:
    langnet-cli {{ args }}

cache-clear:
    just cli cache-clear
    
# Kill zombie diogenes processes (loop mode)
langnet-dg-reaper:
    python3 -m langnet.diogenes.cli_util

# restart uvicorn server
restart-server:
    just autobot server restart
    just autobot server verify
    just cli cache-clear
    
# run ruff & ty
lint-all:
    just ruff-format
    just ruff-check
    just typecheck

# One-shot zombie reap
reap:
    python3 -m langnet.diogenes.cli_util reap --once

# Run the test suite
test-all:
    nose2 -s tests --config tests/nose2.cfg

# nose2 -s tests --config tests/nose2.cfg <...>
test *args:
    nose2 -s tests --config tests/nose2.cfg {{ args }}

# Format code with ruff
ruff-format:
    ruff format src/ tests/ ./.justscripts/

# Lint code with ruff
ruff-check *args:
    ruff check {{ args }}

# Type check with ty
typecheck *args:
    ty check {{ args }}

# # Run arbitrary command in devenv shell
# devenv-bash +ARGS:
#     devenv shell bash -- -c '{{ ARGS }}'

# Build CDSL dictionary (dict should be AP90 or MW)
# build_cdsl dict batch_size="1000":
#     LANGNET_LOG_LEVEL=INFO python3 -m langnet.cologne.load_cdsl --batch-size {{ batch_size }} --force --workers 4 {{ dict }}

# project level automation tool
autobot *args:
    python3 .justscripts/autobot.py {{ args }}
