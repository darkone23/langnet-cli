from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from .base import RawResponseEffect, _new_response_id


class FileToolClient:
    """
    Reads a local file and emits its content as a raw response effect.
    """

    def __init__(self, tool: str) -> None:
        self.tool = tool

    def execute(
        self, call_id: str, endpoint: str, params: Mapping[str, str] | None = None
    ) -> RawResponseEffect:
        path = Path(endpoint)
        data = path.read_bytes()

        return RawResponseEffect(
            response_id=_new_response_id(),
            tool=self.tool,
            call_id=call_id,
            endpoint=str(path),
            status_code=200,
            content_type="application/octet-stream",
            headers={},
            body=data,
        )
