from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from returns.result import Success

from langnet.databuild.base import BuildStatus
from langnet.databuild.foster_ossa import (
    FosterOssaBuildConfig,
    FosterOssaBuilder,
    lookup_concept_mentions,
    lookup_toc_entries,
    search_foster_ossa,
    toc_entry_rows_for_summary,
)
from langnet.databuild.paths import default_foster_ossa_path

EXPECTED_PAGE_COUNT = 2
EXPECTED_ENCOUNTER_COUNT = 1
MIN_EXPECTED_CONCEPT_MENTIONS = 3
FIRST_EXPERIENCE_START_PAGE = 49
TOC_PRINTED_PAGE_FIRST_ENCOUNTER = 3
FIRST_TOC_ENTRY_PAGE_END = 55


def _write_pages(path: Path) -> None:
    rows = [
        {
            "page_number": 9,
            "source_path": "ossa.pdf",
            "extraction_tool": "pdftotext",
            "text": (
                "CONTINENTUR\n"
                "prima experientia 1\n"
                "1. Ossium Gluten: Sententiarum Latinarum Ordo = Exitus Et\n"
                "   Vocabula. Signa Personarum In Verbis 3\n"
                "   the Bones' Glue: the structure of Latin sentences = terminations "
                "and vocabulary.\n"
            ),
            "text_hash": "toc",
            "warning": "",
        },
        {
            "page_number": 49,
            "source_path": "ossa.pdf",
            "extraction_tool": "pdftotext",
            "text": (
                "I Encounter 1 (1)\nFunctions produce true meaning. nom. subject acc. object."
            ),
            "text_hash": "first-experience",
            "warning": "",
        },
    ]
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _write_toc_span_pages(path: Path) -> None:
    rows = [
        {
            "page_number": 9,
            "source_path": "ossa.pdf",
            "extraction_tool": "pdftotext",
            "text": (
                "CONTINENTUR\n"
                "prima experientia 1\n"
                "1. Ossium Gluten 3\n"
                "   the Bones' Glue\n"
                "2. asinus—capra—vehiculum 10\n"
                "   Block I nouns\n"
            ),
            "text_hash": "toc",
            "warning": "",
        },
        {
            "page_number": 49,
            "source_path": "ossa.pdf",
            "extraction_tool": "pdftotext",
            "text": "encounter 1\nOSSIUM GLUTEN\nFunctions produce true meaning.",
            "text_hash": "p49",
            "warning": "",
        },
        {
            "page_number": 50,
            "source_path": "ossa.pdf",
            "extraction_tool": "pdftotext",
            "text": "More about endings and word order.",
            "text_hash": "p50",
            "warning": "",
        },
        {
            "page_number": 56,
            "source_path": "ossa.pdf",
            "extraction_tool": "pdftotext",
            "text": "encounter 2\nASINUS CAPRA\nBlock I nouns.",
            "text_hash": "p56",
            "warning": "",
        },
    ]
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_default_foster_ossa_path_is_build_duckdb() -> None:
    path = default_foster_ossa_path()

    assert path.name == "foster_ossa.duckdb"
    assert path.parent.name == "build"


def test_foster_ossa_builder_imports_pages_structure_and_mentions() -> None:
    with TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        source = base / "foster-ossa-pages.jsonl"
        output = base / "foster_ossa.duckdb"
        _write_pages(source)

        result = FosterOssaBuilder(
            FosterOssaBuildConfig(source_path=source, output_path=output)
        ).build()

        assert result.status == BuildStatus.SUCCESS, result.message
        assert result.status.value == "success"
        assert isinstance(result.stats, Success)
        stats = result.stats.unwrap()
        assert stats.page_count == EXPECTED_PAGE_COUNT
        assert stats.encounter_count == EXPECTED_ENCOUNTER_COUNT
        assert stats.concept_mention_count >= MIN_EXPECTED_CONCEPT_MENTIONS

        search_rows = search_foster_ossa("true meaning", db_path=output)
        assert search_rows[0]["page_number"] == FIRST_EXPERIENCE_START_PAGE
        assert "true meaning" in search_rows[0]["text"]

        mention_rows = lookup_concept_mentions("nom.", db_path=output)
        assert mention_rows[0]["term"] == "nom."
        assert mention_rows[0]["encounter_id"] == "1.1"

        toc_rows = lookup_toc_entries(db_path=output)
        assert toc_rows[0]["encounter_id"] == "1.1"
        assert toc_rows[0]["printed_page"] == TOC_PRINTED_PAGE_FIRST_ENCOUNTER
        assert toc_rows[0]["inferred_page_number"] == FIRST_EXPERIENCE_START_PAGE


