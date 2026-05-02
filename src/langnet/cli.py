from __future__ import annotations

import importlib.util
import logging
import os
import re
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TypedDict, cast

import click
import duckdb
import humanize
import orjson
import query_spec
import requests
from filelock import Timeout as FileLockTimeout
from query_spec import ToolCallSpec, ToolStage

from langnet.cli_databuild import databuild
from langnet.cli_triples import (
    build_triples_dump_payload,
    display_claim_triples,
    display_dico_resolutions,
)
from langnet.clients.base import ToolClient
from langnet.clients.http import HttpToolClient
from langnet.encounter_display import (
    build_analysis_views,
    build_display_payload,
    build_header_view,
    build_meaning_view,
    foster_display_for_analysis,
    foster_features_from_analysis,
    shorten_text,
)
from langnet.encounter_ranking import (
    bucket_learner_quality_order,
    bucket_lemma_values,
    bucket_quality_text,
    bucket_ranking_explanation,
    bucket_sort_key,
    bucket_source_tools,
    cdsl_dictionary_order,
    cdsl_source_order,
    diogenes_source_order,
    effective_preferred_lemma_rank,
    gaffiot_source_order,
    generic_source_order,
    lemma_compare_keys,
    morphology_lemma_preference_key,
    normalize_lemma,
    preferred_lemma_rank,
    preferred_lemmas_for_sorting,
    preferred_lemmas_from_morphology,
    preferred_lemmas_from_reduction,
    reduction_lemma_values,
)
from langnet.encounter_translation import (
    add_translation_counts,
    apply_translation_cache,
    empty_translation_counts,
    encounter_translation_diagnostics,
    merge_translation_counts,
    resolve_translation_mode,
)
from langnet.execution import predicates
from langnet.execution.clients import (
    StubToolClient,
    WhitakerFetchClient,
    find_whitaker_binary,
    get_cltk_fetch_client,
    get_spacy_fetch_client,
)
from langnet.execution.executor import execute_plan_staged
from langnet.execution.handlers import cdsl as cdsl_handlers
from langnet.execution.handlers import gaffiot as gaffiot_handlers
from langnet.execution.handlers import heritage as heritage_handlers
from langnet.execution.handlers.diogenes import _parse_diogenes_html
from langnet.execution.handlers.whitakers import _parse_whitaker_output
from langnet.execution.registry import default_registry
from langnet.execution.source_text import analyze_source_entry, compact_source_gloss
from langnet.heritage.velthuis_converter import to_heritage_velthuis
from langnet.normalizer.core import NormalizationResult, _hash_query
from langnet.normalizer.service import DiogenesConfig, NormalizationService
from langnet.normalizer.utils import strip_accents
from langnet.parsing.integration import enrich_cltk_with_parsed_lewis
from langnet.planner.core import PlannerConfig, ToolPlanner
from langnet.reader_eval import (
    evaluate_reader_token,
    iter_reader_eval_tokens,
    load_reader_eval_fixture,
    summarize_reader_eval,
)
from langnet.reduction import reduce_claims
from langnet.storage.claim_index import ClaimIndex
from langnet.storage.db import connect_duckdb
from langnet.storage.derivation_index import DerivationIndex
from langnet.storage.effects_index import RawResponseIndex
from langnet.storage.extraction_index import ExtractionIndex
from langnet.storage.normalization_index import NormalizationIndex
from langnet.storage.normalization_index import ensure_schema as ensure_normalization_schema
from langnet.storage.path_indices import (
    PathClaimIndex,
    PathDerivationIndex,
    PathExtractionIndex,
    PathPlanResponseIndex,
    PathRawResponseIndex,
)
from langnet.storage.paths import all_db_paths, normalization_db_path
from langnet.storage.plan_index import PlanResponseIndex, apply_schema
from langnet.tool_catalog import canonical_language, catalog_payload, language_payload
from langnet.translation import (
    BASE_SYSTEM,
    TranslationCache,
    apply_translation_schema,
    populate_missing_translations,
    project_cached_translations,
    translation_cache_status_counts,
)

LanguageHint = query_spec.LanguageHint
LanguageValue = query_spec.LanguageHint.ValueType
LATIN_AE_SUFFIX_LEN = 2
ENCOUNTER_LEARNER_GLOSS_MAX_CHARS = 120
ENCOUNTER_LEARNER_GLOSS_ITEM_LIMIT = 4
ENCOUNTER_JSON_SCHEMA_VERSION = "langnet.encounter.v1"
ENCOUNTER_JSON_ERROR_SCHEMA_VERSION = "langnet.encounter.error.v1"
TRANSLATION_CACHE_SCHEMA_VERSION = "langnet.translation_cache.v1"
DOCTOR_SCHEMA_VERSION = "langnet.doctor.v1"


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


def _encounter_json_error_payload(  # noqa: PLR0913
    *,
    language: str,
    text: str,
    tool_filter: str,
    normalize: bool,
    no_cache: bool,
    include_cltk: bool,
    translation_mode: str,
    exc: Exception,
) -> dict[str, object]:
    message = exc.format_message() if isinstance(exc, click.ClickException) else str(exc)
    if not message:
        message = exc.__class__.__name__
    return {
        "schema_version": ENCOUNTER_JSON_ERROR_SCHEMA_VERSION,
        "ok": False,
        "request": {
            "language": language,
            "text": text,
            "tool_filter": tool_filter,
            "normalize": normalize,
            "no_cache": no_cache,
            "include_cltk": include_cltk,
            "translation_mode": translation_mode,
        },
        "error": {
            "code": "click_error" if isinstance(exc, click.ClickException) else "encounter_failed",
            "type": exc.__class__.__name__,
            "message": message,
        },
    }


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
    output: str


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


def _normalization_result_uncached(
    config: NormalizeConfig,
    text: str,
    lang_hint: LanguageValue,
) -> NormalizationResult:
    compute_config = NormalizeConfig(
        diogenes_endpoint=config.diogenes_endpoint,
        heritage_base=config.heritage_base,
        db_path=config.db_path,
        no_cache=True,
        output=config.output,
    )
    with duckdb.connect(database=":memory:") as conn:
        service = _create_normalization_service(compute_config, conn, read_only=False)
        return service.normalize(text, lang_hint)


def _normalization_cache_get(
    *,
    config: NormalizeConfig,
    path: Path,
    text: str,
    lang_hint: LanguageValue,
) -> NormalizationResult | None:
    if not path.exists():
        return None
    query_hash = _hash_query(text, lang_hint)
    with connect_duckdb(path, read_only=False, lock=True) as conn:
        ensure_normalization_schema(conn)
        cached = NormalizationIndex(conn).get(query_hash)
        if cached is not None:
            service = _create_normalization_service(config, conn, read_only=False)
            cached = service._rerank_candidates(text, lang_hint, cached)
            if service._cached_greek_epic_eus_is_stale(text, lang_hint, cached):
                cached = None
    if cached is None:
        return None
    return NormalizationResult(query_hash=query_hash, normalized=cached)


def _normalization_cache_upsert(
    *,
    path: Path,
    text: str,
    lang_hint: LanguageValue,
    result: NormalizationResult,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect_duckdb(path, read_only=False, lock=True) as conn:
        ensure_normalization_schema(conn)
        NormalizationIndex(conn).upsert(
            query_hash=result.query_hash,
            raw_query=text,
            language=str(lang_hint).lower(),
            normalized=result.normalized,
        )


def _normalize_with_short_cache_lock(
    config: NormalizeConfig,
    text: str,
    lang_hint: LanguageValue,
    *,
    use_cache: bool = True,
) -> NormalizationResult:
    path = Path(config.db_path).expanduser() if config.db_path else normalization_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    cache_enabled = use_cache and not config.no_cache
    if cache_enabled:
        cached = _normalization_cache_get(
            config=config,
            path=path,
            text=text,
            lang_hint=lang_hint,
        )
        if cached is not None:
            return cached

    result = _normalization_result_uncached(config, text, lang_hint)
    if cache_enabled:
        _normalization_cache_upsert(path=path, text=text, lang_hint=lang_hint, result=result)
    return result


class _PathTranslationCache:
    """Translation cache facade that does not hold DuckDB open during model calls."""

    def __init__(self, path: Path, *, read_only: bool = False) -> None:
        self.path = path
        self.read_only = read_only

    def get(self, key) -> object | None:
        if not self.path.exists():
            return None
        with connect_duckdb(self.path, read_only=False, lock=True) as conn:
            return TranslationCache(conn, read_only=True).get(key)

    def upsert(self, record) -> str:
        if self.read_only:
            raise RuntimeError("translation cache is read-only")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with connect_duckdb(self.path, read_only=False, lock=True) as conn:
            return TranslationCache(conn, read_only=False).upsert(record)


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
    normalized = _normalize_with_short_cache_lock(
        config,
        text,
        lang_hint,
        use_cache=use_cache,
    )
    return _pick_best_normalization_candidate(normalized, text)


def _diogenes_query_url(base: str, lang: str, word: str) -> str:
    """
    Build a diogenes parse URL with raw Unicode query (avoid percent-encoding Greek).
    """
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}do=parse&lang={lang}&q={word}"


def _normalize_impl(config: NormalizeConfig, language: str, text: str) -> None:
    lang_hint = _parse_language(language)
    result = _normalize_with_short_cache_lock(config, text, lang_hint)
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
    normalized = _normalize_with_short_cache_lock(norm_config, text, lang_hint)
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
        output="pretty",
    )
    click.echo(f"Rebuilding indexes for '{query}' ({language}) with cache reads disabled...")
    _plan_exec_impl(config, language, query)


@click.group()
def main() -> None:
    """langnet-cli — classical language tools."""


# Register subcommands
main.add_command(index)
main.add_command(databuild)


@main.command("tools")
@click.argument("language", required=False)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
def tools(language: str | None, output: str) -> None:
    """List tool_filter values accepted by learner-facing commands."""
    if language and canonical_language(language) is None:
        raise click.UsageError(f"Unsupported language '{language}'. Use lat|grc|san.")

    payload = catalog_payload(language, command="encounter")
    if output == "json":
        click.echo(orjson.dumps(payload, option=orjson.OPT_INDENT_2).decode("utf-8"))
        return

    click.echo("Tool filters")
    languages = cast(Sequence[Mapping[str, object]], payload["languages"])
    tools_payload = cast(Sequence[Mapping[str, object]], payload["tools"])
    for lang_map in languages:
        click.echo(f"\n{lang_map['label']} ({lang_map['code']})")
        click.echo("  all - All default tools for the language")
        for entry in tools_payload:
            if entry.get("language") != lang_map["code"]:
                continue
            suffix = " [translation-capable]" if entry.get("translation_capable") else ""
            click.echo(f"  {entry['tool_filter']} - {entry['label']} ({entry['role']}){suffix}")


@main.command("langs")
@click.argument("language", required=False)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
def langs(language: str | None, output: str) -> None:
    """List supported language codes and aliases."""
    if language and canonical_language(language) is None:
        raise click.UsageError(f"Unsupported language '{language}'. Use lat|grc|san.")

    payload = language_payload(language)
    if output == "json":
        click.echo(orjson.dumps(payload, option=orjson.OPT_INDENT_2).decode("utf-8"))
        return

    click.echo("Languages")
    languages = cast(Sequence[Mapping[str, object]], payload["languages"])
    for lang_map in languages:
        aliases = cast(Sequence[str], lang_map["aliases"])
        click.echo(f"  {lang_map['code']} - {lang_map['label']} (aliases: {', '.join(aliases)})")


