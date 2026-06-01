from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import duckdb
from filelock import FileLock, Timeout

from langnet.storage.db import connect_duckdb

EXPECTED_TRANSIENT_LOCK_CONNECT_ATTEMPTS = 2


def test_connect_duckdb_writer_lock_timeout_is_bounded_by_env() -> None:
    with TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "langnet.duckdb"
        lock = FileLock(f"{db_path}.lock")
        lock.acquire(timeout=0)
        old_timeout = os.environ.get("LANGNET_DUCKDB_LOCK_TIMEOUT_SECONDS")
        os.environ["LANGNET_DUCKDB_LOCK_TIMEOUT_SECONDS"] = "0"
        try:
            try:
                with connect_duckdb(db_path, read_only=False, lock=True):
                    raise AssertionError("connect_duckdb unexpectedly acquired a held lock")
            except Timeout:
                pass
        finally:
            if old_timeout is None:
                os.environ.pop("LANGNET_DUCKDB_LOCK_TIMEOUT_SECONDS", None)
            else:
                os.environ["LANGNET_DUCKDB_LOCK_TIMEOUT_SECONDS"] = old_timeout
            lock.release()


def test_connect_duckdb_retries_transient_duckdb_lock_error() -> None:
    attempts = 0
    original_connect = duckdb.connect

    def flaky_connect(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise duckdb.IOException("IO Error: Could not set lock on file")
        return original_connect(database=":memory:", read_only=kwargs.get("read_only", False))

    with TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "langnet.duckdb"
        with (
            mock.patch.dict(
                os.environ,
                {
                    "LANGNET_DUCKDB_CONNECT_RETRY_SECONDS": "1",
                    "LANGNET_DUCKDB_CONNECT_RETRY_INTERVAL_SECONDS": "0",
                },
            ),
            mock.patch("langnet.storage.db.duckdb.connect", side_effect=flaky_connect),
            connect_duckdb(db_path, read_only=False, lock=False) as conn,
        ):
            row = conn.execute("SELECT 1").fetchone()

    assert attempts == EXPECTED_TRANSIENT_LOCK_CONNECT_ATTEMPTS
    assert row == (1,)
