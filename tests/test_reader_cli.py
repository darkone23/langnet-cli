from __future__ import annotations

import csv
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import duckdb
from click.testing import CliRunner

from langnet.cli import _call_work_classifier_with_retries, main
from langnet.reader.models import (
    ReaderAlias,
    ReaderBookArtifact,
    ReaderDivisionMetadata,
    ReaderEdition,
    ReaderMetadataAttribution,
    ReaderMetadataOverlayEvidence,
    ReaderSegment,
    ReaderSegmentAddress,
    ReaderSourceMetadata,
    ReaderWork,
    ReaderWorkMapNode,
)
from langnet.reader.storage import (
    create_book_db,
    create_catalog_db,
    list_source_metadata,
    register_aliases,
    register_book,
    register_division_metadata,
    register_metadata_attributions,
    register_segment_rows,
    register_source_metadata,
    register_work_map_nodes,
)

ODYSSEY_BOOK_ONE_WORD_COUNT = 6
GENERATED_CLASSIFICATION_COUNT = 2
RETRY_TEST_ATTEMPTS = 2
CANONICAL_POPULARITY_SCORE = 100
PERSEUS_GRAMMAR_METADATA_COUNT = 7
AUTHOR_CLASSIFICATION_FIXTURE_COUNT = 2
CLASSIFICATION_ESCALATION_FIXTURE_COUNT = 2
DEFAULT_RESEARCH_NEED_TYPE_LIMIT = 5
ODYSSEY_FIXTURE_SEGMENT_COUNT = 2
LEGACY_LANGUAGE_REPAIR_EXPECTED_COUNT = 5
VULGATE_METADATA_OVERLAY_EXPECTED_COUNT = 2
GOSPEL_METADATA_OVERLAY_EXPECTED_COUNT = 2


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
    register_work_map_nodes(
        catalog_path,
        [
            ReaderWorkMapNode(
                work_id=work.work_id,
                node_id="odyssey-01",
                level=1,
                kind="book",
                label="Book 1",
                ordinal=1,
                start_citation="1.8",
                end_citation="1.8",
                provenance="curated",
                confidence="high",
                status="accepted",
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
        ["reader", "map"],
        ["reader", "structure"],
        ["reader", "about"],
        ["reader", "citation-maps"],
        ["reader", "sync-citation-maps"],
        ["reader", "sync-work-maps"],
        ["reader", "sync-division-metadata"],
        ["reader", "sync-classifications"],
        ["reader", "sync-author-classifications"],
        ["reader", "sync-metadata-attributions"],
        ["reader", "repair-languages"],
        ["reader", "prune-stale-classifications"],
        ["reader", "popular"],
        ["reader", "facets"],
        ["reader", "author-facets"],
        ["reader", "author-classification-export"],
        ["reader", "classification-escalation-export"],
        ["reader", "research-needs-export"],
        ["reader", "classify-authors"],
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


def test_reader_cli_structure_returns_ui_ready_nodes() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        create_catalog_db(catalog_path)
        _register_fixture_work(
            catalog_path,
            root,
            work_id="urn:cts:sanskritLit:mbh.bhg",
            collection_id="sanskrit_dcs",
            language="san",
            title="Bhagavadgītā",
            author="Vyāsa",
            author_id=None,
            source_id="mbh.bhg",
        )
        register_work_map_nodes(
            catalog_path,
            [
                ReaderWorkMapNode(
                    work_id="urn:cts:sanskritLit:mbh.bhg",
                    node_id="bhg-09",
                    parent_node_id=None,
                    level=1,
                    kind="chapter",
                    label="Rāja Vidyā Rāja Guhya Yoga",
                    native_label="राजविद्याराजगुह्ययोग",
                    ordinal=9,
                    start_citation="231273",
                    end_citation="231341",
                    provenance="curated",
                    confidence="high",
                    status="accepted",
                    note="fixture",
                    source_file="fixture",
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
        register_division_metadata(
            catalog_path,
            [
                ReaderDivisionMetadata(
                    work_id="urn:cts:sanskritLit:mbh.bhg",
                    node_id="bhg-09",
                    summary="A reviewed chapter note.",
                    short_label="Royal knowledge",
                    traditional_reference="BhG 9",
                    status="accepted",
                    confidence="high",
                    generator_model="",
                    review_status="reviewed",
                    note="fixture",
                    source_file="fixture",
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

        result = CliRunner().invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "structure",
                "urn:cts:sanskritLit:mbh.bhg",
                "--output",
                "json",
            ],
        )
        about = CliRunner().invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "about",
                "urn:cts:sanskritLit:mbh.bhg",
                "--output",
                "json",
            ],
        )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["mode"] == "structure"
    assert payload["summary"]["node_count"] == 1
    assert payload["items"][0]["traditional_reference"] == "BhG 9"
    assert about.exit_code == 0, about.output
    about_payload = json.loads(about.output)
    assert about_payload["mode"] == "work-dossier"
    assert about_payload["summary"]["structure_label"] == "1 chapter"
    assert about_payload["division_bios"][0]["traditional_reference"] == "BhG 9"


def test_reader_cli_lists_works_and_retrieves_segment_json() -> None:  # noqa: PLR0915
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
        assert works_payload["items"][0]["source_label"] == "PERSEUS tlg0012.tlg002"
        assert works_payload["items"][0]["short_disambiguation_label"] == "tlg0012.tlg002"

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

        author_detail = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "author",
                "urn:cts:greekLit:tlg0012",
                "--language",
                "grc",
                "--output",
                "json",
            ],
        )
        assert author_detail.exit_code == 0, author_detail.output
        author_payload = json.loads(author_detail.output)
        assert author_payload["mode"] == "author"
        assert author_payload["item"]["display_name"] == "Homer"
        assert author_payload["item"]["source_author_id"] == "urn:cts:greekLit:tlg0012"
        assert author_payload["representative_works"][0]["title"] == "Odyssey"
        assert author_payload["query"] == {
            "language": "grc",
            "author_id": "urn:cts:greekLit:tlg0012",
        }

        work_detail = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "work",
                "urn:cts:greekLit:tlg0012.tlg002",
                "--output",
                "json",
            ],
        )
        assert work_detail.exit_code == 0, work_detail.output
        work_payload = json.loads(work_detail.output)
        assert work_payload["item"]["source_label"] == "PERSEUS tlg0012.tlg002"
        assert work_payload["item"]["edition_label"] == "PERSEUS reader text"
        assert work_payload["item"]["canonical_author_name"] == "Homer"

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

        work_map = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "map",
                "urn:cts:greekLit:tlg0012.tlg002",
                "--output",
                "json",
            ],
        )
        assert work_map.exit_code == 0, work_map.output
        work_map_payload = json.loads(work_map.output)
        assert work_map_payload["mode"] == "map"
        assert work_map_payload["items"][0]["kind"] == "book"
        assert work_map_payload["items"][0]["label"] == "Book 1"
        assert work_map_payload["items"][0]["word_count"] == ODYSSEY_BOOK_ONE_WORD_COUNT
        assert work_map_payload["items"][0]["word_count_method"] == "whitespace_tokens"

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