def _doctor_check(  # noqa: PLR0913
    checks: list[dict[str, object]],
    *,
    check_id: str,
    status: str,
    severity: str,
    message: str,
    metadata: Mapping[str, object] | None = None,
) -> None:
    checks.append(
        {
            "id": check_id,
            "status": status,
            "severity": severity,
            "message": message,
            "metadata": dict(metadata or {}),
        }
    )


def _doctor_schema_checks(checks: list[dict[str, object]]) -> None:
    schema_paths = [
        Path("docs/schemas/languages.v1.schema.json"),
        Path("docs/schemas/tools.v1.schema.json"),
        Path("docs/schemas/encounter.v1.schema.json"),
        Path("docs/schemas/encounter-error.v1.schema.json"),
        Path("docs/schemas/translation-cache.v1.schema.json"),
        Path("docs/schemas/doctor.v1.schema.json"),
    ]
    for schema_path in schema_paths:
        if not schema_path.exists():
            _doctor_check(
                checks,
                check_id=f"schema:{schema_path.name}",
                status="fail",
                severity="error",
                message="JSON schema file is missing.",
                metadata={"path": str(schema_path)},
            )
            continue
        try:
            orjson.loads(schema_path.read_bytes())
        except orjson.JSONDecodeError as exc:
            _doctor_check(
                checks,
                check_id=f"schema:{schema_path.name}",
                status="fail",
                severity="error",
                message="JSON schema file is not valid JSON.",
                metadata={"path": str(schema_path), "error": str(exc)},
            )
            continue
        _doctor_check(
            checks,
            check_id=f"schema:{schema_path.name}",
            status="pass",
            severity="info",
            message="JSON schema file is present and parseable.",
            metadata={"path": str(schema_path)},
        )


def _doctor_catalog_checks(checks: list[dict[str, object]]) -> None:
    languages = language_payload()
    tools_payload = catalog_payload()
    language_rows = cast(Sequence[Mapping[str, object]], languages["languages"])
    tool_rows = cast(Sequence[Mapping[str, object]], tools_payload["tools"])
    language_codes = {str(row.get("code")) for row in language_rows}
    tool_filters = {
        (str(row.get("language")), str(row.get("tool_filter")))
        for row in tool_rows
        if row.get("language") and row.get("tool_filter")
    }
    expected_languages = {"lat", "grc", "san"}
    expected_tools = {
        ("lat", "gaffiot"),
        ("grc", "diogenes"),
        ("san", "cdsl"),
        ("san", "dico"),
        ("san", "heritage"),
    }
    missing_languages = sorted(expected_languages - language_codes)
    missing_tools = sorted(expected_tools - tool_filters)
    if missing_languages or missing_tools:
        _doctor_check(
            checks,
            check_id="catalog:surface",
            status="fail",
            severity="error",
            message="CLI self-description is missing expected languages or tools.",
            metadata={"missing_languages": missing_languages, "missing_tools": missing_tools},
        )
        return
    _doctor_check(
        checks,
        check_id="catalog:surface",
        status="pass",
        severity="info",
        message="CLI self-description exposes expected language and tool surface.",
        metadata={"languages": sorted(language_codes), "tool_count": len(tool_rows)},
    )


def _doctor_translation_checks(
    checks: list[dict[str, object]],
    *,
    translation_cache_db: str,
    require_openai_key: bool,
) -> None:
    cache_path = Path(translation_cache_db)
    cache_status = _translation_cache_status_payload(cache_path)
    cache_error = cache_status.get("error")
    cache_parent = cache_path.parent
    parent_ready = (
        cache_parent.exists()
        and os.access(cache_parent, os.W_OK)
        or (
            not cache_parent.exists()
            and cache_parent.parent.exists()
            and os.access(cache_parent.parent, os.W_OK)
        )
    )
    if parent_ready:
        row_count = cache_status["row_count"]
        _doctor_check(
            checks,
            check_id="translation_cache:path",
            status="pass",
            severity="info",
            message="Translation cache directory exists or can be created.",
            metadata={
                "cache_db": str(cache_path),
                "exists": bool(cache_status["exists"]),
                "row_count": row_count if isinstance(row_count, int) else 0,
            },
        )
    else:
        _doctor_check(
            checks,
            check_id="translation_cache:path",
            status="fail",
            severity="error",
            message="Translation cache directory is missing or not writable.",
            metadata={"cache_db": str(cache_path), "parent": str(cache_parent)},
        )

    if cache_error:
        _doctor_check(
            checks,
            check_id="translation_cache:available",
            status="fail",
            severity="error",
            message="Translation cache exists but could not be opened.",
            metadata={"cache_db": str(cache_path), "error": str(cache_error)},
        )
    else:
        _doctor_check(
            checks,
            check_id="translation_cache:available",
            status="pass",
            severity="info",
            message="Translation cache is available or not yet created.",
            metadata={"cache_db": str(cache_path), "exists": bool(cache_status["exists"])},
        )

    aisuite_available = importlib.util.find_spec("aisuite") is not None
    _doctor_check(
        checks,
        check_id="translation:aisuite",
        status="pass" if aisuite_available else "warn",
        severity="info" if aisuite_available else "warning",
        message=(
            "aisuite is importable."
            if aisuite_available
            else "aisuite is not importable; translation population will fail."
        ),
    )

    has_openai_key = bool(os.environ.get("OPENAI_API_KEY"))
    openai_status = "pass" if has_openai_key else ("fail" if require_openai_key else "warn")
    openai_severity = "info" if has_openai_key else ("error" if require_openai_key else "warning")
    _doctor_check(
        checks,
        check_id="translation:openai_key",
        status=openai_status,
        severity=openai_severity,
        message=(
            "OPENAI_API_KEY is set."
            if has_openai_key
            else (
                "OPENAI_API_KEY is not set; cache hits still work, but cache misses cannot "
                "populate."
            )
        ),
    )


def _doctor_optional_tool_checks(checks: list[dict[str, object]]) -> None:
    whitaker_binary = find_whitaker_binary()
    _doctor_check(
        checks,
        check_id="optional_tool:whitakers",
        status="pass" if whitaker_binary else "warn",
        severity="info" if whitaker_binary else "warning",
        message=(
            "Whitaker's Words binary was found."
            if whitaker_binary
            else (
                "Whitaker's Words binary was not found; Latin Whitaker evidence may be unavailable."
            )
        ),
        metadata={"binary": whitaker_binary or ""},
    )


def _doctor_payload(*, translation_cache_db: str, require_openai_key: bool) -> dict[str, object]:
    checks: list[dict[str, object]] = []
    _doctor_schema_checks(checks)
    _doctor_catalog_checks(checks)
    _doctor_translation_checks(
        checks,
        translation_cache_db=translation_cache_db,
        require_openai_key=require_openai_key,
    )
    _doctor_optional_tool_checks(checks)
    failures = [check for check in checks if check["status"] == "fail"]
    warnings = [check for check in checks if check["status"] == "warn"]
    return {
        "schema_version": DOCTOR_SCHEMA_VERSION,
        "ok": not failures,
        "summary": {
            "checks": len(checks),
            "failures": len(failures),
            "warnings": len(warnings),
        },
        "runtime": {
            "python": sys.version.split()[0],
            "cwd": str(Path.cwd()),
        },
        "checks": checks,
    }


@main.command("doctor")
@click.option(
    "--translation-cache-db",
    default="data/cache/langnet.duckdb",
    show_default=True,
    help="DuckDB cache containing entry_translations rows.",
)
@click.option(
    "--require-openai-key",
    is_flag=True,
    help="Fail when OPENAI_API_KEY is not set.",
)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
def doctor(translation_cache_db: str, require_openai_key: bool, output: str) -> None:
    """Check local CLI assumptions without making network calls."""
    payload = _doctor_payload(
        translation_cache_db=translation_cache_db,
        require_openai_key=require_openai_key,
    )
    if output == "json":
        click.echo(orjson.dumps(payload, option=orjson.OPT_INDENT_2).decode("utf-8"))
    else:
        summary = cast(Mapping[str, int], payload["summary"])
        status = "OK" if payload["ok"] else "FAIL"
        click.echo(
            f"Doctor: {status} "
            f"checks={summary['checks']} failures={summary['failures']} "
            f"warnings={summary['warnings']}"
        )
        for check in cast(Sequence[Mapping[str, object]], payload["checks"]):
            click.echo(f"- {check['status']} {check['id']}: {check['message']}")
    if not payload["ok"]:
        raise click.exceptions.Exit(1)


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


def _create_dico_client(tool: str, use_stubs: bool) -> ToolClient | None:
    """Create a local DICO client, with stub fallback."""
    try:
        from langnet.execution.handlers.dico import DicoFetchClient  # noqa: PLC0415

        return DicoFetchClient()
    except Exception:
        if use_stubs:
            return StubToolClient(tool)
    return None


def _create_gaffiot_client(tool: str, use_stubs: bool) -> ToolClient | None:
    """Create a local Gaffiot client, with stub fallback."""
    try:
        from langnet.execution.handlers.gaffiot import GaffiotFetchClient  # noqa: PLC0415

        return GaffiotFetchClient()
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
        "fetch.dico": lambda: _create_dico_client(tool, use_stubs),
        "fetch.gaffiot": lambda: _create_gaffiot_client(tool, use_stubs),
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


def _tool_stage_name(stage: int) -> str:
    try:
        return ToolStage.Name(stage).removeprefix("TOOL_STAGE_").lower()
    except ValueError:
        return str(stage)


def _stage_summary(plan, result) -> dict[str, dict[str, int]]:
    planned = Counter(_tool_stage_name(call.stage) for call in plan.tool_calls)
    produced = {
        "fetch": len(result.raw_effects),
        "extract": len(result.extractions),
        "derive": len(result.derivations),
        "claim": len(result.claims),
    }
    return {
        stage: {"planned": planned.get(stage, 0), "produced": produced.get(stage, 0)}
        for stage in ("fetch", "extract", "derive", "claim")
    }


def _handler_version_rows(result) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for effect in [*result.extractions, *result.derivations, *result.claims]:
        version = getattr(effect, "handler_version", None)
        tool = getattr(effect, "tool", "")
        if not version or not tool:
            continue
        key = (tool, version)
        if key in seen:
            continue
        seen.add(key)
        rows.append({"tool": tool, "handler_version": version})
    return sorted(rows, key=lambda row: (row["tool"], row["handler_version"]))


def _claim_summary_rows(result) -> list[dict[str, str | None]]:
    return [
        {
            "claim_id": claim.claim_id,
            "tool": claim.tool,
            "subject": claim.subject,
            "predicate": claim.predicate,
            "handler_version": claim.handler_version,
        }
        for claim in result.claims
    ]


