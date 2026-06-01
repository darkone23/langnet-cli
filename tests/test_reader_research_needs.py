from __future__ import annotations

import csv
import tempfile
from pathlib import Path

from langnet.reader.models import (
    ReaderBookArtifact,
    ReaderEdition,
    ReaderMetadataAttribution,
    ReaderMetadataOverlayEvidence,
    ReaderSourceMetadata,
    ReaderWork,
    ReaderWorkMapNode,
)
from langnet.reader.research_needs import (
    ResearchNeedsConfig,
    export_research_needs_csv,
    research_needs_for_classification_csv,
)
from langnet.reader.storage import (
    create_book_db,
    create_catalog_db,
    register_book,
    register_metadata_attributions,
    register_source_metadata,
    register_work_map_nodes,
)

POPULAR_SCORE = 95
LONG_WORK_COUNT = 25000
RESEARCH_NEEDS_FIXTURE_COUNT = 2
UNKNOWN_AUTHOR_INDEX_CUTOFF = 3


def test_research_needs_flags_uncovered_generated_attribution_claim() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = _fixture_catalog(
            root,
            work_id="work-unknown",
            language="san",
            title="Exampleśāstra",
            author="Unknown",
            source_id="dcs_1",
        )
        classification_csv = root / "generated.csv"
        _write_classification_csv(
            classification_csv,
            [
                {
                    "work_id": "work-unknown",
                    "language": "san",
                    "title": "Exampleśāstra",
                    "author": "Unknown",
                    "source_id": "dcs_1",
                    "classification_authorship_status": "traditional",
                    "classification_global_popularity_score": str(POPULAR_SCORE),
                    "classification_confidence": "medium",
                    "classification_notes": "Traditionally attributed to Exampleācārya.",
                }
            ],
        )

        needs = research_needs_for_classification_csv(
            config=ResearchNeedsConfig(
                catalog_path=catalog_path,
                classification_csv=classification_csv,
            )
        )

    assert len(needs) == 1
    assert needs[0]["research_need_type"] == "attribution_needed"
    assert needs[0]["recommended_layer"] == "data/curated/reader_attributions"
    assert "generated attribution is not curated" in needs[0]["research_reason"]
    assert "Exampleśāstra Sanskrit attribution" in needs[0]["suggested_queries"]


def test_research_needs_does_not_repeat_accepted_attribution_research() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = _fixture_catalog(
            root,
            work_id="work-covered",
            language="san",
            title="Coveredśāstra",
            author="Unknown",
            source_id="dcs_2",
        )
        evidence = (
            ReaderMetadataOverlayEvidence(
                source_type="web_source",
                citation="https://example.org/covered",
                label="Example source.",
            ),
        )
        register_metadata_attributions(
            catalog_path,
            [
                ReaderMetadataAttribution(
                    collection_id="sanskrit_dcs",
                    match_field="source_id",
                    match_value="dcs_2",
                    relation_type="traditional_author",
                    agent="Coveredācārya",
                    status="accepted",
                    confidence="high",
                    note="Accepted attribution fixture.",
                    source_file="fixture.yaml",
                    evidence=evidence,
                )
            ],
        )
        register_source_metadata(
            catalog_path,
            [
                ReaderSourceMetadata(
                    collection_id="sanskrit_dcs",
                    subject_kind="work",
                    subject_id="dcs_2",
                    key="source_author",
                    value="Coveredācārya",
                    source_path=root / "fixture.tsv",
                )
            ],
        )
        classification_csv = root / "generated.csv"
        _write_classification_csv(
            classification_csv,
            [
                {
                    "work_id": "work-covered",
                    "language": "san",
                    "title": "Coveredśāstra",
                    "author": "Unknown",
                    "source_id": "dcs_2",
                    "classification_authorship_status": "traditional",
                    "classification_global_popularity_score": str(POPULAR_SCORE),
                    "classification_confidence": "medium",
                    "classification_notes": "Traditionally attributed to Coveredācārya.",
                }
            ],
        )

        needs = research_needs_for_classification_csv(
            config=ResearchNeedsConfig(
                catalog_path=catalog_path,
                classification_csv=classification_csv,
            )
        )

    assert needs == []


