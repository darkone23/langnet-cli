default:
    just -l

sidecar:
    # kill zombie diogenes processes (loop mode)
    python3 -m langnet.diogenes.cli_util

reap:
    # one-shot zombie reap
    python3 -m langnet.diogenes.cli_util reap --once

test:
    nose2 -s tests

ruff:
    ruff format src/ tests/
