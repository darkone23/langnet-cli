from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from bs4 import BeautifulSoup

from langnet.clients.base import ToolClient
from langnet.normalizer.utils import strip_accents
from langnet.storage.effects_index import RawResponseIndex
from langnet.storage.extraction_index import ExtractionIndex


@dataclass
class DiogenesParseResult:
    matched: bool
    canonical: str | None
    lemmas: list[str]
    response_id: str
    extraction_id: str | None
    matches: list[str] = None  # type: ignore[assignment]


class DiogenesParseAdapter:
    """
    Fetches diogenes parse output (Latin) and derives canonical lemmas.
    """

    def __init__(
        self,
        client: ToolClient,
        raw_index: RawResponseIndex,
        extraction_index: ExtractionIndex,
        endpoint: str,
    ) -> None:
        self.client = client
        self.raw_index = raw_index
        self.extraction_index = extraction_index
        self.endpoint = endpoint.rstrip("?")

    def fetch(
        self, call_id: str, query: str, canonical_targets: Iterable[str]
    ) -> DiogenesParseResult:
        params = {"do": "parse", "lang": "lat", "q": query}
        effect = self.client.execute(call_id=call_id, endpoint=self._url(params), params=None)
        ref = self.raw_index.store(effect)

        lemmas = self._parse_lemmas(effect.body)
        targets_normalized = {strip_accents(t).lower() for t in canonical_targets}
        matches: list[str] = []
        for lemma in lemmas:
            if strip_accents(lemma).lower() in targets_normalized:
                matches.append(lemma)
        match = matches[0] if matches else None

        extraction_payload = {
            "lemmas": lemmas,
            "matched": match,
            "matches": matches,
            "targets": list(targets_normalized),
        }
        extraction_id = self.extraction_index.store(
            response=effect,
            kind="diogenes.parse",
            canonical=match or (list(targets_normalized)[0] if targets_normalized else None),
            payload=extraction_payload,
        )

        return DiogenesParseResult(
            matched=match is not None,
            canonical=match,
            lemmas=lemmas,
            response_id=ref.response_id,
            extraction_id=extraction_id,
            matches=matches,
        )

    def _url(self, params: Mapping[str, str]) -> str:
        segments = [f"{k}={v}" for k, v in params.items()]
        return f"{self.endpoint}?{'&'.join(segments)}"

    def _parse_lemmas(self, body: bytes) -> list[str]:
        lemmas: list[str] = []
        try:
            soup = BeautifulSoup(body, "html.parser")
            # Common diogenes parse pages have lemmas in <i> or bold tags.
            for tag in soup.find_all(["i", "b", "em", "strong"]):
                text = (tag.get_text() or "").strip()
                if text and re.match(r"^[A-Za-z]+$", text):
                    lemmas.append(text.lower())
            if not lemmas:
                text = soup.get_text(" ", strip=True)
                candidates = re.findall(r"Lemma[:\\s]+([A-Za-z]+)", text, flags=re.IGNORECASE)
                lemmas.extend([c.lower() for c in candidates])
        except Exception:
            pass
        seen = set()
        out = []
        for lemma in lemmas:
            if lemma not in seen:
                seen.add(lemma)
                out.append(lemma)
        return out
