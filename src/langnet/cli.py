from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import TypedDict, cast

import click
import duckdb
import humanize
import orjson
import query_spec
import requests
from query_spec import ToolCallSpec
from returns.result import Failure, Success

from langnet.clients.base import ToolClient
from langnet.clients.http import HttpToolClient
from langnet.execution.clients import (
    StubToolClient,
    WhitakerFetchClient,
    find_whitaker_binary,
    get_cltk_fetch_client,
    get_spacy_fetch_client,
)
from langnet.execution.executor import execute_plan_staged
from langnet.execution.handlers import cdsl as cdsl_handlers
from langnet.execution.handlers import heritage as heritage_handlers
from langnet.execution.handlers.diogenes import _parse_diogenes_html
from langnet.execution.handlers.whitakers import _parse_whitaker_output
from langnet.execution.registry import default_registry
from langnet.heritage.velthuis_converter import to_heritage_velthuis
from langnet.normalizer.service import DiogenesConfig, NormalizationService
from langnet.normalizer.utils import strip_accents
from langnet.parsing.integration import enrich_cltk_with_parsed_lewis
from langnet.planner.core import PlannerConfig, ToolPlanner
from langnet.storage.claim_index import ClaimIndex
from langnet.storage.db import connect_duckdb
from langnet.storage.derivation_index import DerivationIndex
from langnet.storage.effects_index import RawResponseIndex
from langnet.storage.extraction_index import ExtractionIndex
from langnet.storage.paths import all_db_paths, normalization_db_path
from langnet.storage.plan_index import PlanResponseIndex, apply_schema

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
                "params": dict(c.params or {}),
                "expected_response_type": c.expected_response_type,
                "priority": c.priority,
                "optional": c.optional,
                "stage": dict(c.params or {}).get("stage", ""),
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


def _create_normalization_service(
    config: NormalizeConfig, conn: duckdb.DuckDBPyConnection, *, read_only: bool = False
) -> NormalizationService:
    dio_config = DiogenesConfig(endpoint=config.diogenes_endpoint)

    # Create effects index to capture raw responses when we are allowed to write
    effects_index = None if read_only else RawResponseIndex(conn)

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
        read_only=read_only,
    )


def _norm_text_for_compare(s: str) -> str:
    """Normalize text for comparison (remove accents, fold omega/w, keep only letters)."""
    normalized = strip_accents(s).lower()
    normalized = normalized.replace("ω", "ο").replace("w", "o")
    normalized = re.sub(r"[^a-z]+", "", normalized)
    return normalized or s


