import os
import sys
import time

import duckdb
import orjson
import structlog
from query_spec import LanguageHint, NormalizedQuery

from langnet.cli import NormalizeConfig, _build_exec_clients, _create_normalization_service
from langnet.execution.executor import execute_plan_staged
from langnet.execution.registry import default_registry
from langnet.logging import setup_logging
from langnet.planner.core import PlannerConfig, ToolPlanner
from langnet.storage.claim_index import ClaimIndex
from langnet.storage.db import connect_duckdb
from langnet.storage.derivation_index import DerivationIndex
from langnet.storage.effects_index import RawResponseIndex
from langnet.storage.extraction_index import ExtractionIndex
from langnet.storage.paths import normalization_db_path
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


def _normalize_word(
    word: str, lang_hint, norm_cfg: NormalizeConfig, use_normalizer: bool, log
) -> NormalizedQuery | None:
    """Normalize the input word if requested."""
    norm_path = normalization_db_path()
    norm_path.parent.mkdir(parents=True, exist_ok=True)
    use_memory = not norm_path.exists()
    norm_start = time.time()

    if use_normalizer:
        if use_memory:
            with duckdb.connect(database=":memory:") as norm_conn:
                service = _create_normalization_service(norm_cfg, norm_conn, read_only=False)
                result = service.normalize(word, lang_hint)
        else:
            with connect_duckdb(norm_path, read_only=True, lock=False) as norm_conn:
                service = _create_normalization_service(norm_cfg, norm_conn, read_only=True)
                result = service.normalize(word, lang_hint)
        normalized_str = (
            result.normalized.original if hasattr(result.normalized, "original") else word
        )
        log.info(
            "timing.normalize_ms",
            duration_ms=int((time.time() - norm_start) * 1000),
            normalized=normalized_str,
        )
        return result.normalized

    log.info("normalize.skipped", duration_ms=int((time.time() - norm_start) * 1000))
    return None


def _filter_plan_by_tool(plan, tool_filter: str, log) -> bool:
    """Filter plan to only include matching tools. Returns False if no matches."""
    lf = tool_filter.lower()

    def _matches_tool(tool_name: str) -> bool:
        """Match full prefix (fetch.diogenes) or tool family (diogenes)."""
        t = tool_name.lower()
        if t.startswith(lf):
            return True
        _, _, rest = t.partition(".")
        return bool(rest) and rest.startswith(lf)

    filtered_calls = [c for c in plan.tool_calls if _matches_tool(c.tool)]
    if not filtered_calls:
        available = [c.tool for c in plan.tool_calls]
        print(f"No tool calls match filter '{tool_filter}'. Available: {available}")
        return False

    kept_ids = {c.call_id for c in filtered_calls}
    filtered_deps = [
        d for d in plan.dependencies if d.from_call_id in kept_ids and d.to_call_id in kept_ids
    ]
    plan.ClearField("tool_calls")
    plan.ClearField("dependencies")
    plan.tool_calls.extend(filtered_calls)
    plan.dependencies.extend(filtered_deps)
    log.info("plan.filtered", tool_count=len(plan.tool_calls), deps=len(plan.dependencies))
    return True


def _display_claim(claim, show_parsed: bool) -> None:
    """Display a single claim with its triples and metadata."""
    print(f"TOOL={claim.tool} PRED={claim.predicate} SUBJECT={claim.subject}")
    val = claim.value if isinstance(claim.value, dict) else {}
    triples = val.get("triples") if isinstance(val, dict) else None

    if show_parsed and "parsed" in val:
        print(
            "  parsed",
            orjson.dumps(val["parsed"], option=orjson.OPT_INDENT_2).decode("utf-8"),
        )

    if triples:
        sense_counts: dict[str, int] = {}
        for t in triples:
            if isinstance(t, dict) and t.get("predicate") == "has_sense":
                subj = t.get("subject")
                if isinstance(subj, str):
                    sense_counts[subj] = sense_counts.get(subj, 0) + 1
        if sense_counts:
            print("  sense_counts", sense_counts)
        for t in triples[:10]:
            print("  triple", t)

    if "raw_text" in val:
        print("  raw_text_len", len(val["raw_text"]))
    if "raw_html" in val:
        print("  raw_html_len", len(val["raw_html"]))


