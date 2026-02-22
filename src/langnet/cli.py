from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import TypedDict, cast
import logging

import click
import duckdb
import orjson
import query_spec
from returns.result import Failure, Success

from langnet.normalizer.service import DiogenesConfig, NormalizationService
from langnet.planner.core import PlannerConfig, ToolPlanner
from langnet.storage.effects_index import RawResponseIndex
from langnet.storage.paths import normalization_db_path
from langnet.execution.registry import default_registry
from langnet.execution.executor import execute_plan_staged
from langnet.storage.extraction_index import ExtractionIndex
from langnet.storage.derivation_index import DerivationIndex
from langnet.storage.claim_index import ClaimIndex
from langnet.storage.plan_index import PlanResponseIndex, apply_schema
from langnet.execution.clients import (
    CLTKFetchClient,
    StubToolClient,
    find_whitaker_binary,
    WhitakerFetchClient,
)
from langnet.clients.http import HttpToolClient

LanguageHint = query_spec.LanguageHint
LanguageValue = query_spec.LanguageHint.ValueType


def _ensure_logging(level: int = logging.INFO) -> None:
    """
    Initialize a basic logging configuration if none is set.
    """
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )


class CandidateView(TypedDict):
    lemma: str
    sources: list[str]
    encodings: dict[str, str]


class StepView(TypedDict):
    op: str
    input: str
    output: str
    tool: str


def _parse_language(lang: str) -> LanguageValue:
    normalized = lang.strip().lower()
    alias_map = {
        "san": LanguageHint.LANGUAGE_HINT_SAN,
        "skt": LanguageHint.LANGUAGE_HINT_SAN,
        "grc": LanguageHint.LANGUAGE_HINT_GRC,
        "el": LanguageHint.LANGUAGE_HINT_GRC,
        "lat": LanguageHint.LANGUAGE_HINT_LAT,
        "la": LanguageHint.LANGUAGE_HINT_LAT,
    }
    if normalized not in alias_map:
        raise click.BadParameter(f"Unsupported language '{lang}'. Use san|grc|lat.")
    return alias_map[normalized]


def _heritage_factory(base_url: str | None, tool_client=None):
    def factory():
        from langnet.heritage.client import HeritageHTTPClient  # noqa: PLC0415
        from langnet.heritage.config import HeritageConfig  # noqa: PLC0415

        if base_url:
            cfg = HeritageConfig(base_url=base_url, cgi_path="/cgi-bin/skt/")
            return HeritageHTTPClient(config=cfg, tool_client=tool_client)
        return HeritageHTTPClient(tool_client=tool_client)

    return factory


def _print_result(result, output: str) -> None:
    candidates = cast(
        list[CandidateView],
        [
            {"lemma": c.lemma, "sources": list(c.sources), "encodings": dict(c.encodings)}
            for c in result.normalized.candidates
        ],
    )
    steps = cast(
        list[StepView],
        [
            {"op": s.operation, "input": s.input, "output": s.output, "tool": s.tool}
            for s in result.normalized.normalizations
        ],
    )
    payload = {
        "query_hash": result.query_hash,
        "language": str(result.normalized.language).lower(),
        "original": result.normalized.original,
        "candidates": candidates,
        "steps": steps,
    }
    if output == "json":
        click.echo(orjson.dumps(payload, option=orjson.OPT_INDENT_2).decode("utf-8"))
        return

    click.echo(
        f"Query: {payload['original']} [{payload['language']}] (hash={payload['query_hash']})"
    )
    click.echo("Candidates:")
    for c in candidates:
        enc_strs = [f"{k}={v}" for k, v in sorted(c["encodings"].items())]
        enc_display = "  ".join(enc_strs) if enc_strs else ""
        click.echo(f"  - {c['lemma']}  sources={c['sources']}")
        if enc_display:
            click.echo(f"      {enc_display}")
    if steps:
        click.echo("Steps:")
        for s in steps:
            click.echo(f"  - {s['op']}: {s['input']} -> {s['output']} ({s['tool']})")