def _levenshtein_distance(a: str, b: str) -> int:
    """Calculate Levenshtein distance between two strings."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i]
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            curr.append(min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost))
        prev = curr
    return prev[-1]


def _pick_best_normalization_candidate(normalized, raw_text: str) -> str:
    """Select best candidate from normalized results using Levenshtein distance and frequency."""
    try:
        candidates = getattr(normalized.normalized, "candidates", []) or []
        if candidates:
            raw_norm = _norm_text_for_compare(raw_text)

            def _score(cand) -> tuple[int, int]:
                enc = getattr(cand, "encodings", {}) or {}
                freq = enc.get("freq")
                freq_int = -1
                if freq is not None:
                    try:
                        freq_int = int(freq)
                    except (ValueError, TypeError):
                        freq_int = -1
                lemma = getattr(cand, "lemma", "") or ""
                cand_norm = _norm_text_for_compare(enc.get("betacode", "") or lemma)
                dist = _levenshtein_distance(raw_norm, cand_norm)
                return (dist, -freq_int)

            best = min(candidates, key=_score)
            lemma = getattr(best, "lemma", None)
            if isinstance(lemma, str) and lemma:
                return lemma
            lemma0 = getattr(candidates[0], "lemma", None)
            if isinstance(lemma0, str) and lemma0:
                return lemma0
        original = getattr(normalized.normalized, "original", None)
        if isinstance(original, str) and original:
            return original
    except Exception:
        pass
    return raw_text


def _normalize_word_for_tool(
    language: str, text: str, config: NormalizeConfig, *, use_cache: bool = True
) -> str:
    """
    Run the normalizer and return the best candidate lemma/text for downstream tool calls.
    """
    lang_hint = _parse_language(language)
    path = Path(config.db_path).expanduser() if config.db_path else normalization_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    use_memory = config.no_cache or not use_cache or not path.exists()

    if use_memory:
        with duckdb.connect(database=":memory:") as conn:
            service = _create_normalization_service(config, conn, read_only=False)
            normalized = service.normalize(text, lang_hint)
            return _pick_best_normalization_candidate(normalized, text)
    read_only = config.no_cache
    with connect_duckdb(path, read_only=read_only, lock=not read_only) as conn:
        service = _create_normalization_service(config, conn, read_only=read_only)
        normalized = service.normalize(text, lang_hint)
        return _pick_best_normalization_candidate(normalized, text)


def _diogenes_query_url(base: str, lang: str, word: str) -> str:
    """
    Build a diogenes parse URL with raw Unicode query (avoid percent-encoding Greek).
    """
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}do=parse&lang={lang}&q={word}"


def _normalize_impl(config: NormalizeConfig, language: str, text: str) -> None:
    lang_hint = _parse_language(language)
    path = Path(config.db_path).expanduser() if config.db_path else normalization_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    use_memory = config.no_cache and not path.exists()
    if use_memory:
        with duckdb.connect(database=":memory:") as conn:
            service = _create_normalization_service(config, conn, read_only=False)
            result = service.normalize(text, lang_hint)
            _print_result(result, config.output)
    else:
        read_only = config.no_cache
        with connect_duckdb(path, read_only=read_only, lock=not read_only) as conn:
            service = _create_normalization_service(config, conn, read_only=read_only)
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
    path = (
        Path(norm_config.db_path).expanduser() if norm_config.db_path else normalization_db_path()
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    use_memory = norm_config.no_cache and not path.exists()
    if use_memory:
        with duckdb.connect(database=":memory:") as conn:
            service = _create_normalization_service(norm_config, conn, read_only=False)
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
    else:
        read_only = norm_config.no_cache
        with connect_duckdb(path, read_only=read_only, lock=not read_only) as conn:
            service = _create_normalization_service(norm_config, conn, read_only=read_only)
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


@dataclass
class BuildGaffiotConfig:
    source_path: str | None
    output: str | None
    limit: int | None
    batch_size: int
    wipe: bool
    force: bool


@dataclass
class BuildDicoConfig:
    source_dir: str | None
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


def _build_gaffiot_impl(config: BuildGaffiotConfig) -> None:
    _ensure_logging()
    from langnet.databuild.gaffiot import GaffiotBuildConfig, GaffiotBuilder  # noqa: PLC0415
    from langnet.databuild.paths import default_gaffiot_path  # noqa: PLC0415

    output_path = Path(config.output).expanduser() if config.output else default_gaffiot_path()
    builder_config = GaffiotBuildConfig(
        source_path=Path(config.source_path).expanduser() if config.source_path else None,
        output_path=output_path,
        limit=config.limit,
        batch_size=config.batch_size,
        wipe_existing=config.wipe,
        force_rebuild=config.force,
    )
    builder = GaffiotBuilder(builder_config)
    result = builder.build()
    _print_build_result(result)


def _build_dico_impl(config: BuildDicoConfig) -> None:
    _ensure_logging()
    from langnet.databuild.dico import DicoBuildConfig, DicoBuilder  # noqa: PLC0415
    from langnet.databuild.paths import default_dico_path  # noqa: PLC0415

    output_path = Path(config.output).expanduser() if config.output else default_dico_path()
    builder_config = DicoBuildConfig(
        source_dir=Path(config.source_dir).expanduser() if config.source_dir else None,
        output_path=output_path,
        limit=config.limit,
        batch_size=config.batch_size,
        wipe_existing=config.wipe,
        force_rebuild=config.force,
    )
    builder = DicoBuilder(builder_config)
    result = builder.build()
    _print_build_result(result)


# Index management commands (Task 2: Foundation Work)


@click.group()
def index():
    """Manage storage indexes and caches."""


@index.command("status")
@click.option("--tool", help="Show status for specific tool")
def index_status(tool: str | None):
    """Show storage index status and disk usage."""
    paths = all_db_paths()
    if tool:
        paths = {k: v for k, v in paths.items() if tool in k}

    total_size = 0
    for name, path in paths.items():
        if path.exists():
            size = path.stat().st_size
            total_size += size
            click.echo(f"{name:20} {humanize.naturalsize(size):>10}  {path}")

            # Show row counts for main tables
            try:
                with connect_duckdb(path, read_only=True, lock=False) as conn:
                    tables = [
                        "raw_response_index",
                        "extraction_index",
                        "derivation_index",
                        "claims",
                    ]
                    for table in tables:
                        try:
                            result = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                            if result is not None:
                                count = result[0]
                                click.echo(f"  {table:30} {count:>6} rows")
                        except duckdb.CatalogException:
                            # Table doesn't exist in this database
                            pass
            except Exception as e:
                click.echo(f"  (Unable to read tables: {e})")
        else:
            click.echo(f"{name:20} {'(not created)':>10}")

    if total_size > 0:
        click.echo(f"\nTotal storage: {humanize.naturalsize(total_size)}")


@index.command("clear")
@click.option("--tool", help="Clear specific tool cache")
@click.option("--all", is_flag=True, help="Clear all caches")
@click.confirmation_option(prompt="This will delete cached data. Continue?")
def index_clear(tool: str | None, all: bool):
    """Clear storage indexes (safe - will be rebuilt on next query)."""
    paths = all_db_paths()
    if tool:
        paths = {k: v for k, v in paths.items() if tool in k}
    elif not all:
        raise click.UsageError("Must specify --tool or --all")

    for name, path in paths.items():
        if path.exists():
            path.unlink()
            click.echo(f"✓ Removed {name}")
        else:
            click.echo(f"  Skipped {name} (doesn't exist)")


@index.command("rebuild")
@click.argument("query")
@click.option("--language", required=True, help="Language (lat, grc, san)")
def index_rebuild(query: str, language: str):
    """Re-run plan execution for a query without reading cached effects."""
    config = PlanExecConfig(
        diogenes_endpoint="http://localhost:8888/Diogenes.cgi",
        diogenes_parse_endpoint=None,
        heritage_base="http://localhost:48080",
        heritage_max_results=10,
        db_path=None,
        no_cache=True,
        include_whitakers=True,
        max_candidates=3,
        use_stub_handlers=True,
    )
    click.echo(f"Rebuilding indexes for '{query}' ({language}) with cache reads disabled...")
    _plan_exec_impl(config, language, query)


@click.group()
def main() -> None:
    """langnet-cli — classical language tools."""


# Register subcommands
main.add_command(index)


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
    help=(
        "Path to persistent DuckDB cache for normalization (defaults to data/cache/langnet.duckdb)."
    ),
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
@click.argument(
    "tool",
    type=click.Choice(["diogenes", "whitakers", "cltk", "heritage", "cdsl"], case_sensitive=False),
)
@click.argument("language")
@click.argument("text")
@click.option(
    "--opt",
    default="",
    show_default=True,
    help="Optional arg: diogenes endpoint/whitaker binary/cdsl dict id/heritage base override.",
)
@click.option(
    "--normalize/--no-normalize",
    default=True,
    show_default=True,
    help="Normalize input before querying the tool.",
)
@click.option(
    "--diogenes-endpoint",
    default="http://localhost:8888/Perseus.cgi",
    show_default=True,
    help="Diogenes parse endpoint (Perseus.cgi).",
)
@click.option(
    "--heritage-base",
    default="http://localhost:48080",
    show_default=True,
    help="Base URL for Heritage Platform (unused here; kept for symmetry).",
)
@click.option(
    "--db-path",
    type=click.Path(),
    help=(
        "Path to persistent DuckDB cache for normalization (defaults to data/cache/langnet.duckdb)."
    ),
)
@click.option(
    "--dict",
    "dict_id",
    default="mw",
    show_default=True,
    help="CDSL dictionary id (mw, ap90) when tool=cdsl.",
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Skip normalization cache lookups and writes for this invocation.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "pretty"]),
    default="pretty",
    show_default=True,
    help="Output format: json (raw data) or pretty (human-readable).",
)
def parse(  # noqa: PLR0913, PLR0915
    tool: str,
    language: str,
    text: str,
    opt: str,
    normalize: bool,
    diogenes_endpoint: str,
    heritage_base: str,
    dict_id: str,
    db_path: str | None,
    no_cache: bool,
    output_format: str,
):
    """
    Parse tool output (diogenes|whitakers|cltk|heritage|cdsl) with optional normalization.
    """
    lang_hint = _parse_language(language)
    norm_cfg = NormalizeConfig(
        diogenes_endpoint=diogenes_endpoint,
        heritage_base=heritage_base,
        db_path=db_path,
        no_cache=no_cache,
        output="pretty",
    )
    query_word = text
    if normalize:
        query_word = _normalize_word_for_tool(language, text, norm_cfg, use_cache=not no_cache)

    tool_l = tool.lower()
    if tool_l == "diogenes":
        endpoint = opt or diogenes_endpoint
        mapped_lang = "grk" if lang_hint == LanguageHint.LANGUAGE_HINT_GRC else language
        url = _diogenes_query_url(endpoint, mapped_lang, query_word)
        resp = requests.get(url)
        html = resp.text if resp.ok else ""
        parsed = _parse_diogenes_html(html)
        payload = parsed
    elif tool_l == "whitakers":
        binary = opt or find_whitaker_binary() or "whitakers-words"
        proc = subprocess.run([binary, query_word], check=False, capture_output=True, text=True)
        text_out = proc.stdout or ""
        parsed = _parse_whitaker_output(text_out)
        payload = parsed
    elif tool_l == "cltk":
        try:
            client = get_cltk_fetch_client()
        except Exception as exc:  # noqa: BLE001
            raise click.ClickException(
                "CLTK client unavailable. Ensure CLTK model data is installed "
                "and CLTK_DATA points to a writable directory."
            ) from exc
        effect = client.execute(
            call_id=f"cltk-{query_word}",
            endpoint=f"cltk://ipa/{language}",
            params={"word": query_word, "language": language},
        )
        effect.body.decode("utf-8", errors="ignore")
        parsed = {}
        try:
            parsed = orjson.loads(effect.body)
        except Exception:
            parsed = {}
        # Enrich with parsed Lewis & Short entries
        parsed = enrich_cltk_with_parsed_lewis(parsed)
        payload = parsed
    elif tool_l == "heritage":
        endpoint = opt or f"{heritage_base.rstrip('/')}/cgi-bin/skt/sktreader"
        vh_text = to_heritage_velthuis(query_word)
        query_parts = [
            ("t", "VH"),
            ("lex", "SH"),
            ("font", "roma"),
            ("cache", "f"),
            ("st", "t"),
            ("us", "f"),
            ("best_mode", "b"),
            ("fmode", "w"),
            ("text", vh_text),
            ("topic", ""),
            ("abs", "f"),
            ("corpmode", ""),
            ("corpdir", ""),
            ("sentno", ""),
            ("mode", "p"),
            ("cpts", ""),
            ("rcpts", ""),
            ("max", "5"),
            ("orig", query_word),
        ]
        query_string = ";".join(f"{k}={v}" for k, v in query_parts)
        params = {"__http_query": query_string}
        fetch = HttpToolClient(tool="fetch.heritage").execute(
            call_id="heritage-1", endpoint=endpoint, params=params
        )
        ext_call = ToolCallSpec(
            tool="extract.heritage.html",
            call_id="heritage-parse-1",
            endpoint="internal://heritage/html_extract",
            params={"source_call_id": "heritage-1"},
        )
        extraction = heritage_handlers.extract_html(ext_call, fetch)
        drv_call = ToolCallSpec(
            tool="derive.heritage.morph",
            call_id="heritage-derive-1",
            endpoint="internal://heritage/morph_derive",
            params={"source_call_id": ext_call.call_id},
        )
        derivation = heritage_handlers.derive_morph(drv_call, extraction)
        payload = derivation.payload
    elif tool_l == "cdsl":
        fetch_client = cdsl_handlers.CdslFetchClient()
        use_dict = opt or dict_id
        lemma = cdsl_handlers._to_slp1(query_word)  # type: ignore[attr-defined]
        fetch = fetch_client.execute(
            call_id="cdsl-1",
            endpoint="duckdb",
            params={"lemma": lemma, "dict": use_dict},
        )
        ext_call = ToolCallSpec(
            tool="extract.cdsl.xml",
            call_id="cdsl-parse-1",
            endpoint="internal://cdsl/xml_extract",
            params={"source_call_id": "cdsl-1"},
        )
        extraction = cdsl_handlers.extract_xml(ext_call, fetch)
        drv_call = ToolCallSpec(
            tool="derive.cdsl.sense",
            call_id="cdsl-derive-1",
            endpoint="internal://cdsl/sense_derive",
            params={"source_call_id": ext_call.call_id},
        )
        derivation = cdsl_handlers.derive_sense(drv_call, extraction)
        payload = derivation.payload
    else:  # pragma: no cover - click enforces choices
        raise click.UsageError(f"Unsupported tool '{tool}'.")

    # Output results in requested format
    if output_format == "pretty":
        # Wrap single tool result in dict for _display_pretty
        _display_pretty(language, text, {tool_l: payload})
    else:
        click.echo(orjson.dumps(payload, option=orjson.OPT_INDENT_2).decode("utf-8"))


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


@databuild.command("gaffiot")
@click.option(
    "--source",
    "source_path",
    type=click.Path(),
    default=None,
    help="Path to gaffiot-unicode.xml (defaults to ~/digital-gaffiot-json/gaffiot-unicode.xml).",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output DuckDB path (defaults to data/build/lex_gaffiot.duckdb)",
)
@click.option("--limit", type=int, help="Limit rows for testing.")
@click.option(
    "--batch-size",
    type=int,
    default=500,
    show_default=True,
    help="Rows per batch while inserting.",
)
@click.option(
    "--wipe/--no-wipe", default=True, show_default=True, help="Delete existing DB before building."
)
@click.option("--force", is_flag=True, help="Rebuild even if output exists without wiping.")
def build_gaffiot(  # noqa: PLR0913
    source_path: str | None,
    output: str | None,
    limit: int | None,
    batch_size: int,
    wipe: bool,
    force: bool,
):
    """Build Gaffiot French→Latin index."""
    config = BuildGaffiotConfig(
        source_path=source_path,
        output=output,
        limit=limit,
        batch_size=batch_size,
        wipe=wipe,
        force=force,
    )
    _build_gaffiot_impl(config)


@databuild.command("dico")
@click.option(
    "--source-dir",
    type=click.Path(),
    default=None,
    help=(
        "Path to DICO HTML directory "
        "(defaults to ~/langnet-tools/sanskrit-heritage/webroot/htdocs/DICO/)."
    ),
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output DuckDB path (defaults to data/build/lex_dico.duckdb)",
)
@click.option("--limit", type=int, help="Limit rows for testing.")
@click.option(
    "--batch-size",
    type=int,
    default=500,
    show_default=True,
    help="Rows per batch while inserting.",
)
@click.option(
    "--wipe/--no-wipe", default=True, show_default=True, help="Delete existing DB before building."
)
@click.option("--force", is_flag=True, help="Rebuild even if output exists without wiping.")
def build_dico(  # noqa: PLR0913
    source_dir: str | None,
    output: str | None,
    limit: int | None,
    batch_size: int,
    wipe: bool,
    force: bool,
):
    """Build DICO French→Sanskrit index."""
    config = BuildDicoConfig(
        source_dir=source_dir,
        output=output,
        limit=limit,
        batch_size=batch_size,
        wipe=wipe,
        force=force,
    )
    _build_dico_impl(config)


def _create_http_client(tool: str) -> ToolClient:
    """Create an HTTP client for the given tool."""
    return HttpToolClient(tool=tool)


def _create_whitakers_client(tool: str, use_stubs: bool) -> ToolClient | None:
    """Create a Whitakers client, with stub fallback."""
    binary = find_whitaker_binary()
    if binary:
        return WhitakerFetchClient(binary)
    if use_stubs:
        return StubToolClient(tool)
    return None


def _create_cltk_client(tool: str, use_stubs: bool) -> ToolClient | None:
    """Create a CLTK client, with stub fallback."""
    try:
        return get_cltk_fetch_client()
    except Exception:
        if use_stubs:
            return StubToolClient(tool)
    return None


def _create_spacy_client(tool: str, use_stubs: bool) -> ToolClient | None:
    """Create a spaCy client, with stub fallback."""
    try:
        return get_spacy_fetch_client()
    except Exception:
        if use_stubs:
            return StubToolClient(tool)
    return None


def _create_cdsl_client(tool: str, use_stubs: bool) -> ToolClient | None:
    """Create a CDSL client, with stub fallback."""
    try:
        from langnet.execution.handlers.cdsl import CdslFetchClient  # noqa: PLC0415

        return CdslFetchClient()
    except Exception:
        if use_stubs:
            return StubToolClient(tool)
    return None


def _get_client_factory(tool: str, use_stubs: bool):
    """Get the factory function for creating a client for the given tool."""
    http_tools = {"fetch.diogenes", "fetch.heritage"}

    # Special client factories
    special_factories = {
        "fetch.whitakers": lambda: _create_whitakers_client(tool, use_stubs),
        "fetch.cltk": lambda: _create_cltk_client(tool, use_stubs),
        "fetch.spacy": lambda: _create_spacy_client(tool, use_stubs),
        "fetch.cdsl": lambda: _create_cdsl_client(tool, use_stubs),
    }

    if tool in http_tools:
        return lambda: _create_http_client(tool)
    if tool in special_factories:
        return special_factories[tool]
    if tool.startswith("fetch.") and use_stubs:
        return lambda: StubToolClient(tool)
    return None


def _build_exec_clients(plan, diogenes_endpoint: str, use_stubs: bool) -> dict[str, ToolClient]:
    """Build execution clients for all tools in the plan."""
    clients: dict[str, ToolClient] = {}

    for call in plan.tool_calls:
        tool = call.tool
        if tool in clients:
            continue

        factory = _get_client_factory(tool, use_stubs)
        if factory is not None:
            client = factory()
            if client is not None:
                clients[tool] = client

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
    path = Path(norm_cfg.db_path).expanduser() if norm_cfg.db_path else normalization_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect_duckdb(path, read_only=False, lock=True) as conn:
        service = _create_normalization_service(norm_cfg, conn, read_only=False)
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
        f"derivations={len(result.derivations)} claims={len(result.claims)} "
        f"cache_hit={result.from_cache}"
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


def _get_query_value_for_plan(
    text: str, lang_hint, normalize: bool, norm_cfg: NormalizeConfig
) -> query_spec.NormalizedQuery:
    """Get the query value for planning, either normalized or passthrough."""
    path = Path(norm_cfg.db_path).expanduser() if norm_cfg.db_path else normalization_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    use_memory = norm_cfg.no_cache or not path.exists()

    if normalize:
        if use_memory:
            with duckdb.connect(database=":memory:") as norm_conn:
                service = _create_normalization_service(norm_cfg, norm_conn, read_only=False)
                normalized_result = service.normalize(text, lang_hint)
        else:
            read_only = norm_cfg.no_cache
            with connect_duckdb(path, read_only=read_only, lock=not read_only) as norm_conn:
                service = _create_normalization_service(norm_cfg, norm_conn, read_only=read_only)
                normalized_result = service.normalize(text, lang_hint)
        return normalized_result.normalized

    # Minimal passthrough NormalizedQuery to satisfy the planner.
    return query_spec.NormalizedQuery(
        original=text,
        language=lang_hint,
        candidates=[
            query_spec.CanonicalCandidate(
                lemma=text,
                encodings={"accentless": text},
                sources=["manual"],
            )
        ],
        normalizations=[],
    )


def _filter_plan_tools(plan, tool_filter: str) -> None:
    """Filter plan to only include tools matching the filter."""
    lf = tool_filter.lower()

    def _matches_tool(tool_name: str) -> bool:
        t = tool_name.lower()
        if t.startswith(lf):
            return True
        _, _, rest = t.partition(".")
        return bool(rest) and rest.startswith(lf)

    filtered_calls = [c for c in plan.tool_calls if _matches_tool(c.tool)]
    kept_ids = {c.call_id for c in filtered_calls}
    filtered_deps = [
        d for d in plan.dependencies if d.from_call_id in kept_ids and d.to_call_id in kept_ids
    ]
    plan.ClearField("tool_calls")
    plan.ClearField("dependencies")
    plan.tool_calls.extend(filtered_calls)
    plan.dependencies.extend(filtered_deps)


def _display_claim_triples(result) -> None:
    """Display claim triples to stdout."""
    for claim in result.claims:
        click.echo(f"TOOL={claim.tool} PRED={claim.predicate} SUBJECT={claim.subject}")
        val = claim.value if isinstance(claim.value, dict) else {}
        triples = val.get("triples") if isinstance(val, dict) else None
        if triples:
            sense_counts: dict[str, int] = {}
            for t in triples:
                if isinstance(t, dict) and t.get("predicate") == "has_sense":
                    subj = t.get("subject")
                    if isinstance(subj, str):
                        sense_counts[subj] = sense_counts.get(subj, 0) + 1
            if sense_counts:
                click.echo(f"  sense_counts {sense_counts}")
            for t in triples[:10]:
                click.echo(f"  triple {t}")


@main.command("triples-dump")
@click.argument("language")
@click.argument("text")
@click.argument("tool_filter", default="all")
@click.option(
    "--normalize/--no-normalize",
    default=True,
    show_default=True,
    help="Normalize input before planning/executing.",
)
@click.option(
    "--diogenes-endpoint",
    default="http://localhost:8888/Diogenes.cgi",
    show_default=True,
    help="Diogenes CGI endpoint for planning/fetch.",
)
@click.option(
    "--diogenes-parse-endpoint",
    help="Alternate Diogenes parse endpoint (defaults to diogenes-endpoint).",
)
@click.option(
    "--heritage-base",
    default="http://localhost:48080",
    show_default=True,
    help="Base URL for Heritage Platform (unused here; kept for symmetry).",
)
@click.option(
    "--db-path",
    type=click.Path(),
    help=(
        "Path to persistent DuckDB cache for normalization (defaults to data/cache/langnet.duckdb)."
    ),
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Skip normalization cache lookups and writes for this invocation.",
)
@click.option(
    "--include-cltk/--no-include-cltk",
    default=False,
    show_default=True,
    help="Include CLTK in the plan (may be slow due to warmup).",
)
def triples_dump(  # noqa: PLR0913
    language: str,
    text: str,
    tool_filter: str,
    normalize: bool,
    diogenes_endpoint: str,
    diogenes_parse_endpoint: str | None,
    heritage_base: str,
    db_path: str | None,
    no_cache: bool,
    include_cltk: bool,
):
    """
    Build a ToolPlan for the word and dump claims/triples for selected tools.
    """
    lang_hint = _parse_language(language)
    norm_cfg = NormalizeConfig(
        diogenes_endpoint=diogenes_endpoint,
        heritage_base=heritage_base,
        db_path=db_path,
        no_cache=no_cache,
        output="pretty",
    )

    query_value = _get_query_value_for_plan(text, lang_hint, normalize, norm_cfg)

    planner = ToolPlanner(
        PlannerConfig(
            diogenes_endpoint=diogenes_endpoint,
            diogenes_parse_endpoint=diogenes_parse_endpoint,
            heritage_base_url=heritage_base,
            heritage_max_results=5,
            include_whitakers=lang_hint == LanguageHint.LANGUAGE_HINT_LAT,
            include_cltk=include_cltk
            and lang_hint in {LanguageHint.LANGUAGE_HINT_LAT, LanguageHint.LANGUAGE_HINT_GRC},
            max_candidates=3,
        )
    )
    candidate = planner.select_candidate(query_value)
    plan = planner.build(query_value, candidate)

    if tool_filter and tool_filter.lower() != "all":
        _filter_plan_tools(plan, tool_filter)

    with duckdb.connect(database=":memory:") as conn:
        apply_schema(conn)
        raw_index = RawResponseIndex(conn)
        extraction_index = ExtractionIndex(conn)
        derivation_index = DerivationIndex(conn)
        claim_index = ClaimIndex(conn)
        plan_response_index = PlanResponseIndex(conn)
        registry = default_registry(use_stubs=False)
        clients = _build_exec_clients(plan, diogenes_endpoint, use_stubs=False)
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

    _display_claim_triples(result)


def _display_pretty(language: str, text: str, results: dict) -> None:  # noqa: C901, PLR0912, PLR0915
    """
    Display dictionary lookup results in a human-readable format.

    Args:
        language: Language code (lat, grc, san)
        text: The word that was looked up
        results: Dict mapping tool names to their results
    """
    # Header
    lang_display = {"lat": "Latin", "grc": "Greek", "san": "Sanskrit"}.get(language, language)
    click.echo()
    click.echo(click.style(f"{text.upper()} [{lang_display}]", bold=True, fg="cyan"))
    click.echo(click.style("━" * 60, fg="cyan"))
    click.echo()

    # Track success/failures
    successful = 0
    total = len(results)

    # Display each tool's results
    for tool_name, tool_data in results.items():
        # Check if this tool had an error
        if isinstance(tool_data, dict) and "error" in tool_data:
            click.echo(click.style(f"✗ {tool_name.upper()}", fg="red", bold=True))
            click.echo(f"  Error: {tool_data.get('error', 'Unknown error')}")
            click.echo()
            continue

        successful += 1

        # Tool name header
        tool_display = {
            "whitakers": "Whitaker's Words",
            "diogenes": "Lewis & Short (Diogenes)" if language == "lat" else "LSJ (Diogenes)",
            "cltk": "CLTK",
            "heritage": "Sanskrit Heritage Platform",
            "cdsl": "CDSL (Monier-Williams)",
        }.get(tool_name, tool_name.upper())

        click.echo(click.style(f"● {tool_display}", fg="green", bold=True))

        # Format based on tool type
        if tool_name == "whitakers" and isinstance(tool_data, list):
            for entry in tool_data[:3]:  # Limit to first 3 entries
                if "terms" in entry and entry["terms"]:
                    term = entry["terms"][0]
                    click.echo(f"  Form: {term.get('term', 'N/A')}")
                    if "codeline" in entry:
                        click.echo(f"  Lemma: {entry['codeline'].get('term', 'N/A')}")
                        click.echo(f"  POS: {entry['codeline'].get('pos_code', 'N/A')}")
                if "senses" in entry and entry["senses"]:
                    click.echo(f"  Meaning: {', '.join(entry['senses'][:3])}")
                click.echo()

        elif tool_name == "diogenes":
            # Diogenes can have different structures
            if isinstance(tool_data, dict):
                if "entries" in tool_data:
                    for i, entry in enumerate(tool_data["entries"][:2], 1):
                        click.echo(f"  {i}. {entry.get('headword', 'N/A')}")
                        if "definition" in entry:
                            defn = entry["definition"][:200]
                            click.echo(f"     {defn}...")
                elif "error" not in tool_data:
                    # Show raw structure if not recognized
                    click.echo(f"  (Raw data available - {len(str(tool_data))} chars)")
            click.echo()

        elif tool_name == "cltk" and isinstance(tool_data, dict):
            if "lemma" in tool_data:
                click.echo(f"  Lemma: {tool_data['lemma']}")
            if "lewis_lines" in tool_data and tool_data["lewis_lines"]:
                click.echo("  Lewis & Short:")
                for line in tool_data["lewis_lines"][:3]:
                    click.echo(f"    {line[:80]}...")
            if "parsed_lewis" in tool_data:
                click.echo(f"  (Parsed {len(tool_data['parsed_lewis'])} entries)")
            click.echo()

        elif tool_name == "heritage" and isinstance(tool_data, dict):
            if "morphology" in tool_data:
                click.echo("  Morphological Analysis:")
                for analysis in tool_data["morphology"][:3]:
                    if isinstance(analysis, dict):
                        form = analysis.get("form", "N/A")
                        analysis_text = analysis.get("analysis", "N/A")
                        click.echo(f"    {form}: {analysis_text}")
            elif "segmentations" in tool_data:
                click.echo(f"  Segmentations: {len(tool_data['segmentations'])} found")
            click.echo()

        elif tool_name == "cdsl" and isinstance(tool_data, dict):
            if "entries" in tool_data:
                click.echo(f"  Dictionary Entries: {len(tool_data['entries'])} found")
                for entry in tool_data["entries"][:2]:
                    if isinstance(entry, dict) and "hw" in entry:
                        click.echo(f"    {entry['hw']}: {entry.get('definition', 'N/A')[:60]}...")
            click.echo()

        else:
            # Generic fallback for unknown structures
            click.echo(f"  (Data available - {len(str(tool_data))} chars)")
            click.echo()

    # Footer
    click.echo(click.style("━" * 60, fg="cyan"))
    status_color = "green" if successful == total else "yellow"
    click.echo(click.style(f"Sources: {successful}/{total} successful", fg=status_color))
    click.echo()


@main.command()
@click.argument("language", type=click.Choice(["lat", "grc", "san"], case_sensitive=False))
@click.argument("text")
@click.option(
    "--output",
    type=click.Choice(["json", "pretty"]),
    default="json",
    show_default=True,
    help="Output format.",
)
@click.option(
    "--normalize/--no-normalize",
    default=True,
    show_default=True,
    help="Normalize input before querying tools.",
)
@click.option(
    "--diogenes-endpoint",
    default="http://localhost:8888/Perseus.cgi",
    show_default=True,
    help="Diogenes parse endpoint (Perseus.cgi).",
)
@click.option(
    "--heritage-base",
    default="http://localhost:48080",
    show_default=True,
    help="Base URL for Heritage Platform.",
)
@click.option(
    "--dict",
    "dict_id",
    default="mw",
    show_default=True,
    help="CDSL dictionary id (mw, ap90) for Sanskrit tools.",
)
@click.option(
    "--db-path",
    type=click.Path(),
    help=(
        "Path to persistent DuckDB cache for normalization (defaults to data/cache/langnet.duckdb)."
    ),
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Skip normalization cache lookups and writes for this invocation.",
)
def lookup(  # noqa: PLR0913, PLR0915, C901
    language: str,
    text: str,
    output: str,
    normalize: bool,
    diogenes_endpoint: str,
    heritage_base: str,
    dict_id: str,
    db_path: str | None,
    no_cache: bool,
):
    """
    Unified lookup across all available dictionary sources for a language.

    Queries multiple tools in parallel for the given language:
    - Latin (lat): Whitaker's Words, Diogenes (Lewis & Short), CLTK
    - Greek (grc): Diogenes (LSJ)
    - Sanskrit (san): Heritage Platform, CDSL

    Returns aggregated results from all available sources.
    """
    # Map language to available tools
    tool_map = {
        "lat": ["whitakers", "diogenes", "cltk"],
        "grc": ["diogenes"],
        "san": ["heritage", "cdsl"],
    }

    tools = tool_map.get(language.lower(), [])
    if not tools:
        raise click.UsageError(f"No tools available for language '{language}'.")

    # Set up normalization config
    lang_hint = _parse_language(language)
    norm_cfg = NormalizeConfig(
        diogenes_endpoint=diogenes_endpoint,
        heritage_base=heritage_base,
        db_path=db_path,
        no_cache=no_cache,
        output="pretty",
    )

    # Normalize query word once for all tools
    query_word = text
    if normalize:
        query_word = _normalize_word_for_tool(language, text, norm_cfg, use_cache=not no_cache)

    # Aggregate results from all tools
    results = {}

    for tool in tools:
        try:
            if tool == "diogenes":
                # Diogenes dictionary lookup
                mapped_lang = "grk" if lang_hint == LanguageHint.LANGUAGE_HINT_GRC else language
                url = _diogenes_query_url(diogenes_endpoint, mapped_lang, query_word)
                resp = requests.get(url)
                html = resp.text if resp.ok else ""
                parsed = _parse_diogenes_html(html)
                results[tool] = parsed

            elif tool == "whitakers":
                # Whitaker's Words
                binary = find_whitaker_binary() or "whitakers-words"
                proc = subprocess.run(
                    [binary, query_word], check=False, capture_output=True, text=True
                )
                text_out = proc.stdout or ""
                parsed = _parse_whitaker_output(text_out)
                results[tool] = parsed

            elif tool == "cltk":
                # CLTK dictionary and morphology
                client = get_cltk_fetch_client()
                effect = client.execute(
                    call_id=f"cltk-{query_word}",
                    endpoint=f"cltk://ipa/{language}",
                    params={"word": query_word, "language": language},
                )
                parsed = {}
                try:
                    parsed = orjson.loads(effect.body)
                except Exception:
                    parsed = {}

                # Enrich with parsed Lewis & Short if available
                parsed = enrich_cltk_with_parsed_lewis(parsed)
                results[tool] = parsed

            elif tool == "heritage":
                # Sanskrit Heritage Platform
                endpoint = f"{heritage_base.rstrip('/')}/cgi-bin/skt/sktreader"
                vh_text = to_heritage_velthuis(query_word)
                query_parts = [
                    ("t", "VH"),
                    ("lex", "SH"),
                    ("font", "roma"),
                    ("cache", "f"),
                    ("st", "t"),
                    ("us", "f"),
                    ("best_mode", "b"),
                    ("fmode", "w"),
                    ("text", vh_text),
                    ("topic", ""),
                    ("abs", "f"),
                    ("corpmode", ""),
                    ("corpdir", ""),
                    ("sentno", ""),
                    ("mode", "p"),
                    ("cpts", ""),
                    ("rcpts", ""),
                    ("max", "5"),
                    ("orig", query_word),
                ]
                query_string = ";".join(f"{k}={v}" for k, v in query_parts)
                params = {"__http_query": query_string}
                fetch = HttpToolClient(tool="fetch.heritage").execute(
                    call_id="heritage-1", endpoint=endpoint, params=params
                )
                ext_call = ToolCallSpec(
                    tool="extract.heritage.html",
                    call_id="heritage-parse-1",
                    endpoint="internal://heritage/html_extract",
                    params={"source_call_id": "heritage-1"},
                )
                extraction = heritage_handlers.extract_html(ext_call, fetch)
                drv_call = ToolCallSpec(
                    tool="derive.heritage.morph",
                    call_id="heritage-derive-1",
                    endpoint="internal://heritage/morph_derive",
                    params={"source_call_id": ext_call.call_id},
                )
                derivation = heritage_handlers.derive_morph(drv_call, extraction)
                results[tool] = derivation.payload

            elif tool == "cdsl":
                # CDSL Sanskrit dictionaries
                fetch_client = cdsl_handlers.CdslFetchClient()
                lemma = cdsl_handlers._to_slp1(query_word)  # type: ignore[attr-defined]
                fetch = fetch_client.execute(
                    call_id="cdsl-1",
                    endpoint="duckdb",
                    params={"lemma": lemma, "dict": dict_id},
                )
                ext_call = ToolCallSpec(
                    tool="extract.cdsl.xml",
                    call_id="cdsl-parse-1",
                    endpoint="internal://cdsl/xml_extract",
                    params={"source_call_id": "cdsl-1"},
                )
                extraction = cdsl_handlers.extract_xml(ext_call, fetch)
                drv_call = ToolCallSpec(
                    tool="derive.cdsl.sense",
                    call_id="cdsl-derive-1",
                    endpoint="internal://cdsl/sense_derive",
                    params={"source_call_id": ext_call.call_id},
                )
                derivation = cdsl_handlers.derive_sense(drv_call, extraction)
                results[tool] = derivation.payload

        except Exception as e:
            # Capture errors per tool but continue with others
            results[tool] = {"error": str(e), "error_type": type(e).__name__}

    # Output results
    if output == "pretty":
        _display_pretty(language, text, results)
    else:
        click.echo(orjson.dumps(results, option=orjson.OPT_INDENT_2).decode("utf-8"))


if __name__ == "__main__":
    main()
