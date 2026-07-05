from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from click.testing import CliRunner

from langnet.cli import main
from langnet.foster_ossa.extraction import iter_page_rows_from_pdftotext
from langnet.foster_ossa.summaries import invalid_source_refs_from_summary_jsonl

FIRST_EXPERIENCE_PAGE = 49


def _write_page_jsonl(path: Path) -> None:
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
            "page_number": FIRST_EXPERIENCE_PAGE,
            "source_path": "ossa.pdf",
            "extraction_tool": "pdftotext",
            "text": "I Encounter 1 (1)\nFunctions produce true meaning. nom. subject acc. object.",
            "text_hash": "first-experience",
            "warning": "",
        },
    ]
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _build_test_db(source: Path, db_path: Path) -> None:
    build = CliRunner().invoke(
        main,
        [
            "databuild",
            "foster-ossa",
            "--source",
            str(source),
            "--output",
            str(db_path),
            "--wipe",
        ],
    )
    assert build.exit_code == 0, build.output


def test_foster_ossa_extract_writes_jsonl_with_mocked_runner() -> None:
    with TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        source = base / "ossa.pdf"
        output = base / "foster-ossa-pages.jsonl"
        source.write_bytes(b"%PDF-1.4\n")

        def fake_extract(source_path: Path):
            return iter_page_rows_from_pdftotext("\fOne\n\fTwo\n", source_path=source_path)

        with patch("langnet.foster_ossa.extraction.extract_pdf_pages", side_effect=fake_extract):
            result = CliRunner().invoke(
                main,
                [
                    "foster-ossa-extract",
                    "--source",
                    str(source),
                    "--output",
                    str(output),
                ],
            )

        assert result.exit_code == 0, result.output
        assert "wrote:" in result.output
        rows = [
            json.loads(line)
            for line in output.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert [row["page_number"] for row in rows] == [1, 2]


def test_foster_ossa_search_reads_built_db() -> None:
    with TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        source = base / "foster-ossa-pages.jsonl"
        db_path = base / "foster_ossa.duckdb"
        _write_page_jsonl(source)

        _build_test_db(source, db_path)

        result = CliRunner().invoke(
            main,
            [
                "foster-ossa",
                "search",
                "true meaning",
                "--db",
                str(db_path),
                "--output",
                "json",
            ],
        )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["results"][0]["page_number"] == FIRST_EXPERIENCE_PAGE


def test_foster_ossa_search_uses_lance_index_when_supplied() -> None:
    with TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        source = base / "foster-ossa-pages.jsonl"
        db_path = base / "foster_ossa.duckdb"
        index_path = base / "foster-ossa-search.lance"
        _write_page_jsonl(source)
        _build_test_db(source, db_path)

        build = CliRunner().invoke(
            main,
            [
                "foster-ossa",
                "search-index",
                "build",
                "--db",
                str(db_path),
                "--index",
                str(index_path),
                "--replace",
                "--output",
                "json",
            ],
        )
        assert build.exit_code == 0, build.output

        result = CliRunner().invoke(
            main,
            [
                "foster-ossa",
                "search",
                "true meaning",
                "--index",
                str(index_path),
                "--output",
                "json",
            ],
        )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["backend"] == "duckdb-lance"
        assert payload["results"][0]["source_ref"] == "page:49"


def test_foster_ossa_concept_lookup_outputs_mentions() -> None:
    with TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        source = base / "foster-ossa-pages.jsonl"
        db_path = base / "foster_ossa.duckdb"
        _write_page_jsonl(source)

        _build_test_db(source, db_path)

        result = CliRunner().invoke(
            main,
            [
                "foster-ossa",
                "concept",
                "nom.",
                "--db",
                str(db_path),
                "--output",
                "json",
            ],
        )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["mentions"][0]["term"] == "nom."


def test_foster_ossa_toc_outputs_structured_entries() -> None:
    with TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        source = base / "foster-ossa-pages.jsonl"
        db_path = base / "foster_ossa.duckdb"
        _write_page_jsonl(source)
        _build_test_db(source, db_path)

        result = CliRunner().invoke(
            main,
            ["foster-ossa", "toc", "--db", str(db_path), "--output", "json"],
        )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["entries"][0]["encounter_id"] == "1.1"
        assert payload["entries"][0]["inferred_page_number"] == FIRST_EXPERIENCE_PAGE


def test_foster_ossa_databuild_failure_exits_nonzero() -> None:
    with TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        source = base / "bad-pages.jsonl"
        db_path = base / "foster_ossa.duckdb"
        source.write_text(json.dumps({"page_number": 49}) + "\n", encoding="utf-8")

        result = CliRunner().invoke(
            main,
            [
                "databuild",
                "foster-ossa",
                "--source",
                str(source),
                "--output",
                str(db_path),
            ],
        )

        assert result.exit_code != 0
        assert "failed" in result.output.lower()


def test_foster_ossa_rejects_negative_limits() -> None:
    runner = CliRunner()
    for args in [
        ["foster-ossa", "search", "x", "--limit", "-1"],
        ["foster-ossa", "concept", "nom.", "--limit", "-1"],
        ["foster-ossa", "toc", "--limit", "-1"],
        ["foster-ossa-summarize", "--output", "summaries.jsonl", "--limit", "-1"],
    ]:
        result = runner.invoke(main, args)
        assert result.exit_code != 0, result.output
        assert "Invalid value for '--limit'" in result.output

    with TemporaryDirectory() as tmp_dir:
        source = Path(tmp_dir) / "pages.jsonl"
        _write_page_jsonl(source)
        result = runner.invoke(
            main,
            ["databuild", "foster-ossa", "--source", str(source), "--limit", "-1"],
        )
        assert result.exit_code != 0, result.output
        assert "Invalid value for '--limit'" in result.output


def test_foster_ossa_search_treats_wildcards_literally() -> None:
    with TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        source = base / "foster-ossa-pages.jsonl"
        db_path = base / "foster_ossa.duckdb"
        _write_page_jsonl(source)
        _build_test_db(source, db_path)

        result = CliRunner().invoke(
            main,
            ["foster-ossa", "search", "%", "--db", str(db_path), "--output", "json"],
        )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["results"] == []


def test_foster_ossa_encounter_lookup_outputs_json_and_not_found() -> None:
    with TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        source = base / "foster-ossa-pages.jsonl"
        db_path = base / "foster_ossa.duckdb"
        _write_page_jsonl(source)
        _build_test_db(source, db_path)

        result = CliRunner().invoke(
            main,
            ["foster-ossa", "encounter", "1.1", "--db", str(db_path), "--output", "json"],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["encounter"]["encounter_id"] == "1.1"

        missing = CliRunner().invoke(
            main,
            ["foster-ossa", "encounter", "9.9", "--db", str(db_path)],
        )
        assert missing.exit_code == 0, missing.output
        assert "No Foster Ossa encounter found" in missing.output


def test_foster_ossa_summarize_dry_run_writes_planned_jsonl() -> None:
    with TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        source = base / "foster-ossa-pages.jsonl"
        db_path = base / "foster_ossa.duckdb"
        output = base / "summaries.jsonl"
        _write_page_jsonl(source)
        _build_test_db(source, db_path)

        result = CliRunner().invoke(
            main,
            [
                "foster-ossa-summarize",
                "--db",
                str(db_path),
                "--output",
                str(output),
                "--encounter",
                "1.1",
                "--dry-run",
            ],
            env={"OPENAI_API_KEY": ""},
        )

        assert result.exit_code == 0, result.output
        assert "planned: 1" in result.output
        rows = [
            json.loads(line)
            for line in output.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert rows == [
            {
                "source_ref": "page:49",
                "scope": "page",
                "model": "openai:deepseek/deepseek-v4-flash",
                "prompt_version": "foster-ossa-summary-v1",
                "input_hash": rows[0]["input_hash"],
                "generated_text": "",
                "validation_status": "planned",
            }
        ]
        assert rows[0]["input_hash"]


def test_foster_ossa_summarize_toc_entry_scope_writes_planned_jsonl() -> None:
    with TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        source = base / "foster-ossa-pages.jsonl"
        db_path = base / "foster_ossa.duckdb"
        output = base / "toc-summaries.jsonl"
        _write_page_jsonl(source)
        _build_test_db(source, db_path)

        result = CliRunner().invoke(
            main,
            [
                "foster-ossa-summarize",
                "--db",
                str(db_path),
                "--scope",
                "toc-entry",
                "--output",
                str(output),
                "--encounter",
                "1.1",
                "--dry-run",
            ],
            env={"OPENAI_API_KEY": ""},
        )

        assert result.exit_code == 0, result.output
        assert "planned: 1" in result.output
        rows = [
            json.loads(line)
            for line in output.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert rows[0]["source_ref"] == "toc:1.1"
        assert rows[0]["scope"] == "toc-entry"
        assert rows[0]["prompt_version"] == "foster-ossa-toc-summary-v2"
        assert rows[0]["validation_status"] == "planned"


def test_foster_ossa_summarize_experience_scope_plans_from_toc_summary_jsonl() -> None:
    with TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        input_summaries = base / "toc-summaries.jsonl"
        output = base / "experience-summaries.jsonl"
        input_summaries.write_text(
            json.dumps(
                {
                    "source_ref": "toc:1.1",
                    "scope": "toc-entry",
                    "validation_status": "generated_valid",
                    "generated_json": json.dumps(
                        {
                            "source_ref": "toc:1.1",
                            "encounter_id": "1.1",
                            "title": "Ossium Gluten",
                            "method_claims": ["Functions matter."],
                            "learner_actions": ["Read endings."],
                            "source_refs": ["page:49"],
                        }
                    ),
                }
            )
            + "\n",
            encoding="utf-8",
        )

        result = CliRunner().invoke(
            main,
            [
                "foster-ossa-summarize",
                "--scope",
                "experience",
                "--input-summaries",
                str(input_summaries),
                "--output",
                str(output),
                "--dry-run",
            ],
            env={"OPENAI_API_KEY": ""},
        )

        assert result.exit_code == 0, result.output
        rows = [
            json.loads(line)
            for line in output.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert rows[0]["source_ref"] == "experience:1"
        assert rows[0]["scope"] == "experience"
        assert rows[0]["prompt_version"] == "foster-ossa-experience-summary-v2"


def test_foster_ossa_summary_docs_writes_markdown_documents() -> None:
    with TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        input_summaries = base / "toc-summaries.jsonl"
        output_dir = base / "summary-docs"
        input_summaries.write_text(
            json.dumps(
                {
                    "source_ref": "toc:1.1",
                    "scope": "toc-entry",
                    "validation_status": "generated_valid",
                    "generated_json": json.dumps(
                        {
                            "source_ref": "toc:1.1",
                            "encounter_id": "1.1",
                            "title": "Ossium Gluten",
                            "method_claims": ["Functions matter."],
                            "learner_actions": ["Read endings."],
                            "not_supported_or_unclear": [],
                            "source_refs": ["page:49"],
                        }
                    ),
                }
            )
            + "\n",
            encoding="utf-8",
        )

        result = CliRunner().invoke(
            main,
            [
                "foster-ossa-summary-docs",
                "--input-summaries",
                str(input_summaries),
                "--output-dir",
                str(output_dir),
            ],
        )

        assert result.exit_code == 0, result.output
        assert "wrote: 2" in result.output
        assert (output_dir / "README.md").exists()
        assert "Functions matter." in (output_dir / "experience-1.md").read_text(encoding="utf-8")


def test_invalid_source_refs_from_summary_jsonl_returns_only_invalid_refs() -> None:
    with TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / "summaries.jsonl"
        path.write_text(
            "\n".join(
                [
                    json.dumps({"source_ref": "toc:1.1", "validation_status": "generated_valid"}),
                    json.dumps({"source_ref": "toc:1.2", "validation_status": "generated_invalid"}),
                    json.dumps({"source_ref": "toc:1.3", "validation_status": "generated_invalid"}),
                    json.dumps({"source_ref": "toc:1.4", "validation_status": "planned"}),
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        refs = invalid_source_refs_from_summary_jsonl(path)

        assert refs == ["toc:1.2", "toc:1.3"]


def test_foster_ossa_summarize_retry_only_filters_to_invalid_rows() -> None:
    with TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        source = base / "foster-ossa-pages.jsonl"
        db_path = base / "foster_ossa.duckdb"
        output = base / "summaries.jsonl"
        prior = base / "prior-summaries.jsonl"
        _write_page_jsonl(source)
        _build_test_db(source, db_path)
        prior.write_text(
            json.dumps({"source_ref": "toc:1.1", "validation_status": "generated_invalid"}) + "\n",
            encoding="utf-8",
        )

        result = CliRunner().invoke(
            main,
            [
                "foster-ossa-summarize",
                "--db",
                str(db_path),
                "--scope",
                "toc-entry",
                "--output",
                str(output),
                "--retry-only",
                str(prior),
                "--dry-run",
            ],
            env={"OPENAI_API_KEY": ""},
        )

        assert result.exit_code == 0, result.output
        assert "planned: 1" in result.output


def test_foster_ossa_summarize_retry_only_reports_no_invalid_rows() -> None:
    with TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        prior = base / "prior-summaries.jsonl"
        prior.write_text(
            json.dumps({"source_ref": "toc:1.1", "validation_status": "generated_valid"}) + "\n",
            encoding="utf-8",
        )

        result = CliRunner().invoke(
            main,
            [
                "foster-ossa-summarize",
                "--scope",
                "toc-entry",
                "--output",
                str(base / "out.jsonl"),
                "--retry-only",
                str(prior),
                "--dry-run",
            ],
            env={"OPENAI_API_KEY": ""},
        )

        assert result.exit_code == 0, result.output
        assert "no invalid rows found" in result.output
