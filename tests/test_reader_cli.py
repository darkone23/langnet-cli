from __future__ import annotations

import json
import tempfile
from pathlib import Path

from click.testing import CliRunner

from langnet.cli import main
from langnet.reader.models import (
    ReaderAlias,
    ReaderBookArtifact,
    ReaderEdition,
    ReaderSegment,
    ReaderSegmentAddress,
    ReaderSourceMetadata,
    ReaderWork,
)
from langnet.reader.storage import (
    create_book_db,
    create_catalog_db,
    register_aliases,
    register_book,
    register_segment_rows,
    register_source_metadata,
)


def _write_fixture_reader_catalog(root: Path) -> Path:
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
        segment_count=2,
        token_count=8,
    )
    register_book(catalog_path, work, edition, artifact)
    register_segment_rows(
        book_path,
        segments=[
            ReaderSegment(
                segment_id="odyssey-1-8",
                work_id=work.work_id,
                edition_id=edition.edition_id,
                segment_kind="line",
                citation_path="1.8",
                text="νήπιοι, οἳ κατὰ βοῦς Ὑπερίονος Ἠελίοιο",
                normalized_text="νηπιοι οι κατα βους υπεριονος ηελιοιο",
                sort_key=8,
            ),
            ReaderSegment(
                segment_id="odyssey-3-74",
                work_id=work.work_id,
                edition_id=edition.edition_id,
                segment_kind="line",
                citation_path="3.74",
                text="ψυχὰς παρθέμενοι",
                normalized_text="ψυχας παρθεμενοι",
                sort_key=74,
            ),
        ],
        addresses=[
            ReaderSegmentAddress(
                segment_id="odyssey-1-8",
                address="urn:cts:greekLit:tlg0012.tlg002:1.8",
                address_kind="cts",
                citation_path="1.8",
            ),
            ReaderSegmentAddress(
                segment_id="odyssey-3-74",
                address="urn:cts:greekLit:tlg0012.tlg002:3.74",
                address_kind="cts",
                citation_path="3.74",
            ),
        ],
    )
    register_aliases(
        catalog_path,
        [
            ReaderAlias(
                alias="Odyssey",
                language="grc",
                kind="work_title",
                target=work.work_id,
                display="Homer, Odyssey",
                source_file="fixture",
                sources=("manual",),
            )
        ],
    )
    return catalog_path


def _register_fixture_work(  # noqa: PLR0913
    catalog_path: Path,
    root: Path,
    *,
    work_id: str,
    collection_id: str,
    language: str,
    title: str,
    author: str,
    author_id: str | None,
    source_id: str,
) -> None:
    safe_source = source_id.replace(":", "_").replace(".", "_")
    book_path = root / "books" / f"{safe_source}.duckdb"
    create_book_db(book_path)
    work = ReaderWork(
        work_id=work_id,
        collection_id=collection_id,
        language=language,
        title=title,
        author=author,
        author_id=author_id,
        source_id=source_id,
        cts_work_urn=work_id if work_id.startswith("urn:cts:") else None,
    )
    edition = ReaderEdition(
        edition_id=f"{work_id}:edition",
        work_id=work_id,
        label="Fixture edition",
        language=language,
        source_path=root / f"{safe_source}.xml",
        cts_edition_urn=None,
    )
    register_book(
        catalog_path,
        work,
        edition,
        ReaderBookArtifact(
            artifact_id=f"{work_id}:artifact",
            work_id=work_id,
            edition_id=edition.edition_id,
            artifact_path=book_path,
            source_path=edition.source_path,
            adapter="fixture",
            source_hash="hash",
            segment_count=0,
            token_count=0,
        ),
    )


def test_reader_cli_help_surface() -> None:
    commands = [
        ["reader"],
        ["reader", "works"],
        ["reader", "contents"],
        ["reader", "show"],
        ["reader", "resolve-address"],
        ["reader", "summary"],
        ["reader", "aliases"],
        ["reader", "alias-check"],
        ["reader", "validate"],
    ]
    for args in commands:
        result = CliRunner().invoke(main, [*args, "--help"])
        assert result.exit_code == 0, result.output


