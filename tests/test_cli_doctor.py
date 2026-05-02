from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import duckdb
import jsonschema
from click.testing import CliRunner
from filelock import FileLock

from langnet.cli import main

DOCTOR_SCHEMA_PATH = Path("docs/schemas/doctor.v1.schema.json")


def _assert_matches_schema(payload: object) -> None:
    schema = json.loads(DOCTOR_SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(payload)


def test_doctor_json_reports_cli_assumptions_without_network() -> None:
    with TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "langnet.duckdb"
        result = CliRunner().invoke(
            main,
            [
                "doctor",
                "--translation-cache-db",
                str(cache_path),
                "--output",
                "json",
            ],
            env={"OPENAI_API_KEY": ""},
        )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    _assert_matches_schema(payload)
    assert payload["schema_version"] == "langnet.doctor.v1"
    assert payload["ok"] is True
    check_ids = {check["id"] for check in payload["checks"]}
    assert "catalog:surface" in check_ids
    assert "translation_cache:path" in check_ids
    assert "translation:openai_key" in check_ids


def test_doctor_can_require_openai_key_for_translation_population() -> None:
    with TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "langnet.duckdb"
        result = CliRunner().invoke(
            main,
            [
                "doctor",
                "--translation-cache-db",
                str(cache_path),
                "--require-openai-key",
                "--output",
                "json",
            ],
            env={"OPENAI_API_KEY": ""},
        )

    assert result.exit_code == 1, result.output
    payload = json.loads(result.output)
    _assert_matches_schema(payload)
    assert payload["ok"] is False
    openai_check = next(
        check for check in payload["checks"] if check["id"] == "translation:openai_key"
    )
    assert openai_check["status"] == "fail"


def test_doctor_json_reports_cache_lock_contention() -> None:
    with TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "langnet.duckdb"
        with duckdb.connect(str(cache_path)):
            pass
        lock = FileLock(f"{cache_path}.lock")
        lock.acquire(timeout=0)
        try:
            result = CliRunner().invoke(
                main,
                [
                    "doctor",
                    "--translation-cache-db",
                    str(cache_path),
                    "--output",
                    "json",
                ],
                env={
                    "LANGNET_DUCKDB_LOCK_TIMEOUT_SECONDS": "0",
                    "OPENAI_API_KEY": "",
                },
            )
        finally:
            lock.release()

    assert result.exit_code == 1, result.output
    payload = json.loads(result.output)
    _assert_matches_schema(payload)
    assert payload["ok"] is False
    cache_check = next(
        check for check in payload["checks"] if check["id"] == "translation_cache:available"
    )
    assert cache_check["status"] == "fail"
