# List available just commands
default:
    just -l

# Kill zombie diogenes processes (loop mode)
langnet-dg-reaper:
    python3 -m langnet.diogenes.cli_util

# One-shot zombie reap
reap:
    python3 -m langnet.diogenes.cli_util reap --once

# Run the test suite
test:
    nose2 -s tests --config tests/nose2.cfg

# Format code with ruff
ruff-format:
    ruff format src/ tests/

# Lint code with ruff
ruff-check *args:
    ruff check {{ args }}

# Type check with mypy
typecheck:
    ty check

# Run arbitrary command in devenv shell
devenv-bash +ARGS:
    devenv shell bash -- -c '{{ ARGS }}'

# Build CDSL dictionary (dict should be AP90 or MW)
# build_cdsl dict batch_size="1000":
#     LANGNET_LOG_LEVEL=INFO python3 -m langnet.cologne.load_cdsl --batch-size {{ batch_size }} --force --workers 4 {{ dict }}
