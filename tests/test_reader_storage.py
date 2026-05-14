from __future__ import annotations

import tempfile
from pathlib import Path
from unittest import mock

import duckdb

from langnet.reader.models import (
    ReaderAlias,
    ReaderAuthor,
    ReaderBookArtifact,
    ReaderBookPathParts,
    ReaderContainedWork,
    ReaderEdition,
    ReaderMetadataAttribution,
    ReaderMetadataOverlayEvidence,
    ReaderSegment,
    ReaderSegmentAddress,
    ReaderWork,
)
from langnet.reader.paths import reader_book_path, reader_catalog_path, reader_root
from langnet.reader.storage import (
    create_book_db,
    create_catalog_db,
    list_author_index,
    list_duplicate_audit,
    list_metadata_attributions,
    list_metadata_overlays,
    list_segments_for_work,
    list_works,
    lookup_artifact_for_address,
    lookup_segment_by_address,
    lookup_segment_by_work_and_citation,
    register_book,
    register_books,
    register_contained_works,
    register_metadata_attributions,
    register_segment_rows,
)


def test_reader_paths_are_under_build_reader() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        data_root = Path(tmpdir)
        root = reader_root(data_root)
        assert root == data_root / "build" / "reader"
        assert reader_catalog_path(data_root) == data_root / "build" / "reader" / "catalog.duckdb"
        assert reader_book_path(
            ReaderBookPathParts(
                collection="perseus",
                namespace="greekLit",
                author_id="tlg0012",
                work_id="tlg002",
                edition_id="perseus-grc2",
            ),
            data_root=data_root,
        ) == (
            data_root
            / "build"
            / "reader"
            / "books"
            / "perseus"
            / "greekLit"
            / "tlg0012"
            / "tlg002"
            / "perseus-grc2.duckdb"
        )


def test_reader_model_minimum_fields() -> None:
    segment = ReaderSegment(
        segment_id="seg-1",
        work_id="urn:cts:greekLit:tlg0012.tlg002",
        edition_id="urn:cts:greekLit:tlg0012.tlg002.perseus-grc2",
        segment_kind="line",
        citation_path="3.74",
        text="ψυχὰς παρθέμενοι",
        normalized_text="ψυχας παρθεμενοι",
        sort_key=74,
    )
    alias = ReaderAlias(
        alias="Od.",
        language="grc",
        kind="work_abbreviation",
        target="urn:cts:greekLit:tlg0012.tlg002",
        display="Homer, Odyssey",
        source_file="tests/fixtures/reader/aliases/greek/homer.yaml",
        sources=("lsj", "manual"),
    )
    author = ReaderAuthor(
        author_id="urn:cts:greekLit:tlg0012",
        collection_id="perseus",
        language="grc",
        name="Homer",
        source_id="tlg0012",
    )
    assert segment.citation_path == "3.74"
    assert alias.target.endswith("tlg002")
    assert author.name == "Homer"


