import sys
import re
from pathlib import Path
from lark import Lark, Transformer


def get_senses_grammar():
    grammar_path = Path(__file__).parent / "grammars" / "senses.ebnf"
    return grammar_path.read_text()


class SenseTransformer(Transformer):
    def start(self, args):
        return args[0]

    def extract_parentheses_text(self, text):
        text = (
            text.replace("(", "{").replace(")", "}").replace("[", "(").replace("]", ")")
        )
        extracted = " ".join(
            re.findall(r"\((.*?)\)", text, re.DOTALL)
        )  # Extract text inside parentheses, including newlines
        cleaned_text = re.sub(
            r"\s*\(.*?\)\s*", " ", text, flags=re.DOTALL
        ).strip()  # Remove parentheses and enclosed text
        cleaned_text = cleaned_text.replace("{", "(").replace("}", ")")
        return (cleaned_text, extracted.strip())

    def sense(self, tokens):
        words = []
        for token in tokens:
            (word_part, notes_part) = self.extract_parentheses_text(f"{token}".strip())
            word = dict(sense=word_part, note=notes_part)
            words.append(word)
        return words

    def sense_line(self, tree):
        senses = []
        notes = []
        for node in tree:
            for sense in node:
                # print(sense)
                (s, n) = (sense["sense"], sense["note"])
                if s:
                    senses.append(s)
                if n:
                    notes.append(n)
        obj = dict(senses=senses, notes=notes)
        if len(notes) == 0:
            del obj["notes"]
        return obj


class SensesReducer:
    parser = Lark(get_senses_grammar())
    xformer = SenseTransformer()

    @staticmethod
    def reduce(line):
        tree = SensesReducer.parser.parse(line)
        result = SensesReducer.xformer.transform(tree)
        return result
