from __future__ import annotations

import contextlib
from collections.abc import Iterator
from pathlib import Path

import duckdb
from filelock import FileLock


@contextlib.contextmanager
def connect_duckdb(
    path: Path, read_only: bool = False, lock: bool = True
) -> Iterator[duckdb.DuckDBPyConnection]:
    """
    Open a DuckDB connection with optional file-based locking for writers.

    Readers can set read_only=True to avoid grabbing the lock.
    """
    db_uri = str(path)
    lock_ctx = contextlib.nullcontext()
    if lock and not read_only:
        lock_ctx = FileLock(f"{path}.lock")

    with lock_ctx:
        conn = duckdb.connect(database=db_uri, read_only=read_only)
        try:
            yield conn
        finally:
            conn.close()
