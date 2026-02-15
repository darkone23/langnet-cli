import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import cattrs
import structlog
from sh import Command

from langnet.whitakers_words.enums import (
    Age as WWAge,
)
from langnet.whitakers_words.enums import (
    Area as WWArea,
)
from langnet.whitakers_words.enums import (
    Case as WWCase,
)
from langnet.whitakers_words.enums import (
    Degree as WWDegree,
)
from langnet.whitakers_words.enums import (
    Frequency as WWFrequency,
)
from langnet.whitakers_words.enums import (
    Gender as WWGender,
)
from langnet.whitakers_words.enums import (
    Geography as WWGeography,
)
from langnet.whitakers_words.enums import (
    Mood as WWMood,
)
from langnet.whitakers_words.enums import (
    Number as WWNumber,
)
from langnet.whitakers_words.enums import (
    Person as WWPerson,
)
from langnet.whitakers_words.enums import (
    Source as WWSource,
)
from langnet.whitakers_words.enums import (
    Tense as WWTense,
)
from langnet.whitakers_words.enums import (
    Voice as WWVoice,
)

from .lineparsers import CodesReducer, FactsReducer, SensesReducer

logger = structlog.get_logger(__name__)


def _load_external_enums():
    # """Load enums from whitakers_words library for cross-integration."""
    # try:
    #     import sys
    #     from pathlib import Path
    #     # Try multiple possible locations for whitakers_words
    #     # 1. As a module in the current project (git submodule)
    #     # 2. In the Python path

    #     # Path from current file to project root
    #     current_dir = Path(__file__).parent
    #     # Go up: src/langnet/whitakers_words -> src/langnet -> src -> project root
    #     proj_root = current_dir.parent.parent.parent

    #     # Check for whitakers_words in project root
    #     whitakers_words_path = proj_root / "whitakers_words" / "whitakers_words"
    #     if whitakers_words_path.exists():
    #         if str(whitakers_words_path.parent) not in sys.path:
    #             sys.path.insert(0, str(whitakers_words_path.parent))

    return {
        "Tense": WWTense,
        "Voice": WWVoice,
        "Mood": WWMood,
        "Gender": WWGender,
        "Number": WWNumber,
        "Case": WWCase,
        "Degree": WWDegree,
        "Person": WWPerson,
        "Age": WWAge,
        "Area": WWArea,
        "Geography": WWGeography,
        "Frequency": WWFrequency,
        "Source": WWSource,
    }
    # except ImportError:
    #     logger.warning("external_enums_not_found", package="whitakers_words")
    #     return None


_external_enums = _load_external_enums()


def _create_tense_map():
    return {
        "PRES": "Praesens (Present)",
        "IMP": "Imperfectum (Imperfect)",
        "IMPF": "Imperfectum (Imperfect)",
        "IMPFF": "Imperfectum (Imperfect)",
        "PERF": "Perfectum (Perfect)",
        "FUT": "Futurum Simplex (Future Simple)",
        "FUTP": "Futurum Exactum (Future Perfect)",
        "PLUP": "Plusquamperfectum (Pluperfect)",
        "X": "Unknown",
    }


def _create_voice_map():
    return {"ACTIVE": "Active", "PASSIVE": "Passive", "X": "Unknown"}


def _create_mood_map():
    return {
        "IND": "Indicative",
        "SUB": "Subjunctive",
        "IMP": "Imperative",
        "INF": "Infinitive",
        "PPL": "Participle",
        "X": "Unknown",
    }


def _create_person_map():
    return {"0": "0", "1": "1", "2": "2", "3": "3", "X": "Unknown"}


def _create_number_map():
    return {"S": "Singular", "P": "Plural", "X": "Unknown"}


def _create_case_map():
    return {
        "NOM": "Nominative",
        "VOC": "Vocative",
        "GEN": "Genitive",
        "DAT": "Dative",
        "ACC": "Accusative",
        "ABL": "Ablative",
        "LOC": "Locative",
        "X": "Unknown",
    }


def _create_gender_map():
    return {"M": "Masculine", "F": "Feminine", "N": "Neuter", "C": "Common", "X": "Unknown"}


def _create_degree_map():
    return {"POS": "Positive", "COMP": "Comparative", "SUPER": "Superlative", "X": "Unknown"}