def test_catalog_routes_address_to_book_db() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        book_path = root / "books" / "odyssey.duckdb"
        create_catalog_db(catalog_path)
        create_book_db(book_path)

        work = ReaderWork(
            work_id="urn:cts:greekLit:tlg0012.tlg002",
            collection_id="perseus",
            language="grc",
            title="Odyssey",
            author="Homer",
            author_id="urn:cts:greekLit:tlg0012",
            source_id="tlg0012.tlg002",
            cts_work_urn="urn:cts:greekLit:tlg0012.tlg002",
        )
        edition = ReaderEdition(
            edition_id="urn:cts:greekLit:tlg0012.tlg002.perseus-grc2",
            work_id=work.work_id,
            label="Perseus Greek edition",
            language="grc",
            source_path=root / "odyssey.xml",
            cts_edition_urn="urn:cts:greekLit:tlg0012.tlg002.perseus-grc2",
        )
        artifact = ReaderBookArtifact(
            artifact_id="odyssey-grc2",
            work_id=work.work_id,
            edition_id=edition.edition_id,
            artifact_path=book_path,
            source_path=root / "odyssey.xml",
            adapter="fixture",
            source_hash="hash",
            segment_count=1,
            token_count=2,
        )
        register_book(catalog_path, work, edition, artifact)
        register_segment_rows(
            book_path,
            segments=[
                ReaderSegment(
                    segment_id="odyssey-3-74",
                    work_id=work.work_id,
                    edition_id=edition.edition_id,
                    segment_kind="line",
                    citation_path="3.74",
                    text="ψυχὰς παρθέμενοι",
                    source_text="ψυχὰς παρθέμενοι [source]",
                    normalized_text="ψυχας παρθεμενοι",
                    sort_key=74,
                )
            ],
            addresses=[
                ReaderSegmentAddress(
                    segment_id="odyssey-3-74",
                    address="urn:cts:greekLit:tlg0012.tlg002:3.74",
                    address_kind="cts",
                    citation_path="3.74",
                ),
                ReaderSegmentAddress(
                    segment_id="odyssey-3-74",
                    address="Od. 3.74",
                    address_kind="alias",
                    citation_path="3.74",
                ),
            ],
        )

        routed = lookup_artifact_for_address(catalog_path, "urn:cts:greekLit:tlg0012.tlg002:3.74")
        segment = lookup_segment_by_address(catalog_path, "Od. 3.74")
        works = list_works(catalog_path, language="grc")

        assert routed is not None
        assert routed["artifact_path"] == str(book_path)
        assert segment is not None
        assert segment["text"] == "ψυχὰς παρθέμενοι"
        assert segment["source_text"] == "ψυχὰς παρθέμενοι [source]"
        assert works == [
            {
                "work_id": work.work_id,
                "collection_id": "perseus",
                "language": "grc",
                "title": "Odyssey",
                "author": "Homer",
                "author_id": "urn:cts:greekLit:tlg0012",
                "source_id": "tlg0012.tlg002",
                "cts_work_urn": work.cts_work_urn,
                "work_kind": "work",
                "parent_work_id": None,
                "start_citation": None,
                "end_citation": None,
            }
        ]


def test_contained_work_lists_and_reads_parent_segments() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        book_path = root / "books" / "mahabharata.duckdb"
        create_catalog_db(catalog_path)
        create_book_db(book_path)
        work = ReaderWork(
            work_id="langnet:reader:sanskrit_dcs:dcs_154",
            collection_id="sanskrit_dcs",
            language="san",
            title="Mahābhārata",
            author="Unknown",
            author_id=None,
            source_id="dcs_154",
            cts_work_urn=None,
        )
        edition = ReaderEdition(
            edition_id=f"{work.work_id}:edition",
            work_id=work.work_id,
            label="DCS edition",
            language="san",
            source_path=root / "mahabharata.conllu",
            cts_edition_urn=None,
        )
        register_book(
            catalog_path,
            work,
            edition,
            ReaderBookArtifact(
                artifact_id="mbh-artifact",
                work_id=work.work_id,
                edition_id=edition.edition_id,
                artifact_path=book_path,
                source_path=edition.source_path,
                adapter="fixture",
                source_hash="hash",
                segment_count=4,
                token_count=20,
            ),
        )
        register_segment_rows(
            book_path,
            segments=[
                ReaderSegment(
                    segment_id=f"{work.work_id}:a",
                    work_id=work.work_id,
                    edition_id=edition.edition_id,
                    segment_kind="sentence",
                    citation_path="before",
                    text="before",
                    normalized_text="before",
                    sort_key=1,
                ),
                ReaderSegment(
                    segment_id=f"{work.work_id}:start",
                    work_id=work.work_id,
                    edition_id=edition.edition_id,
                    segment_kind="sentence",
                    citation_path="start",
                    text="dharmakṣetre",
                    normalized_text="dharmaksetre",
                    sort_key=2,
                ),
                ReaderSegment(
                    segment_id=f"{work.work_id}:end",
                    work_id=work.work_id,
                    edition_id=edition.edition_id,
                    segment_kind="sentence",
                    citation_path="end",
                    text="yatra yogeśvaraḥ kṛṣṇaḥ",
                    normalized_text="yatra yogesvarah krsnah",
                    sort_key=3,
                ),
                ReaderSegment(
                    segment_id=f"{work.work_id}:after",
                    work_id=work.work_id,
                    edition_id=edition.edition_id,
                    segment_kind="sentence",
                    citation_path="after",
                    text="after",
                    normalized_text="after",
                    sort_key=4,
                ),
            ],
            addresses=[],
        )
        register_contained_works(
            catalog_path,
            [
                ReaderContainedWork(
                    contained_work_id="langnet:reader:contained:sanskrit:bhagavadgita",
                    parent_work_id=work.work_id,
                    collection_id="contained",
                    language="san",
                    title="Bhagavadgītā",
                    author="Vyāsa",
                    source_id="dcs_154:bhagavadgita",
                    cts_work_urn="urn:cts:sanskritLit:mbh.bhg",
                    start_citation="start",
                    end_citation="end",
                    status="accepted",
                    confidence="medium",
                    note="fixture",
                    evidence=(
                        ReaderMetadataOverlayEvidence(
                            source_type="fixture",
                            citation="fixture",
                            label="fixture",
                        ),
                    ),
                )
            ],
        )

        works = list_works(catalog_path, language="san", query="gītā")
        segments = list_segments_for_work(
            catalog_path,
            "langnet:reader:contained:sanskrit:bhagavadgita",
            limit=10,
        )
        shown = lookup_segment_by_work_and_citation(
            catalog_path,
            "urn:cts:sanskritLit:mbh.bhg",
            "start",
        )
        authors = list_author_index(catalog_path, language="san", query="vyāsa")
        vyasa_author_id = next(
            item["author_id"] for item in authors if item["display_name"] == "Vyāsa"
        )
        author_works = list_works(catalog_path, language="san", author_id=vyasa_author_id)

    assert [work["title"] for work in works] == ["Bhagavadgītā"]
    assert any(work["title"] == "Bhagavadgītā" for work in author_works)
    assert [segment["citation_path"] for segment in segments] == ["start", "end"]
    assert shown is not None
    assert shown["text"] == "dharmakṣetre"