def _display_results(result, log, overall_start: float) -> None:
    """Display execution results and triples."""
    log.info(
        "timing.total_ms",
        duration_ms=int((time.time() - overall_start) * 1000),
        tool_count=len(result.plan.tool_calls),
    )
    log.info(
        "execute.done",
        raw=len(result.raw_effects),
        extracts=len(result.extractions),
        derivations=len(result.derivations),
        claims=len(result.claims),
        cache_hit=result.from_cache,
    )
    show_parsed = bool(os.environ.get("SHOW_PARSED"))
    for claim in result.claims:
        _display_claim(claim, show_parsed)


def run(lang_code: str, word: str, tool_filter: str, use_normalizer: bool = True) -> None:
    """Run the triples dump workflow for a given word."""
    setup_logging()
    log = structlog.get_logger("triples_dump")
    overall_start = time.time()
    include_cltk = False
    lang_hint = _parse_language(lang_code)
    norm_cfg = NormalizeConfig(
        diogenes_endpoint="http://localhost:8888/Diogenes.cgi",
        heritage_base="http://localhost:48080",
        db_path=None,
        no_cache=True,
        output="pretty",
    )

    normalized = _normalize_word(word, lang_hint, norm_cfg, use_normalizer, log)
    planner = ToolPlanner(
        PlannerConfig(
            diogenes_endpoint=norm_cfg.diogenes_endpoint,
            diogenes_parse_endpoint=None,
            heritage_base_url=norm_cfg.heritage_base,
            heritage_max_results=5,
            include_whitakers=lang_hint == LanguageHint.LANGUAGE_HINT_LAT,
            include_cltk=include_cltk
            and lang_hint in {LanguageHint.LANGUAGE_HINT_LAT, LanguageHint.LANGUAGE_HINT_GRC},
            max_candidates=3,
        )
    )
    query_value: NormalizedQuery
    if use_normalizer and normalized:
        query_value = normalized
    else:
        # Create a simple NormalizedQuery from the raw word
        query_value = NormalizedQuery(
            original=word,
            language=lang_hint,
            candidates=[],
        )
    candidate = planner.select_candidate(query_value)
    plan = planner.build(query_value, candidate)
    log.info(
        "plan.built",
        tool_count=len(plan.tool_calls),
        deps=len(plan.dependencies),
        include_cltk=include_cltk,
        filter=tool_filter,
        language=str(lang_hint),
    )

    if (
        tool_filter
        and tool_filter.lower() != "all"
        and not _filter_plan_by_tool(plan, tool_filter, log)
    ):
        return

    with duckdb.connect(database=":memory:") as conn:
        apply_schema(conn)
        raw_index = RawResponseIndex(conn)
        extraction_index = ExtractionIndex(conn)
        derivation_index = DerivationIndex(conn)
        claim_index = ClaimIndex(conn)
        plan_response_index = PlanResponseIndex(conn)
        registry = default_registry(use_stubs=False)

        client_start = time.time()
        clients = _build_exec_clients(plan, norm_cfg.diogenes_endpoint, use_stubs=False)
        log.info("timing.build_clients_ms", duration_ms=int((time.time() - client_start) * 1000))
        log.info("execute.start", calls=[c.tool for c in plan.tool_calls])

        exec_start = time.time()
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
            "timing.execute_ms",
            duration_ms=int((time.time() - exec_start) * 1000),
            calls=[c.tool for c in plan.tool_calls],
        )

    _display_results(result, log, overall_start)


if __name__ == "__main__":
    lang = sys.argv[1] if len(sys.argv) > 1 else "lat"
    word = sys.argv[2] if len(sys.argv) > 2 else "lupus"  # noqa: PLR2004
    tool = sys.argv[3] if len(sys.argv) > 3 else "all"  # noqa: PLR2004
    extra_args = sys.argv[4:]
    if "--no-normalize" in extra_args:
        use_norm = False
    elif "--normalize" in extra_args:
        use_norm = True
    else:
        use_norm = True
    run(lang, word, tool, use_normalizer=use_norm)
