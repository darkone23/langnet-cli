import re
from typing import Any

from bs4 import BeautifulSoup

from .client import HeritageAPIError


class SimpleHeritageParser:
    """Simple parser for Heritage Platform morphology responses"""

    def parse_morphology(self, html_content: str) -> dict[str, Any]:
        """Parse morphology analysis results"""
        soup = BeautifulSoup(html_content, "html.parser")

        result: dict[str, Any] = {
            "solutions": [],
            "word_analyses": [],
            "total_solutions": 0,
            "encoding": "velthuis",
            "metadata": {},
        }

        # Extract solution count from text
        all_text = soup.get_text()
        solution_match = re.search(r"(\d+)\s+solution[s]?\s+kept\s+among\s+(\d+)", all_text)
        if solution_match:
            result["total_solutions"] = int(solution_match.group(1))
            result["metadata"]["total_available"] = int(solution_match.group(2))

        # Look for solution sections
        solution_sections = []
        for span in soup.find_all("span"):
            text = span.get_text()
            if text and "Solution" in text:
                solution_sections.append(span)

        for i, section in enumerate(solution_sections):
            solution = self._parse_solution_section(section, soup)
            if solution:
                result["solutions"].append(solution)

        # If no solution sections found, try to extract from tables
        if not result["solutions"]:
            result["solutions"] = self._parse_tables(soup)

        result["total_solutions"] = len(result["solutions"])

        return result

    def _parse_solution_section(self, section_span, soup) -> dict[str, Any] | None:
        """Parse a single solution section"""
        try:
            # Get the solution number
            solution_text = section_span.get_text()
            solution_num = re.search(r"Solution (\d+)", solution_text)
            if not solution_num:
                return None

            solution: dict[str, Any] = {
                "type": "morphological_analysis",
                "solution_number": int(solution_num.group(1)),
                "analyses": [],
                "total_words": 0,
                "score": 0.0,
                "metadata": {},
            }

            # Look for analysis content near this span
            # Look for the next elements after this span
            next_element = section_span.next_sibling
            if next_element:
                # Look for table elements with analysis data
                table_elements = next_element.find_all("table", class_="grey_back")
                for table in table_elements:
                    analysis = self._parse_analysis_table(table)
                    if analysis:
                        solution["analyses"].append(analysis)
                        solution["total_words"] += 1

            return solution if solution["analyses"] else None

        except Exception:
            return None

    def _parse_analysis_table(self, table) -> dict[str, Any] | None:
        """Parse an analysis table"""
        try:
            analysis = {
                "word": "",
                "lemma": "",
                "root": "",
                "pos": "",
                "case": None,
                "gender": None,
                "number": None,
                "person": None,
                "tense": None,
                "voice": None,
                "mood": None,
                "stem": "",
                "meaning": [],
                "lexicon_refs": [],
                "confidence": 0.0,
            }

            # Extract text content from table
            table_text = table.get_text(strip=True)

            # Look for patterns like [agni]{?}
            pattern_match = re.search(r"\[([^\]]+)\]\{([^}]+)\}", table_text)
            if pattern_match:
                analysis["word"] = pattern_match.group(1)
                analysis["analysis"] = pattern_match.group(2)

            # Look for bold elements (might contain the word)
            bold_elements = table.find_all("b")
            for bold in bold_elements:
                bold_text = bold.get_text(strip=True)
                if bold_text and len(bold_text) > 1:
                    analysis["word"] = bold_text
                    break

            # If we found a word, create basic analysis
            if analysis["word"]:
                analysis["lemma"] = analysis["word"]  # Default lemma to word
                analysis["pos"] = "unknown"  # Default POS

            return analysis if analysis["word"] else None

        except Exception:
            return None

    def _parse_tables(self, soup) -> list[dict[str, Any]]:
        """Parse all tables for analysis data"""
        solutions = []

        tables = soup.find_all("table", class_="grey_back")

        for i, table in enumerate(tables):
            analysis = self._parse_analysis_table(table)
            if analysis:
                solution = {
                    "type": "morphological_analysis",
                    "solution_number": i + 1,
                    "analyses": [analysis],
                    "total_words": 1,
                    "score": 0.0,
                    "metadata": {},
                }
                solutions.append(solution)

        return solutions


class MorphologyParser:
    """Parser for morphological analysis responses (sktreader) - uses SimpleHeritageParser"""

    def __init__(self):
        self.simple_parser = SimpleHeritageParser()

    def parse(self, html_content: str) -> dict[str, Any]:
        """Parse morphology analysis results using simple parser"""
        try:
            return self.simple_parser.parse_morphology(html_content)
        except Exception as e:
            raise HeritageAPIError(f"Failed to parse morphology HTML: {e}")
