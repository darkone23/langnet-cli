from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
import logging

from query_spec import ExecutedPlan, ToolCallSpec, ToolPlan, ToolResponseRef, ToolStage

from langnet.clients.base import RawResponseEffect, ToolClient
from langnet.execution.effects import ClaimEffect, DerivationEffect, ExtractionEffect
from langnet.planner.core import stable_plan_hash
from langnet.storage.claim_index import ClaimIndex
from langnet.storage.derivation_index import DerivationIndex
from langnet.storage.effects_index import RawResponseIndex
from langnet.storage.extraction_index import ExtractionIndex
from langnet.storage.plan_index import PlanResponseIndex
from langnet.execution import handlers_stub

ExtractHandler = Callable[[ToolCallSpec, RawResponseEffect], ExtractionEffect]
DeriveHandler = Callable[[ToolCallSpec, ExtractionEffect], DerivationEffect]
ClaimHandler = Callable[[ToolCallSpec, DerivationEffect], ClaimEffect]


@dataclass(slots=True)
class ExecutionArtifacts:
    plan: ToolPlan  # type: ignore
    executed: ExecutedPlan  # type: ignore
    raw_effects: list[RawResponseEffect] = field(default_factory=list)
    extractions: list[ExtractionEffect] = field(default_factory=list)
    derivations: list[DerivationEffect] = field(default_factory=list)
    claims: list[ClaimEffect] = field(default_factory=list)
    from_cache: bool = False


class ToolRegistry:
    """
    Registry mapping tool names to handlers for each stage.
    """

    def __init__(
        self,
        extract_handlers: Mapping[str, ExtractHandler] | None = None,
        derive_handlers: Mapping[str, DeriveHandler] | None = None,
        claim_handlers: Mapping[str, ClaimHandler] | None = None,
    ) -> None:
        self.extract_handlers = extract_handlers if extract_handlers is not None else {}
        self.derive_handlers = derive_handlers if derive_handlers is not None else {}
        self.claim_handlers = claim_handlers if claim_handlers is not None else {}

    def get_extract(self, tool: str) -> ExtractHandler | None:
        handler = self.extract_handlers.get(tool)
        if handler is None and isinstance(self.extract_handlers, defaultdict):
            handler = self.extract_handlers.default_factory()  # type: ignore[call-arg]
        return handler

    def get_derive(self, tool: str) -> DeriveHandler | None:
        handler = self.derive_handlers.get(tool)
        if handler is None and isinstance(self.derive_handlers, defaultdict):
            handler = self.derive_handlers.default_factory()  # type: ignore[call-arg]
        return handler

    def get_claim(self, tool: str) -> ClaimHandler | None:
        handler = self.claim_handlers.get(tool)
        if handler is None and isinstance(self.claim_handlers, defaultdict):
            handler = self.claim_handlers.default_factory()  # type: ignore[call-arg]
        return handler

    @classmethod
    def with_stubs(cls) -> "ToolRegistry":
        """
        Convenience constructor wiring stub handlers for all tool kinds.
        """
        return cls(
            extract_handlers=defaultdict(lambda: handlers_stub.stub_extract),
            derive_handlers=defaultdict(lambda: handlers_stub.stub_derive),
            claim_handlers=defaultdict(lambda: handlers_stub.stub_claim),
        )


