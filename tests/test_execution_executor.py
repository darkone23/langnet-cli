from __future__ import annotations

from collections.abc import Mapping

import duckdb
from query_spec import (
    LanguageHint,
    NormalizedQuery,
    PlanDependency,
    ToolCallSpec,
    ToolPlan,
    ToolStage,
)

from langnet.clients.base import RawResponseEffect
from langnet.execution.effects import (
    ClaimEffect,
    DerivationEffect,
    ExtractionEffect,
    ProvenanceLink,
    stable_effect_id,
)
from langnet.execution.executor import ExecutionArtifacts, ToolRegistry, execute_plan_staged
from langnet.execution.registry import default_registry
from langnet.storage.claim_index import ClaimIndex
from langnet.storage.derivation_index import DerivationIndex
from langnet.storage.effects_index import RawResponseIndex
from langnet.storage.extraction_index import ExtractionIndex
from langnet.storage.plan_index import PlanResponseIndex, apply_schema


class _FakeClient:
    def __init__(self, tool: str) -> None:
        self.tool = tool
        self.calls: list[str] = []

    def execute(
        self, call_id: str, endpoint: str, params: Mapping[str, str] | None = None
    ) -> RawResponseEffect:
        self.calls.append(call_id)
        body = f"{call_id}:{(params or {}).get('q', '')}".encode()
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


def _build_plan() -> ToolPlan:
    normalized = NormalizedQuery(
        original="lupus",
        language=LanguageHint.LANGUAGE_HINT_LAT,
        candidates=[],
        normalizations=[],
    )
    fetch_call = ToolCallSpec(
        tool="fetch.dummy",
        call_id="call-fetch",
        endpoint="http://example",
        params={"q": "1"},
        stage=ToolStage.TOOL_STAGE_FETCH,
    )
    extract_call = ToolCallSpec(
        tool="extract.dummy",
        call_id="call-extract",
        endpoint="internal://extract",
        params={"source_call_id": "call-fetch"},
        stage=ToolStage.TOOL_STAGE_EXTRACT,
    )
    derive_call = ToolCallSpec(
        tool="derive.dummy",
        call_id="call-derive",
        endpoint="internal://derive",
        params={"source_call_id": "call-extract"},
        stage=ToolStage.TOOL_STAGE_DERIVE,
    )
    claim_call = ToolCallSpec(
        tool="claim.dummy",
        call_id="call-claim",
        endpoint="internal://claim",
        params={"source_call_id": "call-derive"},
        stage=ToolStage.TOOL_STAGE_CLAIM,
    )
    deps = [
        PlanDependency(from_call_id="call-fetch", to_call_id="call-extract"),
        PlanDependency(from_call_id="call-extract", to_call_id="call-derive"),
        PlanDependency(from_call_id="call-derive", to_call_id="call-claim"),
    ]
    plan = ToolPlan(
        plan_id="plan-1",
        plan_hash="",
        query=normalized,
        tool_calls=[fetch_call, extract_call, derive_call, claim_call],
        dependencies=deps,
    )
    return plan


def _registry() -> ToolRegistry:
    def _extract(call: ToolCallSpec, raw: RawResponseEffect) -> ExtractionEffect:
        return ExtractionEffect(
            extraction_id=stable_effect_id("ext", call.call_id, raw.response_id),
            tool=call.tool,
            call_id=call.call_id,
            source_call_id=call.params.get("source_call_id", ""),
            response_id=raw.response_id,
            kind="dummy",
            canonical="lupus",
            payload={"body": raw.body.decode()},
        )

    def _derive(call: ToolCallSpec, extraction: ExtractionEffect) -> DerivationEffect:
        return DerivationEffect(
            derivation_id=stable_effect_id("drv", call.call_id, extraction.extraction_id),
            tool=call.tool,
            call_id=call.call_id,
            source_call_id=call.params.get("source_call_id", ""),
            extraction_id=extraction.extraction_id,
            kind="dummy-derive",
            canonical=extraction.canonical,
            payload={"lemma": "lupus"},
            provenance_chain=[
                ProvenanceLink(stage="extract", tool=extraction.tool, reference_id=extraction.extraction_id)
            ],
        )

    def _claim(call: ToolCallSpec, derivation: DerivationEffect) -> ClaimEffect:
        prov = derivation.provenance_chain or []
        prov.append(ProvenanceLink(stage="derive", tool=derivation.tool, reference_id=derivation.derivation_id))
        return ClaimEffect(
            claim_id=stable_effect_id("clm", call.call_id, derivation.derivation_id),
            tool=call.tool,
            call_id=call.call_id,
            source_call_id=call.params.get("source_call_id", ""),
            derivation_id=derivation.derivation_id,
            subject="lupus",
            predicate="has_lemma",
            value={"lemma": "lupus"},
            provenance_chain=prov,
        )

    return ToolRegistry(
        extract_handlers={"extract.dummy": _extract},
        derive_handlers={"derive.dummy": _derive},
        claim_handlers={"claim.dummy": _claim},
    )


