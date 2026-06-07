from __future__ import annotations

from pathlib import Path

from query_spec import PlanDependency, ToolCallSpec, ToolStage

from langnet.databuild.paths import default_georges_1913_path, default_strongs_greek_path
from langnet.planner.calls import make_call, opts


def _local_index_signature(path: Path) -> str:
    try:
        stat = path.stat()
    except FileNotFoundError:
        return "missing"
    return f"{stat.st_size}:{stat.st_mtime_ns}"


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
    lemma_candidates: list[str] | None = None,
) -> None:
    """Append the staged local Gaffiot source-gloss pipeline."""
    gaffiot_fetch_id = "gaffiot-1"
    params = {"headword": headword, "lemma": lemma}
    if lemma_candidates:
        params["lemma_candidates"] = ";".join(lemma_candidates)
    calls.append(
        make_call(
            tool="fetch.gaffiot",
            call_id=gaffiot_fetch_id,
            endpoint="duckdb://gaffiot",
            params=params,
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


def append_lewis_1890_calls(
    calls: list[ToolCallSpec],
    deps: list[PlanDependency],
    *,
    headword: str,
    lemma: str,
    lemma_candidates: list[str] | None = None,
) -> None:
    """Append the staged local Lewis 1890 source-gloss pipeline."""
    fetch_id = "lewis-1890-1"
    params = {"headword": headword, "lemma": lemma}
    if lemma_candidates:
        params["lemma_candidates"] = ";".join(lemma_candidates)
    calls.append(
        make_call(
            tool="fetch.lewis_1890",
            call_id=fetch_id,
            endpoint="duckdb://lewis_1890",
            params=params,
            opts=opts(expected="json", priority=7, optional=True, stage=ToolStage.TOOL_STAGE_FETCH),
        )
    )
    extract_id = "lewis-1890-extract-1"
    calls.append(
        make_call(
            tool="extract.lewis_1890.json",
            call_id=extract_id,
            endpoint="internal://lewis_1890/json_extract",
            params={"source_call_id": fetch_id},
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
            from_call_id=fetch_id,
            to_call_id=extract_id,
            rationale="Extract local Lewis 1890 JSON after fetch",
        )
    )
    derive_id = "lewis-1890-derive-1"
    calls.append(
        make_call(
            tool="derive.lewis_1890.entries",
            call_id=derive_id,
            endpoint="internal://lewis_1890/entry_derive",
            params={"source_call_id": extract_id},
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
            from_call_id=extract_id,
            to_call_id=derive_id,
            rationale="Derive local Lewis 1890 entries",
        )
    )
    claim_id = "claim-lewis-1890-1"
    calls.append(
        make_call(
            tool="claim.lewis_1890.entries",
            call_id=claim_id,
            endpoint="internal://claim/lewis_1890_entries",
            params={"source_call_id": derive_id},
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
            from_call_id=derive_id,
            to_call_id=claim_id,
            rationale="Produce local Lewis 1890 source gloss claims",
        )
    )


def append_georges_1913_calls(
    calls: list[ToolCallSpec],
    deps: list[PlanDependency],
    *,
    headword: str,
    lemma: str,
    lemma_candidates: list[str] | None = None,
) -> None:
    """Append the staged local Georges 1913 source-gloss pipeline."""
    fetch_id = "georges-1913-1"
    params = {
        "headword": headword,
        "lemma": lemma,
        "index_signature": _local_index_signature(default_georges_1913_path()),
    }
    if lemma_candidates:
        params["lemma_candidates"] = ";".join(lemma_candidates)
    calls.append(
        make_call(
            tool="fetch.georges_1913",
            call_id=fetch_id,
            endpoint="duckdb://georges_1913",
            params=params,
            opts=opts(expected="json", priority=7, optional=True, stage=ToolStage.TOOL_STAGE_FETCH),
        )
    )
    extract_id = "georges-1913-extract-1"
    calls.append(
        make_call(
            tool="extract.georges_1913.json",
            call_id=extract_id,
            endpoint="internal://georges_1913/json_extract",
            params={"source_call_id": fetch_id},
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
            from_call_id=fetch_id,
            to_call_id=extract_id,
            rationale="Extract local Georges 1913 JSON after fetch",
        )
    )
    derive_id = "georges-1913-derive-1"
    calls.append(
        make_call(
            tool="derive.georges_1913.entries",
            call_id=derive_id,
            endpoint="internal://georges_1913/entry_derive",
            params={"source_call_id": extract_id},
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
            from_call_id=extract_id,
            to_call_id=derive_id,
            rationale="Derive local Georges 1913 entries",
        )
    )
    claim_id = "claim-georges-1913-1"
    calls.append(
        make_call(
            tool="claim.georges_1913.entries",
            call_id=claim_id,
            endpoint="internal://claim/georges_1913_entries",
            params={"source_call_id": derive_id},
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
            from_call_id=derive_id,
            to_call_id=claim_id,
            rationale="Produce local Georges 1913 source gloss claims",
        )
    )


def append_bailly_calls(
    calls: list[ToolCallSpec],
    deps: list[PlanDependency],
    *,
    headword: str,
    lemma: str,
    lemma_candidates: list[str] | None = None,
) -> None:
    """Append the staged local Bailly source-gloss pipeline."""
    bailly_fetch_id = "bailly-1"
    params = {"headword": headword, "lemma": lemma}
    if lemma_candidates:
        params["lemma_candidates"] = ";".join(lemma_candidates)
    calls.append(
        make_call(
            tool="fetch.bailly",
            call_id=bailly_fetch_id,
            endpoint="duckdb://bailly",
            params=params,
            opts=opts(expected="json", priority=7, optional=True, stage=ToolStage.TOOL_STAGE_FETCH),
        )
    )
    bailly_extract_id = "bailly-extract-1"
    calls.append(
        make_call(
            tool="extract.bailly.json",
            call_id=bailly_extract_id,
            endpoint="internal://bailly/json_extract",
            params={"source_call_id": bailly_fetch_id},
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
            from_call_id=bailly_fetch_id,
            to_call_id=bailly_extract_id,
            rationale="Extract local Bailly JSON after fetch",
        )
    )
    bailly_derive_id = "bailly-derive-1"
    calls.append(
        make_call(
            tool="derive.bailly.entries",
            call_id=bailly_derive_id,
            endpoint="internal://bailly/entry_derive",
            params={"source_call_id": bailly_extract_id},
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
            from_call_id=bailly_extract_id,
            to_call_id=bailly_derive_id,
            rationale="Derive local Bailly entries",
        )
    )
    bailly_claim_id = "claim-bailly-1"
    calls.append(
        make_call(
            tool="claim.bailly.entries",
            call_id=bailly_claim_id,
            endpoint="internal://claim/bailly_entries",
            params={"source_call_id": bailly_derive_id},
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
            from_call_id=bailly_derive_id,
            to_call_id=bailly_claim_id,
            rationale="Produce local Bailly source gloss claims",
        )
    )


def append_strongs_greek_calls(
    calls: list[ToolCallSpec],
    deps: list[PlanDependency],
    *,
    headword: str,
    lemma: str,
    lemma_candidates: list[str] | None = None,
) -> None:
    """Append the staged local Strong's Greek source-gloss pipeline."""
    fetch_id = "strongs-greek-1"
    params = {
        "headword": headword,
        "lemma": lemma,
        "index_signature": _local_index_signature(default_strongs_greek_path()),
    }
    if lemma_candidates:
        params["lemma_candidates"] = ";".join(lemma_candidates)
    calls.append(
        make_call(
            tool="fetch.strongs_greek",
            call_id=fetch_id,
            endpoint="duckdb://strongs_greek",
            params=params,
            opts=opts(expected="json", priority=7, optional=True, stage=ToolStage.TOOL_STAGE_FETCH),
        )
    )
    extract_id = "strongs-greek-extract-1"
    calls.append(
        make_call(
            tool="extract.strongs_greek.json",
            call_id=extract_id,
            endpoint="internal://strongs_greek/json_extract",
            params={"source_call_id": fetch_id},
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
            from_call_id=fetch_id,
            to_call_id=extract_id,
            rationale="Extract local Strong's Greek JSON after fetch",
        )
    )
    derive_id = "strongs-greek-derive-1"
    calls.append(
        make_call(
            tool="derive.strongs_greek.entries",
            call_id=derive_id,
            endpoint="internal://strongs_greek/entry_derive",
            params={"source_call_id": extract_id},
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
            from_call_id=extract_id,
            to_call_id=derive_id,
            rationale="Derive local Strong's Greek entries",
        )
    )
    claim_id = "claim-strongs-greek-1"
    calls.append(
        make_call(
            tool="claim.strongs_greek.entries",
            call_id=claim_id,
            endpoint="internal://claim/strongs_greek_entries",
            params={"source_call_id": derive_id},
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
            from_call_id=derive_id,
            to_call_id=claim_id,
            rationale="Produce local Strong's Greek source gloss claims",
        )
    )
