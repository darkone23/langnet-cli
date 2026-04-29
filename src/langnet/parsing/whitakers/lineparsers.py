"""Lark reducers for Whitaker's Words line-oriented output."""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from lark import Lark, Transformer, Tree
from lark.visitors import Discard

_GRAMMAR_DIR = Path(__file__).parent / "grammars"


def _grammar(name: str) -> str:
    return (_GRAMMAR_DIR / name).read_text(encoding="utf-8")


class SenseTransformer(Transformer):
    """Transform Whitaker semicolon-separated sense lines."""

    def start(self, args: list[object]) -> object:
        return args[0]

    def sense(self, tokens: list[object]) -> list[dict[str, str]]:
        words: list[dict[str, str]] = []
        for token in tokens:
            word_part, notes_part = self._extract_parentheses_text(str(token).strip())
            words.append({"sense": word_part, "note": notes_part})
        return words

    def sense_line(self, tree: list[object]) -> dict[str, list[str]]:
        senses: list[str] = []
        notes: list[str] = []
        for node in tree:
            if not isinstance(node, list):
                continue
            for sense in node:
                if not isinstance(sense, dict):
                    continue
                sense_map = cast(Mapping[str, object], sense)
                sense_text = str(sense_map.get("sense") or "")
                note_text = str(sense_map.get("note") or "")
                if sense_text:
                    senses.append(sense_text)
                if note_text:
                    notes.append(note_text)
        result = {"senses": senses}
        if notes:
            result["notes"] = notes
        return result

    def _extract_parentheses_text(self, text: str) -> tuple[str, str]:
        working = text.replace("(", "{").replace(")", "}").replace("[", "(").replace("]", ")")
        extracted = " ".join(re.findall(r"\((.*?)\)", working, re.DOTALL))
        cleaned = re.sub(r"\s*\(.*?\)\s*", " ", working, flags=re.DOTALL).strip()
        return cleaned.replace("{", "(").replace("}", ")"), extracted.strip()


class SensesReducer:
    """Parse Whitaker sense lines."""

    parser = Lark(_grammar("senses.ebnf"))
    xformer = SenseTransformer()

    @staticmethod
    def reduce(line: str) -> dict[str, object]:
        tree = SensesReducer.parser.parse(line)
        return cast(dict[str, object], SensesReducer.xformer.transform(tree))


class CodesTransformer(Transformer):
    """Transform Whitaker dictionary codelines."""

    def start(self, args: list[object]) -> object:
        return args[0]

    def code_chunk(self, leaves: list[Tree]) -> object:
        entries: dict[str, object] = {}
        for tree in leaves:
            for leaf in tree.children:
                if isinstance(leaf, dict):
                    entries.update(cast(dict[str, object], leaf))
        return entries if entries else Discard

    def notes(self, args: list[object]) -> dict[str, list[str]] | list[object]:
        for item in args:
            return {"notes": str(item).strip().split()}
        return args

    def proper_names(self, args: list[Tree]) -> dict[str, list[str]]:
        names: list[str] = []
        for item in args:
            for child in item.children:
                names.append(str(child))
        return {"names": names}

    def pos_code(self, args: list[object]) -> dict[str, str]:
        return {"pos_code": str(args[0])}

    def declension(self, args: list[object]) -> dict[str, str]:
        return {"declension": str(args[0])}

    def pos_form(self, args: list[object]) -> dict[str, str]:
        return {"pos_form": str(args[0])}

    def term_info(self, args: list[object]) -> list[object]:
        return args

    def term_txt(self, args: list[object]) -> dict[str, str]:
        return {"term": str(args[0]).strip()}

    def age(self, args: list[object]) -> object:
        return self._code_dict(args, "age")

    def area(self, args: list[object]) -> object:
        return self._code_dict(args, "area")

    def geo(self, args: list[object]) -> object:
        return self._code_dict(args, "geo")

    def freq(self, args: list[object]) -> object:
        return self._code_dict(args, "freq")

    def source(self, args: list[object]) -> object:
        return self._code_dict(args, "source")

    def simple_code_line(self, args: list[object]) -> dict[str, object]:
        return self._flatten(args)

    def full_code_line(self, args: list[object]) -> dict[str, object]:
        return self._flatten(args)

    def basic_code_line(self, args: list[object]) -> dict[str, object]:
        return self._flatten(args)

    def _code_dict(self, args: list[object], key: str) -> object:
        code = self._handle_code(args)
        return {key: code} if code is not None else Discard

    def _handle_code(self, leaves: list[object]) -> str | None:
        for tree in leaves:
            if not isinstance(tree, Tree):
                continue
            for leaf in tree.children:
                code = str(leaf)
                if code == "X":
                    return None
                return code
        return None

    def _flatten(self, args: list[object]) -> dict[str, object]:
        result: dict[str, object] = {}
        for item in args:
            if isinstance(item, list):
                for subitem in item:
                    if isinstance(subitem, dict):
                        result.update(cast(dict[str, object], subitem))
            elif isinstance(item, dict):
                result.update(cast(dict[str, object], item))
        return result


