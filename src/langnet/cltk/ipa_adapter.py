from __future__ import annotations

import importlib
import json
import logging
import uuid
from collections.abc import Callable
from typing import Protocol

from langnet.clients.base import RawResponseEffect, _new_response_id
from langnet.clients.cltk import CLTKService
from langnet.storage.effects_index import RawResponseIndex
from langnet.storage.extraction_index import ExtractionIndex

logger = logging.getLogger(__name__)


class TranscriberProtocol(Protocol):
    def transcribe(self, text: str) -> str: ...


class CLTKIPAAdapter:
    """
    Produces IPA (or phonetic transcription) via CLTK where available.
    """

    _LATIN_TRANSCRIBER_PATH = "cltk.phonology.lat.transcription"
    _GREEK_TRANSCRIBER_PATH = "cltk.phonology.grc.transcription"

    def __init__(
        self,
        service: CLTKService | None,
        raw_index: RawResponseIndex,
        extraction_index: ExtractionIndex,
    ) -> None:
        self.service = service or CLTKService()
        self.raw_index = raw_index
        self.extraction_index = extraction_index

    def lookup(self, language: str, word: str) -> str | None:
        try:
            ipa = self._transcribe(language, word)
        except Exception as exc:  # noqa: BLE001
            logger.debug("cltk_ipa_failed", extra={"error": str(exc), "lang": language})
            return None

        if not ipa:
            return None

        effect = RawResponseEffect(
            response_id=_new_response_id(),
            tool="cltk",
            call_id=f"cltk-ipa-{uuid.uuid4()}",
            endpoint=f"cltk://ipa/{language}",
            status_code=0,
            content_type="application/json",
            headers={},
            body=json.dumps({"word": word, "ipa": ipa}).encode("utf-8"),
        )
        self.raw_index.store(effect)
        self.extraction_index.store(
            response=effect,
            kind="cltk.ipa",
            canonical=word,
            payload={"ipa": ipa, "language": language},
        )
        return ipa

    def _transcribe(self, language: str, word: str) -> str | None:
        factory = self._transcriber_factory(language)
        if factory is None:
            return None
        try:
            transcriber = factory()
            return transcriber.transcribe(word)
        except Exception:
            return None

    def _transcriber_factory(self, language: str) -> Callable[[], TranscriberProtocol] | None:
        if language == "lat":
            return self._latin_transcriber
        if language == "grc":
            return self._greek_transcriber
        return None

    def _latin_transcriber(self) -> TranscriberProtocol:
        module = importlib.import_module(self._LATIN_TRANSCRIBER_PATH)
        transcriber_cls = getattr(module, "Transcriber")
        return transcriber_cls("Classical", "Allen")

    def _greek_transcriber(self) -> TranscriberProtocol:
        module = importlib.import_module(self._GREEK_TRANSCRIBER_PATH)
        transcriber_cls = getattr(module, "Transcriber")
        return transcriber_cls(accent=False)
