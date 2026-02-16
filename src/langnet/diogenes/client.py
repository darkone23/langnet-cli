from __future__ import annotations

import importlib
import re
import urllib.parse
from collections.abc import Mapping
from dataclasses import dataclass

from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag

from langnet.clients.base import ToolClient
from langnet.normalizer.utils import strip_accents


@dataclass(frozen=True)
class WordListResult:
    """Result from Diogenes word_list lookup (Greek)."""

    query: str
    lemmas: list[str]  # Accented lemmas from word_list
    matched: bool


@dataclass(frozen=True)
class ParseResult:
    """Result from Diogenes parse lookup (Latin/Greek)."""

    query: str
    lemmas: list[str]  # Lemmas from parse
    matched: bool


@dataclass(frozen=True)
class WordListEntry:
    """Intermediate representation of a parsed lemma."""

    lemma: str
    count: int
    order_weight: int


@dataclass(order=True)
class RankedLemma:
    """Sortable lemma ranking."""

    dist: int
    ratio_sort: float
    norm_len: int
    norm: str
    lemma: str


STOPWORDS = {
    "tll",
    "old",
    "pike",
    "that",
    "noun",
    "relative",
    "the",
    "quality",
}


def _normalize_for_distance(text: str) -> str:
    try:
        betacode = importlib.import_module("betacode")
        converter = getattr(betacode, "conv", None)
        if converter and hasattr(converter, "uni_to_beta"):
            beta = converter.uni_to_beta(text)
        else:
            beta = text
    except Exception:
        beta = text
    beta = re.sub(r"[^A-Za-z]", "", beta).lower()
    return beta or strip_accents(text).lower()


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i]
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            curr.append(min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost))
        prev = curr
    return prev[-1]


