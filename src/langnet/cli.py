import csv
import hashlib
import importlib.util
import logging
import multiprocessing
import os
import queue as queue_module
import re
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from contextlib import suppress
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, TypedDict, cast

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
    entry_summary_payload,
    foster_display_for_analysis,
    foster_features_from_analysis,
    shorten_text,
    source_detail_summary_payload,
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
from langnet.execution.source_text import analyze_source_entry, compact_source_gloss
from langnet.heritage.velthuis_converter import to_heritage_velthuis
from langnet.learning.concept_mapper import concept_ids_for_features
from langnet.learning.grammar_concepts import (
    GrammarConcept,
    get_grammar_concept,
    load_grammar_concepts,
)
from langnet.morphology.candidates import MorphologyCandidate, candidates_from_triples
from langnet.normalizer.core import NormalizationResult, _hash_query
from langnet.normalizer.service import DiogenesConfig, NormalizationService
from langnet.normalizer.utils import normalize_greek_compatibility, strip_accents
from langnet.paradigm.grammar import LANGNET_PARADIGM_RESOLUTION_SCHEMA_VERSION, ParadigmRequest
from langnet.paradigm.resolver import resolve_paradigm_request
from langnet.paradigm.service import ParadigmService
from langnet.parsing.integration import enrich_cltk_with_parsed_lewis
from langnet.planner.core import PlannerConfig, ToolPlanner
from langnet.reader.author_bulk_classification import (
    AuthorClassificationRunConfig,
    classify_author_csv,
)
from langnet.reader.author_classification import (
    AUTHOR_AGENT_KIND_VALUES,
    AUTHOR_CLASSIFICATION_OUTPUT_FIELDS,
    AUTHOR_HISTORICITY_STATUS_VALUES,
)
from langnet.reader.bulk_classification import (
    CLASSIFICATION_OUTPUT_FIELDS,
    ClassificationRunConfig,
    classify_work_csv,
)
from langnet.reader.search_index import search_reader_segments
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
from langnet.translation.structured import (
    requires_structured_translation,
    structured_translation_system_hint,
    structured_translation_user_content,
)
from langnet.word_index import (
    WordIndexHomographs,
    word_index_browse_payload,
    word_index_list_payload,
    word_index_neighborhood_payload,
    word_index_sections_payload,
    word_index_sources_payload,
    word_index_wheel_payload,
)
from langnet.word_of_day import (
    WordCandidate,
    WordOfDayOptions,
    generate_word_of_day_payload,
    resolve_word_of_day_languages,
)


def _default_registry(*, use_stubs: bool = False):
    from langnet.execution.registry import default_registry  # noqa: PLC0415

    return default_registry(use_stubs=use_stubs)


LanguageHint = query_spec.LanguageHint
LanguageValue = query_spec.LanguageHint.ValueType
LATIN_AE_SUFFIX_LEN = 2
ENCOUNTER_LEARNER_GLOSS_MAX_CHARS = 120
ENCOUNTER_LEARNER_GLOSS_ITEM_LIMIT = 4
ENCOUNTER_MAX_COMPONENTS = 4
ENCOUNTER_SANSKRIT_MORPHOLOGY_SCAN_ROWS = 24
SANSKRIT_AN_STEM_MIN_CHARS = 3
ENCOUNTER_JSON_SCHEMA_VERSION = "langnet.encounter.v1"
ENCOUNTER_JSON_ERROR_SCHEMA_VERSION = "langnet.encounter.error.v1"
DATABASE_BUSY_RETRY_AFTER_MS = 1500
TRANSLATION_CACHE_SCHEMA_VERSION = "langnet.translation_cache.v1"
DOCTOR_SCHEMA_VERSION = "langnet.doctor.v1"
DEFAULT_TRANSLATION_MODEL = "openai:google/gemini-2.5-flash"
DEFAULT_CLASSIFICATION_MODEL = "openai:deepseek/deepseek-v4-flash"
DEFAULT_CLASSIFICATION_BATCH_SIZE = 25
DEFAULT_CLASSIFICATION_TIMEOUT_SECONDS = 120.0
DEFAULT_CLASSIFICATION_MAX_ATTEMPTS = 3
TRANSLATION_FALLBACK_MODELS_ENV = "LANGNET_TRANSLATION_FALLBACK_MODELS"
DEFAULT_TRANSLATION_FALLBACK_MODELS = ("openai:deepseek/deepseek-v4-flash",)
TRANSLATION_MIN_OUTPUT_TOKENS_PER_SECOND_ENV = "LANGNET_TRANSLATION_MIN_OUTPUT_TOKENS_PER_SECOND"
TRANSLATION_MIN_RATE_TOKENS_ENV = "LANGNET_TRANSLATION_MIN_RATE_TOKENS"
TRANSLATION_MIN_RATE_SECONDS_ENV = "LANGNET_TRANSLATION_MIN_RATE_SECONDS"
LEARNING_OVERLAY_SCHEMA_VERSION = "langnet.learning_overlay.v1"
DEFAULT_TRANSLATION_MIN_OUTPUT_TOKENS_PER_SECOND = 8.0
DEFAULT_TRANSLATION_MIN_RATE_TOKENS = 24
DEFAULT_TRANSLATION_MIN_RATE_SECONDS = 5.0
DEFAULT_RECOMMENDATION_MODEL = "openai:google/gemini-2.5-flash"
WORD_INDEX_CONTEXT_RADIUS = 1
GRAMMAR_CONCEPTS_SCHEMA_VERSION = "langnet.grammar_concepts.v1"
GRAMMAR_EVIDENCE_REPORT_SCHEMA_VERSION = "langnet.grammar_evidence_report.v1"
WORD_INDEX_SOURCES = {
    "all",
    "cdsl",
    "dico",
    "gaffiot",
    "lewis_1890",
    "whitakers",
    "diogenes",
    "bailly",
}


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
    cache_policy: str,
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
            "command": "encounter",
            "language": language,
            "text": text,
            "tool_filter": tool_filter,
            "normalize": normalize,
            "no_cache": no_cache,
            "cache_policy": cache_policy,
            "normalization_cache_writes": cache_policy == "read-write",
            "include_cltk": include_cltk,
            "translation_mode": translation_mode,
            "translation_cache_writes": translation_mode in {"populate", "auto"},
        },
        "error": _encounter_json_error_details(exc, message),
    }


def _encounter_json_error_details(exc: Exception, message: str) -> dict[str, object]:
    if _is_database_busy_exception(exc):
        return {
            "code": "database_busy",
            "kind": "database_busy",
            "command": "encounter",
            "type": exc.__class__.__name__,
            "message": message,
            "retryable": True,
            "retry_after_ms": DATABASE_BUSY_RETRY_AFTER_MS,
            "readonly_available": True,
        }
    return {
        "code": "click_error" if isinstance(exc, click.ClickException) else "encounter_failed",
        "command": "encounter",
        "type": exc.__class__.__name__,
        "message": message,
    }


def _is_database_busy_exception(exc: BaseException) -> bool:
    current: BaseException | None = exc
    while current is not None:
        if isinstance(current, FileLockTimeout):
            return True
        if isinstance(current, duckdb.Error):
            message = str(current).casefold()
            if (
                "lock" in message
                or "conflicting lock" in message
                or "database is locked" in message
            ):
                return True
        current = current.__cause__ or current.__context__
    return False


@dataclass
class NormalizeConfig:
    diogenes_endpoint: str
    heritage_base: str
    db_path: str | None
    no_cache: bool
    output: str
    cache_policy: str = "read-write"


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
        cache_policy="off",
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
    try:
        with connect_duckdb(path, read_only=True, lock=False, allow_create=False) as conn:
            cached = NormalizationIndex(conn).get(query_hash)
            if cached is not None:
                service = _create_normalization_service(config, conn, read_only=True)
                if service._cached_greek_compatibility_is_stale(text, lang_hint, cached):
                    cached = None
                else:
                    cached = service._rerank_candidates(text, lang_hint, cached)
                    if service._cached_reader_completion_is_stale(
                        text,
                        lang_hint,
                        cached,
                    ) or service._cached_greek_epic_eus_is_stale(text, lang_hint, cached):
                        cached = None
    except duckdb.Error:
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
    cache_policy = _effective_cache_policy(config)
    cache_enabled = use_cache and cache_policy != "off"
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
    if cache_enabled and cache_policy == "read-write":
        _normalization_cache_upsert(path=path, text=text, lang_hint=lang_hint, result=result)
    return result


def _effective_cache_policy(config: NormalizeConfig) -> str:
    if config.no_cache:
        return "off"
    if config.cache_policy in {"read-write", "read-only", "off"}:
        return config.cache_policy
    return "read-write"


class _PathTranslationCache:
    """Translation cache facade that does not hold DuckDB open during model calls."""

    def __init__(self, path: Path, *, read_only: bool = False) -> None:
        self.path = path
        self.read_only = read_only

    def get(self, key) -> object | None:
        if not self.path.exists():
            return None
        try:
            with connect_duckdb(self.path, read_only=True, lock=False, allow_create=False) as conn:
                return TranslationCache(conn, read_only=True).get(key)
        except duckdb.Error:
            return None

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
            if _normalization_candidates_are_only_heritage_guesses(candidates):
                return raw_text
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


def _normalization_candidates_are_only_heritage_guesses(candidates) -> bool:
    saw_candidate = False
    for cand in candidates:
        saw_candidate = True
        sources = getattr(cand, "sources", []) or []
        if "heritage_sktuser_guess" not in sources:
            return False
    return saw_candidate


def _sanskrit_cdsl_query_from_heritage(heritage_payload: object, fallback: str) -> str:
    if not isinstance(heritage_payload, Mapping):
        return fallback
    heritage_payload = cast(Mapping[str, object], heritage_payload)
    analyses = heritage_payload.get("analyses")
    if isinstance(analyses, Sequence) and not isinstance(analyses, (str, bytes)):
        for analysis in analyses:
            if not isinstance(analysis, Mapping):
                continue
            analysis = cast(Mapping[str, object], analysis)
            if not analysis.get("dictionary_url"):
                continue
            word = analysis.get("word")
            if isinstance(word, str) and word.strip():
                return word.strip()
    lemma = heritage_payload.get("lemma")
    if isinstance(lemma, str) and lemma.strip():
        return lemma.strip()
    return fallback


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


@main.command("foster-ossa-extract")
@click.option(
    "--source",
    "source_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to local Ossa Latinitatis Sola PDF.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, path_type=Path),
    required=True,
    help="Output page JSONL path.",
)
def foster_ossa_extract(source_path: Path, output: Path) -> None:
    """Extract Foster Ossa PDF pages to local generated JSONL."""
    from langnet.foster_ossa.extraction import (  # noqa: PLC0415
        extract_pdf_pages,
        write_page_rows_jsonl,
    )

    count = write_page_rows_jsonl(extract_pdf_pages(source_path), output)
    click.echo(f"wrote: {output.expanduser()} pages={count}")


@click.group("foster-ossa")
def foster_ossa() -> None:
    """Inspect the local Foster Ossa extraction index."""


@foster_ossa.command("search")
@click.argument("query")
@click.option(
    "--db",
    "db_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Foster Ossa DuckDB path. Defaults to data/build/foster_ossa.duckdb.",
)
@click.option(
    "--index",
    "index_path",
    type=click.Path(path_type=Path),
    help="Optional Foster Ossa Lance search index path.",
)
@click.option(
    "--limit",
    type=click.IntRange(min=0),
    default=10,
    show_default=True,
    help="Maximum pages.",
)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
def foster_ossa_search(
    query: str,
    db_path: Path | None,
    index_path: Path | None,
    limit: int,
    output: str,
) -> None:
    """Search page text in the local Foster Ossa index."""
    if index_path is not None:
        from langnet.foster_ossa.search_index import search_foster_ossa_lance  # noqa: PLC0415

        payload = search_foster_ossa_lance(query, index_path=index_path, limit=limit)
        if output == "json":
            click.echo(orjson.dumps(payload, option=orjson.OPT_INDENT_2).decode("utf-8"))
            return
        _echo_foster_ossa_search_results(query, payload["results"])
        return

    from langnet.databuild.foster_ossa import search_foster_ossa  # noqa: PLC0415

    results = search_foster_ossa(query, db_path=db_path, limit=limit)
    if output == "json":
        click.echo(
            orjson.dumps(
                {"backend": "duckdb-like", "results": results},
                option=orjson.OPT_INDENT_2,
            ).decode("utf-8")
        )
        return
    _echo_foster_ossa_search_results(query, results)


@foster_ossa.group("search-index")
def foster_ossa_search_index() -> None:
    """Build and inspect the derived Foster Ossa full-text search index."""


@foster_ossa_search_index.command("build")
@click.option(
    "--db",
    "db_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Foster Ossa DuckDB path. Defaults to data/build/foster_ossa.duckdb.",
)
@click.option("--index", "index_path", type=click.Path(path_type=Path), help="Search index path.")
@click.option("--replace", is_flag=True, help="Replace any existing Lance search index.")
@click.option("--limit", type=click.IntRange(min=0), help="Debug record cap.")
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
def foster_ossa_search_index_build(
    db_path: Path | None,
    index_path: Path | None,
    replace: bool,
    limit: int | None,
    output: str,
) -> None:
    """Build a derived Foster Ossa Lance full-text search index."""
    from langnet.foster_ossa.search_index import build_foster_ossa_search_index  # noqa: PLC0415

    try:
        payload = {
            "mode": "foster-ossa-search-index-build",
            "summary": build_foster_ossa_search_index(
                db_path=db_path,
                index_path=index_path,
                replace=replace,
                limit=limit,
            ),
        }
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    _echo_foster_ossa_search_index_payload(payload, output)


@foster_ossa_search_index.command("status")
@click.option("--index", "index_path", type=click.Path(path_type=Path), help="Search index path.")
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
def foster_ossa_search_index_status(index_path: Path | None, output: str) -> None:
    """Show derived Foster Ossa text index status."""
    from langnet.foster_ossa.search_index import foster_ossa_search_index_status  # noqa: PLC0415

    payload = {
        "mode": "foster-ossa-search-index-status",
        "summary": foster_ossa_search_index_status(index_path),
    }
    _echo_foster_ossa_search_index_payload(payload, output)


@foster_ossa_search_index.command("validate")
@click.option("--index", "index_path", type=click.Path(path_type=Path), help="Search index path.")
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
def foster_ossa_search_index_validate(index_path: Path | None, output: str) -> None:
    """Validate the derived Foster Ossa text index."""
    from langnet.foster_ossa.search_index import validate_foster_ossa_search_index  # noqa: PLC0415

    payload = {
        "mode": "foster-ossa-search-index-validate",
        "validation": validate_foster_ossa_search_index(index_path),
    }
    _echo_foster_ossa_search_index_payload(payload, output)


def _echo_foster_ossa_search_results(query: str, results: list[dict[str, object]]) -> None:
    if not results:
        click.echo(f"No Foster Ossa pages found for {query!r}.")
        return
    for row in results:
        source_ref = row.get("source_ref") or f"page:{row['page_number']}"
        record_kind = row.get("record_kind") or "page"
        click.echo(f"{source_ref} {record_kind} p. {row['page_number']} [{row['section']}]")
        click.echo(f"  {str(row['text']).replace(chr(10), ' ')[:240]}")


def _echo_foster_ossa_search_index_payload(payload: dict[str, object], output: str) -> None:
    if output == "json":
        click.echo(orjson.dumps(payload, option=orjson.OPT_INDENT_2).decode("utf-8"))
        return
    summary = payload.get("summary")
    if isinstance(summary, dict):
        click.echo(f"backend: {summary.get('backend')}")
        click.echo(f"dataset_path: {summary.get('dataset_path')}")
        click.echo(f"record_count: {summary.get('record_count')}")
        if summary.get("record_kind_counts"):
            click.echo(f"record_kind_counts: {summary.get('record_kind_counts')}")
        if summary.get("fts_indexes"):
            click.echo(f"fts_indexes: {', '.join(str(item) for item in summary['fts_indexes'])}")
        return
    validation = payload.get("validation")
    if isinstance(validation, dict):
        issues = validation.get("issues") or []
        click.echo(f"issues: {len(issues)}")
        for issue in issues:
            if isinstance(issue, dict):
                click.echo(f"- {issue.get('code')}: {issue.get('message')}")


@foster_ossa.command("toc")
@click.option(
    "--db",
    "db_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Foster Ossa DuckDB path. Defaults to data/build/foster_ossa.duckdb.",
)
@click.option(
    "--experience",
    type=click.IntRange(min=1, max=5),
    help="Optional experience number.",
)
@click.option(
    "--limit",
    type=click.IntRange(min=0),
    default=200,
    show_default=True,
    help="Maximum TOC entries.",
)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
def foster_ossa_toc(
    db_path: Path | None,
    experience: int | None,
    limit: int,
    output: str,
) -> None:
    """Show structured Foster Ossa table-of-contents entries."""
    from langnet.databuild.foster_ossa import lookup_toc_entries  # noqa: PLC0415

    entries = lookup_toc_entries(db_path=db_path, experience=experience, limit=limit)
    if output == "json":
        click.echo(orjson.dumps({"entries": entries}, option=orjson.OPT_INDENT_2).decode("utf-8"))
        return
    if not entries:
        click.echo("No Foster Ossa TOC entries found.")
        return
    for entry in entries:
        encounter = entry.get("encounter_id") or "-"
        click.echo(
            f"{encounter} printed={entry['printed_page']} page={entry['inferred_page_number']}"
        )
        click.echo(f"  {entry['latin_title']}")
        if entry.get("english_title"):
            click.echo(f"  {entry['english_title']}")


@foster_ossa.command("concept")
@click.argument("term")
@click.option(
    "--db",
    "db_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Foster Ossa DuckDB path. Defaults to data/build/foster_ossa.duckdb.",
)
@click.option(
    "--limit",
    type=click.IntRange(min=0),
    default=20,
    show_default=True,
    help="Maximum mentions.",
)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
def foster_ossa_concept(term: str, db_path: Path | None, limit: int, output: str) -> None:
    """Show page-backed concept mentions from the Foster Ossa index."""
    from langnet.databuild.foster_ossa import lookup_concept_mentions  # noqa: PLC0415

    mentions = lookup_concept_mentions(term, db_path=db_path, limit=limit)
    if output == "json":
        click.echo(orjson.dumps({"mentions": mentions}, option=orjson.OPT_INDENT_2).decode("utf-8"))
        return
    if not mentions:
        click.echo(f"No Foster Ossa concept mentions found for {term!r}.")
        return
    for mention in mentions:
        encounter = mention.get("encounter_id") or "-"
        click.echo(f"p. {mention['page_number']} encounter={encounter} {mention['term']}")
        click.echo(f"  {mention['context']}")


@foster_ossa.command("encounter")
@click.argument("encounter_id")
@click.option(
    "--db",
    "db_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Foster Ossa DuckDB path. Defaults to data/build/foster_ossa.duckdb.",
)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
def foster_ossa_encounter(encounter_id: str, db_path: Path | None, output: str) -> None:
    """Show a Foster Ossa encounter summary row and page span."""
    from langnet.databuild.foster_ossa import lookup_encounter  # noqa: PLC0415

    row = lookup_encounter(encounter_id, db_path=db_path)
    if output == "json":
        click.echo(orjson.dumps({"encounter": row}, option=orjson.OPT_INDENT_2).decode("utf-8"))
        return
    if row is None:
        click.echo(f"No Foster Ossa encounter found for {encounter_id!r}.")
        return
    click.echo(
        f"{row['encounter_id']}: {row['heading']} pages {row['page_start']}-{row['page_end']}"
    )
    if row["title"]:
        click.echo(f"  {row['title']}")


@main.command("foster-ossa-summarize")
@click.option(
    "--db",
    "db_path",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Foster Ossa DuckDB path. Defaults to data/build/foster_ossa.duckdb.",
)
@click.option(
    "--scope",
    type=click.Choice(["page", "toc-entry", "experience"]),
    default="page",
    show_default=True,
    help="Summary scope.",
)
@click.option(
    "--model",
    default="openai:deepseek/deepseek-v4-flash",
    show_default=True,
    help="aisuite model identifier.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, path_type=Path),
    required=True,
    help="Summary JSONL output path.",
)
@click.option(
    "--limit",
    type=click.IntRange(min=0),
    help="Maximum summary plans.",
)
@click.option(
    "--input-summaries",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Generated TOC-entry summary JSONL path for rollup scopes.",
)
@click.option("--encounter", "encounter_id", help="Summarize pages in one encounter, e.g. 1.1.")
@click.option("--dry-run", is_flag=True, help="Plan summaries without generating text.")
def foster_ossa_summarize(  # noqa: C901, PLR0913
    db_path: Path | None,
    scope: str,
    model: str,
    output: Path,
    limit: int | None,
    input_summaries: Path | None,
    encounter_id: str | None,
    dry_run: bool,
) -> None:
    """Generate or plan local Foster Ossa LLM summaries."""
    from langnet.databuild.foster_ossa import (  # noqa: PLC0415
        page_rows_for_summary,
        toc_entry_rows_for_summary,
    )
    from langnet.foster_ossa.summaries import (  # noqa: PLC0415
        experience_rows_from_toc_summary_jsonl,
        generated_summary_json,
        plan_summary_chunks,
        summarize_plan,
        validate_generated_summary,
    )

    if scope == "experience":
        if input_summaries is None:
            raise click.ClickException("--input-summaries is required for --scope experience")
        rows = experience_rows_from_toc_summary_jsonl(input_summaries)
        if limit is not None:
            rows = rows[:limit]
    elif scope == "toc-entry":
        rows = toc_entry_rows_for_summary(
            db_path=db_path,
            limit=limit,
            encounter_id=encounter_id,
        )
    else:
        rows = page_rows_for_summary(db_path=db_path, limit=limit, encounter_id=encounter_id)
    plans = plan_summary_chunks(rows, scope=scope, model=model)
    output_path = output.expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as handle:
        for plan in plans:
            generated_text = ""
            validation_status = "planned"
            validation_issues: list[str] = []
            normalized_json = ""
            if not dry_run:
                try:
                    generated_text = summarize_plan(plan)
                except RuntimeError as exc:
                    raise click.ClickException(str(exc)) from exc
                validation_issues = validate_generated_summary(
                    scope=plan.scope,
                    generated_text=generated_text,
                    expected_source_ref=plan.source_ref,
                )
                validation_status = (
                    "generated_valid" if not validation_issues else "generated_invalid"
                )
                if not validation_issues:
                    normalized_json = generated_summary_json(
                        scope=plan.scope,
                        generated_text=generated_text,
                    )
            payload = {
                "source_ref": plan.source_ref,
                "scope": plan.scope,
                "model": plan.model,
                "prompt_version": plan.prompt_version,
                "input_hash": plan.input_hash,
                "generated_text": generated_text,
                "validation_status": validation_status,
            }
            if validation_issues:
                payload["validation_issues"] = validation_issues
            if normalized_json:
                payload["generated_json"] = normalized_json
            handle.write(orjson.dumps(payload))
            handle.write(b"\n")
    click.echo(f"planned: {len(plans)}")


@main.command("foster-ossa-summary-docs")
@click.option(
    "--input-summaries",
    type=click.Path(dir_okay=False, path_type=Path),
    required=True,
    help="Generated TOC-entry summary JSONL path.",
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, path_type=Path),
    required=True,
    help="Directory for generated Foster Ossa summary Markdown docs.",
)
def foster_ossa_summary_docs(input_summaries: Path, output_dir: Path) -> None:
    """Write reviewable Markdown docs from validated Foster Ossa summary JSONL."""
    from langnet.foster_ossa.summaries import write_summary_markdown_docs  # noqa: PLC0415

    written = write_summary_markdown_docs(input_path=input_summaries, output_dir=output_dir)
    click.echo(f"wrote: {len(written)}")
    for path in written:
        click.echo(str(path))


# Register subcommands
main.add_command(index)
main.add_command(databuild)
main.add_command(foster_ossa)


def _grammar_concept_payload(concept: GrammarConcept) -> dict[str, object]:
    return cast(dict[str, object], asdict(concept))


def _grammar_concept_learning_payload(concept: GrammarConcept) -> dict[str, object]:
    return {
        "id": concept.id,
        "kind": concept.kind,
        "foster_gateway": concept.foster_gateway,
        "plain_english": concept.plain_english,
        "traditional": dict(concept.traditional),
        "source_evidence": [asdict(evidence) for evidence in concept.evidence],
    }


def _grammar_concepts_payload(kind: str | None = None) -> dict[str, object]:
    concepts = sorted(load_grammar_concepts().values(), key=lambda item: (item.kind, item.id))
    if kind:
        kind_key = kind.casefold()
        concepts = [concept for concept in concepts if concept.kind.casefold() == kind_key]
    return {
        "schema_version": GRAMMAR_CONCEPTS_SCHEMA_VERSION,
        "concepts": [_grammar_concept_payload(concept) for concept in concepts],
    }


def _grammar_concept_detail_payload(concept_id: str) -> dict[str, object]:
    try:
        concept = get_grammar_concept(concept_id)
    except KeyError as exc:
        raise click.UsageError(str(exc)) from exc
    return {
        "schema_version": GRAMMAR_CONCEPTS_SCHEMA_VERSION,
        "concept": _grammar_concept_payload(concept),
    }


def _grammar_evidence_report_payload(kind: str | None = None) -> dict[str, object]:
    concepts = sorted(load_grammar_concepts().values(), key=lambda item: (item.kind, item.id))
    if kind:
        kind_key = kind.casefold()
        concepts = [concept for concept in concepts if concept.kind.casefold() == kind_key]
    concept_reports = [_grammar_concept_evidence_report(concept) for concept in concepts]
    total_concepts = len(concept_reports)
    with_source_basis = sum(1 for report in concept_reports if report["source_basis_count"])
    with_work_evidence = sum(
        1 for report in concept_reports if _evidence_count(report, "reader_work")
    )
    with_segment_evidence = sum(
        1 for report in concept_reports if _evidence_count(report, "reader_segment")
    )
    return {
        "schema_version": GRAMMAR_EVIDENCE_REPORT_SCHEMA_VERSION,
        "summary": {
            "total_concepts": total_concepts,
            "with_source_basis": with_source_basis,
            "missing_source_basis": total_concepts - with_source_basis,
            "with_work_evidence": with_work_evidence,
            "missing_work_evidence": total_concepts - with_work_evidence,
            "with_segment_evidence": with_segment_evidence,
            "missing_segment_evidence": total_concepts - with_segment_evidence,
        },
        "concepts": concept_reports,
    }


def _evidence_count(report: Mapping[str, object], level: str) -> int:
    counts = report.get("evidence_counts")
    if not isinstance(counts, Mapping):
        return 0
    value = cast(Mapping[str, object], counts).get(level)
    return value if isinstance(value, int) else 0


def _grammar_concept_evidence_report(concept: GrammarConcept) -> dict[str, object]:
    evidence_counts = Counter(evidence.evidence_level for evidence in concept.evidence)
    missing: list[str] = []
    if not concept.source_basis:
        missing.append("source_basis")
    if not evidence_counts["reader_work"]:
        missing.append("source_work_links")
    if not evidence_counts["reader_segment"]:
        missing.append("reader_segment_links")
    if not concept.traditional:
        missing.append("traditional_terms")
    if not concept.examples:
        missing.append("examples")
    if not concept.skills:
        missing.append("skills")
    return {
        "id": concept.id,
        "kind": concept.kind,
        "source_basis_count": len(concept.source_basis),
        "evidence_counts": {
            "reader_work": evidence_counts["reader_work"],
            "reader_segment": evidence_counts["reader_segment"],
        },
        "missing": missing,
    }