def test_duplicate_author_audit_reports_display_collisions_not_many_works() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        book_path = root / "books" / "fixture.duckdb"
        create_catalog_db(catalog_path)
        create_book_db(book_path)

        for work in (
            ReaderWork(
                work_id="langnet:reader:tlg:tlg0532.001",
                collection_id="tlg",
                language="grc",
                title="Leucippe et Clitophon",
                author="Achilles Tatius",
                author_id="urn:cts:greekLit:tlg0532",
                source_id="tlg0532.001",
                cts_work_urn="urn:cts:greekLit:tlg0532.tlg001",
            ),
            ReaderWork(
                work_id="langnet:reader:tlg:tlg2133.001",
                collection_id="tlg",
                language="grc",
                title="Isagoga excerpta",
                author="Achilles Tatius",
                author_id="tlg2133",
                source_id="tlg2133.001",
                cts_work_urn=None,
            ),
            ReaderWork(
                work_id="langnet:reader:tlg:tlg0012.001",
                collection_id="tlg",
                language="grc",
                title="Ilias",
                author="Homer",
                author_id="tlg0012",
                source_id="tlg0012.001",
                cts_work_urn=None,
            ),
            ReaderWork(
                work_id="langnet:reader:tlg:tlg0012.002",
                collection_id="tlg",
                language="grc",
                title="Odyssea",
                author="Homer",
                author_id="tlg0012",
                source_id="tlg0012.002",
                cts_work_urn=None,
            ),
        ):
            edition = ReaderEdition(
                edition_id=f"{work.work_id}:edition",
                work_id=work.work_id,
                label="fixture",
                language=work.language,
                source_path=root / f"{work.source_id}.txt",
                cts_edition_urn=None,
            )
            register_book(
                catalog_path,
                work,
                edition,
                ReaderBookArtifact(
                    artifact_id=f"{work.work_id}:artifact",
                    work_id=work.work_id,
                    edition_id=edition.edition_id,
                    artifact_path=book_path,
                    source_path=edition.source_path,
                    adapter="fixture",
                    source_hash="hash",
                    segment_count=1,
                    token_count=1,
                ),
            )

        audit = list_duplicate_audit(catalog_path, kind="authors", language="grc")

    assert len(audit) == 1
    assert audit[0]["display"] == "Achilles Tatius"
    assert audit[0]["authority_count"] == len(audit[0]["author_ids"])
    assert audit[0]["suggested_policy"] == "review_authority_collision"


