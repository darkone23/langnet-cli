"""Warm langnet-cli HTTP/JSON server (loopback only).

Exposes `app` for `uvicorn langnet.asgi:app` (see devenv `uvicorn-run`).
Accepted plan: HOL-199 / docs/plans/active/infra/warm-cli-server-http-json.md.

- `POST /api/cli`: argv passthrough for the webapp-used CLI surfaces,
  strict allowlist on `args[0:2]`, executed in-process via CliRunner so the
  response is the JSON the CLI would print (zero semantic drift).
- `GET /api/health`: readiness probe for the compose slot / autobot checks.
- `GET /api/langs`: convenience floor probe through the same path.

No auth/TLS/public exposure: loopback service, same trust domain as the
webapp process. Provider keys come from the slot environment, exactly as
the CLI subprocess would receive them.
"""

from __future__ import annotations

import asyncio
import json
import os
import threading
import time
from dataclasses import dataclass
from importlib import metadata
from typing import Any

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

# Webapp-used CLI surfaces (webapp/src/lib/server/langnet-cli.ts, reader-cli.ts).
# Keep in sync: tests/test_asgi_server.py guards exhaustiveness against the
# webapp sources.
ALLOWED_SURFACES = frozenset(
    {
        "encounter",
        "encounter-briefing",
        "word-index",
        "paradigm",
        "word-of-day",
        "motd-pool",
        "translation-cache",
        "lookup",
        "reader",
        "langs",
    }
)

CLI_GROUP_TOKEN = "cli"
MIN_ARGS = 2
MAX_ARGS = 64
MAX_BODY_BYTES = 8 * 1024 * 1024
DEFAULT_DEADLINE_SECONDS = 60.0
MAX_DEADLINE_SECONDS = 120.0

CONCURRENCY_ENV = "LANGNET_SERVER_MAX_CONCURRENCY"
DEFAULT_CONCURRENCY = 2
MIN_CONCURRENCY = 1
MAX_CONCURRENCY = 8

_CONTROL_CHAR_MIN_ORD = 32
_CONTROL_CHAR_MAX_ORD = 127


def max_concurrency_from_env() -> int:
    """Worker cap from env; default 2, clamped to 1..8.

    Raising the cap beyond 2 is gated on the thread-safety audit of
    langnet.cli module globals (HOL-199 decision).
    """
    raw = os.environ.get(CONCURRENCY_ENV)
    if raw is None:
        return DEFAULT_CONCURRENCY
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_CONCURRENCY
    return max(MIN_CONCURRENCY, min(MAX_CONCURRENCY, value))


def deadline_seconds(timeout_ms: float | int | None) -> float:
    if timeout_ms is None:
        return DEFAULT_DEADLINE_SECONDS
    return min(float(timeout_ms) / 1000.0, MAX_DEADLINE_SECONDS)


@dataclass(frozen=True)
class CliResult:
    status_code: int
    body: dict[str, Any]


class ServerRuntime:
    """Per-process server state: worker semaphore + shared locks."""

    def __init__(self, max_concurrency: int | None = None) -> None:
        self.max_concurrency = (
            max_concurrency if max_concurrency is not None else max_concurrency_from_env()
        )
        self.semaphore = asyncio.Semaphore(self.max_concurrency)
        self.translation_cache_lock = threading.Lock()
        self.started_at = time.monotonic()


_DEFAULT_RUNTIME: ServerRuntime | None = None


def get_default_runtime() -> ServerRuntime:
    global _DEFAULT_RUNTIME  # noqa: PLW0603
    if _DEFAULT_RUNTIME is None:
        _DEFAULT_RUNTIME = ServerRuntime()
    return _DEFAULT_RUNTIME


def reset_default_runtime() -> None:
    """Rebuild runtime state on next use (picks up env changes)."""
    global _DEFAULT_RUNTIME  # noqa: PLW0603
    _DEFAULT_RUNTIME = None


def run_cli_command(args: list[str], stdin: str | None) -> tuple[int, str]:
    """Invoke the CLI in-process. `args` excludes the leading `cli` token."""
    from click.testing import CliRunner  # noqa: PLC0415

    from langnet.cli import main  # noqa: PLC0415

    runner = CliRunner()
    result = runner.invoke(main, args, input=stdin, catch_exceptions=True)
    return result.exit_code, result.output


def run_cli_command_serialized(
    runtime: ServerRuntime, args: list[str], stdin: str | None
) -> CliResult:
    """Thread-side CLI execution: CLI argv passthrough + cache-writer lock."""
    cli_args = args[1:]
    if args[1] == "translation-cache":
        # SQLite writer discipline: serialize cache-mutating calls process-wide.
        with runtime.translation_cache_lock:
            exit_code, stdout = run_cli_command(cli_args, stdin)
    else:
        exit_code, stdout = run_cli_command(cli_args, stdin)
    return _cli_result_to_response(exit_code, stdout)


