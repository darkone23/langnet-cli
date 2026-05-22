from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from click.testing import CliRunner

from langnet.cli import main
from langnet.foster_ossa.essentials import (
    default_foster_essentials,
    foster_essentials_payload,
    get_foster_essential,
    render_foster_essentials_markdown,
    validate_foster_essentials,
    write_foster_essentials_artifacts,
)

ESSENTIAL_TOTAL = 7
CODIFIED_TOTAL = 6


def test_default_foster_essentials_include_codified_bridges_and_aggregate_candidate() -> None:
    essentials = default_foster_essentials()
    by_id = {essential.id: essential for essential in essentials}

    assert by_id["of-possession"].concept_ids == ("case.genitive",)
    assert by_id["to-for-from"].concept_ids == ("case.dative",)
    assert by_id["object-form"].concept_ids == ("case.accusative",)
    assert by_id["function-of-address"].concept_ids == ("case.vocative",)
    assert by_id["location-function"].concept_ids == ("case.locative",)
    assert by_id["subject-form"].concept_ids == ("case.nominative",)
    assert by_id["by-with-from-in"].status == "aggregate_candidate"
    assert by_id["by-with-from-in"].concept_ids == (
        "case.ablative",
        "case.instrumental",
        "case.locative",
    )


def test_validate_foster_essentials_requires_sources_and_concept_or_candidate_status() -> None:
    validation = validate_foster_essentials(default_foster_essentials())

    assert validation["valid"] is True
    assert validation["issues"] == []
    assert validation["summary"]["total"] == ESSENTIAL_TOTAL
    assert validation["summary"]["status_counts"]["codified"] == CODIFIED_TOTAL
    assert validation["summary"]["status_counts"]["aggregate_candidate"] == 1


def test_foster_essentials_payload_is_json_serializable() -> None:
    payload = foster_essentials_payload()

    encoded = json.dumps(payload)

    decoded = json.loads(encoded)
    assert decoded["schema_version"] == "langnet.foster_ossa_essentials.v1"
    assert decoded["validation"]["valid"] is True
    assert decoded["essentials"][0]["id"]


def test_get_foster_essential_accepts_id_and_foster_term_alias() -> None:
    of_possession = get_foster_essential("of-possession")
    to_for_from = get_foster_essential("function to-for-from")

    assert of_possession is not None
    assert to_for_from is not None
    assert of_possession.id == "of-possession"
    assert to_for_from.id == "to-for-from"
    assert get_foster_essential("missing") is None


def test_render_foster_essentials_markdown_lists_status_and_refs() -> None:
    markdown = render_foster_essentials_markdown(default_foster_essentials())

    assert "# Foster Essentials Pack" in markdown
    assert "`of-possession`" in markdown
    assert "`case.genitive`" in markdown
    assert "`toc:1.6`" in markdown
    assert "by-with-from-in" in markdown
    assert "aggregate candidate" in markdown


def test_write_foster_essentials_artifacts_writes_json_and_markdown() -> None:
    with TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        json_path = base / "foster_essentials.json"
        markdown_path = base / "FOSTER_ESSENTIALS.md"

        written = write_foster_essentials_artifacts(
            json_output=json_path,
            markdown_output=markdown_path,
        )

        assert written == [json_path, markdown_path]
        assert json.loads(json_path.read_text(encoding="utf-8"))["validation"]["valid"] is True
        assert "# Foster Essentials Pack" in markdown_path.read_text(encoding="utf-8")


def test_foster_ossa_essentials_cli_list_show_validate_and_write() -> None:
    runner = CliRunner()
    list_result = runner.invoke(main, ["foster-ossa", "essentials", "list", "--output", "json"])

    assert list_result.exit_code == 0, list_result.output
    list_payload = json.loads(list_result.output)
    assert list_payload["essentials"][0]["id"]

    show_result = runner.invoke(
        main,
        ["foster-ossa", "essentials", "show", "function to-for-from", "--output", "json"],
    )
    assert show_result.exit_code == 0, show_result.output
    show_payload = json.loads(show_result.output)
    assert show_payload["essential"]["id"] == "to-for-from"

    validate_result = runner.invoke(
        main,
        ["foster-ossa", "essentials", "validate", "--output", "json"],
    )
    assert validate_result.exit_code == 0, validate_result.output
    assert json.loads(validate_result.output)["validation"]["valid"] is True

    with TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        write_result = runner.invoke(
            main,
            [
                "foster-ossa",
                "essentials",
                "write",
                "--json-output",
                str(base / "essentials.json"),
                "--markdown-output",
                str(base / "essentials.md"),
            ],
        )
        assert write_result.exit_code == 0, write_result.output
        assert "wrote: 2" in write_result.output
        assert (base / "essentials.json").exists()
        assert (base / "essentials.md").exists()