def test_register_books_bulk_writes_catalog_rows() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        create_catalog_db(catalog_path)
        entries = []
        for index in range(2):
            work = ReaderWork(
                work_id=f"langnet:reader:test:work{index}",
                collection_id="test",
                language="lat",
                title=f"Work {index}",
                author="Author",
                author_id="urn:cts:latinLit:phi0001",
                source_id=f"work{index}",
                cts_work_urn=f"urn:cts:latinLit:phi0001.phi00{index}" if index else None,
            )
            edition = ReaderEdition(
                edition_id=f"{work.work_id}:edition",
                work_id=work.work_id,
                label="fixture",
                language="lat",
                source_path=root / f"work{index}.txt",
                cts_edition_urn=None,
            )
            artifact = ReaderBookArtifact(
                artifact_id=f"artifact-{index}",
                work_id=work.work_id,
                edition_id=edition.edition_id,
                artifact_path=root / f"work{index}.duckdb",
                source_path=edition.source_path,
                adapter="fixture",
                source_hash=f"hash-{index}",
                segment_count=1,
                token_count=2,
            )
            entries.append((work, edition, artifact))

        register_books(catalog_path, entries)

        with duckdb.connect(str(catalog_path), read_only=True) as conn:
            work_count = conn.execute("SELECT COUNT(*) FROM works").fetchone()[0]
            edition_count = conn.execute("SELECT COUNT(*) FROM editions").fetchone()[0]
            artifact_count = conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]

    assert (work_count, edition_count, artifact_count) == (2, 2, 2)


def test_register_segment_rows_preserves_missing_source_text_as_null() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        book_path = Path(tmpdir) / "book.duckdb"
        segment = ReaderSegment(
            segment_id="seg-1",
            work_id="work",
            edition_id="edition",
            segment_kind="line",
            citation_path="1",
            text="arma virumque",
            normalized_text="arma virumque",
            sort_key=1,
        )

        register_segment_rows(
            book_path,
            segments=[segment],
            addresses=[
                ReaderSegmentAddress(
                    segment_id=segment.segment_id,
                    address="work:1",
                    address_kind="langnet",
                    citation_path="1",
                )
            ],
        )

        with duckdb.connect(str(book_path), read_only=True) as conn:
            source_text = conn.execute("SELECT source_text FROM segments").fetchone()[0]

    assert source_text is None


def test_register_books_bulk_keeps_last_duplicate_catalog_row() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        create_catalog_db(catalog_path)
        entries = []
        for title, source_hash in [("First", "hash-1"), ("Second", "hash-2")]:
            work = ReaderWork(
                work_id="langnet:reader:test:duplicate",
                collection_id="test",
                language="lat",
                title=title,
                author="Author",
                author_id=None,
                source_id="duplicate",
                cts_work_urn=None,
            )
            edition = ReaderEdition(
                edition_id=f"{work.work_id}:edition",
                work_id=work.work_id,
                label="fixture",
                language="lat",
                source_path=root / f"{source_hash}.txt",
                cts_edition_urn=None,
            )
            artifact = ReaderBookArtifact(
                artifact_id="duplicate-artifact",
                work_id=work.work_id,
                edition_id=edition.edition_id,
                artifact_path=root / "duplicate.duckdb",
                source_path=edition.source_path,
                adapter="fixture",
                source_hash=source_hash,
                segment_count=1,
                token_count=2,
            )
            entries.append((work, edition, artifact))

        register_books(catalog_path, entries)

        with duckdb.connect(str(catalog_path), read_only=True) as conn:
            rows = conn.execute(
                """
                SELECT w.title, a.source_hash
                FROM works w
                JOIN artifacts a ON a.work_id = w.work_id
                """
            ).fetchall()

    assert rows == [("Second", "hash-2")]


