from __future__ import annotations

import tempfile
from contextlib import contextmanager
from os import chdir
from pathlib import Path

import duckdb

from langnet.reader.models import (
    ReaderBookArtifact,
    ReaderEdition,
    ReaderSegment,
    ReaderSegmentAddress,
    ReaderWork,
    ReaderWorkClassification,
)
from langnet.reader.search_index import (
    build_reader_search_index,
    inspect_reader_search_query,
    reader_search_index_status,
    search_reader_segments,
)
from langnet.reader.storage import (
    create_book_db,
    create_catalog_db,
    register_book,
    register_segment_rows,
    register_work_classifications,
)

SEARCH_FIXTURE_SEGMENT_COUNT = 5
SEARCH_FIXTURE_LANGUAGE_COUNTS = {"grc": 2, "lat": 2, "san": 1}
SEARCH_APPENDED_SEGMENT_COUNT = 4
SEARCH_LATE_OPTIONAL_COLUMN_SEGMENT_COUNT = 106


@contextmanager
def _temporary_cwd(path: Path):
    previous = Path.cwd()
    chdir(path)
    try:
        yield
    finally:
        chdir(previous)


def test_build_reader_search_index_writes_normalized_segment_rows() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = _write_search_fixture(root)
        index_path = root / "reader-search.lance"

        summary = build_reader_search_index(catalog_path, index_path, replace=True)
        status = reader_search_index_status(index_path)

        assert summary["backend"] == "duckdb-lance"
        assert summary["fts_indexed"] is True
        assert summary["segment_count"] == SEARCH_FIXTURE_SEGMENT_COUNT
        assert summary["language_counts"] == SEARCH_FIXTURE_LANGUAGE_COUNTS
        assert status["exists"] is True
        assert status["backend"] == "duckdb-lance"
        assert status["segment_count"] == SEARCH_FIXTURE_SEGMENT_COUNT
        assert status["normalizer_version"] == "reader-search-normalizer-v1"
        assert set(status["fts_indexes"]) == {
            "search_text_folded_idx",
            "search_text_idx",
            "token_text_idx",
        }


def test_build_reader_search_index_appends_to_existing_dataset() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = _write_search_fixture(root)
        index_path = root / "reader-search.lance"

        first = build_reader_search_index(
            catalog_path,
            index_path,
            language="grc",
            replace=True,
            batch_size=1,
        )
        second = build_reader_search_index(
            catalog_path,
            index_path,
            language="lat",
            replace=False,
            batch_size=1,
        )
        status = reader_search_index_status(index_path)

        assert first["language_counts"] == {"grc": 2}
        assert second["language_counts"] == {"lat": 2}
        assert status["segment_count"] == SEARCH_APPENDED_SEGMENT_COUNT
        assert status["language_counts"] == {"grc": 2, "lat": 2}


def test_build_reader_search_index_handles_late_non_null_optional_columns() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = _write_search_fixture(root)
        _register_fixture_work(
            root,
            catalog_path,
            work_id="grc.cts.work",
            collection_id="greek_fixture",
            language="grc",
            title="Greek CTS Work",
            author="Greek Author",
            source_id="grc999",
            cts_work_urn="urn:cts:greekLit:tlg0001.tlg001",
            segments=[
                (f"grc-cts-{idx}", str(idx), f"λόγος {idx}", f"λογος {idx}", 100 + idx)
                for idx in range(1, 105)
            ],
        )
        index_path = root / "reader-search.lance"

        summary = build_reader_search_index(catalog_path, index_path, language="grc", replace=True)
        status = reader_search_index_status(index_path)

        assert summary["segment_count"] == SEARCH_LATE_OPTIONAL_COLUMN_SEGMENT_COUNT
        assert status["segment_count"] == SEARCH_LATE_OPTIONAL_COLUMN_SEGMENT_COUNT


def test_search_reader_segments_matches_folded_language_queries_and_filters() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = _write_search_fixture(root)
        index_path = root / "reader-search.lance"
        build_reader_search_index(catalog_path, index_path, replace=True)

        greek = search_reader_segments(
            catalog_path,
            index_path,
            "λογος",
            language="grc",
            limit=5,
        )
        sanskrit = search_reader_segments(
            catalog_path,
            index_path,
            "sankara",
            language="san",
            limit=5,
        )
        latin = search_reader_segments(
            catalog_path,
            index_path,
            "iulius uiuit",
            language="lat",
            collection_id="latin_fixture",
            limit=5,
        )

        assert greek["items"][0]["citation_path"] == "1"
        assert greek["items"][0]["language"] == "grc"
        assert sanskrit["items"][0]["title"] == "Brahmasutrabhasya"
        assert latin["items"][0]["citation_path"] == "2"