def test_reader_cli_builds_and_searches_reader_text_index() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = _write_fixture_reader_catalog(root)
        index_path = root / "reader-search.lance"
        runner = CliRunner()

        build = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "search-index",
                "build",
                "--index",
                str(index_path),
                "--replace",
                "--output",
                "json",
            ],
        )
        assert build.exit_code == 0, build.output
        build_payload = json.loads(build.output)
        assert build_payload["mode"] == "search-index-build"
        assert build_payload["summary"]["backend"] == "duckdb-lance"
        assert build_payload["summary"]["fts_indexed"] is True
        assert build_payload["summary"]["segment_count"] == ODYSSEY_FIXTURE_SEGMENT_COUNT

        status = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "search-index",
                "status",
                "--index",
                str(index_path),
                "--output",
                "json",
            ],
        )
        assert status.exit_code == 0, status.output
        status_payload = json.loads(status.output)
        assert status_payload["summary"]["backend"] == "duckdb-lance"
        assert status_payload["summary"]["segment_count"] == ODYSSEY_FIXTURE_SEGMENT_COUNT
        assert "search_text_folded_idx" in status_payload["summary"]["fts_indexes"]

        normalize = runner.invoke(
            main,
            [
                "reader",
                "search-index",
                "inspect-normalize",
                "--language",
                "grc",
                "λόγος",
                "--output",
                "json",
            ],
        )
        assert normalize.exit_code == 0, normalize.output
        normalize_payload = json.loads(normalize.output)
        assert normalize_payload["summary"]["query"]["search_text_folded"] == "λογοσ"

        inspect_query = runner.invoke(
            main,
            [
                "reader",
                "search-index",
                "inspect-query",
                "--language",
                "grc",
                "--mode",
                "fuzzy",
                "bous",
                "--output",
                "json",
            ],
        )
        assert inspect_query.exit_code == 0, inspect_query.output
        inspect_payload = json.loads(inspect_query.output)
        assert inspect_payload["summary"]["candidates"][1]["query"] == "βουσ"
        assert inspect_payload["summary"]["candidates"][1]["kind"] == "transliteration_expansion"

        search = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "search",
                "βους",
                "--index",
                str(index_path),
                "--language",
                "grc",
                "--output",
                "json",
            ],
        )
        assert search.exit_code == 0, search.output
        search_payload = json.loads(search.output)
        assert search_payload["items"][0]["citation_path"] == "1.8"

        fuzzy = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "search",
                "bous",
                "--index",
                str(index_path),
                "--language",
                "grc",
                "--mode",
                "fuzzy",
                "--output",
                "json",
            ],
        )
        assert fuzzy.exit_code == 0, fuzzy.output
        fuzzy_payload = json.loads(fuzzy.output)
        assert fuzzy_payload["items"][0]["citation_path"] == "1.8"
        assert fuzzy_payload["items"][0]["matched_query"] == "βουσ"
        assert fuzzy_payload["items"][0]["match_type"] == "transliteration_expansion"


def test_reader_sync_work_maps_applies_curated_yaml_to_existing_catalog() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        work_map_dir = root / "work_maps"
        work_map_dir.mkdir()
        create_catalog_db(catalog_path)
        (work_map_dir / "fixture.yaml").write_text(
            """
work_maps:
  - work_id: "urn:cts:greekLit:tlg0012.tlg002"
    node_id: "odyssey-01"
    level: 1
    kind: "book"
    label: "Book 1"
    ordinal: 1
    start_citation: "1.1"
    end_citation: "1.100"
    provenance: "curated"
    confidence: "high"
    status: "accepted"
    note: "fixture"
    evidence:
      - source_type: "fixture"
        citation: "fixture"
        label: "fixture"
""".lstrip(),
            encoding="utf-8",
        )
        runner = CliRunner()

        sync = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "sync-work-maps",
                "--work-map-dir",
                str(work_map_dir),
                "--output",
                "json",
            ],
        )
        work_map = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "map",
                "urn:cts:greekLit:tlg0012.tlg002",
                "--output",
                "json",
            ],
        )

    assert sync.exit_code == 0, sync.output
    assert json.loads(sync.output)["summary"]["synced_count"] == 1
    assert work_map.exit_code == 0, work_map.output
    assert json.loads(work_map.output)["items"][0]["label"] == "Book 1"


def test_reader_cli_sync_division_metadata() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        metadata_root = root / "division_metadata"
        metadata_root.mkdir()
        create_catalog_db(catalog_path)
        (metadata_root / "fixture.yaml").write_text(
            """
division_metadata:
  - work_id: "urn:cts:sanskritLit:mbh.bhg"
    node_id: "bhg-09"
    summary: "A reviewed chapter note."
    short_label: "Royal knowledge"
    traditional_reference: "BhG 9"
    status: "accepted"
    confidence: "high"
    generator_model: ""
    review_status: "reviewed"
    note: "fixture"
    evidence:
      - source_type: "fixture"
        citation: "fixture"
        label: "fixture"
""".lstrip(),
            encoding="utf-8",
        )

        result = CliRunner().invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "sync-division-metadata",
                "--division-metadata-dir",
                str(metadata_root),
                "--output",
                "json",
            ],
        )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["mode"] == "sync-division-metadata"
    assert payload["summary"]["synced_count"] == 1


def test_reader_citation_maps_pretty_output_is_visible() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        citation_map_dir = root / "citation_maps"
        citation_map_dir.mkdir()
        create_catalog_db(catalog_path)
        (citation_map_dir / "fixture.yaml").write_text(
            """
citation_maps:
  - citation_map_id: "lewis-short-de-inventione-book-chapter-section"
    source_id: "lewis_short"
    work_id: "urn:cts:latinLit:phi0474.phi036"
    source_pattern: "book.chapter.section"
    machine_pattern: "book.section"
    projection_rule: "drop_middle_numeric_part"
    example_source_reference: "Cic. Inv. 2, 50, 148"
    example_machine_citation: "2.148"
    status: "accepted"
    confidence: "high"
    note: "fixture"
    evidence:
      - source_type: "fixture"
        citation: "fixture"
        label: "fixture"
""".lstrip(),
            encoding="utf-8",
        )
        runner = CliRunner()

        sync = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "sync-citation-maps",
                "--citation-map-dir",
                str(citation_map_dir),
            ],
        )
        citation_maps = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "citation-maps",
                "urn:cts:latinLit:phi0474.phi036",
            ],
        )

    assert sync.exit_code == 0, sync.output
    assert "synced_count: 1" in sync.output
    assert citation_maps.exit_code == 0, citation_maps.output
    assert "lewis_short" in citation_maps.output
    assert "drop_middle_numeric_part" in citation_maps.output


def test_reader_cli_syncs_generated_classifications_and_lists_popular_works() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = _write_fixture_reader_catalog(root)
        _register_fixture_work(
            catalog_path,
            root,
            work_id="urn:cts:greekLit:tlg0012.tlg001",
            collection_id="perseus",
            language="grc",
            title="Iliad",
            author="Homer",
            author_id="urn:cts:greekLit:tlg0012",
            source_id="tlg0012.tlg001",
        )
        classification_csv = root / "generated-classifications.csv"
        classification_csv.write_text(
            "\n".join(
                [
                    "work_id,classification_category,classification_period,"
                    "classification_date_range,classification_authorship_status,"
                    "classification_popularity_score,classification_popularity_tier,"
                    "classification_scope,classification_scope_popularity_score,"
                    "classification_scope_popularity_tier,"
                    "classification_confidence,classification_notes,"
                    "classification_generator_models,classification_generator_run_id",
                    "urn:cts:greekLit:tlg0012.tlg002,epic,archaic,"
                    '"c. 8th-7th century BCE",traditional,95,canonical,'
                    "Epic Poetry,95,canonical,"
                    "high,Generated by model ensemble,"
                    "deepseek/deepseek-v3.2;openai/gpt-oss-120b,run-1",
                    "urn:cts:greekLit:tlg0012.tlg001,epic,archaic,"
                    '"c. 8th century BCE",traditional,100,canonical,'
                    "Epic Poetry,100,canonical,"
                    "high,Generated by model ensemble,"
                    "deepseek/deepseek-v3.2;openai/gpt-oss-120b,run-1",
                ]
            ),
            encoding="utf-8",
        )
        runner = CliRunner()

        sync = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "sync-classifications",
                "--classification-csv",
                str(classification_csv),
                "--output",
                "json",
            ],
        )
        assert sync.exit_code == 0, sync.output
        assert json.loads(sync.output)["summary"]["synced_count"] == GENERATED_CLASSIFICATION_COUNT

        popular = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "popular",
                "--language",
                "grc",
                "--output",
                "json",
            ],
        )
        assert popular.exit_code == 0, popular.output
        popular_payload = json.loads(popular.output)
        assert [item["title"] for item in popular_payload["items"][:2]] == [
            "Iliad",
            "Odyssey",
        ]
        assert (
            popular_payload["items"][0]["classification_popularity_score"]
            == CANONICAL_POPULARITY_SCORE
        )
        assert popular_payload["items"][0]["classification_generator_models"] == (
            "deepseek/deepseek-v3.2;openai/gpt-oss-120b"
        )
        popular_pretty = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "popular",
                "--language",
                "grc",
            ],
        )
        assert popular_pretty.exit_code == 0, popular_pretty.output
        assert "grc  Homer — Iliad" in popular_pretty.output

        sorted_works = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "works",
                "--language",
                "grc",
                "--sort",
                "popularity",
                "--output",
                "json",
            ],
        )
        assert sorted_works.exit_code == 0, sorted_works.output
        sorted_payload = json.loads(sorted_works.output)
        assert [item["title"] for item in sorted_payload["items"][:2]] == [
            "Iliad",
            "Odyssey",
        ]

        scoped_popular = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "popular",
                "--language",
                "grc",
                "--scope",
                "epic",
                "--output",
                "json",
            ],
        )
        scoped_payload = json.loads(scoped_popular.output)

    assert scoped_popular.exit_code == 0, scoped_popular.output
    assert scoped_payload["request"]["classification_scope"] == "epic"
    assert [item["title"] for item in scoped_payload["items"][:2]] == [
        "Iliad",
        "Odyssey",
    ]


