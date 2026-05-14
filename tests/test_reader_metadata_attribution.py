from __future__ import annotations

import tempfile
from pathlib import Path

from langnet.reader.metadata_attribution import load_metadata_attributions


def test_loads_reader_metadata_attribution_with_evidence() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir) / "attributions"
        source = root / "sanskrit" / "ambiguous.yaml"
        source.parent.mkdir(parents=True)
        source.write_text(
            """\
attributions:
  - collection_id: "sanskrit_dcs"
    match_field: "source_id"
    match_value: "dcs_example"
    relation_type: "possible_author"
    agent: "Aristotle"
    status: "accepted"
    confidence: "medium"
    note: "Accepted as a recorded attribution claim, not as display metadata."
    evidence:
      - source_type: "web_source"
        citation: "https://example.org/source"
        label: "Source records the possible attribution."
        retrieved_at: "2026-05-13"
""",
            encoding="utf-8",
        )

        attributions = load_metadata_attributions(root)

    assert len(attributions) == 1
    attribution = attributions[0]
    assert attribution.collection_id == "sanskrit_dcs"
    assert attribution.match_field == "source_id"
    assert attribution.match_value == "dcs_example"
    assert attribution.relation_type == "possible_author"
    assert attribution.agent == "Aristotle"
    assert attribution.status == "accepted"
    assert attribution.confidence == "medium"
    assert attribution.source_file.endswith("sanskrit/ambiguous.yaml")
    assert attribution.evidence[0].source_type == "web_source"
    assert attribution.evidence[0].citation == "https://example.org/source"


def test_metadata_attribution_loader_rejects_unsupported_relation_type() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir) / "attributions"
        source = root / "bad.yaml"
        source.parent.mkdir(parents=True)
        source.write_text(
            """\
attributions:
  - collection_id: "sanskrit_dcs"
    match_field: "source_id"
    match_value: "dcs_example"
    relation_type: "maybe_sort_of_author"
    agent: "Aristotle"
    status: "accepted"
    confidence: "medium"
    note: "Unsupported relation type."
    evidence:
      - source_type: "web_source"
        citation: "https://example.org/source"
        label: "Source records the possible attribution."
""",
            encoding="utf-8",
        )

        try:
            load_metadata_attributions(root)
        except ValueError as exc:
            assert "unsupported metadata attribution relation_type" in str(exc)
        else:
            raise AssertionError("expected unsupported relation_type to raise ValueError")


def test_curated_reader_metadata_attributions_load() -> None:
    attributions = load_metadata_attributions(Path("data/curated/reader_attributions"))

    seeded = {
        (
            attribution.collection_id,
            attribution.match_value,
            attribution.relation_type,
            attribution.agent,
        )
        for attribution in attributions
    }
    assert (
        "sanskrit_dcs",
        "dcs_154",
        "traditional_author",
        "Vyāsa",
    ) in seeded
    assert (
        "sanskrit_dcs",
        "dcs_354",
        "attributed_author",
        "Kauṭilya",
    ) in seeded
    assert (
        "sanskrit_dcs",
        "dcs_354",
        "possible_author",
        "Chanakya",
    ) in seeded
    assert (
        "sanskrit_dcs",
        "dcs_58",
        "redactor",
        "Dṛḍhabala",
    ) in seeded