def test_search_reader_segments_can_return_context_windows() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = _write_search_fixture(root)
        index_path = root / "reader-search.lance"
        build_reader_search_index(catalog_path, index_path, replace=True)

        payload = search_reader_segments(
            catalog_path,
            index_path,
            "venit",
            language="lat",
            context=1,
            limit=1,
        )

        item = payload["items"][0]
        assert item["citation_path"] == "1"
        assert [row["citation_path"] for row in item["context_after"]] == ["2"]


def test_search_reader_segments_reads_context_from_book_artifacts() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = _write_search_fixture(root)
        index_path = root / "reader-search.lance"
        build_reader_search_index(catalog_path, index_path, replace=True)

        with duckdb.connect(str(root / "books" / "lat001.duckdb")) as conn:
            conn.execute(
                "UPDATE segments SET text = ? WHERE segment_id = ?",
                ["Canonical context after.", "lat-2"],
            )

        payload = search_reader_segments(
            catalog_path,
            index_path,
            "venit",
            language="lat",
            context=1,
            limit=1,
        )

        item = payload["items"][0]
        assert item["citation_path"] == "1"
        assert [row["text"] for row in item["context_after"]] == ["Canonical context after."]


def test_search_reader_segments_resolves_repo_relative_book_artifacts() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        source_catalog_path = _write_search_fixture(root)
        catalog_dir = root / "examples" / "debug" / "reader_full_curated_current"
        catalog_dir.mkdir(parents=True)
        catalog_path = catalog_dir / "catalog.duckdb"
        source_catalog_path.replace(catalog_path)
        (catalog_dir / "books").mkdir()
        (root / "books" / "lat001.duckdb").replace(catalog_dir / "books" / "lat001.duckdb")
        index_path = root / "reader-search.lance"
        repo_relative_book_path = Path(
            "examples/debug/reader_full_curated_current/books/lat001.duckdb"
        )

        with duckdb.connect(str(catalog_path)) as conn:
            conn.execute(
                "UPDATE artifacts SET artifact_path = ? WHERE work_id = ?",
                [str(repo_relative_book_path), "lat.work"],
            )
        with _temporary_cwd(root):
            build_reader_search_index(catalog_path, index_path, replace=True)
            payload = search_reader_segments(
                catalog_path,
                index_path,
                "venit",
                language="lat",
                context=1,
                limit=1,
            )

        item = payload["items"][0]
        assert item["citation_path"] == "1"
        assert [row["citation_path"] for row in item["context_after"]] == ["2"]


def test_search_reader_segments_fuzzy_expands_greek_transliteration() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = _write_search_fixture(root)
        index_path = root / "reader-search.lance"
        build_reader_search_index(catalog_path, index_path, replace=True)

        logos = search_reader_segments(
            catalog_path,
            index_path,
            "logos",
            language="grc",
            mode="fuzzy",
            limit=5,
        )
        andra = search_reader_segments(
            catalog_path,
            index_path,
            "andra",
            language="grc",
            mode="fuzzy",
            limit=5,
        )

        assert logos["items"][0]["citation_path"] == "1"
        assert logos["request"]["query_candidates"][1]["query"] == "λογοσ"
        assert logos["items"][0]["matched_query"] == "λογοσ"
        assert logos["items"][0]["match_type"] == "transliteration_expansion"
        assert logos["items"][0]["candidate_rank"] > 0
        assert andra["items"][0]["citation_path"] == "2"
        assert andra["items"][0]["matched_query"] == "ανδρα"


