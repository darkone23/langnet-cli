from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import cast

import structlog
from query_spec import ExecutedPlan, ToolCallSpec, ToolPlan, ToolResponseRef, ToolStage

from langnet.clients.base import RawResponseEffect, ToolClient
from langnet.execution import handlers_stub
from langnet.execution.effects import ClaimEffect, DerivationEffect, ExtractionEffect
from langnet.execution.versioning import get_handler_version
from langnet.logging import setup_logging
from langnet.planner.core import stable_plan_hash
from langnet.storage.claim_index import ClaimIndex
from langnet.storage.derivation_index import DerivationIndex
from langnet.storage.effects_index import RawResponseIndex
from langnet.storage.extraction_index import ExtractionIndex
from langnet.storage.plan_index import PlanResponseIndex

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
            factory_result = self.extract_handlers.default_factory()  # type: ignore[call-arg]
            handler = cast(ExtractHandler, factory_result)
        return handler

    def get_derive(self, tool: str) -> DeriveHandler | None:
        handler = self.derive_handlers.get(tool)
        if handler is None and isinstance(self.derive_handlers, defaultdict):
            factory_result = self.derive_handlers.default_factory()  # type: ignore[call-arg]
            handler = cast(DeriveHandler, factory_result)
        return handler

    def get_claim(self, tool: str) -> ClaimHandler | None:
        handler = self.claim_handlers.get(tool)
        if handler is None and isinstance(self.claim_handlers, defaultdict):
            factory_result = self.claim_handlers.default_factory()  # type: ignore[call-arg]
            handler = cast(ClaimHandler, factory_result)
        return handler

    @classmethod
    def with_stubs(cls) -> ToolRegistry:
        """
        Convenience constructor wiring stub handlers for all tool kinds.
        """
        return cls(
            extract_handlers=defaultdict(lambda: handlers_stub.stub_extract),
            derive_handlers=defaultdict(lambda: handlers_stub.stub_derive),
            claim_handlers=defaultdict(lambda: handlers_stub.stub_claim),
        )


@dataclass(slots=True)
class _ExecutionState:
    """State tracking for staged execution."""

    raw_by_call: dict[str, RawResponseEffect] = field(default_factory=dict)
    extraction_by_call: dict[str, ExtractionEffect] = field(default_factory=dict)
    derivation_by_call: dict[str, DerivationEffect] = field(default_factory=dict)
    completed: set[str] = field(default_factory=set)
    skipped: set[str] = field(default_factory=set)


@dataclass(slots=True)
class _ExecutionContext:
    """Shared context for stage handlers."""

    logger: object
    clients: Mapping[str, ToolClient]
    registry: ToolRegistry
    raw_index: RawResponseIndex
    extraction_index: ExtractionIndex
    derivation_index: DerivationIndex
    claim_index: ClaimIndex


def _initialize_cache_and_state(  # noqa: PLR0913
    plan: ToolPlan,  # type: ignore
    plan_hash: str,
    allow_cache: bool,
    plan_response_index: PlanResponseIndex | None,
    raw_index: RawResponseIndex,
    logger: object,
) -> tuple[ExecutedPlan, _ExecutionState, list[RawResponseEffect]]:
    """Initialize cache and execution state from plan response index."""
    cached_refs: dict[str, ToolResponseRef] = {}
    if allow_cache and plan_response_index is not None:
        cached = plan_response_index.get(plan_hash)
        if cached:
            cached_refs = {ref.call_id: ref for ref in cached.responses}
            logger.info("executor.cache.hit", plan_hash=plan_hash, response_count=len(cached_refs))  # type: ignore[attr-defined]
        else:
            logger.info("executor.cache.miss", plan_hash=plan_hash)  # type: ignore[attr-defined]
    else:
        logger.debug("executor.cache.disabled", plan_hash=plan_hash)  # type: ignore[attr-defined]

    raw_effects: list[RawResponseEffect] = []
    state = _ExecutionState()
    executed_plan = ExecutedPlan(plan_id=plan.plan_id, plan_hash=plan_hash, from_cache=False)

    if cached_refs:
        executed_plan.from_cache = True
        executed_plan.responses.extend(cached_refs.values())
        for ref in cached_refs.values():
            cached_raw = raw_index.get(ref.response_id)
            if cached_raw:
                state.raw_by_call[ref.call_id] = cached_raw
                raw_effects.append(cached_raw)
        logger.info(  # type: ignore[attr-defined]
            "executor.seeded-from-cache", plan_hash=plan_hash, seeded=len(state.raw_by_call)
        )
        state.completed = set(state.raw_by_call)

    return executed_plan, state, raw_effects