def _learn_feature_map(features: Sequence[str]) -> dict[str, str]:
    feature_map: dict[str, str] = {}
    for feature in features:
        key, sep, value = feature.partition("=")
        key = key.strip()
        value = value.strip()
        if not sep or not key or not value:
            raise click.UsageError("--feature values must use key=value form.")
        feature_map[key] = value
    return feature_map


def _learn_map_payload(
    *,
    features: Sequence[str],
    part_of_speech: str,
    paradigm_kind: str,
) -> dict[str, object]:
    feature_map = _learn_feature_map(features)
    concept_ids = concept_ids_for_features(
        feature_map,
        part_of_speech=part_of_speech,
        paradigm_kind=paradigm_kind,
    )
    concepts = [
        _grammar_concept_payload(get_grammar_concept(concept_id)) for concept_id in concept_ids
    ]
    return {
        "schema_version": GRAMMAR_CONCEPTS_SCHEMA_VERSION,
        "input": {
            "features": feature_map,
            "part_of_speech": part_of_speech,
            "paradigm_kind": paradigm_kind,
        },
        "concept_ids": concept_ids,
        "concepts": concepts,
    }


def _emit_learn_payload(payload: Mapping[str, object], output: str) -> None:
    if output == "json":
        click.echo(orjson.dumps(dict(payload), option=orjson.OPT_INDENT_2).decode("utf-8"))
        return

    concept_ids = payload.get("concept_ids")
    if isinstance(concept_ids, Sequence) and not isinstance(concept_ids, (str, bytes)):
        _echo_learn_mapping(payload, concept_ids)
        return

    concepts = payload.get("concepts")
    if isinstance(concepts, Sequence) and not isinstance(concepts, (str, bytes)):
        for concept in concepts:
            if isinstance(concept, Mapping):
                _echo_grammar_concept_summary(cast(Mapping[str, object], concept))
        return

    concept = payload.get("concept")
    if isinstance(concept, Mapping):
        _echo_grammar_concept_detail(cast(Mapping[str, object], concept))


def _emit_grammar_evidence_report_payload(payload: Mapping[str, object], output: str) -> None:
    if output == "json":
        click.echo(orjson.dumps(dict(payload), option=orjson.OPT_INDENT_2).decode("utf-8"))
        return
    summary = payload.get("summary")
    if isinstance(summary, Mapping):
        summary_map = cast(Mapping[str, object], summary)
        click.echo("Grammar evidence report:")
        click.echo(f"- total concepts: {summary_map.get('total_concepts')}")
        click.echo(f"- with work evidence: {summary_map.get('with_work_evidence')}")
        click.echo(f"- with segment evidence: {summary_map.get('with_segment_evidence')}")
        click.echo(f"- missing segment evidence: {summary_map.get('missing_segment_evidence')}")
    concepts = payload.get("concepts")
    if isinstance(concepts, Sequence) and not isinstance(concepts, (str, bytes)):
        for concept in concepts:
            if not isinstance(concept, Mapping):
                continue
            concept_map = cast(Mapping[str, object], concept)
            missing = concept_map.get("missing")
            missing_text = (
                ", ".join(str(item) for item in missing) if isinstance(missing, list) else ""
            )
            click.echo(f"- {concept_map.get('id')}: {missing_text or 'complete'}")


def _echo_learn_mapping(payload: Mapping[str, object], concept_ids: Sequence[object]) -> None:
    click.echo("Concept mapping:")
    for concept_id in concept_ids:
        click.echo(f"- {concept_id}")
    mapped_concepts = payload.get("concepts")
    if isinstance(mapped_concepts, Sequence) and not isinstance(mapped_concepts, (str, bytes)):
        for concept in mapped_concepts:
            if isinstance(concept, Mapping):
                _echo_grammar_concept_summary(cast(Mapping[str, object], concept))


def _echo_grammar_concept_summary(concept: Mapping[str, object]) -> None:
    foster = concept.get("foster_gateway") or "-"
    plain = concept.get("plain_english") or ""
    click.echo(f"- {concept.get('id')} [{concept.get('kind')}] {foster}: {plain}")


def _echo_grammar_concept_detail(concept: Mapping[str, object]) -> None:
    _echo_grammar_concept_summary(concept)
    traditional = concept.get("traditional")
    if isinstance(traditional, Mapping) and traditional:
        click.echo("  traditional:")
        for key, value in sorted(traditional.items()):
            click.echo(f"    {key}: {value}")
    examples = concept.get("examples")
    if isinstance(examples, Mapping) and examples:
        click.echo("  examples:")
        for key, value in sorted(examples.items()):
            click.echo(f"    {key}: {value}")


@click.group("learn")
def learn_cli() -> None:
    """Explore learner-facing grammar concepts and mappings."""


@learn_cli.command("concepts")
@click.option("--kind", help="Optional concept kind filter, e.g. case, number, process.")
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
def learn_concepts(kind: str | None, output: str) -> None:
    """List grammar concepts in the Foster/traditional registry."""
    _emit_learn_payload(_grammar_concepts_payload(kind), output)


@learn_cli.command("concept")
@click.argument("concept_id")
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
def learn_concept(concept_id: str, output: str) -> None:
    """Show one grammar concept with Foster and traditional terms."""
    _emit_learn_payload(_grammar_concept_detail_payload(concept_id), output)


@learn_cli.command("evidence-report")
@click.option("--kind", help="Optional concept kind filter, e.g. case, number, process.")
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
def learn_evidence_report(kind: str | None, output: str) -> None:
    """Summarize grammar-source evidence coverage for exposed concepts."""
    _emit_grammar_evidence_report_payload(_grammar_evidence_report_payload(kind), output)


@learn_cli.command("map")
@click.option(
    "--feature",
    "features",
    multiple=True,
    help="Morphology feature in key=value form. May be supplied more than once.",
)
@click.option("--part-of-speech", "--pos", default="unknown", show_default=True)
@click.option("--paradigm-kind", default="unknown", show_default=True)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
def learn_map(
    features: tuple[str, ...],
    part_of_speech: str,
    paradigm_kind: str,
    output: str,
) -> None:
    """Map morphology facts to teachable grammar concepts."""
    _emit_learn_payload(
        _learn_map_payload(
            features=features,
            part_of_speech=part_of_speech,
            paradigm_kind=paradigm_kind,
        ),
        output,
    )


main.add_command(learn_cli)


def _reader_service_from_context(ctx: click.Context):
    from langnet.reader.service import ReaderService  # noqa: PLC0415

    obj = ctx.obj if isinstance(ctx.obj, dict) else {}
    catalog = obj.get("reader_catalog")
    return ReaderService(_reader_catalog_path(str(catalog) if catalog else None))


def _reader_catalog_path(catalog: str | None) -> Path:
    from langnet.databuild.paths import default_reader_catalog_path  # noqa: PLC0415

    env_catalog = os.environ.get("LANGNET_READER_CATALOG")
    return (
        Path(str(catalog)).expanduser()
        if catalog
        else Path(env_catalog).expanduser()
        if env_catalog
        else default_reader_catalog_path()
    )


def _reader_search_index_path(index: str | None) -> Path:
    from langnet.databuild.paths import default_reader_search_index_path  # noqa: PLC0415

    return Path(index).expanduser() if index else default_reader_search_index_path()


def _emit_reader_payload(payload: Mapping[str, object], output: str) -> None:
    if output == "json":
        click.echo(orjson.dumps(payload, option=orjson.OPT_INDENT_2).decode("utf-8"))
        return
    mode = str(payload.get("mode", "reader"))
    if _emit_reader_single_payload(mode, payload):
        return

    items = payload.get("items")
    if not isinstance(items, Sequence):
        return
    for item in items:
        if not isinstance(item, Mapping):
            continue
        _emit_reader_item(mode, cast(Mapping[str, object], item))


def _emit_reader_single_payload(  # noqa: C901, PLR0911
    mode: str, payload: Mapping[str, object]
) -> bool:
    if mode == "show":
        segment_value = payload.get("segment")
        if not isinstance(segment_value, Mapping):
            click.echo("No segment found.")
            return True
        segment = cast(Mapping[str, object], segment_value)
        click.echo(f"{segment.get('address')}  {segment.get('citation_path')}")
        click.echo(str(segment.get("text", "")))
        return True
    if mode == "resolve-address":
        click.echo(f"{payload.get('address')} -> {payload.get('resolved_address')}")
        segment_value = payload.get("segment")
        if isinstance(segment_value, Mapping):
            segment = cast(Mapping[str, object], segment_value)
            click.echo(str(segment.get("text", "")))
        return True
    if mode == "summary":
        summary_value = payload.get("summary")
        if isinstance(summary_value, Mapping):
            summary = cast(Mapping[str, object], summary_value)
            for key, value in sorted(summary.items()):
                click.echo(f"{key}: {value}")
        return True
    if mode.startswith("search-index-"):
        summary_value = payload.get("summary")
        if isinstance(summary_value, Mapping):
            summary = cast(Mapping[str, object], summary_value)
            for key, value in sorted(summary.items()):
                click.echo(f"{key}: {value}")
        return True
    if mode == "work":
        item_value = payload.get("item")
        if not isinstance(item_value, Mapping):
            click.echo("No work found.")
            return True
        item = cast(Mapping[str, object], item_value)
        click.echo(
            f"{item.get('language')}  {item.get('author')} — {item.get('title')}  "
            f"[{item.get('work_id')}]"
        )
        return True
    return False


def _emit_reader_item(mode: str, item: Mapping[str, object]) -> None:  # noqa: C901, PLR0912
    if mode == "collections":
        click.echo(
            f"{item.get('collection_id')}  works={item.get('work_count')}  "
            f"words={item.get('word_count')}"
        )
    elif mode == "authors":
        lang = item.get("language")
        source_author = (
            item.get("source_author_name") or item.get("display_name") or item.get("author")
        )
        canonical_author = item.get("canonical_author_name") or item.get("author_canonical_name")
        author = (
            f"{canonical_author} <= {source_author}"
            if canonical_author and canonical_author != source_author
            else source_author
        )
        work_count = item.get("work_count")
        section = item.get("section_key")
        classifier = ""
        if item.get("author_agent_kind"):
            classifier = (
                f"  kind={item.get('author_agent_kind')}"
                f"  status={item.get('author_historicity_status')}"
            )
        click.echo(
            f"{lang}  {section}  {author}  works={work_count}  words={item.get('word_count')}"
            f"{classifier}"
        )
    elif mode == "author-sections":
        click.echo(
            f"{item.get('key')}  authors={item.get('author_count')}  "
            f"works={item.get('work_count')}  words={item.get('word_count')}"
        )
    elif mode == "duplicate-audit":
        click.echo(
            f"{item.get('language')}  {item.get('kind')}  {item.get('display')}  "
            f"works={item.get('work_count')}"
        )
    elif mode in {"popular", "works"}:
        click.echo(
            f"{item.get('language')}  {item.get('author')} — {item.get('title')}  "
            f"[{item.get('work_id')}]  words={item.get('word_count')}"
        )
    elif mode == "search":
        click.echo(
            f"{item.get('score')}  {item.get('language')}  {item.get('author')} — "
            f"{item.get('title')} {item.get('citation_path')}: {item.get('snippet')}"
        )
    elif mode == "contents":
        click.echo(f"{item.get('citation_path')}  {item.get('text')}")
    elif mode == "map":
        click.echo(
            f"{item.get('ordinal')}  {item.get('kind')}  {item.get('label')}  "
            f"{item.get('start_citation')}..{item.get('end_citation')}  "
            f"words={item.get('word_count')}"
        )
    elif mode == "aliases":
        click.echo(f"{item.get('language')}  {item.get('alias')} -> {item.get('target')}")
    elif mode == "alias-check":
        click.echo(f"{item.get('language')}  {item.get('alias')}  {item.get('targets')}")
    elif mode == "overlays":
        click.echo(
            f"{item.get('collection_id')}  {item.get('status')}  "
            f"{item.get('match_field')}={item.get('match_value')}  "
            f"{item.get('field')}={item.get('value')}"
        )
    elif mode == "attributions":
        click.echo(
            f"{item.get('collection_id')}  {item.get('status')}  "
            f"{item.get('match_field')}={item.get('match_value')}  "
            f"{item.get('relation_type')}={item.get('agent')}  "
            f"confidence={item.get('confidence')}"
        )
    elif mode == "sources":
        click.echo(
            f"{item.get('collection_id')}  {item.get('file_status')}  "
            f"{item.get('file_role')}  {item.get('source_path')}"
        )
    elif mode == "metadata":
        click.echo(
            f"{item.get('collection_id')}  {item.get('subject_kind')}  "
            f"{item.get('subject_id')}  {item.get('key')}={item.get('value')}"
        )
    elif mode == "validate":
        click.echo(f"{item.get('code')}  {item.get('message')}")
    elif mode == "catalogs":
        click.echo(
            f"{item.get('id')}  {item.get('readiness')}  "
            f"works={item.get('work_count')}  {item.get('path')}"
        )
    elif mode == "facets":
        detail = item.get("filter") or item.get("command") or ""
        click.echo(f"{item.get('id')}  {item.get('label')}  {detail}")
    elif mode == "author-facets":
        click.echo(f"{item.get('id')}  {item.get('label')}  {item.get('filter')}")


@click.group("reader")
@click.option(
    "--catalog",
    "--catalog-path",
    type=click.Path(),
    default=None,
    help=(
        "Reader catalog DuckDB path "
        "(defaults to LANGNET_READER_CATALOG, then data/build/reader/catalog.duckdb)."
    ),
)
@click.pass_context
def reader_cli(ctx: click.Context, catalog: str | None) -> None:
    """Explore locally indexed reader corpora."""
    ctx.obj = {"reader_catalog": catalog}


@reader_cli.command("collections")
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_collections(ctx: click.Context, output: str) -> None:
    """List reader corpus collections."""
    _emit_reader_payload(_reader_service_from_context(ctx).collections_payload(), output)


@reader_cli.command("catalogs")
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
def reader_catalogs(output: str) -> None:
    """List known reader catalog candidates for downstream UIs."""
    from langnet.reader.service import READER_SCHEMA_VERSION, ReaderService  # noqa: PLC0415

    candidates = [
        (
            "env",
            "Environment reader catalog",
            os.environ.get("LANGNET_READER_CATALOG"),
            "configured" if os.environ.get("LANGNET_READER_CATALOG") else "not_configured",
        ),
        (
            "default",
            "Default reader catalog",
            "data/build/reader/catalog.duckdb",
            "default",
        ),
        (
            "development",
            "Development unified reader catalog",
            "data/build/reader/catalog.duckdb",
            "development",
        ),
        (
            "classics",
            "Audit: Greek and Latin Classics",
            "examples/debug/reader_classics_legacy_full_curated_current/catalog.duckdb",
            "audit_artifact",
        ),
        (
            "sanskrit",
            "Audit: Sanskrit",
            "examples/debug/reader_sanskrit_full_curated_current/catalog.duckdb",
            "audit_artifact",
        ),
        (
            "perseus",
            "Audit: Perseus Classics",
            "examples/debug/reader_perseus_full_curated_current/catalog.duckdb",
            "audit_artifact",
        ),
        (
            "digiliblt",
            "Audit: digilibLT",
            "examples/debug/reader_digiliblt_anonymous_overlay_verify/catalog.duckdb",
            "audit_artifact",
        ),
    ]
    items = []
    for catalog_id, label, path_value, readiness in candidates:
        if not path_value:
            continue
        path = Path(path_value).expanduser()
        exists = path.exists()
        summary = ReaderService(path).summary()["summary"] if exists else {}
        items.append(
            {
                "id": catalog_id,
                "label": label,
                "path": str(path),
                "exists": exists,
                "languages": _reader_catalog_languages(path),
                "work_count": summary.get("work_count", 0),
                "segment_count": summary.get("segment_count", 0),
                "readiness": readiness if exists else "missing",
            }
        )
    _emit_reader_payload(
        {
            "schema_version": READER_SCHEMA_VERSION,
            "mode": "catalogs",
            "items": items,
        },
        output,
    )


def _reader_catalog_languages(path: Path) -> list[str]:
    if not path.exists():
        return []
    with duckdb.connect(str(path), read_only=True) as conn:
        return [
            str(row[0])
            for row in conn.execute(
                "SELECT DISTINCT language FROM works ORDER BY language"
            ).fetchall()
        ]


@reader_cli.command("authors")
@click.option("--language", default=None, help="Optional language filter, e.g. grc, lat, san.")
@click.option("--section", default=None, help="Optional native author-index section key.")
@click.option("--query", default=None, help="Optional author/authority substring filter.")
@click.option(
    "--agent-kind",
    type=click.Choice(AUTHOR_AGENT_KIND_VALUES),
    default=None,
    help="Generated author kind filter.",
)
@click.option(
    "--historicity",
    type=click.Choice(AUTHOR_HISTORICITY_STATUS_VALUES),
    default=None,
    help="Generated author historicity filter.",
)
@click.option(
    "--sort",
    "sort_order",
    type=click.Choice(["catalog", "prominence"]),
    default="catalog",
    show_default=True,
    help="Author ordering.",
)
@click.option("--limit", default=None, type=click.IntRange(1, 5000), help="Maximum rows.")
@click.option("--cursor", default=None, help="Offset cursor returned by prior JSON response.")
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_authors(  # noqa: PLR0913
    ctx: click.Context,
    language: str | None,
    section: str | None,
    query: str | None,
    agent_kind: str | None,
    historicity: str | None,
    sort_order: str,
    limit: int | None,
    cursor: str | None,
    output: str,
) -> None:
    """List reader corpus authors."""
    _emit_reader_payload(
        _reader_service_from_context(ctx).authors_payload(
            language=language,
            section=section,
            query=query,
            agent_kind=agent_kind,
            historicity=historicity,
            sort=sort_order,
            limit=limit,
            cursor=cursor,
        ),
        output,
    )


@reader_cli.command("author-sections")
@click.option("--language", required=True, help="Reader language, e.g. grc, lat, san.")
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_author_sections(ctx: click.Context, language: str, output: str) -> None:
    """List native author-index sections for one reader language."""
    _emit_reader_payload(
        _reader_service_from_context(ctx).author_sections_payload(language=language),
        output,
    )


@reader_cli.command("author")
@click.argument("author_ref")
@click.option("--language", default=None, help="Optional language filter, e.g. grc, lat, san.")
@click.option(
    "--representative-limit",
    default=8,
    show_default=True,
    type=click.IntRange(1, 50),
    help="Representative works to include.",
)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_author(
    ctx: click.Context,
    author_ref: str,
    language: str | None,
    representative_limit: int,
    output: str,
) -> None:
    """Show detail metadata for one reader author selector or name."""
    _emit_reader_payload(
        _reader_service_from_context(ctx).author_payload(
            author_ref,
            language=language,
            representative_limit=representative_limit,
        ),
        output,
    )


@reader_cli.command("author-facets")
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_author_facets(ctx: click.Context, output: str) -> None:
    """List generated author classification filters."""
    _emit_reader_payload(_reader_service_from_context(ctx).author_facets_payload(), output)


@reader_cli.command("duplicate-audit")
@click.option(
    "--kind",
    type=click.Choice(["authors", "titles"]),
    default="authors",
    show_default=True,
    help="Duplicate grouping to inspect.",
)
@click.option("--language", default=None, help="Optional language filter, e.g. grc, lat, san.")
@click.option("--limit", default=100, show_default=True, type=click.IntRange(1, 5000))
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_duplicate_audit(
    ctx: click.Context,
    kind: str,
    language: str | None,
    limit: int,
    output: str,
) -> None:
    """List duplicate-looking author or title groups for corpus QA."""
    _emit_reader_payload(
        _reader_service_from_context(ctx).duplicate_audit_payload(
            kind=kind,
            language=language,
            limit=limit,
        ),
        output,
    )


@reader_cli.command("classification-export")
@click.option("--language", default=None, help="Optional language filter, e.g. grc, lat, san.")
@click.option("--limit", default=None, type=click.IntRange(1, 100000), help="Maximum rows.")
@click.option(
    "--path",
    "output_path",
    type=click.Path(path_type=Path),
    default=None,
    help="CSV output path. Defaults to stdout.",
)
@click.pass_context
def reader_classification_export(
    ctx: click.Context,
    language: str | None,
    limit: int | None,
    output_path: Path | None,
) -> None:
    """Export work rows for bulk chronology/status/popularity classification."""
    payload = _reader_service_from_context(ctx).works_payload(language=language, limit=limit)
    items = payload.get("items")
    if not isinstance(items, Sequence):
        items = []
    fieldnames = CLASSIFICATION_OUTPUT_FIELDS

    def write_rows(handle) -> None:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for raw_item in items:
            if not isinstance(raw_item, Mapping):
                continue
            item = cast(Mapping[str, object], raw_item)
            writer.writerow({name: item.get(name, "") or "" for name in fieldnames})

    if output_path is None:
        write_rows(sys.stdout)
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        write_rows(handle)
    click.echo(str(output_path))


@reader_cli.command("author-classification-export")
@click.option("--language", default=None, help="Optional language filter, e.g. grc, lat, san.")
@click.option("--limit", default=None, type=click.IntRange(1, 100000), help="Maximum rows.")
@click.option(
    "--path",
    "output_path",
    type=click.Path(path_type=Path),
    default=None,
    help="CSV output path. Defaults to stdout.",
)
@click.pass_context
def reader_author_classification_export(
    ctx: click.Context,
    language: str | None,
    limit: int | None,
    output_path: Path | None,
) -> None:
    """Export author rows for generated agent classification."""
    payload = _reader_service_from_context(ctx).authors_payload(
        language=language,
        limit=limit,
    )
    items = payload.get("items")
    if not isinstance(items, Sequence):
        items = []
    fieldnames = AUTHOR_CLASSIFICATION_OUTPUT_FIELDS

    def write_rows(handle) -> None:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for raw_item in items:
            if not isinstance(raw_item, Mapping):
                continue
            item = cast(Mapping[str, object], raw_item)
            writer.writerow(
                {
                    "author_id": item.get("author_id", "") or "",
                    "author_language": item.get("language", "") or "",
                    "author_source_id": item.get("source_author_id", "") or "",
                    "author_display_name": item.get("display_name", "") or "",
                    "author_canonical_name": item.get("author_canonical_name", "") or "",
                    "author_agent_kind": item.get("author_agent_kind", "") or "",
                    "author_historicity_status": item.get(
                        "author_historicity_status",
                        "",
                    )
                    or "",
                    "author_period": item.get("author_period", "") or "",
                    "author_date_range": item.get("author_date_range", "") or "",
                    "author_region": item.get("author_region", "") or "",
                    "author_cultural_context": item.get("author_cultural_context", "") or "",
                    "author_bio": item.get("author_bio", "") or "",
                    "author_prominence_score": item.get("author_prominence_score", "") or "",
                    "author_prominence_tier": item.get("author_prominence_tier", "") or "",
                    "author_confidence": item.get("author_classification_confidence", "") or "",
                    "author_notes": item.get("author_classification_notes", "") or "",
                    "author_generator_models": item.get("author_generator_models", "") or "",
                    "author_generator_run_id": item.get("author_generator_run_id", "") or "",
                    "work_count": item.get("work_count", "") or "",
                    "word_count": item.get("word_count", "") or "",
                    "representative_titles": item.get("representative_titles", "") or "",
                }
            )

    if output_path is None:
        write_rows(sys.stdout)
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        write_rows(handle)
    click.echo(str(output_path))


@reader_cli.command("classify-works")
@click.option(
    "--input-csv",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="CSV produced by reader classification-export.",
)
@click.option(
    "--output-csv",
    type=click.Path(dir_okay=False, path_type=Path),
    required=True,
    help="Generated classification CSV to write.",
)
@click.option(
    "--model",
    default=DEFAULT_CLASSIFICATION_MODEL,
    show_default=True,
    help="OpenRouter/aisuite model identifier.",
)
@click.option("--run-id", default=None, help="Classifier run id. Defaults to timestamp.")
@click.option(
    "--batch-size",
    default=DEFAULT_CLASSIFICATION_BATCH_SIZE,
    show_default=True,
    type=click.IntRange(1, 200),
)
@click.option(
    "--timeout-seconds",
    default=DEFAULT_CLASSIFICATION_TIMEOUT_SECONDS,
    show_default=True,
    type=click.FloatRange(1.0, 600.0),
    help="Per-provider-call timeout.",
)
@click.option(
    "--max-attempts",
    default=DEFAULT_CLASSIFICATION_MAX_ATTEMPTS,
    show_default=True,
    type=click.IntRange(1, 10),
    help="Attempts per model batch before failing.",
)
@click.option(
    "--concurrency",
    default=1,
    show_default=True,
    type=click.IntRange(1, 8),
    help="Number of model batches to request concurrently.",
)
@click.option(
    "--raw-response-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="Optional directory for raw model JSON responses.",
)
@click.option(
    "--shuffle-seed",
    default=None,
    help=(
        "Optional deterministic seed for shuffling rows before batching. "
        "The output CSV keeps input order."
    ),
)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
def reader_classify_works(  # noqa: PLR0913
    input_csv: Path,
    output_csv: Path,
    model: str,
    run_id: str | None,
    batch_size: int,
    timeout_seconds: float,
    max_attempts: int,
    concurrency: int,
    raw_response_dir: Path | None,
    shuffle_seed: str | None,
    output: str,
) -> None:
    """Generate classifier-filled reader work metadata CSV with a model."""
    resolved_run_id = run_id or time.strftime("reader-classifier-%Y%m%d-%H%M%S")
    summary = classify_work_csv(
        config=ClassificationRunConfig(
            input_csv=input_csv.expanduser(),
            output_csv=output_csv.expanduser(),
            model=model,
            run_id=resolved_run_id,
            batch_size=batch_size,
            raw_response_dir=raw_response_dir.expanduser() if raw_response_dir else None,
            shuffle_seed=shuffle_seed,
            concurrency=concurrency,
        ),
        classify=_openrouter_work_classifier_callback(
            model,
            timeout_seconds=timeout_seconds,
            max_attempts=max_attempts,
        ),
    )
    payload = {
        "schema_version": "langnet.reader.v1",
        "mode": "classify-works",
        "summary": summary,
    }
    if output == "json":
        click.echo(orjson.dumps(payload, option=orjson.OPT_INDENT_2).decode("utf-8"))
        return
    click.echo(
        f"Generated {summary['generated_count']} classification row(s) "
        f"from {summary['input_count']} input row(s): {summary['output_csv']}"
    )