def _create_pronoun_type_map():
    return {
        "PERS": "Personal",
        "REFLEX": "Reflexive",
        "DEMONS": "Demonstrative",
        "INDEF": "Indefinite",
        "INTERR": "Interrogative",
        "REL": "Relative",
        "ADJECT": "Adjectival",
        "X": "Unknown",
    }


def _create_numeral_type_map():
    return {
        "CARD": "Cardinal",
        "ORD": "Ordinal",
        "DIST": "Distributive",
        "ADVERB": "Adverbial",
        "X": "Unknown",
    }


TENSE_MAP = _create_tense_map()
VOICE_MAP = _create_voice_map()
MOOD_MAP = _create_mood_map()
PERSON_MAP = _create_person_map()
NUMBER_MAP = _create_number_map()
CASE_MAP = _create_case_map()
GENDER_MAP = _create_gender_map()
DEGREE_MAP = _create_degree_map()
PRONOUN_TYPE_MAP = _create_pronoun_type_map()
NUMERAL_TYPE_MAP = _create_numeral_type_map()


@dataclass
class CodelineData:
    term: str | None = field(default=None)
    notes: list[str] | None = field(default=None)
    age: str | None = field(default=None)
    source: str | None = field(default=None)
    freq: str | None = field(default=None)
    declension: str | None = field(default=None)
    pos_form: str | None = field(default=None)
    pos_code: str | None = field(default=None)


@dataclass
class CodelineName:
    names: list[str]
    notes: list[str] | None = field(default=None)
    age: str | None = field(default=None)
    source: str | None = field(default=None)
    freq: str | None = field(default=None)
    declension: str | None = field(default=None)
    pos_form: str | None = field(default=None)
    pos_code: str | None = field(default=None)


class Frequency(Enum):
    VERY_FREQUENT = "A"  # Top 10%
    FREQUENT = "B"  # Top 10-20%
    COMMON = "C"  # Top 20-40%
    LESSER = "D"  # Top 40-50%
    UNCOMMON = "E"  # Bottom 50%
    RARE = "F"  # Very rare
    OBSCURE = "M"  # Graffiti/Slang/Obscure
    INSCRIPTION = "I"  # Only found in inscriptions
    UNKNOWN = "X"

    @classmethod
    def from_code(cls, code: str):
        # Handle cases where code might be None or whitespace
        if not code or code.strip() == "":
            return cls.UNKNOWN
        for member in cls:
            if member.value == code.upper():
                return member
        return cls.UNKNOWN


class LatinAge(Enum):
    ARCHAIC = "A"  # Pre-200 BC (Plautus, Terence)
    EARLY = "B"  # 200-100 BC
    CLASSICAL = "C"  # 100 BC - 14 AD (Cicero, Caesar, Augustus)
    SILVER = "D"  # 14-200 AD (Tacitus, Seneca)
    LATE = "E"  # 200-600 AD (Jerome, Augustine)
    MEDIEVAL = "F"  # 600-1600 AD
    MODERN = "G"  # 1600-Present (Scientific)
    GENERAL = "X"  # Used throughout ages
    UNKNOWN = "UNKNOWN"

    @classmethod
    def from_code(cls, code: str):
        if not code:
            return cls.UNKNOWN
        for member in cls:
            if member.value == code.upper():
                return member
        return cls.UNKNOWN


class PartOfSpeech(Enum):
    NOUN = "N"
    VERB = "V"
    ADJECTIVE = "ADJ"
    ADVERB = "ADV"
    PREPOSITION = "PREP"
    CONJUNCTION = "CONJ"
    INTERJECTION = "INTERJ"
    NUMERAL = "NUM"
    PRONOUN = "PRON"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def from_code(cls, code: str):
        if not code:
            return cls.UNKNOWN
        # Whitaker's sometimes outputs "ADJ" and sometimes "AD".
        # This handles simple matching.
        clean_code = code.upper().strip()
        for member in cls:
            if member.value == clean_code:
                return member
        return cls.UNKNOWN


FREQ_MAP = {
    "A": "Very Frequent (top 10%)",
    "B": "Frequent (top 20%)",
    "C": "Common",
    "D": "Less Common",
    "E": "Uncommon",
    "F": "Rare",
    "I": "Inscription Only",
    "M": "Obscure/Graffiti",
    "X": "Unknown Frequency",
}

AGE_MAP = {
    "A": "Archaic (Pre-200 BC)",
    "B": "Early (200-100 BC)",
    "C": "Classical (100 BC - 14 AD)",
    "D": "Silver (14-200 AD)",
    "E": "Late (200-600 AD)",
    "F": "Medieval (600+ AD)",
    "G": "Modern/Scientific",
    "X": "General/All Ages",
}