def test_reader_cli_repairs_primary_work_languages_from_legacy_metadata() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        book_path = root / "books" / "john.duckdb"
        create_catalog_db(catalog_path)
        create_book_db(book_path)
        english_work = ReaderWork(
            work_id="langnet:reader:phi:civ0005.058",
            collection_id="phi",
            language="lat",
            title="John",
            author="English Bible (KJV or AV)",
            author_id="civ0005",
            source_id="civ0005.058",
            cts_work_urn=None,
        )
        english_edition = ReaderEdition(
            edition_id="langnet:reader:phi:civ0005.058:legacy",
            work_id=english_work.work_id,
            label="legacy text dump",
            language="lat",
            source_path=root / "civ0005.txt",
            cts_edition_urn=None,
        )
        latin_work = ReaderWork(
            work_id="langnet:reader:phi:civ0007.002",
            collection_id="phi",
            language="lat",
            title="Defensionem Regiam (Latin Works, vol. 7, pp. 1-300)",
            author="John Milton (English and Latin)",
            author_id="civ0007",
            source_id="civ0007.002",
            cts_work_urn=None,
        )
        septuagint_work = ReaderWork(
            work_id="langnet:reader:phi:civ0002.001",
            collection_id="phi",
            language="lat",
            title="Genesis",
            author="Septuagint (Old Greek Bible)",
            author_id="civ0002",
            source_id="civ0002.001",
            cts_work_urn=None,
        )
        septuagint_edition = ReaderEdition(
            edition_id="langnet:reader:phi:civ0002.001:legacy",
            work_id=septuagint_work.work_id,
            label="legacy text dump",
            language="lat",
            source_path=root / "civ0002.txt",
            cts_edition_urn=None,
        )
        hebrew_work = ReaderWork(
            work_id="langnet:reader:phi:civ0001.001",
            collection_id="phi",
            language="lat",
            title="Genesis",
            author="Hebrew Bible (MT or BHS)",
            author_id="civ0001",
            source_id="civ0001.001",
            cts_work_urn=None,
        )
        hebrew_edition = ReaderEdition(
            edition_id="langnet:reader:phi:civ0001.001:legacy",
            work_id=hebrew_work.work_id,
            label="legacy text dump",
            language="lat",
            source_path=root / "civ0001.txt",
            cts_edition_urn=None,
        )
        greek_nt_work = ReaderWork(
            work_id="langnet:reader:phi:civ0003.001",
            collection_id="phi",
            language="lat",
            title="Matthew",
            author="Greek New Testament (NT UBS3 edition)",
            author_id="civ0003",
            source_id="civ0003.001",
            cts_work_urn=None,
        )
        greek_nt_edition = ReaderEdition(
            edition_id="langnet:reader:phi:civ0003.001:legacy",
            work_id=greek_nt_work.work_id,
            label="legacy text dump",
            language="lat",
            source_path=root / "civ0003.txt",
            cts_edition_urn=None,
        )
        coptic_work = ReaderWork(
            work_id="langnet:reader:phi:cop0001.020",
            collection_id="phi",
            language="lat",
            title="James",
            author="Sahidic Coptic Bible",
            author_id="cop0001",
            source_id="cop0001.020",
            cts_work_urn=None,
        )
        coptic_edition = ReaderEdition(
            edition_id="langnet:reader:phi:cop0001.020:legacy",
            work_id=coptic_work.work_id,
            label="legacy text dump",
            language="lat",
            source_path=root / "cop0001.txt",
            cts_edition_urn=None,
        )
        latin_edition = ReaderEdition(
            edition_id="langnet:reader:phi:civ0007.002:legacy",
            work_id=latin_work.work_id,
            label="legacy text dump",
            language="lat",
            source_path=root / "civ0007.txt",
            cts_edition_urn=None,
        )
        register_book(
            catalog_path,
            english_work,
            english_edition,
            ReaderBookArtifact(
                artifact_id="john",
                work_id=english_work.work_id,
                edition_id=english_edition.edition_id,
                artifact_path=book_path,
                source_path=root / "civ0005.txt",
                adapter="phi_idt_legacy",
                source_hash="hash",
                segment_count=1,
                token_count=10,
            ),
        )
        register_book(
            catalog_path,
            latin_work,
            latin_edition,
            ReaderBookArtifact(
                artifact_id="defensio",
                work_id=latin_work.work_id,
                edition_id=latin_edition.edition_id,
                artifact_path=root / "books" / "defensio.duckdb",
                source_path=root / "civ0007.txt",
                adapter="phi_idt_legacy",
                source_hash="hash",
                segment_count=1,
                token_count=4,
            ),
        )
        register_book(
            catalog_path,
            septuagint_work,
            septuagint_edition,
            ReaderBookArtifact(
                artifact_id="septuagint-genesis",
                work_id=septuagint_work.work_id,
                edition_id=septuagint_edition.edition_id,
                artifact_path=root / "books" / "septuagint.duckdb",
                source_path=root / "civ0002.txt",
                adapter="phi_idt_legacy",
                source_hash="hash",
                segment_count=1,
                token_count=7,
            ),
        )
        register_book(
            catalog_path,
            hebrew_work,
            hebrew_edition,
            ReaderBookArtifact(
                artifact_id="hebrew-genesis",
                work_id=hebrew_work.work_id,
                edition_id=hebrew_edition.edition_id,
                artifact_path=root / "books" / "hebrew.duckdb",
                source_path=root / "civ0001.txt",
                adapter="phi_idt_legacy",
                source_hash="hash",
                segment_count=1,
                token_count=7,
            ),
        )
        register_book(
            catalog_path,
            greek_nt_work,
            greek_nt_edition,
            ReaderBookArtifact(
                artifact_id="greek-nt-matthew",
                work_id=greek_nt_work.work_id,
                edition_id=greek_nt_edition.edition_id,
                artifact_path=root / "books" / "greek_nt.duckdb",
                source_path=root / "civ0003.txt",
                adapter="phi_idt_legacy",
                source_hash="hash",
                segment_count=1,
                token_count=7,
            ),
        )
        register_book(
            catalog_path,
            coptic_work,
            coptic_edition,
            ReaderBookArtifact(
                artifact_id="coptic-james",
                work_id=coptic_work.work_id,
                edition_id=coptic_edition.edition_id,
                artifact_path=root / "books" / "coptic.duckdb",
                source_path=root / "cop0001.txt",
                adapter="phi_idt_legacy",
                source_hash="hash",
                segment_count=1,
                token_count=7,
            ),
        )
        register_source_metadata(
            catalog_path,
            [
                ReaderSourceMetadata(
                    collection_id="phi",
                    subject_kind="author",
                    subject_id="civ0005",
                    key="authtab_language",
                    value="lat",
                    source_path=root / "AUTHTAB.DIR",
                ),
                ReaderSourceMetadata(
                    collection_id="phi",
                    subject_kind="author",
                    subject_id="civ0002",
                    key="authtab_language",
                    value="grc",
                    source_path=root / "AUTHTAB.DIR",
                ),
                ReaderSourceMetadata(
                    collection_id="phi",
                    subject_kind="author",
                    subject_id="civ0001",
                    key="authtab_language",
                    value="lat",
                    source_path=root / "AUTHTAB.DIR",
                ),
                ReaderSourceMetadata(
                    collection_id="phi",
                    subject_kind="author",
                    subject_id="civ0003",
                    key="authtab_language",
                    value="grc",
                    source_path=root / "AUTHTAB.DIR",
                ),
                ReaderSourceMetadata(
                    collection_id="phi",
                    subject_kind="author",
                    subject_id="cop0001",
                    key="authtab_language",
                    value="c",
                    source_path=root / "AUTHTAB.DIR",
                ),
            ],
        )
        register_aliases(
            catalog_path,
            [
                ReaderAlias(
                    alias="John",
                    language="lat",
                    kind="work_title",
                    target=english_work.work_id,
                    display="English Bible (KJV or AV), John",
                    source_file="fixture",
                    sources=("generated",),
                )
            ],
        )
        register_segment_rows(
            book_path,
            segments=[
                ReaderSegment(
                    segment_id="john-2-2-1",
                    work_id=english_work.work_id,
                    edition_id=english_edition.edition_id,
                    segment_kind="line",
                    citation_path="2.2.1",
                    text="And both Jesus was called, and his disciples, to the marriage.",
                    normalized_text="and both jesus was called and his disciples to the marriage",
                    sort_key=1,
                )
            ],
            addresses=[],
        )

        result = CliRunner().invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "repair-languages",
                "--output",
                "json",
            ],
        )

        with duckdb.connect(str(catalog_path), read_only=True) as conn:
            work_languages = dict(
                conn.execute("SELECT work_id, language FROM works ORDER BY work_id").fetchall()
            )
            edition_languages = dict(
                conn.execute("SELECT work_id, language FROM editions ORDER BY work_id").fetchall()
            )
            alias_languages = dict(
                conn.execute("SELECT target, language FROM aliases ORDER BY target").fetchall()
            )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["summary"]["updated_count"] == LEGACY_LANGUAGE_REPAIR_EXPECTED_COUNT
    assert work_languages["langnet:reader:phi:civ0005.058"] == "eng"
    assert edition_languages["langnet:reader:phi:civ0005.058"] == "eng"
    assert alias_languages["langnet:reader:phi:civ0005.058"] == "eng"
    assert work_languages["langnet:reader:phi:civ0002.001"] == "grc"
    assert edition_languages["langnet:reader:phi:civ0002.001"] == "grc"
    assert work_languages["langnet:reader:phi:civ0001.001"] == "heb"
    assert edition_languages["langnet:reader:phi:civ0001.001"] == "heb"
    assert work_languages["langnet:reader:phi:civ0003.001"] == "grc"
    assert edition_languages["langnet:reader:phi:civ0003.001"] == "grc"
    assert work_languages["langnet:reader:phi:cop0001.020"] == "cop"
    assert edition_languages["langnet:reader:phi:cop0001.020"] == "cop"
    assert work_languages["langnet:reader:phi:civ0007.002"] == "lat"


