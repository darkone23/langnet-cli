from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory

from filelock import FileLock, Timeout

from langnet.storage.db import connect_duckdb


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
