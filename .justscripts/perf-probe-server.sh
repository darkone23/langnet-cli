#!/usr/bin/env bash
# Repeatable warm-server performance probe (HOL-199 S4a). Read-only surfaces.
# Starts langnet.asgi with uvicorn on a loopback port, times each surface
# through POST /api/cli, and compares with the subprocess CLI transport.
# Output: a markdown timing table (median seconds).
#
# Usage: just perf-probe-server [runs]
# Env:   LANGNET_PROBE_PORT (default 8010; 8000 is the production slot port)
#        LANGNET_VENV_BIN (override venv bin dir, e.g. in git worktrees)
set -uo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

venv_bin="${LANGNET_VENV_BIN:-${repo_root}/.devenv/state/venv/bin}"
uvicorn="${venv_bin}/uvicorn"
cli="${venv_bin}/langnet-cli"
if [[ ! -x "${uvicorn}" || ! -x "${cli}" ]]; then
  echo "venv uvicorn/langnet-cli not found; run 'devenv shell -- true' first" >&2
  exit 1
fi
export PYTHONPATH="${repo_root}/src:${repo_root}/vendor/langnet-spec/generated/python${PYTHONPATH:+:${PYTHONPATH}}"

runs="${1:-10}"
port="${LANGNET_PROBE_PORT:-8010}"
base_url="http://127.0.0.1:${port}"
log_file="${repo_root}/tmp/perf-probe-server-uvicorn.log"
mkdir -p "${repo_root}/tmp"

surfaces=(
  "langs:langs --output json"
  "encounter-lat-all:encounter lat arma all --translation-mode cache --cache-policy read-only --output json"
  "encounter-lat-whitakers:encounter lat arma whitakers --translation-mode cache --cache-policy read-only --output json"
  "word-index-browse:word-index browse lat --limit 12 --output json"
  "paradigm-lat:paradigm lat amo --kind conjugation --output json"
)

json_for() {
  python3 -c 'import json, sys
print(json.dumps({"args": sys.argv[1:], "stdin": None, "timeoutMs": 120000}))' "$@"
}

median() {
  python3 -c 'import sys
xs = sorted(float(line) for line in sys.stdin if line.strip())
print(f"{xs[len(xs) // 2]:.3f}" if xs else "n/a")'
}

cleanup() {
  if [[ -n "${server_pid:-}" ]] && kill -0 "${server_pid}" 2>/dev/null; then
    kill "${server_pid}" 2>/dev/null
    wait "${server_pid}" 2>/dev/null
  fi
}
trap cleanup EXIT

echo "Starting uvicorn langnet.asgi:app on ${base_url} (log: ${log_file})" >&2
"${uvicorn}" langnet.asgi:app --host 127.0.0.1 --port "${port}" --log-level warning \
  >"${log_file}" 2>&1 &
server_pid=$!

healthy=0
for _ in $(seq 1 120); do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "${base_url}/api/health" || true)
  if [[ "${code}" == "200" ]]; then
    healthy=1
    break
  fi
  if ! kill -0 "${server_pid}" 2>/dev/null; then
    echo "uvicorn exited early; log tail:" >&2
    tail -5 "${log_file}" >&2
    exit 1
  fi
  sleep 1
done
if [[ "${healthy}" != "1" ]]; then
  echo "server never became healthy on ${base_url}" >&2
  exit 1
fi

echo "| surface | server median (s) | subprocess median (s) | runs |"
echo "| --- | --- | --- | --- |"
for entry in "${surfaces[@]}"; do
  name="${entry%%:*}"
  args="${entry#*:}"
  # shellcheck disable=SC2086
  request_body="$(json_for cli ${args})"

  warmup=$(curl -s -o /dev/null -w '%{http_code}' --max-time 130 -X POST \
    -H 'content-type: application/json' -d "${request_body}" \
    "${base_url}/api/cli" || true)
  if [[ "${warmup}" != "200" ]]; then
    printf '| %s | unavailable (HTTP %s) | unavailable | %s |\n' "${name}" "${warmup}" "${runs}"
    continue
  fi

  server_times=()
  for _ in $(seq 1 "${runs}"); do
    t=$(curl -s -o /dev/null -w '%{time_total}' --max-time 130 -X POST \
      -H 'content-type: application/json' -d "${request_body}" \
      "${base_url}/api/cli" || true)
    server_times+=("${t}")
  done
  server_median=$(printf '%s\n' "${server_times[@]}" | median)

  # shellcheck disable=SC2086
  if TIMEFORMAT='%R'; { time "${cli}" ${args} >/dev/null 2>&1; } 2>/dev/null; then
    subprocess_times=()
    for _ in $(seq 1 "${runs}"); do
      # shellcheck disable=SC2086
      t=$( { TIMEFORMAT='%R'; time "${cli}" ${args} >/dev/null 2>&1; } 2>&1 )
      subprocess_times+=("${t}")
    done
    subprocess_median=$(printf '%s\n' "${subprocess_times[@]}" | median)
  else
    subprocess_median="n/a"
  fi

  printf '| %s | %s | %s | %s |\n' "${name}" "${server_median}" "${subprocess_median}" "${runs}"
done
