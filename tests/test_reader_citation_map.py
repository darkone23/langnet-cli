from __future__ import annotations

import tempfile
from pathlib import Path

from langnet.reader.citation_map import accepted_citation_maps, load_citation_maps
from langnet.reader.models import ReaderCitationMap, ReaderMetadataOverlayEvidence
from langnet.reader.storage import (
    citation_maps_for_work,
    create_catalog_db,
    register_citation_maps,
)


def test_load_citation_maps_reads_source_scoped_projection_rules() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        path = root / "latin" / "de_inventione.yaml"
        path.parent.mkdir(parents=True)
        path.write_text(
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
    status: "candidate"
    confidence: "medium"
    note: "Three-part dictionary citation maps to local book.section."
    evidence:
      - source_type: "dictionary"
        citation: "Lewis & Short lego"
        label: "Lewis & Short cites legassit at Cic. Inv. 2, 50, 148."
      - source_type: "local-text"
        citation: "Perseus phi0474.phi036.perseus-lat1.xml"
        label: "Local TEI indexes the legassit passage as 2.148."
""".lstrip(),
            encoding="utf-8",
        )

        maps = load_citation_maps(root)

    assert len(maps) == 1
    citation_map = maps[0]
    assert citation_map.citation_map_id == "lewis-short-de-inventione-book-chapter-section"
    assert citation_map.source_id == "lewis_short"
    assert citation_map.work_id == "urn:cts:latinLit:phi0474.phi036"
    assert citation_map.projection_rule == "drop_middle_numeric_part"
    assert citation_map.example_machine_citation == "2.148"
    assert citation_map.status == "candidate"
    assert citation_map.source_file.endswith("latin/de_inventione.yaml")
    assert [evidence.source_type for evidence in citation_map.evidence] == [
        "dictionary",
        "local-text",
    ]


def test_load_citation_maps_rejects_non_mapping_items() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        path = root / "bad.yaml"
        path.write_text(
            """
citation_maps:
  - "not a map"
""".lstrip(),
            encoding="utf-8",
        )

        try:
            load_citation_maps(root)
        except ValueError as exc:
            message = str(exc)
        else:  # pragma: no cover - assertion branch
            raise AssertionError("Expected ValueError")

    assert "citation map item must be a mapping" in message


def test_accepted_citation_maps_filters_to_accepted_status() -> None:
    accepted = ReaderCitationMap(
        citation_map_id="accepted",
        source_id="lewis_short",
        work_id="urn:cts:latinLit:phi0474.phi036",
        source_pattern="book.chapter.section",
        machine_pattern="book.section",
        projection_rule="drop_middle_numeric_part",
        example_source_reference="Cic. Inv. 2, 50, 148",
        example_machine_citation="2.148",
        status="accepted",
        confidence="high",
        note="fixture",
        evidence=(
            ReaderMetadataOverlayEvidence(
                source_type="fixture",
                citation="fixture",
                label="fixture",
            ),
        ),
    )
    candidate = ReaderCitationMap(
        citation_map_id="candidate",
        source_id="lewis_short",
        work_id="urn:cts:latinLit:phi0474.phi036",
        source_pattern="book.chapter.section",
        machine_pattern="book.section",
        projection_rule="drop_middle_numeric_part",
        example_source_reference="Cic. Inv. 2, 50, 148",
        example_machine_citation="2.148",
        status="candidate",
        confidence="medium",
        note="fixture",
        evidence=accepted.evidence,
    )

    assert accepted_citation_maps([accepted, candidate]) == [accepted]


def test_register_citation_maps_and_query_by_work_and_source() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        catalog_path = Path(tmpdir) / "catalog.duckdb"
        create_catalog_db(catalog_path)
        register_citation_maps(
            catalog_path,
            [
                ReaderCitationMap(
                    citation_map_id="lewis-short-de-inventione-book-chapter-section",
                    source_id="lewis_short",
                    work_id="urn:cts:latinLit:phi0474.phi036",
                    source_pattern="book.chapter.section",
                    machine_pattern="book.section",
                    projection_rule="drop_middle_numeric_part",
                    example_source_reference="Cic. Inv. 2, 50, 148",
                    example_machine_citation="2.148",
                    status="candidate",
                    confidence="medium",
                    note="fixture",
                    evidence=(
                        ReaderMetadataOverlayEvidence(
                            source_type="dictionary",
                            citation="Lewis & Short lego",
                            label="Lewis & Short cites legassit at Cic. Inv. 2, 50, 148.",
                        ),
                    ),
                )
            ],
        )

        rows = citation_maps_for_work(
            catalog_path,
            "urn:cts:latinLit:phi0474.phi036",
            source_id="lewis_short",
        )

    assert len(rows) == 1
    assert rows[0]["citation_map_id"] == "lewis-short-de-inventione-book-chapter-section"
    assert rows[0]["source_pattern"] == "book.chapter.section"
    assert rows[0]["machine_pattern"] == "book.section"
    assert rows[0]["projection_rule"] == "drop_middle_numeric_part"
    assert rows[0]["evidence_count"] == 1