def test_toc_entry_rows_for_summary_uses_adjacent_toc_page_span() -> None:
    with TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        source = base / "foster-ossa-pages.jsonl"
        output = base / "foster_ossa.duckdb"
        _write_toc_span_pages(source)

        result = FosterOssaBuilder(
            FosterOssaBuildConfig(source_path=source, output_path=output)
        ).build()
        assert result.status == BuildStatus.SUCCESS, result.message

        rows = toc_entry_rows_for_summary(db_path=output, encounter_id="1.1")

        assert len(rows) == 1
        assert rows[0]["source_ref"] == "toc:1.1"
        assert rows[0]["encounter_id"] == "1.1"
        assert rows[0]["page_start"] == FIRST_EXPERIENCE_START_PAGE
        assert rows[0]["page_end"] == FIRST_TOC_ENTRY_PAGE_END
        assert "Functions produce true meaning" in rows[0]["text"]
        assert "Block I nouns" not in rows[0]["text"]


def test_foster_ossa_builder_rejects_duplicate_page_numbers() -> None:
    with TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        source = base / "foster-ossa-pages.jsonl"
        output = base / "foster_ossa.duckdb"
        row = {
            "page_number": 49,
            "source_path": "ossa.pdf",
            "extraction_tool": "pdftotext",
            "text": "I Encounter 1 (1)\nnom. subject",
            "text_hash": "h1",
            "warning": "",
        }
        source.write_text(
            json.dumps(row) + "\n" + json.dumps({**row, "text_hash": "h2"}) + "\n",
            encoding="utf-8",
        )

        result = FosterOssaBuilder(
            FosterOssaBuildConfig(source_path=source, output_path=output)
        ).build()

        assert result.status == BuildStatus.FAILED
        assert result.message is not None
        assert "Duplicate Foster Ossa page_number 49" in result.message
        assert not output.exists()


def test_foster_ossa_builder_rejects_missing_core_page_fields() -> None:
    with TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        source = base / "foster-ossa-pages.jsonl"
        output = base / "foster_ossa.duckdb"
        source.write_text(
            json.dumps(
                {
                    "page_number": 49,
                    "source_path": "ossa.pdf",
                    "text": "I Encounter 1 (1)",
                    "text_hash": "h1",
                }
            )
            + "\n",
            encoding="utf-8",
        )

        result = FosterOssaBuilder(
            FosterOssaBuildConfig(source_path=source, output_path=output)
        ).build()

        assert result.status == BuildStatus.FAILED
        assert result.message is not None
        assert "Missing required page field on JSONL line 1" in result.message
        assert not output.exists()


def test_foster_ossa_failed_build_does_not_leave_skippable_artifact() -> None:
    with TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        source = base / "foster-ossa-pages.jsonl"
        output = base / "foster_ossa.duckdb"
        source.write_text(
            json.dumps(
                {
                    "page_number": 49,
                    "source_path": "ossa.pdf",
                    "text": "I Encounter 1 (1)",
                }
            )
            + "\n",
            encoding="utf-8",
        )

        failed = FosterOssaBuilder(
            FosterOssaBuildConfig(source_path=source, output_path=output)
        ).build()
        assert failed.status == BuildStatus.FAILED
        assert not output.exists()

        _write_pages(source)
        rebuilt = FosterOssaBuilder(
            FosterOssaBuildConfig(
                source_path=source,
                output_path=output,
                wipe_existing=False,
            )
        ).build()
        assert rebuilt.status == BuildStatus.SUCCESS, rebuilt.message


def test_foster_ossa_builder_expands_output_path() -> None:
    with TemporaryDirectory() as tmp_dir:
        original_home = os.environ.get("HOME")
        os.environ["HOME"] = tmp_dir
        try:
            source = Path(tmp_dir) / "foster-ossa-pages.jsonl"
            _write_pages(source)
            output = Path("~/foster_ossa.duckdb")

            result = FosterOssaBuilder(
                FosterOssaBuildConfig(source_path=source, output_path=output)
            ).build()

            assert result.status == BuildStatus.SUCCESS, result.message
            assert (Path(tmp_dir) / "foster_ossa.duckdb").exists()
        finally:
            if original_home is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = original_home