@reader_cli.command("classify-authors")
@click.option(
    "--input-csv",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="CSV produced by author-classification-export.",
)
@click.option(
    "--output-csv",
    type=click.Path(dir_okay=False, path_type=Path),
    required=True,
    help="Generated author classification CSV to write.",
)
@click.option(
    "--model",
    default=DEFAULT_CLASSIFICATION_MODEL,
    show_default=True,
    help="OpenRouter/aisuite model identifier.",
)
@click.option("--run-id", default=None, help="Classifier run id. Defaults to timestamp.")
@click.option(
    "--batch-size",
    default=DEFAULT_CLASSIFICATION_BATCH_SIZE,
    show_default=True,
    type=click.IntRange(1, 200),
)
@click.option(
    "--timeout-seconds",
    default=DEFAULT_CLASSIFICATION_TIMEOUT_SECONDS,
    show_default=True,
    type=click.FloatRange(1.0, 600.0),
    help="Per-provider-call timeout.",
)
@click.option(
    "--max-attempts",
    default=DEFAULT_CLASSIFICATION_MAX_ATTEMPTS,
    show_default=True,
    type=click.IntRange(1, 10),
    help="Attempts per model batch before failing.",
)
@click.option(
    "--concurrency",
    default=1,
    show_default=True,
    type=click.IntRange(1, 8),
    help="Number of model batches to request concurrently.",
)
@click.option(
    "--raw-response-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="Optional directory for raw model JSON responses.",
)
@click.option(
    "--shuffle-seed",
    default=None,
    help="Optional deterministic seed for shuffling rows before batching.",
)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
def reader_classify_authors(  # noqa: PLR0913
    input_csv: Path,
    output_csv: Path,
    model: str,
    run_id: str | None,
    batch_size: int,
    timeout_seconds: float,
    max_attempts: int,
    concurrency: int,
    raw_response_dir: Path | None,
    shuffle_seed: str | None,
    output: str,
) -> None:
    """Generate author/agent classification CSV with a model."""
    resolved_run_id = run_id or time.strftime("reader-author-classifier-%Y%m%d-%H%M%S")
    summary = classify_author_csv(
        config=AuthorClassificationRunConfig(
            input_csv=input_csv.expanduser(),
            output_csv=output_csv.expanduser(),
            model=model,
            run_id=resolved_run_id,
            batch_size=batch_size,
            raw_response_dir=raw_response_dir.expanduser() if raw_response_dir else None,
            shuffle_seed=shuffle_seed,
            concurrency=concurrency,
        ),
        classify=_openrouter_author_classifier_callback(
            model,
            timeout_seconds=timeout_seconds,
            max_attempts=max_attempts,
        ),
    )
    payload = {
        "schema_version": "langnet.reader.v1",
        "mode": "classify-authors",
        "summary": summary,
    }
    if output == "json":
        click.echo(orjson.dumps(payload, option=orjson.OPT_INDENT_2).decode("utf-8"))
        return
    click.echo(
        f"Generated {summary['generated_count']} author row(s) "
        f"from {summary['input_count']} input row(s): {summary['output_csv']}"
    )


@reader_cli.command("works")
@click.option("--language", default=None, help="Optional language filter, e.g. grc, lat, san.")
@click.option("--collection", "collection_id", default=None, help="Optional collection filter.")
@click.option("--author", default=None, help="Optional display-author substring filter.")
@click.option("--author-id", default=None, help="Optional author index selector or authority id.")
@click.option(
    "--attributed-to",
    default=None,
    help="Optional catalog-only display author or accepted authorship-claim filter.",
)
@click.option(
    "--scope",
    "classification_scope",
    default=None,
    help="Optional generated classification scope/category filter, e.g. grammar or medicine.",
)
@click.option(
    "--group",
    "classification_group",
    default=None,
    help="Optional strict discovery group filter, e.g. grammar, medicine, or epic.",
)
@click.option(
    "--tag",
    "classification_tag",
    default=None,
    help="Optional strict discovery tag filter, e.g. ayurveda, tragedy, or patristics.",
)
@click.option("--query", default=None, help="Optional title/author/id/alias substring filter.")
@click.option("--limit", default=None, type=click.IntRange(1, 5000), help="Maximum rows.")
@click.option("--cursor", default=None, help="Offset cursor returned by prior JSON response.")
@click.option(
    "--sort",
    "sort_order",
    type=click.Choice(["catalog", "popularity", "global-popularity", "group-popularity"]),
    default="catalog",
    show_default=True,
    help="Work ordering.",
)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_works(  # noqa: PLR0913
    ctx: click.Context,
    language: str | None,
    collection_id: str | None,
    author: str | None,
    author_id: str | None,
    attributed_to: str | None,
    classification_scope: str | None,
    classification_group: str | None,
    classification_tag: str | None,
    query: str | None,
    limit: int | None,
    cursor: str | None,
    sort_order: str,
    output: str,
) -> None:
    """List reader corpus works."""
    _emit_reader_payload(
        _reader_service_from_context(ctx).works_payload(
            language=language,
            collection_id=collection_id,
            author=author,
            author_id=author_id,
            attributed_to=attributed_to,
            classification_scope=classification_scope,
            classification_group=classification_group,
            classification_tag=classification_tag,
            query=query,
            limit=limit,
            cursor=cursor,
            sort=sort_order,
        ),
        output,
    )


@reader_cli.command("popular")
@click.option("--language", default=None, help="Optional language filter, e.g. grc, lat, san.")
@click.option("--collection", "collection_id", default=None, help="Optional collection filter.")
@click.option(
    "--scope",
    "classification_scope",
    default=None,
    help="Optional generated classification scope/category filter, e.g. grammar or medicine.",
)
@click.option(
    "--group",
    "classification_group",
    default=None,
    help="Optional strict discovery group filter, e.g. grammar, medicine, or epic.",
)
@click.option(
    "--tag",
    "classification_tag",
    default=None,
    help="Optional strict discovery tag filter, e.g. ayurveda, tragedy, or patristics.",
)
@click.option("--limit", default=50, show_default=True, type=click.IntRange(1, 5000))
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_popular(  # noqa: PLR0913
    ctx: click.Context,
    language: str | None,
    collection_id: str | None,
    classification_scope: str | None,
    classification_group: str | None,
    classification_tag: str | None,
    limit: int,
    output: str,
) -> None:
    """List works ordered by generated popularity metadata."""
    _emit_reader_payload(
        _reader_service_from_context(ctx).works_payload(
            language=language,
            collection_id=collection_id,
            classification_scope=classification_scope,
            classification_group=classification_group,
            classification_tag=classification_tag,
            limit=limit,
            sort="group-popularity" if classification_group or classification_tag else "popularity",
        )
        | {"mode": "popular"},
        output,
    )


@reader_cli.command("groups")
@click.option("--language", default=None, help="Optional language filter, e.g. grc, lat, san.")
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_groups(ctx: click.Context, language: str | None, output: str) -> None:
    """List strict reader discovery groups."""
    _emit_reader_payload(
        _reader_service_from_context(ctx).discovery_groups_payload(language=language),
        output,
    )


@reader_cli.command("tags")
@click.option("--language", default=None, help="Optional language filter, e.g. grc, lat, san.")
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_tags(ctx: click.Context, language: str | None, output: str) -> None:
    """List strict reader discovery tags."""
    _emit_reader_payload(
        _reader_service_from_context(ctx).discovery_tags_payload(language=language),
        output,
    )


@reader_cli.command("facets")
@click.option("--language", default=None, help="Optional language filter, e.g. grc, lat, san.")
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_facets(ctx: click.Context, language: str | None, output: str) -> None:
    """List reader discovery filters, sort modes, and example queries."""
    _emit_reader_payload(
        _reader_service_from_context(ctx).discovery_facets_payload(language=language),
        output,
    )


@reader_cli.command("shelves")
@click.option("--language", default=None, help="Optional language filter, e.g. grc, lat, san.")
@click.option("--limit", default=None, type=click.IntRange(1, None), help="Shelf count cap.")
@click.option(
    "--sample-limit",
    default=3,
    show_default=True,
    type=click.IntRange(0, 20),
    help="Representative works per shelf.",
)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_shelves(
    ctx: click.Context,
    language: str | None,
    limit: int | None,
    sample_limit: int,
    output: str,
) -> None:
    """List reader discovery shelves for a catalog or language."""
    _emit_reader_payload(
        _reader_service_from_context(ctx).discovery_shelves_payload(
            language=language,
            limit=limit,
            sample_limit=sample_limit,
        ),
        output,
    )


@reader_cli.command("coverage")
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_coverage(ctx: click.Context, output: str) -> None:
    """List per-language reader discovery coverage."""
    _emit_reader_payload(_reader_service_from_context(ctx).coverage_payload(), output)


@reader_cli.group("search-index")
def reader_search_index() -> None:
    """Build and inspect the derived reader full-text search index."""


@reader_search_index.command("build")
@click.option("--index", "index_path", type=click.Path(), default=None, help="Search index path.")
@click.option("--language", default=None, help="Optional language slice, e.g. grc, lat, san.")
@click.option("--collection", "collection_id", default=None, help="Optional collection slice.")
@click.option("--replace", is_flag=True, help="Replace existing derived search index tables.")
@click.option("--batch-size", default=50000, show_default=True, type=click.IntRange(1, None))
@click.option("--limit", default=None, type=click.IntRange(1, None), help="Debug segment cap.")
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_search_index_build(  # noqa: PLR0913
    ctx: click.Context,
    index_path: str | None,
    language: str | None,
    collection_id: str | None,
    replace: bool,
    batch_size: int,
    limit: int | None,
    output: str,
) -> None:
    """Build a derived segment-level reader text index."""
    _emit_reader_payload(
        _reader_service_from_context(ctx).search_index_build_payload(
            index_path=_reader_search_index_path(index_path),
            language=language,
            collection_id=collection_id,
            replace=replace,
            batch_size=batch_size,
            limit=limit,
        ),
        output,
    )


@reader_search_index.command("status")
@click.option("--index", "index_path", type=click.Path(), default=None, help="Search index path.")
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_search_index_status(ctx: click.Context, index_path: str | None, output: str) -> None:
    """Show derived reader text index status."""
    _emit_reader_payload(
        _reader_service_from_context(ctx).search_index_status_payload(
            index_path=_reader_search_index_path(index_path)
        ),
        output,
    )


@reader_search_index.command("validate")
@click.option("--index", "index_path", type=click.Path(), default=None, help="Search index path.")
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_search_index_validate(ctx: click.Context, index_path: str | None, output: str) -> None:
    """Validate the derived reader text index against the catalog."""
    _emit_reader_payload(
        _reader_service_from_context(ctx).search_index_validate_payload(
            index_path=_reader_search_index_path(index_path)
        ),
        output,
    )


@reader_search_index.command("inspect-normalize")
@click.option("--language", required=True, help="Language code, e.g. grc, lat, san.")
@click.argument("text")
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_search_index_inspect_normalize(
    ctx: click.Context,
    language: str,
    text: str,
    output: str,
) -> None:
    """Inspect language-aware search normalization for text."""
    _emit_reader_payload(
        _reader_service_from_context(ctx).search_index_inspect_normalize_payload(
            language=language,
            text=text,
        ),
        output,
    )


@reader_search_index.command("inspect-query")
@click.option("--language", required=True, help="Language code, e.g. grc, lat, san.")
@click.option(
    "--mode",
    "search_mode",
    type=click.Choice(["keyword", "phrase", "exact", "fuzzy"]),
    default="keyword",
    show_default=True,
)
@click.option(
    "--field",
    type=click.Choice(["auto", "display", "search", "folded"]),
    default="auto",
    show_default=True,
)
@click.argument("text")
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_search_index_inspect_query(  # noqa: PLR0913
    ctx: click.Context,
    language: str,
    search_mode: str,
    field: str,
    text: str,
    output: str,
) -> None:
    """Inspect language-aware reader search query candidates."""
    _emit_reader_payload(
        _reader_service_from_context(ctx).search_index_inspect_query_payload(
            language=language,
            text=text,
            mode=search_mode,
            field=field,
        ),
        output,
    )


@reader_cli.command("search")
@click.argument("query")
@click.option("--index", "index_path", type=click.Path(), default=None, help="Search index path.")
@click.option("--language", default=None, help="Optional language filter, e.g. grc, lat, san.")
@click.option("--collection", "collection_id", default=None, help="Optional collection filter.")
@click.option("--work-id", default=None, help="Optional work id filter.")
@click.option("--author-id", default=None, help="Optional canonical author id filter.")
@click.option("--group", default=None, help="Optional discovery group filter.")
@click.option("--tag", default=None, help="Optional discovery tag filter.")
@click.option(
    "--mode",
    "search_mode",
    type=click.Choice(["keyword", "phrase", "exact", "fuzzy"]),
    default="keyword",
    show_default=True,
)
@click.option(
    "--field",
    type=click.Choice(["auto", "display", "search", "folded"]),
    default="auto",
    show_default=True,
)
@click.option("--context", default=0, type=click.IntRange(0, 20), show_default=True)
@click.option("--limit", default=20, type=click.IntRange(1, 500), show_default=True)
@click.option("--cursor", default=None, help="Offset cursor returned by prior JSON response.")
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_search(  # noqa: PLR0913
    ctx: click.Context,
    query: str,
    index_path: str | None,
    language: str | None,
    collection_id: str | None,
    work_id: str | None,
    author_id: str | None,
    group: str | None,
    tag: str | None,
    search_mode: str,
    field: str,
    context: int,
    limit: int,
    cursor: str | None,
    output: str,
) -> None:
    """Search indexed reader corpus text."""
    _emit_reader_payload(
        _reader_service_from_context(ctx).search_payload(
            index_path=_reader_search_index_path(index_path),
            query=query,
            language=language,
            collection_id=collection_id,
            work_id=work_id,
            author_id=author_id,
            group=group,
            tag=tag,
            mode=search_mode,
            field=field,
            context=context,
            limit=limit,
            cursor=cursor,
        ),
        output,
    )


@reader_cli.command("work")
@click.argument("work_ref")
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_work(ctx: click.Context, work_ref: str, output: str) -> None:
    """Show exact metadata for one work id, CTS work URN, or alias."""
    _emit_reader_payload(_reader_service_from_context(ctx).work_payload(work_ref), output)


@reader_cli.command("map")
@click.argument("work_ref")
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_map(ctx: click.Context, work_ref: str, output: str) -> None:
    """Show a table-of-contents style map for one reader work."""
    _emit_reader_payload(_reader_service_from_context(ctx).map_payload(work_ref), output)


@reader_cli.command("sync-work-maps")
@click.option(
    "--work-map-dir",
    type=click.Path(),
    default="data/curated/reader_work_maps",
    show_default=True,
    help="Curated reader work-map/table-of-contents directory.",
)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_sync_work_maps(ctx: click.Context, work_map_dir: str, output: str) -> None:
    """Sync curated work-map/table-of-contents metadata into the reader catalog."""
    _emit_reader_payload(
        _reader_service_from_context(ctx).sync_work_maps_payload(Path(work_map_dir).expanduser()),
        output,
    )


@reader_cli.command("sync-classifications")
@click.option(
    "--classification-csv",
    type=click.Path(path_type=Path),
    required=True,
    help="Generated reader classification CSV file or directory of CSV files.",
)
@click.option(
    "--merge",
    is_flag=True,
    help="Replace only rows present in the CSV, preserving other classifications.",
)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_sync_classifications(
    ctx: click.Context,
    classification_csv: Path,
    merge: bool,
    output: str,
) -> None:
    """Sync generated work classification/popularity metadata into the reader catalog."""
    _emit_reader_payload(
        _reader_service_from_context(ctx).sync_classifications_payload(
            classification_csv.expanduser(),
            merge=merge,
        ),
        output,
    )


@reader_cli.command("sync-author-classifications")
@click.option(
    "--classification-csv",
    type=click.Path(path_type=Path),
    required=True,
    help="Generated author classification CSV file or directory.",
)
@click.option(
    "--merge",
    is_flag=True,
    help="Replace only author rows present in the CSV.",
)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_sync_author_classifications(
    ctx: click.Context,
    classification_csv: Path,
    merge: bool,
    output: str,
) -> None:
    """Sync generated author classification metadata."""
    _emit_reader_payload(
        _reader_service_from_context(ctx).sync_author_classifications_payload(
            classification_csv.expanduser(),
            merge=merge,
        ),
        output,
    )


@reader_cli.command("sync-metadata-overlays")
@click.option(
    "--metadata-overlay-dir",
    type=click.Path(path_type=Path),
    default=Path("data/curated/reader_metadata"),
    show_default=True,
    help="Curated reader metadata overlay YAML root.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Report accepted overlay updates without modifying works.",
)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_sync_metadata_overlays(
    ctx: click.Context,
    metadata_overlay_dir: Path,
    dry_run: bool,
    output: str,
) -> None:
    """Sync curated metadata overlays and apply accepted display updates."""
    _emit_reader_payload(
        _reader_service_from_context(ctx).sync_metadata_overlays_payload(
            metadata_overlay_dir.expanduser(),
            dry_run=dry_run,
        ),
        output,
    )


@reader_cli.command("sync-metadata-attributions")
@click.option(
    "--metadata-attribution-dir",
    type=click.Path(path_type=Path),
    default=Path("data/curated/reader_attributions"),
    show_default=True,
    help="Curated reader metadata attribution YAML root.",
)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_sync_metadata_attributions(
    ctx: click.Context,
    metadata_attribution_dir: Path,
    output: str,
) -> None:
    """Sync curated attribution claims that support didactic display."""
    _emit_reader_payload(
        _reader_service_from_context(ctx).sync_metadata_attributions_payload(
            metadata_attribution_dir.expanduser(),
        ),
        output,
    )


@reader_cli.command("repair-languages")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Report work-language repairs without modifying the catalog.",
)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_repair_languages(ctx: click.Context, dry_run: bool, output: str) -> None:
    """Repair primary work languages in an existing reader catalog."""
    _emit_reader_payload(
        _reader_service_from_context(ctx).repair_languages_payload(dry_run=dry_run),
        output,
    )


@reader_cli.command("prune-stale-classifications")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Report stale generated classification rows without modifying the catalog.",
)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_prune_stale_classifications(
    ctx: click.Context,
    dry_run: bool,
    output: str,
) -> None:
    """Remove generated work classifications from the wrong language batch."""
    _emit_reader_payload(
        _reader_service_from_context(ctx).prune_stale_classifications_payload(
            dry_run=dry_run,
        ),
        output,
    )


@reader_cli.command("sync-source-enrichment")
@click.option(
    "--dcs-corpus-table",
    type=click.Path(path_type=Path),
    default=None,
    help="DCS corpus table capture with Text, Author, Time slot, and Subject columns.",
)
@click.option(
    "--dcs-chapter-info",
    type=click.Path(path_type=Path),
    default=None,
    help="DCS chapter-info.xml lookup file.",
)
@click.option(
    "--perseus-catalog-results",
    type=click.Path(path_type=Path),
    multiple=True,
    help="Scraped Perseus catalog search result markdown for one subject URL.",
)
@click.option(
    "--perseus-collection-id",
    default="perseus",
    show_default=True,
    help="Collection id for Perseus result metadata.",
)
@click.option(
    "--perseus-subject",
    default="",
    help="Perseus subject label represented by the result page.",
)
@click.option(
    "--perseus-source-url",
    default="",
    help="Source URL for the scraped Perseus result page.",
)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_sync_source_enrichment(  # noqa: PLR0913
    ctx: click.Context,
    dcs_corpus_table: Path | None,
    dcs_chapter_info: Path | None,
    perseus_catalog_results: tuple[Path, ...],
    perseus_collection_id: str,
    perseus_subject: str,
    perseus_source_url: str,
    output: str,
) -> None:
    """Sync source-backed DCS/Perseus enrichment metadata into the reader catalog."""
    if perseus_catalog_results and not perseus_subject:
        raise click.ClickException("--perseus-subject is required with Perseus result files")
    _emit_reader_payload(
        _reader_service_from_context(ctx).sync_source_enrichment_payload(
            dcs_corpus_table=dcs_corpus_table.expanduser() if dcs_corpus_table else None,
            dcs_chapter_info=dcs_chapter_info.expanduser() if dcs_chapter_info else None,
            perseus_catalog_results=tuple(path.expanduser() for path in perseus_catalog_results),
            perseus_collection_id=perseus_collection_id,
            perseus_subject=perseus_subject,
            perseus_source_url=perseus_source_url,
        ),
        output,
    )


@reader_cli.command("contents")
@click.argument("work_id")
@click.option("--limit", default=50, show_default=True, type=click.IntRange(1, 500))
@click.option("--cursor", default=None, help="Offset cursor returned by prior JSON response.")
@click.option("--from", "from_citation", default=None, help="Start at a citation path.")
@click.option("--around", default=None, help="Center contents around a citation path.")
@click.option("--radius", default=20, show_default=True, type=click.IntRange(1, 250))
@click.option(
    "--char-budget",
    default=None,
    type=click.IntRange(500, 100_000),
    help="Maximum text characters to return while preserving at least one segment.",
)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_contents(  # noqa: PLR0913
    ctx: click.Context,
    work_id: str,
    limit: int,
    cursor: str | None,
    from_citation: str | None,
    around: str | None,
    radius: int,
    char_budget: int | None,
    output: str,
) -> None:
    """List segments for one reader work."""
    _emit_reader_payload(
        _reader_service_from_context(ctx).contents_payload(
            work_id,
            limit=limit,
            cursor=cursor,
            from_citation=from_citation,
            around=around,
            radius=radius,
            char_budget=char_budget,
        ),
        output,
    )


@reader_cli.command("show")
@click.argument("address")
@click.option("--segment", default=None, help="Citation path when ADDRESS is a work id or alias.")
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_show(ctx: click.Context, address: str, segment: str | None, output: str) -> None:
    """Retrieve one segment by address, or by work plus --segment."""
    service = _reader_service_from_context(ctx)
    payload = service.show_work_segment(address, segment) if segment else service.show(address)
    _emit_reader_payload(payload, output)


@reader_cli.command("resolve-address")
@click.argument("address")
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_resolve_address(ctx: click.Context, address: str, output: str) -> None:
    """Resolve a reader address such as 'Od. 3.74'."""
    _emit_reader_payload(_reader_service_from_context(ctx).resolve_address(address), output)


@reader_cli.command("summary")
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_summary(ctx: click.Context, output: str) -> None:
    """Summarize the reader catalog."""
    _emit_reader_payload(_reader_service_from_context(ctx).summary(), output)


@reader_cli.command("aliases")
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_aliases(ctx: click.Context, output: str) -> None:
    """List reader aliases."""
    _emit_reader_payload(_reader_service_from_context(ctx).aliases(), output)


@reader_cli.command("alias-check")
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_alias_check(ctx: click.Context, output: str) -> None:
    """Report reader alias conflicts."""
    _emit_reader_payload(_reader_service_from_context(ctx).alias_conflicts(), output)


@reader_cli.command("overlays")
@click.option("--collection", "collection_id", default=None, help="Optional collection filter.")
@click.option("--status", default=None, help="Optional overlay status filter.")
@click.option("--field", default=None, help="Optional metadata field filter.")
@click.option("--match-value", default=None, help="Optional match value filter.")
@click.option("--limit", default=500, show_default=True, type=click.IntRange(1, 5000))
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_overlays(  # noqa: PLR0913
    ctx: click.Context,
    collection_id: str | None,
    status: str | None,
    field: str | None,
    match_value: str | None,
    limit: int,
    output: str,
) -> None:
    """List curated metadata overlay assertions and evidence."""
    _emit_reader_payload(
        _reader_service_from_context(ctx).overlays(
            collection_id=collection_id,
            status=status,
            field=field,
            match_value=match_value,
            limit=limit,
        ),
        output,
    )


@reader_cli.command("attributions")
@click.option("--collection", "collection_id", default=None, help="Optional collection filter.")
@click.option("--status", default=None, help="Optional attribution status filter.")
@click.option("--relation-type", default=None, help="Optional attribution relation type filter.")
@click.option("--agent", default=None, help="Optional person/group filter.")
@click.option("--match-value", default=None, help="Optional matched work/source value filter.")
@click.option("--limit", default=500, show_default=True, type=click.IntRange(1, 5000))
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_attributions(  # noqa: PLR0913
    ctx: click.Context,
    collection_id: str | None,
    status: str | None,
    relation_type: str | None,
    agent: str | None,
    match_value: str | None,
    limit: int,
    output: str,
) -> None:
    """List curated attribution claims that do not necessarily alter display metadata."""
    _emit_reader_payload(
        _reader_service_from_context(ctx).attributions(
            collection_id=collection_id,
            status=status,
            relation_type=relation_type,
            agent=agent,
            match_value=match_value,
            limit=limit,
        ),
        output,
    )


@reader_cli.command("overlay-review")
@click.option(
    "--metadata-overlay-dir",
    type=click.Path(path_type=Path),
    default=Path("data/curated/reader_metadata"),
    show_default=True,
    help="Curated reader metadata overlay YAML root.",
)
@click.option("--collection", "collection_id", default=None, help="Optional collection filter.")
@click.option("--field", default=None, help="Optional metadata field filter.")
@click.option("--match-value", default=None, help="Optional match value filter.")
@click.option("--limit", default=50, show_default=True, type=click.IntRange(1, 500))
@click.option(
    "--reviewer",
    type=click.Choice(["rule", "llm"]),
    default="rule",
    show_default=True,
    help="Use local rule recommendations or an OpenRouter LLM reviewer.",
)
@click.option(
    "--model",
    default=DEFAULT_RECOMMENDATION_MODEL,
    show_default=True,
    help="OpenRouter model id used when --reviewer llm.",
)
@click.option(
    "--apply",
    "apply_changes",
    is_flag=True,
    help="Prompt to promote reviewed candidates in their YAML files.",
)
@click.option(
    "--yes",
    is_flag=True,
    help="With --apply, approve every accept recommendation without prompting.",
)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
def reader_overlay_review(  # noqa: PLR0913
    metadata_overlay_dir: Path,
    collection_id: str | None,
    field: str | None,
    match_value: str | None,
    limit: int,
    reviewer: str,
    model: str,
    apply_changes: bool,
    yes: bool,
    output: str,
) -> None:
    """Review candidate metadata overlays and optionally promote them."""
    from langnet.reader.metadata_overlay_review import (  # noqa: PLC0415
        llm_overlay_reviewer,
        review_metadata_overlay_candidates,
        review_to_payload,
        rule_overlay_reviewer,
    )

    review_callback = (
        (lambda overlay: llm_overlay_reviewer(overlay, model=model))
        if reviewer == "llm"
        else rule_overlay_reviewer
    )

    def approve(review) -> bool:
        if yes:
            return review.decision.recommendation == "accept"
        _emit_reader_overlay_review_item(review_to_payload(review))
        return click.confirm("Promote to accepted?", default=False)

    reviews = review_metadata_overlay_candidates(
        metadata_overlay_dir,
        reviewer=review_callback,
        collection_id=collection_id,
        field=field,
        match_value=match_value,
        limit=limit,
        apply=apply_changes,
        approve=approve,
    )
    payload = {
        "schema_version": "langnet.reader.overlay_review.v1",
        "mode": "overlay-review",
        "metadata_overlay_dir": str(metadata_overlay_dir),
        "request": {
            "collection_id": collection_id,
            "field": field,
            "match_value": match_value,
            "limit": limit,
            "reviewer": reviewer,
            "model": model if reviewer == "llm" else "local-rule",
            "apply": apply_changes,
            "yes": yes,
        },
        "items": [review_to_payload(review) for review in reviews],
    }
    if output == "json":
        click.echo(orjson.dumps(payload, option=orjson.OPT_INDENT_2).decode("utf-8"))
        return
    if not reviews:
        click.echo("No candidate overlays found.")
        return
    if not apply_changes:
        for item in payload["items"]:
            _emit_reader_overlay_review_item(cast(Mapping[str, object], item))
    applied = sum(1 for review in reviews if review.applied)
    click.echo(f"reviewed={len(reviews)} applied={applied}")


def _emit_reader_overlay_review_item(item: Mapping[str, object]) -> None:
    click.echo(
        f"{item.get('collection_id')}  {item.get('match_value')}  "
        f"{item.get('field')}={item.get('value')}"
    )
    click.echo(
        f"  recommendation={item.get('recommendation')}  "
        f"confidence={item.get('review_confidence')}  reviewer={item.get('reviewer')}"
    )
    flags = item.get("flags")
    if isinstance(flags, Sequence) and not isinstance(flags, (str, bytes)):
        click.echo(f"  flags={', '.join(str(flag) for flag in flags) or 'none'}")
    click.echo(f"  rationale={item.get('rationale')}")