class DiogenesClient:
    """
    Simple Diogenes client for canonical form lookup.

    This client is "dumb" - it just fetches and parses, no storage.
    The full adapters (DiogenesWordListAdapter, DiogenesParseAdapter) handle
    storage for the pipeline.
    """

    def __init__(
        self, client: ToolClient, endpoint: str, parse_endpoint: str | None = None
    ) -> None:
        self.client = client
        self.endpoint = endpoint.rstrip("?")
        if parse_endpoint is None and endpoint.endswith("Diogenes.cgi"):
            parse_endpoint = endpoint.replace("Diogenes.cgi", "Perseus.cgi")
        self.parse_endpoint = (parse_endpoint or endpoint).rstrip("?")

    def _url(self, params: Mapping[str, str]) -> str:
        segments = [f"{k}={urllib.parse.quote_plus(v)}" for k, v in params.items()]
        return f"{self.endpoint}?{'&'.join(segments)}"

    def _parse_url(self, params: Mapping[str, str]) -> str:
        segments = [f"{k}={urllib.parse.quote_plus(v)}" for k, v in params.items()]
        return f"{self.parse_endpoint}?{'&'.join(segments)}"

    def fetch_word_list(self, query: str, limit: int = 50) -> WordListResult:
        """Fetch word_list for Greek queries."""
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
        effect = self.client.execute(
            call_id=f"diogenes-wordlist-{query}",
            endpoint=self._url(params),
            params=None,
        )
        lemmas = self._parse_word_list(effect.body, query, limit)
        return WordListResult(
            query=query,
            lemmas=lemmas,
            matched=len(lemmas) > 0,
        )

    def fetch_parse(self, query: str, lang: str = "lat") -> ParseResult:
        """Fetch parse for Latin/Greek queries."""
        params = {
            "JumpToFromPerseus": "",
            "JumpFromQuery": "",
            "JumpFromLang": "",
            "JumpFromAction": "",
            "externalPdfViewer": "true",
            "externalDict": "",
            "englishDict": "",
            "action": "parse",
            "splash": "true",
            "xml-export-dir": "",
            "lang": lang,
            "q": query,
            "do": "parse",
            "current_pageXXstate": "splash",
        }
        effect = self.client.execute(
            call_id=f"diogenes-parse-{query}",
            endpoint=self._parse_url(params),
            params=None,
        )
        lemmas = self._parse_parse_output(effect.body, query)
        return ParseResult(
            query=query,
            lemmas=lemmas,
            matched=len(lemmas) > 0,
        )

    def _parse_word_list(self, body: bytes, query: str, limit: int | None) -> list[str]:
        """Parse lemmas from word_list HTML response."""
        soup = self._build_soup(body)
        if soup is None:
            return []
        checkboxes = self._checkbox_inputs(soup)
        entries = self._collect_word_list_entries(checkboxes)
        merged = self._merge_word_list(entries)
        ranked = self._rank_word_list(query, merged)
        if limit is not None and len(ranked) > limit:
            return ranked[:limit]
        return ranked

    def _build_soup(self, body: bytes) -> BeautifulSoup | None:
        try:
            html = body.decode("utf-8", errors="ignore")
            return BeautifulSoup(html, "html.parser")
        except Exception:
            return None

    def _checkbox_inputs(self, soup: BeautifulSoup) -> list[Tag]:
        return [inp for inp in soup.find_all("input") if inp.get("type") == "checkbox"]

    def _collect_word_list_entries(self, checkboxes: list[Tag]) -> list[WordListEntry]:
        order_weight = len(checkboxes)
        entries: list[WordListEntry] = []
        for checkbox in checkboxes:
            entry = self._extract_word_list_entry(checkbox, order_weight)
            if entry:
                entries.append(entry)
            order_weight -= 1
        return entries

    def _extract_word_list_entry(self, checkbox: Tag, order_weight: int) -> WordListEntry | None:
        lemma, count = self._lemma_from_parent(checkbox)
        if not lemma:
            lemma, count = self._lemma_from_label(checkbox)
        cleaned = self._clean_lemma_text(lemma)
        if not cleaned:
            return None
        return WordListEntry(cleaned, count, order_weight)

    def _lemma_from_parent(self, checkbox: Tag) -> tuple[str, int]:
        parent = checkbox.parent
        if not isinstance(parent, Tag):
            return ("", 0)
        cells = parent.find_all("td") if parent.name == "tr" else [parent]
        for cell in cells:
            text = cell.get_text(" ", strip=True)
            count = self._extract_count(text)
            link_text = self._link_text(cell)
            if link_text:
                return (link_text, count)
        return ("", 0)

    def _link_text(self, cell: Tag) -> str:
        for anchor in cell.find_all("a"):
            link_text = (anchor.get_text() or "").strip()
            if link_text and re.search(r"[a-zA-Zα-ωά-ώ]", link_text):
                return link_text
        return ""

    def _lemma_from_label(self, checkbox: Tag) -> tuple[str, int]:
        sibling = checkbox.next_sibling
        label_text = ""
        if isinstance(sibling, NavigableString):
            label_text = sibling.strip()
        elif isinstance(sibling, Tag):
            label_text = (sibling.get_text() or "").strip()
        checkbox_value = checkbox.get("value")
        value_text = (
            checkbox_value.strip() if isinstance(checkbox_value, str) else str(checkbox_value or "")
        )
        label_text = label_text or value_text
        if not label_text:
            return ("", 0)
        count = self._extract_count(label_text)
        label = self._strip_count_suffix(label_text)
        return (label, count)

    def _extract_count(self, text: str) -> int:
        match = re.search(r"\((\d+)\)\s*$", text)
        return int(match.group(1)) if match else 0

    def _strip_count_suffix(self, text: str) -> str:
        match = re.search(r"\((\d+)\)\s*$", text)
        if match:
            return text[: match.start()].strip()
        return text.strip()

    def _clean_lemma_text(self, lemma: str) -> str:
        cleaned = re.sub(r"^[^a-zA-Zα-ωά-ώ]+|[^a-zA-Zα-ωά-ώ]+$", "", lemma)
        if cleaned and re.search(r"[a-zA-Zα-ωά-ώ]", cleaned):
            return cleaned
        return ""

    def _merge_word_list(self, entries: list[WordListEntry]) -> dict[str, tuple[int, int]]:
        merged: dict[str, tuple[int, int]] = {}
        for entry in entries:
            if entry.lemma in merged:
                prev_count, prev_order = merged[entry.lemma]
                merged[entry.lemma] = (
                    max(prev_count, entry.count),
                    max(prev_order, entry.order_weight),
                )
            else:
                merged[entry.lemma] = (entry.count, entry.order_weight)
        return merged

    def _rank_word_list(
        self, query: str, lemmas_with_counts: dict[str, tuple[int, int]]
    ) -> list[str]:
        """
        Rank lemmas by: distance (primary), frequency ratio (tie-break),
        length/lexicographic (secondary).
        """

        target_norm = _normalize_for_distance(query)
        total = sum(v[0] for v in lemmas_with_counts.values())
        ranked: list[RankedLemma] = []
        for lemma, (count, _order_weight) in lemmas_with_counts.items():
            norm = _normalize_for_distance(lemma)
            dist = _levenshtein(norm, target_norm)
            ratio = (count / total) if total else 0.0
            ranked.append(
                RankedLemma(
                    dist=dist,
                    ratio_sort=-ratio,
                    norm_len=len(norm),
                    norm=norm,
                    lemma=lemma,
                )
            )

        ranked.sort()
        return [r.lemma for r in ranked]

    def _parse_parse_output(self, body: bytes, query: str) -> list[str]:
        """Parse lemmas from parse HTML response."""
        soup = self._build_soup(body)
        if soup is None:
            return []
        lemmas = self._collect_parse_lemmas(soup)
        return self._prioritize_parse_results(lemmas, query)

    def _collect_parse_lemmas(self, soup: BeautifulSoup) -> list[str]:
        lemmas: list[str] = []
        lemmas.extend(self._headword_candidates(soup))
        lemmas.extend(self._header_candidates(soup))
        lemmas.extend(self._fallback_candidates(soup))
        return lemmas

    def _headword_candidates(self, soup: BeautifulSoup) -> list[str]:
        candidates: list[str] = []
        for header in soup.find_all("h2"):
            text = (header.get_text() or "").strip()
            if not text:
                continue
            head = strip_accents(text.split()[0]).lower()
            if head:
                candidates.append(head)
        return candidates

    def _header_candidates(self, soup: BeautifulSoup) -> list[str]:
        header = soup.find("h1")
        if not header:
            return []
        text = (header.get_text() or "").strip()
        if "analysis" not in text.lower():
            return []
        parts = re.sub(r".*analysis(?:es)? of", "", text, flags=re.IGNORECASE)
        parts = parts.replace(":", "").strip()
        if not parts:
            return []
        return [strip_accents(parts).lower()]

    def _fallback_candidates(self, soup: BeautifulSoup) -> list[str]:
        text = soup.get_text(" ", strip=True)
        candidates = re.findall(r"Lemma[:\s]+([A-Za-z]+)", text, flags=re.IGNORECASE)
        return [c.lower() for c in candidates]

    def _prioritize_parse_results(self, lemmas: list[str], query: str) -> list[str]:
        seen: set[str] = set()
        cleaned: list[str] = []
        for lemma in lemmas:
            if lemma in STOPWORDS or lemma in seen:
                continue
            seen.add(lemma)
            cleaned.append(lemma)

        target = strip_accents(query).lower()

        def score(lemma: str) -> tuple[int, int]:
            dist = abs(len(lemma) - len(target))
            exact = 1 if strip_accents(lemma).lower() == target else 0
            return (exact * 10 - dist, -len(lemma))

        cleaned.sort(key=score, reverse=True)
        return cleaned[:3] if cleaned else []