def _print_build_result(result) -> None:
    status = result.status.value if hasattr(result, "status") else "unknown"
    click.echo(f"status: {status}")
    click.echo(f"output: {result.output_path}")
    if result.message:
        click.echo(f"message: {result.message}")
    if result.stats:
        if isinstance(result.stats, Success):
            stats_val = result.stats.unwrap()
            stats_dict = asdict(stats_val) if is_dataclass(stats_val) else {"value": stats_val}
            for key, value in sorted(stats_dict.items()):
                click.echo(f"{key}: {value}")
        else:
            err = result.stats.failure() if isinstance(result.stats, Failure) else result.stats
            err_dict = asdict(err) if is_dataclass(err) else {"error": str(err)}
            click.echo("error stats:")
            for key, value in sorted(err_dict.items()):
                click.echo(f"{key}: {value}")


def _print_plan(plan, output: str) -> None:
    # Lazy import to avoid adding startup overhead to non-plan commands
    from google.protobuf.json_format import MessageToDict  # noqa: PLC0415

    query_dict = MessageToDict(plan.query, preserving_proto_field_name=True) if plan.query else None
    payload = {
        "plan_id": plan.plan_id,
        "plan_hash": plan.plan_hash,
        "query": query_dict,
        "created_at_unix_ms": plan.created_at_unix_ms,
        "tool_calls": [
            {
                "tool": c.tool,
                "call_id": c.call_id,
                "endpoint": c.endpoint,
                "params": c.params or {},
                "expected_response_type": c.expected_response_type,
                "priority": c.priority,
                "optional": c.optional,
                "stage": (c.params or {}).get("stage", ""),
            }
            for c in plan.tool_calls
        ],
        "dependencies": [
            {"from": d.from_call_id, "to": d.to_call_id, "why": d.rationale}
            for d in plan.dependencies
        ],
    }
    if output == "json":
        click.echo(orjson.dumps(payload, option=orjson.OPT_INDENT_2).decode("utf-8"))
        return

    query_info = payload.get("query")
    lang = "unknown"
    original = ""
    if isinstance(query_info, dict):
        lang = query_info.get("language", "unknown")
        original = query_info.get("original", "")
    click.echo(f"Plan: {payload['plan_id']} (hash={payload['plan_hash']})")
    click.echo(f"Query: {original} [{lang}]")
    click.echo("Tool calls:")
    tool_calls = payload.get("tool_calls")
    if isinstance(tool_calls, list):
        for call in tool_calls:
            if not isinstance(call, dict):
                continue
            stage_val = call.get("stage", "")
            stage = f"[{stage_val}]" if stage_val else ""
            click.echo(
                f"  - {stage} {call.get('tool', '')}#{call.get('call_id', '')} -> "
                f"{call.get('endpoint', '')}"
            )
            params = call.get("params") or {}
            if params:
                click.echo(f"      params={params}")
            click.echo(
                "      expects={} priority={} optional={}".format(
                    call.get("expected_response_type", ""),
                    call.get("priority", ""),
                    call.get("optional", ""),
                )
            )
    deps = payload.get("dependencies")
    if isinstance(deps, list) and deps:
        click.echo("Dependencies:")
        for dep in deps:
            if not isinstance(dep, dict):
                continue
            click.echo(f"  {dep.get('from')} -> {dep.get('to')}  ({dep.get('why')})")


@dataclass
class NormalizeConfig:
    diogenes_endpoint: str
    heritage_base: str
    db_path: str | None
    no_cache: bool
    output: str


@dataclass
class PlanCliConfig:
    diogenes_endpoint: str
    diogenes_parse_endpoint: str | None
    heritage_base: str
    heritage_max_results: int
    db_path: str | None
    no_cache: bool
    output: str
    include_whitakers: bool
    max_candidates: int
    use_stub_handlers: bool


@dataclass
class PlanExecConfig:
    diogenes_endpoint: str
    diogenes_parse_endpoint: str | None
    heritage_base: str
    heritage_max_results: int
    db_path: str | None
    no_cache: bool
    include_whitakers: bool
    max_candidates: int
    use_stub_handlers: bool


