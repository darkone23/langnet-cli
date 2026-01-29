import time
from pathlib import Path
from typing import Any

import orjson
import requests
import structlog
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route

import langnet.logging  # noqa: F401 - ensures logging is configured before use

logger = structlog.get_logger(__name__)

from langnet.core import LangnetWiring  # noqa: E402
from langnet.diogenes.core import DiogenesScraper  # noqa: E402
from langnet.heritage.config import HeritageConfig  # noqa: E402
from langnet.heritage.morphology import HeritageMorphologyService  # noqa: E402


class ORJsonResponse(Response):
    media_type = "application/json"

    def __init__(
        self,
        content: Any,
        status_code: int = 200,
        headers: dict | None = None,
        **kwargs,
    ):
        super().__init__(content, status_code=status_code, headers=headers, **kwargs)

    def render(self, content: Any) -> bytes:
        return orjson.dumps(content)


class HealthChecker:
    @staticmethod
    def diogenes(base_url: str = "http://localhost:8888/") -> dict:
        try:
            scraper = DiogenesScraper(base_url=base_url)
            result = scraper.parse_word("lupus", "lat")
            if result.dg_parsed and len(result.chunks) > 0:
                return {"status": "healthy", "code": 200}
            else:
                return {
                    "status": "unhealthy",
                    "message": "Diogenes parsed but returned no valid chunks",
                }
        except requests.RequestException as e:
            return {"status": "error", "message": str(e)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def cltk() -> dict:
        try:
            import cltk.alphabet.lat as cltk_latchars  # noqa: PLC0415, F401
            import cltk.data.fetch as cltk_fetch  # noqa: PLC0415, F401
            import cltk.lemmatize.lat as cltk_latlem  # noqa: PLC0415, F401
            import cltk.lexicon.lat as cltk_latlex  # noqa: PLC0415, F401
            import cltk.phonology.lat.transcription as cltk_latscript  # noqa: PLC0415, F401
            from cltk.languages.utils import get_lang  # noqa: PLC0415, F401

            return {"status": "healthy"}
        except ImportError as e:
            return {"status": "missing", "message": f"CLTK module not installed: {e}"}

    @staticmethod
    def spacy() -> dict:
        try:
            import spacy  # noqa: PLC0415

            model_name = "grc_odycy_joint_sm"
            try:
                spacy.load(model_name)
                return {"status": "healthy", "model": model_name}
            except OSError as e:
                return {
                    "status": "missing",
                    "message": f"Spacy model '{model_name}' not installed: {e}",
                }
        except ImportError as e:
            return {"status": "missing", "message": f"Spacy module not installed: {e}"}

    @staticmethod
    def whitakers() -> dict:
        whitakers_path = Path.home() / ".local/bin/whitakers-words"
        if whitakers_path.exists() and whitakers_path.is_file():
            return {"status": "healthy"}
        else:
            return {
                "status": "missing",
                "message": "whitakers-words binary not found in ~/.local/bin",
            }

    @staticmethod
    def cdsl() -> dict:
        return {"status": "healthy"}

    @staticmethod
    def heritage() -> dict:
        try:
            config = HeritageConfig()
            morphology = HeritageMorphologyService(config)
            result = morphology.analyze("agni")
            if result and result.total_solutions > 0:
                return {"status": "healthy", "solutions": result.total_solutions}
            elif result:
                return {"status": "degraded", "message": "Heritage responding but no solutions"}
            else:
                return {"status": "unhealthy", "message": "No result from Heritage"}
        except Exception as e:
            return {"status": "unhealthy", "message": str(e)}


async def health_check(request: Request):
    try:
        if not hasattr(request.app.state, "wiring"):
            request.app.state.wiring = LangnetWiring()
    except Exception as e:
        return ORJsonResponse({"error": f"Startup failed: {str(e)}"}, status_code=503)
    try:
        health = {
            "diogenes": HealthChecker.diogenes(),
            "cltk": HealthChecker.cltk(),
            "spacy": HealthChecker.spacy(),
            "whitakers": HealthChecker.whitakers(),
            "cdsl": HealthChecker.cdsl(),
            "heritage": HealthChecker.heritage(),
        }
        overall = (
            "healthy" if all(h.get("status") == "healthy" for h in health.values()) else "degraded"
        )
        return ORJsonResponse({"status": overall, "components": health})
    except Exception as e:
        return ORJsonResponse({"error": str(e)}, status_code=500)


async def cache_stats_api(request: Request):
    try:
        if not hasattr(request.app.state, "wiring"):
            request.app.state.wiring = LangnetWiring()
        wiring: LangnetWiring = request.app.state.wiring
    except Exception as e:
        return ORJsonResponse({"error": f"Startup failed: {str(e)}"}, status_code=503)
    try:
        stats = wiring.engine.cache.get_stats()
        return ORJsonResponse(stats)
    except Exception as e:
        return ORJsonResponse({"error": str(e)}, status_code=500)


def _validate_query_params(lang, word):
    """Validate query parameters and return error message if invalid."""
    if not lang:
        return "Missing required parameter: l (language)"
    if not word:
        return "Missing required parameter: s (search term)"
    valid_languages = {"lat", "grc", "san", "grk"}
    if lang not in valid_languages:
        return f"Invalid language: {lang}. Must be one of: {', '.join(sorted(valid_languages))}"
    if lang == "grk":
        return None  # Will be normalized below
    if not str(word).strip():
        return "Search term cannot be empty"
    return None


async def query_api(request: Request):
    if request.method == "POST":
        form_data = await request.form()
        lang = form_data.get("l")
        word = form_data.get("s")
    else:
        lang = request.query_params.get("l")
        word = request.query_params.get("s")

    validation_error = _validate_query_params(lang, word)
    if validation_error:
        return ORJsonResponse({"error": validation_error}, status_code=400)

    if lang == "grk":
        lang = "grc"

    try:
        if not hasattr(request.app.state, "wiring"):
            request.app.state.wiring = LangnetWiring()
        wiring: LangnetWiring = request.app.state.wiring
    except Exception as e:
        return ORJsonResponse({"error": f"Startup failed: {str(e)}"}, status_code=503)
    try:
        result = wiring.engine.handle_query(lang, word)
        return ORJsonResponse(result)
    except Exception as e:
        return ORJsonResponse({"error": str(e)}, status_code=500)


routes = [
    Route("/api/q", query_api, methods=["GET", "POST"]),
    Route("/api/health", health_check),
    Route("/api/cache/stats", cache_stats_api),
]


def create_app() -> Starlette:
    app = Starlette(routes=routes)

    @app.on_event("startup")
    async def startup():
        start = time.perf_counter()
        try:
            app.state.wiring = LangnetWiring()
            elapsed = time.perf_counter() - start
            logger.info("wiring_initialized", duration_seconds=elapsed)
        except Exception as e:
            logger.error("wiring_initialization_failed", error=str(e))
            print(f"Failed to initialize wiring at startup: {e}")

    return app


app = create_app()
