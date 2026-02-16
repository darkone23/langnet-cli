from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import duckdb

from langnet.databuild.base import BuildStatus
from langnet.databuild.cdsl import CdslBuildConfig, CdslBuilder


def _make_cdsl_sqlite(path: Path, table: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    try:
        conn.execute(f"CREATE TABLE {table} (key TEXT, lnum REAL, data TEXT)")
        rows = [
            (
                "agni",
                1.0,
                "<H1><h><key1>agni</key1><key2>agnI</key2></h><tail><L>1</L><pc>p1</pc></tail><body>fire</body></H1>",
            ),
            (
                "indra",
                2.0,
                "<H1><h><key1>indra</key1></h><tail><L>2</L><pc>p2</pc></tail><body>deity</body></H1>",
            ),
        ]
        conn.executemany(f"INSERT INTO {table} VALUES (?, ?, ?)", rows)
        conn.commit()
    finally:
        conn.close()


def _fetch_single_value(result, default=0):
    """Safely extract a single value from a fetchone result."""
    row = result.fetchone()
    if row is None:
        return default
    return row[0]


def test_cdsl_builder_small_sqlite() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        dict_id = "MW"
        sqlite_path = base / "dict" / dict_id / "web" / "sqlite" / f"{dict_id.lower()}.sqlite"
        _make_cdsl_sqlite(sqlite_path, dict_id)
        out_path = base / "cdsl.duckdb"

        config = CdslBuildConfig(
            dict_id=dict_id,
            source_dir=base / "dict",
            output_path=out_path,
            limit=None,
            batch_size=10,
            wipe_existing=True,
        )
        builder = CdslBuilder(config)
        result = builder.build()
        assert result.status == BuildStatus.SUCCESS, result.message
        assert out_path.exists()

        conn = duckdb.connect(str(out_path))
        try:
            entry_count = _fetch_single_value(conn.execute("SELECT COUNT(*) FROM entries"))
            headword_count = _fetch_single_value(conn.execute("SELECT COUNT(*) FROM headwords"))
            primary_result = conn.execute(
                "SELECT key FROM headwords WHERE key_normalized='agni' AND is_primary = true"
            ).fetchone()
            primary = primary_result[0] if primary_result else ""
            secondary = conn.execute(
                "SELECT key FROM headwords WHERE key_normalized='agni' AND is_primary = false"
            ).fetchone()
        finally:
            conn.close()

        EXPECTED_ENTRY_COUNT = 2
        EXPECTED_HEADWORD_COUNT = 3  # agni primary/secondary + indra
        assert entry_count == EXPECTED_ENTRY_COUNT
        assert headword_count == EXPECTED_HEADWORD_COUNT
        assert primary == "agni"
        assert secondary is not None
        assert secondary[0].lower() == "agni"