def test_reader_cli_lists_works_and_retrieves_segment_json() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        catalog_path = _write_fixture_reader_catalog(Path(tmpdir))
        runner = CliRunner()

        works = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "works",
                "--language",
                "grc",
                "--output",
                "json",
            ],
        )
        assert works.exit_code == 0, works.output
        works_payload = json.loads(works.output)
        assert works_payload["items"][0]["title"] == "Odyssey"

        pretty_works = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "works",
                "--language",
                "grc",
            ],
        )
        assert pretty_works.exit_code == 0, pretty_works.output
        assert "urn:cts:greekLit:tlg0012.tlg002" in pretty_works.output

        author_works = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "works",
                "--author",
                "Homer",
                "--output",
                "json",
            ],
        )
        assert author_works.exit_code == 0, author_works.output
        assert json.loads(author_works.output)["items"][0]["title"] == "Odyssey"

        contents = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "contents",
                "urn:cts:greekLit:tlg0012.tlg002",
                "--output",
                "json",
            ],
        )
        assert contents.exit_code == 0, contents.output
        contents_payload = json.loads(contents.output)
        assert {item["citation_path"] for item in contents_payload["items"]} >= {"1.8", "3.74"}

        segment = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "show",
                "urn:cts:greekLit:tlg0012.tlg002:3.74",
                "--output",
                "json",
            ],
        )
        assert segment.exit_code == 0, segment.output
        segment_payload = json.loads(segment.output)
        assert segment_payload["segment"]["text"] == "ψυχὰς παρθέμενοι"

        by_work = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "show",
                "urn:cts:greekLit:tlg0012.tlg002",
                "--segment",
                "3.74",
                "--output",
                "json",
            ],
        )
        assert by_work.exit_code == 0, by_work.output
        by_work_payload = json.loads(by_work.output)
        assert by_work_payload["segment"]["text"] == "ψυχὰς παρθέμενοι"

        friendly = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "show",
                "Odyssey book 1 line 8",
                "--output",
                "json",
            ],
        )
        assert friendly.exit_code == 0, friendly.output
        friendly_payload = json.loads(friendly.output)
        assert friendly_payload["resolved_address"] == "urn:cts:greekLit:tlg0012.tlg002:1.8"
        assert friendly_payload["segment"]["citation_path"] == "1.8"


def test_reader_cli_supports_web_reader_contracts() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        catalog_path = _write_fixture_reader_catalog(Path(tmpdir))
        runner = CliRunner()

        works = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "works",
                "--query",
                "odys",
                "--limit",
                "1",
                "--output",
                "json",
            ],
        )
        assert works.exit_code == 0, works.output
        works_payload = json.loads(works.output)
        assert works_payload["items"][0]["title"] == "Odyssey"
        assert works_payload["pagination"]["limit"] == 1
        assert works_payload["pagination"]["next_cursor"] is None

        work = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "work",
                "Odyssey",
                "--output",
                "json",
            ],
        )
        assert work.exit_code == 0, work.output
        assert json.loads(work.output)["item"]["title"] == "Odyssey"

        around = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "contents",
                "Odyssey",
                "--around",
                "3.74",
                "--radius",
                "1",
                "--output",
                "json",
            ],
        )
        assert around.exit_code == 0, around.output
        around_payload = json.loads(around.output)
        assert around_payload["window"]["anchor"] == "3.74"
        assert [item["citation_path"] for item in around_payload["items"]] == ["1.8", "3.74"]

        shown = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "show",
                "Odyssey",
                "--segment",
                "1.8",
                "--output",
                "json",
            ],
        )
        assert shown.exit_code == 0, shown.output
        navigation = json.loads(shown.output)["navigation"]
        assert navigation["previous"] is None
        assert navigation["next"]["citation_path"] == "3.74"


