from pathlib import Path

from lark import Lark, Transformer, Tree


def get_term_facts_grammar():
    grammar_path = Path(__file__).parent / "grammars" / "term_facts.ebnf"
    return grammar_path.read_text()


class FactsTransformer(Transformer):
    def __named_token(self, args, name):
        item = args[0]
        if type(item) == Tree:
            item = item.children[0]
        token = f"{item}".strip()
        return {name: token}

    def conjugation(self, args):
        return self.__named_token(args, "conjugation")

    def declension(self, args):
        return self.__named_token(args, "declension")

    def variant(self, args):
        return self.__named_token(args, "variant")

    def notes(self, args):
        return self.__named_token(args, "notes")

    def comparison(self, args):
        return self.__named_token(args, "comparison")

    def person(self, args):
        return self.__named_token(args, "person")

    def gender(self, args):
        return self.__named_token(args, "gender")

    def case(self, args):
        return self.__named_token(args, "case")

    def number(self, args):
        return self.__named_token(args, "number")

    def tense(self, args):
        return self.__named_token(args, "tense")

    def voice(self, args):
        return self.__named_token(args, "voice")

    def mood(self, args):
        return self.__named_token(args, "mood")

    def term(self, args):
        term = f"{args[0]}"
        parts = term.split(".")
        if len(parts) > 1:
            return dict(term=term, term_analysis=dict(stem=parts[0], ending=".".join(parts[1:])))
        else:
            return dict(term=term)

    def start(self, args):
        return args[0]

    def __assemble_args(self, args, part_of_speech):
        obj = dict(part_of_speech=part_of_speech)
        for arg in args:
            if arg is not None:
                obj.update(arg)
        # print("assemble args", args)
        return obj

    def noun_line(self, args):
        return self.__assemble_args(args, "noun")

    def verb_line(self, args):
        return self.__assemble_args(args, "verb")

    def adverb_line(self, args):
        return self.__assemble_args(args, "adverb")

    def pronoun_line(self, args):
        return self.__assemble_args(args, "pronoun")

    def adjective_line(self, args):
        return self.__assemble_args(args, "adjective")

    def conjunction_line(self, args):
        return self.__assemble_args(args, "conjunction")

    def verb_participle_line(self, args):
        return self.__assemble_args(args, "verb-participle")

    def pack_line(self, args):
        return self.__assemble_args(args, "pack")

    def preposition_line(self, args):
        return self.__assemble_args(args, "preposition")

    def tack_line(self, args):
        return self.__assemble_args(args, "tackon")

    def interj_line(self, args):
        return self.__assemble_args(args, "interjection")

    def num_line(self, args):
        return self.__assemble_args(args, "numerator")

    def card_line(self, args):
        return self.__assemble_args(args, "cardinal")

    def suffix_line(self, args):
        return self.__assemble_args(args, "suffix")

    def prefix_line(self, args):
        return self.__assemble_args(args, "prefix")

    def supine_line(self, args):
        return self.__assemble_args(args, "supine")


class FactsReducer:
    parser = Lark(get_term_facts_grammar())
    xformer = FactsTransformer()

    @staticmethod
    def reduce(line):
        tree = FactsReducer.parser.parse(line)
        result = FactsReducer.xformer.transform(tree)
        return result
