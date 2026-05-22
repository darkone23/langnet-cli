from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from langnet.databuild.foster_ossa import FosterOssaBuildConfig, FosterOssaBuilder
from langnet.foster_ossa.search_index import (
    build_foster_ossa_search_index,
    foster_ossa_search_index_status,
    search_foster_ossa_lance,
    validate_foster_ossa_search_index,
)

FIRST_EXPERIENCE_PAGE = 49
SECOND_ENCOUNTER_PAGE = 56
EXPECTED_INDEX_RECORD_COUNT = 4


def test_build_foster_ossa_search_index_writes_page_and_encounter_rows() -> None:
    with TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        db_path = _build_fixture_db(base)
        index_path = base / "foster-ossa-search.lance"

        summary = build_foster_ossa_search_index(
            db_path=db_path,
            index_path=index_path,
            replace=True,
        )
        status = foster_ossa_search_index_status(index_path)

        assert summary["backend"] == "duckdb-lance"
        assert summary["record_count"] == EXPECTED_INDEX_RECORD_COUNT
        assert summary["record_kind_counts"] == {"encounter": 2, "page": 2}
        assert summary["fts_indexed"] is True
        assert status["exists"] is True
        assert status["record_count"] == EXPECTED_INDEX_RECORD_COUNT
        assert set(status["fts_indexes"]) == {"display_text_idx", "search_text_idx", "title_idx"}


def test_search_foster_ossa_lance_returns_ranked_source_refs() -> None:
    with TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        db_path = _build_fixture_db(base)
        index_path = base / "foster-ossa-search.lance"
        build_foster_ossa_search_index(db_path=db_path, index_path=index_path, replace=True)

        payload = search_foster_ossa_lance(
            "Functions produce true meaning",
            index_path=index_path,
            limit=5,
        )

        assert payload["backend"] == "duckdb-lance"
        assert payload["results"][0]["source_ref"] == "page:49"
        assert payload["results"][0]["record_kind"] == "page"
        assert payload["results"][0]["page_number"] == FIRST_EXPERIENCE_PAGE
        assert payload["results"][0]["target"] == {
            "command": "foster-ossa encounter",
            "encounter_id": "1.1",
            "page": 49,
        }


def test_validate_foster_ossa_search_index_reports_missing_index() -> None:
    with TemporaryDirectory() as tmp_dir:
        missing = Path(tmp_dir) / "missing.lance"

        validation = validate_foster_ossa_search_index(missing)

        assert validation["issues"][0]["code"] == "index_missing"


def _build_fixture_db(base: Path) -> Path:
    source = base / "pages.jsonl"
    db_path = base / "foster_ossa.duckdb"
    rows = [
        {
            "page_number": FIRST_EXPERIENCE_PAGE,
            "source_path": "ossa.pdf",
            "extraction_tool": "pdftotext",
            "text": "encounter 1\nOSSIUM GLUTEN\nFunctions produce true meaning.",
            "text_hash": "page-49",
            "warning": "",
        },
        {
            "page_number": SECOND_ENCOUNTER_PAGE,
            "source_path": "ossa.pdf",
            "extraction_tool": "pdftotext",
            "text": "encounter 2\nASINUS CAPRA VEHICULUM\nBlock I nouns.",
            "text_hash": "page-56",
            "warning": "",
        },
    ]
    source.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    result = FosterOssaBuilder(
        FosterOssaBuildConfig(source_path=source, output_path=db_path)
    ).build()
    assert result.status.value == "success", result.message
    return db_path