def test_catalog_routes_langnet_address_without_scanning_unrelated_books() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        create_catalog_db(catalog_path)
        target_book = root / "books" / "target.duckdb"
        other_book = root / "books" / "other.duckdb"

        for work_id, book_path in [
            ("langnet:reader:sanskrit_dcs:dcs_431", target_book),
            ("langnet:reader:sanskrit_dcs:dcs_000", other_book),
        ]:
            create_book_db(book_path)
            work = ReaderWork(
                work_id=work_id,
                collection_id="sanskrit_dcs",
                language="san",
                title=work_id.rsplit(":", 1)[-1],
                author="Unknown",
                author_id=None,
                source_id=work_id.rsplit(":", 1)[-1],
                cts_work_urn=None,
            )
            edition = ReaderEdition(
                edition_id=f"{work_id}:edition",
                work_id=work.work_id,
                label="DCS edition",
                language="san",
                source_path=root / f"{work.source_id}.conllu",
                cts_edition_urn=None,
            )
            artifact = ReaderBookArtifact(
                artifact_id=f"{work.source_id}-artifact",
                work_id=work.work_id,
                edition_id=edition.edition_id,
                artifact_path=book_path,
                source_path=edition.source_path,
                adapter="fixture",
                source_hash="hash",
                segment_count=1,
                token_count=2,
            )
            register_book(catalog_path, work, edition, artifact)

        probe_paths: list[Path] = []

        def fake_has_address(book_path: Path, address: str) -> bool:
            probe_paths.append(book_path)
            return book_path == target_book

        with mock.patch("langnet.reader.storage._book_has_address", side_effect=fake_has_address):
            routed = lookup_artifact_for_address(
                catalog_path,
                "langnet:reader:sanskrit_dcs:dcs_431:561939",
            )

        assert routed is not None
        assert routed["artifact_path"] == str(target_book)
        assert probe_paths == [target_book]


def test_catalog_routes_cts_urn_overlay_to_internal_work_address() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        book_path = root / "books" / "bhagavadgita.duckdb"
        create_book_db(book_path)
        work = ReaderWork(
            work_id="langnet:reader:sanskrit_dcs:dcs_bhagavadgita",
            collection_id="sanskrit_dcs",
            language="san",
            title="Bhagavadgītā",
            author="Vyāsa",
            author_id=None,
            source_id="dcs_bhagavadgita",
            cts_work_urn="urn:cts:sanskritLit:mbh.bhg",
        )
        edition = ReaderEdition(
            edition_id=f"{work.work_id}:edition",
            work_id=work.work_id,
            label="DCS edition",
            language="san",
            source_path=root / "bhagavadgita.conllu",
            cts_edition_urn=None,
        )
        artifact = ReaderBookArtifact(
            artifact_id="bhagavadgita-artifact",
            work_id=work.work_id,
            edition_id=edition.edition_id,
            artifact_path=book_path,
            source_path=edition.source_path,
            adapter="fixture",
            source_hash="hash",
            segment_count=1,
            token_count=4,
        )
        register_book(catalog_path, work, edition, artifact)
        register_segment_rows(
            book_path,
            segments=[
                ReaderSegment(
                    segment_id=f"{work.work_id}:1.1",
                    work_id=work.work_id,
                    edition_id=edition.edition_id,
                    segment_kind="verse",
                    citation_path="1.1",
                    text="dhṛtarāṣṭra uvāca",
                    normalized_text="dhrtarastra uvaca",
                    sort_key=1,
                )
            ],
            addresses=[
                ReaderSegmentAddress(
                    segment_id=f"{work.work_id}:1.1",
                    address=f"{work.work_id}:1.1",
                    address_kind="langnet",
                    citation_path="1.1",
                )
            ],
        )

        contents = list_segments_for_work(catalog_path, "urn:cts:sanskritLit:mbh.bhg")
        segment = lookup_segment_by_address(catalog_path, "urn:cts:sanskritLit:mbh.bhg:1.1")

    assert [row["citation_path"] for row in contents] == ["1.1"]
    assert segment is not None
    assert segment["work_id"] == work.work_id
    assert segment["text"] == "dhṛtarāṣṭra uvāca"