def test_reader_cli_sync_metadata_overlays_updates_existing_catalog_author() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        book_path = root / "books" / "genesis.duckdb"
        overlay_dir = root / "overlays"
        overlay_dir.mkdir()
        create_catalog_db(catalog_path)
        create_book_db(book_path)
        work = ReaderWork(
            work_id="langnet:reader:phi:civ0004.001",
            collection_id="phi",
            language="lat",
            title="Genesis",
            author="Latin Bible (Vulgate)",
            author_id="civ0004",
            source_id="civ0004.001",
            cts_work_urn=None,
        )
        edition = ReaderEdition(
            edition_id="langnet:reader:phi:civ0004.001:legacy",
            work_id=work.work_id,
            label="legacy text dump",
            language="lat",
            source_path=root / "civ0004.txt",
            cts_edition_urn=None,
        )
        register_book(
            catalog_path,
            work,
            edition,
            ReaderBookArtifact(
                artifact_id="vulgate-genesis",
                work_id=work.work_id,
                edition_id=edition.edition_id,
                artifact_path=book_path,
                source_path=root / "civ0004.txt",
                adapter="phi_idt_legacy",
                source_hash="hash",
                segment_count=1,
                token_count=6,
            ),
        )
        (overlay_dir / "vulgate.yaml").write_text(
            """
overlays:
  - collection_id: "phi"
    match_field: "author_id"
    match_value: "civ0004"
    field: "author"
    value: "Saint Jerome"
    status: "accepted"
    confidence: "high"
    note: "Vulgate display author."
    evidence:
      - source_type: "web_source"
        citation: "https://catalog.perseus.org/catalog/urn:cite:perseus:author.785"
        label: "Perseus Catalog Jerome authority."
        retrieved_at: "2026-05-17"
  - collection_id: "phi"
    match_field: "author_id"
    match_value: "civ0004"
    field: "author_id"
    value: "urn:cts:latinLit:stoa0162"
    status: "accepted"
    confidence: "high"
    note: "Vulgate display author id."
    evidence:
      - source_type: "web_source"
        citation: "https://catalog.perseus.org/catalog/urn:cite:perseus:author.785"
        label: "Perseus Catalog Jerome authority."
        retrieved_at: "2026-05-17"
""",
            encoding="utf-8",
        )

        result = CliRunner().invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "sync-metadata-overlays",
                "--metadata-overlay-dir",
                str(overlay_dir),
                "--output",
                "json",
            ],
        )

        with duckdb.connect(str(catalog_path), read_only=True) as conn:
            row = conn.execute(
                "SELECT author, author_id FROM works WHERE work_id = ?",
                [work.work_id],
            ).fetchone()
            assert row is not None
            author, author_id = row

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["summary"]["applied_count"] == VULGATE_METADATA_OVERLAY_EXPECTED_COUNT
    assert (author, author_id) == ("Saint Jerome", "urn:cts:latinLit:stoa0162")


