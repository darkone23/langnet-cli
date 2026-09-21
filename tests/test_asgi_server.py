from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

import httpx
from starlette.testclient import TestClient

from langnet import asgi

REPO_ROOT = Path(__file__).resolve().parents[1]

# The webapp-used CLI surfaces (webapp/src/lib/server/langnet-cli.ts and
# reader-cli.ts). The server allowlist must accept exactly these prefixes.
WEBAPP_SERVER_SOURCES = [
    REPO_ROOT / "webapp/src/lib/server/langnet-cli.ts",
    REPO_ROOT / "webapp/src/lib/server/reader-cli.ts",
]


def _stub_runner(exit_code: int = 0, stdout: str = '{"query":"arma"}') -> mock.MagicMock:
    stub = mock.MagicMock(return_value=(exit_code, stdout))
    return stub


class AsgiServerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        asgi.reset_default_runtime()
        self.client = TestClient(asgi.app)

    def tearDown(self) -> None:
        asgi.reset_default_runtime()


class TestHealthEndpoint(AsgiServerTestCase):
    def test_health_returns_ok_with_worker_count_and_uptime(self) -> None:
        response = self.client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["workers"], 2)
        self.assertIsInstance(payload["version"], str)
        self.assertTrue(payload["version"])
        self.assertIsInstance(payload["uptime_seconds"], int)
        self.assertGreaterEqual(payload["uptime_seconds"], 0)

    def test_health_worker_count_follows_concurrency_env(self) -> None:
        with mock.patch.dict(os.environ, {"LANGNET_SERVER_MAX_CONCURRENCY": "4"}):
            asgi.reset_default_runtime()
            response = self.client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["workers"], 4)

    def test_concurrency_env_clamps_to_sane_bounds(self) -> None:
        with mock.patch.dict(os.environ, {"LANGNET_SERVER_MAX_CONCURRENCY": "99"}):
            self.assertEqual(asgi.max_concurrency_from_env(), 8)
        with mock.patch.dict(os.environ, {"LANGNET_SERVER_MAX_CONCURRENCY": "0"}):
            self.assertEqual(asgi.max_concurrency_from_env(), 1)
        with mock.patch.dict(os.environ, {"LANGNET_SERVER_MAX_CONCURRENCY": "junk"}):
            self.assertEqual(asgi.max_concurrency_from_env(), 2)
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("LANGNET_SERVER_MAX_CONCURRENCY", None)
            self.assertEqual(asgi.max_concurrency_from_env(), 2)