def test_list_works_filters_display_author_and_authorship_claims() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        create_catalog_db(catalog_path)

        for work_id, title, author, source_id in [
            ("urn:cts:greekLit:tlg0059.tlg001", "Euthyphro", "Plato", "tlg0059.tlg001"),
            (
                "urn:cts:greekLit:tlg0059.tlg999",
                "Pseudo-Platonic Test",
                "Pseudo-Plato",
                "tlg0059.tlg999",
            ),
            (
                "urn:cts:greekLit:tlg0086.tlg001",
                "Categories",
                "Aristotle",
                "tlg0086.tlg001",
            ),
        ]:
            book_path = root / "books" / f"{source_id}.duckdb"
            create_book_db(book_path)
            work = ReaderWork(
                work_id=work_id,
                collection_id="perseus",
                language="grc",
                title=title,
                author=author,
                author_id=None,
                source_id=source_id,
                cts_work_urn=work_id,
            )
            edition = ReaderEdition(
                edition_id=f"{work_id}.edition",
                work_id=work.work_id,
                label="Fixture edition",
                language="grc",
                source_path=root / f"{source_id}.xml",
                cts_edition_urn=f"{work_id}.edition",
            )
            artifact = ReaderBookArtifact(
                artifact_id=f"{source_id}-artifact",
                work_id=work.work_id,
                edition_id=edition.edition_id,
                artifact_path=book_path,
                source_path=edition.source_path,
                adapter="fixture",
                source_hash="hash",
                segment_count=0,
                token_count=0,
            )
            register_book(catalog_path, work, edition, artifact)

        register_metadata_attributions(
            catalog_path,
            [
                ReaderMetadataAttribution(
                    collection_id="perseus",
                    match_field="work_id",
                    match_value="urn:cts:greekLit:tlg0086.tlg001",
                    relation_type="possible_author",
                    agent="Plato",
                    status="accepted",
                    confidence="low",
                    note="Fixture possible authorship claim.",
                    source_file="fixture",
                    evidence=(
                        ReaderMetadataOverlayEvidence(
                            source_type="web_source",
                            citation="https://example.org/plato-claim",
                            label="Fixture source records the possible attribution.",
                            retrieved_at="2026-05-14",
                        ),
                    ),
                )
            ],
        )

        display_matches = list_works(catalog_path, author="Plato")
        attribution_matches = list_works(catalog_path, attributed_to="Plato")
        filtered_attribution_matches = list_works(
            catalog_path,
            language="grc",
            attributed_to="Plato",
        )
        pseudo_matches = list_works(catalog_path, author="Pseudo-Plato")

    assert [row["title"] for row in display_matches] == ["Euthyphro"]
    assert {row["title"] for row in attribution_matches} == {"Categories", "Euthyphro"}
    assert {row["title"] for row in filtered_attribution_matches} == {
        "Categories",
        "Euthyphro",
    }
    assert [row["title"] for row in pseudo_matches] == ["Pseudo-Platonic Test"]


def test_list_metadata_overlays_tolerates_catalog_without_overlay_table() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        catalog_path = Path(tmpdir) / "old_catalog.duckdb"
        with duckdb.connect(str(catalog_path)) as conn:
            conn.execute(
                """
                CREATE TABLE works (
                    work_id VARCHAR PRIMARY KEY,
                    collection_id VARCHAR NOT NULL,
                    language VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    author VARCHAR NOT NULL,
                    author_id VARCHAR,
                    source_id VARCHAR NOT NULL,
                    cts_work_urn VARCHAR
                )
                """
            )

        assert list_metadata_overlays(catalog_path) == []


def test_list_works_attributed_to_tolerates_catalog_without_attribution_table() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        catalog_path = Path(tmpdir) / "old_catalog.duckdb"
        create_catalog_db(catalog_path)
        book_path = Path(tmpdir) / "book.duckdb"
        create_book_db(book_path)
        work = ReaderWork(
            work_id="urn:cts:greekLit:tlg0059.tlg001",
            collection_id="perseus",
            language="grc",
            title="Euthyphro",
            author="Plato",
            author_id=None,
            source_id="tlg0059.tlg001",
            cts_work_urn="urn:cts:greekLit:tlg0059.tlg001",
        )
        edition = ReaderEdition(
            edition_id=f"{work.work_id}.edition",
            work_id=work.work_id,
            label="Fixture edition",
            language="grc",
            source_path=Path(tmpdir) / "euthyphro.xml",
            cts_edition_urn=f"{work.work_id}.edition",
        )
        artifact = ReaderBookArtifact(
            artifact_id="euthyphro-artifact",
            work_id=work.work_id,
            edition_id=edition.edition_id,
            artifact_path=book_path,
            source_path=edition.source_path,
            adapter="fixture",
            source_hash="hash",
            segment_count=0,
            token_count=0,
        )
        register_book(catalog_path, work, edition, artifact)
        with duckdb.connect(str(catalog_path)) as conn:
            conn.execute("DROP TABLE metadata_attributions")

        matches = list_works(catalog_path, attributed_to="Plato")

    assert [row["title"] for row in matches] == ["Euthyphro"]