def test_reader_cli_sync_metadata_overlays_updates_individual_gospel_author() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        book_path = root / "books" / "mark.duckdb"
        overlay_dir = root / "overlays"
        overlay_dir.mkdir()
        create_catalog_db(catalog_path)
        create_book_db(book_path)
        work = ReaderWork(
            work_id="langnet:reader:phi:civ0003.002",
            collection_id="phi",
            language="grc",
            title="Mark",
            author="Greek New Testament (NT UBS3 edition)",
            author_id="civ0003",
            source_id="civ0003.002",
            cts_work_urn=None,
        )
        edition = ReaderEdition(
            edition_id="langnet:reader:phi:civ0003.002:legacy",
            work_id=work.work_id,
            label="legacy text dump",
            language="grc",
            source_path=root / "civ0003.txt",
            cts_edition_urn=None,
        )
        register_book(
            catalog_path,
            work,
            edition,
            ReaderBookArtifact(
                artifact_id="gnt-mark",
                work_id=work.work_id,
                edition_id=edition.edition_id,
                artifact_path=book_path,
                source_path=root / "civ0003.txt",
                adapter="phi_idt_legacy",
                source_hash="hash",
                segment_count=1,
                token_count=6,
            ),
        )
        register_source_metadata(
            catalog_path,
            [
                ReaderSourceMetadata(
                    collection_id="phi",
                    subject_kind="author",
                    subject_id="civ0003",
                    key="idt_author_name",
                    value="Greek New Testament (NT UBS3 edition)",
                    source_path=root / "civ0003.idt",
                )
            ],
        )
        (overlay_dir / "gospels.yaml").write_text(
            """
overlays:
  - collection_id: "phi"
    match_field: "source_id"
    match_value: "civ0003.002"
    field: "author"
    value: "Mark the Evangelist"
    status: "accepted"
    confidence: "medium"
    note: "Use traditional Gospel attribution for reader display."
    evidence:
      - source_type: "web_source"
        citation: "https://www.britannica.com/topic/Gospel-New-Testament"
        label: "Britannica gives the traditional four evangelist attribution."
        retrieved_at: "2026-05-17"
  - collection_id: "phi"
    match_field: "source_id"
    match_value: "civ0003.002"
    field: "author_id"
    value: "urn:cts:langnet:author.grc.mark-the-evangelist"
    status: "accepted"
    confidence: "medium"
    note: "Use a local CTS-shaped id for the traditional Gospel attribution."
    evidence:
      - source_type: "web_source"
        citation: "https://www.britannica.com/topic/Gospel-New-Testament"
        label: "Britannica gives the traditional four evangelist attribution."
        retrieved_at: "2026-05-17"
""",
            encoding="utf-8",
        )

        result = CliRunner().invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "sync-metadata-overlays",
                "--metadata-overlay-dir",
                str(overlay_dir),
                "--output",
                "json",
            ],
        )

        with duckdb.connect(str(catalog_path), read_only=True) as conn:
            row = conn.execute(
                "SELECT author, author_id FROM works WHERE work_id = ?",
                [work.work_id],
            ).fetchone()
            assert row is not None
            author, author_id = row
        works_result = CliRunner().invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "works",
                "--language",
                "grc",
                "--query",
                "Mark",
                "--output",
                "json",
            ],
        )

    assert result.exit_code == 0, result.output
    assert works_result.exit_code == 0, works_result.output
    payload = json.loads(result.output)
    works_payload = json.loads(works_result.output)
    work_item = works_payload["items"][0]
    assert payload["summary"]["applied_count"] == GOSPEL_METADATA_OVERLAY_EXPECTED_COUNT
    assert (author, author_id) == (
        "Mark the Evangelist",
        "urn:cts:langnet:author.grc.mark-the-evangelist",
    )
    assert work_item["author"] == "Mark the Evangelist"
    assert work_item["source_author"] == "Greek New Testament (NT UBS3 edition)"
    assert work_item["source_author_id"] == "civ0003"


def test_reader_cli_sync_metadata_attributions_supports_didactic_work_payload() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        attribution_dir = root / "attributions"
        attribution_dir.mkdir()
        _register_fixture_work(
            catalog_path,
            root,
            work_id="langnet:reader:phi:civ0004.001",
            collection_id="phi",
            language="lat",
            title="Genesis",
            author="Saint Jerome",
            author_id="urn:cts:latinLit:stoa0162",
            source_id="civ0004.001",
        )
        (attribution_dir / "vulgate.yaml").write_text(
            """
attributions:
  - collection_id: "phi"
    match_field: "author_id"
    match_value: "civ0004"
    relation_type: "translator"
    agent: "Saint Jerome"
    status: "accepted"
    confidence: "high"
    note: "Vulgate translation attribution."
    evidence:
      - source_type: "web_source"
        citation: "https://catalog.perseus.org/catalog/urn:cite:perseus:author.785"
        label: "Perseus records Jerome as translator."
        retrieved_at: "2026-05-17"
""",
            encoding="utf-8",
        )

        sync_result = CliRunner().invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "sync-metadata-attributions",
                "--metadata-attribution-dir",
                str(attribution_dir),
                "--output",
                "json",
            ],
        )
        works_result = CliRunner().invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "works",
                "--language",
                "lat",
                "--attributed-to",
                "Jerome",
                "--output",
                "json",
            ],
        )

    assert sync_result.exit_code == 0, sync_result.output
    assert works_result.exit_code == 0, works_result.output
    sync_payload = json.loads(sync_result.output)
    works_payload = json.loads(works_result.output)
    assert sync_payload["summary"]["synced_count"] == 1
    assert works_payload["items"][0]["translator_names"] == ["Saint Jerome"]
    assert works_payload["items"][0]["metadata_attributions"][0]["relation_type"] == "translator"


def test_reader_cli_filters_generated_discovery_group_and_tag() -> None:  # noqa: PLR0915
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = _write_fixture_reader_catalog(root)
        _register_fixture_work(
            catalog_path,
            root,
            work_id="urn:cts:greekLit:tlg0012.tlg001",
            collection_id="perseus",
            language="grc",
            title="Iliad",
            author="Homer",
            author_id="urn:cts:greekLit:tlg0012",
            source_id="tlg0012.tlg001",
        )
        classification_csv = root / "generated-classifications.csv"
        classification_csv.write_text(
            "\n".join(
                [
                    "work_id,classification_discovery_group_id,"
                    "classification_discovery_tags,"
                    "classification_global_popularity_score,"
                    "classification_global_popularity_tier,"
                    "classification_group_popularity_score,"
                    "classification_group_popularity_tier,"
                    "classification_period,classification_date_range,"
                    "classification_authorship_status,"
                    "classification_confidence,classification_notes,"
                    "classification_generator_models,classification_generator_run_id",
                    "urn:cts:greekLit:tlg0012.tlg002,narrative,epic|itihasa,"
                    "95,canonical,95,canonical,archaic,"
                    '"c. 8th-7th century BCE",traditional,high,'
                    "Generated by strict discovery classifier,model,run-1",
                    "urn:cts:greekLit:tlg0012.tlg001,epic,epic,"
                    "100,canonical,100,canonical,archaic,"
                    '"c. 8th century BCE",traditional,high,'
                    "Generated by strict discovery classifier,model,run-1",
                ]
            ),
            encoding="utf-8",
        )
        runner = CliRunner()
        sync = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "sync-classifications",
                "--classification-csv",
                str(classification_csv),
                "--output",
                "json",
            ],
        )
        assert sync.exit_code == 0, sync.output

        group = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "works",
                "--language",
                "grc",
                "--group",
                "epic",
                "--sort",
                "group-popularity",
                "--output",
                "json",
            ],
        )
        tag = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "popular",
                "--language",
                "grc",
                "--tag",
                "itihasa",
                "--output",
                "json",
            ],
        )
        groups = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "groups",
                "--language",
                "grc",
                "--output",
                "json",
            ],
        )
        tags = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "tags",
                "--language",
                "grc",
                "--output",
                "json",
            ],
        )
        facets = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "facets",
                "--language",
                "grc",
                "--output",
                "json",
            ],
        )
        shelves = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "shelves",
                "--language",
                "grc",
                "--sample-limit",
                "1",
                "--output",
                "json",
            ],
        )
        coverage = runner.invoke(
            main,
            ["reader", "--catalog", str(catalog_path), "coverage", "--output", "json"],
        )

    assert group.exit_code == 0, group.output
    group_payload = json.loads(group.output)
    assert group_payload["request"]["classification_group"] == "epic"
    assert [item["title"] for item in group_payload["items"]] == ["Iliad"]
    assert group_payload["items"][0]["classification_discovery_group_id"] == "epic"

    assert tag.exit_code == 0, tag.output
    tag_payload = json.loads(tag.output)
    assert tag_payload["request"]["classification_tag"] == "itihasa"
    assert [item["title"] for item in tag_payload["items"]] == ["Odyssey"]

    assert groups.exit_code == 0, groups.output
    group_items = json.loads(groups.output)["items"]
    assert [item["id"] for item in group_items] == ["epic", "narrative"]
    assert group_items[0]["work_count"] == 1
    assert group_items[0]["author_count"] == 1
    assert tags.exit_code == 0, tags.output
    tag_items = json.loads(tags.output)["items"]
    assert [item["id"] for item in tag_items] == ["epic", "itihasa"]
    assert tag_items[0]["work_count"] == GENERATED_CLASSIFICATION_COUNT
    assert facets.exit_code == 0, facets.output
    facets_payload = json.loads(facets.output)
    assert facets_payload["request"]["language"] == "grc"
    facet_ids = {item["id"] for item in facets_payload["items"]}
    assert {
        "discovery_groups",
        "discovery_tags",
        "sorts",
        "examples",
    }.issubset(facet_ids)
    assert any(
        example["command"].endswith("--tag ayurveda --sort group-popularity")
        for item in facets_payload["items"]
        if item["id"] == "examples"
        for example in item["examples"]
    )
    group_values = next(
        item["values"] for item in facets_payload["items"] if item["id"] == "discovery_groups"
    )
    assert [value["id"] for value in group_values] == ["epic", "narrative"]

    assert shelves.exit_code == 0, shelves.output
    shelves_payload = json.loads(shelves.output)
    assert shelves_payload["mode"] == "shelves"
    assert shelves_payload["request"]["language"] == "grc"
    assert shelves_payload["request"]["sample_limit"] == 1
    assert [item["id"] for item in shelves_payload["items"]] == ["epic", "narrative"]
    assert shelves_payload["items"][0]["query"] == {
        "group": "epic",
        "sort": "group-popularity",
    }
    assert [work["title"] for work in shelves_payload["items"][0]["sample_works"]] == ["Iliad"]

    assert coverage.exit_code == 0, coverage.output
    coverage_payload = json.loads(coverage.output)
    assert coverage_payload["mode"] == "coverage"
    coverage_by_language = {item["language"]: item for item in coverage_payload["items"]}
    assert coverage_by_language["grc"]["work_count"] == GENERATED_CLASSIFICATION_COUNT
    assert coverage_by_language["grc"]["classified_work_count"] == GENERATED_CLASSIFICATION_COUNT
    assert coverage_by_language["grc"]["group_count"] == GENERATED_CLASSIFICATION_COUNT
    assert coverage_by_language["grc"]["supported_reader_language"] is True