POS_MAP = {
    "N": "Noun",
    "V": "Verb",
    "ADJ": "Adjective",
    "ADV": "Adverb",
    "PRON": "Pronoun",
    "CONJ": "Conjunction",
    "PREP": "Preposition",
    "NUM": "Numeral",
    "INTERJ": "Interjection",
}

# GENDER_MAP is already defined above line 141 - removing duplicate assignment


def enrich_codeline_data(data: dict) -> dict:
    """
    Returns a NEW CodelineData object with readable English strings
    substituted for the raw Whitaker's codes.
    """
    new_data = data.copy()
    _enrich_frequency_field(new_data)
    _enrich_age_field(new_data)
    _enrich_source_field(new_data)
    raw_pos_code = _enrich_pos_code_field(new_data)
    _enrich_pos_form_field(new_data, raw_pos_code)
    return new_data


def _enrich_frequency_field(new_data: dict) -> None:
    raw_freq = new_data.get("freq", "").strip().upper()
    if raw_freq and _external_enums and "Frequency" in _external_enums:
        try:
            freq_enum = _external_enums["Frequency"]
            freq_value = freq_enum[raw_freq]
            new_data["freq"] = freq_value.value
            return
        except KeyError:
            pass
    if raw_freq:
        freq_map_fallback = {
            "A": "Very Frequent",
            "B": "Frequent",
            "C": "Common",
            "D": "Uncommon",
            "E": "Rare",
            "F": "Very Rare",
            "I": "Inscription",
            "M": "Graffiti",
            "N": "Plinius",
        }
        new_data["freq"] = freq_map_fallback.get(raw_freq, raw_freq)


def _enrich_age_field(new_data: dict) -> None:
    raw_age = new_data.get("age", "").strip().upper()
    if raw_age and _external_enums and "Age" in _external_enums:
        try:
            age_enum = _external_enums["Age"]
            age_value = age_enum[raw_age]
            new_data["age"] = age_value.value
            return
        except KeyError:
            pass
    if raw_age:
        age_map_fallback = {
            "A": "Archaic",
            "B": "Early",
            "C": "Classical",
            "D": "Late",
            "E": "Later",
            "F": "Medieval",
            "G": "Scholar",
            "H": "Modern",
            "X": "DEFAULT",
        }
        new_data["age"] = age_map_fallback.get(raw_age, raw_age)


def _enrich_source_field(new_data: dict) -> None:
    raw_source = new_data.get("source", "").strip().upper()
    if raw_source and _external_enums and "Source" in _external_enums:
        try:
            source_enum = _external_enums["Source"]
            source_value = source_enum[raw_source]
            new_data["source"] = source_value.value
            return
        except KeyError:
            pass
    if raw_source:
        source_map_fallback = {
            "A": "Unused 1",
            "B": "C.H.Beeson, A Primer of Medieval Latin, 1925 (Bee)",
            "C": "Charles Beard, Cassell's Latin Dictionary 1892 (CAS)",
            "D": "J.N.Adams, Latin Sexual Vocabulary, 1982 (Sex)",
            "E": "L.F.Stelten, Dictionary of Eccles. Latin, 1995 (Ecc)",
            "F": "Roy J. Deferrari, Dictionary of St. Thomas Aquinas, 1960 (DeF)",
            "G": "Gildersleeve + Lodge, Latin Grammar 1895 (G+L)",
            "H": "Collatinus Dictionary by Yves Ouvrard",
            "I": "Leverett, F.P., Lexicon of the Latin Language, Boston 1845",
            "J": "Unused 2",
            "K": "Calepinus Novus, modern Latin, by Guy Licoppe (Cal)",
            "L": "Lewis, C.S., Elementary Latin Dictionary 1891",
            "M": "Latham, Revised Medieval Word List, 1980",
            "N": "Lynn Nelson, Wordlist",
            "O": "Oxford Latin Dictionary, 1982 (OLD)",
            "P": "Souter, A Glossary of Later Latin to 600 A.D., Oxford 1949",
            "Q": "Other, cited or unspecified dictionaries",
            "R": "Plater & White, A Grammar of the Vulgate, Oxford 1926",
            "S": "Lewis and Short, A Latin Dictionary, 1879 (L+S)",
            "T": "Found in a translation -- no dictionary reference",
            "U": "Du Cange",
            "V": "Vademecum in opus Saxonis - Franz Blatt (Saxo)",
            "W": "My personal guess",
            "X": "General or unknown or too common to say",
            "Y": "Temp special code",
            "Z": "Sent by user",
        }
        new_data["source"] = source_map_fallback.get(raw_source, raw_source)


