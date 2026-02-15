"""
Lark parser implementation for Heritage Platform morphology responses
"""

import logging
from pathlib import Path

from lark import Lark, Transformer

from ..models import HeritageWordAnalysis

GENDER_MAP = {
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
NUMBER_MAP = {
    "sg": "singular",
    "sg.": "singular",
    "s": "singular",
    "du": "dual",
    "d": "dual",
    "pl": "plural",
    "pl.": "plural",
    "p": "plural",
}
CASE_MAP = {
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
    "gen": "genitive",
    "g": "genitive",
    "loc": "locative",
    "l": "locative",
}
PERSON_MAP = {"1": 1, "2": 2, "3": 3}
TENSE_MAP = {
    "pres": "present",
    "impf": "imperfect",
    "fut": "future",
    "perf": "perfect",
    "plup": "pluperfect",
}
MOOD_MAP = {
    "ind": "indicative",
    "imp": "imperative",
    "opt": "optative",
    "subj": "subjunctive",
}
VOICE_MAP = {"act": "active", "mid": "middle", "pass": "passive"}
POS_MAP = {
    "noun": "noun",
    "n": "noun",
    "verb": "verb",
    "v": "verb",
    "adj": "adjective",
    "adjective": "adjective",
    "pron": "pronoun",
    "adv": "adverb",
    "part": "participle",
    "ind": "indeclinable",
    "inde": "indeclinable",
}

CASE_CODE_INDEX = 1
GENDER_CODE_INDEX = 2
NUMBER_CODE_INDEX = 3


class MorphologyTransformer(Transformer):
    """Transforms parse tree to structured morphology data"""

    def start(self, args):
        """Entry point for transformation"""
        results = []
        for arg in args:
            if isinstance(arg, list):
                results.extend(arg)
            else:
                results.append(arg)
        return results

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

    def solution_content(self, args):
        """Pass through the analyses captured for a solution section."""
        return args

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
            compound_role=features.get("compound_role"),
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
            "compound_role": None,
        }

        if not code or code == "?":
            return features

        # When multiple analyses are separated by '|', use the first alternative
        if "|" in code:
            code = code.split("|", 1)[0].strip()

        # Heritage compound markers (e.g., iic. = initial compound member)
        compound_markers = {
            "iic": "initial",
            "ifc": "final",
        }
        code_lower = code.lower().rstrip(".")
        if code_lower in {"ind", "inde"}:
            features["pos"] = "indeclinable"
            return features
        for marker, role in compound_markers.items():
            if code_lower.startswith(marker):
                features["compound_role"] = role
                if features["pos"] and features["pos"].startswith("unknown"):
                    features["pos"] = "compound_member"
                return features

        # Check for text-based descriptions (e.g., "m. sg. voc.")
        if "." in code and " " in code:
            return self._parse_text_description(code, features)

        # Compact Heritage code format (e.g., "N1msn")
        return self._parse_compact_code(code, features)

    def _parse_text_description(self, code, features):
        """Parse text-based morphological description like 'm. sg. voc.'"""
        parts = code.lower().replace(".", "").replace(",", "").split()

        pos_indicators = []

        for part in parts:
            stripped_part = part.strip()
            if not stripped_part:
                continue
            self._map_part_to_feature(stripped_part, features, pos_indicators)

        if features["pos"] == "unknown":
            features["pos"] = self._infer_pos(pos_indicators)

        return features

    def _is_ordinal(self, part):
        """Check if part is an ordinal number"""
        return part.endswith(("st", "nd", "rd", "th"))

    def _get_ordinal_person(self, part):
        """Get person from ordinal number"""
        num_part = part[:-2]
        return PERSON_MAP.get(num_part)

    def _map_part_to_feature(self, part, features, pos_indicators):
        """Map a part to its grammatical feature"""
        if self._is_ordinal(part):
            person = self._get_ordinal_person(part)
            if person:
                features["person"] = person
                pos_indicators.append("verb")
                return

        mappings = [
            (GENDER_MAP, "gender", "noun"),
            (NUMBER_MAP, "number", None),
            (CASE_MAP, "case", "noun"),
            (PERSON_MAP, "person", "verb"),
            (TENSE_MAP, "tense", "verb"),
            (MOOD_MAP, "mood", "verb"),
            (VOICE_MAP, "voice", "verb"),
        ]

        for mapping, feature_name, pos_indicator in mappings:
            if part in mapping:
                features[feature_name] = mapping[part]
                if pos_indicator:
                    pos_indicators.append(pos_indicator)
                return

        if part in POS_MAP:
            features["pos"] = POS_MAP[part]
        elif part.startswith("verb") or part == "v":
            features["pos"] = "verb"
        elif part.startswith("noun") or part == "n":
            features["pos"] = "noun"

    def _infer_pos(self, pos_indicators):
        """Infer part of speech from grammatical indicators"""
        if "verb" in pos_indicators and "noun" not in pos_indicators:
            return "verb"
        elif "noun" in pos_indicators:
            return "noun"
        return "unknown"

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
            features["pos"] = pos_mapping.get(pos_code, f"unknown({pos_code})")

        if len(code) > CASE_CODE_INDEX and code[CASE_CODE_INDEX].isdigit():
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

        if len(code) > GENDER_CODE_INDEX and code[GENDER_CODE_INDEX] in "mfn":
            gender_mapping = {
                "m": "masculine",
                "f": "feminine",
                "n": "neuter",
            }
            features["gender"] = gender_mapping.get(code[2], code[2])

        if len(code) > NUMBER_CODE_INDEX and code[NUMBER_CODE_INDEX] in "sdp":
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
