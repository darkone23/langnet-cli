from __future__ import annotations

import contextlib
import os
import time
from collections.abc import Iterator
from pathlib import Path

import duckdb
from filelock import FileLock

DEFAULT_DUCKDB_LOCK_TIMEOUT_SECONDS = 30.0
DEFAULT_DUCKDB_CONNECT_RETRY_SECONDS = 2.0
DEFAULT_DUCKDB_CONNECT_RETRY_INTERVAL_SECONDS = 0.05


def _duckdb_lock_timeout_seconds() -> float:
    raw = os.getenv("LANGNET_DUCKDB_LOCK_TIMEOUT_SECONDS")
    if not raw:
        return DEFAULT_DUCKDB_LOCK_TIMEOUT_SECONDS
    try:
        return max(0.0, float(raw))
    except ValueError:
        return DEFAULT_DUCKDB_LOCK_TIMEOUT_SECONDS


def _duckdb_connect_retry_seconds() -> float:
    raw = os.getenv("LANGNET_DUCKDB_CONNECT_RETRY_SECONDS")
    if not raw:
        return DEFAULT_DUCKDB_CONNECT_RETRY_SECONDS
    try:
        return max(0.0, float(raw))
    except ValueError:
        return DEFAULT_DUCKDB_CONNECT_RETRY_SECONDS


def _duckdb_connect_retry_interval_seconds() -> float:
    raw = os.getenv("LANGNET_DUCKDB_CONNECT_RETRY_INTERVAL_SECONDS")
    if not raw:
        return DEFAULT_DUCKDB_CONNECT_RETRY_INTERVAL_SECONDS
    try:
        return max(0.0, float(raw))
    except ValueError:
        return DEFAULT_DUCKDB_CONNECT_RETRY_INTERVAL_SECONDS


def _duckdb_connect_with_retry(
    *,
    database: str,
    read_only: bool,
) -> duckdb.DuckDBPyConnection:
    deadline = time.monotonic() + _duckdb_connect_retry_seconds()
    interval = _duckdb_connect_retry_interval_seconds()
    while True:
        try:
            return duckdb.connect(database=database, read_only=read_only)
        except duckdb.Error as exc:
            if not _is_duckdb_lock_error(exc) or time.monotonic() >= deadline:
                raise
            time.sleep(interval)


def _is_duckdb_lock_error(exc: duckdb.Error) -> bool:
    message = str(exc).casefold()
    return "conflicting lock" in message or "could not set lock" in message


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

    lock_handle: FileLock | None = None
    if lock and not read_only:
        lock_handle = FileLock(f"{path_obj}.lock")

    if lock_handle is not None:
        timeout = _duckdb_lock_timeout_seconds()
        lock_handle.acquire(timeout=timeout, blocking=timeout > 0)
    try:
        conn = _duckdb_connect_with_retry(database=db_uri, read_only=read_only)
        try:
            yield conn
        finally:
            conn.close()
    finally:
        if lock_handle is not None and lock_handle.is_locked:
            lock_handle.release()


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
