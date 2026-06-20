from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import cast
from unittest.mock import patch

from click.testing import CliRunner

from langnet.cli import (
    _reader_word_context_lexical_evidence_from_reduction,
    _reader_word_context_lexical_evidence_provider,
    _reader_word_context_morphology_provider,
    main,
)
from langnet.reduction.models import ReductionResult, SenseBucket, WitnessSenseUnit

Provider = Callable[..., dict[str, object]]


def test_reader_word_context_lexical_evidence_formats_reduction_buckets() -> None:
    witness = WitnessSenseUnit(
        wsu_id="wsu:lat:arma:0",
        lexeme_anchor="lex:arma",
        sense_anchor="sense:lex:arma#0",
        gloss="arms; weapons",
        normalized_gloss="arms; weapons",
        source_tool="lewis_1890",
        claim_id="claim:arma:0",
        source_triple_subject="lex:arma",
        evidence={
            "parsed_glosses": ["arms", "weapons"],
            "source_ref": "lewis_1890:arma",
        },
    )
    reduction = ReductionResult(
        query="arma",
        language="lat",
        lexeme_anchors=["lex:arma"],
        buckets=[
            SenseBucket(
                bucket_id="bucket:lat:arma:0",
                normalized_gloss="arms; weapons",
                display_gloss="arms; weapons",
                witnesses=[witness],
                confidence_label="single-witness",
            )
        ],
    )

    payload = _reader_word_context_lexical_evidence_from_reduction(reduction)

    assert payload == {
        "status": "available",
        "items": [
            {
                "lemma": "arma",
                "source_tool": "lewis_1890",
                "source_label": "lewis_1890",
                "gloss": "arms, weapons",
                "evidence_gloss": "arms; weapons",
                "source_ref": "lewis_1890:arma",
                "bucket_id": "bucket:lat:arma:0",
                "witness_id": "wsu:lat:arma:0",
                "confidence_label": "single-witness",
            }
        ],
        "note": "Encounter-derived lexical evidence.",
    }


def test_reader_word_context_lexical_evidence_reports_no_hits() -> None:
    reduction = ReductionResult(query="nihil", language="lat")

    payload = _reader_word_context_lexical_evidence_from_reduction(reduction)

    assert payload == {
        "status": "no_hits",
        "items": [],
        "note": "No source-backed lexical evidence found.",
    }


def test_reader_word_context_lexical_evidence_provider_uses_encounter_reduction() -> None:
    witness = WitnessSenseUnit(
        wsu_id="wsu:lat:amor:0",
        lexeme_anchor="lex:amor",
        sense_anchor="sense:lex:amor#0",
        gloss="love",
        normalized_gloss="love",
        source_tool="lewis_1890",
        claim_id="claim:amor:0",
        source_triple_subject="lex:amor",
        evidence={"parsed_glosses": ["love"], "source_ref": "lewis_1890:amor"},
    )
    reduction = ReductionResult(
        query="amor",
        language="lat",
        lexeme_anchors=["lex:amor"],
        buckets=[
            SenseBucket(
                bucket_id="bucket:lat:amor:0",
                normalized_gloss="love",
                display_gloss="love",
                witnesses=[witness],
            )
        ],
    )
    calls: list[dict[str, object]] = []

    def execute_lookup_plan(**kwargs: object) -> object:
        calls.append(kwargs)
        return object()

    with (
        patch("langnet.cli._execute_lookup_plan", side_effect=execute_lookup_plan),
        patch("langnet.cli._claims_as_mappings", return_value=[]),
        patch("langnet.cli.reduce_claims", return_value=reduction),
    ):
        payload = _reader_word_context_lexical_evidence_provider()(
            query="amor",
            language="lat",
            candidates=["amor", "amoris"],
        )

    assert calls[0]["text"] == "amor"
    assert calls[0]["language"] == "lat"
    assert calls[0]["cache_policy"] == "read-only"
    assert calls[0]["include_cltk"] is False
    assert payload["status"] == "available"
    items = cast(list[dict[str, object]], payload["items"])
    assert items[0]["lemma"] == "amor"
    assert items[0]["source_ref"] == "lewis_1890:amor"


def test_reader_word_context_morphology_provider_uses_encounter_rows() -> None:
    calls: list[dict[str, object]] = []
    claims = [
        {
            "tool": "whitaker",
            "value": {
                "triples": [
                    {
                        "subject": "form:arma",
                        "predicate": "has_morphology",
                        "object": {
                            "form": "arma",
                            "lemma": "arma",
                            "analysis": "neut. nom./acc. pl.",
                        },
                    }
                ]
            },
        }
    ]

    def execute_lookup_plan(**kwargs: object) -> object:
        calls.append(kwargs)
        return object()

    with (
        patch("langnet.cli._execute_lookup_plan", side_effect=execute_lookup_plan),
        patch("langnet.cli._claims_as_mappings", return_value=claims),
    ):
        payload = _reader_word_context_morphology_provider()(
            query="arma",
            language="lat",
            candidates=["arma"],
        )

    assert calls[0]["text"] == "arma"
    assert calls[0]["cache_policy"] == "read-only"
    assert payload == {
        "status": "available",
        "items": [
            {
                "source_tool": "whitaker",
                "form": "arma",
                "lemma": "arma",
                "analysis": "neut. nom./acc. pl.",
            }
        ],
        "note": "Encounter-derived morphology evidence.",
    }


def test_reader_word_context_cli_passes_lexical_evidence_provider() -> None:
    captured: dict[str, object] = {}

    def lexical_provider(**_kwargs: object) -> dict[str, object]:
        return {"status": "available", "items": [{"lemma": "arma"}]}

    def morphology_provider(**_kwargs: object) -> dict[str, object]:
        return {"status": "available", "items": [{"lemma": "arma", "analysis": "noun"}]}

    class FakeReaderService:
        def word_context_payload(self, **kwargs: object) -> dict[str, object]:
            captured.update(kwargs)
            lexical_provider = cast(Provider, kwargs["lexical_evidence_provider"])
            morphology_provider = cast(Provider, kwargs["morphology_provider"])
            assert callable(lexical_provider)
            assert callable(morphology_provider)
            return {
                "query": kwargs["query"],
                "language": kwargs["language"],
                "lexical_evidence": lexical_provider(
                    query="arma",
                    language="lat",
                    candidates=["arma"],
                ),
                "morphology": morphology_provider(
                    query="arma",
                    language="lat",
                    candidates=["arma"],
                ),
            }

    with (
        patch("langnet.cli._reader_service_from_context", return_value=FakeReaderService()),
        patch(
            "langnet.cli._reader_word_context_lexical_evidence_provider",
            return_value=lexical_provider,
        ),
        patch(
            "langnet.cli._reader_word_context_morphology_provider",
            return_value=morphology_provider,
        ),
    ):
        result = CliRunner().invoke(
            main,
            [
                "reader",
                "word-context",
                "arma",
                "--language",
                "lat",
                "--index",
                str(Path("missing.lance")),
                "--output",
                "json",
            ],
        )

    assert result.exit_code == 0, result.output
    assert captured["query"] == "arma"
    assert captured["language"] == "lat"
    assert captured["lexical_evidence_provider"] is lexical_provider
    assert captured["morphology_provider"] is morphology_provider
    output_payload = json.loads(result.output)
    assert output_payload["lexical_evidence"]["items"] == [{"lemma": "arma"}]
    assert output_payload["morphology"]["items"] == [{"lemma": "arma", "analysis": "noun"}]
