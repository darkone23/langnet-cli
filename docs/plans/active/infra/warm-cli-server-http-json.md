# Warm langnet-cli backend: localhost HTTP/JSON server

Plan for the HOL-195 latency program, story 4 (biggest win).
Tracked as [HOL-199]; parent program [HOL-195]; measured baseline in [HOL-193].

Status: accepted (HOL-199 confirmation `c5b04543`, 2026-09-21); implementation
in flight (S4a). Written 2026-09-21 by Tech VP.

Worker concurrency env: `LANGNET_SERVER_MAX_CONCURRENCY` (default 2, clamp
1..8) — the name agreed at implementation time; supersedes the
`LANGNET_SERVER_WORKERS` spelling used in earlier drafts below.

@architect reviewed the shape; @coder implements after board acceptance;
@sleuth owns the thread-safety audit gate before workers > 2.

## Why

Every webapp API call pays a ~1.0s floor before any backend work: the
SvelteKit server spawns `just -> bash -> fresh Python` per request
(`webapp/src/lib/server/langnet-cli.ts`); interpreter + imports dominate
(`just cli langs` = 1.05s with no backend work). Learner pages stack 2-4
calls (encounter + briefing + motd), so the floor compounds into the
board-reported 15s waits on the slower orion host, and every CLTK-backed
Greek call additionally re-imports and re-loads CLTK per process
(~3.8s every time; story 3 coordinates).

A persistent warm server removes the per-request process cost. The CLI
stays the authoritative surface and the permanent fallback.

## Goals

- p50 < 200ms via server for a cached Latin encounter (vs ~1.2s subprocess).
- Zero semantic drift: server responses are byte-equivalent to what the
  CLI prints for the same argv.
- CLI unchanged and green; subprocess transport stays and always works.
- Rollback is an env flag, not a code rollback.
- No new dependencies: starlette + uvicorn + httpx are already pinned
  in pyproject/poetry (0.52.1 / 0.40.0 / 0.27.2); fastapi is NOT added.

## Non-goals

- No gRPC (decided in HOL-199: contract is already JSON; single-household
  service; upgrade path documented, not built).
- No public exposure, no TLS, no auth layer: loopback-only service, same
  trust domain as the webapp process on orion.
- No rewrite of CLI internals; no typed re-implementation of argv
  building on the Python side.
- No multi-host story: orion is the only deployment target.

## Decisions (record)

1. **HTTP/JSON over loopback**, uvicorn on 127.0.0.1:8000. Matches the
   commented `langnet_cli` slot in `langnet-tools/process-compose.tmpl.yaml`
   and the `.justscripts/server_commands.py` expectations
   (`/api/health` on port 8000).
2. **Argv passthrough with an allowlist**, not typed mirror endpoints.
   The webapp already builds exact CLI argv (single source of truth,
   covered by webapp tests). Typed endpoints would duplicate that mapping
   in Python and drift. The server validates `args` against a prefix
   allowlist instead.
3. **In-process invocation via `click.testing.CliRunner`** invoking
   `langnet.cli:main` with the same argv and stdin. The command body runs
   exactly as today (including `--output json` stdout emit); the server
   parses the captured stdout JSON and returns it as the HTTP body.
   Refactoring 15k lines of click code into importable service functions
   is rejected for now: too much blast radius for this story; can be
   revisited per-surface later if profiling ever shows the
   serialize/parse hop matters (payloads are small; it will not).
4. **Flag-gated webapp transport with subprocess fallback.**
   `LANGNET_SERVER_URL` set → try HTTP first; any transport error,
   non-200, or timeout → log (rate-limited) and fall back to the existing
   subprocess path. Unset → current behavior, byte-for-byte.

## Architecture

### New module: `src/langnet/asgi.py` (~250 lines with tests separate)

- `app` (starlette), bound by uvicorn to `127.0.0.1:8000`
  (`devenv.nix` `uvicorn-run` recipe already points at
  `uvicorn langnet.asgi:app`).

Endpoints:

| Endpoint   | Method | Behavior |
| ---------- | ------ | -------- |
| `/api/cli` | POST   | Body `{"args": [...], "stdin": str\|null, "timeoutMs": int\|null}`. Runs the CLI command in-process, returns the exact JSON payload the CLI would print. |
| `/api/health` | GET | `{"status":"ok","version":...,"uptime_seconds":N,"workers":K}` for the compose readiness probe. |
| `/api/langs` | GET | Convenience floor probe: runs `cli langs --output json` through the same path. |

### `/api/cli` request validation (allowlist)

- `args` must be a list of 2..64 strings, no NUL/newline/control chars.
- `args[0:2]` must prefix-match the allowlist (webapp-used surfaces):
  - `cli encounter`, `cli encounter-briefing`, `cli word-index`,
    `cli paradigm`, `cli word-of-day`, `cli motd-pool`,
    `cli translation-cache`, `cli lookup`, `cli reader`, `cli langs`
- Reject: `--help`, a bare `--` (positional escape), and any arg
  containing control characters. Unknown flags inside an allowlisted
  command still flow to click and fail exactly as they do today.
- Body cap 8MB → 413.
- Violations → 400 with `{"error": ...}`.

Failure mapping:

- Command exits nonzero (ClickException, CLI guard errors) → 502 with
  `{"error": <stderr/exception text>}` (the webapp's
  `errorMessageFromPayload` path keeps working).
- Deadline exceeded → 504. Deadline = `min(timeoutMs ?? 60000, 120000)`.
  Threads are not killed mid-call (cooperative cancellation): the late
  result is discarded, the S1 provider timeout (45s) and diogenes client
  timeouts bound how long a runaway call actually occupies its worker.

### Concurrency model

- Handlers are async; CLI work runs on a thread pool via
  `anyio.to_thread.run_sync` gated by a bounded semaphore:
  `LANGNET_SERVER_WORKERS` (default **2**, clamp 1..8).
- Phase-1 thread-safety guardrails:
  - A process-level lock serializes `cli translation-cache` calls
    (SQLite writer discipline).
  - CLTK analyzer construction goes through a double-checked lock
    (story 3 formalizes the cache; the server must not race its init).
  - Diogenes/sanskrit-heritage access is unchanged: the CLI already talks
    to persistent servers (diogenes :8888, heritage :48080), which the
    webapp hits concurrently today via subprocesses.
- Raising workers beyond 2 is gated on the @sleuth thread-safety audit of
  `langnet.cli` module globals (story 2's import diet lands first, which
  shrinks that audit surface).

### Environment and secrets

- The server runs inside devenv exactly like the CLI
  (`cd langnet-cli && devenv shell uvicorn-run` from the
  `langnet-tools` justfile recipe `langnet-cli-server`), so `PYTHONPATH`
  (repo root, `src/`, `vendor/langnet-spec/generated/python`) matches
  `.justscripts/run-langnet-cli`.
- Provider keys for populate/auto paths come from the slot environment on
  orion (SRE-managed env file; secrets never in the repo, per house rule).
  The webapp currently passes its own env into subprocesses; with the
  server, key management moves to the compose slot env — one place, same
  machine, audited by the SRE seat.

### Restart hygiene

- `langnet-tools/process-compose.tmpl.yaml`: uncomment the existing
  `langnet_cli` slot verbatim — `restart: always`,
  `depends_on` diogenes + sanskrit_heritage healthy, readiness probe
  `GET /api/health` on 127.0.0.1:8000 (initial delay 20s covers imports).
- Repo recipes already fit: `just restart-server`
  (autobot server restart + verify) and the autobot health/restart
  commands target port 8000 `/api/health` — they become the runbook verbs.
- Reload-on-code-change is explicitly NOT enabled in production;
  process restart is the reload path (repo gotcha: cached modules).

## Webapp transport (flag-gated, fallback)

`webapp/src/lib/server/langnet-cli.ts` (and the same pattern later in
`reader-cli.ts`):

- `const serverUrl = process.env.LANGNET_SERVER_URL;` — absent → today's
  behavior untouched.