@reader_cli.command("sources")
@click.option("--collection", "collection_id", default=None, help="Optional collection filter.")
@click.option(
    "--status",
    "file_status",
    default=None,
    help="Optional status filter: text, metadata, or support.",
)
@click.option("--limit", default=500, show_default=True, type=click.IntRange(1, 5000))
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_sources(
    ctx: click.Context,
    collection_id: str | None,
    file_status: str | None,
    limit: int,
    output: str,
) -> None:
    """List source files classified during reader import."""
    _emit_reader_payload(
        _reader_service_from_context(ctx).sources(
            collection_id=collection_id,
            file_status=file_status,
            limit=limit,
        ),
        output,
    )


@reader_cli.command("metadata")
@click.option("--collection", "collection_id", default=None, help="Optional collection filter.")
@click.option("--subject-kind", default=None, help="Optional subject kind filter.")
@click.option("--subject-id", default=None, help="Optional subject id filter.")
@click.option("--limit", default=500, show_default=True, type=click.IntRange(1, 5000))
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_metadata(  # noqa: PLR0913
    ctx: click.Context,
    collection_id: str | None,
    subject_kind: str | None,
    subject_id: str | None,
    limit: int,
    output: str,
) -> None:
    """List source metadata imported from corpus support files."""
    _emit_reader_payload(
        _reader_service_from_context(ctx).metadata(
            collection_id=collection_id,
            subject_kind=subject_kind,
            subject_id=subject_id,
            limit=limit,
        ),
        output,
    )


@reader_cli.command("validate")
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def reader_validate(ctx: click.Context, output: str) -> None:
    """Validate reader catalog and per-book artifacts."""
    _emit_reader_payload(_reader_service_from_context(ctx).validate(), output)


main.add_command(reader_cli)


@main.command("bailly-xml-audit")
@click.argument(
    "xml_dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Optional TSV output path.",
)
def bailly_xml_audit(xml_dir: Path, output: Path | None) -> None:
    """Audit generated Bailly per-page Poppler XML files."""
    from langnet.parsing.bailly_pdf_xml import audit_bailly_xml_pages  # noqa: PLC0415

    report = audit_bailly_xml_pages(xml_dir)
    rows = [
        [
            "page",
            "path",
            "section",
            "text_node_count",
            "entry_count",
            "first_lemma",
            "last_lemma",
            "warning",
        ],
        *[page.as_tsv_row() for page in report.pages],
    ]
    text = "\n".join("\t".join(row) for row in rows) + "\n"
    if output is not None:
        output.expanduser().parent.mkdir(parents=True, exist_ok=True)
        output.expanduser().write_text(text, encoding="utf-8")
        click.echo(f"wrote: {output.expanduser()}")
    else:
        click.echo(text, nl=False)
    if report.missing_pages:
        click.echo(f"missing_pages: {len(report.missing_pages)}", err=True)


@main.command("bailly-xml-extract")
@click.argument(
    "xml_dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Optional JSONL output path. Defaults to stdout.",
)
@click.option("--from-page", type=int, help="First physical PDF page to include.")
@click.option("--to-page", type=int, help="Last physical PDF page to include.")
@click.option("--limit", type=int, help="Maximum number of entries to write.")
def bailly_xml_extract(
    xml_dir: Path,
    output: Path | None,
    from_page: int | None,
    to_page: int | None,
    limit: int | None,
) -> None:
    """Extract Bailly Poppler XML pages to structural JSONL entries."""
    from langnet.parsing.bailly_pdf_xml import (  # noqa: PLC0415
        extract_book_entries_from_pages,
        iter_poppler_pages,
    )

    pages = []
    for path in sorted(xml_dir.expanduser().glob("bailly-2020-p*.xml")):
        page_number = _bailly_page_number_from_path(path)
        if from_page is not None and page_number < from_page:
            continue
        if to_page is not None and page_number > to_page:
            continue
        pages.extend(iter_poppler_pages(path))
    entries = extract_book_entries_from_pages(pages)
    if limit is not None:
        entries = entries[:limit]
    text = "".join(orjson.dumps(entry).decode("utf-8") + "\n" for entry in entries)
    if output is not None:
        output.expanduser().parent.mkdir(parents=True, exist_ok=True)
        output.expanduser().write_text(text, encoding="utf-8")
        click.echo(f"wrote: {output.expanduser()} entries={len(entries)}")
    else:
        click.echo(text, nl=False)


def _bailly_page_number_from_path(path: Path) -> int:
    try:
        return int(path.stem.rsplit("p", 1)[1])
    except (IndexError, ValueError):
        return 0


@main.command("bailly-db-lookup")
@click.argument("headword")
@click.option(
    "--db",
    "db_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Bailly DuckDB path. Defaults to data/build/lex_bailly.duckdb.",
)
@click.option("--limit", type=int, default=10, show_default=True, help="Maximum entries.")
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
def bailly_db_lookup(
    headword: str,
    db_path: Path | None,
    limit: int,
    output: str,
) -> None:
    """Inspect PDF-derived Bailly entries from the local DuckDB index."""
    from langnet.databuild.bailly import lookup_bailly_entries  # noqa: PLC0415

    entries = lookup_bailly_entries(headword, db_path, limit=limit)
    if output == "json":
        click.echo(orjson.dumps({"entries": entries}, option=orjson.OPT_INDENT_2).decode("utf-8"))
        return
    if not entries:
        click.echo(f"No Bailly entries found for {headword!r}.")
        return
    for entry in entries:
        page_start = entry.get("page_start") or "?"
        page_end = entry.get("page_end") or "?"
        click.echo(f"{entry['lemma']} [{entry['entry_id']}] pages {page_start}-{page_end}")
        for block in entry["blocks"]:
            click.echo(f"  {block['path']} {block['marker']} {block['text']}")


@main.command("lewis-1890-db-lookup")
@click.argument("headword")
@click.option(
    "--db",
    "db_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Lewis 1890 DuckDB path. Defaults to data/build/lex_lewis_1890.duckdb.",
)
@click.option("--limit", type=int, default=10, show_default=True, help="Maximum entries.")
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
def lewis_1890_db_lookup(
    headword: str,
    db_path: Path | None,
    limit: int,
    output: str,
) -> None:
    """Inspect Lewis 1890 entries from the local DuckDB index."""
    from langnet.databuild.lewis_1890 import lookup_lewis_1890_entries  # noqa: PLC0415

    entries = lookup_lewis_1890_entries(headword, db_path)[:limit]
    if output == "json":
        click.echo(orjson.dumps({"entries": entries}, option=orjson.OPT_INDENT_2).decode("utf-8"))
        return
    if not entries:
        click.echo(f"No Lewis 1890 entries found for {headword!r}.")
        return
    for entry in entries:
        click.echo(f"{entry['headword_raw']} [{entry['entry_id']}]")
        click.echo(f"  {entry['plain_text']}")


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


@click.group("word-index")
def word_index_cli() -> None:
    """Explore locally indexed dictionary headwords."""


@word_index_cli.command("sources")
@click.argument("language", default="all")
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
def word_index_sources(language: str, output: str) -> None:
    """List available word-index sources."""
    try:
        payload = word_index_sources_payload(language)
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc
    _emit_word_index_payload(payload, output=output)


@word_index_cli.command("sections")
@click.argument("language")
@click.option(
    "--source",
    default="all",
    show_default=True,
    help="Source filter: all, cdsl, dico, gaffiot, or diogenes.",
)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
def word_index_sections(language: str, source: str, output: str) -> None:
    """List native alphabet/section anchors for word-index browsing."""
    try:
        payload = word_index_sections_payload(language, source=source)
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc
    _emit_word_index_sections_payload(payload, output=output)


@word_index_cli.command("list")
@click.argument("language", default="all")
@click.option(
    "--source",
    default="all",
    show_default=True,
    help="Source filter: all, cdsl, dico, gaffiot, or diogenes.",
)
@click.option("--prefix", default="", help="Optional headword prefix filter.")
@click.option("--limit", default=50, show_default=True, type=click.IntRange(1, 500))
@click.option("--cursor", default=None, help="Opaque pagination cursor from prior response.")
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
def word_index_list(  # noqa: PLR0913
    language: str,
    source: str,
    prefix: str,
    limit: int,
    cursor: str | None,
    output: str,
) -> None:
    """List indexed headwords."""
    try:
        payload = word_index_list_payload(
            language,
            source=source,
            prefix=prefix,
            limit=limit,
            cursor=cursor,
        )
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc
    _emit_word_index_payload(payload, output=output)


@word_index_cli.command("browse")
@click.argument("language")
@click.option(
    "--source",
    default="all",
    show_default=True,
    help="Source filter: all, cdsl, dico, gaffiot, or diogenes.",
)
@click.option("--prefix", default="", help="Optional source-native browse prefix.")
@click.option("--limit", default=50, show_default=True, type=click.IntRange(1, 500))
@click.option(
    "--homographs",
    type=click.Choice(["grouped", "raw"]),
    default="grouped",
    show_default=True,
    help="Group adjacent homographs or preserve raw source rows.",
)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
def word_index_browse(  # noqa: PLR0913
    language: str,
    source: str,
    prefix: str,
    limit: int,
    homographs: str,
    output: str,
) -> None:
    """Browse indexed headwords in grouped source-native order."""
    try:
        payload = word_index_browse_payload(
            language,
            source=source,
            prefix=prefix,
            limit=limit,
            homographs=cast(WordIndexHomographs, homographs),
        )
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc
    _emit_word_index_payload(payload, output=output)


@word_index_cli.command("neighborhood")
@click.argument("language")
@click.argument("query")
@click.option(
    "--source",
    default="all",
    show_default=True,
    help="Source filter: all, cdsl, dico, gaffiot, or diogenes.",
)
@click.option("--radius", default=10, show_default=True, type=click.IntRange(1, 100))
@click.option(
    "--merge",
    type=click.Choice(["auto", "none", "lexeme"]),
    default="auto",
    show_default=True,
    help="Merge source-local groups into lexeme cards.",
)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
def word_index_neighborhood(  # noqa: PLR0913
    language: str, query: str, source: str, radius: int, merge: str, output: str
) -> None:
    """Show indexed words before and after a term."""
    _run_word_index_neighborhood(language, query, source, radius, merge, output)


def _run_word_index_neighborhood(  # noqa: PLR0913
    language: str, query: str, source: str, radius: int, merge: str, output: str
) -> None:
    try:
        payload = word_index_neighborhood_payload(
            language,
            query,
            source=source,
            radius=radius,
            merge=merge,
        )
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc
    _emit_word_index_payload(payload, output=output)


@word_index_cli.command("nearby")
@click.argument("language")
@click.argument("query")
@click.option(
    "--source",
    default="all",
    show_default=True,
    help="Source filter: all, cdsl, dico, gaffiot, or diogenes.",
)
@click.option("--radius", default=10, show_default=True, type=click.IntRange(1, 100))
@click.option(
    "--merge",
    type=click.Choice(["auto", "none", "lexeme"]),
    default="auto",
    show_default=True,
    help="Merge source-local groups into lexeme cards.",
)
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
def word_index_nearby(  # noqa: PLR0913
    language: str, query: str, source: str, radius: int, merge: str, output: str
) -> None:
    """Alias for neighborhood: find indexed words near a search query."""
    _run_word_index_neighborhood(language, query, source, radius, merge, output)


@word_index_cli.command("wheel")
@click.argument("language", default="all")
@click.option(
    "--language",
    "language_option",
    default=None,
    help="Language filter: all, lat, grc, or san. Overrides the positional language.",
)
@click.option(
    "--source",
    default="all",
    show_default=True,
    help="Source filter: all, cdsl, dico, gaffiot, or diogenes.",
)
@click.option("--count", default=12, show_default=True, type=click.IntRange(1, 100))
@click.option("--seed", default=None, help="Seed for deterministic word selection.")
@click.option(
    "--output",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    show_default=True,
    help="Output format.",
)
def word_index_wheel(  # noqa: PLR0913
    language: str,
    language_option: str | None,
    source: str,
    count: int,
    seed: str | None,
    output: str,
) -> None:
    """Return a deterministic wheel of indexed study words."""
    requested_language = language_option or language
    try:
        payload = word_index_wheel_payload(
            requested_language,
            source=source,
            count=count,
            seed=seed,
        )
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc
    _emit_word_index_payload(payload, output=output)


def _emit_word_index_payload(payload: Mapping[str, object], *, output: str) -> None:
    if output == "json":
        click.echo(orjson.dumps(dict(payload), option=orjson.OPT_INDENT_2).decode("utf-8"))
        return
    request = cast(Mapping[str, object], payload.get("request") or {})
    mode = request.get("mode")
    click.echo(f"Word index: {mode}")
    sources = payload.get("sources")
    if mode == "sources":
        _echo_word_index_sources(sources)
        return
    groups = payload.get("groups")
    items = payload.get("items")
    if mode == "browse":
        if _has_sequence_items(items):
            click.echo("Learner browse:")
            _echo_word_index_items(items, indent="  ")
            click.echo("Source groups:")
        _echo_word_index_browse_groups(groups)
    else:
        _echo_word_index_items(items)
    neighborhood = payload.get("neighborhood")
    if isinstance(neighborhood, Mapping):
        _echo_word_index_neighborhood(cast(Mapping[str, object], neighborhood))
    _echo_word_index_warnings(payload.get("warnings"))


def _echo_word_index_sources(sources: object) -> None:
    if not isinstance(sources, Sequence) or isinstance(sources, (str, bytes)):
        return
    for source in sources:
        if not isinstance(source, Mapping):
            continue
        source_map = cast(Mapping[str, object], source)
        status = "available" if source_map.get("available") else "missing"
        count = source_map.get("entry_count")
        click.echo(
            f"- {source_map.get('language')}:"
            f"{source_map.get('source')}:"
            f"{source_map.get('dictionary')} "
            f"{status} entries={count}"
        )


def _has_sequence_items(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and bool(value)


def _echo_word_index_items(items: object, *, indent: str = "") -> None:
    if not isinstance(items, Sequence) or isinstance(items, (str, bytes)):
        return
    for item in items:
        if isinstance(item, Mapping):
            click.echo(
                f"{indent}{_word_index_item_line_with_count(cast(Mapping[str, object], item))}"
            )


def _echo_word_index_warnings(warnings: object) -> None:
    if not isinstance(warnings, Sequence) or isinstance(warnings, (str, bytes)):
        return
    for warning in warnings:
        if isinstance(warning, Mapping):
            warning_map = cast(Mapping[str, object], warning)
            click.echo(f"Warning: {warning_map.get('message')}", err=True)


def _echo_word_index_browse_groups(groups: object) -> None:
    if not isinstance(groups, Sequence) or isinstance(groups, (str, bytes)):
        return
    for group in groups:
        if not isinstance(group, Mapping):
            continue
        group_map = cast(Mapping[str, object], group)
        click.echo(
            f"{group_map.get('language')}:{group_map.get('source')}:"
            f"{group_map.get('dictionary')} prefix={group_map.get('prefix')}"
        )
        group_items = group_map.get("items")
        if isinstance(group_items, Sequence) and not isinstance(group_items, (str, bytes)):
            for item in group_items:
                if not isinstance(item, Mapping):
                    continue
                item_map = cast(Mapping[str, object], item)
                click.echo(f"  {_word_index_item_line_with_count(item_map)}")


def _emit_word_index_sections_payload(payload: Mapping[str, object], *, output: str) -> None:
    if output == "json":
        click.echo(orjson.dumps(dict(payload), option=orjson.OPT_INDENT_2).decode("utf-8"))
        return
    order = payload.get("order")
    if isinstance(order, Mapping):
        order_map = cast(Mapping[str, object], order)
        click.echo(f"Word index sections: {order_map.get('label')}")
    sections = payload.get("sections")
    if isinstance(sections, Sequence) and not isinstance(sections, (str, bytes)):
        for section in sections:
            if not isinstance(section, Mapping):
                continue
            section_map = cast(Mapping[str, object], section)
            marker = "*" if section_map.get("available") else "-"
            click.echo(
                f"{marker} {section_map.get('label')} "
                f"({section_map.get('transliteration')}) "
                f"{section_map.get('group_label')}"
            )
    warnings = payload.get("warnings")
    if isinstance(warnings, Sequence) and not isinstance(warnings, (str, bytes)):
        for warning in warnings:
            if isinstance(warning, Mapping):
                warning_map = cast(Mapping[str, object], warning)
                click.echo(f"Warning: {warning_map.get('message')}", err=True)


def _word_index_item_line(item: Mapping[str, object]) -> str:
    display = item.get("display")
    display_map = (
        cast(Mapping[str, object], display)
        if isinstance(display, Mapping)
        else cast(Mapping[str, object], {})
    )
    romanized = (
        display_map.get("transliteration") or item.get("lookup") or item.get("canonical_name")
    )
    native = item.get("canonical_name")
    suffix = f" ({native})" if native and native != romanized else ""
    source_label = _word_index_source_label(item)
    return f"- {item.get('language')}:{source_label} {romanized}{suffix}"


def _word_index_item_line_with_count(item: Mapping[str, object]) -> str:
    line = _word_index_item_line(item)
    count = item.get("homograph_count")
    suffix = f" [{count} entries]" if isinstance(count, int) and count > 1 else ""
    return f"{line}{suffix}"


def _word_index_source_label(item: Mapping[str, object]) -> str:
    source_count = item.get("source_count")
    if not isinstance(source_count, int) or source_count <= 1:
        return str(item.get("source") or "")

    sources = item.get("sources")
    if not isinstance(sources, Sequence) or isinstance(sources, (str, bytes)):
        return str(item.get("source") or "all")
    labels = []
    for source in sources:
        if not isinstance(source, Mapping):
            continue
        source = cast(Mapping[str, object], source)
        source_id = str(source.get("source") or "")
        dictionary = str(source.get("dictionary") or "")
        if source_id and dictionary and source_id != dictionary:
            labels.append(f"{source_id}/{dictionary}")
        elif source_id:
            labels.append(source_id)
    return "+".join(labels) if labels else str(item.get("source") or "all")


def _echo_word_index_neighborhood(neighborhood: Mapping[str, object]) -> None:  # noqa: C901
    if neighborhood.get("policy") in {"merged_lexeme", "integrated_language_native"}:
        policy = neighborhood.get("policy")
        click.echo(
            f"Neighborhood: {neighborhood.get('language')}:{neighborhood.get('source')} {policy}"
        )
        items = neighborhood.get("items")
        if isinstance(items, Sequence) and not isinstance(items, (str, bytes)):
            for item in items:
                if not isinstance(item, Mapping):
                    continue
                item_map = cast(Mapping[str, object], item)
                position = item_map.get("position") or "nearby"
                click.echo(f"  {position}: {_word_index_item_line(item_map).removeprefix('- ')}")
        return
    groups = neighborhood.get("groups")
    if isinstance(groups, Sequence):
        for group in groups:
            if isinstance(group, Mapping):
                _echo_word_index_neighborhood(cast(Mapping[str, object], group))
        return
    anchor = neighborhood.get("anchor")
    click.echo(f"Neighborhood: {neighborhood.get('language')}:{neighborhood.get('source')}")
    if isinstance(anchor, Mapping):
        click.echo(
            f"  anchor "
            f"{_word_index_item_line(cast(Mapping[str, object], anchor)).removeprefix('- ')}"
        )
    for label in ("before", "after"):
        values = neighborhood.get(label)
        if isinstance(values, Sequence):
            rendered = [
                _word_index_item_line(cast(Mapping[str, object], item)).removeprefix("- ")
                for item in values
                if isinstance(item, Mapping)
            ]
            if rendered:
                click.echo(f"  {label}: " + "; ".join(rendered))


main.add_command(word_index_cli)


def _exclude_recent_terms(path: Path | None) -> list[str]:
    if path is None:
        return []
    raw = path.read_text(encoding="utf-8")
    with suppress(orjson.JSONDecodeError):
        parsed = orjson.loads(raw)
        return _word_of_day_terms_from_json(parsed)
    terms: list[str] = []
    for raw_line in raw.splitlines():
        for term in raw_line.split(","):
            cleaned = term.strip()
            if cleaned:
                terms.append(cleaned)
    return terms


def _word_of_day_terms_from_json(value: object) -> list[str]:
    terms: list[str] = []
    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []
    if isinstance(value, Mapping):
        value_map = cast(Mapping[str, object], value)
        for key in ("key", "query"):
            item = value_map.get(key)
            if isinstance(item, str) and item.strip():
                terms.append(item.strip())
        for item in value_map.values():
            terms.extend(_word_of_day_terms_from_json(item))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in value:
            terms.extend(_word_of_day_terms_from_json(item))
    return _dedupe_preserve_order(terms)


def _word_of_day_avoid_terms(avoid: str | None, exclude_recent: Path | None) -> list[str]:
    terms = _exclude_recent_terms(exclude_recent)
    if avoid:
        terms.extend(part.strip() for part in avoid.split(",") if part.strip())
    return _dedupe_preserve_order(terms)


def _word_of_day_probe_translation_mode(translation_mode: str) -> str:
    resolved = _resolve_translation_mode(False, translation_mode)
    if resolved in {"auto", "populate"}:
        return "cache"
    return resolved


def _word_of_day_system_prompt() -> str:
    return (
        "You propose classical-language dictionary lookup candidates for learners. "
        "Return only JSON. Use romanized single-token queries that a CLI dictionary can "
        "verify for Sanskrit, Ancient Greek, and Latin. Avoid proper names unless clearly "
        "pedagogical. Write in a sober scholarly-humanist register: concise, learned, "
        "philological, and suitable for a classical reader. Let Erasmus, Ramon Llull, "
        "Albertus Magnus, and Giordano Bruno serve only as a tonal compass toward learned "
        "seriousness and disciplined curiosity, without archaic imitation or florid "
        "pastiche. Mild eccentricity is welcome only when it grows from real philology, "
        "semantic range, morphology, reception, or textual context. Avoid random novelty, "
        "casual sound-alike associations, and any etymological claim that is not "
        "historically defensible."
    )


def _word_of_day_user_prompt(prompt: Mapping[str, object]) -> str:
    return (
        "Return JSON shaped as "
        '{"items":[{"language":"lat|grc|san","query":"...",'
        '"summary":"3-10 word English learner gloss",'
        '"difficulty":"beginner|intermediate|deep","mnemonic":"..."}]}. '
        "The mnemonic must be a brief scholarly memory note grounded in morphology, "
        "semantic range, etymology, or textual context. If no such note is safe, keep it "
        "plain and descriptive. "
        f"Request: {orjson.dumps(dict(prompt)).decode('utf-8')}"
    )


def _word_of_day_remaining_timeout(
    started: float,
    timeout_ms: int,
) -> float | None:
    if timeout_ms <= 0:
        return None
    remaining = timeout_ms / 1000 - (time.monotonic() - started)
    if remaining <= 0:
        raise click.ClickException("word-of-day generation timed out before LLM request")
    return max(1.0, remaining)


def _word_of_day_llm_error_message(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"


def _word_of_day_llm_call(
    call_name: str,
    kwargs: Mapping[str, object],
    timeout_seconds: float | None,
) -> Any:
    if timeout_seconds is None:
        return _word_of_day_dispatch_llm_call(call_name, dict(kwargs))
    ctx = multiprocessing.get_context("fork")
    result_queue = ctx.Queue(maxsize=1)
    process = ctx.Process(
        target=_word_of_day_llm_process_worker,
        args=(call_name, dict(kwargs), result_queue),
    )
    process.start()
    process.join(timeout_seconds)
    if process.is_alive():
        process.terminate()
        process.join(2)
        if process.is_alive():
            process.kill()
            process.join(2)
        raise TimeoutError(f"LLM word recommendation timed out after {timeout_seconds:.1f}s")
    try:
        status, payload = result_queue.get_nowait()
    except queue_module.Empty as exc:
        exitcode = process.exitcode
        raise click.ClickException(
            f"LLM word recommendation exited without a response (exit code {exitcode})."
        ) from exc
    if status == "ok":
        return payload
    raise click.ClickException(str(payload))


def _word_of_day_llm_process_worker(
    call_name: str,
    kwargs: dict[str, object],
    result_queue,
) -> None:
    try:
        result_queue.put(("ok", _word_of_day_dispatch_llm_call(call_name, kwargs)))
    except Exception as exc:  # noqa: BLE001
        result_queue.put(("error", _word_of_day_llm_error_message(exc)))


def _word_of_day_dispatch_llm_call(call_name: str, kwargs: dict[str, object]) -> Any:
    if call_name == "synthesize":
        return _word_of_day_synthesize_candidates_direct(
            languages=cast(Sequence[str], kwargs["languages"]),
            count=cast(int, kwargs["count"]),
            level=cast(str, kwargs["level"]),
            avoid_terms=cast(Sequence[str], kwargs["avoid_terms"]),
            nonce=cast(str | None, kwargs["nonce"]),
            rotation_key=cast(str | None, kwargs["rotation_key"]),
            model=cast(str, kwargs["model"]),
            timeout_seconds=cast(float | None, kwargs["timeout_seconds"]),
        )
    if call_name == "finalize":
        return _word_of_day_finalize_payload_with_llm_direct(
            payload=cast(dict[str, object], kwargs["payload"]),
            model=cast(str, kwargs["model"]),
            timeout_seconds=cast(float | None, kwargs["timeout_seconds"]),
        )
    raise ValueError(f"Unknown word-of-day LLM call: {call_name}")


def _word_of_day_synthesize_candidates(  # noqa: PLR0913
    *,
    languages: Sequence[str],
    count: int,
    level: str,
    avoid_terms: Sequence[str],
    nonce: str | None,
    rotation_key: str | None,
    model: str,
    timeout_seconds: float | None,
) -> dict[str, list[WordCandidate]]:
    return cast(
        dict[str, list[WordCandidate]],
        _word_of_day_llm_call(
            "synthesize",
            {
                "languages": languages,
                "count": count,
                "level": level,
                "avoid_terms": avoid_terms,
                "nonce": nonce,
                "rotation_key": rotation_key,
                "model": model,
                "timeout_seconds": timeout_seconds,
            },
            timeout_seconds,
        ),
    )


def _word_of_day_synthesize_candidates_direct(  # noqa: PLR0913
    *,
    languages: Sequence[str],
    count: int,
    level: str,
    avoid_terms: Sequence[str],
    nonce: str | None,
    rotation_key: str | None,
    model: str,
    timeout_seconds: float | None,
) -> dict[str, list[WordCandidate]]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise click.ClickException("Set OPENAI_API_KEY before using LLM word recommendations.")
    api_base = os.getenv(
        "OPENAI_API_BASE",
        os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1"),
    )
    os.environ["OPENAI_BASE_URL"] = api_base
    try:
        import aisuite as ai  # noqa: PLC0415
    except ImportError as exc:
        raise click.ClickException("aisuite is required for LLM word recommendations.") from exc

    client = ai.Client({"api_key": api_key})
    per_language = max(count * 4, count + 4)
    prompt = {
        "languages": list(languages),
        "per_language": per_language,
        "level": level,
        "avoid": list(avoid_terms),
        "nonce": nonce or "",
        "rotation_key": rotation_key or "",
    }
    request_kwargs: dict[str, object] = {}
    if timeout_seconds is not None:
        request_kwargs["timeout"] = timeout_seconds
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _word_of_day_system_prompt()},
            {"role": "user", "content": _word_of_day_user_prompt(prompt)},
        ],
        **request_kwargs,
    )
    content = response.choices[0].message.content or ""
    return _word_of_day_parse_synthesized_candidates(content, languages=languages)


