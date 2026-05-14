from __future__ import annotations

import tempfile
from pathlib import Path

from langnet.reader.metadata_overlay import load_metadata_overlays
from langnet.reader.metadata_overlay_review import (
    ReaderMetadataOverlayDecision,
    review_metadata_overlay_candidates,
)


def test_loads_reader_metadata_overlay_with_evidence() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir) / "overlays"
        (root / "sanskrit").mkdir(parents=True)
        (root / "sanskrit" / "panini.yaml").write_text(
            """
overlays:
  - collection_id: "sanskrit_json"
    match_field: "source_id"
    match_value: "corpus_sa_zivasUtra"
    field: "author"
    value: "Pāṇini"
    status: "candidate"
    confidence: "medium"
    note: "Candidate only: grammatical Māheśvara/Śiva Sūtras, not the Kashmir Śaiva work."
    evidence:
      - source_type: "web"
        citation: "https://learnsanskrit.org/panini/shivasutras/"
        label: "Learn Sanskrit Online, The Shiva Sutras - Panini"
        retrieved_at: "2026-05-13"
""",
            encoding="utf-8",
        )

        overlays = load_metadata_overlays(root)

    assert len(overlays) == 1
    overlay = overlays[0]
    assert overlay.collection_id == "sanskrit_json"
    assert overlay.match_field == "source_id"
    assert overlay.match_value == "corpus_sa_zivasUtra"
    assert overlay.field == "author"
    assert overlay.value == "Pāṇini"
    assert overlay.status == "candidate"
    assert overlay.confidence == "medium"
    assert "Candidate only" in overlay.note
    assert overlay.source_file.endswith("sanskrit/panini.yaml")
    assert overlay.evidence[0].source_type == "web"
    assert overlay.evidence[0].citation.startswith("https://learnsanskrit.org/")


def test_metadata_overlay_loader_rejects_missing_evidence() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir) / "overlays"
        root.mkdir()
        (root / "bad.yaml").write_text(
            """
overlays:
  - collection_id: "sanskrit_json"
    match_field: "source_id"
    match_value: "corpus_sa_zivasUtra"
    field: "author"
    value: "Pāṇini"
    status: "accepted"
    confidence: "high"
    note: "Unsupported because no evidence is provided."
""",
            encoding="utf-8",
        )

        try:
            load_metadata_overlays(root)
        except ValueError as exc:
            message = str(exc)
        else:
            message = ""

    assert "bad.yaml" in message
    assert "at least one evidence item" in message


def test_curated_reader_metadata_overlays_load() -> None:
    overlays = load_metadata_overlays(Path("data/curated/reader_metadata"))

    assert any(
        overlay.field == "author" and overlay.value == "Pāṇini" and overlay.status == "candidate"
        for overlay in overlays
    )


def test_overlay_review_can_promote_approved_candidate_with_evidence() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir) / "overlays"
        root.mkdir()
        path = root / "sanskrit.yaml"
        path.write_text(
            """
overlays:
  - collection_id: "sanskrit_json"
    match_field: "source_id"
    match_value: "sanskrit_shiva"
    field: "author"
    value: "Pāṇini"
    status: "candidate"
    confidence: "medium"
    note: "Ambiguous title; source text must be checked before acceptance."
    evidence:
      - source_type: "web"
        citation: "https://learnsanskrit.org/panini/shivasutras/"
        label: "Learn Sanskrit Online, The Shiva Sutras - Panini"
        retrieved_at: "2026-05-13"
""",
            encoding="utf-8",
        )

        def reviewer(_overlay):
            return ReaderMetadataOverlayDecision(
                recommendation="accept",
                confidence="high",
                rationale="Local source and web evidence identify the grammatical Śivasūtra.",
                flags=("source_checked",),
                reviewer="llm",
                model="openai:test",
            )

        reviews = review_metadata_overlay_candidates(
            root,
            reviewer=reviewer,
            apply=True,
            approve=lambda _review: True,
            retrieved_at="2026-05-13",
        )
        overlays = load_metadata_overlays(root)

    assert len(reviews) == 1
    assert reviews[0].approved is True
    assert reviews[0].applied is True
    assert overlays[0].status == "accepted"
    assert overlays[0].confidence == "high"
    assert "LLM review accepted" in overlays[0].note
    assert overlays[0].evidence[-1].source_type == "llm_review"
    assert overlays[0].evidence[-1].citation == "openai:test"
    assert "source_checked" in overlays[0].evidence[-1].label
