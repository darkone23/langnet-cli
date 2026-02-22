from __future__ import annotations

from collections.abc import Mapping
import shutil
import time

from langnet.clients.subprocess import SubprocessToolClient

from langnet.clients.base import RawResponseEffect, _new_response_id


class StubToolClient:
    """
    Minimal stub client for fetch.* tools when no real client is available.
    """

    def __init__(self, tool: str, status_code: int = 204, content_type: str = "text/plain"):
        self.tool = tool
        self.status_code = status_code
        self.content_type = content_type

    def execute(
        self, call_id: str, endpoint: str, params: Mapping[str, str] | None = None
    ) -> RawResponseEffect:
        return RawResponseEffect(
            response_id=_new_response_id(),
            tool=self.tool,
            call_id=call_id,
            endpoint=endpoint,
            status_code=self.status_code,
            content_type=self.content_type,
            headers={},
            body=b"",
        )


def find_whitaker_binary() -> str | None:
    """
    Locate the whitakers-words binary on PATH.
    """
    for name in ["whitakers-words", "words"]:
        path = shutil.which(name)
        if path:
            return path
    return None


class CLTKFetchClient:
    """
    In-process client for fetch.cltk (Latin Lewis/IPA via CLTK).
    """

    def __init__(self) -> None:
        self.tool = "fetch.cltk"
        from cltk.lemmatize.lat import LatinBackoffLemmatizer  # noqa: PLC0415
        from cltk.lexicon.lat import LatinLewisLexicon  # noqa: PLC0415
        from cltk.phonology.lat.transcription import Transcriber  # noqa: PLC0415

        self._lemmatizer = LatinBackoffLemmatizer()
        self._lexicon = LatinLewisLexicon()
        self._transcriber = Transcriber("Classical", "Allen")

    def execute(
        self, call_id: str, endpoint: str, params: Mapping[str, str] | None = None
    ) -> RawResponseEffect:
        import orjson  # noqa: PLC0415

        word = (params or {}).get("word") or (params or {}).get("q") or ""
        start = time.time()
        lemma_pairs = self._lemmatizer.lemmatize([word]) or []
        lemma = lemma_pairs[0][1] if lemma_pairs and len(lemma_pairs[0]) > 1 else word
        lookup = self._lexicon.lookup(word) or self._lexicon.lookup(lemma) or ""
        lines = lookup if isinstance(lookup, list) else [lookup] if isinstance(lookup, str) else []
        ipa_list: list[str] = []
        try:
            ipa_list = self._transcriber.transcribe(word)
        except Exception:
            try:
                ipa_list = self._transcriber.transcribe(lemma)
            except Exception:
                ipa_list = []
        payload = {
            "word": word,
            "lemma": lemma,
            "ipa": ipa_list,
            "lewis_lines": lines,
        }
        duration_ms = int((time.time() - start) * 1000)
        return RawResponseEffect(
            response_id=_new_response_id(),
            tool=self.tool,
            call_id=call_id,
            endpoint=endpoint,
            status_code=200,
            content_type="application/json",
            headers={},
            body=orjson.dumps(payload),
            fetch_duration_ms=duration_ms,
        )


class WhitakerFetchClient:
    """
    Client wrapper for fetch.whitakers using the local whitakers-words binary.
    """

    def __init__(self, binary: str) -> None:
        self.binary = binary
        self.tool = "fetch.whitakers"

    def execute(
        self, call_id: str, endpoint: str, params: Mapping[str, str] | None = None
    ) -> RawResponseEffect:
        params = params or {}
        word = params.get("word") or params.get("q") or ""
        client = SubprocessToolClient(tool=self.tool, command=[self.binary, word])
        return client.execute(call_id=call_id, endpoint=endpoint, params=params)
