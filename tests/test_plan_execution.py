from __future__ import annotations

from collections.abc import Mapping

import duckdb
from query_spec import (
    CanonicalCandidate,
    LanguageHint,
    NormalizedQuery,
    PlanDependency,
    ToolCallSpec,
    ToolPlan,
    ToolResponseRef,
)

from langnet.clients.base import RawResponseEffect
from langnet.planner.executor import execute_plan
from langnet.storage.effects_index import RawResponseIndex
from langnet.storage.plan_index import PlanIndex, PlanResponseIndex, apply_schema

EXPECTED_RESPONSE_COUNT = 2


class _FakeClient:
    def __init__(self, tool: str):
        self.tool = tool

    def execute(
        self, call_id: str, endpoint: str, params: Mapping[str, str] | None = None
    ) -> RawResponseEffect:
        params = params or {}
        body = f"{call_id}:{params.get('q', '')}".encode()
        return RawResponseEffect(
            response_id=f"{call_id}-resp",
            tool=self.tool,
            call_id=call_id,
            endpoint=endpoint,
            status_code=200,
            content_type="text/plain",
            headers={},
            body=body,
        )


def test_plan_index_and_execution_round_trip() -> None:
    conn = duckdb.connect(database=":memory:")
    apply_schema(conn)

    normal = NormalizedQuery(
        original="logos",
        language=LanguageHint.LANGUAGE_HINT_GRC,
        candidates=[CanonicalCandidate(lemma="logos", encodings={}, sources=["local"])],
        normalizations=[],
    )

    call_one = ToolCallSpec(
        tool="dummy", call_id="call-1", endpoint="http://example/one", params={"q": "1"}
    )
    call_two = ToolCallSpec(
        tool="dummy", call_id="call-2", endpoint="http://example/two", params={"q": "2"}
    )

    plan = ToolPlan(
        plan_id="plan-1",
        plan_hash="",
        query=normal,
        tool_calls=[call_one, call_two],
        dependencies=[PlanDependency(from_call_id="call-1", to_call_id="call-2")],
    )

    raw_index = RawResponseIndex(conn)
    result = execute_plan(plan, {"dummy": _FakeClient("dummy")}, response_handler=raw_index)
    assert [eff.call_id for eff in result.effects] == ["call-1", "call-2"]
    assert result.executed.responses and isinstance(result.executed.responses[0], ToolResponseRef)
    # Stored in raw_response_index
    stored = raw_index.get(result.executed.responses[0].response_id)
    assert stored is not None

    pindex = PlanIndex(conn)
    pindex.upsert(
        query_hash="hash-logos",
        query=normal.original,
        language=str(normal.language).lower(),
        plan=result.plan,
    )
    loaded_plan = pindex.get("hash-logos")
    assert loaded_plan is not None
    assert loaded_plan.plan_id == plan.plan_id

    rindex = PlanResponseIndex(conn)
    rindex.upsert(
        plan_hash=result.executed.plan_hash,
        plan_id=result.executed.plan_id,
        response_refs=result.executed.responses,
    )
    loaded_exec = rindex.get(result.executed.plan_hash)
    assert loaded_exec is not None
    assert loaded_exec.plan_id == result.executed.plan_id
    assert len(loaded_exec.responses) == EXPECTED_RESPONSE_COUNT
