from __future__ import annotations

"""
Lightweight Heritage HTML extractor (ported from codesketch).

Extracts solution blocks with [word]{analysis} patterns, attached navy links
(dictionary URLs), CSS color hints, and span segments between solution markers.
"""

import re
from dataclasses import dataclass
from typing import TypedDict

from bs4 import BeautifulSoup, Tag


class MorphologyPattern(TypedDict):
    word: str
    analysis: str
    dictionary_url: str | None


class MorphologySegment(TypedDict, total=False):
    css_class: str | None
    text: str


class MorphologySolution(TypedDict, total=False):
    solution_number: int
    patterns: list[MorphologyPattern]
    color: str | None
    raw_text: str
    segments: list[MorphologySegment]


@dataclass
class _PatternEntry:
    word: str
    analysis: str
    raw_text: str
    url: str | None = None


class HeritageHTMLExtractor:
    """
    Extract patterns/segments from Heritage morphology HTML.
    Mirrors the codesketch extractor but trimmed for current handler needs.
    """

    _pattern_re = re.compile(r"\[([^\]]+)\]\{([^}]+)\}")
    _metadata_re = [
        re.compile(r"solutions?\s+kept", re.I),
        re.compile(r"filtering\s+efficiency", re.I),
        re.compile(r"additional\s+candidate", re.I),
        re.compile(r"^\d+$"),
        re.compile(r"^\d+%$"),
        re.compile(r"%$"),
    ]

    def extract(self, html: str) -> list[MorphologySolution]:
        soup = BeautifulSoup(html, "html.parser")
        solutions = self._extract_solution_blocks(soup)
        if solutions:
            return solutions
        loose = self._extract_loose_patterns(soup)
        if loose:
            raw_text = "\n".join(entry.raw_text for entry in loose)
            patterns = [
                {"word": p.word, "analysis": p.analysis, "dictionary_url": p.url} for p in loose
            ]
            return [
                {
                    "solution_number": 1,
                    "patterns": patterns,
                    "color": None,
                    "raw_text": raw_text,
                    "segments": [],
                }
            ]
        return []

    def _extract_solution_blocks(self, soup) -> list[MorphologySolution]:
        blocks: list[MorphologySolution] = []
        for span in soup.find_all("span"):
            text = span.get_text()
            if not text or "Solution" not in text:
                continue
            match = re.search(r"Solution\s*(\d+)", text)
            if not match:
                continue
            solution_number = int(match.group(1))
            table = self._find_solution_table(span)
            next_solution = self._find_next_solution_marker(span)
            patterns = self._collect_all_patterns(span, table, next_solution)
            segments = self._collect_segments(span, next_solution)
            if not patterns:
                continue
            deduped = self._deduplicate(patterns)
            raw_text = self._build_raw_text(deduped, segments)
            blocks.append(
                {
                    "solution_number": solution_number,
                    "patterns": [
                        {"word": p.word, "analysis": p.analysis, "dictionary_url": p.url}
                        for p in deduped
                    ],
                    "color": self._table_color(table),
                    "raw_text": raw_text,
                    "segments": segments,
                }
            )
        return blocks

    @staticmethod
    def _deduplicate(patterns: list[_PatternEntry]) -> list[_PatternEntry]:
        seen: set[str] = set()
        deduped: list[_PatternEntry] = []
        for p in patterns:
            key = f"{p.word}||{p.analysis}"
            if key in seen:
                continue
            seen.add(key)
            deduped.append(p)
        return deduped

    @staticmethod
    def _build_raw_text(patterns: list[_PatternEntry], segments: list[MorphologySegment]) -> str:
        if patterns:
            return "\n".join(p.raw_text for p in patterns)
        return " ".join(seg.get("text", "") for seg in segments if seg.get("text"))

    def _collect_all_patterns(
        self, start_span: Tag, table, next_solution: Tag | None
    ) -> list[_PatternEntry]:
        patterns = self._collect_patterns(table) if table else []
        patterns.extend(self._collect_patterns_between(start_span, next_solution))
        if not patterns:
            patterns.extend(self._collect_inline_patterns(start_span, next_solution))
        return patterns

    def _collect_patterns_between(
        self, start_span: Tag, next_solution: Tag | None
    ) -> list[_PatternEntry]:
        patterns: list[_PatternEntry] = []
        seen: set[str] = set()
        current = start_span.next_sibling
        while current and current != next_solution:
            if getattr(current, "find_all", None):
                for span in current.find_all("span", class_="latin12"):
                    entry = self._extract_pattern_from_span(span)
                    if not entry:
                        continue
                    key = f"{entry.word}||{entry.analysis}"
                    if key in seen:
                        continue
                    seen.add(key)
                    patterns.append(entry)
            current = current.next_sibling
        return patterns

    def _collect_inline_patterns(
        self, start_span: Tag, next_solution: Tag | None
    ) -> list[_PatternEntry]:
        patterns: list[_PatternEntry] = []
        seen: set[str] = set()
        current = start_span.next_sibling
        while current and current != next_solution:
            if getattr(current, "name", None) == "span" and "latin12" in (current.get("class") or []):
                entry = self._extract_pattern_from_span(current)
                if entry:
                    key = f"{entry.word}||{entry.analysis}"
                    if key not in seen:
                        seen.add(key)
                        patterns.append(entry)
            current = current.next_sibling
        return patterns

    def _collect_patterns(self, container) -> list[_PatternEntry]:
        if container is None:
            return []
        patterns: list[_PatternEntry] = []
        seen: set[str] = set()
        for span in container.find_all("span", class_="latin12"):
            entry = self._extract_pattern_from_span(span)
            if not entry:
                continue
            key = f"{entry.word}||{entry.analysis}"
            if key in seen:
                continue
            seen.add(key)
            patterns.append(entry)
        return patterns

    def _collect_segments(
        self, start_span: Tag, next_solution: Tag | None
    ) -> list[MorphologySegment]:
        segments: list[MorphologySegment] = []

        def collect_from(node):
            if getattr(node, "name", None) == "span":
                text = node.get_text(strip=True)
                if self._is_metadata(text):
                    return
                segments.append({"css_class": (node.get("class") or [None])[0], "text": text})
            for child in getattr(node, "children", []) or []:
                if child == next_solution:
                    return
                collect_from(child)

        current = start_span.next_sibling
        while current and current != next_solution:
            collect_from(current)
            current = current.next_sibling
        return segments

    def _extract_pattern_from_span(self, span) -> _PatternEntry | None:
        span_text = span.get_text(strip=True)
        match = self._pattern_re.search(span_text)
        if not match:
            return None
        word = match.group(1).strip()
        analysis = match.group(2).strip()
        url: str | None = None
        for link in span.find_all("a", class_="navy"):
            href = link.get("href")
            if href and isinstance(href, str):
                url = href
                break
        return _PatternEntry(word, analysis, match.group(0), url)

    def _extract_loose_patterns(self, soup) -> list[_PatternEntry]:
        patterns: list[_PatternEntry] = []
        seen: set[str] = set()
        for table in self._get_innermost_pattern_tables(soup):
            for entry in self._collect_patterns(table):
                key = f"{entry.word}||{entry.analysis}"
                if key in seen:
                    continue
                seen.add(key)
                patterns.append(entry)
        if not patterns:
            for span in soup.find_all("span", class_="latin12"):
                entry = self._extract_pattern_from_span(span)
                if not entry:
                    continue
                key = f"{entry.word}||{entry.analysis}"
                if key in seen:
                    continue
                seen.add(key)
                patterns.append(entry)
        return patterns

    @staticmethod
    def _find_solution_table(solution_span: Tag):
        table = solution_span.find_next("table")
        while table:
            if HeritageHTMLExtractor._is_pattern_table(table):
                return table
            table = table.find_next("table")
        return None

    @staticmethod
    def _find_next_solution_marker(span: Tag) -> Tag | None:
        for candidate in span.find_all_next("span"):
            if candidate is span:
                continue
            if candidate.get_text() and "Solution" in candidate.get_text():
                return candidate
        return None

    @staticmethod
    def _is_pattern_table(table) -> bool:
        classes = table.get("class") or []
        return any("back" in c for c in classes)

    @staticmethod
    def _table_color(table) -> str | None:
        if table is None:
            return None
        classes = table.get("class") or []
        for cls in classes:
            if cls.endswith("_back") or cls.endswith("back"):
                return cls
        return None

    def _is_metadata(self, text: str) -> bool:
        if not text:
            return True
        for pattern in self._metadata_re:
            if pattern.search(text):
                return True
        return False


def extract_solutions(html: str) -> list[MorphologySolution]:
    return HeritageHTMLExtractor().extract(html)