def test_reader_cli_sync_classifications_merge_preserves_existing_rows() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        create_catalog_db(catalog_path)
        for work_id, language, title, author_id in (
            ("lat-1", "lat", "Latin Fixture", "lat-author"),
            ("grc-1", "grc", "Greek Fixture", "grc-author"),
        ):
            book_path = root / "books" / f"{work_id}.duckdb"
            create_book_db(book_path)
            register_book(
                catalog_path,
                ReaderWork(
                    work_id=work_id,
                    collection_id="fixture",
                    language=language,
                    title=title,
                    author=title.replace(" Fixture", " Author"),
                    author_id=author_id,
                    source_id=work_id,
                ),
                ReaderEdition(
                    edition_id=f"{work_id}:edition",
                    work_id=work_id,
                    label="Fixture edition",
                    language=language,
                    source_path=root / f"{work_id}.xml",
                ),
                ReaderBookArtifact(
                    artifact_id=f"{work_id}:artifact",
                    work_id=work_id,
                    edition_id=f"{work_id}:edition",
                    artifact_path=book_path,
                    source_path=root / f"{work_id}.xml",
                    adapter="fixture",
                    source_hash="hash",
                    segment_count=0,
                    token_count=0,
                ),
            )
        first_csv = root / "latin.csv"
        second_csv = root / "greek.csv"
        header = (
            "work_id,classification_discovery_group_id,"
            "classification_discovery_tags,"
            "classification_global_popularity_score,"
            "classification_global_popularity_tier,"
            "classification_group_popularity_score,"
            "classification_group_popularity_tier,"
            "classification_period,classification_confidence"
        )
        first_csv.write_text(
            "\n".join(
                [
                    header,
                    "lat-1,epic,epic,100,canonical,100,canonical,augustan,high",
                ]
            ),
            encoding="utf-8",
        )
        second_csv.write_text(
            "\n".join(
                [
                    header,
                    "grc-1,drama,drama,88,major,91,major,classical,high",
                ]
            ),
            encoding="utf-8",
        )
        runner = CliRunner()

        first = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "sync-classifications",
                "--classification-csv",
                str(first_csv),
                "--output",
                "json",
            ],
        )
        second = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "sync-classifications",
                "--classification-csv",
                str(second_csv),
                "--merge",
                "--output",
                "json",
            ],
        )
        with duckdb.connect(str(catalog_path), read_only=True) as conn:
            work_ids = [
                row[0]
                for row in conn.execute(
                    "SELECT work_id FROM work_classifications ORDER BY work_id"
                ).fetchall()
            ]

    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output
    second_payload = json.loads(second.output)
    assert second_payload["summary"]["sync_mode"] == "merge"
    assert work_ids == ["grc-1", "lat-1"]


def test_reader_cli_classification_export_includes_generation_scaffold() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = _write_fixture_reader_catalog(root)
        output_csv = root / "classification-export.csv"

        result = CliRunner().invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "classification-export",
                "--language",
                "grc",
                "--path",
                str(output_csv),
            ],
        )

        assert result.exit_code == 0, result.output
        header = output_csv.read_text(encoding="utf-8").splitlines()[0].split(",")
        assert "word_count" in header
        assert "word_count_method" in header
        assert "classification_discovery_group_id" in header
        assert "classification_discovery_tags" in header
        assert "classification_global_popularity_score" in header
        assert "classification_group_popularity_score" in header
        assert "classification_popularity_tier" in header
        assert "classification_scope" in header
        assert "classification_scope_popularity_score" in header
        assert "classification_scope_popularity_tier" in header
        assert "classification_confidence" in header
        assert "classification_generator_models" in header
        assert "classification_generator_run_id" in header


def test_reader_cli_classification_export_includes_source_metadata_summary() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        create_catalog_db(catalog_path)
        _register_fixture_work(
            catalog_path,
            root,
            work_id="sanskrit_dcs:dcs_123",
            collection_id="sanskrit_dcs",
            language="san",
            title="Abhidharmakośa",
            author="Vasubandhu",
            author_id=None,
            source_id="dcs_123",
        )
        register_source_metadata(
            catalog_path,
            [
                ReaderSourceMetadata(
                    collection_id="sanskrit_dcs",
                    subject_kind="work",
                    subject_id="dcs_123",
                    key="dcs_subject",
                    value="Buddhist",
                    source_path=root / "dcs-corpus.tsv",
                ),
                ReaderSourceMetadata(
                    collection_id="sanskrit_dcs",
                    subject_kind="work",
                    subject_id="dcs_123",
                    key="dcs_time_slot",
                    value="classical",
                    source_path=root / "dcs-corpus.tsv",
                ),
                ReaderSourceMetadata(
                    collection_id="sanskrit_dcs",
                    subject_kind="work",
                    subject_id="dcs_123",
                    key="dcs_scope_hint",
                    value="Buddhist Scripture",
                    source_path=root / "dcs-corpus.tsv",
                ),
            ],
        )
        output_csv = root / "classification-export.csv"

        result = CliRunner().invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "classification-export",
                "--language",
                "san",
                "--path",
                str(output_csv),
            ],
        )

        assert result.exit_code == 0, result.output
        rows = list(csv.DictReader(output_csv.open("r", encoding="utf-8", newline="")))

    assert rows[0]["source_metadata_summary"] == (
        "dcs_scope_hint=Buddhist Scripture; dcs_subject=Buddhist; dcs_time_slot=classical"
    )