def _execute(conn: duckdb.DuckDBPyConnection, allow_cache: bool = True) -> ExecutionArtifacts:
    apply_schema(conn)
    raw_index = RawResponseIndex(conn)
    extraction_index = ExtractionIndex(conn)
    derivation_index = DerivationIndex(conn)
    claim_index = ClaimIndex(conn)
    plan_response_index = PlanResponseIndex(conn)

    client = _FakeClient(tool="fetch.dummy")
    plan = _build_plan()
    return execute_plan_staged(
        plan=plan,
        clients={client.tool: client},
        registry=_registry(),
        raw_index=raw_index,
        extraction_index=extraction_index,
        derivation_index=derivation_index,
        claim_index=claim_index,
        plan_response_index=plan_response_index,
        allow_cache=allow_cache,
    )


def test_dio_handlers_in_registry() -> None:
    # Fake HTML containing lemmas
    html = b"<html><body><i>Lupus</i><b>Canis</b></body></html>"
    client = _FakeClient(tool="fetch.diogenes")
    client.execute = lambda call_id, endpoint, params=None: RawResponseEffect(
        response_id=f"{call_id}-resp",
        tool="fetch.diogenes",
        call_id=call_id,
        endpoint=endpoint,
        status_code=200,
        content_type="text/html",
        headers={},
        body=html,
    )

    conn = duckdb.connect(database=":memory:")
    apply_schema(conn)
    raw_index = RawResponseIndex(conn)
    extraction_index = ExtractionIndex(conn)
    derivation_index = DerivationIndex(conn)
    claim_index = ClaimIndex(conn)
    plan_response_index = PlanResponseIndex(conn)

    normalized = NormalizedQuery(
        original="lupus",
        language=LanguageHint.LANGUAGE_HINT_LAT,
        candidates=[],
        normalizations=[],
    )
    fetch_call = ToolCallSpec(
        tool="fetch.diogenes",
        call_id="dio-fetch",
        endpoint="http://example",
        params={"q": "lupus"},
        stage=ToolStage.TOOL_STAGE_FETCH,
    )
    extract_call = ToolCallSpec(
        tool="extract.diogenes.html",
        call_id="dio-extract",
        endpoint="internal://diogenes/html_extract",
        params={"source_call_id": "dio-fetch"},
        stage=ToolStage.TOOL_STAGE_EXTRACT,
    )
    derive_call = ToolCallSpec(
        tool="derive.diogenes.morph",
        call_id="dio-derive",
        endpoint="internal://diogenes/morph_derive",
        params={"source_call_id": "dio-extract"},
        stage=ToolStage.TOOL_STAGE_DERIVE,
    )
    claim_call = ToolCallSpec(
        tool="claim.diogenes.morph",
        call_id="dio-claim",
        endpoint="internal://claim/diogenes_morph",
        params={"source_call_id": "dio-derive"},
        stage=ToolStage.TOOL_STAGE_CLAIM,
    )
    plan = ToolPlan(
        plan_id="plan-dio",
        plan_hash="",
        query=normalized,
        tool_calls=[fetch_call, extract_call, derive_call, claim_call],
        dependencies=[
            PlanDependency(from_call_id="dio-fetch", to_call_id="dio-extract"),
            PlanDependency(from_call_id="dio-extract", to_call_id="dio-derive"),
            PlanDependency(from_call_id="dio-derive", to_call_id="dio-claim"),
        ],
    )
    registry = default_registry()
    result = execute_plan_staged(
        plan=plan,
        clients={"fetch.diogenes": client},
        registry=registry,
        raw_index=raw_index,
        extraction_index=extraction_index,
        derivation_index=derivation_index,
        claim_index=claim_index,
        plan_response_index=plan_response_index,
    )
    assert result.claims, "Diogenes claim should be produced"
    assert result.claims[0].predicate == "has_lemmas"
    assert "lupus" in result.claims[0].value.get("lemmas", [])


def test_executor_runs_all_stages_and_caches_fetch() -> None:
    conn = duckdb.connect(database=":memory:")
    first = _execute(conn, allow_cache=True)
    # Fetch executed and produced a claim
    assert first.raw_effects and first.claims

    # Second run should reuse cached fetch and still yield claims
    second = _execute(conn, allow_cache=True)
    assert second.raw_effects and second.claims
    # No new fetch call when using cache
    assert second.from_cache is True


def test_tool_registry_with_stubs() -> None:
    reg = ToolRegistry.with_stubs()
    assert callable(reg.get_extract("anything"))
    assert callable(reg.get_derive("anything"))
    assert callable(reg.get_claim("anything"))
