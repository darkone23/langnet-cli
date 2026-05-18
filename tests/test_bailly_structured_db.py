from __future__ import annotations

import json
import tempfile
from pathlib import Path

import duckdb
from click.testing import CliRunner

from langnet.cli import main
from langnet.databuild.bailly import (
    BaillyBuildConfig,
    BaillyBuilder,
    apply_bailly_schema,
    insert_pdf_structural_entry,
    lookup_bailly_entries,
)
from langnet.databuild.base import BuildStatus

AGELAIOS_PAGE = 90


def test_insert_pdf_structural_entry_writes_entry_and_layout_blocks() -> None:
    conn = duckdb.connect(database=":memory:")
    try:
        apply_bailly_schema(conn)
        insert_pdf_structural_entry(
            conn,
            {
                "entry_id": "bailly-p001-c1-0001",
                "lemma": "ἀγελαῖος",
                "lemma_norm": "agelaios",
                "source": {
                    "kind": "pdf",
                    "path": "~/digital-bailly-pdf",
                    "page_start": 12,
                    "page_end": 12,
                },
                "raw_text": "ἀγελαῖος,α, ον [ᾰγ]\nI qui forme un troupeau",
                "blocks": [
                    {
                        "path": "00",
                        "marker": "head",
                        "text": "ἀγελαῖος,α, ον [ᾰγ]",
                        "layout": {
                            "page": 12,
                            "column": 1,
                            "line_start_x": 72.0,
                            "text_start_x": 72.0,
                        },
                    },
                    {
                        "path": "01",
                        "marker": "I",
                        "text": "qui forme un troupeau",
                        "layout": {
                            "page": 12,
                            "column": 1,
                            "line_start_x": 72.0,
                            "text_start_x": 86.0,
                        },
                    },
                ],
            },
        )

        entry_row = conn.execute(
            """
            SELECT entry_id, lemma, lemma_norm, source_kind, source_path,
                   page_start, page_end, raw_text, block_count
            FROM entries
            """
        ).fetchone()
        block_rows = conn.execute(
            """
            SELECT entry_id, path, marker, text, layout_json, ordinal
            FROM entry_blocks
            ORDER BY ordinal
            """
        ).fetchall()
        indexes = {
            row[0] for row in conn.execute("SELECT index_name FROM duckdb_indexes()").fetchall()
        }
    finally:
        conn.close()

    assert entry_row == (
        "bailly-p001-c1-0001",
        "ἀγελαῖος",
        "agelaios",
        "pdf",
        "~/digital-bailly-pdf",
        12,
        12,
        "ἀγελαῖος,α, ον [ᾰγ]\nI qui forme un troupeau",
        2,
    )
    assert [(row[1], row[2], row[3], row[5]) for row in block_rows] == [
        ("00", "head", "ἀγελαῖος,α, ον [ᾰγ]", 0),
        ("01", "I", "qui forme un troupeau", 1),
    ]
    assert json.loads(block_rows[1][4]) == {
        "page": 12,
        "column": 1,
        "line_start_x": 72.0,
        "text_start_x": 86.0,
    }
    assert "entries_lemma_norm_idx" in indexes
    assert "entry_blocks_entry_path_idx" in indexes


def test_insert_pdf_structural_entry_repairs_legacy_line_break_hyphenation() -> None:
    conn = duckdb.connect(database=":memory:")
    try:
        apply_bailly_schema(conn)
        insert_pdf_structural_entry(
            conn,
            {
                "entry_id": "bailly-p120-c1-0001",
                "lemma": "ἥρως",
                "lemma_norm": "heros",
                "source": {
                    "kind": "pdf",
                    "path": "~/digital-bailly-pdf",
                    "page_start": 120,
                    "page_end": 120,
                },
                "raw_text": "chefs mi- litaires ; θε- ὸν ἢ δαίμο- νας",
                "blocks": [
                    {"path": "00", "marker": "head", "text": "ἥρως, ωος"},
                    {
                        "path": "01",
                        "marker": "I",
                        "text": "chefs mi- litaires ; θε- ὸν ἢ δαίμο- νας",
                    },
                ],
            },
        )

        entry_row = conn.execute("SELECT raw_text FROM entries").fetchone()
        block_row = conn.execute("SELECT text FROM entry_blocks WHERE path = '01'").fetchone()
    finally:
        conn.close()

    assert entry_row == ("chefs militaires ; θεὸν ἢ δαίμονας",)
    assert block_row == ("chefs militaires ; θεὸν ἢ δαίμονας",)


