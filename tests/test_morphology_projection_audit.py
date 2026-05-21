from __future__ import annotations

from pathlib import Path

AUDIT_DOC = Path("docs/technical/morphology-projection-audit.md")


def test_morphology_projection_audit_names_all_current_projectors() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for source in ("Heritage", "Whitaker", "Diogenes/Morpheus", "spaCy", "CLTK"):
        assert f"| {source} |" in text

    assert "not treated as a morphology source" in text.lower()
    assert "has_declension" in text
    assert "has_conjugation" in text


def test_morphology_projection_audit_records_validation_commands() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    assert "just test test_morphology_candidates" in text
    assert "just lint-all" in text
    assert "cd webapp && just verify" in text
