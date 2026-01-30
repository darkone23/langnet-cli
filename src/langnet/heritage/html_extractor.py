"""
HTML parser for Heritage Platform responses
Extracts structured text content for Lark parsing
"""

import re
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional


class HeritageHTMLExtractor:
    """Extracts structured text from Heritage Platform HTML responses"""

    def __init__(self):
        self.pattern = r"\[([^\]]+)\]\{([^}]+)\}"

    def extract_solutions(self, html_content: str) -> List[Dict[str, Any]]:
        """Extract solution data from HTML content"""
        soup = BeautifulSoup(html_content, "html.parser")

        solutions = []

        # Find all solution spans
        for span in soup.find_all("span"):
            span_text = span.get_text()
            if span_text and "Solution" in span_text:
                solution = self._extract_solution(span, soup)
                if solution:
                    solutions.append(solution)

        # If no solution spans found, try alternative extraction
        if not solutions:
            solutions = self._extract_from_tables(soup)

        return solutions

    def _extract_solution(self, solution_span, soup) -> Optional[Dict[str, Any]]:
        """Extract a single solution from a solution span"""
        try:
            # Get solution number
            solution_text = solution_span.get_text()
            solution_match = re.search(r"Solution (\d+)", solution_text)
            if not solution_match:
                return None

            solution_num = int(solution_match.group(1))

            # Look for analysis patterns in the following content
            patterns = []

            # Look for pattern elements after the span
            next_element = solution_span.next_sibling
            if next_element:
                # Extract text content recursively
                pattern_text = self._extract_text_recursive(next_element)
                pattern_matches = re.findall(self.pattern, pattern_text)

                for word, analysis in pattern_matches:
                    patterns.append({"word": word.strip(), "analysis": analysis.strip()})

            return {
                "type": "morphological_analysis",
                "solution_number": solution_num,
                "patterns": patterns,
                "total_words": len(patterns),
                "score": 0.0,
                "metadata": {},
            }

        except Exception:
            return None

    def _extract_from_tables(self, soup) -> List[Dict[str, Any]]:
        """Extract solutions from table elements"""
        solutions = []

        # Look for grey_back tables
        tables = soup.find_all("table", class_="grey_back")

        for i, table in enumerate(tables):
            pattern_text = table.get_text(strip=True)
            pattern_matches = re.findall(self.pattern, pattern_text)

            patterns = []
            for word, analysis in pattern_matches:
                patterns.append({"word": word.strip(), "analysis": analysis.strip()})

            if patterns:
                solution = {
                    "type": "morphological_analysis",
                    "solution_number": i + 1,
                    "patterns": patterns,
                    "total_words": len(patterns),
                    "score": 0.0,
                    "metadata": {},
                }
                solutions.append(solution)

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

    def extract_metadata(self, html_content: str) -> Dict[str, Any]:
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

    def extract_plain_text(self, html_content: str) -> str:
        """Extract plain text from HTML content for Lark parsing"""
        soup = BeautifulSoup(html_content, "html.parser")

        solution_sections = []

        # Find all tables with pattern classes (grey_back, lawngreen_back, etc.)
        pattern_tables = soup.find_all("table", class_="grey_back")
        pattern_tables.extend(soup.find_all("table", class_="lawngreen_back"))

        # Filter to only innermost tables (those that don't contain other pattern tables)
        innermost_tables = []
        for table in pattern_tables:
            has_nested_pattern_table = False
            for nested in table.find_all("table", recursive=False):
                classes = nested.get("class") or []
                if any(c in classes for c in ["grey_back", "lawngreen_back"]):
                    has_nested_pattern_table = True
                    break
            if not has_nested_pattern_table:
                innermost_tables.append(table)

        # Extract text from innermost tables only
        seen_texts = set()
        for table in innermost_tables:
            table_text = table.get_text(strip=True)
            # Extract just the [word]{analysis} pattern part
            pattern_match = re.search(r"\[[^\]]+\]\{[^}]+\}", table_text)
            if pattern_match:
                text = pattern_match.group(0)
                if text not in seen_texts:
                    seen_texts.add(text)
                    solution_sections.append(text)

        # Fallback: extract patterns directly from spans
        if not solution_sections:
            pattern_spans = []
            for span in soup.find_all("span", class_="latin12"):
                span_text = span.get_text()
                pattern_match = re.search(r"\[[^\]]+\]\{[^}]+\}", span_text)
                if pattern_match:
                    text = pattern_match.group(0)
                    if text not in seen_texts:
                        seen_texts.add(text)
                        solution_sections.append(text)

        return "\n".join(solution_sections)

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


def extract_heritage_solutions(html_content: str) -> List[Dict[str, Any]]:
    """Extract structured solutions from Heritage HTML"""
    extractor = HeritageHTMLExtractor()
    return extractor.extract_solutions(html_content)