def _create_normalization_service(config: NormalizeConfig) -> NormalizationService:
    path = Path(config.db_path).expanduser() if config.db_path else normalization_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(database=str(path))
    dio_config = DiogenesConfig(endpoint=config.diogenes_endpoint)

    # Create effects index to capture raw responses
    effects_index = RawResponseIndex(conn)

    def _whitaker_factory():
        from langnet.whitakers.client import WhitakerClient  # noqa: PLC0415

        return WhitakerClient()

    return NormalizationService(
        conn,
        heritage_client=None,  # Will be created with capturing in _ensure_normalizer
        diogenes_config=dio_config,
        whitaker_client=_whitaker_factory,  # type: ignore[arg-type]
        use_cache=not config.no_cache,
        effects_index=effects_index,
    )


def _normalize_impl(config: NormalizeConfig, language: str, text: str) -> None:
    lang_hint = _parse_language(language)
    service = _create_normalization_service(config)
    result = service.normalize(text, lang_hint)
    _print_result(result, config.output)


def _plan_impl(config: PlanCliConfig, language: str, text: str) -> None:
    lang_hint = _parse_language(language)
    norm_config = NormalizeConfig(
        diogenes_endpoint=config.diogenes_endpoint,
        heritage_base=config.heritage_base,
        db_path=config.db_path,
        no_cache=config.no_cache,
        output=config.output,
    )
    service = _create_normalization_service(norm_config)
    normalized = service.normalize(text, lang_hint)

    planner = ToolPlanner(
        PlannerConfig(
            diogenes_endpoint=config.diogenes_endpoint,
            diogenes_parse_endpoint=config.diogenes_parse_endpoint,
            heritage_base_url=config.heritage_base,
            heritage_max_results=config.heritage_max_results,
            include_whitakers=config.include_whitakers,
            max_candidates=config.max_candidates,
        )
    )
    candidate = planner.select_candidate(normalized.normalized)
    plan = planner.build(normalized.normalized, candidate)
    _print_plan(plan, config.output)


@dataclass
class BuildCtsConfig:
    perseus_dir: str
    phi_cdrom_dir: str
    output: str | None
    include_packard: bool
    wipe: bool
    force: bool
    max_works: int | None


def _build_cts_impl(config: BuildCtsConfig) -> None:
    _ensure_logging()
    from langnet.databuild.cts import CtsBuildConfig, CtsUrnBuilder  # noqa: PLC0415
    from langnet.databuild.paths import default_cts_path  # noqa: PLC0415

    output_path = Path(config.output).expanduser() if config.output else default_cts_path()
    cts_config = CtsBuildConfig(
        perseus_dir=Path(config.perseus_dir).expanduser(),
        phi_cdrom_dir=Path(config.phi_cdrom_dir).expanduser(),
        output_path=output_path,
        include_packard=config.include_packard,
        wipe_existing=config.wipe,
        force_rebuild=config.force,
        max_works=config.max_works,
    )
    builder = CtsUrnBuilder(cts_config)
    result = builder.build()
    _print_build_result(result)


@dataclass
class BuildCdslConfig:
    dict_id: str
    source_dir: str
    output: str | None
    limit: int | None
    batch_size: int
    wipe: bool
    force: bool


def _build_cdsl_impl(config: BuildCdslConfig) -> None:
    _ensure_logging()
    from langnet.databuild.cdsl import CdslBuildConfig, CdslBuilder  # noqa: PLC0415
    from langnet.databuild.paths import default_cdsl_path  # noqa: PLC0415

    output_path = (
        Path(config.output).expanduser() if config.output else default_cdsl_path(config.dict_id)
    )
    builder_config = CdslBuildConfig(
        dict_id=config.dict_id,
        source_dir=Path(config.source_dir).expanduser(),
        output_path=output_path,
        limit=config.limit,
        batch_size=config.batch_size,
        wipe_existing=config.wipe,
        force_rebuild=config.force,
    )
    builder = CdslBuilder(builder_config)
    result = builder.build()
    _print_build_result(result)


@click.group()
def main() -> None:
    """langnet-cli — classical language tools."""


