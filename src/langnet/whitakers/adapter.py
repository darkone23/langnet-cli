from __future__ import annotations

import logging
import re
import shutil
from dataclasses import dataclass

from langnet.clients.subprocess import SubprocessToolClient
from langnet.storage.effects_index import RawResponseIndex
from langnet.storage.extraction_index import ExtractionIndex

logger = logging.getLogger(__name__)


@dataclass
class WhitakerResult:
    lemmas: list[str]
    response_id: str | None
    extraction_id: str | None


class WhitakerAdapter:
    """
    Thin wrapper around the whitakers-words binary to obtain lemma candidates.
    """

    def __init__(
        self,
        raw_index: RawResponseIndex,
        extraction_index: ExtractionIndex,
        binary: str | None = None,
    ) -> None:
        self.raw_index = raw_index
        self.extraction_index = extraction_index
        self.binary = binary or self._find_binary()

    def available(self) -> bool:
        return self.binary is not None

    def _find_binary(self) -> str | None:
        for name in ["whitakers-words", "words"]:
            path = shutil.which(name)
            if path:
                return path
        logger.debug("whitakers_binary_not_found")
        return None

    def fetch(self, call_id: str, query: str) -> WhitakerResult:
        if not self.binary:
            return WhitakerResult(lemmas=[], response_id=None, extraction_id=None)

        client = SubprocessToolClient(tool="whitakers", command=[self.binary, query])
        effect = client.execute(call_id=call_id)
        ref = self.raw_index.store(effect)
        lemmas = self._parse_lemmas(effect.body.decode("utf-8", errors="ignore"))
        extraction_id = self.extraction_index.store(
            response=effect,
            kind="whitakers.search",
            canonical=lemmas[0] if lemmas else None,
            payload={"lemmas": lemmas},
        )
        return WhitakerResult(
            lemmas=lemmas, response_id=ref.response_id, extraction_id=extraction_id
        )

    def _parse_lemmas(self, text: str) -> list[str]:
        lemmas: list[str] = []
        for line in text.splitlines():
            m = re.match(r"^([a-zA-Z.]+)\\s+[A-Z]", line.strip())
            if m:
                lemma = m.group(1).replace(".", "")
                lemmas.append(lemma.lower())
        seen = set()
        out = []
        for lemma in lemmas:
            if lemma not in seen:
                seen.add(lemma)
                out.append(lemma)
        return out
