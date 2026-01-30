"""
Lark parser implementation for Heritage Platform morphology responses
"""

from pathlib import Path
from lark import Lark, Transformer

from ..models import HeritageWordAnalysis


class MorphologyTransformer(Transformer):
    """Transforms parse tree to structured morphology data"""

    def start(self, args):
        """Entry point for transformation"""
        return args[0] if args else []

    def solution_section(self, args):
        """Transform a solution section"""
        solution_num = args[0]
        patterns = args[1] if len(args) > 1 else []

        analyses = []
        for pattern in patterns:
            analysis = self._transform_analysis(pattern)
            if analysis:
                analyses.append(analysis)

        return {
            "type": "morphological_analysis",
            "solution_number": solution_num,
            "analyses": analyses,
            "total_words": len(analyses),
            "score": 0.0,
            "metadata": {},
        }

    def pattern_section(self, args):
        """Transform a standalone pattern section"""
        patterns = args if args else []

        analyses = []
        for pattern in patterns:
            analysis = self._transform_analysis(pattern)
            if analysis:
                analyses.append(analysis)

        return {
            "type": "morphological_analysis",
            "solution_number": 1,  # Default number for standalone patterns
            "analyses": analyses,
            "total_words": len(analyses),
            "score": 0.0,
            "metadata": {},
        }

    def analysis_pattern(self, args):
        """Transform an analysis pattern"""
        word = args[0]
        analysis = args[1]
        return {"word": word, "analysis": analysis}

    def word(self, args):
        """Transform word token"""
        return str(args[0])

    def analysis(self, args):
        """Transform analysis code token"""
        return str(args[0])

    def INT(self, args):
        """Transform integer token"""
        return int(args[0])

    def _transform_analysis(self, pattern_data):
        """Transform pattern data to HeritageWordAnalysis"""
        word = pattern_data.get("word", "")
        analysis_code = pattern_data.get("analysis", "")

        # Parse analysis code to extract features
        features = self._parse_analysis_code(analysis_code)

        return HeritageWordAnalysis(
            word=word,
            lemma=word,  # Default lemma to word
            root=features.get("root", ""),
            pos=features.get("pos", "unknown"),
            case=features.get("case"),
            gender=features.get("gender"),
            number=features.get("number"),
            person=features.get("person"),
            tense=features.get("tense"),
            voice=features.get("voice"),
            mood=features.get("mood"),
            stem=features.get("stem", ""),
            meaning=[],  # Not available in morphology responses
            lexicon_refs=[],  # Not available in morphology responses
            confidence=0.0,
        )

    def _parse_analysis_code(self, code):
        """Parse analysis code to extract morphological features"""
        features = {
            "pos": "unknown",
            "case": None,
            "gender": None,
            "number": None,
            "person": None,
            "tense": None,
            "voice": None,
            "mood": None,
            "stem": "",
            "root": "",
        }

        if not code or code == "?":
            return features

        # Check for text-based descriptions (e.g., "m. sg. voc.")
        if "." in code and " " in code:
            return self._parse_text_description(code, features)

        # Compact Heritage code format (e.g., "N1msn")
        return self._parse_compact_code(code, features)

    def _parse_text_description(self, code, features):
        """Parse text-based morphological description like 'm. sg. voc.'"""
        parts = code.lower().replace(".", "").replace(",", "").split()

        gender_map = {
            "m": "masculine",
            "masc": "masculine",
            "m.": "masculine",
            "f": "feminine",
            "fem": "feminine",
            "f.": "feminine",
            "n": "neuter",
            "neut": "neuter",
            "n.": "neuter",
        }
        number_map = {
            "sg": "singular",
            "sg.": "singular",
            "s": "singular",
            "du": "dual",
            "d": "dual",
            "pl": "plural",
            "pl.": "plural",
            "p": "plural",
        }
        case_map = {
            "nom": "nominative",
            "n": "nominative",
            "voc": "vocative",
            "v": "vocative",
            "acc": "accusative",
            "a": "accusative",
            "instr": "instrumental",
            "i": "instrumental",
            "dat": "dative",
            "d": "dative",
            "abl": "ablative",
            "abl": "ablative",
            "gen": "genitive",
            "g": "genitive",
            "loc": "locative",
            "l": "locative",
        }
        person_map = {"1": 1, "2": 2, "3": 3}
        tense_map = {
            "pres": "present",
            "impf": "imperfect",
            "fut": "future",
            "perf": "perfect",
            "plup": "pluperfect",
        }
        mood_map = {
            "ind": "indicative",
            "imp": "imperative",
            "opt": "optative",
            "subj": "subjunctive",
        }
        voice_map = {"act": "active", "mid": "middle", "pass": "passive"}
        pos_map = {
            "noun": "noun",
            "n": "noun",
            "verb": "verb",
            "v": "verb",
            "adj": "adjective",
            "adjective": "adjective",
            "pron": "pronoun",
            "adv": "adverb",
            "part": "participle",
        }

        pos_indicators = []

        for part in parts:
            part = part.strip()
            if not part:
                continue
            # Handle ordinal numbers like "3rd", "1st", "2nd"
            if part.endswith(("st", "nd", "rd", "th")):
                num_part = part[:-2]
                if num_part in person_map:
                    features["person"] = person_map[num_part]
                    pos_indicators.append("verb")
                    continue
            if part in gender_map:
                features["gender"] = gender_map[part]
                pos_indicators.append("noun")
            elif part in number_map:
                features["number"] = number_map[part]
            elif part in case_map:
                features["case"] = case_map[part]
                pos_indicators.append("noun")
            elif part in person_map:
                features["person"] = person_map[part]
                pos_indicators.append("verb")
            elif part in tense_map:
                features["tense"] = tense_map[part]
                pos_indicators.append("verb")
            elif part in mood_map:
                features["mood"] = mood_map[part]
                pos_indicators.append("verb")
            elif part in voice_map:
                features["voice"] = voice_map[part]
                pos_indicators.append("verb")
            elif part in pos_map:
                features["pos"] = pos_map[part]
            elif part.startswith("verb") or part == "v":
                features["pos"] = "verb"
            elif part.startswith("noun") or part == "n":
                features["pos"] = "noun"

        # Infer POS from grammatical features if not explicitly set
        if features["pos"] == "unknown":
            if "verb" in pos_indicators and not "noun" in pos_indicators:
                features["pos"] = "verb"
            elif "noun" in pos_indicators:
                features["pos"] = "noun"

        return features

    def _parse_compact_code(self, code, features):
        """Parse compact Heritage code format (e.g., 'N1msn')"""
        pos_mapping = {
            "N": "noun",
            "V": "verb",
            "A": "adjective",
            "P": "pronoun",
            "C": "conjunction",
            "I": "interjection",
            "D": "adverb",
            "U": "numeral",
        }

        if code:
            pos_code = code[0]
            if pos_code in pos_mapping:
                features["pos"] = pos_mapping[pos_code]
            else:
                features["pos"] = f"unknown({pos_code})"

        if len(code) > 1 and code[1].isdigit():
            case_num = code[1]
            case_mapping = {
                "1": "nominative",
                "2": "accusative",
                "3": "instrumental",
                "4": "dative",
                "5": "ablative",
                "6": "genitive",
                "7": "locative",
                "8": "vocative",
            }
            features["case"] = case_mapping.get(case_num, f"case_{case_num}")

        if len(code) > 2 and code[2] in "mfn":
            gender_mapping = {
                "m": "masculine",
                "f": "feminine",
                "n": "neuter",
            }
            features["gender"] = gender_mapping.get(code[2], code[2])

        if len(code) > 3 and code[3] in "sdp":
            number_mapping = {
                "s": "singular",
                "d": "dual",
                "p": "plural",
            }
            features["number"] = number_mapping.get(code[3], code[3])

        return features