def _plan_exec_summary_payload(plan, result, *, cache_enabled: bool) -> dict[str, object]:
    cache_status = "disabled"
    if cache_enabled:
        cache_status = "hit" if result.from_cache else "miss"

    return {
        "plan_id": plan.plan_id,
        "plan_hash": plan.plan_hash,
        "cache": {
            "enabled": cache_enabled,
            "status": cache_status,
            "response_refs": len(result.executed.responses),
        },
        "duration_ms": result.executed.execution_time_ms,
        "stages": _stage_summary(plan, result),
        "skipped_calls": [asdict(skip) for skip in result.skipped_calls],
        "handler_versions": _handler_version_rows(result),
        "claims": _claim_summary_rows(result),
    }


def _print_plan_exec_summary(plan, result, *, cache_enabled: bool) -> None:
    payload = _plan_exec_summary_payload(plan, result, cache_enabled=cache_enabled)
    cache = cast(dict[str, object], payload["cache"])
    click.echo("Execution summary:")
    click.echo(
        "  cache: {} (enabled={}, response_refs={})".format(
            cache["status"], cache["enabled"], cache["response_refs"]
        )
    )
    click.echo(f"  duration_ms: {payload['duration_ms']}")
    click.echo("  stage counts:")
    stages = cast(dict[str, dict[str, int]], payload["stages"])
    for stage, counts in stages.items():
        click.echo(f"    - {stage}: planned={counts['planned']} produced={counts['produced']}")

    skipped = cast(list[dict[str, object]], payload["skipped_calls"])
    click.echo("  skipped calls:")
    if not skipped:
        click.echo("    - none")
    else:
        for skip in skipped:
            source = f" source={skip['source_call_id']}" if skip.get("source_call_id") else ""
            click.echo(
                "    - {stage} {tool}#{call_id}: {reason}{source}".format(
                    stage=skip["stage"],
                    tool=skip["tool"],
                    call_id=skip["call_id"],
                    reason=skip["reason"],
                    source=source,
                )
            )

    versions = cast(list[dict[str, str]], payload["handler_versions"])
    click.echo("  handler versions:")
    if not versions:
        click.echo("    - none")
    else:
        for row in versions:
            click.echo(f"    - {row['tool']}: {row['handler_version']}")


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
    normalized = _normalize_with_short_cache_lock(
        norm_cfg,
        text,
        lang_hint,
        use_cache=not config.no_cache,
    )

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

    registry = default_registry(use_stubs=config.use_stub_handlers)
    clients = _build_exec_clients(plan, config.diogenes_endpoint, config.use_stub_handlers)

    if config.no_cache:
        with duckdb.connect(database=":memory:") as conn:
            apply_schema(conn)
            result = execute_plan_staged(
                plan=plan,
                clients=clients,
                registry=registry,
                raw_index=RawResponseIndex(conn),
                extraction_index=ExtractionIndex(conn),
                derivation_index=DerivationIndex(conn),
                claim_index=ClaimIndex(conn),
                plan_response_index=None,
                allow_cache=False,
            )
    else:
        result = execute_plan_staged(
            plan=plan,
            clients=clients,
            registry=registry,
            raw_index=PathRawResponseIndex(path),
            extraction_index=PathExtractionIndex(path),
            derivation_index=PathDerivationIndex(path),
            claim_index=PathClaimIndex(path),
            plan_response_index=PathPlanResponseIndex(path),
            allow_cache=True,
        )

    if config.output == "json":
        payload = _plan_exec_summary_payload(plan, result, cache_enabled=not config.no_cache)
        click.echo(orjson.dumps(payload, option=orjson.OPT_INDENT_2).decode("utf-8"))
        return

    _print_plan(plan, "pretty")
    _print_plan_exec_summary(plan, result, cache_enabled=not config.no_cache)
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
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format for the execution summary.",
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
    output: str,
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
        output=output,
    )
    _plan_exec_impl(config, language, text)


def _get_query_value_for_plan(
    text: str, lang_hint, normalize: bool, norm_cfg: NormalizeConfig
) -> query_spec.NormalizedQuery:
    """Get the query value for planning, either normalized or passthrough."""
    if (
        normalize
        and lang_hint == LanguageHint.LANGUAGE_HINT_GRC
        and _contains_greek_script(text)
        and not _requires_greek_script_normalization(text)
    ):
        return _passthrough_normalized_query(text, lang_hint)

    if normalize:
        normalized_result = _normalize_with_short_cache_lock(norm_cfg, text, lang_hint)
        return normalized_result.normalized

    return _passthrough_normalized_query(text, lang_hint)


def _contains_greek_script(text: str) -> bool:
    return any("\u0370" <= char <= "\u03ff" or "\u1f00" <= char <= "\u1fff" for char in text)


def _requires_greek_script_normalization(text: str) -> bool:
    normalized = strip_accents(text.strip()).casefold()
    return normalized.endswith(("ηος", "ηοσ"))


def _passthrough_normalized_query(text: str, lang_hint) -> query_spec.NormalizedQuery:
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