def test_reader_cli_supports_catalog_discovery_and_env_default() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        catalog_path = _write_fixture_reader_catalog(Path(tmpdir))
        runner = CliRunner()

        summary = runner.invoke(
            main,
            ["reader", "summary", "--output", "json"],
            env={"LANGNET_READER_CATALOG": str(catalog_path)},
        )
        assert summary.exit_code == 0, summary.output
        assert json.loads(summary.output)["summary"]["work_count"] == 1

        catalogs = runner.invoke(
            main,
            ["reader", "catalogs", "--output", "json"],
            env={"LANGNET_READER_CATALOG": str(catalog_path)},
        )
        assert catalogs.exit_code == 0, catalogs.output
        env_item = next(
            item for item in json.loads(catalogs.output)["items"] if item["id"] == "env"
        )
        assert env_item["path"] == str(catalog_path)
        assert env_item["work_count"] == 1
        assert env_item["languages"] == ["grc"]


def test_reader_cli_supports_author_query_pagination() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        catalog_path = _write_fixture_reader_catalog(Path(tmpdir))
        result = CliRunner().invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "authors",
                "--query",
                "hom",
                "--limit",
                "1",
                "--output",
                "json",
            ],
        )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["items"][0]["author"] == "Homer"
    assert payload["pagination"]["limit"] == 1
    assert payload["pagination"]["next_cursor"] is None


def test_reader_cli_supports_native_author_index_and_author_id_works() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        create_catalog_db(catalog_path)
        _register_fixture_work(
            catalog_path,
            root,
            work_id="urn:cts:latinLit:phi0690.phi001",
            collection_id="phi",
            language="lat",
            title="Aeneis",
            author="P. Vergilius Maro (Virgil)",
            author_id="urn:cts:latinLit:phi0690",
            source_id="phi0690.phi001",
        )
        _register_fixture_work(
            catalog_path,
            root,
            work_id="urn:cts:latinLit:phi0690.phi002",
            collection_id="phi",
            language="lat",
            title="Georgica",
            author="P. Vergilius Maro (Virgil)",
            author_id="urn:cts:latinLit:phi0690",
            source_id="phi0690.phi002",
        )
        _register_fixture_work(
            catalog_path,
            root,
            work_id="urn:cts:greekLit:tlg0011.tlg001",
            collection_id="tlg",
            language="grc",
            title="Ajax",
            author="Σοφοκλῆς",
            author_id="tlg0011",
            source_id="tlg0011.tlg001",
        )
        _register_fixture_work(
            catalog_path,
            root,
            work_id="urn:cts:greekLit:tlg0086.tlg001",
            collection_id="tlg",
            language="grc",
            title="Categoriae",
            author="Ἀριστοτέλης",
            author_id="tlg0086",
            source_id="tlg0086.tlg001",
        )
        _register_fixture_work(
            catalog_path,
            root,
            work_id="langnet:reader:sanskrit:kali-megha",
            collection_id="sanskrit_texts",
            language="san",
            title="Meghadūta",
            author="Kālidāsa",
            author_id=None,
            source_id="kali-megha",
        )
        _register_fixture_work(
            catalog_path,
            root,
            work_id="langnet:reader:sanskrit:panini-shiva",
            collection_id="sanskrit_texts",
            language="san",
            title="Śivasūtra",
            author="Pāṇini",
            author_id=None,
            source_id="panini-shiva",
        )
        runner = CliRunner()

        latin_sections = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "author-sections",
                "--language",
                "lat",
                "--output",
                "json",
            ],
        )
        latin_authors = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "authors",
                "--language",
                "lat",
                "--section",
                "V",
                "--limit",
                "50",
                "--output",
                "json",
            ],
        )
        greek_sections = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "author-sections",
                "--language",
                "grc",
                "--output",
                "json",
            ],
        )
        sanskrit_sections = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "author-sections",
                "--language",
                "san",
                "--output",
                "json",
            ],
        )
        vergil_works = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "works",
                "--language",
                "lat",
                "--author-id",
                "phi0690",
                "--output",
                "json",
            ],
        )

    assert latin_sections.exit_code == 0, latin_sections.output
    assert json.loads(latin_sections.output)["items"][0]["key"] == "V"
    assert latin_authors.exit_code == 0, latin_authors.output
    latin_item = json.loads(latin_authors.output)["items"][0]
    assert latin_item["display_name"] == "P. Vergilius Maro (Virgil)"
    assert latin_item["index_name"] == "Vergilius Maro"
    assert latin_item["section_key"] == "V"
    assert latin_item["author_id"] == "phi0690"
    assert latin_item["alternate_names"] == ["Virgil", "Vergil"]
    assert greek_sections.exit_code == 0, greek_sections.output
    assert [item["key"] for item in json.loads(greek_sections.output)["items"]] == ["Α", "Σ"]
    assert sanskrit_sections.exit_code == 0, sanskrit_sections.output
    assert [item["key"] for item in json.loads(sanskrit_sections.output)["items"]] == ["क", "प"]
    assert vergil_works.exit_code == 0, vergil_works.output
    assert [item["title"] for item in json.loads(vergil_works.output)["items"]] == [
        "Aeneis",
        "Georgica",
    ]


