from __future__ import annotations

import contextlib
from collections.abc import Iterator
from pathlib import Path

import duckdb
from filelock import FileLock


@contextlib.contextmanager
def connect_duckdb(
    path: Path | str, read_only: bool = False, lock: bool = True, allow_create: bool = True
) -> Iterator[duckdb.DuckDBPyConnection]:
    """
    Open a DuckDB connection with optional file-based locking for writers.

    Readers can set read_only=True to avoid grabbing the lock. When allow_create is
    False, a missing file will raise instead of implicitly creating a new DB.

    Special case: path=":memory:" creates an in-memory database.
    """
    # Handle special :memory: case
    if path == ":memory:":
        conn = duckdb.connect(database=":memory:", read_only=read_only)
        try:
            yield conn
        finally:
            conn.close()
        return

    # Normal file-based path
    path_obj = Path(path) if isinstance(path, str) else path
    db_uri = str(path_obj)
    if not allow_create and not path_obj.exists():
        raise FileNotFoundError(f"DuckDB path does not exist: {path_obj}")

    lock_ctx = contextlib.nullcontext()
    if lock and not read_only:
        lock_ctx = FileLock(f"{path_obj}.lock")

    with lock_ctx:
        conn = duckdb.connect(database=db_uri, read_only=read_only)
        try:
            yield conn
        finally:
            conn.close()


@contextlib.contextmanager
def connect_duckdb_ro(path: Path) -> Iterator[duckdb.DuckDBPyConnection]:
    """
    Safe read-only connection helper that refuses to create new DB files.
    """
    if not path.exists():
        raise FileNotFoundError(f"DuckDB path does not exist: {path}")
    with connect_duckdb(path, read_only=True, lock=False, allow_create=False) as conn:
        yield conn


@contextlib.contextmanager
def connect_duckdb_rw(path: Path) -> Iterator[duckdb.DuckDBPyConnection]:
    """
    Write-enabled connection helper that ensures parent dirs and uses a lock.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect_duckdb(path, read_only=False, lock=True, allow_create=True) as conn:
        yield conn