@main.command("entry-analyze")
@click.argument("text", required=False)
@click.option(
    "--file",
    "text_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Read the source entry from a UTF-8 text file instead of an argument.",
)
@click.option(
    "--source-tool",
    default="unknown",
    show_default=True,
    help="Source label to include in the diagnostic output.",
)
@click.option(
    "--max-items",
    default=12,
    show_default=True,
    type=click.IntRange(1, 50),
    help="Maximum extracted items per category.",
)
@click.option(
    "--output",
    "output_format",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
def entry_analyze(
    text: str | None,
    text_file: Path | None,
    source_tool: str,
    max_items: int,
    output_format: str,
) -> None:
    """
    Inspect one raw dictionary entry for glosses, citations, examples, and references.
    """
    raw_text = _entry_analyze_text(text, text_file)
    payload = analyze_source_entry(raw_text, source_tool=source_tool, max_items=max_items)
    if output_format == "json":
        click.echo(orjson.dumps(payload, option=orjson.OPT_INDENT_2).decode("utf-8"))
        return
    _display_entry_analysis(payload)


def _entry_analyze_text(text: str | None, text_file: Path | None) -> str:
    if text and text_file:
        raise click.UsageError("Pass entry text or --file, not both.")
    if text_file:
        return text_file.read_text(encoding="utf-8")
    if text:
        return text
    raise click.UsageError("Pass entry text or --file.")


def _display_entry_analysis(payload: Mapping[str, object]) -> None:
    click.echo(f"Entry analysis ({payload.get('source_tool', 'unknown')})")
    grammar_parse = payload.get("grammar_parse")
    if isinstance(grammar_parse, Mapping):
        grammar_map = cast(Mapping[str, object], grammar_parse)
        parser = grammar_map.get("parser", "unknown")
        status = "parsed" if grammar_map.get("parsed") is True else "fallback"
        click.echo(f"Grammar: {parser} ({status})")
    learner_gloss = str(payload.get("learner_gloss") or "")
    if learner_gloss:
        click.echo(f"Learner gloss: {learner_gloss}")
    _display_entry_analysis_items("Gloss candidates", payload.get("gloss_candidates"))
    _display_entry_analysis_items("Citations", payload.get("citations"))
    _display_entry_analysis_items("Source references", payload.get("source_references"))
    _display_entry_analysis_items("Examples", payload.get("examples"))
    _display_entry_analysis_items("Source segments", payload.get("source_segments"))


def _display_entry_analysis_items(label: str, value: object) -> None:
    if not isinstance(value, list) or not value:
        return
    click.echo(label + ":")
    for item in value:
        if not isinstance(item, Mapping):
            continue
        item_map = cast(Mapping[str, object], item)
        text = str(item_map.get("text") or item_map.get("display_text") or "")
        if not text:
            continue
        kind = str(item_map.get("kind") or item_map.get("segment_type") or "")
        prefix = f"  - [{kind}] " if kind else "  - "
        suffix = ""
        citation = item_map.get("citation")
        if citation:
            suffix = f" ({citation})"
        click.echo(f"{prefix}{text}{suffix}")


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
@click.option(
    "--predicate",
    "predicate_filter",
    help="Only display triples with this exact predicate.",
)
@click.option(
    "--subject-prefix",
    "subject_filter",
    help="Only display triples whose subject starts with this prefix.",
)
@click.option(
    "--max-triples",
    default=10,
    show_default=True,
    type=int,
    help="Maximum matching triples to print per claim.",
)
@click.option(
    "--output",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
    help="Output format.",
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
    predicate_filter: str | None,
    subject_filter: str | None,
    max_triples: int,
    output_format: str,
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

    if output_format == "json":
        payload = build_triples_dump_payload(
            language=language,
            text=text,
            normalized_candidates=[candidate.lemma for candidate in query_value.candidates],
            tool_filter=tool_filter,
            predicate_filter=predicate_filter,
            subject_filter=subject_filter,
            max_triples=max_triples,
            result=result,
            include_dico_resolutions=lang_hint == LanguageHint.LANGUAGE_HINT_SAN,
        )
        click.echo(orjson.dumps(payload, option=orjson.OPT_INDENT_2).decode("utf-8"))
        return

    display_claim_triples(result, predicate_filter, subject_filter, max_triples)
    if lang_hint == LanguageHint.LANGUAGE_HINT_SAN:
        display_dico_resolutions(result, predicate_filter, subject_filter, max_triples)


def _claims_as_mappings(result) -> list[Mapping[str, object]]:
    return [cast(Mapping[str, object], asdict(claim)) for claim in result.claims]


def _encounter_should_retry_uncached(
    *,
    normalize: bool,
    no_cache: bool,
    tool_filter: str,
    reduction,
) -> bool:
    if not normalize or no_cache or reduction.buckets:
        return False
    return tool_filter.lower() not in {"heritage", "claim.heritage.morph"}


def _shorten(text: str, max_chars: int) -> str:
    return shorten_text(text, max_chars)


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out


def _encounter_bucket_gloss(bucket) -> str:
    witness = bucket.witnesses[0] if bucket.witnesses else None
    if witness is None:
        return bucket.display_gloss
    display_gloss = witness.evidence.get("display_gloss")
    if isinstance(display_gloss, str) and display_gloss:
        return display_gloss
    if witness.source_tool != "cdsl" and witness.evidence.get("source_tool") != "cdsl":
        return bucket.display_gloss
    display_iast = witness.evidence.get("display_iast")
    display_slp1 = witness.evidence.get("display_slp1")
    return cdsl_handlers.cdsl_text_to_iast_display(
        bucket.display_gloss,
        source_slp1=display_slp1 if isinstance(display_slp1, str) else "",
        display_iast=display_iast if isinstance(display_iast, str) else "",
    )


def _encounter_bucket_learner_gloss(
    bucket,
    *,
    max_chars: int = ENCOUNTER_LEARNER_GLOSS_MAX_CHARS,
) -> str:
    witness = bucket.witnesses[0] if bucket.witnesses else None
    if witness is None:
        return _encounter_compact_gloss(bucket.display_gloss, max_chars=max_chars)

    parsed_glosses = _encounter_string_sequence(witness.evidence.get("parsed_glosses"))
    if parsed_glosses:
        return _shorten(
            ", ".join(_dedupe_preserve_order(parsed_glosses)[:ENCOUNTER_LEARNER_GLOSS_ITEM_LIMIT]),
            max_chars,
        )

    learner_gloss = witness.evidence.get("learner_gloss")
    if isinstance(learner_gloss, str) and learner_gloss:
        return _encounter_compact_gloss(learner_gloss, max_chars=max_chars)

    translated_segments = witness.evidence.get("translated_segments")
    segment_gloss = _encounter_first_segment_display(translated_segments)
    if segment_gloss:
        return _encounter_compact_gloss(segment_gloss, max_chars=max_chars)

    return _encounter_compact_gloss(_encounter_bucket_gloss(bucket), max_chars=max_chars)


def _encounter_string_sequence(value: object) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [text for item in value if (text := str(item).strip())]


def _encounter_first_segment_display(segments: object) -> str:
    if not isinstance(segments, Sequence) or isinstance(segments, (str, bytes)):
        return ""
    for segment in segments:
        if not isinstance(segment, Mapping):
            continue
        segment_mapping = cast(Mapping[str, object], segment)
        display_text = segment_mapping.get("display_text")
        if isinstance(display_text, str) and display_text.strip():
            return display_text.strip()
    return ""


def _encounter_compact_gloss(
    gloss: str,
    *,
    max_chars: int = ENCOUNTER_LEARNER_GLOSS_MAX_CHARS,
) -> str:
    return compact_source_gloss(gloss, max_chars=max_chars)


def _encounter_claim_triples(claim: Mapping[str, object]) -> list[Mapping[str, object]]:
    value = claim.get("value")
    if not isinstance(value, Mapping):
        return []
    value_dict = cast(dict[str, object], value)
    triples = value_dict.get("triples")
    if not isinstance(triples, list):
        return []
    return [cast(Mapping[str, object], triple) for triple in triples if isinstance(triple, Mapping)]


_MORPHOLOGY_FEATURE_PREDICATES = {
    predicates.HAS_POS,
    predicates.HAS_CASE,
    predicates.HAS_NUMBER,
    predicates.HAS_GENDER,
    predicates.HAS_PERSON,
    predicates.HAS_TENSE,
    predicates.HAS_VOICE,
    predicates.HAS_MOOD,
    predicates.HAS_DEGREE,
    predicates.HAS_DECLENSION,
    predicates.HAS_CONJUGATION,
}


@dataclass
class _MorphologyGraph:
    interp_to_form: dict[str, str]
    interp_to_lexeme: dict[str, str]
    interp_features: dict[str, list[str]]
    interp_source_tools: dict[str, str]
    form_to_lexeme: dict[str, str]
    form_features: dict[str, list[str]]
    form_source_tools: dict[str, str]


def _encounter_morphology_rows(
    claims: Sequence[Mapping[str, object]],
    *,
    language: str = "",
    original: str = "",
    reduction=None,
    max_rows: int = 4,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str]] = set()
    claim_triples = _encounter_claim_triples_with_tools(claims)
    if _append_direct_morphology_rows(claim_triples, rows, seen, max_rows):
        return rows

    graph = _build_morphology_graph(claim_triples)
    _append_graph_morphology_rows(graph, rows, seen, max_rows)
    if not rows and reduction is not None:
        rows.extend(
            _encounter_local_morphology_rows(
                language=language,
                original=original,
                reduction=reduction,
                max_rows=max_rows,
            )
        )
    return rows


def _encounter_claim_triples_with_tools(
    claims: Sequence[Mapping[str, object]],
) -> list[tuple[str, Mapping[str, object]]]:
    triples: list[tuple[str, Mapping[str, object]]] = []
    for claim in claims:
        claim_tool = str(claim.get("tool") or "")
        triples.extend((claim_tool, triple) for triple in _encounter_claim_triples(claim))
    return triples


def _append_morphology_row(
    rows: list[dict[str, str]],
    seen: set[tuple[str, str, str, str]],
    max_rows: int,
    row: dict[str, str],
) -> bool:
    analysis = row["analysis"].strip()
    if not analysis or analysis == "?":
        return False
    row = {**row, "analysis": analysis}
    key = (row["source_tool"], row["form"], row["lemma"], row["analysis"])
    if key in seen:
        return False
    seen.add(key)
    rows.append(row)
    return len(rows) >= max_rows


def _append_direct_morphology_rows(
    claim_triples: Sequence[tuple[str, Mapping[str, object]]],
    rows: list[dict[str, str]],
    seen: set[tuple[str, str, str, str]],
    max_rows: int,
) -> bool:
    for claim_tool, triple in claim_triples:
        row = _direct_morphology_row(claim_tool, triple)
        if row is None:
            continue
        if _append_morphology_row(rows, seen, max_rows, row):
            return True
    return False


def _direct_morphology_row(
    claim_tool: str,
    triple: Mapping[str, object],
) -> dict[str, str] | None:
    if triple.get("predicate") != predicates.HAS_MORPHOLOGY:
        return None
    obj = triple.get("object")
    if not isinstance(obj, Mapping):
        return None
    obj_dict = cast(dict[str, object], obj)
    row = {
        "source_tool": _encounter_triple_source_tool(triple, claim_tool),
        "form": str(obj_dict.get("form") or triple.get("subject") or "").removeprefix("form:"),
        "lemma": str(obj_dict.get("lemma") or "").removeprefix("lex:"),
        "analysis": str(obj_dict.get("analysis") or "").strip(),
    }
    solution_number = obj_dict.get("solution_number")
    if solution_number is not None:
        row["solution_number"] = str(solution_number)
    return row


def _build_morphology_graph(
    claim_triples: Sequence[tuple[str, Mapping[str, object]]],
) -> _MorphologyGraph:
    graph = _MorphologyGraph(
        interp_to_form={},
        interp_to_lexeme={},
        interp_features={},
        interp_source_tools={},
        form_to_lexeme={},
        form_features={},
        form_source_tools={},
    )
    for claim_tool, triple in claim_triples:
        subject = str(triple.get("subject") or "")
        predicate = str(triple.get("predicate") or "")
        obj = triple.get("object")
        source_tool = _encounter_triple_source_tool(triple, claim_tool)
        if _record_morphology_link(graph, subject, predicate, obj, source_tool):
            continue
        _record_morphology_feature(graph, subject, predicate, obj, source_tool)
    return graph


def _record_morphology_link(
    graph: _MorphologyGraph,
    subject: str,
    predicate: str,
    obj: object,
    source_tool: str,
) -> bool:
    if (
        predicate == predicates.HAS_INTERPRETATION
        and subject.startswith("form:")
        and isinstance(obj, str)
        and obj.startswith("interp:")
    ):
        graph.interp_to_form.setdefault(obj, subject.removeprefix("form:"))
        graph.interp_source_tools.setdefault(obj, source_tool)
        return True
    if (
        predicate == predicates.REALIZES_LEXEME
        and subject.startswith("interp:")
        and isinstance(obj, str)
    ):
        graph.interp_to_lexeme.setdefault(subject, _display_lexeme_anchor(obj))
        graph.interp_source_tools.setdefault(subject, source_tool)
        return True
    if (
        predicate == predicates.INFLECTION_OF
        and subject.startswith("form:")
        and isinstance(obj, str)
    ):
        form = subject.removeprefix("form:")
        graph.form_to_lexeme.setdefault(form, _display_lexeme_anchor(obj))
        graph.form_source_tools.setdefault(form, source_tool)
        return True
    return False


def _record_morphology_feature(
    graph: _MorphologyGraph,
    subject: str,
    predicate: str,
    obj: object,
    source_tool: str,
) -> None:
    if subject.startswith("interp:") and predicate in _MORPHOLOGY_FEATURE_PREDICATES:
        values = _encounter_morphology_feature_values(predicate, obj)
        if values:
            graph.interp_features.setdefault(subject, []).extend(values)
            graph.interp_source_tools.setdefault(subject, source_tool)
        return
    if subject.startswith("form:") and (
        predicate in _MORPHOLOGY_FEATURE_PREDICATES or predicate == predicates.HAS_FEATURE
    ):
        values = _encounter_morphology_feature_values(predicate, obj)
        if values:
            form = subject.removeprefix("form:")
            graph.form_features.setdefault(form, []).extend(values)
            graph.form_source_tools.setdefault(form, source_tool)


def _append_graph_morphology_rows(
    graph: _MorphologyGraph,
    rows: list[dict[str, str]],
    seen: set[tuple[str, str, str, str]],
    max_rows: int,
) -> bool:
    for interp, features in graph.interp_features.items():
        form = graph.interp_to_form.get(interp)
        lemma = graph.interp_to_lexeme.get(interp)
        if not form or not lemma:
            continue
        source_tool = graph.interp_source_tools.get(interp, "")
        analysis = _encounter_morphology_analysis(features)
        row = {"source_tool": source_tool, "form": form, "lemma": lemma, "analysis": analysis}
        if _append_morphology_row(rows, seen, max_rows, row):
            return True

    for form, features in graph.form_features.items():
        lemma = graph.form_to_lexeme.get(form, form)
        source_tool = graph.form_source_tools.get(form, "")
        analysis = _encounter_morphology_analysis(features)
        row = {"source_tool": source_tool, "form": form, "lemma": lemma, "analysis": analysis}
        if _append_morphology_row(rows, seen, max_rows, row):
            return True
    return False


def _encounter_triple_source_tool(triple: Mapping[str, object], claim_tool: str) -> str:
    metadata = triple.get("metadata")
    metadata_dict = cast(dict[str, object], metadata) if isinstance(metadata, Mapping) else {}
    evidence = metadata_dict.get("evidence")
    if isinstance(evidence, Mapping):
        evidence_dict = cast(dict[str, object], evidence)
        source_tool = str(evidence_dict.get("source_tool") or "")
        if source_tool:
            return source_tool
    return claim_tool.replace("claim.", "").split(".", 1)[0]


def _display_lexeme_anchor(value: str) -> str:
    lemma = value.removeprefix("lex:")
    return lemma.split("#", 1)[0]


def _encounter_morphology_feature_values(predicate: str, obj: object) -> list[str]:
    if predicate == predicates.HAS_FEATURE:
        return _encounter_feature_bag_morphology_values(obj)

    value = "" if obj is None else str(obj).strip()
    if not value or value == "?":
        return []
    prefixes = {
        predicates.HAS_DECLENSION: "declension",
        predicates.HAS_CONJUGATION: "conjugation",
        predicates.HAS_DEGREE: "degree",
    }
    prefix = prefixes.get(predicate)
    return [f"{prefix} {value}" if prefix else value]


def _encounter_feature_bag_morphology_values(obj: object) -> list[str]:
    if not isinstance(obj, Mapping):
        return []
    obj_dict = cast(Mapping[str, object], obj)
    tags = obj_dict.get("tags")
    if isinstance(tags, Sequence) and not isinstance(tags, (str, bytes)):
        tag_values = [str(tag) for tag in tags if str(tag)]
        if tag_values:
            return [f"tags: {', '.join(tag_values)}"]
    notes = obj_dict.get("notes")
    return [str(notes)] if isinstance(notes, str) and notes else []


def _encounter_morphology_analysis(features: Sequence[str]) -> str:
    return "; ".join(_dedupe_preserve_order([feature for feature in features if feature]))


def _encounter_foster_display(language: str, analysis: str) -> str:
    return foster_display_for_analysis(language, analysis)


def _encounter_foster_display_alternative(language: str, analysis: str) -> str:
    return foster_display_for_analysis(language, analysis)


def _encounter_foster_features_from_analysis(analysis: str) -> dict[str, str]:
    return foster_features_from_analysis(analysis)


def _encounter_morphology_fallback_terms(
    claims: Sequence[Mapping[str, object]],
    *,
    language: str,
    original: str,
    max_terms: int = 2,
) -> list[str]:
    if language != "san":
        return []

    morphology_rows = _encounter_morphology_rows(claims, max_rows=8)
    if any(_is_sanskrit_compound_component(row["analysis"]) for row in morphology_rows):
        return []

    candidates = _encounter_sanskrit_morphology_fallback_candidates(
        morphology_rows,
        original=original,
    )
    if not candidates:
        return []
    selected_candidates = _encounter_preferred_sanskrit_morphology_candidates(candidates)
    return _encounter_candidate_terms(selected_candidates, max_terms=max_terms)


def _encounter_sanskrit_morphology_fallback_candidates(
    morphology_rows: Sequence[Mapping[str, str]],
    *,
    original: str,
) -> list[tuple[int | None, int, str]]:
    original_norm = original.strip().lower()
    candidates: list[tuple[int | None, int, str]] = []
    for row in morphology_rows:
        term = _encounter_sanskrit_candidate_term(row, original_norm=original_norm)
        if not term:
            continue
        candidates.append((_encounter_morphology_solution_number(row), len(candidates), term))
    return candidates


def _encounter_sanskrit_candidate_term(
    row: Mapping[str, str],
    *,
    original_norm: str,
) -> str:
    form = row["form"].strip()
    lemma = row["lemma"].strip()
    analysis = row["analysis"].strip()
    term = _encounter_sanskrit_morphology_lookup_term(lemma)
    if not term or analysis == "?":
        return ""
    if form != lemma:
        return ""
    if term.lower() == original_norm:
        return ""
    if "_" in term:
        return ""
    return term


def _encounter_candidate_terms(
    candidates: Sequence[tuple[int | None, int, str]],
    *,
    max_terms: int,
) -> list[str]:
    terms: list[str] = []
    for _solution_number, _index, term in candidates:
        if term not in terms:
            terms.append(term)
        if len(terms) >= max_terms:
            break
    return terms


def _encounter_sanskrit_morphology_lookup_term(lemma: str) -> str:
    lemma = lemma.strip()
    if not lemma or lemma == "?":
        return ""
    return re.sub(r"_\d+$", "", lemma)


def _encounter_morphology_solution_number(row: Mapping[str, str]) -> int | None:
    raw = row.get("solution_number")
    if raw is None:
        return None
    with suppress(ValueError):
        return int(raw)
    return None


def _encounter_preferred_sanskrit_morphology_candidates(
    candidates: Sequence[tuple[int | None, int, str]],
) -> list[tuple[int | None, int, str]]:
    numbered = [candidate for candidate in candidates if candidate[0] is not None]
    if not numbered:
        return list(candidates)

    solution_sizes: dict[int, int] = {}
    for solution_number, _index, _term in numbered:
        if solution_number is None:
            continue
        solution_sizes[solution_number] = solution_sizes.get(solution_number, 0) + 1
    if not solution_sizes:
        return list(candidates)

    smallest_solution_size = min(solution_sizes.values())
    preferred_solutions = {
        solution_number
        for solution_number, size in solution_sizes.items()
        if size == smallest_solution_size
    }
    return [candidate for candidate in candidates if candidate[0] in preferred_solutions]


def _is_sanskrit_compound_component(analysis: str) -> bool:
    analysis = analysis.strip()
    return analysis == "iic." or analysis.startswith("iic ")


def _encounter_local_morphology_rows(
    *,
    language: str,
    original: str,
    reduction,
    max_rows: int,
) -> list[dict[str, str]]:
    if not original:
        return []
    if language == "lat":
        row = _encounter_latin_local_morphology_row(original, reduction)
        return [row] if row else []
    if language == "grc":
        row = _encounter_greek_local_morphology_row(original, reduction)
        return [row] if row else []
    return []


def _encounter_latin_local_morphology_row(original: str, reduction) -> dict[str, str] | None:
    surface = original.strip()
    lower = surface.lower()
    if not lower.endswith("ae") or len(lower) <= LATIN_AE_SUFFIX_LEN:
        return None
    lemma = f"{lower[:-2]}a"
    reduction_lemmas = {value.lower() for value in _encounter_reduction_lemma_values(reduction)}
    if lemma not in reduction_lemmas:
        return None
    return {
        "source_tool": "local",
        "form": surface,
        "lemma": lemma,
        "analysis": (
            "first-declension -ae form; genitive/dative singular or nominative/vocative plural"
        ),
    }


def _encounter_greek_local_morphology_row(original: str, reduction) -> dict[str, str] | None:
    surface = original.strip()
    normalized_surface = strip_accents(surface).casefold()
    if not normalized_surface.endswith(("ηος", "ηοσ")):
        return None
    lemma = _encounter_first_reduction_lemma_with_suffix(reduction, "eus")
    if not lemma:
        return None
    return {
        "source_tool": "local",
        "form": surface,
        "lemma": lemma,
        "analysis": "epic genitive singular; -ῆος form of a -εύς noun",
    }


def _encounter_first_reduction_lemma_with_suffix(reduction, suffix: str) -> str:
    for value in _encounter_reduction_lemma_values(reduction):
        clean = re.sub(r"[^A-Za-z]+", "", value).lower()
        if clean.endswith(suffix):
            return value
    return ""


def _encounter_reduction_lemma_values(reduction) -> list[str]:
    return reduction_lemma_values(reduction)


def _encounter_preferred_lemmas_from_reduction(reduction) -> list[str]:
    return preferred_lemmas_from_reduction(reduction)


def _encounter_sanskrit_morphology_lookup_terms(
    *,
    claims: Sequence[Mapping[str, object]],
    language: str,
    original: str,
    tool_filter: str,
    reduction,
) -> tuple[list[str], str | None]:
    if language != "san" or tool_filter.lower() in {"heritage", "claim.heritage.morph"}:
        return [], None

    terms = _encounter_morphology_fallback_terms(
        claims,
        language=language,
        original=original,
    )
    if not terms:
        return [], None
    if not reduction.buckets:
        return (
            terms,
            "No sense buckets for surface form; followed Sanskrit morphology lemma "
            "for meaning evidence.",
        )

    if len(terms) != 1:
        return [], None
    reduction_lemmas = {value.lower() for value in _encounter_reduction_lemma_values(reduction)}
    if terms[0].lower() in reduction_lemmas:
        return [], None
    return (
        terms,
        "Followed Sanskrit morphology lemma for additional meaning evidence.",
    )


def _encounter_cdsl_source_order(bucket) -> int:
    return cdsl_source_order(bucket)


def _encounter_cdsl_dictionary_order(bucket) -> int:
    return cdsl_dictionary_order(bucket)


def _encounter_bucket_learner_quality_order(bucket) -> int:
    return bucket_learner_quality_order(bucket, bucket_gloss=_encounter_bucket_gloss)


def _encounter_bucket_quality_text(bucket) -> str:
    return bucket_quality_text(bucket, bucket_gloss=_encounter_bucket_gloss)


def _encounter_bucket_source_tools(bucket) -> set[str]:
    return bucket_source_tools(bucket)


def _encounter_gaffiot_source_order(bucket) -> int:
    return gaffiot_source_order(bucket)


def _encounter_source_order(bucket, source_tool: str) -> int:
    return generic_source_order(bucket, source_tool)


def _encounter_diogenes_source_order(bucket) -> tuple[int, ...]:
    return diogenes_source_order(bucket)


def _encounter_bucket_lemma_values(bucket) -> list[str]:
    return bucket_lemma_values(bucket)


def _encounter_normalize_lemma(value: str) -> str:
    return normalize_lemma(value)


def _encounter_lemma_compare_keys(value: str) -> set[str]:
    return lemma_compare_keys(value)


def _encounter_preferred_lemmas_from_morphology(
    morphology_rows: Sequence[Mapping[str, str]],
) -> list[str]:
    return preferred_lemmas_from_morphology(morphology_rows)


def _encounter_preferred_lemmas_for_sorting(
    reduction,
    morphology_rows: Sequence[Mapping[str, str]],
    fallback_terms: Sequence[str] = (),
) -> list[str]:
    return preferred_lemmas_for_sorting(reduction, morphology_rows, fallback_terms)


def _encounter_morphology_lemma_preference_key(
    row: Mapping[str, str],
    idx: int,
) -> tuple[int, int]:
    return morphology_lemma_preference_key(row, idx)


def _encounter_preferred_lemma_rank(
    bucket,
    preferred_lemmas: Sequence[str],
) -> int:
    return preferred_lemma_rank(bucket, preferred_lemmas)


def _encounter_effective_preferred_lemma_rank(
    bucket,
    preferred_lemmas: Sequence[str],
    learner_quality_order: int,
) -> int:
    return effective_preferred_lemma_rank(bucket, preferred_lemmas, learner_quality_order)


def _encounter_bucket_sort_key(
    bucket,
    preferred_lemmas: Sequence[str] = (),
) -> tuple[int, int, int, int, int, int, tuple[int, ...], int, str]:
    return bucket_sort_key(
        bucket,
        preferred_lemmas,
        bucket_gloss=_encounter_bucket_gloss,
    )


def _openrouter_translation_callback(model: str):
    client = None

    def translate(projection) -> str:
        nonlocal client
        if client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise click.ClickException("Set OPENAI_API_KEY before populating translations.")
            api_base = os.getenv(
                "OPENAI_API_BASE",
                os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1"),
            )
            os.environ["OPENAI_BASE_URL"] = api_base
            try:
                import aisuite as ai  # noqa: PLC0415
            except ImportError as exc:
                raise click.ClickException("aisuite is required to populate translations.") from exc
            client = ai.Client({"api_key": api_key})

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": BASE_SYSTEM},
                {"role": "system", "content": projection.hint},
                {"role": "user", "content": projection.source_text},
            ],
        )
        content = response.choices[0].message.content or ""
        return content.replace("*", "").strip()

    return translate


