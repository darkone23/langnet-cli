import duckdb
import sys
from query_spec import LanguageHint
from langnet.cli import _create_normalization_service, _build_exec_clients, NormalizeConfig
from langnet.planner.core import PlannerConfig, ToolPlanner
from langnet.execution.executor import execute_plan_staged
from langnet.execution.registry import default_registry
from langnet.storage.effects_index import RawResponseIndex
from langnet.storage.extraction_index import ExtractionIndex
from langnet.storage.derivation_index import DerivationIndex
from langnet.storage.claim_index import ClaimIndex
from langnet.storage.plan_index import PlanResponseIndex, apply_schema


def run(tool_filter: str, word: str) -> None:
    norm_cfg = NormalizeConfig(
        diogenes_endpoint="http://localhost:8888/Diogenes.cgi",
        heritage_base="http://localhost:48080",
        db_path=None,
        no_cache=True,
        output="pretty",
    )
    service = _create_normalization_service(norm_cfg)
    normalized = service.normalize(word, LanguageHint.LANGUAGE_HINT_LAT)
    planner = ToolPlanner(
        PlannerConfig(
            diogenes_endpoint=norm_cfg.diogenes_endpoint,
            diogenes_parse_endpoint=None,
            heritage_base_url=norm_cfg.heritage_base,
            heritage_max_results=5,
            include_whitakers=True,
            max_candidates=3,
        )
    )
    candidate = planner.select_candidate(normalized.normalized)
    plan = planner.build(normalized.normalized, candidate)
    if tool_filter and tool_filter.lower() != "all":
        filtered_calls = [c for c in plan.tool_calls if c.tool.startswith(tool_filter)]
        if not filtered_calls:
            print(f"No tool calls match filter '{tool_filter}'. Available: {[c.tool for c in plan.tool_calls]}")
            return
        plan.tool_calls[:] = filtered_calls
        kept_ids = {c.call_id for c in plan.tool_calls}
        plan.dependencies[:] = [d for d in plan.dependencies if d.from_call_id in kept_ids and d.to_call_id in kept_ids]

    conn = duckdb.connect(database=":memory:")
    apply_schema(conn)
    raw_index = RawResponseIndex(conn)
    extraction_index = ExtractionIndex(conn)
    derivation_index = DerivationIndex(conn)
    claim_index = ClaimIndex(conn)
    plan_response_index = PlanResponseIndex(conn)
    registry = default_registry(use_stubs=False)
    clients = _build_exec_clients(plan, norm_cfg.diogenes_endpoint, use_stubs=False)
    result = execute_plan_staged(
        plan=plan,
        clients=clients,
        registry=registry,
        raw_index=raw_index,
        extraction_index=extraction_index,
        derivation_index=derivation_index,
        claim_index=claim_index,
        plan_response_index=plan_response_index,
        allow_cache=False,
    )
    for claim in result.claims:
        print(f"TOOL={claim.tool} PRED={claim.predicate} SUBJECT={claim.subject}")
        val = claim.value if isinstance(claim.value, dict) else {}
        triples = val.get("triples") if isinstance(val, dict) else None
        if triples:
            for t in triples[:10]:
                print("  triple", t)
        if "raw_text" in val:
            print("  raw_text_len", len(val["raw_text"]))
        if "raw_html" in val:
            print("  raw_html_len", len(val["raw_html"]))


if __name__ == "__main__":
    tool = sys.argv[1] if len(sys.argv) > 1 else "all"
    word = sys.argv[2] if len(sys.argv) > 2 else "lupus"
    run(tool, word)
