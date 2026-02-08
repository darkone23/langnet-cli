"""
HTML parser for Heritage Platform responses
Extracts structured text content for Lark parsing
"""

import re
from typing import Any

from bs4 import BeautifulSoup


class HeritageHTMLExtractor:
    """Extracts structured text from Heritage Platform HTML responses"""

    def __init__(self):
        self.pattern = r"\[([^\]]+)\]\{([^}]+)\}"

    def extract_solutions(self, html_content: str) -> list[dict[str, Any]]:
        """Extract solution data from HTML content using Heritage layout hints."""
        soup = BeautifulSoup(html_content, "html.parser")

        # Prefer explicit "Solution" sections when present
        solutions: list[dict[str, Any]] = []
        for block in self._extract_solution_blocks(soup):
            patterns = [{"word": w, "analysis": a} for w, a, _ in block["patterns"]]
            solutions.append(
                {
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
            )

        # Fallback to loose table extraction if no solution markers were found
        if not solutions:
            loose_patterns = self._extract_loose_patterns(soup)
            if loose_patterns:
                patterns = [{"word": w, "analysis": a} for w, a, _ in loose_patterns]
                solutions.append(
                    {
                        "type": "morphological_analysis",
                        "solution_number": 1,
                        "patterns": patterns,
                        "total_words": len(patterns),
                        "score": 0.0,
                        "metadata": {
                            "color": None,
                            "raw_text": "\n".join(raw for _, _, raw in loose_patterns),
                        },
                    }
                )

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

    def extract_metadata(self, html_content: str) -> dict[str, Any]:
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
                lines.extend(f"[{word}]{{{analysis}}}" for word, analysis, _ in patterns)
            return "\n".join(lines)

        # Fallback: collect any pattern-bearing tables/spans we can find
        loose_patterns = self._extract_loose_patterns(soup)
        lines.extend(f"[{word}]{{{analysis}}}" for word, analysis, _ in loose_patterns)
        return "\n".join(lines)

    def _extract_solution_blocks(self, soup) -> list[dict[str, Any]]:
        """Return solution blocks with number, patterns, color class, and raw text."""
        blocks: list[dict[str, Any]] = []

        for span in soup.find_all("span"):
            text = span.get_text()
            if not text or "Solution" not in text:
                continue

            solution_match = re.search(r"Solution\s*(\d+)", text)
            if not solution_match:
                continue

            solution_number = int(solution_match.group(1))
            table = self._find_solution_table(span)
            if not table:
                continue

            patterns = self._collect_patterns(table)
            if patterns:
                color = self._table_color(table)
                raw_text = "\n".join(raw for _, _, raw in patterns)
                blocks.append(
                    {
                        "number": solution_number,
                        "patterns": patterns,
                        "color": color,
                        "raw_text": raw_text,
                    }
                )

        return blocks

    def _find_solution_table(self, solution_span):
        """Locate the first pattern table after the given solution span."""
        table = solution_span.find_next("table")
        while table:
            if self._is_pattern_table(table):
                return table
            table = table.find_next("table")
        return None

    def _collect_patterns(self, container) -> list[tuple[str, str, str]]:
        """Collect unique (word, analysis, raw_text) triples from latin12 spans within a container."""
        if container is None:
            return []

        patterns: list[tuple[str, str, str]] = []
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
            patterns.append((word, analysis, match.group(0)))

        return patterns

    def _extract_loose_patterns(self, soup) -> list[tuple[str, str, str]]:
        """Extract patterns when no explicit solution sections are present."""
        patterns: list[tuple[str, str, str]] = []
        seen: set[str] = set()

        for table in self._get_innermost_pattern_tables(soup):
            for word, analysis, raw_text in self._collect_patterns(table):
                key = f"{word}||{analysis}"
                if key in seen:
                    continue
                seen.add(key)
                patterns.append((word, analysis, raw_text or f"[{word}]{{{analysis}}}"))

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
                patterns.append((word, analysis, match.group(0)))

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


def extract_heritage_solutions(html_content: str) -> list[dict[str, Any]]:
    """Extract structured solutions from Heritage HTML"""
    extractor = HeritageHTMLExtractor()
    return extractor.extract_solutions(html_content)
