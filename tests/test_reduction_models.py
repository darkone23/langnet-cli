from __future__ import annotations

from dataclasses import asdict

from langnet.reduction import ReductionResult, SenseBucket, WitnessSenseUnit


def test_reduction_models_construct_and_serialize() -> None:
    witness = WitnessSenseUnit(
        wsu_id="wsu:lupus-wolf",
        lexeme_anchor="lex:lupus#noun",
        sense_anchor="sense:lex:lupus#noun#whitaker-wolf",
        gloss="wolf",
        normalized_gloss="wolf",
        source_tool="whitaker",
        claim_id="claim-whitaker-lupus-001",
        source_triple_subject="lex:lupus#noun",
        evidence={"claim_id": "claim-whitaker-lupus-001", "raw_blob_ref": "raw_text"},
    )
    bucket = SenseBucket(
        bucket_id="bucket:wolf",
        normalized_gloss="wolf",
        display_gloss="wolf",
        witnesses=[witness],
        confidence_label="fixture",
    )
    result = ReductionResult(
        query="lupus",
        language="lat",
        lexeme_anchors=["lex:lupus#noun"],
        buckets=[bucket],
    )

    serialized = asdict(result)
    assert serialized["query"] == "lupus"
    assert serialized["buckets"][0]["witnesses"][0]["claim_id"] == "claim-whitaker-lupus-001"
    assert serialized["buckets"][0]["witnesses"][0]["evidence"]["raw_blob_ref"] == "raw_text"
