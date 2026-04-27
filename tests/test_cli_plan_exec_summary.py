from __future__ import annotations

from types import SimpleNamespace

from query_spec import LanguageHint, NormalizedQuery, ToolCallSpec, ToolPlan, ToolStage

from langnet.cli import _plan_exec_summary_payload
from langnet.execution.effects import ClaimEffect
from langnet.execution.executor import SkippedCall


def _plan() -> ToolPlan:
    return ToolPlan(
        plan_id="plan-summary",
        plan_hash="hash-summary",
        query=NormalizedQuery(
            original="lupus",
            language=LanguageHint.LANGUAGE_HINT_LAT,
            candidates=[],
            normalizations=[],
        ),
        tool_calls=[
            ToolCallSpec(
                tool="fetch.example",
                call_id="fetch-1",
                endpoint="http://example",
                stage=ToolStage.TOOL_STAGE_FETCH,
            ),
            ToolCallSpec(
                tool="extract.example",
                call_id="extract-1",
                endpoint="internal://extract",
                stage=ToolStage.TOOL_STAGE_EXTRACT,
            ),
            ToolCallSpec(
                tool="derive.example",
                call_id="derive-1",
                endpoint="internal://derive",
                stage=ToolStage.TOOL_STAGE_DERIVE,
            ),
            ToolCallSpec(
                tool="claim.example",
                call_id="claim-1",
                endpoint="internal://claim",
                stage=ToolStage.TOOL_STAGE_CLAIM,
            ),
        ],
    )


def test_plan_exec_summary_payload_reports_cache_stages_skips_and_versions() -> None:
    claim = ClaimEffect(
        claim_id="clm-1",
        tool="claim.example",
        call_id="claim-1",
        source_call_id="derive-1",
        derivation_id="drv-1",
        subject="lex:lupus",
        predicate="has_sense",
        value={},
        provenance_chain=[],
        handler_version="claim-v1",
    )
    result = SimpleNamespace(
        executed=SimpleNamespace(responses=["raw-1"], execution_time_ms=12),
        raw_effects=[SimpleNamespace(tool="fetch.example")],
        extractions=[SimpleNamespace(tool="extract.example", handler_version="extract-v1")],
        derivations=[],
        claims=[claim],
        skipped_calls=[
            SkippedCall(
                call_id="derive-1",
                tool="derive.example",
                stage="derive",
                reason="missing_source_derive",
                source_call_id="extract-1",
            )
        ],
        from_cache=False,
    )

    payload = _plan_exec_summary_payload(_plan(), result, cache_enabled=True)

    assert payload["cache"] == {
        "enabled": True,
        "status": "miss",
        "response_refs": 1,
    }
    assert payload["stages"] == {
        "fetch": {"planned": 1, "produced": 1},
        "extract": {"planned": 1, "produced": 1},
        "derive": {"planned": 1, "produced": 0},
        "claim": {"planned": 1, "produced": 1},
    }
    assert payload["skipped_calls"] == [
        {
            "call_id": "derive-1",
            "tool": "derive.example",
            "stage": "derive",
            "reason": "missing_source_derive",
            "source_call_id": "extract-1",
        }
    ]
    assert payload["handler_versions"] == [
        {"tool": "claim.example", "handler_version": "claim-v1"},
        {"tool": "extract.example", "handler_version": "extract-v1"},
    ]
    assert payload["claims"] == [
        {
            "claim_id": "clm-1",
            "tool": "claim.example",
            "subject": "lex:lupus",
            "predicate": "has_sense",
            "handler_version": "claim-v1",
        }
    ]