class CodesReducer:
    """Parse Whitaker dictionary codelines."""

    parser = Lark(_grammar("term_codes.ebnf"))
    xformer = CodesTransformer()

    @staticmethod
    def reduce(line: str) -> dict[str, object]:
        tree = CodesReducer.parser.parse(line)
        return cast(dict[str, object], CodesReducer.xformer.transform(tree))


class FactsTransformer(Transformer):
    """Transform Whitaker morphology fact lines."""

    def conjugation(self, args: list[object]) -> dict[str, str]:
        return self._named_token(args, "conjugation")

    def declension(self, args: list[object]) -> dict[str, str]:
        return self._named_token(args, "declension")

    def variant(self, args: list[object]) -> dict[str, str]:
        return self._named_token(args, "variant")

    def notes(self, args: list[object]) -> dict[str, str]:
        return self._named_token(args, "notes")

    def comparison(self, args: list[object]) -> dict[str, str]:
        return self._named_token(args, "comparison")

    def person(self, args: list[object]) -> dict[str, str]:
        return self._named_token(args, "person")

    def gender(self, args: list[object]) -> dict[str, str]:
        return self._named_token(args, "gender")

    def case(self, args: list[object]) -> dict[str, str]:
        return self._named_token(args, "case")

    def number(self, args: list[object]) -> dict[str, str]:
        return self._named_token(args, "number")

    def tense(self, args: list[object]) -> dict[str, str]:
        return self._named_token(args, "tense")

    def voice(self, args: list[object]) -> dict[str, str]:
        return self._named_token(args, "voice")

    def mood(self, args: list[object]) -> dict[str, str]:
        return self._named_token(args, "mood")

    def term(self, args: list[object]) -> dict[str, object]:
        term = str(args[0])
        stem, dot, ending = term.partition(".")
        if dot:
            return {"term": term, "term_analysis": {"stem": stem, "ending": ending}}
        return {"term": term}

    def start(self, args: list[object]) -> object:
        return args[0]

    def noun_line(self, args: list[object]) -> dict[str, object]:
        return self._assemble_args(args, "noun")

    def verb_line(self, args: list[object]) -> dict[str, object]:
        return self._assemble_args(args, "verb")

    def adverb_line(self, args: list[object]) -> dict[str, object]:
        return self._assemble_args(args, "adverb")

    def pronoun_line(self, args: list[object]) -> dict[str, object]:
        return self._assemble_args(args, "pronoun")

    def adjective_line(self, args: list[object]) -> dict[str, object]:
        return self._assemble_args(args, "adjective")

    def conjunction_line(self, args: list[object]) -> dict[str, object]:
        return self._assemble_args(args, "conjunction")

    def verb_participle_line(self, args: list[object]) -> dict[str, object]:
        return self._assemble_args(args, "verb-participle")

    def pack_line(self, args: list[object]) -> dict[str, object]:
        return self._assemble_args(args, "pack")

    def preposition_line(self, args: list[object]) -> dict[str, object]:
        return self._assemble_args(args, "preposition")

    def tack_line(self, args: list[object]) -> dict[str, object]:
        return self._assemble_args(args, "tackon")

    def interj_line(self, args: list[object]) -> dict[str, object]:
        return self._assemble_args(args, "interjection")

    def num_line(self, args: list[object]) -> dict[str, object]:
        return self._assemble_args(args, "numerator")

    def card_line(self, args: list[object]) -> dict[str, object]:
        return self._assemble_args(args, "cardinal")

    def suffix_line(self, args: list[object]) -> dict[str, object]:
        return self._assemble_args(args, "suffix")

    def prefix_line(self, args: list[object]) -> dict[str, object]:
        return self._assemble_args(args, "prefix")

    def supine_line(self, args: list[object]) -> dict[str, object]:
        return self._assemble_args(args, "supine")

    def _named_token(self, args: list[object], name: str) -> dict[str, str]:
        item = args[0]
        if isinstance(item, Tree):
            item = item.children[0]
        return {name: str(item).strip()}

    def _assemble_args(self, args: list[object], part_of_speech: str) -> dict[str, object]:
        result: dict[str, object] = {"part_of_speech": part_of_speech}
        for arg in args:
            if isinstance(arg, dict):
                result.update(cast(dict[str, object], arg))
        return result


class FactsReducer:
    """Parse Whitaker morphology fact lines."""

    parser = Lark(_grammar("term_facts.ebnf"))
    xformer = FactsTransformer()

    @staticmethod
    def reduce(line: str) -> dict[str, object]:
        tree = FactsReducer.parser.parse(line)
        return cast(dict[str, object], FactsReducer.xformer.transform(tree))
