import re
from typing import cast

from bs4 import BeautifulSoup
from langnet.types import JSONMapping

from .html_extractor import HeritageHTMLExtractor, _PatternEntry
from .lineparsers.parse_morphology import MorphologyReducer
from .models import HeritageWordAnalysis
from .types import (
    MorphologyParseResult,
    MorphologySolutionDict,
)

# NB: I don't actually want abbreviation functionality in this file
GRAMMATICAL_ABBREVIATIONS = {}

COMPOUND_INDICATORS = {}


def _convert_dict_to_analysis(data: dict) -> HeritageWordAnalysis:
    """Convert dict to HeritageWordAnalysis dataclass."""
    return HeritageWordAnalysis(
        word=data.get("word", ""),
        lemma=data.get("lemma", data.get("word", "")),
        root=data.get("root", ""),
        pos=data.get("pos", ""),
        case=data.get("case"),
        gender=data.get("gender"),
        number=data.get("number"),
        person=data.get("person"),
        tense=data.get("tense"),
        voice=data.get("voice"),
        mood=data.get("mood"),
        stem=data.get("stem", ""),
        meaning=data.get("meaning", []),
        dictionary_url=data.get("dictionary_url"),
    )


def expand_abbreviation(abbr: str, context: str = "") -> str:
    """Expand a French abbreviation to English with optional context."""
    abbr = abbr.strip().lower()

    # Check all abbreviation dictionaries
    if abbr in GRAMMATICAL_ABBREVIATIONS:
        return GRAMMATICAL_ABBREVIATIONS[abbr]
    elif abbr in COMPOUND_INDICATORS:
        return COMPOUND_INDICATORS[abbr]

    # Return original if not found
    return abbr


