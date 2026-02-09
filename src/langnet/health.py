from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import duckdb
import requests
import structlog

from langnet.config import LangnetSettings
from langnet.heritage.client import HeritageHTTPClient
from langnet.heritage.config import HeritageConfig
from langnet.types import JSONMapping

logger = structlog.get_logger(__name__)
HEALTHY_STATUS = 200
NOT_FOUND_STATUS = 404
DEGRADED_THRESHOLD = 500


@dataclass
class ComponentStatus:
    status: str
    message: str | None = None
    duration_ms: float | None = None
    details: JSONMapping | None = None

    def as_dict(self) -> JSONMapping:
        payload: JSONMapping = {"status": self.status}
        if self.message:
            payload["message"] = self.message
        if self.duration_ms is not None:
            payload["duration_ms"] = round(self.duration_ms, 3)
        if self.details:
            payload["details"] = self.details
        return payload


def _time_call(fn: Callable[[], ComponentStatus]) -> ComponentStatus:
    start = time.perf_counter()
    result = fn()
    result.duration_ms = (time.perf_counter() - start) * 1000
    return result


def check_diogenes(
    base_url: str,
    timeout: int,
    requester: Callable[..., requests.Response] = requests.get,
) -> ComponentStatus:
    def _check() -> ComponentStatus:
        url = base_url.rstrip("/") + "/Perseus.cgi"
        params = {"do": "parse", "lang": "lat", "q": "amo"}
        try:
            response = requester(url, params=params, timeout=timeout)
            if response.status_code == HEALTHY_STATUS:
                return ComponentStatus(
                    status="healthy", details={"status_code": response.status_code}
                )
            return ComponentStatus(
                status="degraded",
                message=f"HTTP {response.status_code} from Diogenes",
                details={"status_code": response.status_code},
            )
        except requests.Timeout as exc:
            return ComponentStatus(status="error", message=f"Diogenes timeout: {exc}")
        except requests.RequestException as exc:  # noqa: BLE001
            return ComponentStatus(status="unreachable", message=str(exc))

    return _time_call(_check)


def check_heritage(
    base_url: str,
    timeout: int,
    requester: Callable[..., requests.Response] = requests.get,
) -> ComponentStatus:
    def _check() -> ComponentStatus:
        config = HeritageConfig(base_url=base_url, timeout=timeout)
        client = HeritageHTTPClient(config)
        primary_url = client.build_cgi_url("sktsearch", {"q": "agni", "lex": "MW"})
        fallback_url = base_url.rstrip("/") + "/cgi-bin/sktsearch?q=agni&lex=MW"
        attempted: list[tuple[str, int | str]] = []

        for url in (primary_url, fallback_url):
            try:
                response = requester(url, timeout=timeout)
                status_code = int(getattr(response, "status_code", 0) or 0)
                attempted.append((url, status_code))
                if status_code == HEALTHY_STATUS:
                    return ComponentStatus(
                        status="healthy",
                        details={"status_code": status_code, "endpoint": url},
                    )
                if status_code == NOT_FOUND_STATUS:
                    continue
                level = "degraded" if status_code < DEGRADED_THRESHOLD else "error"
                return ComponentStatus(
                    status=level,
                    message=f"HTTP {status_code} from Heritage",
                    details={"status_code": status_code, "endpoint": url},
                )
            except requests.Timeout as exc:
                return ComponentStatus(status="error", message=f"Heritage timeout: {exc}")
            except requests.RequestException as exc:  # noqa: BLE001
                return ComponentStatus(status="unreachable", message=str(exc))

        return ComponentStatus(
            status="missing",
            message="sktsearch returned 404 for all known endpoints",
            details={"attempted": attempted},
        )

    return _time_call(_check)


