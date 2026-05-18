from __future__ import annotations

import tempfile
from pathlib import Path

import duckdb

from langnet.databuild.base import BuildStatus
from langnet.databuild.lewis_1890 import (
    Lewis1890BuildConfig,
    Lewis1890Builder,
    lookup_lewis_1890_entries,
    lookup_lewis_1890_entries_by_headword,
)


def test_lewis_1890_build_imports_yaml_entries() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        source = base / "lewis.yaml"
        output = base / "lex_lewis_1890.duckdb"
        source.write_text(
            'lupus: "lupus ī, m a wolf: lupa, V.; lupus in fabula."\n'
            'amo: "amō āvī ātus āre, to love, like."\n',
            encoding="utf-8",
        )

        result = Lewis1890Builder(
            Lewis1890BuildConfig(source_path=source, output_path=output, batch_size=1)
        ).build()
        entries = lookup_lewis_1890_entries("lupus", output)

    assert result.status == BuildStatus.SUCCESS, result.message
    assert len(entries) == 1
    assert entries[0]["entry_id"] == "lewis-1890:lupus"
    assert entries[0]["headword_norm"] == "lupus"
    assert "wolf" in entries[0]["plain_text"]


def test_lewis_1890_lookup_uses_ordered_candidates() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        source = base / "lewis.yaml"
        output = base / "lex_lewis_1890.duckdb"
        source.write_text(
            'lupus: "lupus ī, m a wolf."\namo: "amō āvī ātus āre, to love, like."\n',
            encoding="utf-8",
        )
        result = Lewis1890Builder(
            Lewis1890BuildConfig(source_path=source, output_path=output)
        ).build()

        entries = lookup_lewis_1890_entries_by_headword(["lupi", "lupus"], output)

    assert result.status == BuildStatus.SUCCESS, result.message
    assert [entry["source_key"] for entry in entries] == ["lupus"]


def test_lewis_1890_build_creates_indexes() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        source = base / "lewis.yaml"
        output = base / "lex_lewis_1890.duckdb"
        source.write_text('nox: "nox noctis, f night."\n', encoding="utf-8")
        result = Lewis1890Builder(
            Lewis1890BuildConfig(source_path=source, output_path=output)
        ).build()

        with duckdb.connect(str(output)) as conn:
            indexes = {
                row[0] for row in conn.execute("SELECT index_name FROM duckdb_indexes()").fetchall()
            }

    assert result.status == BuildStatus.SUCCESS, result.message
    assert "lewis_1890_headword_norm_idx" in indexes
    assert "lewis_1890_headword_entry_idx" in indexes