def test_reader_cli_classification_export_matches_perseus_metadata_by_cts_work_urn() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        create_catalog_db(catalog_path)
        _register_fixture_work(
            catalog_path,
            root,
            work_id="urn:cts:latinLit:phi0303.phi001",
            collection_id="phi",
            language="lat",
            title="grammatica",
            author="Aurelius Opillus",
            author_id="phi0303",
            source_id="lat0303.001",
        )
        register_source_metadata(
            catalog_path,
            [
                ReaderSourceMetadata(
                    collection_id="perseus",
                    subject_kind="work",
                    subject_id="phi0303.phi001",
                    key="perseus_subject",
                    value="Latin language--Grammar--Early works to 1500",
                    source_path=root / "perseus-latin-grammar.md",
                ),
                ReaderSourceMetadata(
                    collection_id="perseus",
                    subject_kind="work",
                    subject_id="phi0303.phi001",
                    key="perseus_year_published",
                    value="1907",
                    source_path=root / "perseus-latin-grammar.md",
                ),
            ],
        )
        output_csv = root / "classification-export.csv"

        result = CliRunner().invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "classification-export",
                "--language",
                "lat",
                "--path",
                str(output_csv),
            ],
        )
        rows = list(csv.DictReader(output_csv.open("r", encoding="utf-8", newline="")))

    assert result.exit_code == 0, result.output
    assert rows[0]["source_metadata_summary"] == (
        "perseus_subject=Latin language--Grammar--Early works to 1500; perseus_year_published=1907"
    )


def test_reader_cli_classification_export_preserves_multiple_source_subjects() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        create_catalog_db(catalog_path)
        _register_fixture_work(
            catalog_path,
            root,
            work_id="urn:cts:latinLit:phi0690.phi003",
            collection_id="phi",
            language="lat",
            title="Aeneis",
            author="Virgil",
            author_id="phi0690",
            source_id="lat0690.003",
        )
        register_source_metadata(
            catalog_path,
            [
                ReaderSourceMetadata(
                    collection_id="perseus",
                    subject_kind="work",
                    subject_id="phi0690.phi003",
                    key="perseus_subject",
                    value="Epic poetry, Latin",
                    source_path=root / "perseus-latin-epic.md",
                ),
                ReaderSourceMetadata(
                    collection_id="perseus",
                    subject_kind="work",
                    subject_id="phi0690.phi003",
                    key="perseus_subject",
                    value="Latin poetry",
                    source_path=root / "perseus-latin-poetry.md",
                ),
                ReaderSourceMetadata(
                    collection_id="perseus",
                    subject_kind="work",
                    subject_id="phi0690.phi003",
                    key="perseus_author",
                    value="Virgil",
                    source_path=root / "perseus-latin-epic.md",
                ),
            ],
        )
        output_csv = root / "classification-export.csv"

        result = CliRunner().invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "classification-export",
                "--language",
                "lat",
                "--path",
                str(output_csv),
            ],
        )
        rows = list(csv.DictReader(output_csv.open("r", encoding="utf-8", newline="")))

    assert result.exit_code == 0, result.output
    assert rows[0]["source_metadata_summary"] == (
        "perseus_subject=Epic poetry, Latin | Latin poetry; perseus_author=Virgil"
    )


def test_reader_cli_classify_works_writes_generated_csv() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        input_csv = root / "classification-export.csv"
        output_csv = root / "generated-classifications.csv"
        input_csv.write_text(
            "\n".join(
                [
                    "work_id,language,title,author,author_id,word_count",
                    "urn:cts:greekLit:tlg0012.tlg002,grc,Odyssey,Homer,"
                    "urn:cts:greekLit:tlg0012,121109",
                ]
            ),
            encoding="utf-8",
        )

        def classify(_payload: dict[str, object]) -> str:
            return (
                '{"rows":[{'
                '"work_id":"urn:cts:greekLit:tlg0012.tlg002",'
                '"classification_category":"epic",'
                '"classification_period":"archaic",'
                '"classification_date_range":"c. 8th-7th century BCE",'
                '"classification_authorship_status":"traditional",'
                '"classification_popularity_score":100,'
                '"classification_popularity_tier":"canonical",'
                '"classification_scope":"Epic Poetry",'
                '"classification_scope_popularity_score":100,'
                '"classification_scope_popularity_tier":"canonical",'
                '"classification_confidence":"high",'
                '"classification_notes":"Generated by test classifier"'
                "}]}"
            )

        with patch("langnet.cli._openrouter_work_classifier_callback", return_value=classify):
            result = CliRunner().invoke(
                main,
                [
                    "reader",
                    "classify-works",
                    "--input-csv",
                    str(input_csv),
                    "--output-csv",
                    str(output_csv),
                    "--model",
                    "openai:test-model",
                    "--run-id",
                    "run-test",
                    "--shuffle-seed",
                    "fixture-seed",
                    "--output",
                    "json",
                ],
            )

        rows = output_csv.read_text(encoding="utf-8").splitlines()
        payload = json.loads(result.output)

    assert result.exit_code == 0, result.output
    assert payload["summary"]["generated_count"] == 1
    assert payload["summary"]["shuffle_seed"] == "fixture-seed"
    assert "classification_category" in rows[0]
    assert "epic" in rows[1]
    assert "run-test" in rows[1]


def test_reader_cli_classification_escalation_export_selects_priority_rows() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        input_csv = root / "generated-classifications.csv"
        output_csv = root / "pro-audit-input.csv"
        input_csv.write_text(
            "\n".join(
                [
                    "work_id,language,title,classification_global_popularity_score,"
                    "classification_group_popularity_score,classification_confidence",
                    "minor,grc,Minor Work,12,20,high",
                    "iliad,grc,Iliad,100,100,high",
                    "uncertain,grc,Fragmenta,2,4,low",
                ]
            ),
            encoding="utf-8",
        )

        result = CliRunner().invoke(
            main,
            [
                "reader",
                "classification-escalation-export",
                "--input-csv",
                str(input_csv),
                "--path",
                str(output_csv),
                "--output",
                "json",
            ],
        )
        payload = json.loads(result.output)
        rows = list(csv.DictReader(output_csv.open("r", encoding="utf-8", newline="")))

    assert result.exit_code == 0, result.output
    assert payload["summary"]["selected_count"] == CLASSIFICATION_ESCALATION_FIXTURE_COUNT
    assert payload["summary"]["reason_counts"] == {
        "global_score": 1,
        "group_score": 1,
        "confidence": 1,
    }
    assert payload["summary"]["recommended_audit_model"] == "openai:deepseek/deepseek-v4-pro"
    assert [row["work_id"] for row in rows] == ["iliad", "uncertain"]


