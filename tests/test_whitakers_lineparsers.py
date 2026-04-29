from __future__ import annotations

from langnet.parsing.whitakers import CodesReducer, FactsReducer, SensesReducer


def test_whitaker_senses_reducer_parses_senses_and_notes() -> None:
    result = SensesReducer.reduce("joy, delight, gladness; poetic use [rare];")

    assert result == {
        "senses": ["joy, delight, gladness", "poetic use"],
        "notes": ["rare"],
    }


def test_whitaker_codes_reducer_discards_unknown_codes() -> None:
    result = CodesReducer.reduce("amo, amare, amavi, amatus  V (1st)   [XXXAO]")

    assert result == {
        "term": "amo, amare, amavi, amatus",
        "pos_code": "V",
        "declension": "1st",
        "freq": "A",
        "source": "O",
    }


def test_whitaker_facts_reducer_parses_verb_features() -> None:
    result = FactsReducer.reduce("am.arem              V      1 1 IMPF ACTIVE  SUB 1 S")

    assert result == {
        "part_of_speech": "verb",
        "term": "am.arem",
        "term_analysis": {"stem": "am", "ending": "arem"},
        "conjugation": "1",
        "variant": "1",
        "tense": "IMPF",
        "voice": "ACTIVE",
        "mood": "SUB",
        "person": "1",
        "number": "S",
    }
