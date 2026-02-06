import re
from dataclasses import dataclass, asdict, field
from pathlib import Path

import cattrs
import structlog
from sh import Command

from enum import Enum, auto

import langnet.logging  # noqa: F401 - ensures logging is configured before use


from .lineparsers import CodesReducer, FactsReducer, SensesReducer

logger = structlog.get_logger(__name__)


@dataclass
class CodelineName:
    names: list[str]
    notes: list[str] | None = field(default=None)


@dataclass
class CodelineData:
    term: str
    notes: list[str] | None = field(default=None)
    age: str | None = field(default="X")
    source: str | None = field(default="X")
    freq: str | None = field(default="X")
    declension: str | None = field(default=None)
    pos_form: str | None = field(default=None)
    pos_code: str | None = field(default=None)


class Frequency(Enum):
    VERY_FREQUENT = "A"  # Top 10%
    FREQUENT = "B"       # Top 10-20%
    COMMON = "C"         # Top 20-40%
    LESSER = "D"         # Top 40-50%
    UNCOMMON = "E"       # Bottom 50%
    RARE = "F"           # Very rare
    OBSCURE = "M"        # Graffiti/Slang/Obscure
    INSCRIPTION = "I"    # Only found in inscriptions
    UNKNOWN = "X"
    
    @staticmethod
    def from_code(cls, code: str):
        # Handle cases where code might be None or whitespace
        if not code or code.strip() == "": return cls.UNKNOWN
        for member in cls:
            if member.value == code.upper(): return member
        return cls.UNKNOWN

class LatinAge(Enum):
    ARCHAIC = "A"      # Pre-200 BC (Plautus, Terence)
    EARLY = "B"        # 200-100 BC
    CLASSICAL = "C"    # 100 BC - 14 AD (Cicero, Caesar, Augustus)
    SILVER = "D"       # 14-200 AD (Tacitus, Seneca)
    LATE = "E"         # 200-600 AD (Jerome, Augustine)
    MEDIEVAL = "F"     # 600-1600 AD
    MODERN = "G"       # 1600-Present (Scientific)
    GENERAL = "X"      # Used throughout ages
    UNKNOWN = "UNKNOWN"

    @staticmethod
    def from_code(cls, code: str):
        if not code: return cls.UNKNOWN
        for member in cls:
            if member.value == code.upper(): return member
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

    @staticmethod
    def from_code(cls, code: str):
        if not code: return cls.UNKNOWN
        # Whitaker's sometimes outputs "ADJ" and sometimes "AD".
        # This handles simple matching.
        clean_code = code.upper().strip()
        for member in cls:
            if member.value == clean_code: return member
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
    "X": "Unknown Frequency"
}

AGE_MAP = {
    "A": "Archaic (Pre-200 BC)",
    "B": "Early (200-100 BC)",
    "C": "Classical (100 BC - 14 AD)",
    "D": "Silver (14-200 AD)",
    "E": "Late (200-600 AD)",
    "F": "Medieval (600+ AD)",
    "G": "Modern/Scientific",
    "X": "General/All Ages"
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
    "INTERJ": "Interjection"
}

GENDER_MAP = {'M': 'Masculine', 'F': 'Feminine', 'N': 'Neuter', 'C': 'Common'}

