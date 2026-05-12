from __future__ import annotations

import tempfile
from pathlib import Path

import duckdb
from returns.result import Success

from langnet.databuild.base import BuildStatus
from langnet.databuild.whitakers import WhitakersBuildConfig, WhitakersBuilder

EXPECTED_ENTRY_COUNT = 3


def _write_whitakers_dictline(path: Path) -> None:
    rows = [
        (
            "lup",
            "lup",
            "",
            "",
            "N      2 1 M T          X X X A X wolf; grappling iron;",
        ),
        (
            "am",
            "am",
            "amav",
            "amat",
            "V      1 1 X            X X X A O love, like; be fond of;",
        ),
        (
            "amodo",
            "",
            "",
            "",
            "ADV    POS              D X X E S henceforth, from this time forward;",
        ),
    ]
    text = "".join(
        f"{stem1:<19}{stem2:<19}{stem3:<19}{stem4:<19}{tail}\n"
        for stem1, stem2, stem3, stem4, tail in rows
    )
    path.write_text(text, encoding="utf-8")


def test_whitakers_build_derives_learner_headwords_from_dictline() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        source_path = base / "DICTLINE.GEN"
        output_path = base / "lex_whitakers.duckdb"
        _write_whitakers_dictline(source_path)

        builder = WhitakersBuilder(
            WhitakersBuildConfig(
                source_path=source_path,
                output_path=output_path,
                batch_size=2,
                wipe_existing=True,
            )
        )

        result = builder.build()
        assert result.status == BuildStatus.SUCCESS, result.message
        assert isinstance(result.stats, Success)
        stats = result.stats.unwrap()
        assert stats.entry_count == EXPECTED_ENTRY_COUNT
        assert stats.headword_count == EXPECTED_ENTRY_COUNT

        conn = duckdb.connect(str(output_path))
        try:
            rows = conn.execute(
                """
                SELECT entry_id, headword_raw, headword_norm, source_stem, pos, plain_text
                FROM entries
                ORDER BY entry_id
                """
            ).fetchall()
            indexes = {
                row[0] for row in conn.execute("SELECT index_name FROM duckdb_indexes()").fetchall()
            }
        finally:
            conn.close()

    assert rows == [
        (1, "lupus", "lupus", "lup", "N", "wolf; grappling iron;"),
        (2, "amo", "amo", "am", "V", "love, like; be fond of;"),
        (3, "amodo", "amodo", "amodo", "ADV", "henceforth, from this time forward;"),
    ]
    assert "whitakers_entries_headword_norm_idx" in indexes
    assert "whitakers_entries_headword_entry_idx" in indexes
