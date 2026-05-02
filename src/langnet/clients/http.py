from __future__ import annotations

import os
import time
from collections.abc import Mapping

import requests

from .base import RawResponseEffect, _new_response_id


class HttpToolClient:
    """
    Simple HTTP client wrapper that emits RawResponseEffect.
    """

    def __init__(
        self,
        tool: str,
        method: str = "GET",
        session: requests.Session | None = None,
        timeout: float | None = None,
    ) -> None:
        self.tool = tool
        self.method = method.upper()
        self.session = session or requests.Session()
        self.timeout = timeout if timeout is not None else _default_timeout()

    def execute(
        self, call_id: str, endpoint: str, params: Mapping[str, str] | None = None
    ) -> RawResponseEffect:
        params = params or {}
        # Allow callers to supply a prebuilt query string (e.g., semicolon-delimited Heritage CGI).
        raw_query = params.get("__http_query")
        http_params = {k: v for k, v in params.items() if not k.startswith("__")}
        if raw_query is not None:
            # Do not send http_params when a raw query string is provided.
            http_params = {}
            endpoint = f"{endpoint}&{raw_query}" if "?" in endpoint else f"{endpoint}?{raw_query}"

        start = time.perf_counter()
        response = (
            self.session.post(endpoint, data=http_params, timeout=self.timeout)
            if self.method == "POST"
            else self.session.get(endpoint, params=http_params, timeout=self.timeout)
        )
        duration_ms = int((time.perf_counter() - start) * 1000)

        content_type = response.headers.get("Content-Type", "")
        return RawResponseEffect(
            response_id=_new_response_id(),
            tool=self.tool,
            call_id=call_id,
            endpoint=endpoint,
            status_code=response.status_code,
            content_type=content_type,
            headers=dict(response.headers),
            body=response.content,
            fetch_duration_ms=duration_ms,
        )


def _default_timeout() -> float:
    raw = os.getenv("LANGNET_HTTP_TIMEOUT_SECONDS", "10")
    try:
        return max(0.1, float(raw))
    except ValueError:
        return 10.0
