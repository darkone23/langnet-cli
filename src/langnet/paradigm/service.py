from __future__ import annotations

import socket
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from http.client import BadStatusLine
from typing import Protocol
from urllib.parse import urlencode, urlparse, urlunparse

import requests

from langnet.paradigm.diogenes import parse_diogenes_inflect_html
from langnet.paradigm.grammar import ParadigmRequest
from langnet.paradigm.heritage import (
    parse_heritage_conjugation_html,
    parse_heritage_declension_html,
)
from langnet.paradigm.models import ParadigmPayload


class HttpResponse(Protocol):
    text: str
    ok: bool


HttpGet = Callable[[str, Mapping[str, str] | None], HttpResponse]
DEFAULT_HTTP_TIMEOUT_SECONDS = 30
RECV_CHUNK_SIZE = 65536


@dataclass(frozen=True)
class Http09Response:
    text: str
    ok: bool = True


class ParadigmService:
    def __init__(
        self,
        *,
        heritage_base: str = "http://localhost:48080",
        diogenes_endpoint: str = "http://localhost:8888/Perseus.cgi",
        http_get: HttpGet | None = None,
    ) -> None:
        self.heritage_base = heritage_base.rstrip("/")
        self.diogenes_endpoint = diogenes_endpoint
        self.http_get = http_get or _requests_get

    def fetch(self, request: ParadigmRequest) -> ParadigmPayload:
        if request.source == "heritage:sktdeclin":
            return self._fetch_heritage_declension(request)
        if request.source == "heritage:sktconjug":
            return self._fetch_heritage_conjugation(request)
        if request.source == "diogenes:inflect":
            return self._fetch_diogenes_inflect(request)
        msg = f"Unsupported paradigm source: {request.source}"
        raise ValueError(msg)

    def _fetch_heritage_declension(self, request: ParadigmRequest) -> ParadigmPayload:
        gender = request.options.get("gender")
        if not isinstance(gender, str) or not gender:
            msg = "Sanskrit Heritage declension requests require a gender option."
            raise ValueError(msg)
        url = (
            f"{self.heritage_base}/cgi-bin/skt/sktdeclin"
            f"?q={request.lemma};g={gender};font=roma;t=VH;lex=SH"
        )
        try:
            response = self.http_get(url, None)
        except Exception as exc:  # noqa: BLE001
            return _failed_payload(
                request,
                {"url": url, "params": {"q": request.lemma, "g": gender}},
                f"heritage_declension_request_failed: {type(exc).__name__}",
            )
        payload = parse_heritage_declension_html(
            response.text if response.ok else "",
            lemma=request.lemma,
            gender=gender,
            request_url=url,
        )
        if not response.ok:
            payload.warnings.append("heritage_declension_request_failed")
        return payload

    def _fetch_heritage_conjugation(self, request: ParadigmRequest) -> ParadigmPayload:
        present_class = request.options.get("class")
        if not isinstance(present_class, str) or not present_class:
            msg = "Sanskrit Heritage conjugation requests require a class option."
            raise ValueError(msg)
        url = (
            f"{self.heritage_base}/cgi-bin/skt/sktconjug"
            f"?q={request.lemma};c={present_class};font=roma;t=VH;lex=SH"
        )
        try:
            response = self.http_get(url, None)
        except Exception as exc:  # noqa: BLE001
            return _failed_payload(
                request,
                {"url": url, "params": {"q": request.lemma, "c": present_class}},
                f"heritage_conjugation_request_failed: {type(exc).__name__}",
            )
        payload = parse_heritage_conjugation_html(
            response.text if response.ok else "",
            root=request.lemma,
            present_class=present_class,
            request_url=url,
        )
        if not response.ok:
            payload.warnings.append("heritage_conjugation_request_failed")
        return payload

    def _fetch_diogenes_inflect(self, request: ParadigmRequest) -> ParadigmPayload:
        lang = "grk" if request.language == "grc" else request.language
        params = {"do": "inflect", "lang": lang, "q": request.lemma, "noheader": "1"}
        try:
            response = self.http_get(self.diogenes_endpoint, params)
        except Exception as exc:  # noqa: BLE001
            return _failed_payload(
                request,
                {"url": self.diogenes_endpoint, "params": params},
                f"diogenes_inflect_request_failed: {type(exc).__name__}",
            )
        payload = parse_diogenes_inflect_html(
            response.text if response.ok else "",
            language=request.language,
            lemma=request.lemma,
            kind=request.kind,
            request_url=self.diogenes_endpoint,
        )
        payload.source_request["params"] = params
        if not response.ok:
            payload.warnings.append("diogenes_inflect_request_failed")
        return payload


def _requests_get(url: str, params: Mapping[str, str] | None = None) -> HttpResponse:
    try:
        return requests.get(url, params=params, timeout=DEFAULT_HTTP_TIMEOUT_SECONDS)
    except requests.exceptions.ConnectionError as exc:
        if _is_bad_status_line(exc):
            return _http09_get(url, params)
        raise


def _is_bad_status_line(exc: BaseException) -> bool:
    if isinstance(exc, BadStatusLine):
        return True
    return any(_contains_bad_status_line(arg) for arg in exc.args)


def _contains_bad_status_line(value: object) -> bool:
    if isinstance(value, BadStatusLine):
        return True
    if isinstance(value, BaseException):
        return any(_contains_bad_status_line(arg) for arg in value.args)
    if isinstance(value, tuple):
        return any(_contains_bad_status_line(item) for item in value)
    return False


def _http09_get(url: str, params: Mapping[str, str] | None = None) -> Http09Response:
    request_url = _url_with_params(url, params)
    parsed = urlparse(request_url)
    host = parsed.hostname
    if host is None:
        msg = f"Cannot fetch URL without host: {url}"
        raise ValueError(msg)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if parsed.scheme == "https":
        msg = "HTTP/0.9 fallback only supports plain HTTP Diogenes endpoints."
        raise ValueError(msg)
    path = urlunparse(("", "", parsed.path or "/", parsed.params, parsed.query, ""))
    with socket.create_connection((host, port), timeout=DEFAULT_HTTP_TIMEOUT_SECONDS) as sock:
        sock.sendall(f"GET {path}\r\n\r\n".encode("ascii"))
        body = _recv_all(sock)
    return Http09Response(text=body.decode("utf-8", errors="replace"), ok=True)


def _url_with_params(url: str, params: Mapping[str, str] | None) -> str:
    if not params:
        return url
    parsed = urlparse(url)
    query = urlencode(params)
    merged_query = f"{parsed.query}&{query}" if parsed.query else query
    return urlunparse(parsed._replace(query=merged_query))


def _recv_all(sock: socket.socket) -> bytes:
    chunks: list[bytes] = []
    while True:
        chunk = sock.recv(RECV_CHUNK_SIZE)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def _failed_payload(
    request: ParadigmRequest, source_request: dict[str, object], warning: str
) -> ParadigmPayload:
    return ParadigmPayload(
        language=request.language,
        lemma=request.lemma,
        kind=request.kind,
        source=request.source,
        source_request=source_request,
        paradigms=[],
        warnings=[warning],
    )
