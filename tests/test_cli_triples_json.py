from __future__ import annotations

import json
from types import SimpleNamespace
from typing import cast
from unittest.mock import patch

from click.testing import CliRunner

from langnet.cli import main
from langnet.cli_triples import build_triples_dump_payload
from langnet.execution.effects import ClaimEffect, ProvenanceLink

TRIPLE_COUNT = 2
ONE_MATCH = 1


def _claim() -> ClaimEffect:
    triples = [
        {
            "subject": "lex:lupus#noun",
            "predicate": "has_sense",
            "object": "sense:lex:lupus#noun#1",
            "metadata": {
                "evidence": {
                    "source_tool": "whitaker",
                    "claim_id": "clm-1",
                    "response_id": "raw-1",
                }
            },
        },
        {
            "subject": "sense:lex:lupus#noun#1",
            "predicate": "gloss",
            "object": "wolf",
            "metadata": {"source_ref": "fixture"},
        },
    ]
    return ClaimEffect(
        claim_id="clm-1",
        tool="claim.whitakers.wordlist",
        call_id="call-1",
        source_call_id="derive-1",
        derivation_id="drv-1",
        subject="lex:lupus#noun",
        predicate="has_sense",
        value={"triples": triples},
        provenance_chain=[
            ProvenanceLink(
                stage="derive",
                tool="derive.whitakers.wordlist",
                reference_id="drv-1",
                metadata={"handler_version": "v1"},
            )
        ],
        handler_version="v1",
    )


def test_triples_dump_payload_separates_claims_and_triples() -> None:
    payload = build_triples_dump_payload(
        language="lat",
        text="lupus",
        normalized_candidates=["lupus"],
        tool_filter="whitakers",
        predicate_filter=None,
        subject_filter=None,
        max_triples=1,
        result=SimpleNamespace(claims=[_claim()]),
    )

    assert payload["query"] == {
        "language": "lat",
        "text": "lupus",
        "normalized_candidates": ["lupus"],
    }
    assert payload["tool_filter"] == "whitakers"
    assert payload["filters"] == {
        "predicate": None,
        "subject_prefix": None,
        "max_triples": 1,
    }

    claims = cast(list[dict[str, object]], payload["claims"])
    assert claims[0]["claim_id"] == "clm-1"
    assert claims[0]["tool"] == "claim.whitakers.wordlist"
    assert claims[0]["triple_count"] == TRIPLE_COUNT
    assert claims[0]["matching_triple_count"] == TRIPLE_COUNT
    assert claims[0]["emitted_triple_count"] == ONE_MATCH
    provenance = cast(list[dict[str, object]], claims[0]["provenance_chain"])
    assert provenance[0]["reference_id"] == "drv-1"

    triples = cast(list[dict[str, object]], payload["triples"])
    assert len(triples) == ONE_MATCH
    assert triples[0]["claim_id"] == "clm-1"
    assert triples[0]["claim_tool"] == "claim.whitakers.wordlist"
    assert triples[0]["predicate"] == "has_sense"


def test_triples_dump_payload_applies_predicate_and_subject_filters() -> None:
    payload = build_triples_dump_payload(
        language="lat",
        text="lupus",
        normalized_candidates=["lupus"],
        tool_filter="whitakers",
        predicate_filter="gloss",
        subject_filter="sense:",
        max_triples=10,
        result=SimpleNamespace(claims=[_claim()]),
    )

    claims = cast(list[dict[str, object]], payload["claims"])
    assert claims[0]["triple_count"] == TRIPLE_COUNT
    assert claims[0]["matching_triple_count"] == ONE_MATCH

    triples = cast(list[dict[str, object]], payload["triples"])
    assert len(triples) == ONE_MATCH
    assert triples[0]["subject"] == "sense:lex:lupus#noun#1"
    assert triples[0]["predicate"] == "gloss"


def test_triples_dump_json_cli_uses_structured_payload() -> None:
    class FakePlanner:
        def __init__(self, _config: object) -> None:
            pass

        def select_candidate(self, query: object) -> object:
            return getattr(query, "candidates")[0]

        def build(self, _query: object, _candidate: object) -> object:
            return SimpleNamespace(tool_calls=[], dependencies=[])

    with (
        patch("langnet.cli.ToolPlanner", FakePlanner),
        patch("langnet.cli.execute_plan_staged", return_value=SimpleNamespace(claims=[_claim()])),
    ):
        result = CliRunner().invoke(
            main,
            [
                "triples-dump",
                "lat",
                "lupus",
                "all",
                "--no-normalize",
                "--output",
                "json",
            ],
        )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["query"]["language"] == "lat"
    assert payload["query"]["text"] == "lupus"
    assert payload["query"]["normalized_candidates"] == ["lupus"]
    assert payload["claims"][0]["claim_id"] == "clm-1"
    assert payload["triples"][0]["claim_tool"] == "claim.whitakers.wordlist"
