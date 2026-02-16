from __future__ import annotations

import time
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class RawResponseEffect:
    """
    Transport-level response emitted by a tool client.

    This is an effect record only; higher layers will extract/derive.
    """

    response_id: str
    tool: str
    call_id: str
    endpoint: str
    status_code: int
    content_type: str
    headers: Mapping[str, str]
    body: bytes
    received_at: float = field(default_factory=time.time)


class ToolClient(Protocol):
    """
    Minimal interface for dumb tool clients.
    """

    tool: str

    def execute(
        self, call_id: str, endpoint: str, params: Mapping[str, str] | None = None
    ) -> RawResponseEffect: ...  # pragma: no cover


def _new_response_id() -> str:
    return str(uuid.uuid4())