def test_registers_and_lists_metadata_attributions() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        catalog_path = Path(tmpdir) / "catalog.duckdb"
        create_catalog_db(catalog_path)
        register_metadata_attributions(
            catalog_path,
            [
                ReaderMetadataAttribution(
                    collection_id="sanskrit_dcs",
                    match_field="source_id",
                    match_value="dcs_example",
                    relation_type="possible_author",
                    agent="Aristotle",
                    status="accepted",
                    confidence="medium",
                    note="Accepted as a recorded attribution claim.",
                    source_file="data/curated/reader_attributions/sanskrit/example.yaml",
                    evidence=(
                        ReaderMetadataOverlayEvidence(
                            source_type="web_source",
                            citation="https://example.org/source",
                            label="Source records the possible attribution.",
                            retrieved_at="2026-05-13",
                        ),
                        ReaderMetadataOverlayEvidence(
                            source_type="web_source",
                            citation="https://example.org/source-2",
                            label="Second source records the same possible attribution.",
                            retrieved_at="2026-05-14",
                        ),
                    ),
                )
            ],
        )

        rows = list_metadata_attributions(
            catalog_path,
            collection_id="sanskrit_dcs",
            relation_type="possible_author",
            agent="Aristotle",
        )

    assert rows == [
        {
            "collection_id": "sanskrit_dcs",
            "match_field": "source_id",
            "match_value": "dcs_example",
            "relation_type": "possible_author",
            "agent": "Aristotle",
            "status": "accepted",
            "confidence": "medium",
            "note": "Accepted as a recorded attribution claim.",
            "source_file": "data/curated/reader_attributions/sanskrit/example.yaml",
            "evidence_source_type": "web_source",
            "evidence_citation": "https://example.org/source",
            "evidence_label": "Source records the possible attribution.",
            "evidence_retrieved_at": "2026-05-13",
        }
    ]


def test_list_metadata_attributions_tolerates_catalog_without_table() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        catalog_path = Path(tmpdir) / "old_catalog.duckdb"
        with duckdb.connect(str(catalog_path)) as conn:
            conn.execute(
                """
                CREATE TABLE works (
                    work_id VARCHAR PRIMARY KEY,
                    collection_id VARCHAR NOT NULL,
                    language VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    author VARCHAR NOT NULL,
                    author_id VARCHAR,
                    source_id VARCHAR NOT NULL,
                    cts_work_urn VARCHAR
                )
                """
            )

        assert list_metadata_attributions(catalog_path) == []


