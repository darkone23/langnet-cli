from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from langnet.reader.work_map import load_work_map_nodes

BHAGAVADGITA_CHAPTER_COUNT = 18


def test_load_work_map_nodes_reads_accepted_curated_nodes() -> None:
    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        source = root / "sanskrit" / "bhagavadgita.yaml"
        source.parent.mkdir()
        source.write_text(
            """
work_maps:
  - work_id: "urn:cts:sanskritLit:mbh.bhg"
    node_id: "bhg-01"
    parent_node_id: ""
    level: 1
    kind: "chapter"
    label: "Arjuna Viṣāda Yoga"
    native_label: "अर्जुनविषादयोग"
    ordinal: 1
    start_citation: "230573_1"
    end_citation: "230646"
    provenance: "curated"
    confidence: "high"
    status: "accepted"
    note: "Fixture chapter."
    evidence:
      - source_type: "source-root"
        citation: "fixture"
        label: "fixture"
""".lstrip(),
            encoding="utf-8",
        )

        nodes = load_work_map_nodes(root)

    assert len(nodes) == 1
    assert nodes[0].work_id == "urn:cts:sanskritLit:mbh.bhg"
    assert nodes[0].node_id == "bhg-01"
    assert nodes[0].label == "Arjuna Viṣāda Yoga"
    assert nodes[0].provenance == "curated"
    assert nodes[0].confidence == "high"
    assert nodes[0].source_file == str(source)


def test_load_work_map_nodes_rejects_missing_evidence() -> None:
    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        source = root / "bad.yaml"
        source.write_text(
            """
work_maps:
  - work_id: "urn:cts:sanskritLit:mbh.bhg"
    node_id: "bhg-01"
    level: 1
    kind: "chapter"
    label: "Arjuna Viṣāda Yoga"
    ordinal: 1
    start_citation: "230573_1"
    end_citation: "230646"
    provenance: "curated"
    confidence: "high"
    status: "accepted"
    note: "Fixture chapter."
""".lstrip(),
            encoding="utf-8",
        )

        try:
            load_work_map_nodes(root)
        except ValueError as exc:
            assert "requires at least one evidence item" in str(exc)
        else:
            raise AssertionError("expected missing evidence to fail")


def test_seed_bhagavadgita_work_map_has_eighteen_chapters() -> None:
    nodes = load_work_map_nodes(Path("data/curated/reader_work_maps/sanskrit"))

    bhg_nodes = [node for node in nodes if node.work_id == "urn:cts:sanskritLit:mbh.bhg"]

    assert len(bhg_nodes) == BHAGAVADGITA_CHAPTER_COUNT
    assert bhg_nodes[0].label == "Arjuna Viṣāda Yoga"
    assert bhg_nodes[-1].label == "Mokṣa Sannyāsa Yoga"
    assert {node.provenance for node in bhg_nodes} == {"curated"}
