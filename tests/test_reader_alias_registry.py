from __future__ import annotations

import tempfile
from pathlib import Path

from langnet.reader.alias_registry import AliasConflict, load_aliases, validate_aliases


def test_loads_composed_alias_files() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir) / "aliases"
        (root / "greek").mkdir(parents=True)
        (root / "greek" / "homer.yaml").write_text(
            """
aliases:
  - alias: "Od."
    language: "grc"
    kind: "work_abbreviation"
    target: "urn:cts:greekLit:tlg0012.tlg002"
    display: "Homer, Odyssey"
    sources: ["lsj", "manual"]
""",
            encoding="utf-8",
        )

        aliases = load_aliases(root)

        assert len(aliases) == 1
        assert aliases[0].alias == "Od."
        assert aliases[0].language == "grc"
        assert aliases[0].sources == ("lsj", "manual")
        assert aliases[0].source_file.endswith("greek/homer.yaml")


def test_validate_aliases_reports_conflicting_targets() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir) / "aliases"
        root.mkdir()
        (root / "a.yaml").write_text(
            """
aliases:
  - alias: "Cat."
    language: "grc"
    kind: "work_abbreviation"
    target: "urn:cts:greekLit:tlg0086.tlg006"
    display: "Aristotle, Categories"
    sources: ["manual"]
  - alias: "Cat."
    language: "grc"
    kind: "work_abbreviation"
    target: "urn:cts:latinLit:phi0474.phi001"
    display: "Catullus"
    sources: ["manual"]
""",
            encoding="utf-8",
        )

        conflicts = validate_aliases(load_aliases(root))

        assert conflicts == [
            AliasConflict(
                alias="Cat.",
                language="grc",
                targets=(
                    "urn:cts:greekLit:tlg0086.tlg006",
                    "urn:cts:latinLit:phi0474.phi001",
                ),
            )
        ]


def test_alias_loader_rejects_unsupported_yaml_shape() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir) / "aliases"
        root.mkdir()
        alias_file = root / "bad.yaml"
        alias_file.write_text(
            """
aliases:
  - alias: "Od."
    language:
      code: "grc"
""",
            encoding="utf-8",
        )

        try:
            load_aliases(root)
        except ValueError as exc:
            message = str(exc)
        else:
            message = ""

        assert "bad.yaml:4" in message
        assert "unsupported alias YAML line" in message


def test_curated_seed_aliases_load_without_conflicts() -> None:
    aliases = load_aliases(Path("data/curated/reader_aliases"))
    conflicts = validate_aliases(aliases)

    assert conflicts == []
    assert any(alias.alias == "Od." for alias in aliases)
    assert any(alias.alias == "Śivasūtra" for alias in aliases)