def test_reader_cli_research_needs_export_uses_catalog_coverage() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        create_catalog_db(catalog_path)
        _register_fixture_work(
            catalog_path,
            root,
            work_id="work-needs-research",
            collection_id="sanskrit_dcs",
            language="san",
            title="Needsresearchśāstra",
            author="Unknown",
            author_id=None,
            source_id="dcs_needs",
        )
        _register_fixture_work(
            catalog_path,
            root,
            work_id="work-covered",
            collection_id="sanskrit_dcs",
            language="san",
            title="Coveredśāstra",
            author="Unknown",
            author_id=None,
            source_id="dcs_covered",
        )
        register_metadata_attributions(
            catalog_path,
            [
                ReaderMetadataAttribution(
                    collection_id="sanskrit_dcs",
                    match_field="source_id",
                    match_value="dcs_covered",
                    relation_type="traditional_author",
                    agent="Coveredācārya",
                    status="accepted",
                    confidence="high",
                    note="Accepted fixture attribution.",
                    source_file="fixture.yaml",
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
        classification_csv = root / "generated.csv"
        output_csv = root / "research-needs.csv"
        classification_csv.write_text(
            "\n".join(
                [
                    "work_id,language,title,author,source_id,"
                    "classification_authorship_status,"
                    "classification_global_popularity_score,"
                    "classification_confidence,classification_notes",
                    "work-needs-research,san,Needsresearchśāstra,Unknown,dcs_needs,"
                    "traditional,90,medium,Traditionally attributed to Needācārya.",
                    "work-covered,san,Coveredśāstra,Unknown,dcs_covered,"
                    "traditional,90,medium,Traditionally attributed to Coveredācārya.",
                ]
            ),
            encoding="utf-8",
        )

        result = CliRunner().invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "research-needs-export",
                "--classification-csv",
                str(classification_csv),
                "--path",
                str(output_csv),
                "--output",
                "json",
            ],
        )
        payload = json.loads(result.output)
        rows = list(csv.DictReader(output_csv.open("r", encoding="utf-8", newline="")))

    assert result.exit_code == 0, result.output
    assert payload["summary"]["research_need_count"] == 1
    assert payload["summary"]["per_need_type_limit"] == DEFAULT_RESEARCH_NEED_TYPE_LIMIT
    assert rows[0]["work_id"] == "work-needs-research"
    assert rows[0]["research_need_type"] == "attribution_needed"
    assert rows[0]["recommended_layer"] == "data/curated/reader_attributions"


def test_reader_cli_sync_source_enrichment_imports_perseus_catalog_results() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        create_catalog_db(catalog_path)
        _register_fixture_work(
            catalog_path,
            root,
            work_id="urn:cts:latinLit:phi0419.phi001",
            collection_id="perseus",
            language="lat",
            title="Grammatica",
            author="Orbilius Pupillus",
            author_id="urn:cts:latinLit:phi0419",
            source_id="phi0419.phi001",
        )
        results_path = root / "perseus-latin-grammar.md"
        results_path.write_text(
            """
##### 1\\. [Grammatica](https://catalog.perseus.org/catalog/urn:cts:latinLit:phi0419.phi001.opp-lat1)

URN:urn:cts:latinLit:phi0419.phi001.opp-lat1Author:Orbilius PupillusEditor:Funaioli, Gino
Year Published:1907Language:Latin
""",
            encoding="utf-8",
        )

        result = CliRunner().invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "sync-source-enrichment",
                "--perseus-catalog-results",
                str(results_path),
                "--perseus-subject",
                "Latin language--Grammar--Early works to 1500",
                "--perseus-source-url",
                "https://catalog.perseus.org/latin-grammar",
                "--output",
                "json",
            ],
        )
        payload = json.loads(result.output)
        metadata = list_source_metadata(
            catalog_path,
            collection_id="perseus",
            subject_kind="work",
            subject_id="phi0419.phi001",
        )

    assert result.exit_code == 0, result.output
    assert payload["summary"]["perseus_metadata_count"] == PERSEUS_GRAMMAR_METADATA_COUNT
    metadata_by_key = {row["key"]: row["value"] for row in metadata}
    assert metadata_by_key["perseus_subject"] == ("Latin language--Grammar--Early works to 1500")
    assert metadata_by_key["perseus_year_published"] == "1907"


def test_work_classifier_retry_helper_retries_transient_exception() -> None:
    attempts = 0

    def request() -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("provider connection failed")
        return "ok"

    result = _call_work_classifier_with_retries(
        request,
        max_attempts=RETRY_TEST_ATTEMPTS,
        sleep_seconds=0,
    )

    assert result == "ok"
    assert attempts == RETRY_TEST_ATTEMPTS


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
        catalog_items = {item["id"]: item for item in json.loads(catalogs.output)["items"]}
        assert catalog_items["development"]["path"] == "data/build/reader/catalog.duckdb"
        assert catalog_items["classics"]["readiness"] in {"audit_artifact", "missing"}
        assert catalog_items["sanskrit"]["readiness"] in {"audit_artifact", "missing"}
        assert catalog_items["classics"]["label"].startswith("Audit")
        assert catalog_items["sanskrit"]["label"].startswith("Audit")


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


def test_reader_cli_exports_syncs_and_filters_author_classifications() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        export_csv = root / "author-export.csv"
        classification_csv = root / "author-classifications.csv"
        create_catalog_db(catalog_path)
        _register_fixture_work(
            catalog_path,
            root,
            work_id="urn:cts:latinLit:phi0690.phi003",
            collection_id="phi",
            language="lat",
            title="Aeneis",
            author="P. Vergilius Maro (Virgil)",
            author_id="urn:cts:latinLit:phi0690",
            source_id="lat0690.003",
        )
        _register_fixture_work(
            catalog_path,
            root,
            work_id="urn:cts:latinLit:civ0005.001",
            collection_id="phi",
            language="lat",
            title="Genesis",
            author="English Bible (KJV or AV)",
            author_id="civ0005",
            source_id="civ0005.001",
        )
        runner = CliRunner()

        export = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "author-classification-export",
                "--language",
                "lat",
                "--path",
                str(export_csv),
            ],
        )
        classification_csv.write_text(
            "\n".join(
                [
                    "author_id,author_language,author_canonical_name,"
                    "author_agent_kind,author_historicity_status,"
                    "author_period,author_date_range,author_region,"
                    "author_cultural_context,author_bio,"
                    "author_prominence_score,author_prominence_tier,"
                    "author_confidence,author_notes,"
                    "author_generator_models,author_generator_run_id",
                    "phi0690,lat,Virgil,person,historical,Augustan,70-19 BCE,"
                    'Italy,Roman poetry,"Roman poet of the Aeneid.",100,canonical,high,'
                    "Canonical Latin poet,test-model,run-1",
                    "civ0005,lat,King James Bible,collective,not_applicable,"
                    'early modern,1611 CE,England,English Bible,"Translation label.",20,'
                    "specialist,high,Source collection label,test-model,run-1",
                ]
            ),
            encoding="utf-8",
        )
        sync = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "sync-author-classifications",
                "--classification-csv",
                str(classification_csv),
                "--output",
                "json",
            ],
        )
        authors = runner.invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "authors",
                "--language",
                "lat",
                "--agent-kind",
                "collective",
                "--output",
                "json",
            ],
        )
        exported_header = export_csv.read_text(encoding="utf-8").splitlines()[0]
        exported_rows = list(csv.DictReader(export_csv.open("r", encoding="utf-8")))

    assert export.exit_code == 0, export.output
    assert "author_agent_kind" in exported_header
    assert "author_source_id" in exported_header
    assert "representative_titles" in exported_header
    assert {row["author_source_id"] for row in exported_rows} == {
        "civ0005",
        "urn:cts:latinLit:phi0690",
    }
    assert {row["representative_titles"] for row in exported_rows} == {"Aeneis", "Genesis"}
    assert sync.exit_code == 0, sync.output
    assert json.loads(sync.output)["summary"]["synced_count"] == AUTHOR_CLASSIFICATION_FIXTURE_COUNT
    assert authors.exit_code == 0, authors.output
    payload = json.loads(authors.output)
    assert [item["author_id"] for item in payload["items"]] == ["civ0005"]
    assert payload["items"][0]["author_canonical_name"] == "King James Bible"
    assert payload["items"][0]["author_agent_kind"] == "collective"
    assert payload["items"][0]["author_region"] == "England"


def test_reader_cli_classify_authors_generates_csv_with_stubbed_classifier() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        input_csv = root / "author-export.csv"
        output_csv = root / "author-generated.csv"
        input_csv.write_text(
            "\n".join(
                [
                    "author_id,author_language,author_display_name",
                    "phi0690,lat,P. Vergilius Maro (Virgil)",
                ]
            ),
            encoding="utf-8",
        )

        def classify(_model: str, **_kwargs):
            return lambda _payload: (
                '{"rows":[{'
                '"author_id":"phi0690",'
                '"author_language":"lat",'
                '"author_canonical_name":"Virgil",'
                '"author_agent_kind":"person",'
                '"author_historicity_status":"historical",'
                '"author_prominence_score":100,'
                '"author_prominence_tier":"canonical",'
                '"author_confidence":"high",'
                '"author_notes":"Canonical Latin poet."'
                "}]}"
            )

        with patch("langnet.cli._openrouter_author_classifier_callback", classify):
            result = CliRunner().invoke(
                main,
                [
                    "reader",
                    "classify-authors",
                    "--input-csv",
                    str(input_csv),
                    "--output-csv",
                    str(output_csv),
                    "--output",
                    "json",
                ],
            )
        rows = list(csv.DictReader(output_csv.open("r", encoding="utf-8", newline="")))

    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["summary"]["generated_count"] == 1
    assert rows[0]["author_canonical_name"] == "Virgil"


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
