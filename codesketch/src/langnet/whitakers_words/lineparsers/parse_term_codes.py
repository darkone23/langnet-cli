from pathlib import Path

from lark import Lark, Transformer
from lark.visitors import Discard


def get_term_codes_grammar():
    grammar_path = Path(__file__).parent / "grammars" / "term_codes.ebnf"
    return grammar_path.read_text()


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
    parser = Lark(get_term_codes_grammar())
    xformer = CodesTransformer()

    @staticmethod
    def reduce(line):
        tree = CodesReducer.parser.parse(line)
        result = CodesReducer.xformer.transform(tree)
        return result
