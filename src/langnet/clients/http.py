from __future__ import annotations

import time
from collections.abc import Mapping

import requests

from .base import RawResponseEffect, _new_response_id


class HttpToolClient:
    """
    Simple HTTP client wrapper that emits RawResponseEffect.
    """

    def __init__(
        self, tool: str, method: str = "GET", session: requests.Session | None = None
    ) -> None:
        self.tool = tool
        self.method = method.upper()
        self.session = session or requests.Session()

    def execute(
        self, call_id: str, endpoint: str, params: Mapping[str, str] | None = None
    ) -> RawResponseEffect:
        params = params or {}
        start = time.perf_counter()
        response = (
            self.session.post(endpoint, data=params)
            if self.method == "POST"
            else self.session.get(endpoint, params=params)
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
