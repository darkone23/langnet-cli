from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from unittest import mock

import duckdb

from langnet.reader.builder import ReaderBuildConfig, ReaderBuilder
from langnet.reader.validation import validate_reader_catalog

FIXTURES = Path("tests/fixtures/reader")


def _copy_fixture(name: str, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(FIXTURES / name, target_dir / name)


def _build_fixture_catalog(root: Path) -> Path:
    perseus_dir = root / "perseus"
    sanskrit_dir = root / "sanskrit"
    _copy_fixture("perseus_odyssey.xml", perseus_dir)
    _copy_fixture("sanskrit_raghuvamsa.json", sanskrit_dir)
    result = ReaderBuilder(
        ReaderBuildConfig(
            perseus_dir=perseus_dir,
            sanskrit_dir=sanskrit_dir,
            alias_dir=Path("data/curated/reader_aliases"),
            output_root=root / "build" / "reader",
        )
    ).build()
    return result.output_path


def test_validate_reader_catalog_accepts_fixture_build() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        catalog_path = _build_fixture_catalog(Path(tmpdir))

        assert validate_reader_catalog(catalog_path) == []


def test_validate_reader_catalog_reports_alias_conflict() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        catalog_path = _build_fixture_catalog(Path(tmpdir))
        with duckdb.connect(str(catalog_path)) as conn:
            conn.execute(
                """
                INSERT INTO aliases (alias, language, kind, target, display, source_file, sources)
                VALUES (
                    'Od.', 'grc', 'work_abbreviation', 'other:target', 'Other', 'test', 'manual'
                )
                """
            )

        issues = validate_reader_catalog(catalog_path)

        assert any(issue["code"] == "alias_conflict" for issue in issues)


def test_validate_reader_catalog_reports_unresolved_alias_target() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        catalog_path = _build_fixture_catalog(Path(tmpdir))
        with duckdb.connect(str(catalog_path)) as conn:
            conn.execute(
                """
                INSERT INTO aliases (alias, language, kind, target, display, source_file, sources)
                VALUES (
                    'Missing Work',
                    'grc',
                    'title',
                    'urn:cts:greekLit:tlg9999.tlg999',
                    'Missing Work',
                    'test',
                    'manual'
                )
                """
            )

        issues = validate_reader_catalog(catalog_path)

        assert any(issue["code"] == "alias_target_missing" for issue in issues)


def test_validate_reader_catalog_reports_missing_legacy_cts_work_urn() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        catalog_path = _build_fixture_catalog(Path(tmpdir))
        with duckdb.connect(str(catalog_path)) as conn:
            conn.execute(
                """
                INSERT INTO works (
                    work_id,
                    collection_id,
                    language,
                    title,
                    author,
                    author_id,
                    source_id,
                    cts_work_urn
                )
                VALUES (
                    'langnet:reader:tlg:tlg0012.001',
                    'tlg',
                    'grc',
                    'Iliad',
                    'Homer',
                    'tlg0012',
                    'tlg0012.001',
                    NULL
                )
                """
            )

        issues = validate_reader_catalog(catalog_path)

        assert any(issue["code"] == "legacy_cts_work_urn_missing" for issue in issues)


def test_validate_reader_catalog_reports_missing_artifact_path() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        catalog_path = _build_fixture_catalog(Path(tmpdir))
        with duckdb.connect(str(catalog_path)) as conn:
            conn.execute(
                """
                UPDATE artifacts
                SET artifact_path = 'missing.duckdb'
                WHERE artifact_id = (SELECT artifact_id FROM artifacts LIMIT 1)
                """
            )

        issues = validate_reader_catalog(catalog_path)

        assert any(issue["code"] == "artifact_missing" for issue in issues)


def test_validate_reader_catalog_scans_shared_artifact_path_once() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        catalog_path = _build_fixture_catalog(Path(tmpdir))
        with duckdb.connect(str(catalog_path)) as conn:
            first_path = conn.execute("SELECT artifact_path FROM artifacts LIMIT 1").fetchone()[0]
            conn.execute(
                """
                INSERT INTO artifacts (
                    artifact_id, work_id, edition_id, artifact_path, source_path, adapter,
                    source_hash, segment_count, token_count
                )
                SELECT
                    artifact_id || ':duplicate', work_id, edition_id, artifact_path,
                    source_path, adapter, source_hash, segment_count, token_count
                FROM artifacts
                LIMIT 1
                """
            )
        calls: list[str] = []
        original = duckdb.connect

        def tracking_connect(path, *args, **kwargs):
            if str(path) == str(first_path):
                calls.append(str(path))
            return original(path, *args, **kwargs)

        with mock.patch("duckdb.connect", side_effect=tracking_connect):
            issues = validate_reader_catalog(catalog_path)

    assert issues == []
    assert calls == [str(first_path)]


def test_validate_reader_catalog_reports_missing_book_table() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        catalog_path = _build_fixture_catalog(Path(tmpdir))
        artifact_path = _first_artifact_path(catalog_path)
        with duckdb.connect(str(artifact_path)) as conn:
            conn.execute("DROP TABLE addresses")

        issues = validate_reader_catalog(catalog_path)

        assert any(issue["code"] == "book_table_missing" for issue in issues)


def test_validate_reader_catalog_reports_zero_segment_artifact() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        catalog_path = _build_fixture_catalog(Path(tmpdir))
        with duckdb.connect(str(catalog_path)) as conn:
            conn.execute(
                """
                UPDATE artifacts
                SET segment_count = 0
                WHERE artifact_id = (SELECT artifact_id FROM artifacts LIMIT 1)
                """
            )

        issues = validate_reader_catalog(catalog_path)

        assert any(issue["code"] == "artifact_zero_segments" for issue in issues)


def test_validate_reader_catalog_reports_legacy_markup_in_work_metadata() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        catalog_path = _build_fixture_catalog(Path(tmpdir))
        with duckdb.connect(str(catalog_path)) as conn:
            conn.execute(
                """
                UPDATE works
                SET author = '&1Homerus& Epic.'
                WHERE work_id = (SELECT work_id FROM works LIMIT 1)
                """
            )

        issues = validate_reader_catalog(catalog_path)

        assert any(issue["code"] == "work_metadata_markup" for issue in issues)


def test_validate_reader_catalog_reports_blank_segment_text() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        catalog_path = _build_fixture_catalog(Path(tmpdir))
        artifact_path = _first_artifact_path(catalog_path)
        with duckdb.connect(str(artifact_path)) as conn:
            conn.execute(
                """
                UPDATE segments
                SET text = ''
                WHERE segment_id = (SELECT segment_id FROM segments LIMIT 1)
                """
            )

        issues = validate_reader_catalog(catalog_path)

        assert any(issue["code"] == "segment_blank_text" for issue in issues)


def test_validate_reader_catalog_reports_segment_markup_leakage() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        catalog_path = _build_fixture_catalog(Path(tmpdir))
        artifact_path = _first_artifact_path(catalog_path)
        with duckdb.connect(str(artifact_path)) as conn:
            conn.execute(
                """
                UPDATE segments
                SET text = '&1Homerus& Epic.'
                WHERE segment_id = (SELECT segment_id FROM segments LIMIT 1)
                """
            )

        issues = validate_reader_catalog(catalog_path)

        assert any(issue["code"] == "segment_text_markup" for issue in issues)


def test_validate_reader_catalog_reports_xml_like_segment_markup() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        catalog_path = _build_fixture_catalog(Path(tmpdir))
        artifact_path = _first_artifact_path(catalog_path)
        with duckdb.connect(str(artifact_path)) as conn:
            conn.execute(
                """
                UPDATE segments
                SET text = 'Visible text <note type="footnote">editorial note</note>'
                WHERE segment_id = (SELECT segment_id FROM segments LIMIT 1)
                """
            )

        issues = validate_reader_catalog(catalog_path)

        assert any(issue["code"] == "segment_text_markup" for issue in issues)


def test_validate_reader_catalog_allows_angle_bracket_editorial_sigla() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        catalog_path = _build_fixture_catalog(Path(tmpdir))
        artifact_path = _first_artifact_path(catalog_path)
        with duckdb.connect(str(artifact_path)) as conn:
            conn.execute(
                """
                UPDATE segments
                SET text = 'The note cites <Kr.) and later prints 6rg>ieus.'
                WHERE segment_id = (SELECT segment_id FROM segments LIMIT 1)
                """
            )

        issues = validate_reader_catalog(catalog_path)

        assert not any(issue["code"] == "segment_text_markup" for issue in issues)


def test_validate_reader_catalog_allows_editorial_angle_bracket_words() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        catalog_path = _build_fixture_catalog(Path(tmpdir))
        artifact_path = _first_artifact_path(catalog_path)
        with duckdb.connect(str(artifact_path)) as conn:
            conn.execute(
                """
                UPDATE segments
                SET text = 'The <Pisidians> carried shields, and the text supplies <et>.'
                WHERE segment_id = (SELECT segment_id FROM segments LIMIT 1)
                """
            )

        issues = validate_reader_catalog(catalog_path)

        assert not any(issue["code"] == "segment_text_markup" for issue in issues)


def test_validate_reader_catalog_allows_monetary_dollar_signs_in_segments() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        catalog_path = _build_fixture_catalog(Path(tmpdir))
        artifact_path = _first_artifact_path(catalog_path)
        with duckdb.connect(str(artifact_path)) as conn:
            conn.execute(
                """
                UPDATE segments
                SET text = 'The tribute was $583,200 in the translator note.'
                WHERE segment_id = (SELECT segment_id FROM segments LIMIT 1)
                """
            )

        issues = validate_reader_catalog(catalog_path)

        assert not any(issue["code"] == "segment_text_markup" for issue in issues)


def _first_artifact_path(catalog_path: Path) -> Path:
    with duckdb.connect(str(catalog_path)) as conn:
        row = conn.execute("SELECT artifact_path FROM artifacts LIMIT 1").fetchone()
    if row is None:
        msg = "fixture catalog has no artifacts"
        raise AssertionError(msg)
    return Path(str(row[0]))