def _word_of_day_finalize_payload_with_llm(
    payload: dict[str, object],
    *,
    model: str,
    timeout_seconds: float | None,
) -> dict[str, object]:
    return cast(
        dict[str, object],
        _word_of_day_llm_call(
            "finalize",
            {
                "payload": payload,
                "model": model,
                "timeout_seconds": timeout_seconds,
            },
            timeout_seconds,
        ),
    )


def _word_of_day_finalize_payload_with_llm_direct(
    payload: dict[str, object],
    *,
    model: str,
    timeout_seconds: float | None,
) -> dict[str, object]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise click.ClickException("Set OPENAI_API_KEY before using LLM word recommendations.")
    api_base = os.getenv(
        "OPENAI_API_BASE",
        os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1"),
    )
    os.environ["OPENAI_BASE_URL"] = api_base
    try:
        import aisuite as ai  # noqa: PLC0415
    except ImportError as exc:
        raise click.ClickException("aisuite is required for LLM word recommendations.") from exc

    client = ai.Client({"api_key": api_key})
    finalization_input = _word_of_day_finalization_input(payload)
    request_kwargs: dict[str, object] = {}
    if timeout_seconds is not None:
        request_kwargs["timeout"] = timeout_seconds
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _word_of_day_finalizer_system_prompt()},
            {
                "role": "user",
                "content": _word_of_day_finalizer_user_prompt(finalization_input),
            },
        ],
        **request_kwargs,
    )
    content = response.choices[0].message.content or ""
    updates = _word_of_day_parse_finalized_cards(content)
    _word_of_day_apply_finalized_cards(payload, updates)
    return payload


def _word_of_day_finalizer_system_prompt() -> str:
    return (
        "You write final learner cards from verified dictionary evidence. Return only JSON. "
        "Do not propose new words. Use only the supplied source_basis evidence and metadata. "
        "The summary field is a terse English gloss in 1-5 words, preferably a compact "
        "gloss cluster. "
        "Write learner_note as one concise sentence explaining why this is a good word for "
        "learners: morphology, semantic range, commonness, ambiguity, cultural value, or "
        "textual importance. The learner_note must not be a longer definition. "
        "Use a sober scholarly-humanist "
        "register with disciplined curiosity: memorable, philological, and historically "
        "grounded. Mild eccentricity is acceptable only when it grows from the evidence. "
        "Avoid random novelty, casual sound-alike associations, and unsupported etymology. "
        "If the evidence is thin, keep the card plain and conservative."
    )


def _word_of_day_finalizer_user_prompt(finalization_input: Mapping[str, object]) -> str:
    return (
        "Return JSON shaped as "
        '{"items":[{"key":"language:query","summary":"...",'
        '"learner_note":"...","mnemonic":"..."}]}. '
        "Use summary for the short gloss. Use learner_note for why the word is worth "
        "learning. "
        "Verified source-backed items: "
        f"{orjson.dumps(dict(finalization_input)).decode('utf-8')}"
    )


def _word_of_day_finalization_input(payload: Mapping[str, object]) -> dict[str, object]:
    items = payload.get("items")
    compact_items: list[dict[str, object]] = []
    if isinstance(items, Sequence) and not isinstance(items, (str, bytes)):
        for raw_item in items:
            if not isinstance(raw_item, Mapping):
                continue
            item = cast(Mapping[str, object], raw_item)
            compact_items.append(
                {
                    "key": item.get("key"),
                    "language": item.get("language"),
                    "query": item.get("query"),
                    "display": item.get("display"),
                    "canonical_name": item.get("canonical_name"),
                    "canonical": item.get("canonical"),
                    "primary_lexeme": item.get("primary_lexeme"),
                    "lexeme_anchors": item.get("lexeme_anchors"),
                    "current_summary": item.get("summary"),
                    "source_basis": item.get("source_basis"),
                    "ambiguity": item.get("ambiguity"),
                }
            )
    return {"items": compact_items}


def _word_of_day_parse_finalized_cards(content: str) -> dict[str, dict[str, str]]:
    payload_text = content.strip()
    if payload_text.startswith("```"):
        payload_text = re.sub(r"^```(?:json)?\s*", "", payload_text)
        payload_text = re.sub(r"\s*```$", "", payload_text)
    try:
        payload = orjson.loads(payload_text)
    except orjson.JSONDecodeError as exc:
        raise click.ClickException(f"LLM word card response was not valid JSON: {exc}")
    items = payload.get("items") if isinstance(payload, Mapping) else None
    if not isinstance(items, Sequence) or isinstance(items, (str, bytes)):
        raise click.ClickException("LLM word card response did not contain items[].")
    updates: dict[str, dict[str, str]] = {}
    for raw_item in items:
        if not isinstance(raw_item, Mapping):
            continue
        item = cast(Mapping[str, object], raw_item)
        key = str(item.get("key") or "").strip().lower()
        if not key:
            continue
        summary = str(item.get("summary") or "").strip()
        learner_note = str(item.get("learner_note") or "").strip()
        mnemonic = str(item.get("mnemonic") or "").strip()
        if _word_of_day_has_unsuitable_learner_text(summary, learner_note, mnemonic):
            continue
        updates[key] = {
            "summary": summary,
            "learner_note": learner_note,
            "mnemonic": mnemonic,
        }
    return updates


def _word_of_day_apply_finalized_cards(
    payload: dict[str, object],
    updates: Mapping[str, Mapping[str, str]],
) -> None:
    items = payload.get("items")
    if not isinstance(items, list):
        return
    for raw_item in items:
        if not isinstance(raw_item, dict):
            continue
        item = cast(dict[str, object], raw_item)
        key = str(item.get("key") or "").strip().lower()
        update = updates.get(key)
        if not update:
            continue
        summary = update.get("summary", "").strip()
        if summary:
            item["summary"] = _word_of_day_terse_summary(summary)
            ui = item.get("ui")
            if isinstance(ui, dict):
                cast(dict[str, object], ui)["short_gloss"] = _word_of_day_short_gloss(
                    str(item["summary"])
                )
        learner_note = update.get("learner_note", "").strip()
        if learner_note:
            item["learner_note"] = learner_note
        mnemonic = update.get("mnemonic", "").strip()
        if mnemonic:
            item["mnemonic"] = mnemonic


def _word_of_day_short_gloss(summary: str) -> str:
    return summary.split(";", 1)[0].split(",", 1)[0].strip()


def _word_of_day_terse_summary(summary: str) -> str:
    return shorten_text(summary.strip(), 48)


def _word_of_day_parse_synthesized_candidates(
    content: str,
    *,
    languages: Sequence[str],
) -> dict[str, list[WordCandidate]]:
    payload_text = content.strip()
    if payload_text.startswith("```"):
        payload_text = re.sub(r"^```(?:json)?\s*", "", payload_text)
        payload_text = re.sub(r"\s*```$", "", payload_text)
    try:
        payload = orjson.loads(payload_text)
    except orjson.JSONDecodeError as exc:
        raise click.ClickException(f"LLM word recommendation response was not valid JSON: {exc}")
    items = payload.get("items") if isinstance(payload, Mapping) else None
    if not isinstance(items, Sequence) or isinstance(items, (str, bytes)):
        raise click.ClickException("LLM word recommendation response did not contain items[].")
    allowed_languages = set(languages)
    pools: dict[str, list[WordCandidate]] = {language: [] for language in languages}
    seen: set[str] = set()
    for raw_item in items:
        if not isinstance(raw_item, Mapping):
            continue
        item = cast(Mapping[str, object], raw_item)
        language = str(item.get("language") or "").strip().lower()
        query = str(item.get("query") or "").strip()
        if language not in allowed_languages or not query:
            continue
        key = f"{language}:{query.lower()}"
        if key in seen or not re.fullmatch(r"[\w\-āīūṛṝḷṅñṭḍṇśṣṃḥôōêē]+", query, re.I):
            continue
        seen.add(key)
        difficulty = str(item.get("difficulty") or "beginner").strip().lower()
        if difficulty not in {"beginner", "intermediate", "deep"}:
            difficulty = "beginner"
        mnemonic = str(item.get("mnemonic") or "").strip()
        summary = str(item.get("summary") or "").strip()
        if _word_of_day_has_unsuitable_learner_text(summary, mnemonic):
            continue
        pools[language].append(WordCandidate(language, query, difficulty, mnemonic, summary))
    return {language: candidates for language, candidates in pools.items() if candidates}


_UNSUITABLE_LEARNER_TEXT_PATTERNS = (
    r"\bsuperhero\b",
    r"\bcomic[- ]?book\b",
    r"\bmeme\b",
    r"\bmascot\b",
    r"\bcartoon\b",
    r"\bvideo game\b",
    r"\bpokemon\b",
    r"\bharry potter\b",
    r"\bstar wars\b",
    r"\bpun\b",
    r"\bjoke\b",
    r"\bsounds like\b",
    r"\brhymes with\b",
    r"\bpop[- ]?culture\b",
    r"\binternet[- ]?culture\b",
    r"\bbrand\b",
)


def _word_of_day_has_unsuitable_learner_text(*values: str) -> bool:
    text = " ".join(value for value in values if value).lower()
    return any(re.search(pattern, text) for pattern in _UNSUITABLE_LEARNER_TEXT_PATTERNS)


def _word_of_day_candidate_pools(  # noqa: PLR0913
    *,
    languages: Sequence[str],
    count: int,
    level: str,
    avoid_terms: Sequence[str],
    nonce: str | None,
    rotation_key: str | None,
    candidate_source: str,
    recommendation_model: str,
    started: float,
    timeout_ms: int,
    warnings: list[dict[str, str]],
) -> dict[str, list[WordCandidate]] | None:
    if candidate_source == "curated":
        return None
    try:
        candidate_pools = _word_of_day_synthesize_candidates(
            languages=languages,
            count=count,
            level=level,
            avoid_terms=avoid_terms,
            nonce=nonce,
            rotation_key=rotation_key,
            model=recommendation_model,
            timeout_seconds=_word_of_day_remaining_timeout(started, timeout_ms),
        )
        missing_languages = [
            language for language in languages if not candidate_pools.get(language)
        ]
        if missing_languages:
            message = (
                "LLM candidate synthesis returned no candidates for "
                f"{', '.join(missing_languages)}."
            )
            if candidate_source == "llm":
                raise click.ClickException(message)
            warnings.append(
                {
                    "language": "",
                    "query": "",
                    "message": f"{message} Fell back to curated pools.",
                }
            )
            return None
        return candidate_pools
    except Exception as exc:
        if candidate_source == "llm":
            if isinstance(exc, click.ClickException):
                raise
            raise click.ClickException(_word_of_day_llm_error_message(exc)) from exc
        warnings.append(
            {
                "language": "",
                "query": "",
                "message": (
                    "LLM candidate synthesis unavailable; fell back to curated pools. "
                    f"{_word_of_day_llm_error_message(exc)}"
                ),
            }
        )
        return None


def _word_of_day_probe_reduction(  # noqa: PLR0913
    *,
    language: str,
    text: str,
    dictionary: str,
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
):
    result = _execute_lookup_plan(
        language=language,
        text=text,
        tool_filter=dictionary,
        normalize=normalize,
        diogenes_endpoint=diogenes_endpoint,
        diogenes_parse_endpoint=diogenes_parse_endpoint,
        heritage_base=heritage_base,
        db_path=db_path,
        # Recommendation probes must not contend for the shared DuckDB writer lock.
        no_cache=True,
        include_cltk=include_cltk,
    )
    claims = _claims_as_mappings(result)
    resolved_translation_mode = _resolve_translation_mode(False, translation_mode)
    populate_translations = resolved_translation_mode in {"populate", "auto"}
    cache_path = Path(translation_cache_db)
    if resolved_translation_mode != "off" and (cache_path.exists() or populate_translations):
        if populate_translations:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
        diagnostics = _encounter_translation_diagnostics(
            mode=resolved_translation_mode,
            cache_path=cache_path,
            model=translation_model,
            populate=populate_translations,
        )
        diagnostics["cache_available"] = True
        translation_cache = _PathTranslationCache(
            cache_path,
            read_only=not populate_translations,
        )
        claims = _encounter_apply_translation_cache(
            claims=claims,
            language=language,
            model=translation_model,
            cache=translation_cache,  # type: ignore[arg-type]
            populate=populate_translations,
            translate=_encounter_translation_callback(translation_model),
            diagnostics=diagnostics,
            context="word-of-day",
        )
    reduction = reduce_claims(query=text, language=language, claims=claims)
    morphology_rows = _encounter_morphology_rows(
        claims,
        language=language,
        original=text,
        reduction=reduction,
    )
    preferred_lemmas = _encounter_preferred_lemmas_for_sorting(
        reduction,
        morphology_rows,
        [],
        [text],
    )
    reduction.buckets = sorted(
        reduction.buckets,
        key=lambda bucket: _encounter_bucket_sort_key(bucket, preferred_lemmas),
    )
    return reduction


def _emit_word_recommendations(  # noqa: PLR0913
    *,
    language: str,
    count: int,
    seed: str | None,
    level: str,
    dictionary: str,
    reader_lang: str,
    translation_mode: str,
    max_source_chars: int,
    avoid: str | None,
    exclude_recent: Path | None,
    fresh: bool,
    nonce: str | None,
    rotation_key: str | None,
    candidate_source: str,
    recommendation_model: str,
    include_ambiguous: bool,
    require_clean_primary: bool,
    timeout_ms: int,
    normalize: bool,
    diogenes_endpoint: str,
    diogenes_parse_endpoint: str | None,
    heritage_base: str,
    db_path: str | None,
    no_cache: bool,
    include_cltk: bool,
    translation_cache_db: str,
    translation_model: str,
    output: str,
) -> None:
    started = time.monotonic()
    try:
        languages = resolve_word_of_day_languages(language)
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc
    avoid_terms = _word_of_day_avoid_terms(avoid, exclude_recent)
    synthesis_warnings: list[dict[str, str]] = []
    probe_translation_mode = _word_of_day_probe_translation_mode(translation_mode)
    if probe_translation_mode != _resolve_translation_mode(False, translation_mode):
        synthesis_warnings.append(
            {
                "language": "",
                "query": "",
                "message": (
                    "word-of-day uses cached translations during recommendation probing; "
                    "skipped translation population for bounded response time."
                ),
            }
        )
    candidate_pools = _word_of_day_candidate_pools(
        languages=languages,
        count=count,
        level=level,
        avoid_terms=avoid_terms,
        nonce=nonce,
        rotation_key=rotation_key,
        candidate_source=candidate_source,
        recommendation_model=recommendation_model,
        started=started,
        timeout_ms=timeout_ms,
        warnings=synthesis_warnings,
    )
    options = WordOfDayOptions(
        count=count,
        level=level,
        dictionary=dictionary,
        reader_lang=reader_lang,
        translation_mode=translation_mode,
        max_source_chars=max_source_chars,
        include_ambiguous=include_ambiguous,
        require_clean_primary=require_clean_primary,
        timeout_ms=timeout_ms,
        seed=seed,
        fresh=fresh,
        avoid=tuple(avoid_terms),
        nonce=nonce,
        rotation_key=rotation_key,
        candidate_source=candidate_source if candidate_pools is not None else "curated",
    )

    def probe(probe_language: str, query: str):
        return _word_of_day_probe_reduction(
            language=probe_language,
            text=query,
            dictionary=dictionary,
            normalize=normalize,
            diogenes_endpoint=diogenes_endpoint,
            diogenes_parse_endpoint=diogenes_parse_endpoint,
            heritage_base=heritage_base,
            db_path=db_path,
            no_cache=no_cache,
            include_cltk=include_cltk,
            translation_mode=probe_translation_mode,
            translation_cache_db=translation_cache_db,
            translation_model=translation_model,
        )

    payload = generate_word_of_day_payload(
        languages=languages,
        options=options,
        probe_encounter=probe,
        bucket_gloss=_encounter_bucket_gloss,
        bucket_learner_gloss=lambda bucket: _encounter_bucket_learner_gloss(
            bucket,
            max_chars=80,
        ),
        exclude_terms=[],
        candidate_pools=candidate_pools,
    )
    if synthesis_warnings:
        payload["warnings"] = [*synthesis_warnings, *payload["warnings"]]
    if candidate_pools is not None and payload.get("items"):
        try:
            payload = _word_of_day_finalize_payload_with_llm(
                payload,
                model=recommendation_model,
                timeout_seconds=_word_of_day_remaining_timeout(started, timeout_ms),
            )
        except Exception as exc:
            if candidate_source == "llm":
                if isinstance(exc, click.ClickException):
                    raise
                raise click.ClickException(_word_of_day_llm_error_message(exc)) from exc
            payload["warnings"] = [
                {
                    "language": "",
                    "query": "",
                    "message": (
                        "LLM card finalization unavailable; returned source-derived cards. "
                        f"{_word_of_day_llm_error_message(exc)}"
                    ),
                },
                *cast(list[dict[str, str]], payload["warnings"]),
            ]
    if output == "json":
        click.echo(orjson.dumps(payload, option=orjson.OPT_INDENT_2).decode("utf-8"))
        return
    _print_word_recommendations(payload)


def _print_word_recommendations(payload: Mapping[str, object]) -> None:
    items = payload.get("items")
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, Mapping):
                continue
            item_map = cast(Mapping[str, object], item)
            badge: object = item_map.get("language")
            ui = item_map.get("ui")
            ui_map: Mapping[str, object] | None = None
            if isinstance(ui, Mapping):
                ui_map = cast(Mapping[str, object], ui)
                badge = ui_map.get("badge") or badge
            display = item_map.get("canonical_name") or item_map.get("display")
            click.echo(f"{badge}: {display} - {item_map.get('summary')}")
            click.echo(f"  Query: {item_map.get('query')}")
            click.echo(f"  Note: {item_map.get('learner_note')}")
            if ui_map is not None and ui_map.get("href_query"):
                click.echo(f"  Link params: {ui_map['href_query']}")
            click.echo()
    warnings = payload.get("warnings")
    if isinstance(warnings, list) and warnings:
        click.echo("Warnings:")
        for warning in warnings:
            if not isinstance(warning, Mapping):
                continue
            warning_map = cast(Mapping[str, object], warning)
            message = warning_map.get("message")
            language = warning_map.get("language")
            query = warning_map.get("query")
            prefix = ":".join(str(part) for part in (language, query) if part)
            click.echo(f"- {prefix}: {message}" if prefix else f"- {message}")


@main.command("word-of-day")
@click.argument("language", default="all")
@click.option("--count", default=1, show_default=True, type=click.IntRange(1, 10))
@click.option("--seed", help="Optional deterministic seed for reproducible recommendations.")
@click.option(
    "--level",
    type=click.Choice(["beginner", "intermediate", "deep"]),
    default="beginner",
    show_default=True,
)
@click.option("--dictionary", default="all", show_default=True)
@click.option("--reader-lang", default="en", show_default=True)
@click.option(
    "--translation-mode",
    type=click.Choice(["off", "cache", "populate", "auto", "do-it-all"]),
    default="cache",
    show_default=True,
)
@click.option("--max-source-chars", default=140, show_default=True, type=click.IntRange(20, 1000))
@click.option("--avoid", help="Comma-separated language:query keys or raw query terms to avoid.")
@click.option(
    "--exclude-recent",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to a newline- or CSV-style list of recently shown query terms.",
)
@click.option("--fresh", is_flag=True, help="Prefer suggestions outside --avoid/--exclude-recent.")
@click.option("--nonce", help="Caller-provided entropy for refresh actions.")
@click.option("--rotation-key", help="Stable caller/session key for repeatable rotations.")
@click.option(
    "--candidate-source",
    type=click.Choice(["auto", "llm", "curated"]),
    default="auto",
    show_default=True,
    help="Use OpenRouter synthesis when available, require it, or use curated pools only.",
)
@click.option(
    "--recommendation-model",
    default=DEFAULT_RECOMMENDATION_MODEL,
    show_default=True,
    help="Model id used for LLM candidate synthesis.",
)
@click.option("--include-ambiguous", is_flag=True, help="Allow multiple-lexeme candidates.")
@click.option(
    "--require-clean-primary/--allow-fallback-ambiguous",
    default=False,
    show_default=True,
    help="Require one clear primary lexeme instead of falling back to marked ambiguity.",
)
@click.option("--timeout-ms", default=45000, show_default=True, type=click.IntRange(0, 120000))
@click.option("--normalize/--no-normalize", default=True, show_default=True)
@click.option(
    "--diogenes-endpoint",
    default="http://localhost:8888/Diogenes.cgi",
    show_default=True,
)
@click.option("--diogenes-parse-endpoint")
@click.option("--heritage-base", default="http://localhost:48080", show_default=True)
@click.option("--db-path", type=click.Path())
@click.option("--no-cache", is_flag=True)
@click.option("--include-cltk/--no-include-cltk", default=False, show_default=True)
@click.option(
    "--translation-cache-db",
    default="data/cache/langnet.duckdb",
    show_default=True,
)
@click.option(
    "--translation-model",
    default=DEFAULT_TRANSLATION_MODEL,
    show_default=True,
)
@click.option(
    "--output",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
)
def word_of_day(  # noqa: PLR0913
    language: str,
    count: int,
    seed: str | None,
    level: str,
    dictionary: str,
    reader_lang: str,
    translation_mode: str,
    max_source_chars: int,
    avoid: str | None,
    exclude_recent: Path | None,
    fresh: bool,
    nonce: str | None,
    rotation_key: str | None,
    candidate_source: str,
    recommendation_model: str,
    include_ambiguous: bool,
    require_clean_primary: bool,
    timeout_ms: int,
    normalize: bool,
    diogenes_endpoint: str,
    diogenes_parse_endpoint: str | None,
    heritage_base: str,
    db_path: str | None,
    no_cache: bool,
    include_cltk: bool,
    translation_cache_db: str,
    translation_model: str,
    output: str,
) -> None:
    """Recommend source-verified learner words to look up in detail."""
    _emit_word_recommendations(
        language=language,
        count=count,
        seed=seed,
        level=level,
        dictionary=dictionary,
        reader_lang=reader_lang,
        translation_mode=translation_mode,
        max_source_chars=max_source_chars,
        avoid=avoid,
        exclude_recent=exclude_recent,
        fresh=fresh,
        nonce=nonce,
        rotation_key=rotation_key,
        candidate_source=candidate_source,
        recommendation_model=recommendation_model,
        include_ambiguous=include_ambiguous,
        require_clean_primary=require_clean_primary,
        timeout_ms=timeout_ms,
        normalize=normalize,
        diogenes_endpoint=diogenes_endpoint,
        diogenes_parse_endpoint=diogenes_parse_endpoint,
        heritage_base=heritage_base,
        db_path=db_path,
        no_cache=no_cache,
        include_cltk=include_cltk,
        translation_cache_db=translation_cache_db,
        translation_model=translation_model,
        output=output,
    )


main.add_command(word_of_day, "recommend-words")


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
        Path("docs/schemas/word_of_day.v1.schema.json"),
        Path("docs/schemas/word_index.v1.schema.json"),
        Path("docs/schemas/word_index_sections.v1.schema.json"),
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


def _create_bailly_client(tool: str, use_stubs: bool) -> ToolClient | None:
    """Create a local Bailly client, with stub fallback."""
    try:
        from langnet.execution.handlers.bailly import BaillyFetchClient  # noqa: PLC0415

        return BaillyFetchClient()
    except Exception:
        if use_stubs:
            return StubToolClient(tool)
    return None


def _create_lewis_1890_client(tool: str, use_stubs: bool) -> ToolClient | None:
    """Create a local Lewis 1890 client, with stub fallback."""
    try:
        from langnet.execution.handlers.lewis_1890 import Lewis1890FetchClient  # noqa: PLC0415

        return Lewis1890FetchClient()
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
        "fetch.bailly": lambda: _create_bailly_client(tool, use_stubs),
        "fetch.lewis_1890": lambda: _create_lewis_1890_client(tool, use_stubs),
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

    registry = _default_registry(use_stubs=config.use_stub_handlers)
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
    stripped = text.strip()
    if normalize_greek_compatibility(stripped) != stripped:
        return True
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
        registry = _default_registry(use_stubs=False)
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


_PARADIGM_ANALYSIS_FEATURES = {
    "case",
    "number",
    "gender",
    "person",
    "tense",
    "mood",
    "voice",
    "degree",
}


