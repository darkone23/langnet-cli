from __future__ import annotations

from query_spec import (
    CanonicalCandidate,
    ExecutedPlan,
    LanguageHint,
    NormalizationStep,
    NormalizedQuery,
    PlanDependency,
    ToolCallSpec,
    ToolPlan,
    ToolResponseRef,
)


def test_tool_plan_structures_are_constructible() -> None:
    query = NormalizedQuery(
        original="shiva",
        language=LanguageHint.SAN,
        candidates=[
            CanonicalCandidate(lemma="śiva", encodings={}, sources=["local"]),
        ],
        normalizations=[
            NormalizationStep(
                operation="transliterate",
                input="shiva",
                output="śiva",
                tool="velthuis_to_iast",
            ),
            NormalizationStep(
                operation="normalize_case",
                input="śiva",
                output="śiva",
                tool="lowercase",
            ),
        ],
    )

    cdsl_call = ToolCallSpec(
        tool="cdsl",
        call_id="call-cdsl",
        endpoint="http://localhost:48080/sktreader",
        params={"q": "Siva"},
        expected_response_type="xml",
        priority=1,
        optional=False,
    )
    heritage_call = ToolCallSpec(
        tool="heritage",
        call_id="call-heritage",
        endpoint="http://localhost:8080/morph",
        params={"q": "ziva"},
        expected_response_type="json",
        priority=1,
        optional=False,
    )

    plan = ToolPlan(
        plan_id="plan-001",
        plan_hash="hash-001",
        query=query,
        tool_calls=[cdsl_call, heritage_call],
        dependencies=[
            PlanDependency(
                from_call_id="call-cdsl",
                to_call_id="call-heritage",
                rationale="Ensure lexicon lookup completes before morphology hydrating",
            )
        ],
    )

    assert plan.query is not None, "Query should not be None"
    assert plan.query.original == "shiva"
    assert plan.tool_calls, "Tool calls should not be empty"
    assert plan.tool_calls[0].params is not None, "Tool call params should not be None"
    assert plan.tool_calls[0].params.get("q") == "Siva"
    assert plan.dependencies[0].from_call_id == "call-cdsl"

    executed_plan = ExecutedPlan(
        plan_id=plan.plan_id,
        plan_hash=plan.plan_hash,
        responses=[
            ToolResponseRef(
                tool="cdsl",
                call_id="call-cdsl",
                response_id="resp-001",
                cached=False,
            )
        ],
        execution_time_ms=12,
        from_cache=False,
    )

    assert executed_plan.responses[0].tool == "cdsl"
    assert not executed_plan.from_cache