async def execute_cli_request(
    runtime: ServerRuntime,
    args: list[str],
    stdin: str | None,
    timeout_ms: float | int | None,
) -> CliResult:
    error = validate_cli_args(args)
    if error is not None:
        return CliResult(400, {"error": error})

    deadline = deadline_seconds(timeout_ms)
    async with runtime.semaphore:
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(run_cli_command_serialized, runtime, args, stdin),
                timeout=deadline,
            )
        except TimeoutError:
            # Cooperative cancellation: the thread is not killed mid-call; the
            # late result is discarded and the worker slot is released.
            return CliResult(
                504,
                {"error": f"langnet-cli command exceeded {deadline:.0f}s deadline"},
            )


def _validate_cli_request_body(body: dict[str, Any]) -> str | None:
    error = validate_cli_args(body.get("args"))
    if error is not None:
        return error

    stdin = body.get("stdin")
    if stdin is not None and not isinstance(stdin, str):
        return "stdin must be a string or null"

    timeout_ms = body.get("timeoutMs")
    if timeout_ms is not None and not isinstance(timeout_ms, (int, float)):
        return "timeoutMs must be a number or null"
    return None


def _forbidden_arg_error(args: list[str]) -> str | None:
    for arg in args:
        if not isinstance(arg, str):
            continue
        if any(
            ord(char) < _CONTROL_CHAR_MIN_ORD or ord(char) == _CONTROL_CHAR_MAX_ORD for char in arg
        ):
            return "args must not contain control characters"
        if arg == "--":
            return "positional escape '--' is not allowed"
        if arg == "--help":
            return "--help is not allowed over the server transport"
    return None


def validate_cli_args(args: Any) -> str | None:
    if not isinstance(args, list):
        return "args must be a list of strings"
    if len(args) < MIN_ARGS or len(args) > MAX_ARGS:
        return f"args must contain {MIN_ARGS}..{MAX_ARGS} entries"
    if not all(isinstance(arg, str) for arg in args):
        return "args must be a list of strings"
    if args[0] != CLI_GROUP_TOKEN:
        return f"args must start with the '{CLI_GROUP_TOKEN}' group"
    if args[1] not in ALLOWED_SURFACES:
        return f"cli surface '{args[1]}' is not allowed"
    return _forbidden_arg_error(args)


def _extract_json_object(stdout: str) -> dict[str, Any] | None:
    start = stdout.find("{")
    end = stdout.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        payload = json.loads(stdout[start : end + 1])
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _cli_result_to_response(exit_code: int, stdout: str) -> CliResult:
    payload = _extract_json_object(stdout)
    if exit_code == 0:
        if payload is not None:
            return CliResult(200, payload)
        return CliResult(502, {"error": stdout.strip() or "langnet-cli produced no JSON"})
    error_text = stdout.strip()
    if not error_text:
        error_text = "langnet-cli command failed"
    return CliResult(502, {"error": error_text})


def _error_response(status_code: int, message: str) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status_code)


async def run_cli_endpoint(request: Request) -> JSONResponse:
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > MAX_BODY_BYTES:
        return _error_response(413, "request body too large")

    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return _error_response(400, "request body must be JSON")

    if not isinstance(body, dict):
        return _error_response(400, "request body must be a JSON object")

    error = _validate_cli_request_body(body)
    if error is not None:
        return _error_response(400, error)

    args = body["args"]
    stdin: str | None = body.get("stdin")
    timeout_ms: float | int | None = body.get("timeoutMs")

    result = await execute_cli_request(get_default_runtime(), args, stdin, timeout_ms)
    return JSONResponse(result.body, status_code=result.status_code)


def _server_version() -> str:
    try:
        return metadata.version("langnet-cli")
    except metadata.PackageNotFoundError:
        return "unknown"


async def health_endpoint(request: Request) -> JSONResponse:
    runtime = get_default_runtime()
    return JSONResponse(
        {
            "status": "ok",
            "version": _server_version(),
            "uptime_seconds": int(time.monotonic() - runtime.started_at),
            "workers": runtime.max_concurrency,
        }
    )


async def langs_endpoint(request: Request) -> JSONResponse:
    result = await execute_cli_request(
        get_default_runtime(), ["cli", "langs", "--output", "json"], None, None
    )
    return JSONResponse(result.body, status_code=result.status_code)


app = Starlette(
    routes=[
        Route("/api/health", health_endpoint, methods=["GET"]),
        Route("/api/cli", run_cli_endpoint, methods=["POST"]),
        Route("/api/langs", langs_endpoint, methods=["GET"]),
    ]
)
