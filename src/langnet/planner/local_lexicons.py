from __future__ import annotations

from query_spec import PlanDependency, ToolCallSpec, ToolStage

from langnet.planner.calls import make_call, opts


def append_dico_calls(
    calls: list[ToolCallSpec],
    deps: list[PlanDependency],
    *,
    velthuis: str,
    lemma: str,
    original: str,
) -> None:
    """Append the staged local DICO source-gloss pipeline."""
    dico_fetch_id = "dico-1"
    calls.append(
        make_call(
            tool="fetch.dico",
            call_id=dico_fetch_id,
            endpoint="duckdb://dico",
            params={
                "headword": velthuis,
                "velthuis": velthuis,
                "lemma": lemma,
                "q": original,
            },
            opts=opts(expected="json", priority=6, optional=True, stage=ToolStage.TOOL_STAGE_FETCH),
        )
    )
    dico_extract_id = "dico-extract-1"
    calls.append(
        make_call(
            tool="extract.dico.json",
            call_id=dico_extract_id,
            endpoint="internal://dico/json_extract",
            params={"source_call_id": dico_fetch_id},
            opts=opts(
                expected="extraction",
                priority=7,
                optional=True,
                stage=ToolStage.TOOL_STAGE_EXTRACT,
            ),
        )
    )
    deps.append(
        PlanDependency(
            from_call_id=dico_fetch_id,
            to_call_id=dico_extract_id,
            rationale="Extract local DICO JSON after fetch",
        )
    )
    dico_derive_id = "dico-derive-1"
    calls.append(
        make_call(
            tool="derive.dico.entries",
            call_id=dico_derive_id,
            endpoint="internal://dico/entry_derive",
            params={"source_call_id": dico_extract_id},
            opts=opts(
                expected="derivation",
                priority=8,
                optional=True,
                stage=ToolStage.TOOL_STAGE_DERIVE,
            ),
        )
    )
    deps.append(
        PlanDependency(
            from_call_id=dico_extract_id,
            to_call_id=dico_derive_id,
            rationale="Derive local DICO entries",
        )
    )
    dico_claim_id = "claim-dico-1"
    calls.append(
        make_call(
            tool="claim.dico.entries",
            call_id=dico_claim_id,
            endpoint="internal://claim/dico_entries",
            params={"source_call_id": dico_derive_id},
            opts=opts(
                expected="claim", priority=9, optional=True, stage=ToolStage.TOOL_STAGE_CLAIM
            ),
        )
    )
    deps.append(
        PlanDependency(
            from_call_id=dico_derive_id,
            to_call_id=dico_claim_id,
            rationale="Produce local DICO source gloss claims",
        )
    )


def append_gaffiot_calls(
    calls: list[ToolCallSpec],
    deps: list[PlanDependency],
    *,
    headword: str,
    lemma: str,
) -> None:
    """Append the staged local Gaffiot source-gloss pipeline."""
    gaffiot_fetch_id = "gaffiot-1"
    calls.append(
        make_call(
            tool="fetch.gaffiot",
            call_id=gaffiot_fetch_id,
            endpoint="duckdb://gaffiot",
            params={"headword": headword, "lemma": lemma},
            opts=opts(expected="json", priority=7, optional=True, stage=ToolStage.TOOL_STAGE_FETCH),
        )
    )
    gaffiot_extract_id = "gaffiot-extract-1"
    calls.append(
        make_call(
            tool="extract.gaffiot.json",
            call_id=gaffiot_extract_id,
            endpoint="internal://gaffiot/json_extract",
            params={"source_call_id": gaffiot_fetch_id},
            opts=opts(
                expected="extraction",
                priority=8,
                optional=True,
                stage=ToolStage.TOOL_STAGE_EXTRACT,
            ),
        )
    )
    deps.append(
        PlanDependency(
            from_call_id=gaffiot_fetch_id,
            to_call_id=gaffiot_extract_id,
            rationale="Extract local Gaffiot JSON after fetch",
        )
    )
    gaffiot_derive_id = "gaffiot-derive-1"
    calls.append(
        make_call(
            tool="derive.gaffiot.entries",
            call_id=gaffiot_derive_id,
            endpoint="internal://gaffiot/entry_derive",
            params={"source_call_id": gaffiot_extract_id},
            opts=opts(
                expected="derivation",
                priority=9,
                optional=True,
                stage=ToolStage.TOOL_STAGE_DERIVE,
            ),
        )
    )
    deps.append(
        PlanDependency(
            from_call_id=gaffiot_extract_id,
            to_call_id=gaffiot_derive_id,
            rationale="Derive local Gaffiot entries",
        )
    )
    gaffiot_claim_id = "claim-gaffiot-1"
    calls.append(
        make_call(
            tool="claim.gaffiot.entries",
            call_id=gaffiot_claim_id,
            endpoint="internal://claim/gaffiot_entries",
            params={"source_call_id": gaffiot_derive_id},
            opts=opts(
                expected="claim",
                priority=10,
                optional=True,
                stage=ToolStage.TOOL_STAGE_CLAIM,
            ),
        )
    )
    deps.append(
        PlanDependency(
            from_call_id=gaffiot_derive_id,
            to_call_id=gaffiot_claim_id,
            rationale="Produce local Gaffiot source gloss claims",
        )
    )
