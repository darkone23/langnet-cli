import re
from typing import Any

from bs4 import BeautifulSoup

from .html_extractor import HeritageHTMLExtractor
from .lineparsers.parse_morphology import MorphologyReducer

# Grammatical abbreviations (copied from abbreviations.py to avoid import issues)
GRAMMATICAL_ABBREVIATIONS = {
    # Case and number
    "a.": "adjective",
    "abl.": "ablative",
    "abs.": "absolutive",
    "acc.": "accusative",
    "ac.": "active",
    "act.": "action",
    "adr.": "term of address",
    "adv.": "adverb",
    "agt.": "agent",
    "all.": "German",
    "ang.": "English",
    "ant.": "before the common era",
    "aor.": "aorist",
    "approx.": "approximately",
    "arch.": "architecture",
    "astr.": "astronomy",
    "av.": "with",
    "bd.": "Buddhism",
    "bén.": "benedictive",
    "bio.": "biology",
    "ca.": "causative",
    "c.-à-d.": "that is to say / i.e.",
    "cf.": "compare / see",
    "cél.": "celebrative",
    "comp.": "comparative",
    "cond.": "conditional",
    "conf.": "confer / compare",
    "conj.": "conjunction",
    "cons.": "consonant",
    "contr.": "contraction",
    "cop.": "copulative",
    "cor.": "correlative",
    "désid.": "desiderative",
    "désin.": "desinential",
    "dét.": "determinative",
    "dir.": "direct",
    "dist.": "distributive",
    "dr.": "doctor",
    "dur.": "durative",
    "écon.": "economic",
    "ép.": "epic",
    "équ.": "equative",
    "err.": "error",
    "excl.": "exclamatory",
    "f.": "feminine",
    "fam.": "familial",
    "fig.": "figurative",
    "fut.": "future",
    "géom.": "geometry",
    "ger.": "gerund",
    "gér.": "causative",
    "gr.": "Greek",
    "hébr.": "Hebrew",
    "hist.": "historical",
    "i.": "intransitive",
    "imp.": "imperative",
    "impf.": "imperfect",
    "ind.": "indicative",
    "infin.": "infinitive",
    "intens.": "intensive",
    "intr.": "intransitive",
    "irr.": "irregular",
    "it.": "Italian",
    "lat.": "Latin",
    "law.": "law",
    "lit.": "literally",
    "loc.": "locative",
    "log.": "logic",
    "m.": "masculine",
    "math.": "mathematics",
    "med.": "medical",
    "méd.": "medial",
    "mét.": "metal",
    "métaph.": "metaphorical",
    "mil.": "military",
    "modal.": "modal",
    "mood.": "mood",
    "morf.": "morphological",
    "mor.": "moral",
    "msc.": "miscellaneous",
    "n.": "neuter",
    "nom.": "nominative",
    "nucl.": "nuclear",
    "num.": "numeral",
    "obj.": "objective",
    "obl.": "oblique",
    "opt.": "optative (potential)",
    "ord.": "ordinal",
    "part.": "particle",
    "patr.": "patronymic",
    "péj.": "pejorative",
    "péri.": "periphrastic",
    "pers.": "person",
    "pf.": "prefix",
    "pft.": "perfect",
    "phil.": "philosophy",
    "phon.": "phonetics",
    "pl.": "plural",
    "poss.": "possessive",
    "pfut.": "future participle",
    "pfp.": "future passive participle",
    "pp.": "past passive participle",
    "ppa.": "past active participle",
    "ppft.": "perfect participle",
    "ppr.": "present participle",
    "pr.": "present",
    "prép.": "preposition",
    "priv.": "privative",
    "prk.": "Prakrit",
    "pron.": "pronoun",
    "ps.": "passive",
    "pt.": "Portuguese",
    "qqc.": "something",
    "qqf.": "sometimes",
    "qqn.": "someone",
    "red.": "reduplication",
    "refl.": "reflexive",
    "rel.": "relative",
    "rét.": "retroflex",
    "s.": "singular",
    "sc.": "science",
    "schol.": "scholarly",
    "sec.": "secondary",
    "sem.": "semantic",
    "sg.": "singular",
    "socio.": "sociological",
    "spéc.": "specific",
    "subj.": "subjunctive",
    "subord.": "subordinating",
    "superl.": "superlative",
    "syn.": "synonymous",
    "syntax.": "syntactic",
    "t.": "transitive",
    "tech.": "technical",
    "temp.": "temporal",
    "théol.": "theological",
    "topo.": "topography",
    "top.": "topic",
    "tr.": "transitive",
    "un.": "union",
    "univ.": "universal",
    "v.": "verb",
    "véd.": "Vedic",
    "voc.": "vocative",
    "vol.": "volitional",
    "vr.": "vṛddhi",
    "ZOO.": "zoology",
}

COMPOUND_INDICATORS = {
    "ic.": "in composition",
    "ifc.": "at the end of a compound",
    "iic.": "at the beginning of a compound",
    "iiv.": "at the beginning of a verb",
}


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
                # Expand abbreviations in the analysis
                expanded_analysis = expand_abbreviation(analysis["analysis"])
                analysis["expanded_analysis"] = expanded_analysis

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
        """Parse all tables for analysis data, handling pattern tables and generic tables."""
        solutions: list[dict[str, Any]] = []

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
                            # Extract analyses from first solution
                            first = parsed[0]
                            # MorphologyReducer returns dict, so access directly
                            if isinstance(first, dict):
                                solution = first
                                solutions.append(solution)
                    except Exception:
                        # If parsing fails, create basic solution
                        solution = {
                            "type": "morphological_analysis",
                            "solution_number": i,
                            "analyses": [
                                {
                                    "word": word,
                                    "lemma": word,
                                    "root": "",
                                    "pos": "unknown",
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
                                    "analysis": analysis_code,
                                    # Expand abbreviations in the analysis
                                    "expanded_analysis": expand_abbreviation(analysis_code),
                                }
                            ],
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

    def parse(self, html_content: str) -> dict[str, Any]:
        """Parse morphology analysis results using new Lark-based parser with fallback"""
        if self.use_new_parser:
            plain_text = self.html_extractor.extract_plain_text(html_content)
            if plain_text.strip():
                try:
                    solutions = self.morphology_reducer.reduce(plain_text)
                    result = {
                        "solutions": solutions,
                        "word_analyses": [],
                        "total_solutions": len(solutions),
                        "encoding": "velthuis",
                        "metadata": self.html_extractor.extract_metadata(html_content),
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
