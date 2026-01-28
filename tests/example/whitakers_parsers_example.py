import sys
from pathlib import Path

from langnet.whitakers_words.lineparsers.parse_senses import SensesReducer
from langnet.whitakers_words.lineparsers.parse_term_codes import CodesReducer
from langnet.whitakers_words.lineparsers.parse_term_facts import FactsReducer

test_data = Path() / "tests/data/whitakers-lines"


def facts_reducer():
    input_data = (test_data / "term-facts.txt").read_text()

    if not input_data:
        print("⚠️ No input data received! Please check your input file.")
        sys.exit(1)

    from rich.pretty import pprint

    for line in input_data.splitlines():
        # print("Looking at line:")
        print(line)
        result = FactsReducer.reduce(line)
        pprint(result)


def codes_reducer():
    input_data = (test_data / "term-codes.txt").read_text()

    if not input_data:
        print("⚠️ No input data received! Please check your input file.")
        sys.exit(1)

    from rich.pretty import pprint

    for line in input_data.splitlines():
        print(line)
        result = CodesReducer.reduce(line)
        pprint(result)
        # print(result.pretty())


def senses_reducer():
    input_data = (test_data / "senses.txt").read_text()

    if not input_data:
        print("⚠️ No input data received! Please check your input file.")
        sys.exit(1)

    from rich.pretty import pprint

    for line in input_data.splitlines():
        # print("Looking at line:")
        print(line)
        result = SensesReducer.reduce(line)
        pprint(result)
        # print(result.pretty())


if __name__ == "__main__":
    facts_reducer()
    codes_reducer()
    senses_reducer()