def _enrich_pos_code_field(new_data: dict) -> str:
    raw_pos_code = new_data.get("pos_code", "").strip().upper()
    if raw_pos_code:
        code = PartOfSpeech.from_code(raw_pos_code)
        if isinstance(code, PartOfSpeech):
            new_data["pos_code"] = POS_MAP.get(code.value, raw_pos_code)
    return raw_pos_code


def _enrich_pos_form_field(new_data: dict, raw_pos_code: str) -> None:
    raw_pos_form = new_data.get("pos_form", "").strip().upper()
    if not (raw_pos_form and raw_pos_code):
        return
    form = raw_pos_form
    if raw_pos_code == "N":
        new_data["pos_form"] = GENDER_MAP.get(form, form)
    elif raw_pos_code == "V":
        new_data["pos_form"] = f"{form} Conjugation"
    elif raw_pos_code == "ADJ":
        comparison = DEGREE_MAP.get(form)
        new_data["pos_form"] = comparison if comparison else f"{form} Declension"
    elif raw_pos_code == "ADV":
        new_data["pos_form"] = DEGREE_MAP.get(form, form)
    elif raw_pos_code == "PREP":
        new_data["pos_form"] = CASE_MAP.get(form, form)
    elif raw_pos_code == "PRON":
        new_data["pos_form"] = PRONOUN_TYPE_MAP.get(form, f"{form} Declension")
    elif raw_pos_code == "NUM":
        new_data["pos_form"] = NUMERAL_TYPE_MAP.get(form, f"{form} Declension")
    elif raw_pos_code in {"CONJ", "INTERJ"}:
        new_data["pos_form"] = None


def _enrich_term_data(data: dict) -> dict:
    """
    Enrich term data with readable morphology information from external enums.
    Translates raw codes (PRES, ACTIVE, IND, etc.) into human-readable strings.
    """
    new_data = data.copy()

    # Enrich Tense
    if new_data.get("tense"):
        tense_code = new_data["tense"].strip().upper()
        new_data["tense"] = TENSE_MAP.get(tense_code, tense_code)

    if new_data.get("part_of_speech"):
        part_of_speech_code = new_data["part_of_speech"].strip().capitalize()
        new_data["part_of_speech"] = part_of_speech_code

    # Enrich Voice
    if new_data.get("voice"):
        voice_code = new_data["voice"].strip().upper()
        new_data["voice"] = VOICE_MAP.get(voice_code, voice_code)

    # Enrich Mood
    if new_data.get("mood"):
        mood_code = new_data["mood"].strip().upper()
        new_data["mood"] = MOOD_MAP.get(mood_code, mood_code)

    # Enrich Person
    if new_data.get("person"):
        person_code = new_data["person"].strip()
        new_data["person"] = PERSON_MAP.get(person_code, person_code)

    # Enrich Number
    if new_data.get("number"):
        number_code = new_data["number"].strip().upper()
        new_data["number"] = NUMBER_MAP.get(number_code, number_code)

    # Enrich Case
    if new_data.get("case"):
        case_code = new_data["case"].strip().upper()
        new_data["case"] = CASE_MAP.get(case_code, case_code)

    # Enrich Gender
    if new_data.get("gender"):
        gender_code = new_data["gender"].strip().upper()
        new_data["gender"] = GENDER_MAP.get(gender_code, gender_code)

    # Enrich Comparison/Degree
    if new_data.get("comparison"):
        comp_code = new_data["comparison"].strip().upper()
        new_data["comparison"] = DEGREE_MAP.get(comp_code, comp_code)

    return new_data


@dataclass
class WhitakerWordParts:
    stem: str
    ending: str


@dataclass
class WhitakerWordData:
    term: str
    part_of_speech: str
    declension: str | None = field(default=None)
    case: str | None = field(default=None)
    number: str | None = field(default=None)
    gender: str | None = field(default=None)
    variant: str | None = field(default=None)
    comparison: str | None = field(default=None)
    term_analysis: WhitakerWordParts | None = field(default=None)
    conjugation: str | None = field(default=None)
    tense: str | None = field(default=None)
    voice: str | None = field(default=None)
    mood: str | None = field(default=None)
    person: str | None = field(default=None)


