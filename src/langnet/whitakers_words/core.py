from sh import Command
from pathlib import Path
import re

from .lineparsers import FactsReducer, SensesReducer, CodesReducer


from pydantic import BaseModel, Field


class CodelineName(BaseModel):
    notes: list[str] | None = Field(default=None)
    names: list[str]


class CodelineData(BaseModel):
    term: str
    notes: list[str] | None = Field(default=None)
    age: str | None = Field(default=None)
    source: str | None = Field(default=None)
    freq: str | None = Field(default=None)
    declension: str | None = Field(default=None)
    pos_form: str | None = Field(default=None)
    pos_code: str | None = Field(default=None)


class WhitakerWordParts(BaseModel):
    stem: str
    ending: str


class WhitakerWordData(BaseModel):
    declension: str | None = Field(default=None)
    case: str | None = Field(default=None)
    number: str | None = Field(default=None)
    gender: str | None = Field(default=None)
    variant: str | None = Field(default=None)
    comparison: str | None = Field(default=None)
    term_analysis: WhitakerWordParts | None = Field(default=None)
    term: str
    part_of_speech: str


class WhitakersWordsT(BaseModel):
    unknown: list[str] | None = Field(default=None)
    raw_lines: list[str] = Field(default=[])
    senses: list[str] = Field(default=[])
    terms: list[WhitakerWordData] = Field(default=[])
    codeline: CodelineData | CodelineName | None = Field(default=None)


class WhitakersWordsResult(BaseModel):
    wordlist: list[WhitakersWordsT]


def get_whitakers_proc():
    home = Path.home()
    maybe_words = home / ".local/bin/whitakers-words"
    if maybe_words.exists():
        return Command(maybe_words)
    maybe_words = Path() / "deps/whitakers-words/bin/words"
    if maybe_words.exists():
        return Command(maybe_words)
    else:
        test_cmd = Command("test")
        return test_cmd.bake("!", "-z")  # test non empty str


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
        self.result = self.ww(*input)

    def classify_line(self, line):
        line_type = None
        if ";" in line:
            line_type = "sense"
        elif "]" in line:
            line_type = "term-code"
        elif "RETURN/ENTER" in line or "exception in PAUSE" in line or "*" == line:
            line_type = "ui-control"
        elif line.startswith("Word mod") or "An internal 'b'" in line:
            line_type = "ui-control"
        elif line.strip() == "":
            line_type = "empty"
        elif re.match(self.term_pattern, line):
            line_type = "term-facts"
        else:
            line_type = "unknown"
        return dict(line_txt=line, line_type=line_type)

    def get_next_word(
        self, current: dict | None, last_line: dict | None, line_info: dict
    ):
        next_word = dict(lines=[line_info])
        start_new_word = False

        if not last_line:
            start_new_word = True
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

        if start_new_word:
            return next_word
        else:
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
            if len(lines):
                wordlist.append(word)
        return WhitakersWordsResult(wordlist=fixup(wordlist))
