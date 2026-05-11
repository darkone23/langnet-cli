from __future__ import annotations

import json
from pathlib import Path

import jsonschema
from click.testing import CliRunner

from langnet.cli import main

SCHEMA_PATH = Path("docs/schemas/paradigm_resolution.v1.schema.json")
PUELLAE_ANALYSIS_COUNT = 3


def _assert_matches_schema(payload: object) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(payload)


def test_paradigm_resolve_cli_reports_latin_ambiguity_from_record_json() -> None:
    record = json.dumps(
        {
            "lemma": "puella",
            "part_of_speech": "noun",
            "genitive_singular": "puellae",
            "gender": "feminine",
            "source": "whitakers",
            "analyses": [
                {"case": "genitive", "number": "singular"},
                {"case": "dative", "number": "singular"},
                {"case": "nominative", "number": "plural"},
            ],
        },
        ensure_ascii=False,
    )

    result = CliRunner().invoke(
        main,
        [
            "paradigm-resolve",
            "lat",
            "puellae",
            "--record-json",
            record,
            "--output",
            "json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    _assert_matches_schema(payload)
    candidate = payload["candidates"][0]
    assert candidate["lemma"] == "puella"
    assert len(candidate["native_analyses"]) == PUELLAE_ANALYSIS_COUNT
    assert candidate["paradigm_request"]["source"] == "diogenes:inflect"


def test_paradigm_resolve_cli_reports_missing_sanskrit_gender_without_fetching() -> None:
    record = json.dumps(
        {
            "lemma": "agni",
            "part_of_speech": "noun",
            "source": "cdsl:mw",
        },
        ensure_ascii=False,
    )

    result = CliRunner().invoke(
        main,
        [
            "paradigm-resolve",
            "san",
            "agni",
            "--record-json",
            record,
            "--output",
            "json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    _assert_matches_schema(payload)
    assert payload["candidates"][0]["paradigm_request"] is None
    assert payload["candidates"][0]["unresolved_reason"] == "missing_gender_or_declension"


def test_paradigm_resolve_cli_maps_greek_learner_key_without_record_json() -> None:
    result = CliRunner().invoke(
        main,
        [
            "paradigm-resolve",
            "grc",
            "sophos",
            "--output",
            "json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    _assert_matches_schema(payload)
    candidate = next(
        candidate for candidate in payload["candidates"] if candidate["paradigm_request"]
    )
    assert candidate["paradigm_request"] == {
        "source": "diogenes:inflect",
        "language": "grc",
        "lemma": "sofo/s",
        "kind": "declension",
        "options": {},
    }


def test_paradigm_resolve_cli_maps_more_greek_motd_learner_keys() -> None:
    result = CliRunner().invoke(
        main,
        [
            "paradigm-resolve",
            "grc",
            "selene",
            "--output",
            "json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    candidate = payload["candidates"][0]
    assert candidate["paradigm_request"]["lemma"] == "selh/nh"
