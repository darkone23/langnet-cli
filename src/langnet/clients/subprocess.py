from __future__ import annotations

import importlib
import logging
from collections.abc import Iterable, Mapping

from .base import RawResponseEffect, _new_response_id

logger = logging.getLogger(__name__)


class SubprocessToolClient:
    """
    Wraps a local executable and emits stdout/stderr as a raw response effect.

    Prefers the `sh` library for predictable shelling; falls back to stdlib
    subprocess if unavailable.
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

        try:
            sh_module = importlib.import_module("sh")
            sh_command = sh_module.Command(cmd[0])
            result = sh_command(*cmd[1:], _ok_code=list(range(0, 256)), _encoding=None)
            body = result.stdout if hasattr(result, "stdout") else bytes(result)  # type: ignore[arg-type]
            status_code = result.exit_code if hasattr(result, "exit_code") else 0  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001
            logger.debug("sh_subprocess_unavailable_fallback", extra={"error": str(exc)})
            subprocess = importlib.import_module("subprocess")
            proc = subprocess.run(cmd, capture_output=True, check=False)
            body = proc.stdout if proc.stdout else proc.stderr
            status_code = proc.returncode

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
