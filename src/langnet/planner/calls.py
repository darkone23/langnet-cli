from __future__ import annotations

from dataclasses import dataclass

from query_spec import ToolCallSpec, ToolStage


@dataclass(slots=True)
class CallOptions:
    expected: str
    priority: int
    optional: bool
    stage: ToolStage.ValueType


def opts(
    *, expected: str, priority: int, optional: bool, stage: ToolStage.ValueType
) -> CallOptions:
    return CallOptions(expected=expected, priority=priority, optional=optional, stage=stage)


def make_call_params(*, params: dict[str, str], stage: ToolStage.ValueType) -> dict[str, str]:
    payload = dict(params)
    payload["stage"] = ToolStage.Name(stage)
    payload.setdefault("source_call_id", payload.get("source_call_id", ""))
    return payload


def make_call(
    tool: str,
    call_id: str,
    endpoint: str,
    params: dict[str, str],
    *,
    opts: CallOptions,
) -> ToolCallSpec:
    payload = make_call_params(params=params, stage=opts.stage)
    return ToolCallSpec(
        tool=tool,
        call_id=call_id,
        endpoint=endpoint,
        params=payload,
        expected_response_type=opts.expected,
        priority=opts.priority,
        optional=opts.optional,
        stage=opts.stage,
        source_call_id=payload.get("source_call_id", ""),
    )