def test_catalog_routes_work_address_to_edition_containing_segment() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        work = ReaderWork(
            work_id="urn:cts:greekLit:tlg0012.tlg002",
            collection_id="perseus",
            language="grc",
            title="Odyssey",
            author="Homer",
            author_id="urn:cts:greekLit:tlg0012",
            source_id="tlg0012.tlg002",
            cts_work_urn="urn:cts:greekLit:tlg0012.tlg002",
        )
        for edition_suffix, citation_path, text in [
            ("perseus-eng3", "1.1", "Tell me, Muse"),
            ("perseus-grc2", "3.74", "ψυχὰς παρθέμενοι"),
        ]:
            book_path = root / "books" / f"{edition_suffix}.duckdb"
            edition = ReaderEdition(
                edition_id=f"{work.work_id}.{edition_suffix}",
                work_id=work.work_id,
                label=edition_suffix,
                language="eng" if "eng" in edition_suffix else "grc",
                source_path=root / f"{edition_suffix}.xml",
                cts_edition_urn=f"{work.work_id}.{edition_suffix}",
            )
            artifact = ReaderBookArtifact(
                artifact_id=edition_suffix,
                work_id=work.work_id,
                edition_id=edition.edition_id,
                artifact_path=book_path,
                source_path=edition.source_path,
                adapter="fixture",
                source_hash="hash",
                segment_count=1,
                token_count=2,
            )
            register_book(catalog_path, work, edition, artifact)
            register_segment_rows(
                book_path,
                segments=[
                    ReaderSegment(
                        segment_id=f"{work.work_id}:{citation_path}",
                        work_id=work.work_id,
                        edition_id=edition.edition_id,
                        segment_kind="line",
                        citation_path=citation_path,
                        text=text,
                        normalized_text=text.casefold(),
                        sort_key=1,
                    )
                ],
                addresses=[
                    ReaderSegmentAddress(
                        segment_id=f"{work.work_id}:{citation_path}",
                        address=f"{work.work_id}:{citation_path}",
                        address_kind="cts",
                        citation_path=citation_path,
                    )
                ],
            )

        segment = lookup_segment_by_address(catalog_path, f"{work.work_id}:3.74")

        assert segment is not None
        assert segment["edition_id"] == "urn:cts:greekLit:tlg0012.tlg002.perseus-grc2"
        assert segment["text"] == "ψυχὰς παρθέμενοι"


def test_shared_book_db_can_hold_multiple_work_artifacts() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        shared_book_path = root / "books" / "shared.duckdb"
        create_catalog_db(catalog_path)
        entries = []
        for index, work_id in enumerate(
            ["langnet:reader:tlg:tlg0012.001", "langnet:reader:tlg:tlg0012.002"],
            start=1,
        ):
            work = ReaderWork(
                work_id=work_id,
                collection_id="tlg",
                language="grc",
                title=f"Work {index}",
                author="Homer",
                author_id="urn:cts:greekLit:tlg0012",
                source_id=f"tlg0012.00{index}",
                cts_work_urn=f"urn:cts:greekLit:tlg0012.tlg00{index}",
            )
            edition = ReaderEdition(
                edition_id=f"{work.work_id}:edition",
                work_id=work.work_id,
                label="legacy text dump + IDT",
                language="grc",
                source_path=root / "tlg0012.txt",
                cts_edition_urn=None,
            )
            artifact = ReaderBookArtifact(
                artifact_id=f"artifact-{index}",
                work_id=work.work_id,
                edition_id=edition.edition_id,
                artifact_path=shared_book_path,
                source_path=edition.source_path,
                adapter="tlg_idt_legacy",
                source_hash="hash",
                segment_count=1,
                token_count=2,
            )
            register_segment_rows(
                shared_book_path,
                segments=[
                    ReaderSegment(
                        segment_id=f"{work.work_id}:1.1",
                        work_id=work.work_id,
                        edition_id=edition.edition_id,
                        segment_kind="line",
                        citation_path="1.1",
                        text=f"text {index}",
                        normalized_text=f"text {index}",
                        sort_key=index,
                    )
                ],
                addresses=[
                    ReaderSegmentAddress(
                        segment_id=f"{work.work_id}:1.1",
                        address=f"{work.work_id}:1.1",
                        address_kind="langnet",
                        citation_path="1.1",
                    )
                ],
                replace_work_id=work.work_id,
            )
            entries.append((work, edition, artifact))
        register_books(catalog_path, entries)

        first = lookup_segment_by_address(catalog_path, "langnet:reader:tlg:tlg0012.001:1.1")
        second = lookup_segment_by_address(catalog_path, "urn:cts:greekLit:tlg0012.tlg002:1.1")
        second_contents = list_segments_for_work(
            catalog_path,
            "urn:cts:greekLit:tlg0012.tlg002",
            limit=5,
        )
        with mock.patch("langnet.reader.storage._book_has_address") as book_has_address:
            missing = lookup_segment_by_work_and_citation(
                catalog_path,
                "urn:cts:greekLit:tlg0012.tlg002",
                "9.9",
            )

    assert first is not None
    assert first["text"] == "text 1"
    assert second is not None
    assert second["text"] == "text 2"
    assert [row["text"] for row in second_contents] == ["text 2"]
    assert missing is None
    book_has_address.assert_not_called()