@main.command()
@click.argument("language")
@click.argument("text")
@click.option(
    "--diogenes-endpoint",
    default="http://localhost:8888/Diogenes.cgi",
    show_default=True,
    help="Diogenes CGI endpoint.",
)
@click.option(
    "--heritage-base",
    default="http://localhost:48080",
    show_default=True,
    help="Base URL for Heritage Platform (CGI path is appended automatically).",
)
@click.option(
    "--db-path",
    type=click.Path(),
    help="Path to persistent DuckDB cache for normalization (defaults to data/cache/langnet.duckdb).",
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Skip normalization cache lookups and writes for this invocation.",
)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
def normalize(  # noqa: PLR0913
    language: str,
    text: str,
    diogenes_endpoint: str,
    heritage_base: str,
    db_path: str | None,
    no_cache: bool,
    output: str,
):
    """
    Normalize a query and show canonical candidates from authoritative backends.

    Examples:
      langnet-cli normalize san shiva
      langnet-cli normalize grc λόγος
      langnet-cli normalize lat lupus
    """
    config = NormalizeConfig(
        diogenes_endpoint=diogenes_endpoint,
        heritage_base=heritage_base,
        db_path=db_path,
        no_cache=no_cache,
        output=output,
    )
    _normalize_impl(config, language, text)


@main.command()
@click.argument("language")
@click.argument("text")
@click.option(
    "--diogenes-endpoint",
    default="http://localhost:8888/Diogenes.cgi",
    show_default=True,
    help="Diogenes CGI endpoint for planning.",
)
@click.option(
    "--diogenes-parse-endpoint",
    help="Alternate Diogenes parse endpoint (defaults to diogenes-endpoint).",
)
@click.option(
    "--heritage-base",
    default="http://localhost:48080",
    show_default=True,
    help="Base URL for Heritage Platform (CGI path is appended automatically).",
)
@click.option(
    "--heritage-max-results",
    type=int,
    default=5,
    show_default=True,
    help="Max results to request from Heritage sktreader.",
)
@click.option(
    "--db-path",
    type=click.Path(),
    help="Path to persistent DuckDB cache for normalization (defaults to data/langnet.duckdb).",
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Skip normalization cache lookups and writes for this invocation.",
)
@click.option(
    "--include-whitakers/--no-whitakers",
    default=True,
    show_default=True,
    help="Include Whitaker's Words in the generated plan (Latin).",
)
@click.option(
    "--max-candidates",
    type=int,
    default=3,
    show_default=True,
    help="Max canonical candidates to include when building tool plans.",
)
@click.option(
    "--use-stub-handlers/--no-stub-handlers",
    default=False,
    show_default=True,
    help="Use stub handlers for tools without real implementations.",
)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
def plan(  # noqa: PLR0913
    language: str,
    text: str,
    diogenes_endpoint: str,
    diogenes_parse_endpoint: str | None,
    heritage_base: str,
    heritage_max_results: int,
    db_path: str | None,
    no_cache: bool,
    include_whitakers: bool,
    max_candidates: int,
    use_stub_handlers: bool,
    output: str,
):
    """
    Normalize a query and emit the ToolPlan that would be executed for the query.
    """
    config = PlanCliConfig(
        diogenes_endpoint=diogenes_endpoint,
        diogenes_parse_endpoint=diogenes_parse_endpoint,
        heritage_base=heritage_base,
        heritage_max_results=heritage_max_results,
        db_path=db_path,
        no_cache=no_cache,
        output=output,
        include_whitakers=include_whitakers,
        max_candidates=max_candidates,
        use_stub_handlers=use_stub_handlers,
    )
    _plan_impl(config, language, text)


@main.group()
def databuild():
    """Offline data/index builders."""