- `runJsonCommand(args, timeoutMs, options)`: when the server URL is set
  and `args` passes the same client-side allowlist, POST
  `{args, stdin, timeoutMs}` with the existing `AbortSignal`/timeout
  semantics; on transport failure, non-200, or timeout, log once per 60s
  (rate-limited, no spam) and fall back to `runJsonCommandUnlocked`.
- The existing promise queue (`queued: true`) stays in server mode too:
  cache-mutating calls (translation-cache clear, briefing populate) keep
  their ordering guarantee. `queued: false` calls go straight through —
  the server's worker pool replaces process parallelism.
- Response mappers (`mapCliPayload`, `mapWordIndexPayload`, ...) are
  untouched: the HTTP body is the same JSON the subprocess printed.

## Rollout (matches HOL-199 steps)

1. **This design doc** (todo/infra → active/ when implementation starts).
2. **Implement app + tests** on a branch: `src/langnet/asgi.py`,
   `tests/test_asgi_server.py`, webapp transport flag — TDD, tests
   written first.
3. **Enable the compose slot on orion** (SRE-coordinated; the slot YAML
   exists, this is uncomment + `just compose-restart` + health check, plus
   slot env for provider keys).
4. **Flip the webapp flag** (`LANGNET_SERVER_URL=http://127.0.0.1:8000`
   in the slot env) and measure with the extended perf probe.

### Rollback

- Webapp: unset `LANGNET_SERVER_URL` (or compose slot down) — subprocess
  path resumes; no code rollback needed. The fallback makes even a
  half-dead server non-fatal.
- Server: `just compose down langnet_cli` (or slot comment-out) +
  `compose-restart`.

## Tests and verification

`tests/test_asgi_server.py` (nose2 + starlette `TestClient`; httpx is
already installed), TDD order:

1. Health endpoint returns `ok` with worker count.
2. Allowlist: `["cli","databuild",...]` and `["os",...]` → 400.
3. Arg guard: control characters / `--` escape → 400.
4. Contract equality: server `/api/cli` payload is JSON-equal to CLI
   stdout for the same argv — fixture-guarded per the repo pattern
   (skip when the corpus/fixture is absent, never fail on a bare
   checkout). Surfaces: `langs`, `word-index browse lat --limit 12`,
   `paradigm lat amo --kind conjugation`, `encounter lat arma all
   --translation-mode cache --cache-policy read-only`.
5. Stdin passthrough: `encounter-briefing --input-json - --cache-only`
   with a canned encounter payload.
6. Deadline: monkeypatched slow command → 504, semaphore never leaks.
7. Worker gate: two concurrent `/api/cli` calls overlap (timing assert
   with a stubbed runner, no real backend needed).

Measurement: extend the HOL-195 probe with a server mode
(`just perf-probe-server`): same surfaces, POSTed to `/api/cli`, same
markdown table, run before/after flag flip on orion.

Acceptance (from HOL-199, restated):

- p50 < 200ms via server for a cached Latin encounter.
- CLI unchanged: `just test-fast` green, `just lint-all` clean.
- Rollback verified with the flag off (subprocess timings reproduced).

## Risks and mitigations

| Risk | Mitigation |
| ---- | ---------- |
| CLI module globals not thread-safe | Default 2 workers; lock on translation-cache writes + CLTK init; @sleuth audit gates raising the cap |
| Resident memory on orion (CLTK models, reader catalogs) | SRE confirms host headroom before enabling the slot; server is one process, not per-request copies |
| Port 8000 collision / stale uvicorn | Slot owns the port; `just restart-server` is the only sanctioned restart verb (pkill + health wait) |
| Provider key now in server env | SRE-managed slot env file; never in repo/logs/comments (house rule) |
| Server down + fallback silent | Fallback logs rate-limited; `/api/health` probe restarts the slot automatically |
| Payload drift between CLI and server | Contract-equality tests (§4) fail CI on drift |

## Open items

- Exact env var name for the OpenRouter key in the slot env (SRE step).
- Optional later: msgpack responses (webapp already has a msgpack
  response util) — noted, not built.
- Optional later: per-surface import of service functions to skip the
  stdout capture hop — only if profiling ever justifies it.
