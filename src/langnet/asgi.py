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

from langnet.core import LangnetWiring


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
            from langnet.diogenes.core import DiogenesScraper

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
            import cltk.alphabet.lat as cltk_latchars
            import cltk.data.fetch as cltk_fetch
            import cltk.lemmatize.lat as cltk_latlem
            import cltk.lexicon.lat as cltk_latlex
            import cltk.phonology.lat.transcription as cltk_latscript
            from cltk.languages.utils import get_lang

            return {"status": "healthy"}
        except ImportError as e:
            return {"status": "missing", "message": f"CLTK module not installed: {e}"}

    @staticmethod
    def spacy() -> dict:
        try:
            import spacy

            model_name = "grc_odycy_joint_sm"
            try:
                nlp = spacy.load(model_name)
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
        from pathlib import Path

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
        return {
            "status": "healthy",
            "message": "CDSL integration pending implementation",
        }


async def health_check(request: Request):
    try:
        if not hasattr(request.app.state, "wiring"):
            request.app.state.wiring = LangnetWiring()
        wiring: LangnetWiring = request.app.state.wiring
    except Exception as e:
        return ORJsonResponse({"error": f"Startup failed: {str(e)}"}, status_code=503)
    try:
        health = {
            "diogenes": HealthChecker.diogenes(),
            "cltk": HealthChecker.cltk(),
            "spacy": HealthChecker.spacy(),
            "whitakers": HealthChecker.whitakers(),
            "cdsl": HealthChecker.cdsl(),
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


async def query_api(request: Request):
    if request.method == "POST":
        form_data = await request.form()
        lang = form_data.get("l")
        word = form_data.get("s")
    else:
        lang = request.query_params.get("l")
        word = request.query_params.get("s")

    if not lang:
        return ORJsonResponse(
            {"error": "Missing required parameter: l (language)"}, status_code=400
        )
    if not word:
        return ORJsonResponse(
            {"error": "Missing required parameter: s (search term)"}, status_code=400
        )

    valid_languages = {"lat", "grc", "san", "grk"}
    if lang not in valid_languages:
        return ORJsonResponse(
            {
                "error": f"Invalid language: {lang}. Must be one of: {', '.join(sorted(valid_languages))}"
            },
            status_code=400,
        )

    if lang == "grk":
        lang = "grc"

    word = str(word).strip() if word else ""
    if not word:
        return ORJsonResponse({"error": "Search term cannot be empty"}, status_code=400)

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
        import time

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