_PARADIGM_DIRECT_FEATURE_KEYS = {
    "gender",
    "declension",
    "genitive_singular",
    "genitive",
    "gen_sg",
    "article",
    "source_key",
    "diogenes_key",
    "betacode",
    "present_class",
    "class",
    "conjugation",
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


def _encounter_paradigm_resolution_payload(
    language: str,
    text: str,
    claims: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    language_code = canonical_language(language)
    if language_code not in {"lat", "grc", "san"}:
        return _empty_encounter_paradigm_resolution(
            language=language,
            text=text,
            warning=f"unsupported_language: {language}",
        )
    try:
        records = _encounter_paradigm_records(cast(Any, language_code), text, claims)
        payload = resolve_paradigm_request(cast(Any, language_code), text, records)
        return asdict(payload)
    except Exception as exc:  # noqa: BLE001
        return _empty_encounter_paradigm_resolution(
            language=language_code,
            text=text,
            warning=f"resolver_failed: {type(exc).__name__}",
        )


def _encounter_add_learning_overlays(
    paradigm_resolution: Mapping[str, object],
) -> dict[str, object]:
    payload = dict(paradigm_resolution)
    candidates = paradigm_resolution.get("candidates")
    if not isinstance(candidates, Sequence) or isinstance(candidates, (str, bytes)):
        return payload

    overlayed_candidates: list[object] = []
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            overlayed_candidates.append(candidate)
            continue
        candidate_map = cast(Mapping[str, object], candidate)
        candidate_payload = dict(candidate_map)
        candidate_payload["learning_overlay"] = _encounter_learning_candidate_overlay(candidate_map)
        overlayed_candidates.append(candidate_payload)
    payload["candidates"] = overlayed_candidates
    return payload


def _encounter_learning_candidate_overlay(candidate: Mapping[str, object]) -> dict[str, object]:
    raw_concept_ids = candidate.get("concept_ids")
    concept_ids = (
        [concept_id for concept_id in raw_concept_ids if isinstance(concept_id, str)]
        if isinstance(raw_concept_ids, Sequence) and not isinstance(raw_concept_ids, (str, bytes))
        else []
    )
    concepts: list[dict[str, object]] = []
    missing_evidence: list[str] = []
    for concept_id in concept_ids:
        try:
            concept = get_grammar_concept(concept_id)
        except KeyError:
            missing_evidence.append(f"unknown_concept:{concept_id}")
            continue
        concepts.append(_grammar_concept_learning_payload(concept))
    if concepts:
        if not any(concept.get("source_evidence") for concept in concepts):
            missing_evidence.append("source_work_links")
        if not _learning_concepts_all_have_reader_segments(concepts):
            missing_evidence.append("reader_segment_links")
    if not concept_ids:
        missing_evidence.append(_encounter_learning_missing_reason(candidate))
    return {
        "schema_version": LEARNING_OVERLAY_SCHEMA_VERSION,
        "status": "mapped" if concepts else "unmapped",
        "concept_ids": concept_ids,
        "concepts": concepts,
        "missing_evidence": missing_evidence,
    }


def _learning_concepts_all_have_reader_segments(concepts: Sequence[Mapping[str, object]]) -> bool:
    for concept in concepts:
        raw_evidence = concept.get("source_evidence")
        if not isinstance(raw_evidence, Sequence) or isinstance(raw_evidence, (str, bytes)):
            return False
        has_reader_segment = False
        for evidence in raw_evidence:
            if not isinstance(evidence, Mapping):
                continue
            evidence_map = cast(Mapping[str, object], evidence)
            if evidence_map.get("evidence_level") == "reader_segment":
                has_reader_segment = True
                break
        if not has_reader_segment:
            return False
    return bool(concepts)


def _encounter_learning_missing_reason(candidate: Mapping[str, object]) -> str:
    if candidate.get("unresolved_reason"):
        return f"unresolved:{candidate['unresolved_reason']}"
    if not candidate.get("slot_features"):
        return "no_grammar_evidence"
    return "no_mapped_concepts"


def _empty_encounter_paradigm_resolution(
    *,
    language: str,
    text: str,
    warning: str,
) -> dict[str, object]:
    return {
        "schema_version": LANGNET_PARADIGM_RESOLUTION_SCHEMA_VERSION,
        "searched_form": text,
        "normalized_form": text,
        "language": language,
        "candidates": [],
        "warnings": [warning],
    }


def _encounter_paradigm_records(
    language: str,
    text: str,
    claims: Sequence[Mapping[str, object]],
) -> list[Mapping[str, object]]:
    triples = _encounter_claim_triples_with_tools(claims)
    records = _candidate_paradigm_records(language, text, triples)
    records.extend(_direct_paradigm_records(language, text, triples))
    records.extend(_graph_paradigm_records(language, text, triples))
    return _merge_paradigm_records(records)


def _candidate_paradigm_records(
    language: str,
    text: str,
    triples: Sequence[tuple[str, Mapping[str, object]]],
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    raw_triples = [triple for _, triple in triples]
    for candidate in candidates_from_triples(language, text, raw_triples):
        if not candidate.features:
            continue
        records.append(_paradigm_record_from_candidate(candidate))
    return records


def _paradigm_record_from_candidate(candidate: MorphologyCandidate) -> dict[str, object]:
    features: dict[str, object] = dict(candidate.features)
    if candidate.part_of_speech:
        features.setdefault("part_of_speech", candidate.part_of_speech)
    record = _paradigm_record_from_features(
        language=candidate.language,
        normalized_form=candidate.normalized_form,
        lemma=candidate.lemma,
        features=features,
        source=_paradigm_source_label(candidate.source),
    )
    record["observed_form"] = candidate.observed_form
    record["foster_display"] = candidate.foster_display
    record["ranking_reasons"] = list(candidate.ranking_reasons)
    if candidate.functional_relations:
        record["functional_relations"] = list(candidate.functional_relations)
    return record


def _direct_paradigm_records(
    language: str,
    text: str,
    triples: Sequence[tuple[str, Mapping[str, object]]],
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for claim_tool, triple in triples:
        if triple.get("predicate") != predicates.HAS_MORPHOLOGY:
            continue
        obj = triple.get("object")
        if not isinstance(obj, Mapping):
            continue
        obj_map = cast(Mapping[str, object], obj)
        features = _paradigm_features_from_morphology_object(obj_map)
        lemma = str(obj_map.get("lemma") or "").removeprefix("lex:")
        form = str(obj_map.get("form") or triple.get("subject") or text).removeprefix("form:")
        record = _paradigm_record_from_features(
            language=language,
            normalized_form=form or text,
            lemma=lemma or form or text,
            features=features,
            source=_paradigm_source_label(_encounter_triple_source_tool(triple, claim_tool)),
        )
        _copy_paradigm_string_fields(record, obj_map)
        records.append(record)
    return records


def _graph_paradigm_records(  # noqa: C901
    language: str,
    text: str,
    triples: Sequence[tuple[str, Mapping[str, object]]],
) -> list[dict[str, object]]:
    form_by_interp: dict[str, str] = {}
    lemma_by_interp: dict[str, str] = {}
    features_by_interp: dict[str, dict[str, object]] = {}
    source_by_interp: dict[str, str] = {}
    lemma_by_form: dict[str, str] = {}
    features_by_form: dict[str, dict[str, object]] = {}
    source_by_form: dict[str, str] = {}

    for claim_tool, triple in triples:
        subject = str(triple.get("subject") or "")
        predicate = str(triple.get("predicate") or "")
        obj = triple.get("object")
        source = _paradigm_source_label(_encounter_triple_source_tool(triple, claim_tool))
        if (
            predicate == predicates.HAS_INTERPRETATION
            and subject.startswith("form:")
            and isinstance(obj, str)
        ):
            form_by_interp.setdefault(obj, subject.removeprefix("form:"))
            source_by_interp.setdefault(obj, source)
            continue
        if (
            predicate == predicates.REALIZES_LEXEME
            and subject.startswith("interp:")
            and isinstance(obj, str)
        ):
            lemma_by_interp.setdefault(subject, _display_lexeme_anchor(obj))
            source_by_interp.setdefault(subject, source)
            continue
        if (
            predicate == predicates.INFLECTION_OF
            and subject.startswith("form:")
            and isinstance(obj, str)
        ):
            form = subject.removeprefix("form:")
            lemma_by_form.setdefault(form, _display_lexeme_anchor(obj))
            source_by_form.setdefault(form, source)
            continue
        feature = _paradigm_feature_from_predicate(predicate, obj)
        if feature is None:
            continue
        key, value = feature
        if subject.startswith("interp:"):
            features_by_interp.setdefault(subject, {})[key] = value
            source_by_interp.setdefault(subject, source)
        elif subject.startswith("form:"):
            form = subject.removeprefix("form:")
            features_by_form.setdefault(form, {})[key] = value
            source_by_form.setdefault(form, source)

    records: list[dict[str, object]] = []
    for interp, features in features_by_interp.items():
        form = form_by_interp.get(interp)
        lemma = lemma_by_interp.get(interp)
        if not form or not lemma:
            continue
        records.append(
            _paradigm_record_from_features(
                language=language,
                normalized_form=form,
                lemma=lemma,
                features=features,
                source=source_by_interp.get(interp, "encounter"),
            )
        )
    for form, features in features_by_form.items():
        records.append(
            _paradigm_record_from_features(
                language=language,
                normalized_form=form or text,
                lemma=lemma_by_form.get(form, form or text),
                features=features,
                source=source_by_form.get(form, "encounter"),
            )
        )
    return records


def _paradigm_features_from_morphology_object(obj: Mapping[str, object]) -> dict[str, object]:
    features: dict[str, object] = {}
    raw_features = obj.get("features")
    if isinstance(raw_features, Mapping):
        features.update(
            {
                str(key): value
                for key, value in raw_features.items()
                if isinstance(key, str) and _is_paradigm_feature_value(value)
            }
        )
    for key in (*_PARADIGM_ANALYSIS_FEATURES, "pos", "part_of_speech", "present_class"):
        value = obj.get(key)
        if value is not None and _is_paradigm_feature_value(value):
            features.setdefault(key, value)
    analysis = obj.get("analysis")
    if isinstance(analysis, str):
        for key, value in _paradigm_features_from_analysis_text(analysis).items():
            if features.get(key) is None:
                features[key] = value
    return features


def _paradigm_features_from_analysis_text(analysis: str) -> dict[str, object]:  # noqa: C901, PLR0912
    normalized = analysis.casefold().replace(",", " ")
    tokens = [token.strip() for token in re.split(r"[\s;|]+", normalized) if token.strip()]
    features: dict[str, object] = {}
    for token in tokens:
        key = token.rstrip(".")
        if key in {"m", "mas", "masc"}:
            features["gender"] = "masculine"
        elif key in {"f", "fem"}:
            features["gender"] = "feminine"
        elif key in {"n", "neu", "neut"}:
            features["gender"] = "neuter"
        elif key in {"sg", "s"}:
            features["number"] = "singular"
        elif key in {"du", "d"}:
            features["number"] = "dual"
        elif key in {"pl", "p"}:
            features["number"] = "plural"
        elif key in {"nom"}:
            features["case"] = "nominative"
        elif key in {"voc", "v"}:
            features["case"] = "vocative"
        elif key in {"acc", "a"}:
            features["case"] = "accusative"
        elif key in {"instr", "ins", "i"}:
            features["case"] = "instrumental"
        elif key in {"dat"}:
            features["case"] = "dative"
        elif key in {"abl"}:
            features["case"] = "ablative"
        elif key in {"gen", "g"}:
            features["case"] = "genitive"
        elif key in {"loc", "l"}:
            features["case"] = "locative"
        elif key in {"ind", "inde"}:
            features["pos"] = "indeclinable"
        elif key == "iic":
            features["pos"] = "compound_member"
        elif key in {"noun", "verb", "adjective", "pronoun"}:
            features["pos"] = key
        elif class_match := re.fullmatch(r"\[(\d+)\]", key):
            features["verb_class"] = class_match.group(1)
    if "pos" not in features:
        if any(key in features for key in ("case", "gender", "number")):
            features["pos"] = "noun"
        elif any(key in features for key in ("person", "tense", "mood", "voice", "verb_class")):
            features["pos"] = "verb"
    return features


def _paradigm_record_from_features(
    *,
    language: str,
    normalized_form: str,
    lemma: str,
    features: Mapping[str, object],
    source: str,
) -> dict[str, object]:
    record: dict[str, object] = {
        "language": language,
        "normalized_form": normalized_form,
        "lemma": lemma,
        "source": source,
        "part_of_speech": _paradigm_part_of_speech(features),
    }
    for key in _PARADIGM_DIRECT_FEATURE_KEYS:
        value = features.get(key)
        if _is_paradigm_feature_value(value):
            record[key] = value
    if "verb_class" in features and "present_class" not in record:
        verb_class = features.get("verb_class")
        if _is_paradigm_feature_value(verb_class):
            record["present_class"] = verb_class
    analysis = {
        key: value
        for key, value in features.items()
        if key in _PARADIGM_ANALYSIS_FEATURES and _is_paradigm_feature_value(value)
    }
    if analysis:
        record["analyses"] = [analysis]
    return record


def _paradigm_part_of_speech(features: Mapping[str, object]) -> str:
    value = features.get("part_of_speech") or features.get("pos")
    if isinstance(value, str) and value:
        if value == "unknown" or value.startswith("unknown("):
            pass
        elif value == "compound_member":
            return "unknown"
        else:
            return value
    if any(key in features for key in ("case", "gender", "number")):
        return "noun"
    if any(key in features for key in ("person", "tense", "mood", "voice", "verb_class")):
        return "verb"
    return "unknown"


def _paradigm_feature_from_predicate(
    predicate: str,
    obj: object,
) -> tuple[str, object] | None:
    if not _is_paradigm_feature_value(obj):
        return None
    mapping = {
        predicates.HAS_POS: "part_of_speech",
        predicates.HAS_CASE: "case",
        predicates.HAS_NUMBER: "number",
        predicates.HAS_GENDER: "gender",
        predicates.HAS_PERSON: "person",
        predicates.HAS_TENSE: "tense",
        predicates.HAS_MOOD: "mood",
        predicates.HAS_VOICE: "voice",
        predicates.HAS_DEGREE: "degree",
        predicates.HAS_DECLENSION: "declension",
        predicates.HAS_CONJUGATION: "conjugation",
    }
    key = mapping.get(predicate)
    return (key, obj) if key else None


def _merge_paradigm_records(records: Sequence[dict[str, object]]) -> list[Mapping[str, object]]:
    merged: dict[tuple[object, ...], dict[str, object]] = {}
    for record in records:
        key = _paradigm_record_key(record)
        current = merged.setdefault(key, {**record, "analyses": []})
        current_analyses = cast(list[object], current.setdefault("analyses", []))
        analyses = record.get("analyses")
        if isinstance(analyses, Sequence) and not isinstance(analyses, (str, bytes)):
            for analysis in analyses:
                if analysis not in current_analyses:
                    current_analyses.append(analysis)
    return list(merged.values())


def _paradigm_record_key(record: Mapping[str, object]) -> tuple[object, ...]:
    return (
        record.get("language"),
        record.get("lemma"),
        record.get("part_of_speech"),
        record.get("source"),
        record.get("gender"),
        record.get("genitive_singular") or record.get("genitive") or record.get("gen_sg"),
        record.get("article"),
        record.get("source_key") or record.get("diogenes_key") or record.get("betacode"),
        record.get("present_class") or record.get("class") or record.get("conjugation"),
    )


def _copy_paradigm_string_fields(
    record: dict[str, object],
    source: Mapping[str, object],
) -> None:
    for key in _PARADIGM_DIRECT_FEATURE_KEYS:
        value = source.get(key)
        if value is not None and _is_paradigm_feature_value(value):
            record.setdefault(key, value)


def _is_paradigm_feature_value(value: object) -> bool:
    return isinstance(value, str | int | float | bool) or value is None


def _paradigm_source_label(source_tool: str) -> str:
    normalized = source_tool.strip().lower()
    if normalized == "heritage":
        return "heritage:sktreader"
    if normalized == "whitaker":
        return "whitakers"
    if normalized == "diogenes":
        return "diogenes"
    return source_tool or "encounter"


def _encounter_morphology_rows(
    claims: Sequence[Mapping[str, object]],
    *,
    language: str = "",
    original: str = "",
    reduction=None,
    max_rows: int = 4,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str, str]] = set()
    claim_triples = _encounter_claim_triples_with_tools(claims)
    scan_rows = (
        max(max_rows, ENCOUNTER_SANSKRIT_MORPHOLOGY_SCAN_ROWS) if language == "san" else max_rows
    )
    if _append_direct_morphology_rows(claim_triples, rows, seen, scan_rows):
        return _encounter_prioritize_morphology_rows(rows, language=language)[:max_rows]

    graph = _build_morphology_graph(claim_triples)
    _append_graph_morphology_rows(graph, rows, seen, scan_rows)
    if not rows and reduction is not None:
        rows.extend(
            _encounter_local_morphology_rows(
                language=language,
                original=original,
                reduction=reduction,
                max_rows=max_rows,
            )
        )
    return _encounter_prioritize_morphology_rows(rows, language=language)[:max_rows]


def _encounter_claim_triples_with_tools(
    claims: Sequence[Mapping[str, object]],
) -> list[tuple[str, Mapping[str, object]]]:
    triples: list[tuple[str, Mapping[str, object]]] = []
    for claim in claims:
        claim_tool = str(claim.get("tool") or "")
        triples.extend((claim_tool, triple) for triple in _encounter_claim_triples(claim))
    return triples


def _encounter_prioritize_morphology_rows(
    rows: Sequence[Mapping[str, str]],
    *,
    language: str,
) -> list[dict[str, str]]:
    row_list = [dict(row) for row in rows]
    if language != "san":
        return row_list
    selected = _encounter_sanskrit_component_solution_rows(row_list)
    if not selected or list(selected) == row_list:
        return row_list

    ordered: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str, str]] = set()
    for row in [*selected, *row_list]:
        key = (
            row.get("source_tool", ""),
            row.get("form", ""),
            row.get("lemma", ""),
            row.get("analysis", ""),
            row.get("solution_number", ""),
        )
        if key in seen:
            continue
        seen.add(key)
        ordered.append(dict(row))
    return ordered


def _append_morphology_row(
    rows: list[dict[str, str]],
    seen: set[tuple[str, str, str, str, str]],
    max_rows: int,
    row: dict[str, str],
) -> bool:
    analysis = row["analysis"].strip()
    if not analysis or analysis == "?":
        return False
    row = {**row, "analysis": analysis}
    key = (
        row["source_tool"],
        row["form"],
        row["lemma"],
        row["analysis"],
        row.get("solution_number", ""),
    )
    if key in seen:
        return False
    seen.add(key)
    rows.append(row)
    return len(rows) >= max_rows


def _append_direct_morphology_rows(
    claim_triples: Sequence[tuple[str, Mapping[str, object]]],
    rows: list[dict[str, str]],
    seen: set[tuple[str, str, str, str, str]],
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
    seen: set[tuple[str, str, str, str, str]],
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


def _encounter_sanskrit_normalization_fallback_terms(  # noqa: PLR0913
    *,
    language: str,
    text: str,
    tool_filter: str,
    normalize: bool,
    norm_config: NormalizeConfig,
    no_cache: bool,
    reduction,
    max_terms: int = 2,
) -> tuple[list[str], str | None]:
    if (
        language != "san"
        or not normalize
        or reduction.buckets
        or tool_filter.lower() in {"heritage", "claim.heritage.morph"}
    ):
        return [], None
    normalized = _normalize_with_short_cache_lock(
        norm_config,
        text,
        LanguageHint.LANGUAGE_HINT_SAN,
        use_cache=not no_cache,
    )
    candidates = list(getattr(normalized.normalized, "candidates", []) or [])
    if len(candidates) <= 1:
        return [], None
    original_terms = {_encounter_normalization_fallback_key(text)}
    terms: list[str] = []
    for candidate in candidates[1:]:
        for term in _encounter_normalization_candidate_terms(candidate):
            key = _encounter_normalization_fallback_key(term)
            if not term or not key or key in original_terms:
                continue
            if key in {_encounter_normalization_fallback_key(existing) for existing in terms}:
                continue
            terms.append(term)
            if len(terms) >= max_terms:
                return (
                    terms,
                    "No sense buckets for surface form; followed Sanskrit normalization "
                    "candidate for meaning evidence.",
                )
    if not terms:
        return [], None
    return (
        terms,
        "No sense buckets for surface form; followed Sanskrit normalization candidate "
        "for meaning evidence.",
    )


def _encounter_normalization_candidate_terms(candidate: object) -> list[str]:
    terms: list[str] = []
    lemma = getattr(candidate, "lemma", "")
    if isinstance(lemma, str) and lemma.strip():
        terms.append(lemma.strip())
    encodings = getattr(candidate, "encodings", {}) or {}
    if isinstance(encodings, Mapping):
        for key in ("iast", "hk"):
            value = encodings.get(key)
            if isinstance(value, str) and value.strip():
                terms.append(value.strip())
    return _dedupe_preserve_order([term for term in terms if "_" not in term])


def _encounter_normalization_fallback_key(value: str) -> str:
    return re.sub(r"\s+", "", strip_accents(value).casefold())


def _encounter_component_links(  # noqa: PLR0913
    *,
    language: str,
    original: str,
    tool_filter: str,
    normalize: bool,
    diogenes_endpoint: str,
    diogenes_parse_endpoint: str | None,
    heritage_base: str,
    db_path: str | None,
    include_cltk: bool,
    morphology_rows: Sequence[Mapping[str, str]],
    reduction,
    max_gloss_chars: int,
    translation_cache: _PathTranslationCache | None = None,
    populate_translations: bool = False,
    translation_model: str = "",
    translation_callback=None,
    translation_diagnostics: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    components = _encounter_component_candidates(morphology_rows, language=language)
    if not components:
        return []

    links: list[dict[str, object]] = []
    for component in components:
        lookup_terms = cast(list[str], component.get("lookup_terms", []))
        buckets = _encounter_component_buckets_from_reduction(reduction, lookup_terms)
        evidence_source = "primary_reduction" if buckets else ""
        lookup_tool_filter = ""
        error = ""
        if not buckets and _encounter_should_lookup_component(language, component):
            lookup_tool_filter = _encounter_component_lookup_tool_filter(language, tool_filter)
            buckets, error = _encounter_lookup_component_buckets(
                language=language,
                lookup_terms=lookup_terms,
                context=f"component:{component.get('display') or lookup_terms[0]}",
                lookup_tool_filter=lookup_tool_filter,
                normalize=normalize,
                diogenes_endpoint=diogenes_endpoint,
                diogenes_parse_endpoint=diogenes_parse_endpoint,
                heritage_base=heritage_base,
                db_path=db_path,
                include_cltk=include_cltk,
                translation_cache=translation_cache,
                populate_translations=populate_translations,
                translation_model=translation_model,
                translation_callback=translation_callback,
                translation_diagnostics=translation_diagnostics,
            )
            if buckets:
                evidence_source = "component_lookup"
        buckets = _encounter_sort_component_buckets(buckets, component)
        meanings = [
            _encounter_component_meaning_payload(bucket, max_gloss_chars=max_gloss_chars)
            for bucket in buckets[:2]
        ]
        links.append(
            {
                **component,
                "evidence": {
                    "status": "linked" if meanings else "unlinked",
                    "source": evidence_source,
                    "lookup_tool_filter": lookup_tool_filter,
                    "meanings": meanings,
                    "error": error,
                },
            }
        )
    return links


def _encounter_component_candidates(
    morphology_rows: Sequence[Mapping[str, str]],
    *,
    language: str,
) -> list[dict[str, object]]:
    if language == "san":
        return _encounter_sanskrit_component_candidates(morphology_rows)
    if language == "lat":
        return _encounter_latin_component_candidates(morphology_rows)
    return []


def _encounter_sanskrit_component_candidates(
    morphology_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, object]]:
    if not any(_is_sanskrit_compound_component(row.get("analysis", "")) for row in morphology_rows):
        return []
    selected_rows = _encounter_sanskrit_component_solution_rows(morphology_rows)
    components: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for row in selected_rows:
        analysis = row.get("analysis", "").strip()
        lemma = row.get("lemma", "").strip()
        if not lemma:
            continue
        if _encounter_analysis_is_particle_only(analysis):
            role = "particle"
        elif _is_sanskrit_compound_component(analysis):
            role = "initial"
        else:
            role = "final"
        lookup_terms = _encounter_sanskrit_component_lookup_terms(lemma)
        if not lookup_terms:
            continue
        key = (role, lookup_terms[0])
        if key in seen:
            continue
        seen.add(key)
        components.append(
            {
                "surface": row.get("form", ""),
                "lemma": lemma,
                "display": _encounter_display_component_lemma(lemma),
                "role": role,
                "analysis": analysis,
                "source_tool": row.get("source_tool", ""),
                "lookup_terms": lookup_terms,
            }
        )
        if len(components) >= ENCOUNTER_MAX_COMPONENTS:
            break
    return components


def _encounter_sanskrit_component_solution_rows(
    morphology_rows: Sequence[Mapping[str, str]],
) -> list[Mapping[str, str]]:
    groups: dict[str, list[Mapping[str, str]]] = {}
    group_order: list[str] = []
    for row in morphology_rows:
        key = row.get("solution_number") or "_unscoped"
        if key not in groups:
            groups[key] = []
            group_order.append(key)
        groups[key].append(row)
    compound_groups = [
        (index, groups[key])
        for index, key in enumerate(group_order)
        if any(_is_sanskrit_compound_component(row.get("analysis", "")) for row in groups[key])
    ]
    if compound_groups:
        return min(
            compound_groups,
            key=lambda item: _encounter_sanskrit_component_solution_key(item[1], item[0]),
        )[1]
    return list(morphology_rows)


def _encounter_sanskrit_component_solution_key(
    rows: Sequence[Mapping[str, str]],
    index: int,
) -> tuple[int, int, int, int]:
    has_final = any(_encounter_sanskrit_row_is_final_component(row) for row in rows)
    has_particle = any(
        _encounter_analysis_is_particle_only(row.get("analysis", "")) for row in rows
    )
    # Prefer complete compound parses; for tied complete parses, keep compact didactic
    # splits before more fragmented alternatives, then preserve source order.
    return (0 if has_final else 1, 0 if has_particle else 1, len(rows), index)


def _encounter_sanskrit_row_is_final_component(row: Mapping[str, str]) -> bool:
    analysis = row.get("analysis", "").strip()
    return (
        bool(row.get("lemma", "").strip())
        and not _is_sanskrit_compound_component(analysis)
        and not _encounter_analysis_is_particle_only(analysis)
    )


def _encounter_latin_component_candidates(
    morphology_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, object]]:
    tackon_rows = [row for row in morphology_rows if "tackon" in row.get("analysis", "").casefold()]
    if not tackon_rows:
        return []
    base_rows = [
        row
        for row in morphology_rows
        if "tackon" not in row.get("analysis", "").casefold()
        and row.get("lemma", "")
        and row.get("lemma") != row.get("form")
    ]
    if not base_rows:
        base_rows = [
            row
            for row in morphology_rows
            if "tackon" not in row.get("analysis", "").casefold() and row.get("lemma", "")
        ]

    components: list[dict[str, object]] = []
    if base_rows:
        base = base_rows[0]
        lemma = base.get("lemma", "")
        components.append(
            {
                "surface": base.get("form", ""),
                "lemma": lemma,
                "display": lemma,
                "role": "base",
                "analysis": base.get("analysis", ""),
                "source_tool": base.get("source_tool", ""),
                "lookup_terms": [lemma],
            }
        )
    for row in tackon_rows[:2]:
        lemma = row.get("lemma", "")
        if not lemma:
            continue
        components.append(
            {
                "surface": row.get("form", ""),
                "lemma": lemma,
                "display": f"-{lemma}",
                "role": "tackon",
                "analysis": row.get("analysis", ""),
                "source_tool": row.get("source_tool", ""),
                "lookup_terms": [lemma],
            }
        )
    return components


def _encounter_analysis_is_particle_only(analysis: str) -> bool:
    normalized = analysis.strip().casefold()
    return normalized in {"ind.", "ind", "particle", "part.", "tackon"}


def _encounter_sanskrit_component_lookup_terms(lemma: str) -> list[str]:
    base = _encounter_sanskrit_morphology_lookup_term(lemma)
    if not base:
        return []
    terms: list[str] = []
    terms.append(base)
    if base.endswith("an") and len(base) > SANSKRIT_AN_STEM_MIN_CHARS:
        terms.append(f"{base[:-2]}a")
    return _dedupe_preserve_order(terms)


def _encounter_display_component_lemma(lemma: str) -> str:
    return _encounter_sanskrit_morphology_lookup_term(lemma) or lemma


def _encounter_component_buckets_from_reduction(
    reduction,
    lookup_terms: Sequence[str],
) -> list[object]:
    if not lookup_terms:
        return []
    lookup_keys = set().union(*(lemma_compare_keys(term) for term in lookup_terms))
    buckets: list[object] = []
    for bucket in reduction.buckets:
        bucket_keys = set().union(
            *(lemma_compare_keys(value) for value in bucket_lemma_values(bucket))
        )
        if lookup_keys & bucket_keys:
            buckets.append(bucket)
    return buckets


def _encounter_should_lookup_component(language: str, component: Mapping[str, object]) -> bool:
    return language == "san" and component.get("role") in {"initial", "final", "particle"}


def _encounter_component_lookup_tool_filter(language: str, tool_filter: str) -> str:
    normalized = tool_filter.lower()
    if language == "san" and normalized in {"all", "dico"}:
        return "dico"
    return tool_filter


def _encounter_lookup_component_buckets(  # noqa: PLR0913
    *,
    language: str,
    lookup_terms: Sequence[str],
    context: str,
    lookup_tool_filter: str,
    normalize: bool,
    diogenes_endpoint: str,
    diogenes_parse_endpoint: str | None,
    heritage_base: str,
    db_path: str | None,
    include_cltk: bool,
    translation_cache: _PathTranslationCache | None,
    populate_translations: bool,
    translation_model: str,
    translation_callback,
    translation_diagnostics: dict[str, object] | None,
) -> tuple[list[object], str]:
    last_error = ""
    for term in lookup_terms:
        try:
            result = _execute_lookup_plan(
                language=language,
                text=term,
                tool_filter=lookup_tool_filter,
                normalize=normalize,
                diogenes_endpoint=diogenes_endpoint,
                diogenes_parse_endpoint=diogenes_parse_endpoint,
                heritage_base=heritage_base,
                db_path=db_path,
                no_cache=True,
                include_cltk=include_cltk,
            )
            claims = _claims_as_mappings(result)
            if translation_cache is not None and translation_diagnostics is not None:
                claims = _encounter_apply_translation_cache(
                    claims=claims,
                    language=language,
                    model=translation_model,
                    cache=translation_cache,  # type: ignore[arg-type]
                    populate=populate_translations,
                    translate=translation_callback,
                    diagnostics=translation_diagnostics,
                    context=context,
                )
            reduction = reduce_claims(query=term, language=language, claims=claims)
            preferred = _encounter_preferred_lemmas_for_sorting(reduction, [], [term])
            reduction.buckets = sorted(
                reduction.buckets,
                key=lambda bucket: _encounter_bucket_sort_key(bucket, preferred),
            )
            if reduction.buckets:
                return list(reduction.buckets), ""
        except Exception as exc:  # noqa: BLE001
            last_error = f"{type(exc).__name__}: {exc}"
    return [], last_error


def _encounter_sort_component_buckets(
    buckets: Sequence[object],
    component: Mapping[str, object],
) -> list[object]:
    return [
        bucket
        for _idx, bucket in sorted(
            enumerate(buckets),
            key=lambda item: (
                _encounter_component_bucket_pos_penalty(item[1], component),
                item[0],
            ),
        )
    ]


def _encounter_component_bucket_pos_penalty(
    bucket: object,
    component: Mapping[str, object],
) -> int:
    if _encounter_analysis_is_particle_only(str(component.get("analysis") or "")):
        return 0
    text = _encounter_bucket_quality_text(bucket)
    if any(term in text for term in (" part.", " particle", " ind.")):
        return 1
    return 0


def _encounter_component_meaning_payload(
    bucket,
    *,
    max_gloss_chars: int,
) -> dict[str, object]:
    view = build_meaning_view(
        bucket,
        learner_gloss=_encounter_bucket_learner_gloss(bucket, max_chars=max_gloss_chars),
        evidence_gloss=_encounter_bucket_gloss(bucket),
        max_gloss_chars=max_gloss_chars,
        include_source_details=True,
    )
    return {
        "bucket_id": str(getattr(bucket, "bucket_id", "")),
        "display_gloss": view.display_gloss,
        "evidence_gloss": view.evidence_gloss,
        "evidence_length_note": view.evidence_length_note,
        "length_note": view.length_note,
        "sources": list(view.sources),
        "source_text": view.source_text,
        "witness_count": view.witness_count,
        "confidence_label": view.confidence_label,
        "source_refs": list(view.source_refs),
        "source_detail_summary": source_detail_summary_payload(view.source_detail_summary),
        "translation_sources": list(view.translation_sources),
        "source_langs": list(view.source_langs),
        "entries": [entry_summary_payload(witness) for witness in bucket.witnesses],
    }


def _encounter_word_index_query_candidates(
    text: str,
    reduction,
    preferred_lemmas: Sequence[str],
) -> list[str]:
    candidates: list[str] = [text]
    candidates.extend(preferred_lemmas)
    for anchor in getattr(reduction, "lexeme_anchors", []) or []:
        if not isinstance(anchor, str):
            continue
        value = anchor.removeprefix("lex:").strip()
        if value:
            candidates.append(value)
    for bucket in getattr(reduction, "buckets", []) or []:
        for witness in getattr(bucket, "witnesses", []) or []:
            evidence = getattr(witness, "evidence", {})
            if not isinstance(evidence, Mapping):
                continue
            candidates.extend(_encounter_word_index_evidence_terms(evidence))
    return _dedupe_preserve_order(
        [
            candidate.strip()
            for candidate in candidates
            if _encounter_word_index_candidate_is_useful(candidate)
        ]
    )[:8]


def _encounter_word_index_evidence_terms(evidence: Mapping[str, object]) -> list[str]:
    terms: list[str] = []
    for key in (
        "display_iast",
        "display_slp1",
        "headword",
        "source_key",
        "source_headword",
    ):
        value = evidence.get(key)
        if isinstance(value, str) and value.strip():
            terms.append(value.strip())
    source_entry = evidence.get("source_entry")
    if isinstance(source_entry, Mapping):
        source_entry = cast(Mapping[str, object], source_entry)
        for key in (
            "key_iast",
            "key_slp1",
            "key2_iast",
            "key2_slp1",
            "headword_roma",
            "headword_norm",
        ):
            value = source_entry.get(key)
            if isinstance(value, str) and value.strip():
                terms.append(value.strip())
    return terms


def _encounter_word_index_candidate_is_useful(value: str) -> bool:
    candidate = value.strip()
    if not candidate:
        return False
    return not re.fullmatch(r"\d+(?::\d+)+", candidate)


def _encounter_actions(
    *,
    language: str,
    text: str,
    word_index: Mapping[str, object] | None,
    paradigm_resolution: Mapping[str, object] | None,
) -> list[dict[str, object]]:
    actions: list[dict[str, object]] = []
    actions.extend(_encounter_paradigm_actions(paradigm_resolution))
    actions.extend(_encounter_word_index_actions(language=language, word_index=word_index))
    return actions


def _encounter_reader_search_context(  # noqa: PLR0913
    *,
    language: str,
    text: str,
    reduction,
    preferred_lemmas: Sequence[str],
    index_path: Path | None,
    limit: int,
    context: int,
    field: str,
    catalog_path: Path | None = None,
    all_candidates: bool = False,
) -> dict[str, object]:
    candidates = _encounter_word_index_query_candidates(text, reduction, preferred_lemmas)
    if not candidates:
        candidates = [text]
    search_candidates = candidates if all_candidates else candidates[:1]
    actions = [
        _encounter_reader_search_action(
            query=query,
            language=language,
            index_path=index_path,
            limit=limit,
            context=context,
            field=field,
        )
        for query in search_candidates
    ]
    items: list[dict[str, object]] = []
    warnings: list[dict[str, object]] = []
    if index_path is not None:
        items, warnings = _encounter_reader_search_items(
            language=language,
            text=text,
            catalog_path=catalog_path,
            index_path=index_path,
            candidates=search_candidates,
            limit=limit,
            context=context,
            field=field,
        )
    return {
        "schema_version": "langnet.encounter.reader_search.v1",
        "query_candidates": candidates,
        "search_all_candidates": all_candidates,
        "index_path": str(index_path) if index_path is not None else None,
        "actions": actions,
        "items": items,
        "warnings": warnings,
    }


def _encounter_reader_search_items(  # noqa: PLR0913
    *,
    language: str,
    text: str,
    catalog_path: Path | None,
    index_path: Path,
    candidates: Sequence[str],
    limit: int,
    context: int,
    field: str,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    items: list[dict[str, object]] = []
    warnings: list[dict[str, object]] = []
    seen_hits: set[tuple[str, str]] = set()
    for candidate_rank, query in enumerate(candidates):
        try:
            payload = search_reader_segments(
                catalog_path or _reader_catalog_path(None),
                index_path,
                query,
                language=language,
                field=field,
                context=context,
                limit=limit,
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(
                {
                    "code": "reader_search_failed",
                    "message": str(exc),
                    "index_path": str(index_path),
                    "query": query,
                    "candidate_rank": candidate_rank,
                }
            )
            continue
        _append_reader_search_hits(
            items,
            seen_hits,
            payload.get("items", []),
            input_query=text,
            matched_query=query,
            candidate_rank=candidate_rank,
            limit=limit,
        )
        if len(items) >= limit:
            break
    return items, warnings


def _append_reader_search_hits(  # noqa: PLR0913
    items: list[dict[str, object]],
    seen_hits: set[tuple[str, str]],
    raw_items: object,
    *,
    input_query: str,
    matched_query: str,
    candidate_rank: int,
    limit: int,
) -> None:
    if not isinstance(raw_items, list):
        return
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        typed_item = cast(Mapping[str, object], item)
        dedupe_key = _reader_search_hit_dedupe_key(typed_item)
        if dedupe_key in seen_hits:
            continue
        seen_hits.add(dedupe_key)
        items.append(
            _reader_search_hit_with_match_metadata(
                typed_item,
                input_query=input_query,
                matched_query=matched_query,
                candidate_rank=candidate_rank,
            )
        )
        if len(items) >= limit:
            break


def _reader_search_hit_dedupe_key(item: Mapping[str, object]) -> tuple[str, str]:
    segment_id = str(item.get("segment_id") or "")
    if segment_id:
        return ("segment_id", segment_id)
    work_id = str(item.get("work_id") or "")
    citation_path = str(item.get("citation_path") or "")
    return ("work_citation", f"{work_id}:{citation_path}")


def _reader_search_hit_with_match_metadata(
    item: Mapping[str, object],
    *,
    input_query: str,
    matched_query: str,
    candidate_rank: int,
) -> dict[str, object]:
    match_type = (
        "exact_surface"
        if candidate_rank == 0 and matched_query == input_query
        else "candidate_expansion"
    )
    return dict(item) | {
        "matched_query": matched_query,
        "input_query": input_query,
        "match_type": match_type,
        "candidate_rank": candidate_rank,
    }


def _encounter_reader_search_action(  # noqa: PLR0913
    *,
    query: str,
    language: str,
    index_path: Path | None,
    limit: int,
    context: int,
    field: str,
) -> dict[str, object]:
    argv = [
        "reader",
        "search",
        query,
        "--language",
        language,
        "--field",
        field,
        "--context",
        str(context),
        "--limit",
        str(limit),
        "--output",
        "json",
    ]
    request: dict[str, object] = {
        "command": "reader search",
        "query": query,
        "language": language,
        "field": field,
        "context": context,
        "limit": limit,
        "argv": argv,
    }
    if index_path is not None:
        request["index_path"] = str(index_path)
        argv[3:3] = ["--index", str(index_path)]
    return {
        "kind": "search_reader_corpus",
        "label": f"Search corpus for {query}",
        "status": "available",
        "source": "reader_search",
        "request": request,
    }


def _encounter_paradigm_actions(
    paradigm_resolution: Mapping[str, object] | None,
) -> list[dict[str, object]]:
    if not isinstance(paradigm_resolution, Mapping):
        return []
    candidates = paradigm_resolution.get("candidates")
    if not isinstance(candidates, Sequence) or isinstance(candidates, (str, bytes)):
        return []
    actions: list[dict[str, object]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for index, candidate_raw in enumerate(candidates):
        if not isinstance(candidate_raw, Mapping):
            continue
        candidate = cast(Mapping[str, object], candidate_raw)
        request_raw = candidate.get("paradigm_request")
        if not isinstance(request_raw, Mapping):
            continue
        request = cast(Mapping[str, object], request_raw)
        source = str(request.get("source") or "")
        language = str(request.get("language") or "")
        lemma = str(request.get("lemma") or "")
        kind = str(request.get("kind") or "")
        if not language or not lemma or not kind:
            continue
        key = (source, language, lemma, kind)
        if key in seen:
            continue
        seen.add(key)
        action_request = _encounter_paradigm_action_request(request)
        actions.append(
            {
                "kind": "view_paradigm",
                "label": f"View {lemma} {kind}",
                "status": "available",
                "source": "paradigm_resolution",
                "request": action_request,
                "target": {
                    "candidate_index": index,
                    "lemma": lemma,
                    "entry_type": candidate.get("entry_type") or "",
                    "part_of_speech": candidate.get("part_of_speech") or "",
                },
            }
        )
    return actions


def _encounter_paradigm_action_request(request: Mapping[str, object]) -> dict[str, object]:
    language = str(request.get("language") or "")
    lemma = str(request.get("lemma") or "")
    kind = str(request.get("kind") or "")
    source = str(request.get("source") or "")
    options = dict(cast(Mapping[str, object], request.get("options") or {}))
    argv = ["paradigm", language, lemma, "--kind", kind]
    for key, value in options.items():
        if value is None or value == "":
            continue
        argv.extend([f"--{key}", str(value)])
    argv.extend(["--output", "json"])
    return {
        "command": "paradigm",
        "language": language,
        "lemma": lemma,
        "kind": kind,
        "source": source,
        "options": options,
        "argv": argv,
    }


def _encounter_word_index_actions(
    *,
    language: str,
    word_index: Mapping[str, object] | None,
) -> list[dict[str, object]]:
    if not isinstance(word_index, Mapping):
        return []
    anchors = word_index.get("anchors")
    if not isinstance(anchors, Sequence) or isinstance(anchors, (str, bytes)):
        return []
    actions: list[dict[str, object]] = []
    seen_neighborhoods: set[tuple[str, str, str, str]] = set()
    seen_sources: set[tuple[str, str, str, str]] = set()
    for anchor_raw in anchors:
        if not isinstance(anchor_raw, Mapping):
            continue
        anchor = cast(Mapping[str, object], anchor_raw)
        query = str(anchor.get("query") or anchor.get("canonical_key") or "")
        source = str(anchor.get("source") or "all")
        dictionary = str(anchor.get("dictionary") or "")
        anchor_language = str(anchor.get("language") or language)
        if query:
            key = (anchor_language, query, source, dictionary)
            if key not in seen_neighborhoods:
                seen_neighborhoods.add(key)
                actions.append(_encounter_word_index_neighborhood_action(anchor, language=language))
        index_entry_id = str(anchor.get("index_entry_id") or "")
        source_ref = str(anchor.get("source_ref") or "")
        if index_entry_id or source_ref:
            key = (anchor_language, source, dictionary, index_entry_id or source_ref)
            if key not in seen_sources:
                seen_sources.add(key)
                actions.append(_encounter_source_entry_action(anchor, language=language))
    return actions


def _encounter_word_index_neighborhood_action(
    anchor: Mapping[str, object],
    *,
    language: str,
) -> dict[str, object]:
    action_language = str(anchor.get("language") or language)
    query = str(anchor.get("query") or anchor.get("canonical_key") or "")
    source = str(anchor.get("source") or "all")
    argv = [
        "word-index",
        "nearby",
        action_language,
        query,
        "--source",
        source,
        "--radius",
        str(WORD_INDEX_CONTEXT_RADIUS),
        "--output",
        "json",
    ]
    return {
        "kind": "open_word_index_neighborhood",
        "label": f"Open {query} neighborhood",
        "status": "available",
        "source": "word_index",
        "request": {
            "command": "word-index nearby",
            "language": action_language,
            "query": query,
            "source": source,
            "radius": WORD_INDEX_CONTEXT_RADIUS,
            "merge": "auto",
            "argv": argv,
        },
        "target": _encounter_word_index_action_target(anchor),
    }


def _encounter_source_entry_action(
    anchor: Mapping[str, object],
    *,
    language: str,
) -> dict[str, object]:
    action_language = str(anchor.get("language") or language)
    source = str(anchor.get("source") or "")
    dictionary = str(anchor.get("dictionary") or "")
    source_ref = str(anchor.get("source_ref") or "")
    index_entry_id = str(anchor.get("index_entry_id") or "")
    label_key = str(anchor.get("canonical_key") or anchor.get("query") or source_ref)
    return {
        "kind": "inspect_source_entry",
        "label": f"Inspect {label_key} source entry",
        "status": "available",
        "source": "word_index",
        "request": {
            "command": "inspect_source_entry",
            "language": action_language,
            "source": source,
            "dictionary": dictionary,
            "source_ref": source_ref,
            "index_entry_id": index_entry_id,
        },
        "target": _encounter_word_index_action_target(anchor),
    }


def _encounter_word_index_action_target(anchor: Mapping[str, object]) -> dict[str, object]:
    return {
        "lexeme_id": anchor.get("lexeme_id") or "",
        "index_entry_id": anchor.get("index_entry_id") or "",
        "source_order_id": anchor.get("source_order_id") or "",
        "source_order_key": anchor.get("source_order_key") or "",
        "source_ref": anchor.get("source_ref") or "",
        "anchor_status": anchor.get("anchor_status") or "",
    }


def _encounter_word_index_context(
    *,
    language: str,
    text: str,
    tool_filter: str,
    query_candidates: Sequence[str] | None = None,
) -> dict[str, object]:
    source = _encounter_word_index_source(tool_filter)
    candidates = _dedupe_preserve_order(
        [candidate for candidate in (query_candidates or [text]) if candidate]
    )
    context: dict[str, object] = {
        "request": {
            "language": language,
            "query": text,
            "query_candidates": candidates,
            "source": source,
            "radius": WORD_INDEX_CONTEXT_RADIUS,
        },
        "primary_result_contiguity": {
            "scope": "encounter_sense_buckets",
            "contiguous": False,
            "reason": (
                "Encounter buckets are ranked meaning evidence, not a contiguous "
                "dictionary or wheel window."
            ),
        },
        "lookup_strategy": {
            "inline_window_entries": False,
            "source_neighborhood_command": "word-index nearby",
            "wheel_neighborhood_status": "planned",
        },
        "anchors": [],
        "warnings": [],
    }
    warnings: list[object] = []
    anchors: list[dict[str, object]] = []
    seen_anchor_keys: set[tuple[str, str, str]] = set()
    for candidate in candidates:
        try:
            payload = word_index_neighborhood_payload(
                language,
                candidate,
                source=source,
                radius=WORD_INDEX_CONTEXT_RADIUS,
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(
                {
                    "source": source,
                    "query": candidate,
                    "message": (f"word-index context unavailable: {type(exc).__name__}: {exc}"),
                }
            )
            continue
        warnings.extend(cast(Sequence[object], payload.get("warnings") or []))
        for anchor in _encounter_word_index_anchors(
            payload.get("neighborhood"),
            query=candidate,
        ):
            key = (
                str(anchor.get("source") or ""),
                str(anchor.get("dictionary") or ""),
                str(anchor.get("index_entry_id") or ""),
            )
            if key in seen_anchor_keys:
                continue
            seen_anchor_keys.add(key)
            anchors.append(anchor)
    anchors = _encounter_word_index_preferred_anchors(anchors)
    context["warnings"] = _dedupe_word_index_warnings(warnings)
    context["anchors"] = anchors
    return context


def _encounter_word_index_preferred_anchors(
    anchors: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    exact = [anchor for anchor in anchors if anchor.get("anchor_status") == "exact"]
    return exact or list(anchors)


def _dedupe_word_index_warnings(warnings: Sequence[object]) -> list[object]:
    deduped: list[object] = []
    seen: set[str] = set()
    for warning in warnings:
        key = orjson.dumps(warning, option=orjson.OPT_SORT_KEYS).decode("utf-8")
        if key in seen:
            continue
        seen.add(key)
        deduped.append(warning)
    return deduped


def _encounter_word_index_source(tool_filter: str) -> str:
    normalized = tool_filter.strip().lower()
    return normalized if normalized in WORD_INDEX_SOURCES else "all"


def _encounter_word_index_anchors(
    neighborhood: object,
    *,
    query: str,
) -> list[dict[str, object]]:
    if not isinstance(neighborhood, Mapping):
        return []
    neighborhood = cast(Mapping[str, object], neighborhood)
    groups = neighborhood.get("groups")
    if isinstance(groups, Sequence) and not isinstance(groups, (str, bytes)):
        anchors: list[dict[str, object]] = []
        for group in groups:
            anchors.extend(_encounter_word_index_anchors(group, query=query))
        return anchors

    anchor = neighborhood.get("anchor")
    if not isinstance(anchor, Mapping):
        return []
    anchor = cast(Mapping[str, object], anchor)

    window = neighborhood.get("window")
    before = _encounter_word_index_entry_sequence(neighborhood.get("before"))
    after = _encounter_word_index_entry_sequence(neighborhood.get("after"))
    entries = [*before, anchor, *after]
    return [
        {
            "language": anchor.get("language", ""),
            "query": query,
            "source": anchor.get("source", ""),
            "dictionary": anchor.get("dictionary", ""),
            "anchor_status": neighborhood.get("anchor_status", ""),
            "lexeme_id": anchor.get("lexeme_id", ""),
            "wheel_id": anchor.get("wheel_id", ""),
            "wheel_order_key": anchor.get("wheel_order_key", ""),
            "canonical_name": anchor.get("canonical_name", ""),
            "canonical_key": anchor.get("canonical_key", ""),
            "source_name": anchor.get("source_name", ""),
            "source_ref": anchor.get("source_ref", ""),
            "index_entry_id": anchor.get("index_entry_id", ""),
            "source_order_id": anchor.get("source_order_id", ""),
            "source_order_key": anchor.get("source_order_key", ""),
            "window": _encounter_word_index_window_summary(window, entries),
        }
    ]


def _encounter_word_index_entry_sequence(value: object) -> list[Mapping[str, object]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [cast(Mapping[str, object], item) for item in value if isinstance(item, Mapping)]


def _encounter_word_index_window_summary(
    window: object,
    entries: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    summary = dict(cast(Mapping[str, object], window)) if isinstance(window, Mapping) else {}
    source_order_ids = [
        str(item.get("source_order_id") or "") for item in entries if item.get("source_order_id")
    ]
    source_order_keys = [
        str(item.get("source_order_key") or "") for item in entries if item.get("source_order_key")
    ]
    index_entry_ids = [
        str(item.get("index_entry_id") or "") for item in entries if item.get("index_entry_id")
    ]
    if source_order_ids:
        summary["min_source_order_id"] = source_order_ids[0]
        summary["max_source_order_id"] = source_order_ids[-1]
    if source_order_keys:
        summary["min_source_order_key"] = source_order_keys[0]
        summary["max_source_order_key"] = source_order_keys[-1]
    if index_entry_ids:
        summary["min_index_entry_id"] = index_entry_ids[0]
        summary["max_index_entry_id"] = index_entry_ids[-1]
    return summary


def _encounter_component_display_line(component: Mapping[str, object]) -> str:
    display = str(component.get("display") or component.get("lemma") or "")
    role = str(component.get("role") or "component")
    lookup_terms = component.get("lookup_terms")
    lookup_text = ""
    if isinstance(lookup_terms, Sequence) and not isinstance(lookup_terms, (str, bytes)):
        values = [str(term) for term in lookup_terms if str(term)]
        if values and values[0] != display:
            lookup_text = f"; lookup: {values[0]}"
    evidence = component.get("evidence")
    evidence_map = cast(Mapping[str, object], evidence) if isinstance(evidence, Mapping) else {}
    meanings = evidence_map.get("meanings")
    gloss = ""
    source_text = ""
    if isinstance(meanings, Sequence) and not isinstance(meanings, (str, bytes)) and meanings:
        first = meanings[0]
        if isinstance(first, Mapping):
            gloss = str(first.get("display_gloss") or "")
            source_text = str(first.get("source_text") or "")
    suffix = f": {gloss}" if gloss else ""
    source_suffix = f" [{source_text}]" if source_text else ""
    return f"- {display} ({role}{lookup_text}){suffix}{source_suffix}"


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
    surface_terms: Sequence[str] = (),
) -> list[str]:
    return preferred_lemmas_for_sorting(reduction, morphology_rows, fallback_terms, surface_terms)


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
    model_candidates = _translation_model_candidates(model)

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

        messages = [
            {"role": "system", "content": BASE_SYSTEM},
            {"role": "system", "content": projection.hint},
        ]
        if requires_structured_translation(projection):
            messages.append({"role": "system", "content": structured_translation_system_hint()})
            messages.append(
                {"role": "user", "content": structured_translation_user_content(projection)}
            )
        else:
            messages.append({"role": "user", "content": projection.source_text})

        kwargs = {"messages": messages}
        if requires_structured_translation(projection):
            kwargs["response_format"] = {"type": "json_object"}
            kwargs["temperature"] = 0
        response = _create_translation_completion_with_model_fallback(
            client.chat.completions,
            model_candidates=model_candidates,
            request_kwargs=kwargs,
        )
        content = _translation_response_content(response)
        if requires_structured_translation(projection):
            return content.strip()
        return content.replace("*", "").strip()

    return translate


def _translation_model_candidates(primary_model: str) -> list[str]:
    fallback_source = os.getenv(TRANSLATION_FALLBACK_MODELS_ENV)
    fallback_models = [
        model.strip()
        for model in (
            fallback_source.split(",")
            if fallback_source is not None
            else DEFAULT_TRANSLATION_FALLBACK_MODELS
        )
        if model.strip()
    ]
    return list(dict.fromkeys([primary_model, *fallback_models]))


def _create_translation_completion_with_model_fallback(
    completions,
    *,
    model_candidates: Sequence[str],
    request_kwargs: Mapping[str, Any],
):
    last_exception: Exception | None = None
    for candidate in model_candidates:
        try:
            start = time.perf_counter()
            response = completions.create(model=candidate, **request_kwargs)
            elapsed_seconds = time.perf_counter() - start
            if not _translation_response_content(response).strip():
                raise ValueError("translation provider returned an empty response")
            _validate_translation_response_latency_budget(
                response,
                elapsed_seconds=elapsed_seconds,
                model=candidate,
            )
            return response
        except Exception as exc:  # noqa: BLE001
            last_exception = exc
    assert last_exception is not None
    raise last_exception


def _translation_response_content(response) -> str:
    return str(response.choices[0].message.content or "")


def _validate_translation_response_latency_budget(
    response: object,
    *,
    elapsed_seconds: float,
    model: str,
) -> None:
    min_tokens_per_second = _float_env(
        TRANSLATION_MIN_OUTPUT_TOKENS_PER_SECOND_ENV,
        DEFAULT_TRANSLATION_MIN_OUTPUT_TOKENS_PER_SECOND,
    )
    if min_tokens_per_second <= 0:
        return
    min_tokens = _int_env(TRANSLATION_MIN_RATE_TOKENS_ENV, DEFAULT_TRANSLATION_MIN_RATE_TOKENS)
    min_seconds = _float_env(
        TRANSLATION_MIN_RATE_SECONDS_ENV,
        DEFAULT_TRANSLATION_MIN_RATE_SECONDS,
    )
    output_tokens = _translation_output_token_count(response)
    if elapsed_seconds < min_seconds or output_tokens < min_tokens:
        return
    tokens_per_second = output_tokens / max(elapsed_seconds, 0.001)
    if tokens_per_second < min_tokens_per_second:
        raise ValueError(
            f"translation provider {model} was too slow: "
            f"{tokens_per_second:.1f} output tokens/sec over {elapsed_seconds:.1f}s "
            f"for {output_tokens} output tokens; "
            f"minimum is {min_tokens_per_second:.1f}"
        )


def _translation_output_token_count(response: object) -> int:
    usage = getattr(response, "usage", None)
    usage_tokens = getattr(usage, "completion_tokens", None)
    if isinstance(usage_tokens, int) and usage_tokens > 0:
        return usage_tokens
    if isinstance(usage, Mapping):
        usage_value = usage.get("completion_tokens")
        if isinstance(usage_value, int) and usage_value > 0:
            return usage_value
    content = _translation_response_content(response)
    return max(1, len(content.split()), len(content) // 4)


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    with suppress(ValueError):
        return float(value)
    return default


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    with suppress(ValueError):
        return int(value)
    return default


def _call_work_classifier_with_retries(
    request: Callable[[], Any],
    *,
    max_attempts: int,
    sleep_seconds: float = 1.0,
) -> Any:
    last_exception: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return request()
        except Exception as exc:  # noqa: PERF203
            last_exception = exc
            if attempt >= max_attempts:
                break
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)
    raise click.ClickException(
        f"Reader work classifier failed after {max_attempts} attempt(s): {last_exception}"
    ) from last_exception


def _openrouter_work_classifier_callback(
    model: str,
    *,
    timeout_seconds: float | None = DEFAULT_CLASSIFICATION_TIMEOUT_SECONDS,
    max_attempts: int = DEFAULT_CLASSIFICATION_MAX_ATTEMPTS,
):
    client = None

    def classify(payload: Mapping[str, Any]) -> str:
        nonlocal client
        if client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise click.ClickException("Set OPENAI_API_KEY before classifying reader works.")
            api_base = os.getenv(
                "OPENAI_API_BASE",
                os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1"),
            )
            os.environ["OPENAI_BASE_URL"] = api_base
            try:
                import aisuite as ai  # noqa: PLC0415
            except ImportError as exc:
                raise click.ClickException("aisuite is required to classify reader works.") from exc
            client_config: dict[str, Any] = {
                "api_key": api_key,
                "max_retries": 0,
            }
            if timeout_seconds is not None:
                client_config["timeout"] = timeout_seconds
            client = ai.Client({"openai": client_config})

        request_kwargs = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You generate scholarly metadata for classical literature reader "
                        "catalog rows. Return JSON only. The output is generated data "
                        "for direct catalog import."
                    ),
                },
                {
                    "role": "user",
                    "content": orjson.dumps(payload, option=orjson.OPT_SORT_KEYS).decode("utf-8"),
                },
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        }
        if timeout_seconds is not None:
            request_kwargs["timeout"] = timeout_seconds
        active_client = client
        assert active_client is not None
        response = _call_work_classifier_with_retries(
            lambda: active_client.chat.completions.create(**request_kwargs),
            max_attempts=max_attempts,
        )
        return (response.choices[0].message.content or "").strip()

    return classify


def _openrouter_author_classifier_callback(
    model: str,
    *,
    timeout_seconds: float | None = DEFAULT_CLASSIFICATION_TIMEOUT_SECONDS,
    max_attempts: int = DEFAULT_CLASSIFICATION_MAX_ATTEMPTS,
):
    client = None

    def classify(payload: Mapping[str, Any]) -> str:
        nonlocal client
        if client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise click.ClickException("Set OPENAI_API_KEY before classifying reader authors.")
            api_base = os.getenv(
                "OPENAI_API_BASE",
                os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1"),
            )
            os.environ["OPENAI_BASE_URL"] = api_base
            try:
                import aisuite as ai  # noqa: PLC0415
            except ImportError as exc:
                raise click.ClickException(
                    "aisuite is required to classify reader authors."
                ) from exc
            client_config: dict[str, Any] = {
                "api_key": api_key,
                "max_retries": 0,
            }
            if timeout_seconds is not None:
                client_config["timeout"] = timeout_seconds
            client = ai.Client({"openai": client_config})

        request_kwargs = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You generate scholarly metadata for classical literature "
                        "author and agent index rows. Return JSON only. The output "
                        "is generated data for direct catalog import."
                    ),
                },
                {
                    "role": "user",
                    "content": orjson.dumps(payload, option=orjson.OPT_SORT_KEYS).decode("utf-8"),
                },
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        }
        if timeout_seconds is not None:
            request_kwargs["timeout"] = timeout_seconds
        active_client = client
        assert active_client is not None
        response = _call_work_classifier_with_retries(
            lambda: active_client.chat.completions.create(**request_kwargs),
            max_attempts=max_attempts,
        )
        return (response.choices[0].message.content or "").strip()

    return classify


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
    cache_policy: str = "read-write",
):
    lang_hint = _parse_language(language)
    norm_cfg = NormalizeConfig(
        diogenes_endpoint=diogenes_endpoint,
        heritage_base=heritage_base,
        db_path=db_path,
        no_cache=no_cache,
        output="pretty",
        cache_policy=cache_policy,
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

    path = Path(norm_cfg.db_path).expanduser() if norm_cfg.db_path else normalization_db_path()
    registry = _default_registry(use_stubs=False)
    clients = _build_exec_clients(plan, diogenes_endpoint, use_stubs=False)
    if cache_policy == "read-write" and not no_cache:
        return execute_plan_staged(
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

    if cache_policy == "read-only" and not no_cache and path.exists():
        cached_plan = PathPlanResponseIndex(path).get(plan.plan_hash)
        if cached_plan is not None:
            with duckdb.connect(database=":memory:") as conn:
                apply_schema(conn)
                return execute_plan_staged(
                    plan=plan,
                    clients=clients,
                    registry=registry,
                    raw_index=PathRawResponseIndex(path),
                    extraction_index=ExtractionIndex(conn),
                    derivation_index=DerivationIndex(conn),
                    claim_index=ClaimIndex(conn),
                    plan_response_index=PathPlanResponseIndex(path),
                    allow_cache=True,
                )

    with duckdb.connect(database=":memory:") as conn:
        apply_schema(conn)
        raw_index = RawResponseIndex(conn)
        extraction_index = ExtractionIndex(conn)
        derivation_index = DerivationIndex(conn)
        claim_index = ClaimIndex(conn)
        plan_response_index = PlanResponseIndex(conn)
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
        with connect_duckdb(cache_path, read_only=True, lock=False, allow_create=False) as conn:
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


def _translation_retry_generation(  # noqa: PLR0913
    conn: duckdb.DuckDBPyConnection,
    *,
    source_lexicon: str | None,
    entry_id: str | None,
    occurrence: int | None,
    source_text_hash: str | None,
    translation_id: str | None,
) -> int:
    if source_lexicon and entry_id and occurrence is not None and source_text_hash:
        row = conn.execute(
            """
            SELECT COUNT(*)
            FROM entry_translation_rejections
            WHERE source_lexicon = ?
              AND entry_id = ?
              AND occurrence = ?
              AND source_text_hash = ?
            """,
            [source_lexicon, entry_id, occurrence, source_text_hash],
        ).fetchone()
    elif translation_id:
        row = conn.execute(
            """
            SELECT COUNT(*)
            FROM entry_translation_rejections
            WHERE translation_id = ?
            """,
            [translation_id],
        ).fetchone()
    else:
        return 0
    return int(row[0]) if row is not None else 0


def _record_translation_retry_rejection(  # noqa: PLR0913
    conn: duckdb.DuckDBPyConnection,
    *,
    translation_id: str | None,
    source_lexicon: str | None,
    entry_id: str | None,
    occurrence: int | None,
    source_text_hash: str | None,
    headword: str | None,
    retry_reason: str | None,
) -> None:
    if not (source_lexicon and entry_id and occurrence is not None and source_text_hash):
        return
    material = "\x1f".join(
        [
            translation_id or "",
            source_lexicon,
            entry_id,
            str(occurrence),
            source_text_hash,
            str(time.time()),
        ]
    )
    rejection_id = f"tr-reject:{hashlib.sha256(material.encode('utf-8')).hexdigest()[:24]}"
    conn.execute(
        """
        INSERT INTO entry_translation_rejections
        (rejection_id, translation_id, source_lexicon, entry_id, occurrence, headword_norm,
         source_text_hash, reason, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            rejection_id,
            translation_id,
            source_lexicon,
            entry_id,
            occurrence,
            headword,
            source_text_hash,
            retry_reason,
            time.time(),
        ],
    )


def _translation_cache_clear_payload(  # noqa: C901, PLR0913
    cache_path: Path,
    *,
    translation_id: str | None = None,
    source_lexicon: str | None = None,
    status: str | None = None,
    headword: str | None = None,
    entry_id: str | None = None,
    occurrence: int | None = None,
    source_text_hash: str | None = None,
    retry_reason: str | None = None,
    max_retries: int | None = None,
) -> dict[str, object]:
    filters_payload = {
        "translation_id": translation_id,
        "source_lexicon": source_lexicon,
        "status": status,
        "headword": headword,
        "entry_id": entry_id,
        "occurrence": occurrence,
        "source_text_hash": source_text_hash,
        "retry_reason": retry_reason,
        "max_retries": max_retries,
    }
    before = _translation_cache_status_payload(cache_path)
    if before.get("error"):
        return {
            "schema_version": TRANSLATION_CACHE_SCHEMA_VERSION,
            "cache_db": str(cache_path),
            **filters_payload,
            "deleted": 0,
            "before": before,
            "after": before,
            "error": before["error"],
        }
    if cache_path.exists():
        with connect_duckdb(cache_path, read_only=False, lock=True) as conn:
            apply_translation_schema(conn)
            retry_generation = _translation_retry_generation(
                conn,
                source_lexicon=source_lexicon,
                entry_id=entry_id,
                occurrence=occurrence,
                source_text_hash=source_text_hash,
                translation_id=translation_id,
            )
            if max_retries is not None and retry_generation >= max_retries:
                return {
                    "schema_version": TRANSLATION_CACHE_SCHEMA_VERSION,
                    "cache_db": str(cache_path),
                    **filters_payload,
                    "deleted": 0,
                    "retry_generation": retry_generation,
                    "limit_reached": True,
                    "before": before,
                    "after": before,
                }
            where_clauses: list[str] = []
            params: list[object] = []
            if translation_id:
                where_clauses.append("translation_id = ?")
                params.append(translation_id)
            if source_lexicon:
                where_clauses.append("source_lexicon = ?")
                params.append(source_lexicon)
            if status:
                where_clauses.append("status = ?")
                params.append(status)
            if headword:
                where_clauses.append("headword_norm = ?")
                params.append(headword)
            if entry_id:
                where_clauses.append("entry_id = ?")
                params.append(entry_id)
            if occurrence is not None:
                where_clauses.append("occurrence = ?")
                params.append(occurrence)
            if source_text_hash:
                where_clauses.append("source_text_hash = ?")
                params.append(source_text_hash)
            where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            row = conn.execute(
                f"SELECT COUNT(*) FROM entry_translations{where_sql}",
                params,
            ).fetchone()
            deleted = int(row[0]) if row is not None else 0
            conn.execute(f"DELETE FROM entry_translations{where_sql}", params)
            if retry_reason and deleted:
                _record_translation_retry_rejection(
                    conn,
                    translation_id=translation_id,
                    source_lexicon=source_lexicon,
                    entry_id=entry_id,
                    occurrence=occurrence,
                    source_text_hash=source_text_hash,
                    headword=headword,
                    retry_reason=retry_reason,
                )
                retry_generation = _translation_retry_generation(
                    conn,
                    source_lexicon=source_lexicon,
                    entry_id=entry_id,
                    occurrence=occurrence,
                    source_text_hash=source_text_hash,
                    translation_id=translation_id,
                )
    else:
        deleted = 0
        retry_generation = 0
    after = _translation_cache_status_payload(cache_path)
    return {
        "schema_version": TRANSLATION_CACHE_SCHEMA_VERSION,
        "cache_db": str(cache_path),
        **filters_payload,
        "deleted": deleted,
        "retry_generation": retry_generation,
        "limit_reached": False,
        "before": before,
        "after": after,
    }


@click.group("translation-cache")
def translation_cache_cli() -> None:
    """Inspect and clear cached DICO/Gaffiot/Bailly translation rows."""


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
@click.option(
    "--source-lexicon",
    type=click.Choice(["bailly", "dico", "gaffiot"]),
    default=None,
    help="Delete only rows for one generated translation source.",
)
@click.option(
    "--translation-id",
    default=None,
    help="Delete one exact cached translation row by translation_id.",
)
@click.option(
    "--status",
    type=click.Choice(["ok", "empty", "error"]),
    default=None,
    help="Delete only rows with one cache status.",
)
@click.option(
    "--headword",
    default=None,
    help="Delete only rows for one normalized headword.",
)
@click.option(
    "--entry-id",
    default=None,
    help="Delete only rows for one source entry id.",
)
@click.option(
    "--occurrence",
    type=int,
    default=None,
    help="Delete only rows for one source entry occurrence.",
)
@click.option(
    "--source-text-hash",
    default=None,
    help="Delete only rows for one source text hash.",
)
@click.option(
    "--retry-reason",
    default=None,
    help="Record a bounded user-triggered retry reason while clearing.",
)
@click.option(
    "--max-retries",
    type=click.IntRange(min=0),
    default=None,
    help="Refuse to clear when this projection already has this many retry rejections.",
)
@click.confirmation_option(
    "--yes",
    prompt="Delete matching cached translation rows?",
)
def translation_cache_clear(  # noqa: PLR0913
    translation_cache_db: str,
    output: str,
    translation_id: str | None,
    source_lexicon: str | None,
    status: str | None,
    headword: str | None,
    entry_id: str | None,
    occurrence: int | None,
    source_text_hash: str | None,
    retry_reason: str | None,
    max_retries: int | None,
) -> None:
    """Delete cached DICO/Gaffiot/Bailly translation rows."""
    payload = _translation_cache_clear_payload(
        Path(translation_cache_db),
        translation_id=translation_id,
        source_lexicon=source_lexicon,
        status=status,
        headword=headword,
        entry_id=entry_id,
        occurrence=occurrence,
        source_text_hash=source_text_hash,
        retry_reason=retry_reason,
        max_retries=max_retries,
    )
    if output == "json":
        click.echo(orjson.dumps(payload, option=orjson.OPT_INDENT_2).decode("utf-8"))
        return

    filters = [
        label
        for label in (
            f"translation_id={translation_id}" if translation_id is not None else None,
            source_lexicon,
            f"status={status}" if status is not None else None,
            f"headword={headword}" if headword is not None else None,
            f"entry_id={entry_id}" if entry_id is not None else None,
            f"occurrence={occurrence}" if occurrence is not None else None,
            f"source_text_hash={source_text_hash}" if source_text_hash is not None else None,
            f"retry_reason={retry_reason}" if retry_reason is not None else None,
            f"max_retries={max_retries}" if max_retries is not None else None,
        )
        if label
    ]
    label = f" for {', '.join(filters)}" if filters else ""
    click.echo(
        f"Cleared {payload['deleted']} translation row(s){label} from {payload['cache_db']}."
    )


main.add_command(translation_cache_cli)


@main.command("translation-warm")
@click.argument("language", type=click.Choice(["grc", "lat", "san"], case_sensitive=False))
@click.argument(
    "wordlist",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--tool-filter",
    default="all",
    show_default=True,
    help="Restrict lookup tools before collecting French translation candidates.",
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
    default=DEFAULT_TRANSLATION_MODEL,
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
    """Warm French lexicon translation cache rows for a word list."""
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
    "--cache-policy",
    type=click.Choice(["read-write", "read-only", "off"]),
    default="read-write",
    show_default=True,
    help=(
        "Normalization cache behavior. read-only may read warmed rows but never writes; "
        "off skips normalization cache reads and writes."
    ),
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
    help="Display cached French-to-English lexicon translations when available.",
)
@click.option(
    "--translation-mode",
    type=click.Choice(["off", "cache", "populate", "auto", "do-it-all"]),
    default="cache",
    show_default=True,
    help=(
        "French source translation mode: cache-only, off, or populate missing "
        "lexicon rows via OpenRouter before display. do-it-all is an alias for auto."
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
    default=DEFAULT_TRANSLATION_MODEL,
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
@click.option(
    "--include-paradigm-resolution/--no-include-paradigm-resolution",
    default=False,
    show_default=True,
    help="Include local paradigm-resolution metadata in JSON output without fetching tables.",
)
@click.option(
    "--include-learning/--no-include-learning",
    default=False,
    show_default=True,
    help=(
        "Attach Foster/traditional learning overlays to paradigm-resolution candidates. "
        "This computes paradigm resolution if needed."
    ),
)
@click.option(
    "--include-reader-search/--no-include-reader-search",
    default=False,
    show_default=True,
    help="Include reader corpus search actions in JSON output.",
)
@click.option(
    "--reader-search-index",
    type=click.Path(),
    default=None,
    help="Optional Lance reader search index for inline corpus hits.",
)
@click.option(
    "--reader-catalog",
    type=click.Path(),
    default=None,
    help="Reader catalog path used for reader search metadata.",
)
@click.option(
    "--reader-search-limit",
    default=5,
    show_default=True,
    type=click.IntRange(1, 50),
    help="Maximum inline reader corpus hits when --reader-search-index is supplied.",
)
@click.option(
    "--reader-search-context",
    default=0,
    show_default=True,
    type=click.IntRange(0, 10),
    help="Context radius for inline reader corpus hits.",
)
@click.option(
    "--reader-search-field",
    type=click.Choice(["auto", "display", "search", "folded"]),
    default="auto",
    show_default=True,
    help="Reader search field passed to the corpus search index.",
)
@click.option(
    "--reader-search-all-candidates/--no-reader-search-all-candidates",
    default=False,
    show_default=True,
    help="Search every encounter reader-search candidate and deduplicate inline hits.",
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
    cache_policy: str,
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
    include_paradigm_resolution: bool,
    include_learning: bool,
    include_reader_search: bool,
    reader_search_index: str | None,
    reader_catalog: str | None,
    reader_search_limit: int,
    reader_search_context: int,
    reader_search_field: str,
    reader_search_all_candidates: bool,
):
    """
    Show a compact, source-backed learner encounter for one word.
    """
    cache_policy = "off" if no_cache else cache_policy
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
            cache_policy=cache_policy,
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
        normalization_fallback_terms: list[str] = []
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

        norm_cfg = NormalizeConfig(
            diogenes_endpoint=diogenes_endpoint,
            heritage_base=heritage_base,
            db_path=db_path,
            no_cache=no_cache,
            output="pretty",
            cache_policy=cache_policy,
        )
        normalization_fallback_terms, normalization_fallback_warning = (
            _encounter_sanskrit_normalization_fallback_terms(
                language=language,
                text=text,
                tool_filter=tool_filter,
                normalize=normalize,
                norm_config=norm_cfg,
                no_cache=no_cache,
                reduction=reduction,
            )
        )
        if normalization_fallback_terms:
            original_bucket_count = len(reduction.buckets)
            fallback_claims = list(claims)
            for fallback_term in normalization_fallback_terms:
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
                            context=f"normalization-fallback:{fallback_term}",
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
                    if normalization_fallback_warning:
                        reduction.warnings.append(normalization_fallback_warning)

        morphology_rows = _encounter_morphology_rows(
            morphology_claims,
            language=language,
            original=text,
            reduction=reduction,
        )
        preferred_lemmas = _encounter_preferred_lemmas_for_sorting(
            reduction,
            morphology_rows,
            [*normalization_fallback_terms, *fallback_terms],
            [text],
        )
        reduction.buckets = sorted(
            reduction.buckets,
            key=lambda bucket: _encounter_bucket_sort_key(bucket, preferred_lemmas),
        )
        component_links = _encounter_component_links(
            language=language,
            original=text,
            tool_filter=tool_filter,
            normalize=normalize,
            diogenes_endpoint=diogenes_endpoint,
            diogenes_parse_endpoint=diogenes_parse_endpoint,
            heritage_base=heritage_base,
            db_path=db_path,
            include_cltk=include_cltk,
            morphology_rows=morphology_rows,
            reduction=reduction,
            max_gloss_chars=max_gloss_chars,
            translation_cache=translation_cache,
            populate_translations=populate_translations,
            translation_model=translation_model,
            translation_callback=translation_callback,
            translation_diagnostics=translation_diagnostics,
        )

        if output == "json":
            payload = asdict(reduction)
            include_reader_search_payload = include_reader_search or bool(reader_search_index)
            request_payload = {
                "command": "encounter",
                "language": language,
                "text": text,
                "tool_filter": tool_filter,
                "normalize": normalize,
                "no_cache": no_cache,
                "cache_policy": cache_policy,
                "normalization_cache_writes": cache_policy == "read-write",
                "include_cltk": include_cltk,
                "translation_mode": resolved_translation_mode,
                "translation_cache_writes": populate_translations,
                "include_paradigm_resolution": include_paradigm_resolution,
                "include_learning": include_learning,
            }
            if include_reader_search_payload:
                request_payload.update(
                    {
                        "include_reader_search": include_reader_search,
                        "reader_search_index": reader_search_index,
                        "reader_search_limit": reader_search_limit,
                        "reader_search_context": reader_search_context,
                        "reader_search_field": reader_search_field,
                        "reader_search_all_candidates": reader_search_all_candidates,
                    }
                )
            payload["schema_version"] = ENCOUNTER_JSON_SCHEMA_VERSION
            payload["request"] = request_payload
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
            if isinstance(payload["display"], dict):
                payload["display"]["components"] = component_links
            payload["components"] = component_links
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
            payload["word_index"] = _encounter_word_index_context(
                language=language,
                text=text,
                tool_filter=tool_filter,
                query_candidates=_encounter_word_index_query_candidates(
                    text,
                    reduction,
                    preferred_lemmas,
                ),
            )
            paradigm_resolution_payload = None
            if include_paradigm_resolution or include_learning:
                paradigm_resolution_payload = _encounter_paradigm_resolution_payload(
                    language,
                    text,
                    morphology_claims,
                )
                if include_learning:
                    paradigm_resolution_payload = _encounter_add_learning_overlays(
                        paradigm_resolution_payload
                    )
                payload["paradigm_resolution"] = paradigm_resolution_payload
            reader_search_payload = None
            reader_search_index_path = (
                Path(reader_search_index).expanduser() if reader_search_index else None
            )
            if include_reader_search_payload:
                reader_search_payload = _encounter_reader_search_context(
                    language=language,
                    text=text,
                    reduction=reduction,
                    preferred_lemmas=preferred_lemmas,
                    index_path=reader_search_index_path,
                    limit=reader_search_limit,
                    context=reader_search_context,
                    field=reader_search_field,
                    catalog_path=_reader_catalog_path(reader_catalog),
                    all_candidates=reader_search_all_candidates,
                )
                payload["reader_search"] = reader_search_payload
            actions = _encounter_actions(
                language=language,
                text=text,
                word_index=cast(Mapping[str, object], payload.get("word_index") or {}),
                paradigm_resolution=paradigm_resolution_payload,
            )
            if isinstance(reader_search_payload, Mapping):
                reader_actions = reader_search_payload.get("actions")
                if isinstance(reader_actions, list):
                    actions.extend(
                        cast(dict[str, object], action)
                        for action in reader_actions
                        if isinstance(action, dict)
                    )
            payload["actions"] = actions
            if isinstance(payload["display"], dict):
                payload["display"]["actions"] = actions
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
        if component_links:
            click.echo("\nComponents")
            for component in component_links:
                click.echo(_encounter_component_display_line(component))
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
                        cache_policy=cache_policy,
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
    default=DEFAULT_TRANSLATION_MODEL,
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
    "--kind",
    type=click.Choice(["declension", "conjugation"], case_sensitive=False),
    default="declension",
    show_default=True,
    help="Paradigm kind to fetch.",
)
@click.option("--gender", help="Sanskrit Heritage gender value for declension: Mas, Fem, or Neu.")
@click.option(
    "--class",
    "present_class",
    help="Sanskrit Heritage present class for conjugation.",
)
@click.option(
    "--diogenes-endpoint",
    default="http://localhost:8888/Perseus.cgi",
    show_default=True,
    help="Diogenes inflection endpoint.",
)
@click.option(
    "--heritage-base",
    default="http://localhost:48080",
    show_default=True,
    help="Base URL for Heritage Platform.",
)
@click.option(
    "--output",
    type=click.Choice(["json", "pretty"]),
    default="json",
    show_default=True,
    help="Output format.",
)
def paradigm(  # noqa: PLR0913
    language: str,
    text: str,
    kind: str,
    gender: str | None,
    present_class: str | None,
    diogenes_endpoint: str,
    heritage_base: str,
    output: str,
) -> None:
    """Fetch a source-backed inflectional paradigm for a resolved lemma."""
    request = _paradigm_request_from_cli(language.lower(), text, kind, gender, present_class)
    service = ParadigmService(heritage_base=heritage_base, diogenes_endpoint=diogenes_endpoint)
    payload = service.fetch(request)
    data = asdict(payload)

    if output == "json":
        click.echo(orjson.dumps(data, option=orjson.OPT_INDENT_2).decode("utf-8"))
        return

    click.echo(f"{payload.language} {payload.lemma} {payload.kind} via {payload.source}")
    for block in payload.paradigms:
        click.echo(block.label)
        for slot in block.slots:
            feature_text = ", ".join(f"{key}={value}" for key, value in slot.features.items())
            forms = ", ".join(form.text for form in slot.forms)
            click.echo(f"  {feature_text}: {forms}")


def _paradigm_request_from_cli(
    language: str,
    lemma: str,
    kind: str,
    gender: str | None,
    present_class: str | None,
) -> ParadigmRequest:
    if language == "san" and kind == "declension":
        if not gender:
            raise click.UsageError("Sanskrit declension paradigm requires --gender.")
        return ParadigmRequest(
            source="heritage:sktdeclin",
            language="san",
            lemma=lemma,
            kind="declension",
            options={"gender": gender},
        )
    if language == "san" and kind == "conjugation":
        if not present_class:
            raise click.UsageError("Sanskrit conjugation paradigm requires --class.")
        return ParadigmRequest(
            source="heritage:sktconjug",
            language="san",
            lemma=lemma,
            kind="conjugation",
            options={"class": present_class},
        )
    if language in {"lat", "grc"}:
        return ParadigmRequest(
            source="diogenes:inflect",
            language=cast(Any, language),
            lemma=lemma,
            kind=cast(Any, kind),
            options={},
        )
    raise click.UsageError(f"Unsupported language for paradigm: {language}")


@main.command()
@click.argument("language", type=click.Choice(["lat", "grc", "san"], case_sensitive=False))
@click.argument("text")
@click.option(
    "--record-json",
    "record_jsons",
    multiple=True,
    help="Lookup/analyzer record JSON to feed the resolver without calling external services.",
)
@click.option(
    "--output",
    type=click.Choice(["json", "pretty"]),
    default="json",
    show_default=True,
    help="Output format.",
)
def paradigm_resolve(
    language: str,
    text: str,
    record_jsons: tuple[str, ...],
    output: str,
) -> None:
    """
    Explain how a searched form resolves to possible paradigm requests.

    This command is intentionally endpoint-free when --record-json is supplied:
    it shows the resolver's native grammar, functional grammar, and request
    metadata before any Heritage or Diogenes paradigm table is fetched.
    """
    records: list[Mapping[str, object]] = []
    for raw_record in record_jsons:
        try:
            decoded = orjson.loads(raw_record)
        except orjson.JSONDecodeError as exc:
            raise click.UsageError(f"Invalid --record-json value: {exc}") from exc
        if not isinstance(decoded, Mapping):
            raise click.UsageError("--record-json must decode to a JSON object.")
        records.append(cast(Mapping[str, object], decoded))

    if not records:
        records.append({"lemma": text, "part_of_speech": "unknown", "source": "cli"})

    payload = resolve_paradigm_request(
        cast(Any, language.lower()),
        text,
        records,
    )
    data = asdict(payload)

    if output == "json":
        click.echo(orjson.dumps(data, option=orjson.OPT_INDENT_2).decode("utf-8"))
        return

    click.echo(f"{data['language']} {data['searched_form']} -> {data['normalized_form']}")
    for candidate in data["candidates"]:
        click.echo(
            f"- {candidate['lemma']} "
            f"({candidate['entry_type']}, {candidate['part_of_speech']}): "
            f"{candidate['confidence']}"
        )
        if candidate["paradigm_request"] is None:
            click.echo(f"  unresolved: {candidate['unresolved_reason']}")
        else:
            request = candidate["paradigm_request"]
            click.echo(f"  request: {request['source']} {request['lemma']}")


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
                cdsl_query_word = (
                    _sanskrit_cdsl_query_from_heritage(results.get("heritage"), query_word)
                    if language.lower() == "san"
                    else query_word
                )
                lemma = cdsl_handlers._to_slp1(cdsl_query_word)  # type: ignore[attr-defined]
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
