from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from langnet.reader.division_metadata import (
    accepted_division_metadata,
    load_division_metadata,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CURATED_DIVISION_METADATA_ROOT = REPO_ROOT / "data" / "curated" / "reader_division_metadata"


def _accepted_metadata_node_ids_for_work(work_id: str) -> list[str]:
    rows = accepted_division_metadata(load_division_metadata(CURATED_DIVISION_METADATA_ROOT))
    return sorted([row.node_id for row in rows if row.work_id == work_id])


def test_load_division_metadata_reads_chapter_bio_with_provenance() -> None:
    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        source = root / "sanskrit" / "bhagavadgita.yaml"
        source.parent.mkdir()
        source.write_text(
            """
division_metadata:
  - work_id: "urn:cts:sanskritLit:mbh.bhg"
    node_id: "bhg-09"
    summary: "A concise reviewed note on royal knowledge and secrecy."
    short_label: "Royal knowledge"
    traditional_reference: "BhG 9"
    status: "accepted"
    confidence: "high"
    generator_model: ""
    review_status: "reviewed"
    note: "Fixture reviewed chapter note."
    evidence:
      - source_type: "source-root"
        citation: "fixture"
        label: "fixture evidence"
""".lstrip(),
            encoding="utf-8",
        )

        rows = load_division_metadata(root)

    assert len(rows) == 1
    row = rows[0]
    assert row.work_id == "urn:cts:sanskritLit:mbh.bhg"
    assert row.node_id == "bhg-09"
    assert row.summary.startswith("A concise reviewed note")
    assert row.short_label == "Royal knowledge"
    assert row.traditional_reference == "BhG 9"
    assert row.status == "accepted"
    assert row.review_status == "reviewed"
    assert row.source_file == str(source)
    assert row.evidence[0].source_type == "source-root"


def test_accepted_division_metadata_filters_reviewable_drafts() -> None:
    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        source = root / "draft.yaml"
        source.write_text(
            """
division_metadata:
  - work_id: "w"
    node_id: "n1"
    summary: "accepted"
    short_label: "accepted"
    traditional_reference: "W 1"
    status: "accepted"
    confidence: "high"
    generator_model: ""
    review_status: "reviewed"
    note: "fixture"
    evidence:
      - source_type: "fixture"
        citation: "fixture"
        label: "fixture"
  - work_id: "w"
    node_id: "n2"
    summary: "draft"
    short_label: "draft"
    traditional_reference: "W 2"
    status: "candidate"
    confidence: "medium"
    generator_model: "openrouter:test"
    review_status: "llm_draft"
    note: "fixture"
    evidence:
      - source_type: "llm"
        citation: "openrouter:test"
        label: "fixture"
""".lstrip(),
            encoding="utf-8",
        )

        rows = load_division_metadata(root)

    assert [row.node_id for row in accepted_division_metadata(rows)] == ["n1"]


def test_load_division_metadata_rejects_missing_evidence() -> None:
    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        source = root / "bad.yaml"
        source.write_text(
            """
division_metadata:
  - work_id: "w"
    node_id: "n"
    summary: "missing evidence"
    short_label: "bad"
    traditional_reference: "W 1"
    status: "accepted"
    confidence: "high"
    generator_model: ""
    review_status: "reviewed"
    note: "fixture"
""".lstrip(),
            encoding="utf-8",
        )

        try:
            load_division_metadata(root)
        except ValueError as exc:
            message = str(exc)
        else:
            raise AssertionError("expected missing evidence to fail")

    assert "requires at least one evidence item" in message


def test_curated_bhagavadgita_division_metadata_covers_all_chapters() -> None:
    node_ids = _accepted_metadata_node_ids_for_work("urn:cts:sanskritLit:mbh.bhg")
    expected = [f"bhg-{index:02d}" for index in range(1, 19)]
    assert node_ids == expected


def test_curated_republic_division_metadata_covers_all_books() -> None:
    node_ids = _accepted_metadata_node_ids_for_work("urn:ctsv2:grc:politeia-kateben-chthes-eis")
    expected = [f"rep-book-{index:02d}" for index in range(1, 11)]
    assert node_ids == expected