def test_reader_cli_disambiguates_duplicate_author_display_names() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        create_catalog_db(catalog_path)
        _register_fixture_work(
            catalog_path,
            root,
            work_id="langnet:reader:tlg:tlg0324.001",
            collection_id="tlg",
            language="grc",
            title="Fragmenta",
            author="Patrocles",
            author_id="tlg0324",
            source_id="tlg0324.001",
        )
        register_source_metadata(
            catalog_path,
            [
                ReaderSourceMetadata(
                    collection_id="tlg",
                    subject_kind="author",
                    subject_id="tlg0324",
                    key="tlg_canon_category",
                    value="Trag.",
                    source_path=root / "doccan1.txt",
                ),
                ReaderSourceMetadata(
                    collection_id="tlg",
                    subject_kind="author",
                    subject_id="tlg2479",
                    key="tlg_canon_category",
                    value="Hist.",
                    source_path=root / "doccan1.txt",
                ),
            ],
        )
        _register_fixture_work(
            catalog_path,
            root,
            work_id="langnet:reader:tlg:tlg2479.003",
            collection_id="tlg",
            language="grc",
            title="Fragmenta",
            author="Patrocles",
            author_id="tlg2479",
            source_id="tlg2479.003",
        )
        runner = CliRunner()

        result = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "authors",
                "--language",
                "grc",
                "--query",
                "patrocles",
                "--output",
                "json",
            ],
        )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert [item["display_name"] for item in payload["items"]] == [
        "Patrocles (Hist.)",
        "Patrocles (Trag.)",
    ]


def test_reader_cli_uses_canon_author_descriptor_before_id_suffix() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        create_catalog_db(catalog_path)
        _register_fixture_work(
            catalog_path,
            root,
            work_id="langnet:reader:tlg:tlg3141.002",
            collection_id="tlg",
            language="grc",
            title="Annales",
            author="Georgius",
            author_id="tlg3141",
            source_id="tlg3141.002",
        )
        _register_fixture_work(
            catalog_path,
            root,
            work_id="langnet:reader:tlg:tlg3143.001",
            collection_id="tlg",
            language="grc",
            title="Chronicon",
            author="Georgius",
            author_id="tlg3143",
            source_id="tlg3143.001",
        )
        register_source_metadata(
            catalog_path,
            [
                ReaderSourceMetadata(
                    collection_id="tlg",
                    subject_kind="author",
                    subject_id="tlg3141",
                    key="tlg_canon_author_name",
                    value="Georgius Acropolites",
                    source_path=root / "doccan1.txt",
                ),
                ReaderSourceMetadata(
                    collection_id="tlg",
                    subject_kind="author",
                    subject_id="tlg3141",
                    key="tlg_canon_category",
                    value="Hist.",
                    source_path=root / "doccan1.txt",
                ),
                ReaderSourceMetadata(
                    collection_id="tlg",
                    subject_kind="author",
                    subject_id="tlg3143",
                    key="tlg_canon_author_name",
                    value="Georgius Sphrantzes",
                    source_path=root / "doccan1.txt",
                ),
                ReaderSourceMetadata(
                    collection_id="tlg",
                    subject_kind="author",
                    subject_id="tlg3143",
                    key="tlg_canon_category",
                    value="Hist.",
                    source_path=root / "doccan1.txt",
                ),
            ],
        )
        runner = CliRunner()

        result = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "authors",
                "--language",
                "grc",
                "--query",
                "georgius",
                "--output",
                "json",
            ],
        )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert [item["display_name"] for item in payload["items"]] == [
        "Georgius (Acropolites)",
        "Georgius (Sphrantzes)",
    ]


