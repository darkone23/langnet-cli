from __future__ import annotations

import tempfile
from pathlib import Path

from click.testing import CliRunner

from langnet.cli import main
from langnet.reader.ogl_audit import audit_ogl_imports, write_ogl_view_comparison_artifact
from langnet.reader.storage import create_catalog_db

SELECTED_SEGMENT_COUNT = 2
FIXTURE_TOKEN_COUNT = 3


def _write_tei(
    path: Path,
    *,
    urn: str,
    title: str,
    author: str,
    paragraphs: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(f'<p n="{index}">{text}</p>' for index, text in enumerate(paragraphs, 1))
    path.write_text(
        f"""
        <TEI xml:lang="lat">
          <teiHeader>
            <fileDesc>
              <titleStmt>
                <title>{title}</title>
                <author>{author}</author>
              </titleStmt>
            </fileDesc>
          </teiHeader>
          <text>
            <body>
              <div type="edition" n="{urn}">
                {body}
              </div>
            </body>
          </text>
        </TEI>
        """,
        encoding="utf-8",
    )


def test_ogl_audit_reports_source_view_comparison_samples() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        source_root = root / "patrologia"
        create_catalog_db(catalog_path)
        urn = "urn:cts:latinLit:stoa0001.stoa001.opp-lat1"
        _write_tei(
            source_root / "data" / "stoa0001" / "stoa001" / "stoa0001.stoa001.opp-lat1.xml",
            urn=urn,
            title="Selected Title",
            author="Selected Author",
            paragraphs=["alpha beta", "gamma"],
        )
        _write_tei(
            source_root / "corrected" / "stoa0001" / "stoa001" / "stoa0001.stoa001.opp-lat1.xml",
            urn=urn,
            title="Corrected Title",
            author="Corrected Author",
            paragraphs=["alpha beta gamma"],
        )

        payload = audit_ogl_imports(
            catalog_path=catalog_path,
            roots={"opengreekandlatin_patrologia": source_root},
            sample_limit=5,
        )

    item = payload["items"][0]
    assert item["view_comparison_sample_count"] == 1
    comparison = item["view_comparison_samples"][0]
    assert comparison["work_key"] == "urn:cts:latinLit:stoa0001.stoa001"
    assert comparison["selected"]["source_view"] == "data"
    assert comparison["selected"]["segment_count"] == SELECTED_SEGMENT_COUNT
    assert comparison["selected"]["token_count"] == FIXTURE_TOKEN_COUNT
    assert comparison["selected"]["title"] == "Selected Title"
    assert comparison["alternate"]["source_view"] == "alternate_view_corrected"
    assert comparison["alternate"]["segment_count"] == 1
    assert comparison["alternate"]["token_count"] == FIXTURE_TOKEN_COUNT
    assert comparison["alternate"]["title"] == "Corrected Title"
    assert comparison["differences"] == {
        "segment_delta": -1,
        "token_delta": 0,
        "title_changed": True,
        "author_changed": True,
    }


def test_write_ogl_view_comparison_artifact_writes_json_and_tsv() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        source_root = root / "patrologia"
        output_dir = root / "audit"
        urn = "urn:cts:latinLit:stoa0001.stoa001.opp-lat1"
        _write_tei(
            source_root / "data" / "stoa0001" / "stoa001" / "stoa0001.stoa001.opp-lat1.xml",
            urn=urn,
            title="Selected Title",
            author="Selected Author",
            paragraphs=["alpha beta", "gamma"],
        )
        _write_tei(
            source_root / "corrected" / "stoa0001" / "stoa001" / "stoa0001.stoa001.opp-lat1.xml",
            urn=urn,
            title="Corrected Title",
            author="Corrected Author",
            paragraphs=["alpha beta gamma"],
        )
        _write_tei(
            source_root / "split" / "stoa0001" / "stoa001" / "stoa0001.stoa001.opp-lat1.xml",
            urn=urn,
            title="Split Title",
            author="Selected Author",
            paragraphs=["alpha", "beta", "gamma"],
        )

        payload = write_ogl_view_comparison_artifact(
            root=source_root,
            collection_id="opengreekandlatin_patrologia",
            output_dir=output_dir,
            limit_per_view=1,
        )

        assert payload["summary"]["comparison_count"] == SELECTED_SEGMENT_COUNT
        json_path = Path(str(payload["outputs"]["json_path"]))
        tsv_path = Path(str(payload["outputs"]["tsv_path"]))
        assert json_path.exists()
        assert tsv_path.exists()
        tsv_text = tsv_path.read_text(encoding="utf-8")
        assert "alternate_view\twork_key" in tsv_text
        assert "alternate_view_corrected\turn:cts:latinLit:stoa0001.stoa001" in tsv_text
        assert "alternate_view_split\turn:cts:latinLit:stoa0001.stoa001" in tsv_text


def test_reader_cli_ogl_view_comparison_writes_artifacts() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        source_root = root / "patrologia"
        output_dir = root / "audit"
        urn = "urn:cts:latinLit:stoa0001.stoa001.opp-lat1"
        _write_tei(
            source_root / "data" / "stoa0001" / "stoa001" / "stoa0001.stoa001.opp-lat1.xml",
            urn=urn,
            title="Selected Title",
            author="Selected Author",
            paragraphs=["alpha beta", "gamma"],
        )
        _write_tei(
            source_root / "corrected" / "stoa0001" / "stoa001" / "stoa0001.stoa001.opp-lat1.xml",
            urn=urn,
            title="Corrected Title",
            author="Corrected Author",
            paragraphs=["alpha beta gamma"],
        )

        result = CliRunner().invoke(
            main,
            [
                "reader",
                "ogl-view-comparison",
                "--collection",
                "opengreekandlatin_patrologia",
                "--root",
                str(source_root),
                "--output-dir",
                str(output_dir),
                "--limit-per-view",
                "1",
                "--alternate-view",
                "alternate_view_corrected",
                "--output",
                "json",
            ],
        )

        assert result.exit_code == 0, result.output
        assert (output_dir / "opengreekandlatin_patrologia_source_view_comparison.json").exists()
        assert (output_dir / "opengreekandlatin_patrologia_source_view_comparison.tsv").exists()