def check_cdsl(db_dir: Path, dict_dir: Path | None = None) -> ComponentStatus:
    def _check() -> ComponentStatus:
        required_dbs = ["mw.db", "ap90.db"]
        missing = [name for name in required_dbs if not (db_dir / name).exists()]
        if missing:
            return ComponentStatus(
                status="missing",
                message=f"Missing CDSL indexes: {', '.join(sorted(missing))}",
            )

        try:
            conn = duckdb.connect(str(db_dir / "mw.db"), read_only=True)
            conn.execute("SELECT 1 FROM entries LIMIT 1").fetchone()
            conn.close()
        except Exception as exc:  # noqa: BLE001
            return ComponentStatus(status="error", message=f"CDSL index error: {exc}")

        details: JSONMapping = {"db_path": str(db_dir)}
        if dict_dir:
            details["dict_dir"] = str(dict_dir)

        return ComponentStatus(status="healthy", details=details)

    return _time_call(_check)


def check_cltk() -> ComponentStatus:
    def _check() -> ComponentStatus:
        try:
            import cltk  # noqa: PLC0415
            from cltk.languages.utils import get_lang  # noqa: PLC0415

            get_lang("lat")
            return ComponentStatus(
                status="healthy", details={"version": getattr(cltk, "__version__", "")}
            )
        except ImportError as exc:
            return ComponentStatus(status="missing", message=f"CLTK module not installed: {exc}")
        except Exception as exc:  # noqa: BLE001
            return ComponentStatus(status="degraded", message=f"CLTK issue: {exc}")

    return _time_call(_check)


def check_spacy(model_name: str = "grc_odycy_joint_sm") -> ComponentStatus:
    def _check() -> ComponentStatus:
        try:
            import spacy  # noqa: PLC0415

            try:
                spacy.load(model_name)
                return ComponentStatus(
                    status="healthy",
                    details={
                        "model": model_name,
                        "spacy_version": getattr(spacy, "__version__", ""),
                    },
                )
            except OSError as exc:
                return ComponentStatus(
                    status="missing",
                    message=f"spaCy model '{model_name}' not installed: {exc}",
                    details={"model": model_name},
                )
        except ImportError as exc:
            return ComponentStatus(status="missing", message=f"spaCy module not installed: {exc}")
        except Exception as exc:  # noqa: BLE001
            return ComponentStatus(status="degraded", message=f"spaCy issue: {exc}")

    return _time_call(_check)


def check_whitakers() -> ComponentStatus:
    def _check() -> ComponentStatus:
        binary_path = Path.home() / ".local/bin/whitakers-words"
        if binary_path.exists() and binary_path.is_file():
            return ComponentStatus(status="healthy", details={"path": str(binary_path)})
        return ComponentStatus(
            status="missing", message="whitakers-words binary not found in ~/.local/bin"
        )

    return _time_call(_check)


def check_cache(stats_provider: Callable[[], JSONMapping] | None = None) -> ComponentStatus:
    def _check() -> ComponentStatus:
        if stats_provider is None:
            return ComponentStatus(
                status="not_configured",
                message="Cache stats unavailable; wire a stats_provider to enable",
            )
        try:
            stats = stats_provider()
            return ComponentStatus(status="healthy", details=stats)
        except Exception as exc:  # noqa: BLE001
            return ComponentStatus(status="error", message=f"Cache stats error: {exc}")

    return _time_call(_check)


def overall_status(components: dict[str, ComponentStatus]) -> str:
    statuses = {name: comp.status for name, comp in components.items()}
    if any(status in {"error", "unreachable"} for status in statuses.values()):
        return "degraded"
    if any(status not in {"healthy"} for status in statuses.values()):
        return "degraded"
    return "healthy"


def run_health_checks(
    settings: LangnetSettings,
    cache_stats_provider: Callable[[], JSONMapping] | None = None,
    requester: Callable[..., requests.Response] = requests.get,
) -> JSONMapping:
    components = {
        "diogenes": check_diogenes(
            settings.diogenes_url, settings.http_timeout, requester=requester
        ),
        "cltk": check_cltk(),
        "spacy": check_spacy(),
        "whitakers": check_whitakers(),
        "cdsl": check_cdsl(settings.cdsl_db_dir, settings.cdsl_dict_dir),
        "heritage": check_heritage(
            settings.heritage_url, settings.http_timeout, requester=requester
        ),
        "cache": check_cache(cache_stats_provider),
    }
    return {
        "status": overall_status(components),
        "components": {name: comp.as_dict() for name, comp in components.items()},
    }