def get_morphology_grammar():
    """Load the morphology grammar from file"""
    grammar_path = Path(__file__).parent / "grammars" / "morphology.ebnf"
    return grammar_path.read_text()


class MorphologyReducer:
    """Main parser class combining Lark parser and transformer"""

    def __init__(self, parser_options=None):
        """Initialize the parser"""
        self.grammar = get_morphology_grammar()
        self.parser_options = parser_options or {}
        self._parser = None

    @property
    def parser(self):
        """Lazy initialization of Lark parser"""
        if self._parser is None:
            self._parser = Lark(
                self.grammar,
                start="start",
                parser="lalr",
                transformer=MorphologyTransformer(),
                **self.parser_options,
            )
        return self._parser

    def reduce(self, text):
        """Parse morphology text and return structured data"""
        try:
            result = self.parser.parse(text)
            # Ensure result is always a list
            if isinstance(result, list):
                return result
            elif result is not None:
                return [result]
            else:
                return []
        except Exception as e:
            # Log error and return empty list for robustness
            import logging

            logging.error(f"Failed to parse morphology: {e}")
            return []

    def parse_line(self, line):
        """Parse a single line of morphology text"""
        return self.reduce(line)


# Convenience function for direct parsing
def parse_morphology(text):
    """Parse morphology text and return structured data"""
    reducer = MorphologyReducer()
    return reducer.reduce(text)
