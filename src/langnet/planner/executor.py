from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from query_spec import ExecutedPlan, ToolCallSpec, ToolPlan, ToolResponseRef

from langnet.clients.base import RawResponseEffect, ToolClient
from langnet.planner.core import stable_plan_hash


class ResponseStore(Protocol):
    def store(self, effect: RawResponseEffect) -> ToolResponseRef: ...


@dataclass
class PlanExecutionResult:
    plan: ToolPlan  # type: ignore
    executed: ExecutedPlan  # type: ignore
    effects: list[RawResponseEffect]  # type: ignore


def execute_plan(
    plan: ToolPlan,  # type: ignore
    clients: Mapping[str, ToolClient],  # type: ignore
    response_handler: ResponseStore | None = None,
) -> PlanExecutionResult:  # type: ignore
    """
    Execute a ToolPlan using dumb tool clients, respecting dependencies when provided.
    """
    plan_hash = plan.plan_hash or stable_plan_hash(plan)
    plan.plan_hash = plan_hash

    start = time.time()
    pending: dict[str, ToolCallSpec] = {call.call_id: call for call in plan.tool_calls}
    deps: dict[str, set[str]] = {call.call_id: set() for call in plan.tool_calls}
    for dep in plan.dependencies:
        deps.setdefault(dep.to_call_id, set()).add(dep.from_call_id)

    executed_effects: list[RawResponseEffect] = []
    completed: set[str] = set()

    while pending:
        progressed = False
        for call_id, call in list(pending.items()):
            if any(d not in completed for d in deps.get(call_id, set())):
                continue

            client = clients.get(call.tool)
            if client is None:
                raise ValueError(f"No client registered for tool '{call.tool}'")

            effect = client.execute(
                call_id=call.call_id, endpoint=call.endpoint, params=call.params
            )
            executed_effects.append(effect)
            completed.add(call_id)
            pending.pop(call_id)
            progressed = True
        if not progressed:
            raise RuntimeError("Dependency cycle detected in ToolPlan")

    duration_ms = int((time.time() - start) * 1000)
    executed_plan = ExecutedPlan(
        plan_id=plan.plan_id,
        plan_hash=plan_hash,
        execution_time_ms=duration_ms,
        from_cache=False,
    )
    for eff in executed_effects:
        if response_handler and hasattr(response_handler, "store"):
            ref = response_handler.store(eff)  # type: ignore[attr-defined]
            executed_plan.responses.append(ref)
        else:
            executed_plan.responses.append(
                ToolResponseRef(
                    tool=eff.tool, call_id=eff.call_id, response_id=eff.response_id, cached=False
                )
            )

    return PlanExecutionResult(plan=plan, executed=executed_plan, effects=executed_effects)