@dataclass
class WhitakersWordsT:
    unknown: list[str] | None = field(default=None)
    raw_lines: list[str] = field(default_factory=list)
    senses: list[str] = field(default_factory=list)
    terms: list[WhitakerWordData] = field(default_factory=list)
    codeline: CodelineData | CodelineName | None = field(default=None)


@dataclass
class WhitakersWordsResult:
    wordlist: list[WhitakersWordsT]


class _WhitakersProcHolder:
    _instance: "_WhitakersProcHolder | None" = None
    proc: "Command | None" = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get(self) -> "Command | None":
        if self.proc is not None:
            return self.proc

        home = Path.home()
        maybe_words = home / ".local/bin/whitakers-words"
        if maybe_words.exists():
            logger.info("using_whitakers_binary", path=str(maybe_words))
            self.proc = Command(maybe_words).bake(_tty=False, _tty_out=False, _tty_in=False)
            return self.proc
        maybe_words = Path() / "deps/whitakers-words/bin/words"
        if maybe_words.exists():
            logger.info("using_whitakers_binary", path=str(maybe_words))
            self.proc = Command(maybe_words).bake(_tty=False, _tty_out=False, _tty_in=False)
            return self.proc
        else:
            logger.warning("whitakers_binary_not_found")
            test_cmd = Command("test")
            self.proc = test_cmd.bake("!", "-z", _tty=False, _tty_out=False, _tty_in=False)
            return self.proc


_holder = _WhitakersProcHolder()


def get_whitakers_proc() -> "Command | None":
    return _holder.get()


# def fixlines(lines):
#     fixed_lines = []
#     for line in lines:
#         if line.startswith(" "):
#             fixed_lines[len(fixed_lines) - 1] += line
#         else:
#             fixed_lines.append(line)
#     return fixed_lines
def fixup(wordlist):
    fixed_words = []
    for word in wordlist:
        codeline = word.get("codeline", None)
        if codeline is not None:
            # Add term from first term if codeline doesn't have one
            if not codeline.get("term") and word.get("terms"):
                codeline["term"] = word["terms"][0]["term"]
            codeline = enrich_codeline_data(codeline)
            word["codeline"] = codeline

        # Enrich term data with morphology
        terms = word.get("terms", [])
        if terms:
            enriched_terms = [_enrich_term_data(term) for term in terms]
            word["terms"] = enriched_terms

        fixed_words.append(word)
    logger.debug("fixup_completed", input_count=len(wordlist), output_count=len(fixed_words))
    return fixed_words


class WhitakersWordsChunker:
    # https://sourceforge.net/p/wwwords/wiki/wordsdoc.htm/

    # TODO: this is blowing up if not available
    # should be a litle nicer and just have some error state like 'dont use me'

    ww = get_whitakers_proc()
    # Command(Path.home() / ".local/bin/whitakers-words")
    term_pattern = r"^[a-z.]+(?:\.[a-z]+)*\s+[A-Z]+"

    def __init__(self, input: list[str]):
        # we might be in a special input mode
        # need special output parsing for that case
        self.input = input
        # Disable TTY allocation to work in sandboxed environments
        self.result: str = self.ww(*input, _tty=False, _encoding="utf-8")  # type: ignore[assignment]

    def classify_line(self, line):
        line_type = None
        if ";" in line:
            line_type = "sense"
        elif "]" in line:
            line_type = "term-code"
        elif (
            "RETURN/ENTER" in line
            or "exception in PAUSE" in line
            or line == "*"
            or line.startswith("Word mod")
            or "An internal 'b'" in line
        ):
            line_type = "ui-control"
        elif line.strip() == "":
            line_type = "empty"
        elif re.match(self.term_pattern, line):
            line_type = "term-facts"
        else:
            line_type = "unknown"
        logger.debug("classify_line", line_preview=line[:50], line_type=line_type)
        return dict(line_txt=line, line_type=line_type)

    def get_next_word(self, current: dict | None, last_line: dict | None, line_info: dict) -> dict:
        next_word: dict = dict(lines=[line_info])
        start_new_word = False

        if not last_line:
            start_new_word = True
            logger.debug("get_next_word_first_line", start_new_word=True)
        else:
            this_line_type = line_info["line_type"]
            last_line_type = last_line["line_type"]
            if last_line_type == "term-code":
                start_new_word = this_line_type != "sense"
            elif last_line_type == "sense":
                if this_line_type == "unknown":
                    pass
                else:
                    start_new_word = this_line_type != "sense"
            elif last_line_type == "unknown":
                start_new_word = this_line_type.startswith("term-")

            logger.debug(
                "get_next_word_state",
                last_line_type=last_line_type,
                this_line_type=this_line_type,
                start_new_word=start_new_word,
            )

        if start_new_word:
            return next_word
        else:
            assert current is not None
            current["lines"].append(line_info)
            return current

    def analyze_chunk(self, entry: dict):
        entry["txts"] = txts = []
        entry["types"] = types = []
        for line in entry["lines"]:
            line_type = line["line_type"]
            line_txt = line["line_txt"]
            if line_type in {"ui-control", "empty"}:
                pass
            else:
                txts.append(line_txt)
                types.append(line_type)
        entry["size"] = len(txts)
        del entry["lines"]
        logger.debug("analyze_chunk", entry_size=entry["size"], type_count=len(types))

    def get_word_chunks(self):
        word_chunks = []
        current_word = None
        last_line = None
        for line in self.result.splitlines():
            line_info = self.classify_line(line)
            next_word = self.get_next_word(current_word, last_line, line_info)
            # print(f"I think the next word is: {next_word}")
            last_line = line_info
            if next_word is not current_word:
                current_word = next_word
                word_chunks.append(current_word)
        for chunk in word_chunks:
            self.analyze_chunk(chunk)
        return word_chunks