def _handle_fetch_stage(
    call: ToolCallSpec,
    ctx: _ExecutionContext,
    state: _ExecutionState,
    raw_effects: list[RawResponseEffect],
    executed_plan: ExecutedPlan,
) -> bool:
    """
    Handle FETCH stage for a tool call.

    Returns True if the call was processed (completed or skipped).
    """
    call_id = call.call_id
    if call_id in state.raw_by_call:
        state.completed.add(call_id)
        ctx.logger.debug("executor.skip.fetch.cached", call_id=call_id, tool=call.tool)  # type: ignore[attr-defined]
        return True

    client = ctx.clients.get(call.tool)
    if client is None:
        if call.optional:
            ctx.logger.info("executor.skip.missing_client", call_id=call_id, tool=call.tool)  # type: ignore[attr-defined]
            state.skipped.add(call_id)
            state.completed.add(call_id)
            return True
        raise ValueError(f"No client registered for tool '{call.tool}'")

    params = call.params or {}
    effect = client.execute(call_id=call.call_id, endpoint=call.endpoint, params=params)
    ref = ctx.raw_index.store(effect)
    raw_effects.append(effect)
    state.raw_by_call[call_id] = effect
    executed_plan.responses.append(ref)
    ctx.logger.info(  # type: ignore[attr-defined]
        "executor.fetch.completed",
        call_id=call_id,
        tool=call.tool,
        status=effect.status_code,
        duration_ms=effect.fetch_duration_ms,
    )
    return True


def _handle_extract_stage(
    call: ToolCallSpec,
    ctx: _ExecutionContext,
    state: _ExecutionState,
    extractions: list[ExtractionEffect],
) -> bool:
    """
    Handle EXTRACT stage for a tool call.

    Returns True if the call was processed (completed or skipped).
    """
    call_id = call.call_id
    handler = ctx.registry.get_extract(call.tool)
    if handler is None:
        if call.optional:
            ctx.logger.info(  # type: ignore[attr-defined]
                "executor.skip.missing_extract_handler", call_id=call_id, tool=call.tool
            )
            state.skipped.add(call_id)
            state.completed.add(call_id)
            return True
        raise ValueError(f"No extract handler registered for tool '{call.tool}'")

    params = call.params or {}
    source_call_id = params.get("source_call_id", "")
    if source_call_id in state.skipped:
        if call.optional:
            ctx.logger.info(  # type: ignore[attr-defined]
                "executor.skip.missing_source_extract",
                call_id=call_id,
                tool=call.tool,
                source_call=source_call_id,
            )
            state.skipped.add(call_id)
            state.completed.add(call_id)
            return True
        raise RuntimeError(f"Missing source raw response for call '{call_id}'")

    source_raw = state.raw_by_call.get(source_call_id)
    if source_raw is None:
        if call.optional:
            ctx.logger.info(  # type: ignore[attr-defined]
                "executor.skip.missing_source_extract",
                call_id=call_id,
                tool=call.tool,
                source_call=source_call_id,
            )
            state.skipped.add(call_id)
            state.completed.add(call_id)
            return True
        raise RuntimeError(f"Missing source raw response for call '{call_id}'")

    handler_start = time.time()
    extraction = handler(call, source_raw)
    handler_ms = int((time.time() - handler_start) * 1000)

    # Inject handler version for cache invalidation
    handler_version = get_handler_version(handler)
    if handler_version is not None:
        extraction.handler_version = handler_version

    ctx.extraction_index.store_effect(extraction)
    extractions.append(extraction)
    state.extraction_by_call[call_id] = extraction
    ctx.logger.info(  # type: ignore[attr-defined]
        "executor.extract.completed",
        call_id=call_id,
        tool=call.tool,
        source_call=source_call_id,
        duration_ms=handler_ms,
    )
    return True


