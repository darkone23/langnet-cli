default:
    just -l

langnet-dg-reaper:
    # kill zombie diogenes processes (loop mode)
    python3 -m langnet.diogenes.cli_util

reap:
    # one-shot zombie reap
    python3 -m langnet.diogenes.cli_util reap --once

test:
    nose2 -s tests --config tests/nose2.cfg

ruff:
    ruff format src/ tests/

typecheck:
    ty check

devenv-bash +ARGS:
    devenv shell bash -- -c '{{ ARGS }}'

build_cdsl dict batch_size="1000":
    # dict should be AP90 or MW
    LANGNET_LOG_LEVEL=INFO python3 -m langnet.cologne.load_cdsl --batch-size {{ batch_size }} --force --workers 4 {{ dict }}