def test_reader_cli_does_not_treat_second_word_as_descriptor() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        create_catalog_db(catalog_path)
        _register_fixture_work(
            catalog_path,
            root,
            work_id="langnet:reader:tlg:tlg0532.001",
            collection_id="tlg",
            language="grc",
            title="Leucippe et Clitophon",
            author="Achilles Tatius",
            author_id="tlg0532",
            source_id="tlg0532.001",
        )
        _register_fixture_work(
            catalog_path,
            root,
            work_id="langnet:reader:tlg:tlg2133.001",
            collection_id="tlg",
            language="grc",
            title="Isagoga excerpta",
            author="Achilles Tatius",
            author_id="tlg2133",
            source_id="tlg2133.001",
        )
        register_source_metadata(
            catalog_path,
            [
                ReaderSourceMetadata(
                    collection_id="tlg",
                    subject_kind="author",
                    subject_id="tlg0532",
                    key="tlg_canon_author_name",
                    value="Achilles Tatius",
                    source_path=root / "doccan1.txt",
                ),
                ReaderSourceMetadata(
                    collection_id="tlg",
                    subject_kind="author",
                    subject_id="tlg0532",
                    key="tlg_canon_category",
                    value="Scr. Erot.",
                    source_path=root / "doccan1.txt",
                ),
                ReaderSourceMetadata(
                    collection_id="tlg",
                    subject_kind="author",
                    subject_id="tlg2133",
                    key="tlg_canon_author_name",
                    value="Achilles Tatius",
                    source_path=root / "doccan1.txt",
                ),
                ReaderSourceMetadata(
                    collection_id="tlg",
                    subject_kind="author",
                    subject_id="tlg2133",
                    key="tlg_canon_category",
                    value="Astron.",
                    source_path=root / "doccan1.txt",
                ),
            ],
        )
        runner = CliRunner()

        result = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "authors",
                "--language",
                "grc",
                "--query",
                "achilles",
                "--output",
                "json",
            ],
        )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert [item["display_name"] for item in payload["items"]] == [
        "Achilles Tatius (Astron.)",
        "Achilles Tatius (Scr. Erot.)",
    ]


def test_reader_cli_accepts_cts_work_urn_when_work_id_is_internal() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        book_path = root / "books" / "bhagavadgita.duckdb"
        create_catalog_db(catalog_path)
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
        register_book(
            catalog_path,
            work,
            edition,
            ReaderBookArtifact(
                artifact_id="bhagavadgita-artifact",
                work_id=work.work_id,
                edition_id=edition.edition_id,
                artifact_path=book_path,
                source_path=edition.source_path,
                adapter="fixture",
                source_hash="hash",
                segment_count=1,
                token_count=4,
            ),
        )
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
        runner = CliRunner()

        contents = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "contents",
                "urn:cts:sanskritLit:mbh.bhg",
                "--output",
                "json",
            ],
        )
        shown = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "show",
                "urn:cts:sanskritLit:mbh.bhg",
                "--segment",
                "1.1",
                "--output",
                "json",
            ],
        )

    assert contents.exit_code == 0, contents.output
    contents_segment = json.loads(contents.output)["items"][0]
    assert contents_segment["citation_path"] == "1.1"
    assert contents_segment["language"] == "san"
    assert contents_segment["display"]["transliteration"] == "dhṛtarāṣṭra uvāca"
    assert contents_segment["display"]["script"] == "Devanagari"
    assert "devanagari" in contents_segment["available_layers"]
    assert shown.exit_code == 0, shown.output
    shown_segment = json.loads(shown.output)["segment"]
    assert shown_segment["text"] == "dhṛtarāṣṭra uvāca"
    assert shown_segment["native_script"] == "धृतराष्ट्र उवाच"


def test_databuild_reader_command_creates_empty_catalog() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        output_root = Path(tmpdir) / "reader"
        result = CliRunner().invoke(
            main,
            [
                "databuild",
                "reader",
                "--output-root",
                str(output_root),
                "--wipe",
            ],
        )

        assert result.exit_code == 0, result.output
        assert (output_root / "catalog.duckdb").exists()
        assert "status: success" in result.output