def _encounter_translation_callback(model: str):
    translate = _openrouter_translation_callback(model)

    def _translate_with_progress(projection) -> str:
        source = projection.source
        label = f"{source.source_lexicon}:{source.entry_id}:{source.occurrence}"
        sent_chars = len(projection.source_text)
        click.echo(
            f"translation start: {label} source_chars={sent_chars} sent_chars={sent_chars}",
            err=True,
        )
        start = time.perf_counter()
        try:
            translated = translate(projection)
        except Exception:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            click.echo(f"translation failed: {label} elapsed_ms={elapsed_ms}", err=True)
            raise
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        click.echo(
            f"translation finished: {label} elapsed_ms={elapsed_ms} output_chars={len(translated)}",
            err=True,
        )
        return translated

    return _translate_with_progress


def _resolve_translation_mode(use_translation_cache: bool, translation_mode: str) -> str:
    return resolve_translation_mode(use_translation_cache, translation_mode)


def _encounter_translation_diagnostics(
    *,
    mode: str,
    cache_path: Path,
    model: str,
    populate: bool,
) -> dict[str, object]:
    return encounter_translation_diagnostics(
        mode=mode,
        cache_path=cache_path,
        model=model,
        populate=populate,
    )


def _encounter_apply_translation_cache(  # noqa: PLR0913
    *,
    claims: Sequence[Mapping[str, object]],
    language: str,
    model: str,
    cache: TranslationCache,
    populate: bool,
    translate,
    diagnostics: dict[str, object],
    context: str,
) -> list[Mapping[str, object]]:
    return apply_translation_cache(
        claims=claims,
        language=language,
        model=model,
        cache=cache,
        populate=populate,
        translate=translate,
        diagnostics=diagnostics,
        context=context,
    )