@databuild.command("cts")
@click.option(
    "--perseus-dir",
    type=click.Path(),
    default=str(Path.home() / "perseus"),
    show_default=True,
    help="Perseus corpus root (expects canonical-latinLit and canonical-greekLit).",
)
@click.option(
    "--phi-cdrom-dir",
    type=click.Path(),
    default=str(Path.home() / "Classics-Data"),
    show_default=True,
    help="Packard PHI/TLG corpus root (authtab/idt).",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output DuckDB path (defaults to data/build/cts_urn.duckdb)",
)
@click.option(
    "--include-packard/--no-packard",
    default=True,
    show_default=True,
    help="Include Packard PHI/TLG authtab/idt data when available.",
)
@click.option(
    "--wipe/--no-wipe", default=True, show_default=True, help="Delete existing DB before building."
)
@click.option("--force", is_flag=True, help="Rebuild even if output exists without wiping.")
@click.option("--max-works", type=int, help="Limit number of works ingested (sampling/debug).")
def build_cts(  # noqa: PLR0913
    perseus_dir: str,
    phi_cdrom_dir: str,
    output: str | None,
    include_packard: bool,
    wipe: bool,
    force: bool,
    max_works: int | None,
):
    """Build CTS URN index (Perseus + Packard/legacy)."""
    config = BuildCtsConfig(
        perseus_dir=perseus_dir,
        phi_cdrom_dir=phi_cdrom_dir,
        output=output,
        include_packard=include_packard,
        wipe=wipe,
        force=force,
        max_works=max_works,
    )
    _build_cts_impl(config)


@databuild.command("cdsl")
@click.argument("dict_id")
@click.option(
    "--source-dir",
    type=click.Path(),
    default=str(Path.home() / "cdsl_data" / "dict"),
    show_default=True,
    help=(
        "CDSL dictionary root containing subdirectories per dictionary (with web/sqlite/*.sqlite)."
    ),
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output DuckDB path (defaults to data/build/cdsl_<dict>.duckdb)",
)
@click.option("--limit", type=int, help="Limit rows for testing.")
@click.option(
    "--batch-size",
    type=int,
    default=1000,
    show_default=True,
    help="Rows per batch while inserting.",
)
@click.option(
    "--wipe/--no-wipe", default=True, show_default=True, help="Delete existing DB before building."
)
@click.option("--force", is_flag=True, help="Rebuild even if output exists without wiping.")
def build_cdsl(  # noqa: PLR0913
    dict_id: str,
    source_dir: str,
    output: str | None,
    limit: int | None,
    batch_size: int,
    wipe: bool,
    force: bool,
):
    """Build CDSL dictionary index for a specific dictionary id (e.g., MW, AP90)."""
    config = BuildCdslConfig(
        dict_id=dict_id,
        source_dir=source_dir,
        output=output,
        limit=limit,
        batch_size=batch_size,
        wipe=wipe,
        force=force,
    )
    _build_cdsl_impl(config)


def _build_exec_clients(plan, diogenes_endpoint: str, use_stubs: bool) -> dict[str, object]:
    clients: dict[str, object] = {}
    for call in plan.tool_calls:
        tool = call.tool
        if tool == "fetch.diogenes":
            if tool not in clients:
                clients[tool] = HttpToolClient(tool="fetch.diogenes")
        elif tool == "fetch.whitakers":
            if tool not in clients:
                binary = find_whitaker_binary()
                if binary:
                    clients[tool] = WhitakerFetchClient(binary)
                elif use_stubs:
                    clients[tool] = StubToolClient(tool)
        elif tool == "fetch.cltk":
            if tool not in clients:
                try:
                    clients[tool] = CLTKFetchClient()
                except Exception:
                    if use_stubs:
                        clients[tool] = StubToolClient(tool)
        elif tool.startswith("fetch.") and use_stubs:
            clients.setdefault(tool, StubToolClient(tool))
    return clients


