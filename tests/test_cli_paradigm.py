from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import jsonschema
from click.testing import CliRunner

from langnet.cli import main
from langnet.paradigm.models import ParadigmBlock, ParadigmForm, ParadigmPayload, ParadigmSlot

SCHEMA_PATH = Path("docs/schemas/paradigm.v1.schema.json")


def _assert_matches_schema(payload: object) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(payload)


class FakeParadigmService:
    def __init__(self, *args: object, **kwargs: object) -> None:
        self.args = args
        self.kwargs = kwargs

    def fetch(self, request: object) -> ParadigmPayload:
        return ParadigmPayload(
            language="san",
            lemma="putra",
            kind="declension",
            source="heritage:sktdeclin",
            source_request={"request": repr(request)},
            paradigms=[
                ParadigmBlock(
                    label="putra declension",
                    dimensions=["case", "number"],
                    slots=[
                        ParadigmSlot(
                            features={"case": "genitive", "number": "plural"},
                            forms=[
                                ParadigmForm(
                                    text="putrāṇām",
                                    normalized="putrāṇām",
                                    source_key="putrāṇām",
                                )
                            ],
                            source_label="Genitive / plural",
                        )
                    ],
                )
            ],
        )


def test_paradigm_cli_returns_schema_valid_json() -> None:
    with patch("langnet.cli.ParadigmService", FakeParadigmService):
        result = CliRunner().invoke(
            main,
            [
                "paradigm",
                "san",
                "putra",
                "--kind",
                "declension",
                "--gender",
                "Mas",
                "--output",
                "json",
            ],
        )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    _assert_matches_schema(payload)
    assert payload["paradigms"][0]["slots"][0]["forms"][0]["text"] == "putrāṇām"


def test_paradigm_cli_requires_gender_for_sanskrit_declension() -> None:
    result = CliRunner().invoke(
        main,
        ["paradigm", "san", "putra", "--kind", "declension", "--output", "json"],
    )

    assert result.exit_code != 0
    assert "requires --gender" in result.output
