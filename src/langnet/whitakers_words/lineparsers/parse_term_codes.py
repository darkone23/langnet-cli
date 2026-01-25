import sys
from lark import Lark, Transformer
from lark.visitors import Discard

TERM_CODES_GRAMMAR = """
start: simple_code_line | full_code_line | basic_code_line 

simple_code_line: term_info pos_code code_chunk [notes]
full_code_line: term_info pos_code [declension] [pos_form] code_chunk [notes]
basic_code_line: code_chunk [notes]

pos_form: /[A-Z]{1,7}/
pos_code: /[A-Z]{1,7}/
term_txt: /[A-Za-z.]{1}[a-z., ()-\/]+/
term_info: proper_names | term_txt
proper_names: name ("," name)*
name: /[A-Z][a-z]+/
declension: "(" /[0-9]{1}[sthnrd]{2}/ ")"
age: char
area: char
geo: char
freq: char
source: char
code: age area geo freq source
code_chunk: "[" code  "]"
char: /[A-Z]{1}/
notes: /[A-Za-z0-9,\/()\[\]~=>.:\-\+'"!_\? ]+/

%import common.WS -> WS
%ignore WS
"""


class CodesTransformer(Transformer):
    def start(self, args):
        # print("start", args)
        return args[0]

    def code_chunk(self, leaves):
        entries = {}
        for tree in leaves:
            for leaf in tree.children:
                entries.update(leaf)
        if len(entries.items()) == 0:
            return Discard
        else:
            return entries

    def notes(self, args):
        for x in args:
            # print("notes", x)
            return dict(notes=f"{x}".strip().split())
        return args

    def proper_names(self, args):
        names = []
        for item in args:
            for thing in item.children:
                names.append(f"{thing}")
        return dict(names=names)

    def pos_code(self, args):
        for x in args:
            return dict(pos_code=f"{x}")

    def declension(self, args):
        for x in args:
            return dict(declension=f"{x}")

    def pos_form(self, args):
        for x in args:
            return dict(pos_form=f"{x}")

    def term_info(self, args):
        # print("info", type(args), args)
        return args

    def term_txt(self, args):
        for x in args:
            # print("txt", type(x), x)
            return dict(term=f"{x}".strip())
        return args

    def handle_code(self, leaves):
        for tree in leaves:
            for leaf in tree.children:
                if leaf == "X":
                    return Discard
                return f"{leaf}"

    def age(self, args):
        code = self.handle_code(args)
        if code is not Discard:
            return dict(age=code)
        else:
            return Discard

    def area(self, args):
        code = self.handle_code(args)
        if code is not Discard:
            return dict(area=code)
        else:
            return Discard

    def geo(self, args):
        code = self.handle_code(args)
        if code is not Discard:
            return dict(geo=code)
        else:
            return Discard

    def freq(self, args):
        code = self.handle_code(args)
        # print("freq", code)
        if code is not Discard:
            return dict(freq=code)
        else:
            return Discard

    def source(self, args):
        code = self.handle_code(args)
        # print("source", code)
        if code is not Discard:
            return dict(source=code)
        else:
            return Discard

    def flatten(self, args):
        xs = dict()
        for item in args:
            if type(item) is list:
                for x in item:
                    # print("flatten", x)
                    xs.update(x)
            elif item is None:
                pass
            elif type(item) is dict:
                # print("flatten", item)
                xs.update(item)
        return xs

    def simple_code_line(self, args):
        return self.flatten(args)

    def full_code_line(self, args):
        # print("full", args)
        return self.flatten(args)

    def basic_code_line(self, args):
        # print("basic", args)
        return self.flatten(args)


class CodesReducer:
    parser = Lark(TERM_CODES_GRAMMAR)
    xformer = CodesTransformer()

    @staticmethod
    def reduce(line):
        tree = CodesReducer.parser.parse(line)
        result = CodesReducer.xformer.transform(tree)
        return result