def test_bailly_builder_reads_pdf_structural_jsonl() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        source_path = base / "bailly_pdf_entries.jsonl"
        output_path = base / "lex_bailly.duckdb"
        source_path.write_text(
            json.dumps(
                {
                    "entry_id": "bailly-p001-c1-0001",
                    "lemma": "ἀγελαῖος",
                    "lemma_norm": "agelaios",
                    "source": {"kind": "pdf", "path": "~/digital-bailly-pdf", "page_start": 12},
                    "raw_text": "ἀγελαῖος,α, ον",
                    "blocks": [{"path": "00", "marker": "head", "text": "ἀγελαῖος,α, ον"}],
                },
                ensure_ascii=False,
            )
            + "\n"
            + json.dumps(
                {
                    "entry_id": "bailly-p001-c1-0002",
                    "lemma": "ἀγελαιοτροφία",
                    "lemma_norm": "agelaiotrophia",
                    "source": {"kind": "pdf", "path": "~/digital-bailly-pdf", "page_start": 12},
                    "raw_text": "ἀγελαιοτροφία,ας",
                    "blocks": [{"path": "00", "marker": "head", "text": "ἀγελαιοτροφία,ας"}],
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        builder = BaillyBuilder(
            BaillyBuildConfig(
                source_path=source_path,
                output_path=output_path,
                batch_size=1,
                wipe_existing=True,
            )
        )

        result = builder.build()

        assert result.status == BuildStatus.SUCCESS, result.message
        conn = duckdb.connect(str(output_path))
        try:
            rows = conn.execute(
                "SELECT entry_id, lemma_norm, block_count FROM entries ORDER BY entry_id"
            ).fetchall()
        finally:
            conn.close()

    assert rows == [
        ("bailly-p001-c1-0001", "agelaios", 1),
        ("bailly-p001-c1-0002", "agelaiotrophia", 1),
    ]


def test_lookup_bailly_entries_returns_ordered_blocks_by_greek_or_normalized_headword() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "lex_bailly.duckdb"
        with duckdb.connect(str(db_path)) as conn:
            apply_bailly_schema(conn)
            insert_pdf_structural_entry(
                conn,
                {
                    "entry_id": "bailly-p090-c1-0004",
                    "lemma": "ἀγελαῖος",
                    "lemma_norm": "agelaios",
                    "source": {"kind": "pdf", "page_start": 90, "page_end": 90},
                    "raw_text": "ἀγελαῖος, α, ον [ ᾰγ ] I qui forme un troupeau",
                    "blocks": [
                        {"path": "00", "marker": "head", "text": "ἀγελαῖος, α, ον [ ᾰγ ]"},
                        {"path": "01", "marker": "I", "text": "qui forme un troupeau"},
                    ],
                },
            )

        greek_entries = lookup_bailly_entries("ἀγελαῖος", db_path)
        normalized_entries = lookup_bailly_entries("agelaios", db_path)

    assert greek_entries == normalized_entries
    assert greek_entries[0]["lemma"] == "ἀγελαῖος"
    assert greek_entries[0]["page_start"] == AGELAIOS_PAGE
    assert [(block["path"], block["marker"]) for block in greek_entries[0]["blocks"]] == [
        ("00", "head"),
        ("01", "I"),
    ]


def test_lookup_bailly_entries_prefers_comma_head_and_composition_dot_variants() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "lex_bailly.duckdb"
        with duckdb.connect(str(db_path)) as conn:
            apply_bailly_schema(conn)
            insert_pdf_structural_entry(
                conn,
                {
                    "entry_id": "bailly-p081-c1-0001",
                    "lemma": "Α",
                    "lemma_norm": "a",
                    "source": {"kind": "pdf", "page_start": 81, "page_end": 81},
                    "raw_text": "Α, α alpha",
                    "blocks": [{"path": "00", "marker": "head", "text": "Α, α alpha"}],
                },
            )
            insert_pdf_structural_entry(
                conn,
                {
                    "entry_id": "bailly-p081-c1-0009",
                    "lemma": "ἃ ἅ",
                    "lemma_norm": "a_a",
                    "source": {"kind": "pdf", "page_start": 81, "page_end": 81},
                    "raw_text": "ἃ ἅ ah",
                    "blocks": [{"path": "00", "marker": "head", "text": "ἃ ἅ ah"}],
                },
            )
            insert_pdf_structural_entry(
                conn,
                {
                    "entry_id": "bailly-p090-c1-0003",
                    "lemma": "ἀγελαιο·κομική",
                    "lemma_norm": "agelaio_komikh",
                    "source": {"kind": "pdf", "page_start": 90, "page_end": 90},
                    "raw_text": "ἀγελαιο·κομική",
                    "blocks": [{"path": "00", "marker": "head", "text": "ἀγελαιο·κομική"}],
                },
            )

        alpha = lookup_bailly_entries("Α, α", db_path, limit=1)
        komike = lookup_bailly_entries("ἀγελαιοκομική", db_path, limit=1)

    assert alpha[0]["entry_id"] == "bailly-p081-c1-0001"
    assert komike[0]["entry_id"] == "bailly-p090-c1-0003"


def test_bailly_db_lookup_cli_prints_structural_blocks() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "lex_bailly.duckdb"
        with duckdb.connect(str(db_path)) as conn:
            apply_bailly_schema(conn)
            insert_pdf_structural_entry(
                conn,
                {
                    "entry_id": "bailly-p090-c1-0004",
                    "lemma": "ἀγελαῖος",
                    "lemma_norm": "agelaios",
                    "source": {"kind": "pdf", "page_start": 90, "page_end": 90},
                    "raw_text": "ἀγελαῖος",
                    "blocks": [
                        {"path": "00", "marker": "head", "text": "ἀγελαῖος, α, ον"},
                        {"path": "01", "marker": "I", "text": "qui forme un troupeau"},
                    ],
                },
            )

        result = CliRunner().invoke(
            main,
            ["bailly-db-lookup", "agelaios", "--db", str(db_path)],
        )

    assert result.exit_code == 0, result.output
    assert "ἀγελαῖος [bailly-p090-c1-0004] pages 90-90" in result.output
    assert "00 head ἀγελαῖος, α, ον" in result.output
    assert "01 I qui forme un troupeau" in result.output
