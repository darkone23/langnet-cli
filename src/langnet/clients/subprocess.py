from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping

import sh

from .base import RawResponseEffect, _new_response_id

logger = logging.getLogger(__name__)


class SubprocessToolClient:
    """
    Wraps a local executable and emits stdout/stderr as a raw response effect.

    Uses the `sh` library for predictable shelling.
    """

    def __init__(self, tool: str, command: Iterable[str]) -> None:
        self.tool = tool
        self.command = list(command)

    def execute(
        self, call_id: str, endpoint: str = "", params: Mapping[str, str] | None = None
    ) -> RawResponseEffect:
        cmd = list(self.command)
        params = params or {}
        for key, value in params.items():
            cmd.append(f"{key}={value}")

        sh_cmd = sh.Command(cmd[0])
        result = sh_cmd(
            *cmd[1:], _ok_code=list(range(0, 256)), _encoding="utf-8", _decode_errors="ignore"
        )
        raw_out = result.stdout if hasattr(result, "stdout") else result
        body = raw_out if isinstance(raw_out, (bytes, bytearray)) else str(raw_out).encode("utf-8")
        status_code = result.exit_code if hasattr(result, "exit_code") else 0  # type: ignore[attr-defined]

        return RawResponseEffect(
            response_id=_new_response_id(),
            tool=self.tool,
            call_id=call_id,
            endpoint=endpoint or " ".join(cmd),
            status_code=status_code,
            content_type="text/plain",
            headers={},
            body=body if isinstance(body, (bytes, bytearray)) else str(body).encode("utf-8"),
        )
