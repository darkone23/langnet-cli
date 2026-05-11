from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from http.client import BadStatusLine
from unittest.mock import patch

import requests
import urllib3

from langnet.paradigm import service as paradigm_service
from langnet.paradigm.grammar import ParadigmRequest
from langnet.paradigm.service import ParadigmService
from tests.test_paradigm_parsers import (
    DIOGENES_GREEK_LOGOS_INFLECT,
    HERITAGE_GAM_CONJUGATION,
    HERITAGE_PUTRA_DECLENSION,
)


@dataclass(frozen=True)
class FakeResponse:
    text: str
    ok: bool = True


class FakeHttpGet:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.calls: list[tuple[str, Mapping[str, str] | None]] = []

    def __call__(self, url: str, params: Mapping[str, str] | None = None) -> FakeResponse:
        self.calls.append((url, params))
        return self.response


class RaisingHttpGet:
    def __call__(self, url: str, params: Mapping[str, str] | None = None) -> FakeResponse:
        raise RuntimeError("service unavailable")


def test_service_fetches_heritage_declension_from_resolved_request() -> None:
    fake_get = FakeHttpGet(FakeResponse(HERITAGE_PUTRA_DECLENSION))
    service = ParadigmService(heritage_base="http://heritage.local", http_get=fake_get)

    payload = service.fetch(
        ParadigmRequest(
            source="heritage:sktdeclin",
            language="san",
            lemma="putra",
            kind="declension",
            options={"gender": "Mas"},
        )
    )

    assert fake_get.calls[0][0] == (
        "http://heritage.local/cgi-bin/skt/sktdeclin?q=putra;g=Mas;font=roma;t=VH;lex=SH"
    )
    assert payload.paradigms[0].slots[5].forms[0].text == "putrāṇām"


def test_service_fetches_diogenes_greek_with_grk_language_parameter() -> None:
    fake_get = FakeHttpGet(FakeResponse(DIOGENES_GREEK_LOGOS_INFLECT))
    service = ParadigmService(
        diogenes_endpoint="http://diogenes.local/Perseus.cgi", http_get=fake_get
    )

    payload = service.fetch(
        ParadigmRequest(
            source="diogenes:inflect",
            language="grc",
            lemma="lo/gos",
            kind="declension",
            options={},
        )
    )

    assert fake_get.calls[0] == (
        "http://diogenes.local/Perseus.cgi",
        {"do": "inflect", "lang": "grk", "q": "lo/gos", "noheader": "1"},
    )
    assert payload.paradigms[0].slots[2].forms[0].text == "λόγῳ"


def test_service_fetches_heritage_conjugation_from_resolved_request() -> None:
    fake_get = FakeHttpGet(FakeResponse(HERITAGE_GAM_CONJUGATION))
    service = ParadigmService(heritage_base="http://heritage.local", http_get=fake_get)

    payload = service.fetch(
        ParadigmRequest(
            source="heritage:sktconjug",
            language="san",
            lemma="gam",
            kind="conjugation",
            options={"class": "1"},
        )
    )

    assert fake_get.calls[0][0] == (
        "http://heritage.local/cgi-bin/skt/sktconjug?q=gam;c=1;font=roma;t=VH;lex=SH"
    )
    assert payload.paradigms[0].slots[0].forms[0].text == "gacchāmi"


def test_service_returns_warning_payload_when_source_request_raises() -> None:
    service = ParadigmService(http_get=RaisingHttpGet())

    payload = service.fetch(
        ParadigmRequest(
            source="diogenes:inflect",
            language="lat",
            lemma="amo",
            kind="conjugation",
            options={},
        )
    )

    assert payload.paradigms == []
    assert payload.warnings == ["diogenes_inflect_request_failed: RuntimeError"]


def test_default_http_get_falls_back_for_diogenes_http09_body() -> None:
    def raise_bad_status(*args: object, **kwargs: object) -> object:
        raise requests.exceptions.ConnectionError(BadStatusLine("<span>body</span>"))

    with (
        patch.object(paradigm_service.requests, "get", raise_bad_status),
        patch.object(
            paradigm_service,
            "_http09_get",
            return_value=paradigm_service.Http09Response(text="fallback body", ok=True),
        ) as fallback,
    ):
        response = paradigm_service._requests_get(
            "http://diogenes.local/Perseus.cgi",
            {"do": "inflect", "lang": "lat", "q": "amo"},
        )

    assert response.text == "fallback body"
    fallback.assert_called_once()


def test_default_http_get_detects_nested_protocol_bad_status_line() -> None:
    def raise_nested_bad_status(*args: object, **kwargs: object) -> object:
        protocol_error = urllib3.exceptions.ProtocolError(
            "Connection aborted.",
            BadStatusLine("<span>body</span>"),
        )
        raise requests.exceptions.ConnectionError(protocol_error)

    with (
        patch.object(paradigm_service.requests, "get", raise_nested_bad_status),
        patch.object(
            paradigm_service,
            "_http09_get",
            return_value=paradigm_service.Http09Response(text="nested fallback", ok=True),
        ) as fallback,
    ):
        response = paradigm_service._requests_get(
            "http://diogenes.local/Perseus.cgi",
            {"do": "inflect", "lang": "lat", "q": "amo"},
        )

    assert response.text == "nested fallback"
    fallback.assert_called_once()
