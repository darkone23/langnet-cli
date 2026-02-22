import duckdb
import sys
import structlog
from query_spec import LanguageHint
from langnet.cli import _create_normalization_service, _build_exec_clients, NormalizeConfig
from langnet.execution.executor import execute_plan_staged
from langnet.execution.registry import default_registry
from langnet.logging import setup_logging
from langnet.planner.core import PlannerConfig, ToolPlanner
from langnet.storage.claim_index import ClaimIndex
from langnet.storage.derivation_index import DerivationIndex
from langnet.storage.effects_index import RawResponseIndex
from langnet.storage.extraction_index import ExtractionIndex
from langnet.storage.plan_index import PlanResponseIndex, apply_schema


def _parse_language(lang: str) -> LanguageHint.ValueType:
    lang_l = lang.lower()
    if lang_l in {"lat", "la", "latin"}:
        return LanguageHint.LANGUAGE_HINT_LAT
    if lang_l in {"grc", "el", "greek"}:
        return LanguageHint.LANGUAGE_HINT_GRC
    if lang_l in {"san", "sa", "sanskrit"}:
        return LanguageHint.LANGUAGE_HINT_SAN
    return LanguageHint.LANGUAGE_HINT_LAT


def run(lang_code: str, word: str, tool_filter: str) -> None:
    setup_logging()
    log = structlog.get_logger("triples_dump")
    include_cltk = False
    lang_hint = _parse_language(lang_code)
    norm_cfg = NormalizeConfig(
        diogenes_endpoint="http://localhost:8888/Diogenes.cgi",
        heritage_base="http://localhost:48080",
        db_path=None,
        no_cache=True,
        output="pretty",
    )
    service = _create_normalization_service(norm_cfg)
    normalized = service.normalize(word, lang_hint)
    planner = ToolPlanner(
        PlannerConfig(
            diogenes_endpoint=norm_cfg.diogenes_endpoint,
            diogenes_parse_endpoint=None,
            heritage_base_url=norm_cfg.heritage_base,
            heritage_max_results=5,
            include_whitakers=lang_hint == LanguageHint.LANGUAGE_HINT_LAT,
            include_cltk=include_cltk and lang_hint in {LanguageHint.LANGUAGE_HINT_LAT, LanguageHint.LANGUAGE_HINT_GRC},
            max_candidates=3,
        )
    )
    candidate = planner.select_candidate(normalized.normalized)
    plan = planner.build(normalized.normalized, candidate)
    log.info(
        "plan.built",
        tool_count=len(plan.tool_calls),
        deps=len(plan.dependencies),
        include_cltk=include_cltk,
        filter=tool_filter,
        language=str(lang_hint),
    )
    if tool_filter and tool_filter.lower() != "all":
        filtered_calls = [c for c in plan.tool_calls if c.tool.startswith(tool_filter)]
        if not filtered_calls:
            print(f"No tool calls match filter '{tool_filter}'. Available: {[c.tool for c in plan.tool_calls]}")
            return
        kept_ids = {c.call_id for c in filtered_calls}
        filtered_deps = [d for d in plan.dependencies if d.from_call_id in kept_ids and d.to_call_id in kept_ids]
        plan.ClearField("tool_calls")
        plan.ClearField("dependencies")
        plan.tool_calls.extend(filtered_calls)
        plan.dependencies.extend(filtered_deps)
        log.info("plan.filtered", tool_count=len(plan.tool_calls), deps=len(plan.dependencies))

    conn = duckdb.connect(database=":memory:")
    apply_schema(conn)
    raw_index = RawResponseIndex(conn)
    extraction_index = ExtractionIndex(conn)
    derivation_index = DerivationIndex(conn)
    claim_index = ClaimIndex(conn)
    plan_response_index = PlanResponseIndex(conn)
    registry = default_registry(use_stubs=False)
    clients = _build_exec_clients(plan, norm_cfg.diogenes_endpoint, use_stubs=False)
    log.info("execute.start", calls=[c.tool for c in plan.tool_calls])
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
    log.info(
        "execute.done",
        raw=len(result.raw_effects),
        extracts=len(result.extractions),
        derivations=len(result.derivations),
        claims=len(result.claims),
        cache_hit=result.from_cache,
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
    lang = sys.argv[1] if len(sys.argv) > 1 else "lat"
    word = sys.argv[2] if len(sys.argv) > 2 else "lupus"
    tool = sys.argv[3] if len(sys.argv) > 3 else "all"
    run(lang, word, tool)
