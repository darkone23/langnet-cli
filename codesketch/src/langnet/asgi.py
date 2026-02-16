import time
import uuid
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import cast

import cattrs
import orjson
import structlog
from langnet.config import get_settings
from langnet.core import LangnetWiring, build_langnet_wiring
from langnet.health import run_health_checks
from langnet.logging import scoped_context, setup_logging
from langnet.semantic_converter import convert_multiple_entries
from langnet.types import JSONMapping
from langnet.validation import validate_query, validate_tool_request
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route

logger = structlog.get_logger(__name__)

# Configure cattrs for JSON serialization with omit_if_default
json_converter = cattrs.Converter(omit_if_default=True)
settings = get_settings()
setup_logging(settings.log_level_value)


def _request_context(request: Request) -> AbstractContextManager[None]:
    request_id = (
        request.headers.get("x-request-id")
        or request.headers.get("x-correlation-id")
        or str(uuid.uuid4())
    )
    return scoped_context(
        request_id=request_id,
        path=str(request.url.path),
        method=request.method,
    )


def _ensure_wiring(request: Request) -> LangnetWiring:
    if not hasattr(request.app.state, "wiring"):
        request.app.state.wiring = build_langnet_wiring(settings=settings)
    return cast(LangnetWiring, request.app.state.wiring)


# from langnet.citation.models import CitationCollection, Citation, TextReference, CitationType
# from langnet.citation.cts_urn import CTSUrnMapper


class ORJsonResponse(Response):
    media_type = "application/json"

    def __init__(
        self,
        content: object,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        **kwargs,
    ):
        super().__init__(content, status_code=status_code, headers=headers, **kwargs)

    def render(self, content: object) -> bytes:
        return orjson.dumps(content)


async def health_check(request: Request):
    with _request_context(request):
        try:
            _ensure_wiring(request)
        except Exception as e:
            return ORJsonResponse({"error": f"Startup failed: {str(e)}"}, status_code=503)
        try:
            cache_stats_provider = None
            if hasattr(request.app.state, "wiring"):
                cache = getattr(request.app.state.wiring.engine, "cache", None)
                if cache and hasattr(cache, "get_stats"):
                    cache_stats_provider = cast(Callable[[], JSONMapping], cache.get_stats)
            health = run_health_checks(settings, cache_stats_provider=cache_stats_provider)
            return ORJsonResponse(health)
        except Exception as e:
            return ORJsonResponse({"error": str(e)}, status_code=500)


async def cache_stats_api(request: Request):
    try:
        cache = getattr(request.app.state.wiring.engine, "cache", None)
        if cache and hasattr(cache, "get_stats"):
            stats = cache.get_stats()
        else:
            stats = {"message": "Cache stats not configured"}
        return ORJsonResponse(stats)
    except Exception as e:
        return ORJsonResponse({"error": str(e)}, status_code=500)


async def query_api(request: Request):
    with _request_context(request):
        request_start = time.perf_counter()

        # Check if semantic format is requested
        semantic_format = request.query_params.get("format") == "semantic"

        if request.method == "POST":
            form_data = await request.form()
            raw_lang = form_data.get("l")
            raw_word = form_data.get("s")
        else:
            raw_lang = request.query_params.get("l")
            raw_word = request.query_params.get("s")

        lang = str(raw_lang) if isinstance(raw_lang, str) else None
        word = str(raw_word) if isinstance(raw_word, str) else None

        validation_error, normalized_lang = validate_query(lang, word)
        if validation_error:
            return ORJsonResponse({"error": validation_error}, status_code=400)

        lang = normalized_lang or lang

        try:
            wiring_start = time.perf_counter()
            wiring: LangnetWiring = _ensure_wiring(request)
            wiring_ms = (time.perf_counter() - wiring_start) * 1000
        except Exception as e:
            return ORJsonResponse({"error": f"Startup failed: {str(e)}"}, status_code=503)

        try:
            handle_start = time.perf_counter()
            result = wiring.engine.handle_query(lang, word)
            handle_ms = (time.perf_counter() - handle_start) * 1000

            if semantic_format:
                # Convert to semantic structs format
                semantic_response = convert_multiple_entries(result)
                # Convert to dict for JSON serialization
                result_dict = semantic_response.to_dict()
            else:
                # Unstructure DictionaryEntry objects to dicts (omits None fields)
                result_dict = [json_converter.unstructure(entry) for entry in result]

            total_ms = (time.perf_counter() - request_start) * 1000

            timings_payload = {
                "wiring_ms": round(wiring_ms, 3),
                "handle_query_ms": round(handle_ms, 3),
                "total_ms": round(total_ms, 3),
            }

            if not semantic_format:
                for entry in result_dict:
                    if not isinstance(entry, dict):
                        continue
                    if "metadata" in entry and isinstance(entry["metadata"], dict):
                        entry["metadata"].pop("timings_ms", None)
                        entry["metadata"].pop("request_timings_ms", None)

            logger.info(
                "query_timings",
                lang=lang,
                word=word,
                format="semantic" if semantic_format else "legacy",
                request_timings=timings_payload,
            )

            return ORJsonResponse(result_dict)
        except Exception as e:
            logger.error(
                "query_api_failed",
                error=str(e),
                exc_info=True,
                lang=lang,
                word=word,
                format="semantic" if semantic_format else "legacy",
            )
            return ORJsonResponse({"error": str(e)}, status_code=500)


async def tool_api(request: Request):
    """API endpoint for tool-specific debugging and raw data access."""
    with _request_context(request):
        tool = request.path_params.get("tool")
        action = request.path_params.get("action")
        lang = request.query_params.get("lang")
        query = request.query_params.get("query")
        dict_name = request.query_params.get("dict")

    # Validate parameters
    validation_error = validate_tool_request(tool, action, lang, query, dict_name)
    if validation_error:
        return ORJsonResponse({"error": validation_error}, status_code=400)

    try:
        wiring: LangnetWiring = _ensure_wiring(request)
    except Exception as e:
        return ORJsonResponse({"error": f"Startup failed: {str(e)}"}, status_code=503)

    try:
        result = wiring.engine.get_tool_data(
            tool or "", action or "", lang or "", query or "", dict_name or ""
        )
        return ORJsonResponse(result)
    except ValueError as e:
        logger.error("tool_api_param_error", error=str(e))
        return ORJsonResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error(
            "tool_api_failed",
            error=str(e),
            exc_info=True,
            tool=tool,
            action=action,
        )
        return ORJsonResponse({"error": f"Internal server error: {str(e)}"}, status_code=500)


routes = [
    Route("/api/q", query_api, methods=["GET", "POST"]),
    Route("/api/health", health_check),
    Route("/api/cache/stats", cache_stats_api),
    Route("/api/tool/{tool}/{action}", tool_api, methods=["GET", "POST"]),
]


def create_app() -> Starlette:
    app = Starlette(routes=routes)

    @app.on_event("startup")
    async def startup():
        start = time.perf_counter()
        try:
            app.state.wiring = build_langnet_wiring(settings=settings)
            elapsed = time.perf_counter() - start
            logger.info("wiring_initialized", duration_seconds=elapsed)
        except Exception as e:
            logger.error("wiring_initialization_failed", error=str(e))
            print(f"Failed to initialize wiring at startup: {e}")

    return app


app = create_app()
