from __future__ import annotations

from pathlib import Path

DOCS = [
    Path("docs/GRAMMAR_LEARNING_OVERLAY.md"),
    Path("docs/technical/grammar-concept-registry.md"),
    Path("docs/technical/grammar-source-anchors.md"),
    Path("docs/plans/todo/pedagogy/foster-grammar-learning-overlay.md"),
]


def test_grammar_learning_overlay_docs_exist_and_name_core_goal() -> None:
    for path in DOCS:
        text = path.read_text(encoding="utf-8")
        assert "Foster" in text
        assert "traditional" in text.lower()
        assert "source-backed" in text


def test_grammar_learning_overlay_plan_has_actionable_phases() -> None:
    text = Path("docs/plans/todo/pedagogy/foster-grammar-learning-overlay.md").read_text(
        encoding="utf-8"
    )

    for phase in (
        "Phase 1: Concept Registry",
        "Phase 2: Morphology-To-Concept Mapper",
        "Phase 3: CLI Learning Surface",
        "Phase 4: Web Learn This Form Panel",
        "Phase 5: Advanced Grammar Processes",
        "Phase 6: Audit And Validation",
    ):
        assert phase in text

    assert "just test test_grammar_concepts" in text
    assert "cd webapp && just verify" in text


def test_grammar_learning_overlay_captures_reader_annotation_goals() -> None:
    text = DOCS[0].read_text(encoding="utf-8")

    assert "Annotation-Inspired Reading Goals" in text
    assert "subject, object, verb" in text
    assert "distant connections" in text
    assert "clause boundary" in text
    assert "learn evidence-report" in text
    assert "sound_change.guna" in text


def test_grammar_registry_documents_local_grammar_source_anchors() -> None:
    text = Path("docs/technical/grammar-concept-registry.md").read_text(encoding="utf-8")

    assert "grammar-source-anchors.md" in text
    assert "reader_segment" in text
    assert "evidence_level" in text
    assert "sound_change.guna" in text


def test_grammar_source_anchor_doc_names_canonical_sources() -> None:
    text = Path("docs/technical/grammar-source-anchors.md").read_text(encoding="utf-8")

    for expected in (
        "langnet:reader:sanskrit_dcs:dcs_413",
        "langnet:reader:phi:lat0684.001",
        "langnet:reader:tlg:tlg0063.001",
        "urn:cts:greekLit:tlg0082.tlg004",
        "urn:ctsv2:san:kasikavrtti-vrddhisabdah-samjnatvena-vidhiyate",
        "https://catalog.perseus.org/catalog/urn:cts:latinLit:phi0684.phi001.opp-eng2",
        "https://www.britannica.com/topic/Ashtadhyayi",
        "http://www.sanskrit-linguistics.org/dcs/",
    ):
        assert expected in text

    assert "reader_work" in text
    assert "reader_segment" in text
    assert "sound_change.guna" in text