def _handle_derive_stage(
    call: ToolCallSpec,
    ctx: _ExecutionContext,
    state: _ExecutionState,
    derivations: list[DerivationEffect],
) -> bool:
    """
    Handle DERIVE stage for a tool call.

    Returns True if the call was processed (completed or skipped).
    """
    call_id = call.call_id
    handler = ctx.registry.get_derive(call.tool)
    if handler is None:
        if call.optional:
            ctx.logger.info("executor.skip.missing_derive_handler", call_id=call_id, tool=call.tool)  # type: ignore[attr-defined]
            state.skipped.add(call_id)
            state.completed.add(call_id)
            return True
        raise ValueError(f"No derive handler registered for tool '{call.tool}'")

    params = call.params or {}
    source_call_id = params.get("source_call_id", "")
    if source_call_id in state.skipped:
        if call.optional:
            ctx.logger.info(  # type: ignore[attr-defined]
                "executor.skip.missing_source_derive",
                call_id=call_id,
                tool=call.tool,
                source_call=source_call_id,
            )
            state.skipped.add(call_id)
            state.completed.add(call_id)
            return True
        raise RuntimeError(f"Missing source extraction for call '{call_id}'")

    source_extraction = state.extraction_by_call.get(source_call_id)
    if source_extraction is None:
        if call.optional:
            ctx.logger.info(  # type: ignore[attr-defined]
                "executor.skip.missing_source_derive",
                call_id=call_id,
                tool=call.tool,
                source_call=source_call_id,
            )
            state.skipped.add(call_id)
            state.completed.add(call_id)
            return True
        raise RuntimeError(f"Missing source extraction for call '{call_id}'")

    handler_start = time.time()
    derivation = handler(call, source_extraction)
    handler_ms = int((time.time() - handler_start) * 1000)

    # Inject handler version for cache invalidation
    handler_version = get_handler_version(handler)
    if handler_version is not None:
        derivation.handler_version = handler_version

    ctx.derivation_index.store_effect(derivation)
    derivations.append(derivation)
    state.derivation_by_call[call_id] = derivation
    ctx.logger.info(  # type: ignore[attr-defined]
        "executor.derive.completed",
        call_id=call_id,
        tool=call.tool,
        source_call=source_call_id,
        duration_ms=handler_ms,
    )
    return True


def _handle_claim_stage(
    call: ToolCallSpec,
    ctx: _ExecutionContext,
    state: _ExecutionState,
    claims: list[ClaimEffect],
) -> bool:
    """
    Handle CLAIM stage for a tool call.

    Returns True if the call was processed (completed or skipped).
    """
    call_id = call.call_id
    handler = ctx.registry.get_claim(call.tool)
    if handler is None:
        if call.optional:
            ctx.logger.info("executor.skip.missing_claim_handler", call_id=call_id, tool=call.tool)  # type: ignore[attr-defined]
            state.skipped.add(call_id)
            state.completed.add(call_id)
            return True
        raise ValueError(f"No claim handler registered for tool '{call.tool}'")

    params = call.params or {}
    source_call_id = params.get("source_call_id", "")
    if source_call_id in state.skipped:
        if call.optional:
            ctx.logger.info(  # type: ignore[attr-defined]
                "executor.skip.missing_source_claim",
                call_id=call_id,
                tool=call.tool,
                source_call=source_call_id,
            )
            state.skipped.add(call_id)
            state.completed.add(call_id)
            return True
        raise RuntimeError(f"Missing source derivation for call '{call_id}'")

    source_derivation = state.derivation_by_call.get(source_call_id)
    if source_derivation is None:
        if call.optional:
            ctx.logger.info(  # type: ignore[attr-defined]
                "executor.skip.missing_source_claim",
                call_id=call_id,
                tool=call.tool,
                source_call=source_call_id,
            )
            state.skipped.add(call_id)
            state.completed.add(call_id)
            return True
        raise RuntimeError(f"Missing source derivation for call '{call_id}'")

    handler_start = time.time()
    claim = handler(call, source_derivation)
    handler_ms = int((time.time() - handler_start) * 1000)

    # Inject handler version for cache invalidation
    handler_version = get_handler_version(handler)
    if handler_version is not None:
        claim.handler_version = handler_version

    ctx.claim_index.store_effect(claim)
    claims.append(claim)
    ctx.logger.info(  # type: ignore[attr-defined]
        "executor.claim.completed",
        call_id=call_id,
        tool=call.tool,
        source_call=source_call_id,
        duration_ms=handler_ms,
    )
    return True


