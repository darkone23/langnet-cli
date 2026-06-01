from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from langnet.reduction import reduce_claims

EXPECTED_WOLF_WITNESSES = 2
EXPECTED_TRANSLATED_SOURCE_WITNESSES = 2


def _load_lupus_claims() -> list[Mapping[str, Any]]:
    fixture_path = Path(__file__).parent / "fixtures" / "lupus_claims_wsu.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    return [cast(Mapping[str, Any], claim) for claim in fixture["claims"]]


def test_reduce_claims_exact_buckets_from_fixture() -> None:
    result = reduce_claims(query="lupus", language="lat", claims=_load_lupus_claims())

    assert result.query == "lupus"
    assert result.language == "lat"
    assert {bucket.display_gloss for bucket in result.buckets} == {"wolf", "wild dog", "pike"}
    wolf = next(bucket for bucket in result.buckets if bucket.display_gloss == "wolf")
    assert wolf.confidence_label == "multi-witness"
    assert len(wolf.witnesses) == EXPECTED_WOLF_WITNESSES


def test_reduce_claims_merges_source_bucket_behind_translation() -> None:
    claims = [
        {
            "claim_id": "claim-gaffiot-edo",
            "tool": "claim.gaffiot.entries",
            "value": {
                "triples": [
                    {
                        "subject": "lex:edo",
                        "predicate": "has_sense",
                        "object": "sense:lex:edo#source",
                        "metadata": {
                            "evidence": {
                                "source_tool": "gaffiot",
                                "source_ref": "gaffiot:gaffiot_22738",
                                "source_lang": "fr",
                                "source_entry": {
                                    "dict": "gaffiot",
                                    "entry_id": "gaffiot_22738",
                                    "source_text": "manger; dîner",
                                },
                            }
                        },
                    },
                    {
                        "subject": "sense:lex:edo#source",
                        "predicate": "gloss",
                        "object": "manger; dîner",
                        "metadata": {
                            "evidence": {
                                "source_tool": "gaffiot",
                                "source_ref": "gaffiot:gaffiot_22738",
                                "source_lang": "fr",
                                "source_entry": {
                                    "dict": "gaffiot",
                                    "entry_id": "gaffiot_22738",
                                    "source_text": "manger; dîner",
                                },
                            }
                        },
                    },
                    {
                        "subject": "lex:edo",
                        "predicate": "has_sense",
                        "object": "sense:lex:edo#translation",
                        "metadata": {
                            "evidence": {
                                "source_tool": "translation",
                                "source_ref": "gaffiot:gaffiot_22738",
                                "source_lang": "en",
                                "translation_id": "tr:gaffiot:edo",
                                "derived_from_tool": "gaffiot",
                                "derived_from_sense": "sense:lex:edo#source",
                            }
                        },
                    },
                    {
                        "subject": "sense:lex:edo#translation",
                        "predicate": "gloss",
                        "object": "to eat; to dine",
                        "metadata": {
                            "evidence": {
                                "source_tool": "translation",
                                "source_ref": "gaffiot:gaffiot_22738",
                                "source_lang": "en",
                                "translation_id": "tr:gaffiot:edo",
                                "derived_from_tool": "gaffiot",
                                "derived_from_sense": "sense:lex:edo#source",
                            }
                        },
                    },
                ]
            },
        }
    ]

    result = reduce_claims(query="edo", language="lat", claims=claims)

    assert [bucket.display_gloss for bucket in result.buckets] == ["to eat; to dine"]
    assert len(result.buckets[0].witnesses) == EXPECTED_TRANSLATED_SOURCE_WITNESSES
    assert {witness.source_tool for witness in result.buckets[0].witnesses} == {
        "gaffiot",
        "translation",
    }