def test_inspect_reader_search_query_reports_fuzzy_candidates() -> None:
    payload = inspect_reader_search_query("grc", "logos", mode="fuzzy", field="auto")
    sanskrit = inspect_reader_search_query("san", "sankara", mode="fuzzy", field="auto")

    assert payload["language"] == "grc"
    assert payload["input"] == "logos"
    assert payload["mode"] == "fuzzy"
    assert payload["candidates"][0]["query"] == "logos"
    assert {
        "query": "λογοσ",
        "kind": "transliteration_expansion",
        "field": "search_text_folded",
        "rank": 1,
    } in payload["candidates"]
    assert {
        "query": "samkara",
        "kind": "normalized_surface",
        "field": "search_text_folded",
        "rank": 1,
    } in sanskrit["candidates"]


def _write_search_fixture(root: Path) -> Path:
    catalog_path = root / "catalog.duckdb"
    create_catalog_db(catalog_path)
    _register_fixture_work(
        root,
        catalog_path,
        work_id="lat.work",
        collection_id="latin_fixture",
        language="lat",
        title="Latin Work",
        author="Latin Author",
        source_id="lat001",
        segments=[
            ("lat-1", "1", "Iulius venit.", "iulius venit", 1),
            ("lat-2", "2", "Julius vivit.", "julius vivit", 2),
        ],
    )
    _register_fixture_work(
        root,
        catalog_path,
        work_id="grc.work",
        collection_id="greek_fixture",
        language="grc",
        title="Greek Work",
        author="Greek Author",
        source_id="grc001",
        segments=[
            ("grc-1", "1", "Λόγος τις ἐστίν.", "λογος τις εστιν", 1),
            ("grc-2", "2", "ἄνδρα μοι ἔννεπε.", "ανδρα μοι εννεπε", 2),
        ],
    )
    _register_fixture_work(
        root,
        catalog_path,
        work_id="san.work",
        collection_id="sanskrit_fixture",
        language="san",
        title="Brahmasutrabhasya",
        author="Śaṃkara",
        source_id="san001",
        segments=[("san-1", "1", "Śaṃkara uvāca.", "samkara uvaca", 1)],
    )
    register_work_classifications(
        catalog_path,
        [
            ReaderWorkClassification(
                work_id="san.work",
                category="Philosophy",
                period="classical",
                date_range="",
                authorship_status="traditional",
                popularity_score=90,
                popularity_tier="high",
                confidence="medium",
                note="fixture",
                generator_models="fixture",
                generator_run_id="fixture",
                discovery_group_id="philosophy",
                discovery_tags="vedanta|commentary",
            )
        ],
    )
    return catalog_path


def _register_fixture_work(  # noqa: PLR0913
    root: Path,
    catalog_path: Path,
    *,
    work_id: str,
    collection_id: str,
    language: str,
    title: str,
    author: str,
    source_id: str,
    segments: list[tuple[str, str, str, str, int]],
    cts_work_urn: str | None = None,
) -> None:
    book_path = root / "books" / f"{source_id}.duckdb"
    create_book_db(book_path)
    edition = ReaderEdition(
        edition_id=f"{work_id}.edition",
        work_id=work_id,
        label="Fixture edition",
        language=language,
        source_path=root / f"{source_id}.xml",
    )
    register_book(
        catalog_path,
        ReaderWork(
            work_id=work_id,
            collection_id=collection_id,
            language=language,
            title=title,
            author=author,
            author_id=f"{language}.author",
            source_id=source_id,
            cts_work_urn=cts_work_urn,
        ),
        edition,
        ReaderBookArtifact(
            artifact_id=f"{work_id}.artifact",
            work_id=work_id,
            edition_id=edition.edition_id,
            artifact_path=book_path,
            source_path=edition.source_path,
            adapter="fixture",
            source_hash="hash",
            segment_count=len(segments),
            token_count=sum(len(text.split()) for _, _, text, _, _ in segments),
        ),
    )
    register_segment_rows(
        book_path,
        segments=[
            ReaderSegment(
                segment_id=segment_id,
                work_id=work_id,
                edition_id=edition.edition_id,
                segment_kind="line",
                citation_path=citation_path,
                text=text,
                normalized_text=normalized_text,
                sort_key=sort_key,
            )
            for segment_id, citation_path, text, normalized_text, sort_key in segments
        ],
        addresses=[
            ReaderSegmentAddress(
                segment_id=segment_id,
                address=f"{work_id}:{citation_path}",
                address_kind="fixture",
                citation_path=citation_path,
            )
            for segment_id, citation_path, _, _, _ in segments
        ],
    )