class TestCliEndpointAllowlist(AsgiServerTestCase):
    def post_args(self, args: object, **body_extra: object) -> httpx.Response:
        body: dict[str, object] = {"args": args}
        body.update(body_extra)
        return self.client.post("/api/cli", json=body)

    def test_accepts_allowlisted_surface(self) -> None:
        with mock.patch.object(asgi, "run_cli_command", return_value=(0, '{"langs":["lat"]}')):
            response = self.post_args(["cli", "langs", "--output", "json"])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"langs": ["lat"]})

    def test_runner_receives_args_without_leading_cli_token(self) -> None:
        with mock.patch.object(asgi, "run_cli_command", return_value=(0, "{}")) as runner:
            self.post_args(["cli", "langs", "--output", "json"])

        runner.assert_called_once()
        call = runner.call_args
        self.assertEqual(call.args[0], ["langs", "--output", "json"])

    def test_accepts_every_allowlisted_surface(self) -> None:
        for surface in sorted(asgi.ALLOWED_SURFACES):
            with self.subTest(surface=surface):
                with mock.patch.object(asgi, "run_cli_command", return_value=(0, "{}")):
                    response = self.post_args(["cli", surface, "x"])

                self.assertEqual(response.status_code, 200, surface)

    def test_rejects_non_allowlisted_surfaces(self) -> None:
        for args in (
            ["cli", "databuild", "reader"],
            ["cli", "learn", "practice"],
            ["os", "-c", "id"],
            ["bash", "-c", "id"],
            ["langnet-cli", "encounter", "lat", "arma"],
        ):
            with self.subTest(args=args):
                with mock.patch.object(asgi, "run_cli_command", return_value=(0, "{}")):
                    response = self.post_args(args)

                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.json())

    def test_rejects_missing_or_malformed_args(self) -> None:
        for body in ({}, {"args": "cli langs"}, {"args": [1, 2]}, {"args": []}):
            with self.subTest(body=body):
                response = self.client.post("/api/cli", json=body)
                self.assertEqual(response.status_code, 400)

    def test_rejects_too_many_args(self) -> None:
        response = self.post_args(["cli", "langs", *(f"--{i}" for i in range(64))])
        self.assertEqual(response.status_code, 400)

    def test_rejects_help_flag(self) -> None:
        response = self.post_args(["cli", "encounter", "--help"])
        self.assertEqual(response.status_code, 400)

    def test_rejects_positional_escape(self) -> None:
        response = self.post_args(["cli", "encounter", "lat", "--", "arma"])
        self.assertEqual(response.status_code, 400)

    def test_rejects_control_characters_in_args(self) -> None:
        for arg in ("lat\n--output", "arma\x00", "a\tb", "x\r\n"):
            with self.subTest(arg=arg):
                response = self.post_args(["cli", "encounter", arg])
                self.assertEqual(response.status_code, 400)

    def test_rejects_oversized_body(self) -> None:
        response = self.client.post(
            "/api/cli",
            json={"args": ["cli", "langs", "x" * (asgi.MAX_BODY_BYTES + 1024)]},
        )
        self.assertEqual(response.status_code, 413)

    def test_stdin_is_passed_through_to_runner(self) -> None:
        with mock.patch.object(
            asgi, "run_cli_command", return_value=(0, '{"cached":true}')
        ) as runner:
            response = self.post_args(
                ["cli", "encounter-briefing", "--cache-only"], stdin='{"query":"arma"}'
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(runner.call_args.args[1], '{"query":"arma"}')

    def test_nonzero_cli_exit_maps_to_502_with_error(self) -> None:
        with mock.patch.object(asgi, "run_cli_command", return_value=(1, "Error: no such word")):
            response = self.post_args(["cli", "encounter", "nosuchword"])

        self.assertEqual(response.status_code, 502)
        self.assertIn("no such word", response.json()["error"])

    def test_translation_cache_calls_are_serialized(self) -> None:
        runtime = asgi.ServerRuntime(max_concurrency=8)
        active = 0
        peak = 0
        guard = threading.Lock()

        def fake_run(args: list[str], stdin: str | None) -> tuple[int, str]:
            nonlocal active, peak
            with guard:
                active += 1
                peak = max(peak, active)
            time.sleep(0.05)
            with guard:
                active -= 1
            return 0, '{"cleared":true}'

        with mock.patch.object(asgi, "run_cli_command", fake_run):

            async def scenario() -> None:
                calls = [
                    asyncio.to_thread(
                        asgi.run_cli_command_serialized,
                        runtime,
                        ["cli", "translation-cache", "clear", "--yes"],
                        None,
                    )
                    for _ in range(4)
                ]
                await asyncio.gather(*calls)

            asyncio.run(scenario())

        self.assertEqual(peak, 1)


class TestCliEndpointDeadline(AsgiServerTestCase):
    def test_deadline_exceeded_maps_to_504(self) -> None:
        def slow_run(args: list[str], stdin: str | None) -> tuple[int, str]:
            time.sleep(2)
            return 0, '{"late":true}'

        with mock.patch.object(asgi, "run_cli_command", slow_run):
            response = self.client.post(
                "/api/cli", json={"args": ["cli", "langs"], "timeoutMs": 50}
            )

        self.assertEqual(response.status_code, 504)
        self.assertIn("error", response.json())

    def test_deadline_defaults_and_caps(self) -> None:
        # Accepted semantics: min(timeoutMs ?? 60000, 120000).
        self.assertEqual(asgi.deadline_seconds(None), 60.0)
        self.assertEqual(asgi.deadline_seconds(999_999), asgi.MAX_DEADLINE_SECONDS)
        self.assertEqual(asgi.deadline_seconds(1_500), 1.5)

    def test_semaphore_not_leaked_after_deadline(self) -> None:
        def slow_run(args: list[str], stdin: str | None) -> tuple[int, str]:
            time.sleep(2)
            return 0, "{}"

        runtime = asgi.ServerRuntime(max_concurrency=1)
        with mock.patch.object(asgi, "run_cli_command", slow_run):
            first = asyncio.run(asgi.execute_cli_request(runtime, ["cli", "langs"], None, 50))
            self.assertEqual(first.status_code, 504)

            after = asyncio.run(asgi.execute_cli_request(runtime, ["cli", "langs"], None, 5_000))
        # 200 proves the worker slot was released after the 504 cancellation
        # (a leaked semaphore would leave this call stuck until its deadline).
        self.assertEqual(after.status_code, 200)


class TestWorkerConcurrencyGate(AsgiServerTestCase):
    def _run_overlapping(self, max_concurrency: int, calls: int = 4) -> int:
        runtime = asgi.ServerRuntime(max_concurrency=max_concurrency)
        active = 0
        peak = 0
        guard = threading.Lock()

        def fake_run(args: list[str], stdin: str | None) -> tuple[int, str]:
            nonlocal active, peak
            with guard:
                active += 1
                peak = max(peak, active)
            time.sleep(0.08)
            with guard:
                active -= 1
            return 0, "{}"

        with mock.patch.object(asgi, "run_cli_command", fake_run):

            async def scenario() -> None:
                requests = [
                    asgi.execute_cli_request(runtime, ["cli", "langs"], None, 5_000)
                    for _ in range(calls)
                ]
                results = await asyncio.gather(*requests)
                for result in results:
                    assert result.status_code == 200  # noqa: PLR2004

            asyncio.run(scenario())

        return peak

    def test_single_worker_never_overlaps(self) -> None:
        self.assertEqual(self._run_overlapping(1), 1)

    def test_default_two_workers_overlap_but_cap_holds(self) -> None:
        self.assertEqual(self._run_overlapping(2), 2)


class TestAllowlistExhaustivenessAgainstWebapp(unittest.TestCase):
    def test_server_allowlist_covers_every_webapp_cli_surface(self) -> None:
        found: set[str] = set()
        missing_sources: list[str] = []

        for source in WEBAPP_SERVER_SOURCES:
            if not source.exists():
                missing_sources.append(str(source))
                continue
            text = source.read_text(encoding="utf-8")
            found |= set(re.findall(r"\[\s*'cli'\s*,\s*'([a-z0-9-]+)'", text))

        if missing_sources:
            self.skipTest(f"webapp sources absent: {missing_sources}")

        self.assertTrue(found, "no cli surfaces found in webapp sources")
        uncovered = found - asgi.ALLOWED_SURFACES
        self.assertEqual(
            uncovered,
            set(),
            f"webapp surfaces not covered by server allowlist: {uncovered}",
        )


class TestLangsConvenienceEndpoint(AsgiServerTestCase):
    def test_langs_runs_the_same_cli_path(self) -> None:
        with mock.patch.object(
            asgi, "run_cli_command", return_value=(0, '{"langs":["lat","grc"]}')
        ) as runner:
            response = self.client.get("/api/langs")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"langs": ["lat", "grc"]})
        self.assertEqual(runner.call_args.args[0], ["langs", "--output", "json"])


