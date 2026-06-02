from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

import jsonschema
from click.testing import CliRunner

from langnet.cli import main
from langnet.tool_catalog import catalog_entries, catalog_payload, language_payload

LANGUAGE_SCHEMA_PATH = Path("docs/schemas/languages.v1.schema.json")
TOOL_SCHEMA_PATH = Path("docs/schemas/tools.v1.schema.json")


def _assert_matches_schema(payload: object, schema_path: Path) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(payload)


def test_catalog_lists_sanskrit_encounter_filters() -> None:
    filters = {entry.tool_filter for entry in catalog_entries("san")}

    assert {"heritage", "cdsl", "dico"} <= filters


def test_catalog_lists_greek_bailly_filter() -> None:
    filters = {entry.tool_filter for entry in catalog_entries("grc")}

    assert "bailly" in filters


def test_catalog_lists_greek_strongs_greek_filter() -> None:
    filters = {entry.tool_filter for entry in catalog_entries("grc")}

    assert "strongs_greek" in filters


def test_catalog_lists_latin_lewis_1890_filter() -> None:
    filters = {entry.tool_filter for entry in catalog_entries("lat")}

    assert "lewis_1890" in filters


def test_tools_json_output_lists_translation_capable_sources() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["tools", "san", "--output", "json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    _assert_matches_schema(payload, TOOL_SCHEMA_PATH)
    dico = next(tool for tool in payload["tools"] if tool["tool_filter"] == "dico")
    cdsl = next(tool for tool in payload["tools"] if tool["tool_filter"] == "cdsl")
    assert payload["schema_version"] == "langnet.tools.v1"
    assert payload["languages"] == [{"code": "san", "label": "Sanskrit", "tool_filter": "all"}]
    assert cdsl["dictionaries"] == ["mw", "ap90"]
    assert dico["accepted_filter"] == "dico"
    assert dico["translation_capable"] is True
    assert "claim.dico.entries" in dico["plan_tools"]


def test_tools_json_output_lists_greek_bailly() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["tools", "grc", "--output", "json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    _assert_matches_schema(payload, TOOL_SCHEMA_PATH)
    bailly = next(tool for tool in payload["tools"] if tool["tool_filter"] == "bailly")
    assert bailly["accepted_filter"] == "bailly"
    assert bailly["translation_capable"] is True
    assert "claim.bailly.entries" in bailly["plan_tools"]


def test_tools_json_output_lists_greek_strongs_greek() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["tools", "grc", "--output", "json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    _assert_matches_schema(payload, TOOL_SCHEMA_PATH)
    strongs = next(tool for tool in payload["tools"] if tool["tool_filter"] == "strongs_greek")
    assert strongs["accepted_filter"] == "strongs_greek"
    assert strongs["dictionary_genre"] == "religious"
    assert strongs["translation_capable"] is False
    assert "claim.strongs_greek.entries" in strongs["plan_tools"]


def test_tools_json_output_lists_latin_lewis_1890() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["tools", "lat", "--output", "json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    _assert_matches_schema(payload, TOOL_SCHEMA_PATH)
    lewis = next(tool for tool in payload["tools"] if tool["tool_filter"] == "lewis_1890")
    assert lewis["accepted_filter"] == "lewis_1890"
    assert lewis["translation_capable"] is False
    assert "claim.lewis_1890.entries" in lewis["plan_tools"]


def test_tools_json_output_can_list_all_languages() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["tools", "--output", "json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    _assert_matches_schema(payload, TOOL_SCHEMA_PATH)
    assert {language["code"] for language in payload["languages"]} == {"lat", "grc", "san"}
    assert {tool["tool_filter"] for tool in payload["tools"]} >= {
        "bailly",
        "dico",
        "gaffiot",
        "lewis_1890",
        "strongs_greek",
        "cdsl",
    }


def test_catalog_payload_includes_all_pseudo_filter() -> None:
    payload = catalog_payload("lat")

    _assert_matches_schema(payload, TOOL_SCHEMA_PATH)
    assert payload["pseudo_filters"] == [
        {
            "tool_filter": "all",
            "label": "All default tools for the language",
            "languages": ["lat"],
        }
    ]


def test_language_payload_lists_codes_and_aliases() -> None:
    payload = language_payload()

    _assert_matches_schema(payload, LANGUAGE_SCHEMA_PATH)
    assert payload["schema_version"] == "langnet.languages.v1"
    language_rows = cast(Sequence[Mapping[str, object]], payload["languages"])
    languages = {language["code"]: language for language in language_rows}
    assert set(languages) == {"lat", "grc", "san"}
    san_aliases = cast(Sequence[str], languages["san"]["aliases"])
    assert "skt" in san_aliases
    assert languages["san"]["tools_command"] == ["tools", "san", "--output", "json"]


def test_langs_json_output_can_filter_language() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["langs", "skt", "--output", "json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    _assert_matches_schema(payload, LANGUAGE_SCHEMA_PATH)
    assert payload["languages"] == [
        {
            "code": "san",
            "label": "Sanskrit",
            "aliases": ["san", "sanskrit", "skt"],
            "default_tool_filter": "all",
            "tools_command": ["tools", "san", "--output", "json"],
            "encounter_command": ["encounter", "san", "<text>", "all", "--output", "json"],
        }
    ]
