from __future__ import annotations

from pathlib import Path
from typing import cast

import requests

from langnet.clients import (
    FileToolClient,
    HttpToolClient,
    RawResponseEffect,
    SubprocessToolClient,
)

HTTP_OK = 200


class _FakeResponse:
    def __init__(
        self, content: bytes, status_code: int = HTTP_OK, headers: dict[str, str] | None = None
    ):
        self.content = content
        self.status_code = status_code
        self.headers = headers or {"Content-Type": "text/plain"}


class _FakeSession:
    def __init__(self, response: _FakeResponse):
        self._response = response

    def get(self, endpoint, params=None):  # noqa: ANN001, D401
        return self._response

    def post(self, endpoint, data=None):  # noqa: ANN001, D401
        return self._response


def test_http_tool_client_emits_raw_response(tmp_path: Path) -> None:
    fake_response = _FakeResponse(b"ok", headers={"Content-Type": "application/json"})
    client = HttpToolClient(
        tool="dummy", session=cast(requests.Session, _FakeSession(fake_response))
    )
    effect = client.execute(call_id="call-1", endpoint="http://example.com", params={"q": "x"})

    assert isinstance(effect, RawResponseEffect)
    assert effect.tool == "dummy"
    assert effect.status_code == HTTP_OK
    assert effect.content_type == "application/json"
    assert effect.body == b"ok"


def test_file_tool_client_reads_bytes(tmp_path: Path) -> None:
    path = tmp_path / "sample.txt"
    path.write_text("hello", encoding="utf-8")
    client = FileToolClient(tool="file")
    effect = client.execute(call_id="call-file", endpoint=str(path))

    assert effect.status_code == HTTP_OK
    assert effect.body == b"hello"
    assert path.name in effect.endpoint


def test_subprocess_tool_client_captures_stdout() -> None:
    client = SubprocessToolClient(tool="echo", command=["/bin/sh", "-c", "echo hello"])
    effect = client.execute(call_id="call-echo")

    assert effect.status_code == 0
    assert effect.body.strip() == b"hello"