class SimpleHeritageParser:
    """Simple parser for Heritage Platform morphology responses"""

    # Constants for table parsing
    MIN_CELLS_COUNT = 2

    def parse_morphology(self, html_content: str) -> MorphologyParseResult:
        """Parse morphology analysis results"""
        soup = BeautifulSoup(html_content, "html.parser")

        result: MorphologyParseResult = {
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

    def _parse_solution_section(self, section_span, soup) -> MorphologySolutionDict | None:
        """Parse a single solution section"""
        try:
            # Get the solution number
            solution_text = section_span.get_text()
            solution_num = re.search(r"Solution (\d+)", solution_text)
            if not solution_num:
                return None

            solution: MorphologySolutionDict = {
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

    def _parse_analysis_table(self, table) -> HeritageWordAnalysis | None:
        """Parse an analysis table and return HeritageWordAnalysis."""
        try:
            word = ""

            # Extract text content from table
            table_text = table.get_text(strip=True)

            # Look for patterns like [agni]{?}
            pattern_match = re.search(r"\[([^\]]+)\]\{([^}]+)\}", table_text)
            if pattern_match:
                word = pattern_match.group(1)

            # Look for bold elements (might contain the word)
            bold_elements = table.find_all("b")
            for bold in bold_elements:
                bold_text = bold.get_text(strip=True)
                if bold_text and len(bold_text) > 1:
                    word = bold_text
                    break

            # If we found a word, create HeritageWordAnalysis
            if word:
                return HeritageWordAnalysis(
                    word=word,
                    lemma=word,  # Default lemma to word
                    root="",
                    pos="unknown",  # Default POS
                    stem="",
                    meaning=[],
                )

            return None

        except Exception:
            return None

    def _parse_tables(self, soup) -> list[MorphologySolutionDict]:
        """Parse all tables for analysis data, handling pattern tables and generic tables."""
        solutions: list[MorphologySolutionDict] = []

        # First, handle tables that directly contain patterns like [word]{analysis}
        pattern_tables = soup.find_all("table", class_="grey_back")
        for i, table in enumerate(pattern_tables, start=1):
            analysis = self._parse_analysis_table(table)
            if analysis:
                solutions.append(
                    {
                        "type": "morphological_analysis",
                        "solution_number": i,
                        "analyses": [analysis],
                        "total_words": 1,
                        "score": 0.0,
                        "metadata": {},
                    }
                )

        # Next, handle generic tables with word in first column, analysis in second column
        all_tables = soup.find_all("table")
        for i, table in enumerate(all_tables, start=1):
            if table in pattern_tables:
                continue
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all("td")
                if len(cells) >= self.MIN_CELLS_COUNT:
                    word = cells[0].get_text(strip=True)
                    analysis_code = cells[1].get_text(strip=True)
                    # Build pattern string for MorphologyReducer
                    pattern = f"[{word}]{{{analysis_code}}}"
                    try:
                        reducer = MorphologyReducer()
                        parsed = reducer.reduce(pattern)
                        if parsed:
                            # Convert MorphologyReducer output to proper types
                            first = parsed[0]
                            if isinstance(first, dict):
                                # Convert dict analyses to HeritageWordAnalysis
                                analyses_raw = first.get("analyses", [])
                                analyses = [
                                    a
                                    if isinstance(a, HeritageWordAnalysis)
                                    else _convert_dict_to_analysis(a)
                                    for a in analyses_raw
                                ]
                                solution: MorphologySolutionDict = {
                                    "type": first.get("type", "morphological_analysis"),
                                    "solution_number": first.get("solution_number", i),
                                    "analyses": analyses,
                                    "total_words": first.get("total_words", len(analyses)),
                                    "score": first.get("score", 0.0),
                                    "metadata": first.get("metadata", {}),
                                }
                                solutions.append(solution)
                    except Exception:
                        # If parsing fails, create basic solution with HeritageWordAnalysis
                        analysis = HeritageWordAnalysis(
                            word=word,
                            lemma=word,
                            root="",
                            pos="unknown",
                            stem="",
                            meaning=[],
                        )
                        solution: MorphologySolutionDict = {
                            "type": "morphological_analysis",
                            "solution_number": i,
                            "analyses": [analysis],
                            "total_words": 1,
                            "score": 0.0,
                            "metadata": {},
                        }
                        solutions.append(solution)

        return solutions


class MorphologyParser:
    """Parser for morphological analysis responses (sktreader) - uses new Lark-based parser"""

    def __init__(self):
        self.html_extractor = HeritageHTMLExtractor()
        self.morphology_reducer = MorphologyReducer()
        self.use_new_parser = True
        self.simple_parser = SimpleHeritageParser()

    def _convert_raw_solutions(self, raw_solutions: list) -> list[MorphologySolutionDict]:
        """Convert MorphologyReducer output to proper MorphologySolutionDict."""
        solutions: list[MorphologySolutionDict] = []
        for raw_sol in raw_solutions:
            if isinstance(raw_sol, dict):
                analyses_raw = raw_sol.get("analyses", [])
                analyses: list[HeritageWordAnalysis] = []
                for a in analyses_raw:
                    if isinstance(a, HeritageWordAnalysis):
                        analyses.append(a)
                    elif isinstance(a, dict):
                        analyses.append(_convert_dict_to_analysis(a))
                sol: MorphologySolutionDict = {
                    "type": raw_sol.get("type", "morphological_analysis"),
                    "solution_number": raw_sol.get("solution_number", 1),
                    "analyses": analyses,
                    "total_words": raw_sol.get("total_words", len(analyses)),
                    "score": raw_sol.get("score", 0.0),
                    "metadata": raw_sol.get("metadata", {}),
                }
                solutions.append(sol)
        return solutions

    def _enrich_with_urls(
        self,
        solutions: list[MorphologySolutionDict],
        solution_blocks: list,
    ) -> list[MorphologySolutionDict]:
        """Enrich analyses with dictionary URLs from solution block patterns."""

        context_by_num = {b["number"]: b for b in solution_blocks}
        for sol in solutions:
            sol_num = sol.get("solution_number")
            if sol_num is None:
                continue
            ctx = context_by_num.get(sol_num)
            if not ctx:
                continue
            patterns = ctx.get("patterns", [])
            analyses = sol.get("analyses", [])
            for i, analysis in enumerate(analyses):
                if i < len(patterns):
                    pattern = patterns[i]
                    if isinstance(pattern, _PatternEntry) and pattern.url:
                        # Create new analysis with dictionary_url
                        new_analysis = HeritageWordAnalysis(
                            word=analysis.word,
                            lemma=analysis.lemma,
                            root=analysis.root,
                            pos=analysis.pos,
                            case=analysis.case,
                            gender=analysis.gender,
                            number=analysis.number,
                            person=analysis.person,
                            tense=analysis.tense,
                            voice=analysis.voice,
                            mood=analysis.mood,
                            stem=analysis.stem,
                            meaning=analysis.meaning,
                            dictionary_url=pattern.url,
                        )
                        analyses[i] = new_analysis
        return solutions

    def parse(self, html_content: str) -> MorphologyParseResult:
        """Parse morphology analysis results using new Lark-based parser with fallback"""
        if self.use_new_parser:
            solution_blocks = self.html_extractor._extract_solution_blocks(
                BeautifulSoup(html_content, "html.parser")
            )
            plain_text = self.html_extractor.extract_plain_text(html_content)
            if plain_text.strip():
                try:
                    raw_solutions = self.morphology_reducer.reduce(plain_text)
                    # Convert MorphologyReducer output to proper
                    # MorphologySolutionDict with HeritageWordAnalysis
                    solutions = self._convert_raw_solutions(raw_solutions)
                    # Enrich with dictionary URLs from HTML patterns
                    solutions = self._enrich_with_urls(solutions, solution_blocks)

                    # Enrich solutions with raw text/color where available
                    context_by_num = {b["number"]: b for b in solution_blocks}
                    for sol in solutions:
                        sol_num = sol.get("solution_number")
                        if sol_num is None:
                            continue
                        ctx = context_by_num.get(sol_num)
                        if ctx:
                            sol_metadata = sol.get("metadata", {})
                            segments = ctx.get("segments")
                            sol_metadata.update(
                                {
                                    "color": ctx.get("color"),
                                    "raw_text": ctx.get("raw_text"),
                                    "segments": cast(JSONMapping, {"data": segments})
                                    if segments
                                    else None,
                                }
                            )
                            sol["metadata"] = sol_metadata
                    result: MorphologyParseResult = {
                        "solutions": solutions,
                        "word_analyses": [],
                        "total_solutions": len(solutions),
                        "encoding": "velthuis",
                        "metadata": cast(
                            JSONMapping, self.html_extractor.extract_metadata(html_content)
                        ),
                    }
                    return result
                except Exception:
                    # If Lark parsing fails, fall back to simple parser
                    return self.simple_parser.parse_morphology(html_content)
            else:
                # No plain text extracted; use simple parser as fallback
                return self.simple_parser.parse_morphology(html_content)
        else:
            return self.simple_parser.parse_morphology(html_content)