def test_research_needs_flags_large_work_without_work_map_until_curated() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = _fixture_catalog(
            root,
            work_id="work-long",
            language="grc",
            title="Long Treatise",
            author="Known Author",
            source_id="tlg0001.001",
        )
        classification_csv = root / "generated.csv"
        _write_classification_csv(
            classification_csv,
            [
                {
                    "work_id": "work-long",
                    "language": "grc",
                    "title": "Long Treatise",
                    "author": "Known Author",
                    "source_id": "tlg0001.001",
                    "word_count": str(LONG_WORK_COUNT),
                    "classification_global_popularity_score": "60",
                    "classification_confidence": "high",
                    "classification_notes": "A long multi-book technical treatise.",
                }
            ],
        )

        before = research_needs_for_classification_csv(
            config=ResearchNeedsConfig(
                catalog_path=catalog_path,
                classification_csv=classification_csv,
            )
        )
        register_work_map_nodes(
            catalog_path,
            [
                ReaderWorkMapNode(
                    work_id="work-long",
                    node_id="book-1",
                    level=1,
                    kind="book",
                    label="Book 1",
                    ordinal=1,
                    start_citation="1",
                    end_citation="1",
                    provenance="curated",
                    confidence="high",
                    status="accepted",
                    note="Accepted map fixture.",
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
        after = research_needs_for_classification_csv(
            config=ResearchNeedsConfig(
                catalog_path=catalog_path,
                classification_csv=classification_csv,
            )
        )

    assert [need["research_need_type"] for need in before] == ["work_map_needed"]
    assert after == []


def test_export_research_needs_csv_writes_priority_order() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = _fixture_catalog(
            root,
            work_id="work-1",
            language="lat",
            title="Popular Work",
            author="Unknown",
            source_id="phi0001.001",
        )
        _fixture_catalog(
            root,
            work_id="work-2",
            language="lat",
            title="Low Confidence Work",
            author="Known Author",
            source_id="phi0002.001",
            catalog_path=catalog_path,
        )
        classification_csv = root / "generated.csv"
        output_csv = root / "research-needs.csv"
        _write_classification_csv(
            classification_csv,
            [
                {
                    "work_id": "work-1",
                    "language": "lat",
                    "title": "Popular Work",
                    "author": "Unknown",
                    "source_id": "phi0001.001",
                    "classification_authorship_status": "traditional",
                    "classification_global_popularity_score": "99",
                    "classification_confidence": "medium",
                    "classification_notes": "Traditionally attributed to Popularius.",
                },
                {
                    "work_id": "work-2",
                    "language": "lat",
                    "title": "Low Confidence Work",
                    "author": "Known Author",
                    "source_id": "phi0002.001",
                    "classification_global_popularity_score": "10",
                    "classification_confidence": "low",
                    "classification_notes": "Classification is uncertain.",
                },
            ],
        )

        summary = export_research_needs_csv(
            config=ResearchNeedsConfig(
                catalog_path=catalog_path,
                classification_csv=classification_csv,
                output_csv=output_csv,
            )
        )
        rows = list(csv.DictReader(output_csv.open("r", encoding="utf-8", newline="")))

    assert summary["input_count"] == RESEARCH_NEEDS_FIXTURE_COUNT
    assert summary["research_need_count"] == RESEARCH_NEEDS_FIXTURE_COUNT
    assert rows[0]["work_id"] == "work-1"
    assert rows[0]["research_need_type"] == "attribution_needed"
    assert rows[1]["research_need_type"] == "source_context_needed"


def test_research_needs_can_cap_each_need_type_for_queue_diversity() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        create_catalog_db(catalog_path)
        for index in range(1, 5):
            _fixture_catalog(
                root,
                work_id=f"work-{index}",
                language="grc",
                title=f"Work {index}",
                author="Unknown" if index < UNKNOWN_AUTHOR_INDEX_CUTOFF else "Known Author",
                source_id=f"tlg000{index}.001",
                catalog_path=catalog_path,
            )
        classification_csv = root / "generated.csv"
        _write_classification_csv(
            classification_csv,
            [
                {
                    "work_id": "work-1",
                    "language": "grc",
                    "title": "Work 1",
                    "author": "Unknown",
                    "source_id": "tlg0001.001",
                    "classification_authorship_status": "traditional",
                    "classification_global_popularity_score": "99",
                    "classification_confidence": "medium",
                    "classification_notes": "Traditionally attributed to First.",
                },
                {
                    "work_id": "work-2",
                    "language": "grc",
                    "title": "Work 2",
                    "author": "Unknown",
                    "source_id": "tlg0002.001",
                    "classification_authorship_status": "traditional",
                    "classification_global_popularity_score": "98",
                    "classification_confidence": "medium",
                    "classification_notes": "Traditionally attributed to Second.",
                },
                {
                    "work_id": "work-3",
                    "language": "grc",
                    "title": "Work 3",
                    "author": "Known Author",
                    "source_id": "tlg0003.001",
                    "classification_global_popularity_score": "10",
                    "classification_confidence": "low",
                    "classification_notes": "Low confidence classification.",
                },
                {
                    "work_id": "work-4",
                    "language": "grc",
                    "title": "Work 4",
                    "author": "Known Author",
                    "source_id": "tlg0004.001",
                    "classification_global_popularity_score": "9",
                    "classification_confidence": "low",
                    "classification_notes": "Low confidence classification.",
                },
            ],
        )

        needs = research_needs_for_classification_csv(
            config=ResearchNeedsConfig(
                catalog_path=catalog_path,
                classification_csv=classification_csv,
                per_need_type_limit=1,
            )
        )

    assert [need["research_need_type"] for need in needs] == [
        "attribution_needed",
        "source_context_needed",
    ]
    assert [need["work_id"] for need in needs] == ["work-1", "work-3"]


def test_research_needs_skips_unresolved_generated_rows_by_default() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = _fixture_catalog(
            root,
            work_id="work-resolved",
            language="grc",
            title="Resolved Work",
            author="Unknown",
            source_id="tlg0001.001",
        )
        classification_csv = root / "generated.csv"
        _write_classification_csv(
            classification_csv,
            [
                {
                    "work_id": "work-unresolved",
                    "language": "grc",
                    "title": "Unresolved Work",
                    "author": "Unknown",
                    "source_id": "tlg9999.001",
                    "classification_authorship_status": "traditional",
                    "classification_global_popularity_score": "99",
                    "classification_confidence": "medium",
                    "classification_notes": "Traditionally attributed to Missing.",
                },
                {
                    "work_id": "work-resolved",
                    "language": "grc",
                    "title": "Resolved Work",
                    "author": "Unknown",
                    "source_id": "tlg0001.001",
                    "classification_authorship_status": "traditional",
                    "classification_global_popularity_score": "90",
                    "classification_confidence": "medium",
                    "classification_notes": "Traditionally attributed to Present.",
                },
            ],
        )

        needs = research_needs_for_classification_csv(
            config=ResearchNeedsConfig(
                catalog_path=catalog_path,
                classification_csv=classification_csv,
            )
        )

    assert [need["work_id"] for need in needs] == ["work-resolved"]
    assert needs[0]["research_need_type"] == "attribution_needed"


def test_research_needs_resolves_generated_tlg_id_to_current_catalog_identity() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = _fixture_catalog(
            root,
            work_id="urn:cts:greekLit:tlg0086.tlg034",
            language="grc",
            title="Περὶ ποιητικῆς",
            author="Aristotle",
            source_id="tlg0086.tlg034",
        )
        classification_csv = root / "generated.csv"
        _write_classification_csv(
            classification_csv,
            [
                {
                    "work_id": "langnet:reader:tlg:tlg0086.034",
                    "language": "grc",
                    "title": "Poetica",
                    "author": "Aristotle",
                    "source_id": "tlg0086.034",
                    "classification_authorship_status": "single_attributed",
                    "classification_global_popularity_score": "90",
                    "classification_confidence": "high",
                    "classification_notes": "The work is securely attributed to Aristotle.",
                }
            ],
        )

        needs = research_needs_for_classification_csv(
            config=ResearchNeedsConfig(
                catalog_path=catalog_path,
                classification_csv=classification_csv,
            )
        )

    assert len(needs) == 1
    assert needs[0]["work_id"] == "urn:cts:greekLit:tlg0086.tlg034"
    assert needs[0]["source_id"] == "tlg0086.tlg034"
    assert needs[0]["title"] == "Περὶ ποιητικῆς"
    assert needs[0]["research_need_type"] == "attribution_needed"


def test_research_needs_prefers_exact_catalog_work_id_over_ambiguous_alias() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = _fixture_catalog(
            root,
            work_id="langnet:reader:tlg:tlg0090.001",
            language="grc",
            title="Geographiae informatio",
            author="Agathemerus",
            source_id="tlg0090.001",
        )
        _fixture_catalog(
            root,
            work_id="urn:cts:greekLit:tlg0090.tlg001",
            language="lat",
            title="Geographiae Informatio",
            author="Agathemerus",
            source_id="tlg0090.tlg001",
            catalog_path=catalog_path,
        )
        classification_csv = root / "generated.csv"
        _write_classification_csv(
            classification_csv,
            [
                {
                    "work_id": "langnet:reader:tlg:tlg0090.001",
                    "language": "grc",
                    "title": "Geographiae informatio",
                    "author": "Agathemerus",
                    "source_id": "tlg0090.001",
                    "classification_authorship_status": "single_attributed",
                    "classification_global_popularity_score": "25",
                    "classification_confidence": "high",
                    "classification_notes": "The work is attributed to Agathemerus.",
                }
            ],
        )

        needs = research_needs_for_classification_csv(
            config=ResearchNeedsConfig(
                catalog_path=catalog_path,
                classification_csv=classification_csv,
            )
        )

    assert len(needs) == 1
    assert needs[0]["work_id"] == "langnet:reader:tlg:tlg0090.001"
    assert needs[0]["language"] == "grc"
    assert needs[0]["source_id"] == "tlg0090.001"


def test_research_needs_can_emit_unresolved_generated_rows_for_maintenance() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = _fixture_catalog(
            root,
            work_id="work-resolved",
            language="grc",
            title="Resolved Work",
            author="Known Author",
            source_id="tlg0001.001",
        )
        classification_csv = root / "generated.csv"
        output_csv = root / "research-needs.csv"
        _write_classification_csv(
            classification_csv,
            [
                {
                    "work_id": "work-unresolved",
                    "language": "grc",
                    "title": "Unresolved Work",
                    "author": "Unknown",
                    "source_id": "tlg9999.001",
                    "classification_authorship_status": "traditional",
                    "classification_global_popularity_score": "99",
                    "classification_confidence": "medium",
                    "classification_notes": "Traditionally attributed to Missing.",
                }
            ],
        )

        summary = export_research_needs_csv(
            config=ResearchNeedsConfig(
                catalog_path=catalog_path,
                classification_csv=classification_csv,
                output_csv=output_csv,
                include_unresolved=True,
            )
        )
        rows = list(csv.DictReader(output_csv.open("r", encoding="utf-8", newline="")))

    assert summary["catalog_resolved_count"] == 0
    assert summary["unresolved_input_count"] == 1
    assert summary["include_unresolved"] is True
    assert rows[0]["research_status"] == "identity_unresolved"
    assert rows[0]["research_need_type"] == "catalog_identity_needed"
    assert rows[0]["recommended_layer"] == "generated classification CSV / catalog restore"


def _fixture_catalog(  # noqa: PLR0913
    root: Path,
    *,
    work_id: str,
    language: str,
    title: str,
    author: str,
    source_id: str,
    catalog_path: Path | None = None,
) -> Path:
    catalog_path = catalog_path or root / "catalog.duckdb"
    book_path = root / "books" / f"{work_id}.duckdb"
    create_catalog_db(catalog_path)
    create_book_db(book_path)
    work = ReaderWork(
        work_id=work_id,
        collection_id=_collection_for_language(language),
        language=language,
        title=title,
        author=author,
        source_id=source_id,
    )
    edition = ReaderEdition(
        edition_id=f"{work_id}:edition",
        work_id=work_id,
        label="Fixture edition",
        language=language,
        source_path=root / f"{work_id}.xml",
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
        ),
    )
    return catalog_path


def _collection_for_language(language: str) -> str:
    if language == "san":
        return "sanskrit_dcs"
    if language == "lat":
        return "phi"
    return "tlg"


def _write_classification_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "work_id",
        "language",
        "title",
        "author",
        "source_id",
        "word_count",
        "classification_authorship_status",
        "classification_global_popularity_score",
        "classification_confidence",
        "classification_notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})
