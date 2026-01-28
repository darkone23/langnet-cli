import re
from dataclasses import dataclass, field
from pathlib import Path

import cattrs
import structlog
from sh import Command

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
    age: str | None = field(default=None)
    source: str | None = field(default=None)
    freq: str | None = field(default=None)
    declension: str | None = field(default=None)
    pos_form: str | None = field(default=None)
    pos_code: str | None = field(default=None)


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


_cached_whitakers_proc = None


def get_whitakers_proc():
    global _cached_whitakers_proc
    if _cached_whitakers_proc is not None:
        return _cached_whitakers_proc

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
        if codeline is not None:
            maybe_term = codeline.get("term", None)
            if maybe_term is None:
                codeline["term"] = word["terms"][0]["term"]
                word["codeline"] = codeline
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
            if line_type == "ui-control" or line_type == "empty":
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
    def words(search: list[str]) -> WhitakersWordsResult:
        words_chunker = WhitakersWordsChunker(search)
        chunks = words_chunker.get_word_chunks()
        wordlist = []

        def smart_merge(src: dict, dest: dict):
            for k, v in src.items():
                if k in dest:
                    _v = dest[k]
                    if v == _v:
                        pass
                    else:
                        logger.warning("merge_collision", key=k, src_value=v, dest_value=_v)
                        if type(v) == list and type(_v) == list:
                            dest[k] = v + _v
                        elif type(v) == list:
                            dest[k] = v + [f"{_v}".strip()]
                        elif type(_v) == list:
                            dest[k] = _v + [f"{v}".strip()]
                        else:
                            pass
                else:
                    dest[k] = v

        for word_chunk in chunks:
            unknown = []
            terms = []
            lines = []
            word = dict(terms=terms, raw_lines=lines, unknown=unknown)
            for i in range(word_chunk["size"]):
                (txt, line_type) = (word_chunk["txts"][i], word_chunk["types"][i])
                # print(line_type, txt)
                lines.append(txt)
                if line_type == "sense":
                    data = SensesReducer.reduce(txt)
                    smart_merge(data, word)
                elif line_type == "term-facts":
                    data = FactsReducer.reduce(txt)
                    terms.append(data)
                elif line_type == "term-code":
                    data = CodesReducer.reduce(txt)
                    smart_merge(dict(codeline=data), word)
                elif line_type == "unknown":
                    unknown.append(txt)
                else:
                    assert False, f"Unexpected line type! [{line_type}]"
            if len(unknown) == 0:
                del word["unknown"]
            if lines:
                wordlist.append(word)

        structured_wordlist = []
        for w in fixup(wordlist):
            try:
                structured_wordlist.append(cattrs.structure(w, WhitakersWordsT))
            except Exception as e:
                logger.error("cattrs_structure_failed", word=str(w)[:100], error=str(e))
                raise

        logger.debug("whitakers_words_completed", word_count=len(structured_wordlist))
        return WhitakersWordsResult(wordlist=structured_wordlist)
