from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, cast

from query_spec import ToolCallSpec, ToolStage

from langnet.execution.effects import ClaimEffect


def make_call(
    tool: str,
    call_id: str,
    stage: ToolStage,
    params: Mapping[str, str] | None = None,
    endpoint: str = "internal://test",
) -> ToolCallSpec:
    return ToolCallSpec(
        tool=tool,
        call_id=call_id,
        endpoint=endpoint,
        params=dict(params or {}),
        stage=stage,
    )


def claim_value_mapping(claim: ClaimEffect) -> Mapping[str, Any]:
    assert isinstance(claim.value, Mapping)
    return cast(Mapping[str, Any], claim.value)


def claim_triples(claim: ClaimEffect) -> list[dict[str, Any]]:
    value = claim_value_mapping(claim)
    triples = value.get("triples")
    assert isinstance(triples, Sequence)
    return [cast(dict[str, Any], triple) for triple in triples if isinstance(triple, Mapping)]


def find_triple(
    triples: Sequence[Mapping[str, Any]],
    subject: str | None = None,
    predicate: str | None = None,
    obj: object | None = None,
) -> Mapping[str, Any] | None:
    for triple in triples:
        if subject is not None and triple.get("subject") != subject:
            continue
        if predicate is not None and triple.get("predicate") != predicate:
            continue
        if obj is not None and triple.get("object") != obj:
            continue
        return triple
    return None


def assert_claim_contract(claim: ClaimEffect) -> None:
    assert claim.claim_id
    assert claim.tool
    assert claim.call_id
    assert claim.derivation_id
    assert claim.subject
    assert claim.predicate
    assert claim.provenance_chain

    value = claim.value
    if not isinstance(value, Mapping):
        return
    value_mapping = cast(Mapping[str, Any], value)

    triples = value_mapping.get("triples")
    if triples is None:
        return
    assert isinstance(triples, Sequence)

    for triple in triples:
        assert isinstance(triple, Mapping)
        assert triple.get("subject")
        assert triple.get("predicate")
        assert "object" in triple

        metadata = triple.get("metadata")
        if metadata is None:
            continue
        assert isinstance(metadata, Mapping)
        evidence = metadata.get("evidence")
        if evidence is None:
            continue
        assert isinstance(evidence, Mapping)
        assert evidence.get("source_tool")
        assert evidence.get("call_id") == claim.call_id
        assert evidence.get("derivation_id") == claim.derivation_id
        assert evidence.get("claim_id") == claim.claim_id