def _execute_lookup_plan(  # noqa: PLR0913
    *,
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
        return execute_plan_staged(
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


def _translation_warm_terms(wordlist: Path, *, limit: int | None = None) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for raw_line in wordlist.read_text(encoding="utf-8").splitlines():
        term = raw_line.split("#", 1)[0].strip()
        if not term or term in seen:
            continue
        terms.append(term)
        seen.add(term)
        if limit is not None and len(terms) >= limit:
            break
    return terms


def _add_translation_counts(
    total: dict[str, int],
    counts: Mapping[str, int],
    *,
    prefix: str = "",
) -> None:
    add_translation_counts(total, counts, prefix=prefix)


def _empty_translation_counts() -> dict[str, int]:
    return empty_translation_counts()


def _merge_translation_counts(total: dict[str, int], counts: Mapping[str, int]) -> None:
    merge_translation_counts(total, counts)


def _translation_cache_count_rows(conn: duckdb.DuckDBPyConnection) -> int:
    try:
        row = conn.execute("SELECT COUNT(*) FROM entry_translations").fetchone()
    except duckdb.CatalogException:
        return 0
    return int(row[0]) if row is not None else 0


def _translation_cache_group_counts(conn: duckdb.DuckDBPyConnection, column: str) -> dict[str, int]:
    try:
        rows = conn.execute(
            f"""
            SELECT COALESCE({column}, ''), COUNT(*)
            FROM entry_translations
            GROUP BY 1
            ORDER BY 1
            """
        ).fetchall()
    except duckdb.CatalogException:
        return {}
    return {str(key or "unknown"): int(count) for key, count in rows}


def _translation_cache_status_payload(cache_path: Path) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": TRANSLATION_CACHE_SCHEMA_VERSION,
        "cache_db": str(cache_path),
        "exists": cache_path.exists(),
        "available": True,
        "row_count": 0,
        "status_counts": {},
        "source_lexicon_counts": {},
        "model_counts": {},
    }
    if not cache_path.exists():
        return payload
    try:
        with connect_duckdb(cache_path, read_only=False, lock=True) as conn:
            payload["row_count"] = _translation_cache_count_rows(conn)
            payload["status_counts"] = _translation_cache_group_counts(conn, "status")
            payload["source_lexicon_counts"] = _translation_cache_group_counts(
                conn,
                "source_lexicon",
            )
            payload["model_counts"] = _translation_cache_group_counts(conn, "model")
    except FileLockTimeout as exc:
        payload["available"] = False
        payload["error"] = f"Timed out waiting for DuckDB cache lock: {exc}"
    except Exception as exc:  # noqa: BLE001
        payload["available"] = False
        payload["error"] = str(exc)
    return payload


def _translation_cache_clear_payload(cache_path: Path) -> dict[str, object]:
    before = _translation_cache_status_payload(cache_path)
    if before.get("error"):
        return {
            "schema_version": TRANSLATION_CACHE_SCHEMA_VERSION,
            "cache_db": str(cache_path),
            "deleted": 0,
            "before": before,
            "after": before,
            "error": before["error"],
        }
    row_count = before["row_count"]
    deleted = row_count if isinstance(row_count, int) else 0
    if cache_path.exists():
        with connect_duckdb(cache_path, read_only=False, lock=True) as conn:
            apply_translation_schema(conn)
            conn.execute("DELETE FROM entry_translations")
    after = _translation_cache_status_payload(cache_path)
    return {
        "schema_version": TRANSLATION_CACHE_SCHEMA_VERSION,
        "cache_db": str(cache_path),
        "deleted": deleted,
        "before": before,
        "after": after,
    }


@click.group("translation-cache")
def translation_cache_cli() -> None:
    """Inspect and clear cached DICO/Gaffiot translation rows."""


@translation_cache_cli.command("status")
@click.option(
    "--translation-cache-db",
    default="data/cache/langnet.duckdb",
    show_default=True,
    help="DuckDB cache containing entry_translations rows.",
)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
def translation_cache_status(translation_cache_db: str, output: str) -> None:
    """Show translation cache row counts."""
    payload = _translation_cache_status_payload(Path(translation_cache_db))
    if output == "json":
        click.echo(orjson.dumps(payload, option=orjson.OPT_INDENT_2).decode("utf-8"))
        return

    click.echo(
        f"Translation cache: {payload['cache_db']} "
        f"exists={payload['exists']} rows={payload['row_count']}"
    )
    status_counts = cast(Mapping[str, int], payload["status_counts"])
    if status_counts:
        click.echo(
            "Statuses: " + ", ".join(f"{status}={count}" for status, count in status_counts.items())
        )


@translation_cache_cli.command("clear")
@click.option(
    "--translation-cache-db",
    default="data/cache/langnet.duckdb",
    show_default=True,
    help="DuckDB cache containing entry_translations rows.",
)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.confirmation_option(
    "--yes",
    prompt="Delete all cached DICO/Gaffiot translation rows?",
)
def translation_cache_clear(translation_cache_db: str, output: str) -> None:
    """Delete cached DICO/Gaffiot translation rows only."""
    payload = _translation_cache_clear_payload(Path(translation_cache_db))
    if output == "json":
        click.echo(orjson.dumps(payload, option=orjson.OPT_INDENT_2).decode("utf-8"))
        return

    click.echo(f"Cleared {payload['deleted']} translation row(s) from {payload['cache_db']}.")


main.add_command(translation_cache_cli)


@main.command("translation-warm")
@click.argument("language", type=click.Choice(["lat", "san"], case_sensitive=False))
@click.argument(
    "wordlist",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--tool-filter",
    default="all",
    show_default=True,
    help="Restrict lookup tools before collecting DICO/Gaffiot translation candidates.",
)
@click.option(
    "--limit",
    type=click.IntRange(min=1),
    help="Maximum number of non-empty wordlist terms to process.",
)
@click.option(
    "--normalize/--no-normalize",
    default=True,
    show_default=True,
    help="Normalize input before querying tools.",
)
@click.option(
    "--diogenes-endpoint",
    default="http://localhost:8888/Diogenes.cgi",
    show_default=True,
    help="Diogenes CGI endpoint.",
)
@click.option(
    "--diogenes-parse-endpoint",
    default=None,
    help="Optional Diogenes morphology endpoint.",
)
@click.option(
    "--heritage-base",
    default="http://localhost:48080",
    show_default=True,
    help="Base URL for Heritage Platform.",
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
    help="Skip normalization cache lookups and writes for each lookup.",
)
@click.option(
    "--include-cltk/--no-include-cltk",
    default=False,
    show_default=True,
    help="Include CLTK in the plan (may be slow due to warmup).",
)
@click.option(
    "--translation-cache-db",
    default="data/cache/langnet.duckdb",
    show_default=True,
    help="DuckDB cache receiving entry_translations rows.",
)
@click.option(
    "--translation-model",
    default="openai:google/gemini-3.1-pro-preview",
    show_default=True,
    help="Model id used when computing translation cache keys.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Inspect cache hits/misses without calling the translation model or writing rows.",
)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
def translation_warm(  # noqa: PLR0913, PLR0915
    language: str,
    wordlist: Path,
    tool_filter: str,
    limit: int | None,
    normalize: bool,
    diogenes_endpoint: str,
    diogenes_parse_endpoint: str | None,
    heritage_base: str,
    db_path: str | None,
    no_cache: bool,
    include_cltk: bool,
    translation_cache_db: str,
    translation_model: str,
    dry_run: bool,
    output: str,
) -> None:
    """Warm DICO/Gaffiot translation cache rows for a word list."""
    terms = _translation_warm_terms(wordlist, limit=limit)
    cache_path = Path(translation_cache_db)
    if not dry_run:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
    translation_cache = _PathTranslationCache(cache_path, read_only=dry_run)

    translate = None if dry_run else _encounter_translation_callback(translation_model)
    term_summaries: list[dict[str, object]] = []
    totals: dict[str, int] = {
        "terms": len(terms),
        "written": 0,
    }

    for term in terms:
        result = _execute_lookup_plan(
            language=language,
            text=term,
            tool_filter=tool_filter,
            normalize=normalize,
            diogenes_endpoint=diogenes_endpoint,
            diogenes_parse_endpoint=diogenes_parse_endpoint,
            heritage_base=heritage_base,
            db_path=db_path,
            no_cache=no_cache,
            include_cltk=include_cltk,
        )
        claims = _claims_as_mappings(result)
        before = translation_cache_status_counts(
            claims=claims,
            language=language,
            model=translation_model,
            cache=translation_cache,  # type: ignore[arg-type]
        )
        written = 0
        if not dry_run and before["total"] > before["hits"]:
            assert translate is not None
            written = populate_missing_translations(
                claims=claims,
                language=language,
                model=translation_model,
                cache=translation_cache,  # type: ignore[arg-type]
                translate=translate,
            )
        after = translation_cache_status_counts(
            claims=claims,
            language=language,
            model=translation_model,
            cache=translation_cache,  # type: ignore[arg-type]
        )
        totals["written"] += written
        _add_translation_counts(totals, before, prefix="before_")
        _add_translation_counts(totals, after, prefix="after_")
        term_summaries.append(
            {
                "term": term,
                "before": before,
                "written": written,
                "after": after,
            }
        )

    payload = {
        "language": language,
        "wordlist": str(wordlist),
        "translation_cache_db": str(cache_path),
        "translation_model": translation_model,
        "dry_run": dry_run,
        "summary": totals,
        "terms": term_summaries,
    }
    if output == "json":
        click.echo(orjson.dumps(payload, option=orjson.OPT_INDENT_2).decode("utf-8"))
        return

    action = "Dry run" if dry_run else "Warm"
    click.echo(
        f"{action}: terms={totals['terms']} "
        f"projections={totals.get('before_total', 0)} "
        f"hits={totals.get('before_hits', 0)} "
        f"missing={totals.get('before_missing', 0)} "
        f"written={totals['written']}"
    )
    for item in term_summaries:
        before = cast(Mapping[str, int], item["before"])
        after = cast(Mapping[str, int], item["after"])
        click.echo(
            f"- {item['term']}: projections={before['total']} "
            f"hits={before['hits']} missing={before['missing']} "
            f"written={item['written']} after_hits={after['hits']}"
        )


@main.command("encounter")
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
    help="Base URL for Heritage Platform.",
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
@click.option(
    "--max-buckets",
    default=6,
    show_default=True,
    type=int,
    help="Maximum sense buckets to display.",
)
@click.option(
    "--max-gloss-chars",
    default=240,
    show_default=True,
    type=int,
    help="Maximum characters to display for each gloss.",
)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.option(
    "--use-translation-cache",
    is_flag=True,
    help="Display cached DICO/Gaffiot French-to-English translations when available.",
)
@click.option(
    "--translation-mode",
    type=click.Choice(["off", "cache", "populate", "auto", "do-it-all"]),
    default="cache",
    show_default=True,
    help=(
        "French source translation mode: cache-only, off, or populate missing "
        "DICO/Gaffiot rows via OpenRouter before display. do-it-all is an alias for auto."
    ),
)
@click.option(
    "--translation-cache-db",
    default="data/cache/langnet.duckdb",
    show_default=True,
    help="DuckDB cache containing entry_translations rows.",
)
@click.option(
    "--translation-model",
    default="openai:google/gemini-3.1-pro-preview",
    show_default=True,
    help="Model id used when computing translation cache keys.",
)
@click.option(
    "--foster-labels/--no-foster-labels",
    default=True,
    show_default=True,
    help="Show optional Foster functional grammar labels beside morphology analysis.",
)
@click.option(
    "--source-details/--no-source-details",
    default=True,
    show_default=True,
    help="Show compact typed source notes from dictionary source segments.",
)
def encounter(  # noqa: C901, PLR0912, PLR0913, PLR0915
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
    max_buckets: int,
    max_gloss_chars: int,
    output: str,
    use_translation_cache: bool,
    translation_mode: str,
    translation_cache_db: str,
    translation_model: str,
    foster_labels: bool,
    source_details: bool,
):
    """
    Show a compact, source-backed learner encounter for one word.
    """
    translation_cache: _PathTranslationCache | None = None
    try:
        result = _execute_lookup_plan(
            language=language,
            text=text,
            tool_filter=tool_filter,
            normalize=normalize,
            diogenes_endpoint=diogenes_endpoint,
            diogenes_parse_endpoint=diogenes_parse_endpoint,
            heritage_base=heritage_base,
            db_path=db_path,
            no_cache=no_cache,
            include_cltk=include_cltk,
        )
        claims = _claims_as_mappings(result)
        resolved_translation_mode = _resolve_translation_mode(
            use_translation_cache,
            translation_mode,
        )
        cache_path = Path(translation_cache_db)
        populate_translations = resolved_translation_mode in {"populate", "auto"}
        translation_diagnostics = _encounter_translation_diagnostics(
            mode=resolved_translation_mode,
            cache_path=cache_path,
            model=translation_model,
            populate=populate_translations,
        )
        translation_callback = _encounter_translation_callback(translation_model)
        if resolved_translation_mode != "off" and (cache_path.exists() or populate_translations):
            if populate_translations:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
            translation_cache = _PathTranslationCache(
                cache_path,
                read_only=not populate_translations,
            )
            translation_diagnostics["cache_available"] = True
            try:
                claims = _encounter_apply_translation_cache(
                    claims=claims,
                    language=language,
                    model=translation_model,
                    cache=translation_cache,  # type: ignore[arg-type]
                    populate=populate_translations,
                    translate=translation_callback,
                    diagnostics=translation_diagnostics,
                    context="initial",
                )
            except Exception as exc:  # noqa: BLE001
                raise click.ClickException(
                    f"Unable to use translation cache {translation_cache_db}: {exc}"
                ) from exc

        reduction = reduce_claims(query=text, language=language, claims=claims)
        if _encounter_should_retry_uncached(
            normalize=normalize,
            no_cache=no_cache,
            tool_filter=tool_filter,
            reduction=reduction,
        ):
            fresh_result = _execute_lookup_plan(
                language=language,
                text=text,
                tool_filter=tool_filter,
                normalize=normalize,
                diogenes_endpoint=diogenes_endpoint,
                diogenes_parse_endpoint=diogenes_parse_endpoint,
                heritage_base=heritage_base,
                db_path=db_path,
                no_cache=True,
                include_cltk=include_cltk,
            )
            fresh_claims = _claims_as_mappings(fresh_result)
            if translation_cache is not None:
                try:
                    fresh_claims = _encounter_apply_translation_cache(
                        claims=fresh_claims,
                        language=language,
                        model=translation_model,
                        cache=translation_cache,  # type: ignore[arg-type]
                        populate=populate_translations,
                        translate=translation_callback,
                        diagnostics=translation_diagnostics,
                        context="retry",
                    )
                except Exception as exc:  # noqa: BLE001
                    raise click.ClickException(
                        f"Unable to read translation cache {translation_cache_db}: {exc}"
                    ) from exc
            fresh_reduction = reduce_claims(query=text, language=language, claims=fresh_claims)
            if fresh_reduction.buckets:
                claims = fresh_claims
                reduction = fresh_reduction
                reduction.warnings.append(
                    "Cached normalization produced no sense buckets; retried with fresh "
                    "normalization."
                )

        morphology_claims = claims
        fallback_terms, fallback_warning = _encounter_sanskrit_morphology_lookup_terms(
            claims=claims,
            language=language,
            original=text,
            tool_filter=tool_filter,
            reduction=reduction,
        )
        if fallback_terms:
            original_bucket_count = len(reduction.buckets)
            fallback_claims = list(claims)
            for fallback_term in fallback_terms:
                fallback_result = _execute_lookup_plan(
                    language=language,
                    text=fallback_term,
                    tool_filter=tool_filter,
                    normalize=normalize,
                    diogenes_endpoint=diogenes_endpoint,
                    diogenes_parse_endpoint=diogenes_parse_endpoint,
                    heritage_base=heritage_base,
                    db_path=db_path,
                    no_cache=True,
                    include_cltk=include_cltk,
                )
                term_claims = _claims_as_mappings(fallback_result)
                if translation_cache is not None:
                    try:
                        term_claims = _encounter_apply_translation_cache(
                            claims=term_claims,
                            language=language,
                            model=translation_model,
                            cache=translation_cache,  # type: ignore[arg-type]
                            populate=populate_translations,
                            translate=translation_callback,
                            diagnostics=translation_diagnostics,
                            context=f"fallback:{fallback_term}",
                        )
                    except Exception as exc:  # noqa: BLE001
                        raise click.ClickException(
                            f"Unable to read translation cache {translation_cache_db}: {exc}"
                        ) from exc
                fallback_claims.extend(term_claims)
            if len(fallback_claims) > len(claims):
                fallback_reduction = reduce_claims(
                    query=text,
                    language=language,
                    claims=fallback_claims,
                )
                if len(fallback_reduction.buckets) > original_bucket_count:
                    claims = fallback_claims
                    reduction = fallback_reduction
                    if fallback_warning:
                        reduction.warnings.append(fallback_warning)

        morphology_rows = _encounter_morphology_rows(
            morphology_claims,
            language=language,
            original=text,
            reduction=reduction,
        )
        preferred_lemmas = _encounter_preferred_lemmas_for_sorting(
            reduction,
            morphology_rows,
            fallback_terms,
        )
        reduction.buckets = sorted(
            reduction.buckets,
            key=lambda bucket: _encounter_bucket_sort_key(bucket, preferred_lemmas),
        )

        if output == "json":
            payload = asdict(reduction)
            payload["schema_version"] = ENCOUNTER_JSON_SCHEMA_VERSION
            payload["request"] = {
                "language": language,
                "text": text,
                "tool_filter": tool_filter,
                "normalize": normalize,
                "no_cache": no_cache,
                "include_cltk": include_cltk,
                "translation_mode": resolved_translation_mode,
            }
            payload["display"] = build_display_payload(
                reduction,
                morphology_rows,
                language=language,
                max_gloss_chars=max_gloss_chars,
                include_foster=foster_labels,
                include_source_details=source_details,
                bucket_gloss=_encounter_bucket_gloss,
                bucket_learner_gloss=lambda bucket: _encounter_bucket_learner_gloss(
                    bucket,
                    max_chars=max_gloss_chars,
                ),
            )
            payload["ranking"] = [
                asdict(
                    bucket_ranking_explanation(
                        bucket,
                        preferred_lemmas,
                        bucket_gloss=_encounter_bucket_gloss,
                    )
                )
                for bucket in reduction.buckets
            ]
            payload["translation_cache"] = translation_diagnostics
            click.echo(orjson.dumps(payload, option=orjson.OPT_INDENT_2).decode("utf-8"))
            return

        click.echo(f"{text} [{language}]")
        click.echo("=" * (len(text) + len(language) + 3))
        header_view = build_header_view(reduction)
        if header_view.forms:
            click.echo("Forms: " + ", ".join(header_view.forms[:4]))
        if header_view.source_keys and header_view.source_keys != header_view.forms:
            click.echo("Source keys: " + ", ".join(header_view.source_keys[:4]))
        if reduction.warnings:
            for warning in reduction.warnings:
                if (
                    morphology_rows
                    and warning == "No has_sense/gloss witness units were extracted."
                ):
                    continue
                click.echo(f"Warning: {warning}")

        if morphology_rows:
            click.echo("\nAnalysis")
            for analysis_view in build_analysis_views(
                morphology_rows,
                language=language,
                include_foster=foster_labels,
            ):
                click.echo(f"- {analysis_view.display_text}")
        if not reduction.buckets:
            return

        click.echo("\nMeanings")
        for idx, bucket in enumerate(reduction.buckets[:max_buckets], start=1):
            learner_gloss = _encounter_bucket_learner_gloss(bucket, max_chars=max_gloss_chars)
            evidence_gloss = _encounter_bucket_gloss(bucket)
            meaning_view = build_meaning_view(
                bucket,
                learner_gloss=learner_gloss,
                evidence_gloss=evidence_gloss,
                max_gloss_chars=max_gloss_chars,
                include_source_details=source_details,
            )
            click.echo(f"{idx}. {meaning_view.display_gloss}")
            if meaning_view.evidence_gloss:
                click.echo(f"   evidence: {meaning_view.evidence_gloss}")
                if meaning_view.evidence_length_note:
                    click.echo(f"   {meaning_view.evidence_length_note}")
            elif meaning_view.length_note:
                click.echo(f"   {meaning_view.length_note}")
            click.echo(
                f"   sources: {meaning_view.source_text}; "
                f"witnesses: {meaning_view.witness_count}; "
                f"confidence: {meaning_view.confidence_label}"
            )
            if meaning_view.source_refs:
                click.echo(f"   refs: {', '.join(meaning_view.source_refs[:3])}")
            source_note_summary = meaning_view.source_detail_summary.format()
            if source_note_summary:
                click.echo(f"   source notes: {source_note_summary}")
            if meaning_view.translation_sources:
                click.echo(f"   translated from: {', '.join(meaning_view.translation_sources[:3])}")
            if meaning_view.source_langs:
                click.echo(f"   source language: {', '.join(meaning_view.source_langs)}")
        if len(reduction.buckets) > max_buckets:
            click.echo(f"\n({len(reduction.buckets) - max_buckets} more bucket(s) hidden)")
    except Exception as exc:
        if output == "json":
            resolved_error_mode = _resolve_translation_mode(
                use_translation_cache,
                translation_mode,
            )
            click.echo(
                orjson.dumps(
                    _encounter_json_error_payload(
                        language=language,
                        text=text,
                        tool_filter=tool_filter,
                        normalize=normalize,
                        no_cache=no_cache,
                        include_cltk=include_cltk,
                        translation_mode=resolved_error_mode,
                        exc=exc,
                    ),
                    option=orjson.OPT_INDENT_2,
                ).decode("utf-8")
            )
            raise click.exceptions.Exit(1) from exc
        raise


def _reader_eval_translation_claims(
    *,
    claims: list[Mapping[str, object]],
    language: str,
    translation_mode: str,
    translation_cache_db: str,
    translation_model: str,
) -> list[Mapping[str, object]]:
    resolved_translation_mode = _resolve_translation_mode(False, translation_mode)
    if resolved_translation_mode == "off":
        return claims

    cache_path = Path(translation_cache_db)
    populate_translations = resolved_translation_mode in {"populate", "auto"}
    if not cache_path.exists() and not populate_translations:
        return claims

    if populate_translations:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache = _PathTranslationCache(cache_path, read_only=not populate_translations)
    if populate_translations:
        populate_missing_translations(
            claims=claims,
            language=language,
            model=translation_model,
            cache=cache,  # type: ignore[arg-type]
            translate=_openrouter_translation_callback(translation_model),
        )
    return project_cached_translations(
        claims=claims,
        language=language,
        model=translation_model,
        cache=cache,  # type: ignore[arg-type]
    )


def _reader_eval_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value:
        return int(value)
    return 0


def _reader_eval_float(value: object) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value:
        return float(value)
    return 0.0


def _reader_eval_display(report: Mapping[str, object]) -> None:
    summary = report.get("summary")
    summary_map = cast(Mapping[str, object], summary) if isinstance(summary, Mapping) else {}
    total = _reader_eval_int(summary_map.get("total"))
    passed = _reader_eval_int(summary_map.get("passed"))
    failed = _reader_eval_int(summary_map.get("failed"))
    hit_rate = _reader_eval_float(summary_map.get("hit_rate"))
    meaning_passed = _reader_eval_int(summary_map.get("meaning_passed"))
    meaning_hit_rate = _reader_eval_float(summary_map.get("meaning_hit_rate"))
    top_passed = _reader_eval_int(summary_map.get("top_passed"))
    top_hit_rate = _reader_eval_float(summary_map.get("top_hit_rate"))
    click.echo(f"Reader eval: {passed}/{total} passed ({hit_rate:.0%} hit rate); {failed} failed")
    click.echo(f"Meaning: {meaning_passed}/{total} ({meaning_hit_rate:.0%} hit rate)")
    click.echo(f"Top answer: {top_passed}/{total} ({top_hit_rate:.0%} hit rate)")

    results = report.get("results")
    if not isinstance(results, list):
        return
    for result in results:
        if not isinstance(result, Mapping):
            continue
        result_map = cast(Mapping[str, object], result)
        status = "PASS" if result_map.get("passed") is True else "MISS"
        label = (f"{result_map.get('language', '')} {result_map.get('surface', '')}").strip()
        click.echo(f"- {status} {label}")
        error = result_map.get("error")
        if error:
            click.echo(f"  error: {error}")
            continue
        checks = result_map.get("checks")
        if isinstance(checks, Mapping):
            missed = [key for key, value in checks.items() if value is not True]
            if missed:
                click.echo(f"  checks: {', '.join(str(key) for key in missed)}")
        actual = result_map.get("actual")
        if isinstance(actual, Mapping):
            actual_map = cast(Mapping[str, object], actual)
            top_glosses = actual_map.get("top_glosses")
            if isinstance(top_glosses, list) and top_glosses:
                click.echo(f"  top: {top_glosses[0]}")


@main.command("reader-eval")
@click.option(
    "--fixture",
    "fixture_path",
    default="tests/fixtures/reader_eval_classics.json",
    show_default=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Reader-eval fixture file.",
)
@click.option(
    "--language",
    "languages",
    multiple=True,
    help="Restrict evaluation to one or more language codes.",
)
@click.option(
    "--limit",
    type=int,
    help="Evaluate at most this many fixture tokens.",
)
@click.option(
    "--tool-filter",
    default="all",
    show_default=True,
    help="Tool filter passed to encounter lookup planning.",
)
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
    help="Base URL for Heritage Platform.",
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
@click.option(
    "--translation-mode",
    type=click.Choice(["off", "cache", "populate", "auto", "do-it-all"]),
    default="cache",
    show_default=True,
    help="French source translation mode used before scoring gloss evidence.",
)
@click.option(
    "--translation-cache-db",
    default="data/cache/langnet.duckdb",
    show_default=True,
    help="DuckDB cache containing entry_translations rows.",
)
@click.option(
    "--translation-model",
    default="openai:google/gemini-3.1-pro-preview",
    show_default=True,
    help="Model id used when computing translation cache keys.",
)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.option(
    "--fail-on-miss",
    is_flag=True,
    help="Exit non-zero when any fixture token misses.",
)
def reader_eval(  # noqa: PLR0913, PLR0915
    fixture_path: Path,
    languages: tuple[str, ...],
    limit: int | None,
    tool_filter: str,
    normalize: bool,
    diogenes_endpoint: str,
    diogenes_parse_endpoint: str | None,
    heritage_base: str,
    db_path: str | None,
    no_cache: bool,
    include_cltk: bool,
    translation_mode: str,
    translation_cache_db: str,
    translation_model: str,
    output: str,
    fail_on_miss: bool,
) -> None:
    """Run reader-oriented fixture checks against live encounter reductions."""
    language_filter = set(languages) if languages else None
    fixture = load_reader_eval_fixture(fixture_path)
    tokens = iter_reader_eval_tokens(fixture, languages=language_filter, limit=limit)
    results: list[dict[str, object]] = []

    for token in tokens:
        language = str(token["language"])
        surface = str(token["surface"])
        try:
            lookup_result = _execute_lookup_plan(
                language=language,
                text=surface,
                tool_filter=tool_filter,
                normalize=normalize,
                diogenes_endpoint=diogenes_endpoint,
                diogenes_parse_endpoint=diogenes_parse_endpoint,
                heritage_base=heritage_base,
                db_path=db_path,
                no_cache=no_cache,
                include_cltk=include_cltk,
            )
            claims = _reader_eval_translation_claims(
                claims=_claims_as_mappings(lookup_result),
                language=language,
                translation_mode=translation_mode,
                translation_cache_db=translation_cache_db,
                translation_model=translation_model,
            )
            reduction = reduce_claims(query=surface, language=language, claims=claims)
            morphology_claims = claims
            fallback_terms, _fallback_warning = _encounter_sanskrit_morphology_lookup_terms(
                claims=claims,
                language=language,
                original=surface,
                tool_filter=tool_filter,
                reduction=reduction,
            )
            if fallback_terms:
                original_bucket_count = len(reduction.buckets)
                fallback_claims = list(claims)
                for fallback_term in fallback_terms:
                    fallback_result = _execute_lookup_plan(
                        language=language,
                        text=fallback_term,
                        tool_filter=tool_filter,
                        normalize=normalize,
                        diogenes_endpoint=diogenes_endpoint,
                        diogenes_parse_endpoint=diogenes_parse_endpoint,
                        heritage_base=heritage_base,
                        db_path=db_path,
                        no_cache=True,
                        include_cltk=include_cltk,
                    )
                    fallback_claims.extend(
                        _reader_eval_translation_claims(
                            claims=_claims_as_mappings(fallback_result),
                            language=language,
                            translation_mode=translation_mode,
                            translation_cache_db=translation_cache_db,
                            translation_model=translation_model,
                        )
                    )
                if len(fallback_claims) > len(claims):
                    fallback_reduction = reduce_claims(
                        query=surface,
                        language=language,
                        claims=fallback_claims,
                    )
                    if len(fallback_reduction.buckets) > original_bucket_count:
                        claims = fallback_claims
                        reduction = fallback_reduction
            morphology_rows = _encounter_morphology_rows(
                morphology_claims,
                language=language,
                original=surface,
                reduction=reduction,
                max_rows=8,
            )
            preferred_lemmas = _encounter_preferred_lemmas_for_sorting(
                reduction,
                morphology_rows,
                fallback_terms,
            )
            reduction.buckets = sorted(
                reduction.buckets,
                key=lambda bucket: _encounter_bucket_sort_key(bucket, preferred_lemmas),
            )
            results.append(
                evaluate_reader_token(
                    token,
                    asdict(reduction),
                    morphology_rows=morphology_rows,
                )
            )
        except Exception as exc:  # noqa: BLE001
            results.append(evaluate_reader_token(token, {}, error=str(exc)))

    report = {
        "fixture": str(fixture_path),
        "summary": summarize_reader_eval(results),
        "results": results,
    }
    if output == "json":
        click.echo(orjson.dumps(report, option=orjson.OPT_INDENT_2).decode("utf-8"))
    else:
        _reader_eval_display(report)

    summary = cast(Mapping[str, object], report["summary"])
    if fail_on_miss and _reader_eval_int(summary["failed"]) > 0:
        raise click.ClickException("Reader eval reported misses.")


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
def lookup(  # noqa: PLR0912, PLR0913, PLR0915, C901
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
    - Latin (lat): Whitaker's Words, Diogenes (Lewis & Short), CLTK, Gaffiot
    - Greek (grc): Diogenes (LSJ)
    - Sanskrit (san): Heritage Platform, CDSL

    Returns aggregated results from all available sources.
    """
    # Map language to available tools
    tool_map = {
        "lat": ["whitakers", "diogenes", "cltk", "gaffiot"],
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

            elif tool == "gaffiot":
                # Local Gaffiot Latin dictionary
                fetch_client = gaffiot_handlers.GaffiotFetchClient()
                fetch = fetch_client.execute(
                    call_id="gaffiot-1",
                    endpoint="duckdb://gaffiot",
                    params={"headword": query_word, "lemma": query_word, "q": text},
                )
                ext_call = ToolCallSpec(
                    tool="extract.gaffiot.json",
                    call_id="gaffiot-parse-1",
                    endpoint="internal://gaffiot/json_extract",
                    params={"source_call_id": "gaffiot-1"},
                )
                extraction = gaffiot_handlers.extract_gaffiot_json(ext_call, fetch)
                drv_call = ToolCallSpec(
                    tool="derive.gaffiot.entries",
                    call_id="gaffiot-derive-1",
                    endpoint="internal://gaffiot/entry_derive",
                    params={"source_call_id": ext_call.call_id},
                )
                derivation = gaffiot_handlers.derive_gaffiot_entries(drv_call, extraction)
                claim_call = ToolCallSpec(
                    tool="claim.gaffiot.entries",
                    call_id="gaffiot-claim-1",
                    endpoint="internal://claim/gaffiot_entries",
                    params={"source_call_id": drv_call.call_id},
                )
                claim = gaffiot_handlers.claim_gaffiot_entries(claim_call, derivation)
                payload = (
                    cast(Mapping[str, object], derivation.payload)
                    if isinstance(derivation.payload, Mapping)
                    else {}
                )
                claim_value = (
                    cast(Mapping[str, object], claim.value)
                    if isinstance(claim.value, Mapping)
                    else {}
                )
                results[tool] = {
                    "entries": payload.get("entries", []),
                    "triples": claim_value.get("triples", []),
                }

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