class TestContractEqualityWithCliSubprocess(unittest.TestCase):
    """Server /api/cli payloads must be JSON-identical to CLI stdout.

    Fixture-guarded: skipped on a bare checkout without the venv CLI binary,
    and per-surface when the CLI itself cannot produce output.
    """

    SURFACES = [
        ["langs", "--output", "json"],
        ["word-index", "browse", "lat", "--limit", "12", "--output", "json"],
        ["paradigm", "lat", "amo", "--kind", "conjugation", "--output", "json"],
        [
            "encounter",
            "lat",
            "arma",
            "all",
            "--translation-mode",
            "cache",
            "--cache-policy",
            "read-only",
            "--output",
            "json",
        ],
    ]

    def _cli_binary(self) -> str | None:
        binary = REPO_ROOT / ".devenv/state/venv/bin/langnet-cli"
        if binary.exists():
            return str(binary)
        return shutil.which("langnet-cli")

    def _run_cli_subprocess(self, args: list[str]) -> tuple[int, str]:
        binary = self._cli_binary()
        if binary is None:
            self.skipTest("langnet-cli binary not available")
        assert binary is not None
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": os.environ.get("HOME", "/tmp"),
            "NO_COLOR": "1",
            "PYTHONPATH": ":".join(
                [
                    str(REPO_ROOT / "src"),
                    str(REPO_ROOT / "vendor/langnet-spec/generated/python"),
                ]
            ),
        }
        proc = subprocess.run(
            [binary, *args],
            check=False,
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
        )
        return proc.returncode, proc.stdout or ""

    def test_server_payload_matches_cli_stdout(self) -> None:
        client = TestClient(asgi.app)
        for surface_args in self.SURFACES:
            with self.subTest(surface=surface_args[0]):
                code, stdout = self._run_cli_subprocess(surface_args)
                if code != 0:
                    self.skipTest(f"cli surface unavailable: {surface_args[0]}")
                start = stdout.find("{")
                end = stdout.rfind("}")
                if start == -1 or end <= start:
                    self.skipTest(f"cli produced no JSON for {surface_args[0]}")
                expected = json.loads(stdout[start : end + 1])

                response = client.post(
                    "/api/cli", json={"args": ["cli", *surface_args], "timeoutMs": 180_000}
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), expected)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
