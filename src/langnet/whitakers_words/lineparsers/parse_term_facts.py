import sys
from lark import Lark, Transformer, Tree

TERM_FACTS_GRAMMAR = """
start: noun_line
	  | verb_line
	  | adverb_line
	  | pronoun_line
	  | adjective_line
	  | conjunction_line
	  | verb_participle_line
	  | pack_line
	  | preposition_line
	  | tack_line
	  | interj_line
	  | num_line
	  | card_line
	  | suffix_line
	  | prefix_line
	  | supine_line

noun_line: term "N" declension variant case number gender [notes]
pronoun_line: term "PRON" declension variant case number gender [notes]
adjective_line: term "ADJ" declension variant case number gender comparison [notes]
verb_line: term "V" conjugation variant tense voice [mood] person number [notes]
verb_participle_line: term "VPAR" conjugation variant case number gender tense [voice] "PPL" [notes]
num_line: term "NUM" declension variant case number gender "ORD" [notes]
card_line: term "NUM" declension variant case number gender "CARD" [notes]
supine_line: term "SUPINE" declension variant case number gender [notes]
adverb_line: term "ADV" comparison [notes]
preposition_line: term "PREP" case [notes]
conjunction_line: term "CONJ" [notes]
tack_line: term "TACKON" [notes]
interj_line: term "INTERJ" [notes]
suffix_line: term "SUFFIX" [notes]
prefix_line: term "PREFIX" [notes]
pack_line: term "PACK" [notes]

tense: word
voice: word
mood: word
person: num
gender: char
case: word
number: char
comparison: word
term: /[A-Za-z\.]+/
num: /[0-9]{1}/
word: /[A-Z]+/
char: /[A-Z]{1}/
declension: num
conjugation: num
variant: num
notes: /[A-Za-z0-9,\/()\[\]~=>.:\-\+'"!_\? ]+/

%import common.WS -> WS
%ignore WS
"""


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
            return dict(
                term=term, term_analysis=dict(stem=parts[0], ending=".".join(parts[1:]))
            )
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
    parser = Lark(TERM_FACTS_GRAMMAR)
    xformer = FactsTransformer()

    @staticmethod
    def reduce(line):
        tree = FactsReducer.parser.parse(line)
        result = FactsReducer.xformer.transform(tree)
        return result