def _plan_exec_impl(config: PlanExecConfig, language: str, text: str) -> None:
    lang_hint = _parse_language(language)

    norm_cfg = NormalizeConfig(
        diogenes_endpoint=config.diogenes_endpoint,
        heritage_base=config.heritage_base,
        db_path=config.db_path,
        no_cache=config.no_cache,
        output="pretty",
    )
    service = _create_normalization_service(norm_cfg)
    normalized = service.normalize(text, lang_hint)

    planner = ToolPlanner(
        PlannerConfig(
            diogenes_endpoint=config.diogenes_endpoint,
            diogenes_parse_endpoint=config.diogenes_parse_endpoint,
            heritage_base_url=config.heritage_base,
            heritage_max_results=config.heritage_max_results,
            include_whitakers=config.include_whitakers,
            max_candidates=config.max_candidates,
        )
    )
    candidate = planner.select_candidate(normalized.normalized)
    plan = planner.build(normalized.normalized, candidate)

    # Shared DuckDB cache
    db_path = Path(config.db_path).expanduser() if config.db_path else normalization_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(database=str(db_path))
    apply_schema(conn)

    raw_index = RawResponseIndex(conn)
    extraction_index = ExtractionIndex(conn)
    derivation_index = DerivationIndex(conn)
    claim_index = ClaimIndex(conn)
    plan_response_index = PlanResponseIndex(conn)

    registry = default_registry(use_stubs=config.use_stub_handlers)
    clients = _build_exec_clients(plan, config.diogenes_endpoint, config.use_stub_handlers)

    result = execute_plan_staged(
        plan=plan,
        clients=clients,
        registry=registry,
        raw_index=raw_index,
        extraction_index=extraction_index,
        derivation_index=derivation_index,
        claim_index=claim_index,
        plan_response_index=plan_response_index,
        allow_cache=not config.no_cache,
    )

    _print_plan(plan, "pretty")
    click.echo(
        f"counts: raw={len(result.raw_effects)} extractions={len(result.extractions)} "
        f"derivations={len(result.derivations)} claims={len(result.claims)} cache_hit={result.from_cache}"
    )
    if result.claims:
        click.echo("Claims:")
        for c in result.claims:
            click.echo(f"  - {c.predicate} subject={c.subject} value={c.value}")


@main.command("plan-exec")
@click.argument("language")
@click.argument("text")
@click.option(
    "--diogenes-endpoint",
    default="http://localhost:8888/Diogenes.cgi",
    show_default=True,
    help="Diogenes CGI endpoint for planning/execution.",
)
@click.option(
    "--diogenes-parse-endpoint",
    help="Alternate Diogenes parse endpoint (defaults to diogenes-endpoint).",
)
@click.option(
    "--heritage-base",
    default="http://localhost:48080",
    show_default=True,
    help="Base URL for Heritage Platform (CGI path is appended automatically).",
)
@click.option(
    "--heritage-max-results",
    type=int,
    default=5,
    show_default=True,
    help="Max results to request from Heritage sktreader.",
)
@click.option(
    "--db-path",
    type=click.Path(),
    help="Path to persistent DuckDB cache (defaults to data/cache/langnet.duckdb).",
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Skip cache lookups and writes for this invocation.",
)
@click.option(
    "--include-whitakers/--no-whitakers",
    default=True,
    show_default=True,
    help="Include Whitaker's Words in the generated plan (Latin).",
)
@click.option(
    "--max-candidates",
    type=int,
    default=3,
    show_default=True,
    help="Max canonical candidates to include when building tool plans.",
)
@click.option(
    "--use-stub-handlers/--no-stub-handlers",
    default=True,
    show_default=True,
    help="Use stub handlers for tools without real implementations.",
)
def plan_exec(  # noqa: PLR0913
    language: str,
    text: str,
    diogenes_endpoint: str,
    diogenes_parse_endpoint: str | None,
    heritage_base: str,
    heritage_max_results: int,
    db_path: str | None,
    no_cache: bool,
    include_whitakers: bool,
    max_candidates: int,
    use_stub_handlers: bool,
):
    """
    Normalize → plan → execute ToolPlan → emit claim summary.
    """
    config = PlanExecConfig(
        diogenes_endpoint=diogenes_endpoint,
        diogenes_parse_endpoint=diogenes_parse_endpoint,
        heritage_base=heritage_base,
        heritage_max_results=heritage_max_results,
        db_path=db_path,
        no_cache=no_cache,
        include_whitakers=include_whitakers,
        max_candidates=max_candidates,
        use_stub_handlers=use_stub_handlers,
    )
    _plan_exec_impl(config, language, text)


if __name__ == "__main__":
    main()