def enrich_codeline_data(data: dict) -> dict:
    """
    Returns a NEW CodelineData object with readable English strings 
    substituted for the raw Whitaker's codes.
    """
    # Create a shallow copy so we don't mutate the original object in place
    # (Good practice to avoid side effects)
    # new_data = dataclasses.replace(data)
    new_data = data.copy()
    # asdict(data)

    # print("before xform")
    # print(new_data)

    raw_freq = new_data.get("freq", "").strip().upper()
    # 1. Enrich Frequency
    if raw_freq:
        # Check the first char just in case strict formatting is loose
        code = Frequency.from_code(Frequency, raw_freq)
        if isinstance(code, Frequency):
            new_data["freq"] = FREQ_MAP.get(code.value, f"Unknown Frequency: {raw_freq}")

    # 2. Enrich Age
    raw_age = new_data.get("age", "").strip().upper()
    if raw_age:
        code = LatinAge.from_code(LatinAge, raw_age)
        # Some Whitaker's implementations might pass longer strings, handle generic fallback
        if isinstance(code, LatinAge):
            new_data["age"] = AGE_MAP.get(code.value, f"Unknown Age: {raw_age}")

    # 3. Enrich Part of Speech (POS)
    # We need to remember the RAW code for step 4 (contextual parsing)
    raw_pos_code = new_data.get("pos_code", "").strip().upper()
 
    if raw_pos_code:
        code =  PartOfSpeech.from_code(PartOfSpeech, raw_pos_code)
        if isinstance(code, PartOfSpeech):
            new_data["pos_code"] = POS_MAP.get(code.value, raw_pos_code)

    # 4. Enrich 'pos_form' based on what the POS was
    # Whitaker's reuses this field (Gender for Nouns, Conjugation for Verbs)
    raw_pos_form = new_data.get("pos_form", "").strip().upper()
    
    if raw_pos_form and raw_pos_code:
        form = raw_pos_form

        if raw_pos_code == "N": # Noun - Form is GENDEr
            new_data["pos_form"] = GENDER_MAP.get(form, form)
        
        elif raw_pos_code == "V": # Verb - Form is CONJUGATION
            new_data["pos_form"] = f"{form} Conjugation"
            
        elif raw_pos_code == "ADJ": # Adjective - Form is DECLENSION
            new_data["pos_form"] = f"{form} Declension"

    # print("wow")
    # print(new_data)

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
            self.proc = Command(maybe_words)
            return self.proc
        maybe_words = Path() / "deps/whitakers-words/bin/words"
        if maybe_words.exists():
            logger.info("using_whitakers_binary", path=str(maybe_words))
            self.proc = Command(maybe_words)
            return self.proc
        else:
            logger.warning("whitakers_binary_not_found")
            test_cmd = Command("test")
            self.proc = test_cmd.bake("!", "-z")
            return self.proc


_holder = _WhitakersProcHolder()


def get_whitakers_proc() -> "Command | None":
    return _holder.get()

    home = Path.home()
    maybe_words = home / ".local/bin/whitakers-words"
    if maybe_words.exists():
        logger.info("using_whitakers_binary", path=str(maybe_words))
        _cached_whitakers_proc = Command(maybe_words)
        return _cached_whitakers_proc
    maybe_words = Path() / "deps/whitakers-words/bin/words"
    if maybe_words.exists():
        logger.info("using_whitakers_binary", path=str(maybe_words))
        _cached_whitakers_proc = Command(maybe_words)
        return _cached_whitakers_proc
    else:
        logger.warning("whitakers_binary_not_found")
        test_cmd = Command("test")
        _cached_whitakers_proc = test_cmd.bake("!", "-z")
        return _cached_whitakers_proc


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
        # print("hihi", enrich_codeline_data(codeline))
        if codeline is not None:
            codeline = enrich_codeline_data(codeline)
            word["codeline"] = codeline
            # word["codeline"] = codeline
            # maybe_term = codeline.get("term", None)
            # if maybe_term is None:
            #     codeline["term"] = word["terms"][0]["term"]
            #     word["codeline"] = enrich_codeline_data(codeline)
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
        self.result: str = self.ww(*input, _encoding="utf-8")  # type: ignore[assignment]

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
                    logger.warning("merge_collision", key=k, src_value=v, dest_value=_v)
                    if isinstance(v, list) and isinstance(_v, list):
                        dest[k] = v + _v
                    elif isinstance(v, list):
                        dest[k] = v + [f"{_v}".strip()]
                    elif isinstance(_v, list):
                        dest[k] = _v + [f"{v}".strip()]
                    else:
                        pass
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
        print("in words fn")
        for w in fixup(wordlist):
            try:
                structured_wordlist.append(cattrs.structure(w, WhitakersWordsT))
            except Exception as e:
                logger.error("cattrs_structure_failed", word=str(w)[:100], error=str(e))
                raise

        logger.debug("whitakers_words_completed", word_count=len(structured_wordlist))
        return WhitakersWordsResult(wordlist=structured_wordlist)