class WhitakersWords:
    @staticmethod
    def smart_merge(src: dict, dest: dict):
        for k, v in src.items():
            if k in dest:
                _v = dest[k]
                if v == _v:
                    pass
                else:
                    # Only warn for non-list collisions (e.g., codeline with different values)
                    # List concatenation (senses, terms) is expected behavior
                    if not (isinstance(v, list) or isinstance(_v, list)):
                        logger.warning("merge_collision", key=k, src_value=v, dest_value=_v)
                    if isinstance(v, list) and isinstance(_v, list):
                        dest[k] = _v + v  # Preserve order: existing first, then new
                    elif isinstance(v, list):
                        dest[k] = [f"{_v}".strip()] + v  # Convert single to list, prepend
                    elif isinstance(_v, list):
                        dest[k] = _v + [f"{v}".strip()]  # Append single to existing list
                    else:
                        pass  # Non-list collision: preserve existing, drop new
            else:
                dest[k] = v

    @staticmethod
    def process_chunk(word_chunk: dict, word: dict, terms: list, unknown: list, lines: list):
        for i in range(word_chunk["size"]):
            (txt, line_type) = (word_chunk["txts"][i], word_chunk["types"][i])
            lines.append(txt)
            if line_type == "sense":
                data = SensesReducer.reduce(txt)
                WhitakersWords.smart_merge(data, word)
            elif line_type == "term-facts":
                data = FactsReducer.reduce(txt)
                terms.append(data)
            elif line_type == "term-code":
                data = CodesReducer.reduce(txt)
                WhitakersWords.smart_merge(dict(codeline=data), word)
            elif line_type == "unknown":
                unknown.append(txt)
            else:
                assert False, f"Unexpected line type! [{line_type}]"

    @staticmethod
    def create_word_structure(word_chunk: dict) -> dict | None:
        unknown = []
        terms = []
        lines = []
        word = dict(terms=terms, raw_lines=lines, unknown=unknown)
        WhitakersWords.process_chunk(word_chunk, word, terms, unknown, lines)
        if len(unknown) == 0:
            del word["unknown"]
        return word if lines else None

    @staticmethod
    def words(search: list[str]) -> WhitakersWordsResult:
        words_chunker = WhitakersWordsChunker(search)
        chunks = words_chunker.get_word_chunks()
        wordlist = []

        for word_chunk in chunks:
            word_structure = WhitakersWords.create_word_structure(word_chunk)
            if word_structure:
                wordlist.append(word_structure)

        structured_wordlist = []
        # print("in words fn")
        for w in fixup(wordlist):
            try:
                structured_wordlist.append(cattrs.structure(w, WhitakersWordsT))
            except Exception as e:
                logger.error("cattrs_structure_failed", word=str(w)[:100], error=str(e))
                raise

        logger.debug("whitakers_words_completed", word_count=len(structured_wordlist))
        return WhitakersWordsResult(wordlist=structured_wordlist)