def execute_plan_staged(  # noqa: PLR0913
    plan: ToolPlan,  # type: ignore
    clients: Mapping[str, ToolClient],  # type: ignore
    registry: ToolRegistry,
    *,
    raw_index: RawResponseIndex,
    extraction_index: ExtractionIndex,
    derivation_index: DerivationIndex,
    claim_index: ClaimIndex,
    plan_response_index: PlanResponseIndex | None = None,
    allow_cache: bool = True,
) -> ExecutionArtifacts:
    """
    Execute a ToolPlan through fetch → extract → derive → claim stages.

    Fetch calls use ToolClient instances. Subsequent stages dispatch to
    handlers registered in ToolRegistry, and all effects are persisted
    to DuckDB indices with memoizable plan_hash reuse.
    """
    logger = logging.getLogger(__name__)
    plan_hash = plan.plan_hash or stable_plan_hash(plan)
    plan.plan_hash = plan_hash

    cached_refs: dict[str, ToolResponseRef] = {}
    if allow_cache and plan_response_index is not None:
        cached = plan_response_index.get(plan_hash)
        if cached:
            cached_refs = {ref.call_id: ref for ref in cached.responses}
            logger.info("executor.cache.hit", plan_hash=plan_hash, response_count=len(cached_refs))
        else:
            logger.info("executor.cache.miss", plan_hash=plan_hash)
    else:
        logger.debug("executor.cache.disabled", plan_hash=plan_hash)

    start_time = time.time()
    pending: dict[str, ToolCallSpec] = {c.call_id: c for c in plan.tool_calls}
    deps: dict[str, set[str]] = {c.call_id: set() for c in plan.tool_calls}
    for dep in plan.dependencies:
        deps.setdefault(dep.to_call_id, set()).add(dep.from_call_id)

    raw_effects: list[RawResponseEffect] = []
    extractions: list[ExtractionEffect] = []
    derivations: list[DerivationEffect] = []
    claims: list[ClaimEffect] = []

    raw_by_call: dict[str, RawResponseEffect] = {}
    extraction_by_call: dict[str, ExtractionEffect] = {}
    derivation_by_call: dict[str, DerivationEffect] = {}

    executed_plan = ExecutedPlan(plan_id=plan.plan_id, plan_hash=plan_hash, from_cache=False)
    if cached_refs:
        executed_plan.from_cache = True
        executed_plan.responses.extend(cached_refs.values())
        for ref in cached_refs.values():
            cached_raw = raw_index.get(ref.response_id)
            if cached_raw:
                raw_by_call[ref.call_id] = cached_raw
                raw_effects.append(cached_raw)
        logger.info("executor.seeded-from-cache", plan_hash=plan_hash, seeded=len(raw_by_call))

    completed: set[str] = set(raw_by_call)
    skipped: set[str] = set()

    while pending:
        progressed = False
        for call_id, call in list(pending.items()):
            if any(dep not in completed for dep in deps.get(call_id, set())):
                continue

            stage = call.stage
            params = call.params or {}
            if stage == ToolStage.TOOL_STAGE_FETCH:
                if call_id in raw_by_call:
                    completed.add(call_id)
                    pending.pop(call_id)
                    progressed = True
                    logger.debug("executor.skip.fetch.cached", call_id=call_id, tool=call.tool)
                    continue
                client = clients.get(call.tool)
                if client is None:
                    if call.optional:
                        logger.info("executor.skip.missing_client", call_id=call_id, tool=call.tool)
                        skipped.add(call_id)
                        completed.add(call_id)
                        pending.pop(call_id)
                        progressed = True
                        continue
                    raise ValueError(f"No client registered for tool '{call.tool}'")
                effect = client.execute(call_id=call.call_id, endpoint=call.endpoint, params=params)
                ref = raw_index.store(effect)
                raw_effects.append(effect)
                raw_by_call[call_id] = effect
                executed_plan.responses.append(ref)
                logger.info(
                    "executor.fetch.completed",
                    call_id=call_id,
                    tool=call.tool,
                    status=effect.status_code,
                    duration_ms=effect.fetch_duration_ms,
                )
            elif stage == ToolStage.TOOL_STAGE_EXTRACT:
                handler = registry.get_extract(call.tool)
                if handler is None:
                    if call.optional:
                        logger.info("executor.skip.missing_extract_handler", call_id=call_id, tool=call.tool)
                        skipped.add(call_id)
                        completed.add(call_id)
                        pending.pop(call_id)
                        progressed = True
                        continue
                    raise ValueError(f"No extract handler registered for tool '{call.tool}'")
                source_call_id = params.get("source_call_id", "")
                if source_call_id in skipped:
                    if call.optional:
                        logger.info("executor.skip.missing_source_extract", call_id=call_id, tool=call.tool, source_call=source_call_id)
                        skipped.add(call_id)
                        completed.add(call_id)
                        pending.pop(call_id)
                        progressed = True
                        continue
                    raise RuntimeError(f"Missing source raw response for call '{call_id}'")
                source_raw = raw_by_call.get(source_call_id)
                if source_raw is None:
                    if call.optional:
                        logger.info("executor.skip.missing_source_extract", call_id=call_id, tool=call.tool, source_call=source_call_id)
                        skipped.add(call_id)
                        completed.add(call_id)
                        pending.pop(call_id)
                        progressed = True
                        continue
                    raise RuntimeError(f"Missing source raw response for call '{call_id}'")
                extraction = handler(call, source_raw)
                extraction_index.store_effect(extraction)
                extractions.append(extraction)
                extraction_by_call[call_id] = extraction
                logger.info(
                    "executor.extract.completed",
                    call_id=call_id,
                    tool=call.tool,
                    source_call=source_call_id,
                )
            elif stage == ToolStage.TOOL_STAGE_DERIVE:
                handler = registry.get_derive(call.tool)
                if handler is None:
                    if call.optional:
                        logger.info("executor.skip.missing_derive_handler", call_id=call_id, tool=call.tool)
                        skipped.add(call_id)
                        completed.add(call_id)
                        pending.pop(call_id)
                        progressed = True
                        continue
                    raise ValueError(f"No derive handler registered for tool '{call.tool}'")
                source_call_id = params.get("source_call_id", "")
                if source_call_id in skipped:
                    if call.optional:
                        logger.info("executor.skip.missing_source_derive", call_id=call_id, tool=call.tool, source_call=source_call_id)
                        skipped.add(call_id)
                        completed.add(call_id)
                        pending.pop(call_id)
                        progressed = True
                        continue
                    raise RuntimeError(f"Missing source extraction for call '{call_id}'")
                source_extraction = extraction_by_call.get(source_call_id)
                if source_extraction is None:
                    if call.optional:
                        logger.info("executor.skip.missing_source_derive", call_id=call_id, tool=call.tool, source_call=source_call_id)
                        skipped.add(call_id)
                        completed.add(call_id)
                        pending.pop(call_id)
                        progressed = True
                        continue
                    raise RuntimeError(f"Missing source extraction for call '{call_id}'")
                derivation = handler(call, source_extraction)
                derivation_index.store_effect(derivation)
                derivations.append(derivation)
                derivation_by_call[call_id] = derivation
                logger.info(
                    "executor.derive.completed",
                    call_id=call_id,
                    tool=call.tool,
                    source_call=source_call_id,
                )
            elif stage == ToolStage.TOOL_STAGE_CLAIM:
                handler = registry.get_claim(call.tool)
                if handler is None:
                    if call.optional:
                        logger.info("executor.skip.missing_claim_handler", call_id=call_id, tool=call.tool)
                        skipped.add(call_id)
                        completed.add(call_id)
                        pending.pop(call_id)
                        progressed = True
                        continue
                    raise ValueError(f"No claim handler registered for tool '{call.tool}'")
                source_call_id = params.get("source_call_id", "")
                if source_call_id in skipped:
                    if call.optional:
                        logger.info("executor.skip.missing_source_claim", call_id=call_id, tool=call.tool, source_call=source_call_id)
                        skipped.add(call_id)
                        completed.add(call_id)
                        pending.pop(call_id)
                        progressed = True
                        continue
                    raise RuntimeError(f"Missing source derivation for call '{call_id}'")
                source_derivation = derivation_by_call.get(source_call_id)
                if source_derivation is None:
                    if call.optional:
                        logger.info("executor.skip.missing_source_claim", call_id=call_id, tool=call.tool, source_call=source_call_id)
                        skipped.add(call_id)
                        completed.add(call_id)
                        pending.pop(call_id)
                        progressed = True
                        continue
                    raise RuntimeError(f"Missing source derivation for call '{call_id}'")
                claim = handler(call, source_derivation)
                claim_index.store_effect(claim)
                claims.append(claim)
                logger.info(
                    "executor.claim.completed",
                    call_id=call_id,
                    tool=call.tool,
                    source_call=source_call_id,
                )
            else:
                raise ValueError(f"Unsupported tool stage for call '{call_id}': {stage}")

            completed.add(call_id)
            pending.pop(call_id)
            progressed = True

        if not progressed:
            raise RuntimeError("Dependency cycle detected in ToolPlan")

    duration_ms = int((time.time() - start_time) * 1000)
    executed_plan.execution_time_ms = duration_ms
    logger.info(
        "executor.finished",
        plan_hash=plan_hash,
        duration_ms=duration_ms,
        fetch_count=len(raw_effects),
        extraction_count=len(extractions),
        derivation_count=len(derivations),
        claim_count=len(claims),
    )

    if plan_response_index is not None and raw_effects:
        # Only upsert when we have new responses; cache reuse keeps prior index.
        plan_response_index.upsert(
            plan_hash=executed_plan.plan_hash, plan_id=executed_plan.plan_id, response_refs=executed_plan.responses
        )

    return ExecutionArtifacts(
        plan=plan,
        executed=executed_plan,
        raw_effects=raw_effects,
        extractions=extractions,
        derivations=derivations,
        claims=claims,
        from_cache=bool(cached_refs),
    )
