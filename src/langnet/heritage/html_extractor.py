"""
HTML parser for Heritage Platform responses
Extracts structured text content for Lark parsing
"""

import re
from dataclasses import dataclass
from typing import TypedDict, cast

from bs4 import BeautifulSoup

from .types import MorphologyPattern, MorphologySegment, MorphologySolutionDict


@dataclass
class _PatternEntry:
    """A pattern entry extracted from HTML with word, analysis, raw text, and optional URL."""

    word: str
    analysis: str
    raw_text: str
    url: str | None = None


class _SolutionBlock(TypedDict):
    number: int
    patterns: list[_PatternEntry]
    color: str | None
    raw_text: str
    segments: list[MorphologySegment]


class HeritageHTMLExtractor:
    """Extracts structured text from Heritage Platform HTML responses"""

    def __init__(self):
        self.pattern = r"\[([^\]]+)\]\{([^}]+)\}"

    def extract_solutions(self, html_content: str) -> list[MorphologySolutionDict]:
        """Extract solution data from HTML content using Heritage layout hints."""
        soup = BeautifulSoup(html_content, "html.parser")

        # Prefer explicit "Solution" sections when present
        solutions: list[MorphologySolutionDict] = []
        for block in self._extract_solution_blocks(soup):
            pattern_entries = block["patterns"]
            pattern_dicts = [
                {"word": entry.word, "analysis": entry.analysis, "dictionary_url": entry.url}
                for entry in pattern_entries
            ]
            patterns = cast(list[MorphologyPattern], pattern_dicts)
            solution: MorphologySolutionDict = {
                "type": "morphological_analysis",
                "solution_number": block["number"],
                "patterns": patterns,
                "total_words": len(patterns),
                "score": 0.0,
                "metadata": {
                    "color": block["color"],
                    "raw_text": block["raw_text"],
                },
            }
            solutions.append(solution)

        # Fallback to loose table extraction if no solution markers were found
        if not solutions:
            loose_patterns = self._extract_loose_patterns(soup)
            if loose_patterns:
                pattern_dicts = [
                    {"word": entry.word, "analysis": entry.analysis, "dictionary_url": entry.url}
                    for entry in loose_patterns
                ]
                patterns = cast(list[MorphologyPattern], pattern_dicts)
                loose_solution: MorphologySolutionDict = {
                    "type": "morphological_analysis",
                    "solution_number": 1,
                    "patterns": patterns,
                    "total_words": len(patterns),
                    "score": 0.0,
                    "metadata": {
                        "color": None,
                        "raw_text": "\n".join(entry.raw_text for entry in loose_patterns),
                    },
                }
                solutions.append(loose_solution)

        return solutions

    def _extract_text_recursive(self, element) -> str:
        """Extract text content from element and its children"""
        if hasattr(element, "get_text"):
            return element.get_text()
        elif hasattr(element, "text"):
            return element.text
        elif hasattr(element, "string"):
            return element.string or ""
        else:
            return str(element)

    def extract_metadata(self, html_content: str) -> dict[str, int | str]:
        """Extract metadata from HTML content"""
        soup = BeautifulSoup(html_content, "html.parser")
        all_text = soup.get_text()

        metadata = {}

        # Extract solution count
        solution_match = re.search(r"(\d+)\s+solution[s]?\s+kept\s+among\s+(\d+)", all_text)
        if solution_match:
            metadata["solutions_kept"] = int(solution_match.group(1))
            metadata["total_available"] = int(solution_match.group(2))

        # Extract encoding
        encoding_match = re.search(r"t=([A-Z]+)", all_text)
        if encoding_match:
            metadata["encoding"] = encoding_match.group(1)

        return metadata

    def _is_pattern_table(self, table) -> bool:
        """Check if a table is a pattern table by class"""
        classes = table.get("class") or []
        return any("back" in c for c in classes)

    def _extract_pattern_from_element(self, element) -> str | None:
        """Extract [word]{analysis} pattern from an element's text"""
        text = element.get_text(strip=True)
        match = re.search(r"\[[^\]]+\]\{[^}]+\}", text)
        return match.group(0) if match else None

    def _get_innermost_pattern_tables(self, soup):
        """Find innermost pattern tables (those without nested pattern tables)"""
        pattern_tables = soup.find_all("table")
        pattern_tables = [t for t in pattern_tables if self._is_pattern_table(t)]

        innermost = []
        for table in pattern_tables:
            has_nested = False
            for nested in table.find_all("table", recursive=False):
                if self._is_pattern_table(nested):
                    has_nested = True
                    break
            if not has_nested:
                innermost.append(table)
        return innermost

    def extract_plain_text(self, html_content: str) -> str:
        """Extract plain text from HTML content for Lark parsing"""
        soup = BeautifulSoup(html_content, "html.parser")
        lines: list[str] = []

        # Prefer explicit solution sections to preserve solution boundaries
        solution_blocks = self._extract_solution_blocks(soup)
        if solution_blocks:
            for block in solution_blocks:
                solution_number = block["number"]
                patterns = block["patterns"]
                lines.append(f"Solution {solution_number}")
                lines.extend(f"[{entry.word}]{{{entry.analysis}}}" for entry in patterns)
            return "\n".join(lines)

        # Fallback: collect any pattern-bearing tables/spans we can find
        loose_patterns = self._extract_loose_patterns(soup)
        lines.extend(f"[{entry.word}]{{{entry.analysis}}}" for entry in loose_patterns)
        return "\n".join(lines)

    def _extract_solution_blocks(self, soup) -> list[_SolutionBlock]:
        """Return solution blocks with number, patterns, color class, and raw text."""
        blocks: list[_SolutionBlock] = []

        for span in soup.find_all("span"):
            text = span.get_text()
            if not text or "Solution" not in text:
                continue

            solution_match = re.search(r"Solution\s*(\d+)", text)
            if not solution_match:
                continue

            solution_number = int(solution_match.group(1))
            table = self._find_solution_table(span)
            next_solution = None
            for candidate in span.find_all_next("span"):
                if candidate is span:
                    continue
                if candidate.get_text() and "Solution" in candidate.get_text():
                    next_solution = candidate
                    break

            patterns = self._collect_patterns(table) if table else []
            if not patterns:
                patterns.extend(self._collect_inline_patterns(span, next_solution))
            segments = self._collect_segments(span, next_solution)
            if patterns:
                color = self._table_color(table) if table else None
                raw_text = "\n".join(entry.raw_text for entry in patterns) or " ".join(
                    seg["text"] for seg in segments if seg.get("text")
                )
                blocks.append(
                    {
                        "number": solution_number,
                        "patterns": patterns,
                        "color": color,
                        "raw_text": raw_text,
                        "segments": segments,
                    }
                )

        return blocks

    def _collect_segments(self, start_span, next_solution_span) -> list[MorphologySegment]:
        """Collect span text/class between current solution marker and the next one."""
        segments: list[MorphologySegment] = []
        current = start_span.next_sibling
        while current and current != next_solution_span:
            if getattr(current, "name", None) == "span":
                segments.append(
                    {
                        "css_class": (current.get("class") or [None])[0],
                        "text": current.get_text(strip=True),
                    }
                )
            current = current.next_sibling
        return segments

    def _collect_inline_patterns(self, start_span, next_solution_span) -> list[_PatternEntry]:
        """Collect latin12 patterns between solution markers when no table exists."""
        patterns: list[_PatternEntry] = []
        current = start_span.next_sibling
        seen: set[str] = set()
        while current and current != next_solution_span:
            if getattr(current, "name", None) == "span" and "latin12" in (
                current.get("class") or []
            ):
                span_text = current.get_text(strip=True)
                match = re.search(self.pattern, span_text)
                if match:
                    word = match.group(1).strip()
                    analysis = match.group(2).strip()
                    key = f"{word}||{analysis}"
                    if key not in seen:
                        seen.add(key)
                        # Extract URL from navy links within this span
                        url: str | None = None
                        for link in current.find_all("a", class_="navy"):
                            href = link.get("href")
                            if href and isinstance(href, str):
                                url = href
                                break
                        patterns.append(_PatternEntry(word, analysis, match.group(0), url))
            current = current.next_sibling
        return patterns

    def _find_solution_table(self, solution_span):
        """Locate the first pattern table after the given solution span."""
        table = solution_span.find_next("table")
        while table:
            if self._is_pattern_table(table):
                return table
            table = table.find_next("table")
        return None

    def _collect_patterns(self, container) -> list[_PatternEntry]:
        """Collect _PatternEntry objects from latin12 spans in a container."""
        if container is None:
            return []

        patterns: list[_PatternEntry] = []
        seen: set[str] = set()

        for span in container.find_all("span", class_="latin12"):
            span_text = span.get_text(strip=True)
            match = re.search(self.pattern, span_text)
            if not match:
                continue

            word = match.group(1).strip()
            analysis = match.group(2).strip()
            key = f"{word}||{analysis}"
            if key in seen:
                continue
            seen.add(key)

            # Extract URL from navy links within this span
            url: str | None = None
            for link in span.find_all("a", class_="navy"):
                href = link.get("href")
                if href and isinstance(href, str):
                    url = href
                    break

            patterns.append(_PatternEntry(word, analysis, match.group(0), url))

        return patterns

    def _extract_loose_patterns(self, soup) -> list[_PatternEntry]:
        """Extract patterns when no explicit solution sections are present."""
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
                span_text = span.get_text(strip=True)
                match = re.search(self.pattern, span_text)
                if not match:
                    continue
                word = match.group(1).strip()
                analysis = match.group(2).strip()
                key = f"{word}||{analysis}"
                if key in seen:
                    continue
                seen.add(key)
                # Extract URL from navy links within this span
                url: str | None = None
                for link in span.find_all("a", class_="navy"):
                    href = link.get("href")
                    if href and isinstance(href, str):
                        url = href
                        break
                patterns.append(_PatternEntry(word, analysis, match.group(0), url))

        return patterns

    def _table_color(self, table) -> str | None:
        """Return the CSS class that signals color (e.g., deep_sky_back)."""
        classes = table.get("class") or []
        for cls in classes:
            if cls.endswith("_back") or cls.endswith("back"):
                return cls
        return None

    def _extract_solution_text(self, solution_span) -> str:
        """Extract text content from a solution section"""
        lines = []

        # Add the solution header
        lines.append(solution_span.get_text())

        # Add content from following elements
        next_element = solution_span.next_sibling
        if next_element:
            content_text = self._extract_text_recursive(next_element)
            if content_text:
                lines.append(content_text)

        return "\n".join(lines)


# Convenience function
def extract_heritage_text(html_content: str) -> str:
    """Extract plain text from Heritage HTML for Lark parsing"""
    extractor = HeritageHTMLExtractor()
    return extractor.extract_plain_text(html_content)


def extract_heritage_solutions(html_content: str) -> list[MorphologySolutionDict]:
    """Extract structured solutions from Heritage HTML"""
    extractor = HeritageHTMLExtractor()
    return extractor.extract_solutions(html_content)