def _process_pending_calls(  # noqa: PLR0913
    pending: dict[str, ToolCallSpec],
    deps: dict[str, set[str]],
    state: _ExecutionState,
    ctx: _ExecutionContext,
    raw_effects: list[RawResponseEffect],
    extractions: list[ExtractionEffect],
    derivations: list[DerivationEffect],
    claims: list[ClaimEffect],
    executed_plan: ExecutedPlan,
) -> bool:
    """
    Process one iteration of pending calls. Returns True if progress was made.
    """
    progressed = False
    for call_id, call in list(pending.items()):
        if any(dep not in state.completed for dep in deps.get(call_id, set())):
            continue

        stage = call.stage
        processed = False

        if stage == ToolStage.TOOL_STAGE_FETCH:
            processed = _handle_fetch_stage(call, ctx, state, raw_effects, executed_plan)
        elif stage == ToolStage.TOOL_STAGE_EXTRACT:
            processed = _handle_extract_stage(call, ctx, state, extractions)
        elif stage == ToolStage.TOOL_STAGE_DERIVE:
            processed = _handle_derive_stage(call, ctx, state, derivations)
        elif stage == ToolStage.TOOL_STAGE_CLAIM:
            processed = _handle_claim_stage(call, ctx, state, claims)
        else:
            raise ValueError(f"Unsupported tool stage for call '{call_id}': {stage}")

        if processed:
            state.completed.add(call_id)
            pending.pop(call_id)
            progressed = True

    return progressed


def execute_plan_staged(  # noqa: PLR0913
    plan: ToolPlan,
    clients: Mapping[str, ToolClient],
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
    setup_logging()
    logger = structlog.get_logger(__name__)
    plan_hash = plan.plan_hash or stable_plan_hash(plan)
    plan.plan_hash = plan_hash

    start_time = time.time()
    executed_plan, state, raw_effects = _initialize_cache_and_state(
        plan, plan_hash, allow_cache, plan_response_index, raw_index, logger
    )

    pending: dict[str, ToolCallSpec] = {c.call_id: c for c in plan.tool_calls}
    deps: dict[str, set[str]] = {c.call_id: set() for c in plan.tool_calls}
    for dep in plan.dependencies:
        deps.setdefault(dep.to_call_id, set()).add(dep.from_call_id)

    extractions: list[ExtractionEffect] = []
    derivations: list[DerivationEffect] = []
    claims: list[ClaimEffect] = []

    ctx = _ExecutionContext(
        logger=logger,
        clients=clients,
        registry=registry,
        raw_index=raw_index,
        extraction_index=extraction_index,
        derivation_index=derivation_index,
        claim_index=claim_index,
    )

    while pending:
        progressed = _process_pending_calls(
            pending, deps, state, ctx, raw_effects, extractions, derivations, claims, executed_plan
        )
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
            plan_hash=executed_plan.plan_hash,
            plan_id=executed_plan.plan_id,
            response_refs=executed_plan.responses,
        )

    return ExecutionArtifacts(
        plan=plan,
        executed=executed_plan,
        raw_effects=raw_effects,
        extractions=extractions,
        derivations=derivations,
        claims=claims,
        from_cache=executed_plan.from_cache,
    )
