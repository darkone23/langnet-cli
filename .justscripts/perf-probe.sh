#!/usr/bin/env bash
# Repeatable performance probe for the common learner surfaces (HOL-195).
# Read-only: every command runs in cache/off modes; no provider network calls.
# Runs each surface twice (warm page cache) and reports both wall times so
# cold vs warm is visible. Output: a markdown timing table.
set -uo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

cli="${repo_root}/.devenv/state/venv/bin/langnet-cli"
if [[ ! -x "${cli}" ]]; then
  echo "venv langnet-cli not found; run 'devenv shell -- true' first" >&2
  exit 1
fi
export PYTHONPATH="${repo_root}/src:${repo_root}/vendor/langnet-spec/generated/python${PYTHONPATH:+:${PYTHONPATH}}"

surfaces=(
  "floor:langs --output json"
  "encounter-lat-all:encounter lat arma all --translation-mode cache --output json"
  "encounter-san-all:encounter san dharma all --translation-mode cache --output json"
  "encounter-grc-all:encounter grc lo/gos all --translation-mode cache --output json"
  "word-index-browse:word-index browse lat --limit 12 --output json"
  "paradigm-lat:paradigm lat amo --kind conjugation --output json"
  "word-of-day-lat:word-of-day lat --count 3 --level beginner --dictionary all --translation-mode cache --candidate-source auto --timeout-ms 60000 --output json"
  "lookup-lat-all:lookup lat lupus --output json"
)

TIMEFORMAT='%R'
echo "| surface | run1 (s) | run2 warm (s) |"
echo "| --- | --- | --- |"
for entry in "${surfaces[@]}"; do
  name="${entry%%:*}"
  args="${entry#*:}"
  # shellcheck disable=SC2086
  t1=$( { time "${cli}" ${args} >/dev/null 2>&1; } 2>&1 )
  # shellcheck disable=SC2086
  t2=$( { time "${cli}" ${args} >/dev/null 2>&1; } 2>&1 )
  printf '| %s | %s | %s |\n' "${name}" "${t1}" "${t2}"
done
