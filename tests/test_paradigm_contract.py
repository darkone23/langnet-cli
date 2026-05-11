from __future__ import annotations

import json
from pathlib import Path

import cattrs
import jsonschema

from langnet.paradigm.models import ParadigmBlock, ParadigmForm, ParadigmPayload, ParadigmSlot

SCHEMA_PATH = Path("docs/schemas/paradigm.v1.schema.json")


def _assert_matches_schema(payload: object) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(payload)


def test_paradigm_payload_schema_supports_source_backed_noun_table() -> None:
    payload = ParadigmPayload(
        language="san",
        lemma="putra",
        kind="declension",
        source="heritage:sktdeclin",
        source_request={
            "url": "http://localhost:48080/cgi-bin/skt/sktdeclin",
            "params": {"q": "putra", "g": "Mas"},
        },
        paradigms=[
            ParadigmBlock(
                label="putra masculine declension",
                dimensions=["case", "number"],
                slots=[
                    ParadigmSlot(
                        features={"case": "nominative", "number": "singular"},
                        forms=[
                            ParadigmForm(
                                text="putraḥ",
                                normalized="putraḥ",
                                source_key="putraḥ",
                            )
                        ],
                        source_label="Nominative / Singular",
                    ),
                    ParadigmSlot(
                        features={"case": "genitive", "number": "plural"},
                        forms=[
                            ParadigmForm(
                                text="putrāṇām",
                                normalized="putrāṇām",
                                source_key="putrāṇām",
                            )
                        ],
                        source_label="Genitive / Plural",
                    ),
                ],
            )
        ],
    )

    data = cattrs.unstructure(payload)

    _assert_matches_schema(data)
    assert data["schema_version"] == "langnet.paradigm.v1"
    assert data["paradigms"][0]["slots"][1]["forms"][0]["text"] == "putrāṇām"


def test_paradigm_schema_rejects_missing_source() -> None:
    payload = {
        "schema_version": "langnet.paradigm.v1",
        "language": "lat",
        "lemma": "amo",
        "kind": "conjugation",
        "source_request": {},
        "paradigms": [],
        "warnings": [],
    }
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)

    errors = list(validator.iter_errors(payload))

    assert errors
