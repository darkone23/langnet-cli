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
class DiogenesWordListResult:
    matched: bool
    canonical: str | None
    lemmas: list[str]
    response_id: str
    extraction_id: str | None
    all_candidates: list[str] = None  # type: ignore[assignment]
    matches: list[str] = None  # type: ignore[assignment]


class DiogenesWordListAdapter:
    """
    Fetches diogenes word_list output and marks canonical match if accentless lemma matches target.
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
    ) -> DiogenesWordListResult:
        # diogenes expects semicolon params in URL
        params = {
            "JumpToFromPerseus": "",
            "JumpFromQuery": "",
            "JumpFromLang": "",
            "JumpFromAction": "",
            "externalPdfViewer": "true",
            "externalDict": "",
            "englishDict": "",
            "action": "word_list",
            "splash": "true",
            "xml-export-dir": "",
            "corpus": "TLG Texts",
            "query": query,
            "current_pageXXstate": "splash",
        }
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
            kind="diogenes.word_list",
            canonical=match or (list(targets_normalized)[0] if targets_normalized else None),
            payload=extraction_payload,
        )

        return DiogenesWordListResult(
            matched=match is not None,
            canonical=match,
            lemmas=lemmas,
            response_id=ref.response_id,
            extraction_id=extraction_id,
            all_candidates=lemmas,
            matches=matches,
        )

    def _url(self, params: Mapping[str, str]) -> str:
        segments = [f"{k}={v}" for k, v in params.items()]
        return f"{self.endpoint}?{'&'.join(segments)}"

    def _parse_lemmas(self, body: bytes) -> list[str]:
        lemmas: list[str] = []
        try:
            soup = BeautifulSoup(body, "html.parser")
            for a in soup.find_all("a"):
                text = (a.get_text() or "").strip()
                if text:
                    lemmas.append(text)
            if not lemmas:
                # Fallback: grab words from the body text, keeping Greek letters.
                text = soup.get_text(" ", strip=True)
                words = re.findall(r"[\\wάέήίόύώϊΐϋΰἀ-῾]+", text)
                lemmas.extend(words)
        except Exception:
            pass
        # Deduplicate while preserving order
        seen = set()
        out = []
        for lemma in lemmas:
            if lemma not in seen:
                seen.add(lemma)
                out.append(lemma)
        return out
