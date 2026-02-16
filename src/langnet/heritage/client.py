from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from heritage_spec import MonierWilliamsResult, SktSearchResult

from langnet.clients.base import ToolClient

from .config import HeritageConfig, heritage_config

HTTP_OK = 200

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SktSearchMatch:
    canonical: str  # Velthuis form from URL anchor
    display: str  # IAST form from <i> tag
    entry_url: str


class HeritageHTTPClient:
    """
    Minimal Heritage Platform client focused on canonicalization.

    This is a thin port of the codesketch implementation: it uses sktsearch to
    retrieve canonical Velthuis/Devanagari forms for bare ASCII/HK inputs.
    """

    def __init__(
        self,
        config: HeritageConfig | None = None,
        session: requests.Session | None = None,
        tool_client: ToolClient | None = None,
    ) -> None:
        self.config = config or heritage_config
        self.session = session or requests.Session()
        self._tool_client = tool_client

    def _build_url(self, script_name: str, params: Mapping[str, str] | None = None) -> str:
        base_url = self.config.base_url.rstrip("/")
        cgi_path = self.config.cgi_path.rstrip("/") + "/"
        url = urljoin(base_url, cgi_path + script_name)
        if params:
            filtered = {k: v for k, v in params.items() if v is not None}
            if filtered:
                param_string = "&".join([f"{k}={v}" for k, v in filtered.items()])
                url += "?" + param_string
        return url

    def fetch_canonical_sanskrit(self, query: str) -> MonierWilliamsResult:
        matches = self.fetch_all_matches(query)
        if not matches:
            return MonierWilliamsResult(
                original_query=query,
                bare_query=re.sub(r"[^a-zA-Z]", "", query.lower()),
                canonical_sanskrit="",
                match_method="not_found",
                entry_url="",
            )
        first = matches[0]
        return MonierWilliamsResult(
            original_query=query,
            bare_query=re.sub(r"[^a-zA-Z]", "", query.lower()),
            canonical_sanskrit=first.canonical,
            match_method="sktsearch",
            entry_url=first.entry_url,
        )

    def _get_response_text(self, url: str, call_id: str) -> str | None:
        """Fetch URL and return response text, using tool_client if available."""
        if self._tool_client is not None:
            try:
                effect = self._tool_client.execute(
                    call_id=call_id,
                    endpoint=url,
                    params={},
                )
                if effect.status_code == HTTP_OK:
                    return effect.body.decode("utf-8")
                return None
            except Exception as exc:
                logger.debug("heritage_http_failed", extra={"error": str(exc), "url": url})
                return None
        else:
            try:
                response = self.session.get(url, timeout=self.config.timeout)
                response.raise_for_status()
                return response.text
            except Exception as exc:
                logger.debug("heritage_sktsearch_failed", extra={"error": str(exc)})
                return None

    def fetch_all_matches(self, query: str) -> list[SktSearchMatch]:
        bare_query = re.sub(r"[^a-zA-Z]", "", query.lower())
        params = {"q": bare_query, "lex": "SH"}
        url = self._build_url("sktsearch", params)
        text = self._get_response_text(url, f"heritage-sktsearch-{bare_query}")
        if text is None:
            return []

        soup = BeautifulSoup(text, "html.parser")
        matches: list[SktSearchMatch] = []

        for link in soup.find_all("a", href=True):
            href = link.get("href")
            if not isinstance(href, str):
                continue
            if "/skt/MW" in href and "H_" in href:
                canonical = href.split("H_")[-1]
                display = canonical
                i_tag = link.find("i")
                if i_tag:
                    display = i_tag.get_text().strip()
                matches.append(SktSearchMatch(canonical=canonical, display=display, entry_url=href))

        return matches

    def fetch_canonical_via_sktsearch(self, query: str) -> SktSearchResult:
        matches = self.fetch_all_matches(query)
        if not matches:
            return SktSearchResult(
                original_query=query,
                bare_query=re.sub(r"[^a-zA-Z]", "", query.lower()),
                canonical_text="",
                canonical_sanskrit="",
                match_method="not_found",
                entry_url="",
            )
        first = matches[0]
        return SktSearchResult(
            original_query=query,
            bare_query=re.sub(r"[^a-zA-Z]", "", query.lower()),
            canonical_text=first.canonical,
            canonical_sanskrit=first.canonical,
            match_method="sktsearch",
            entry_url=first.entry_url,
        )
