from langnet.pedagogy.foster import (
    FOSTER_GREEK_MAPPINGS,
    FOSTER_LATIN_MAPPINGS,
    FOSTER_SANSKRIT_MAPPINGS,
    foster_codes_for_features,
    foster_display_for_features,
)


def test_foster_latin_core_labels() -> None:
    assert FOSTER_LATIN_MAPPINGS.cases["nom"] == "NAMING"
    assert FOSTER_LATIN_MAPPINGS.cases["voc"] == "CALLING"
    assert FOSTER_LATIN_MAPPINGS.cases["acc"] == "RECEIVING"
    assert FOSTER_LATIN_MAPPINGS.cases["gen"] == "POSSESSING"
    assert FOSTER_LATIN_MAPPINGS.cases["dat"] == "TO_FOR"
    assert FOSTER_LATIN_MAPPINGS.cases["abl"] == "BY_WITH_FROM_IN"
    assert FOSTER_LATIN_MAPPINGS.cases["loc"] == "IN_WHERE"
    assert FOSTER_LATIN_MAPPINGS.tenses["perf"] == "TIME_PAST"
    assert FOSTER_LATIN_MAPPINGS.voices["pass"] == "BEING_DONE_TO"


def test_foster_greek_core_labels() -> None:
    assert FOSTER_GREEK_MAPPINGS.cases["nom"] == "NAMING"
    assert FOSTER_GREEK_MAPPINGS.cases["acc"] == "RECEIVING"
    assert FOSTER_GREEK_MAPPINGS.tenses["aor"] == "TIME_PAST"
    assert FOSTER_GREEK_MAPPINGS.voices["mid"] == "FOR_SELF"
    assert FOSTER_GREEK_MAPPINGS.moods["opt"] == "MAYBE_WILL_DO"


def test_foster_sanskrit_cases_use_standard_numbering() -> None:
    assert FOSTER_SANSKRIT_MAPPINGS.cases["1"] == "NAMING"
    assert FOSTER_SANSKRIT_MAPPINGS.cases["2"] == "RECEIVING"
    assert FOSTER_SANSKRIT_MAPPINGS.cases["3"] == "BY_WITH_FROM_IN"
    assert FOSTER_SANSKRIT_MAPPINGS.cases["4"] == "TO_FOR"
    assert FOSTER_SANSKRIT_MAPPINGS.cases["5"] == "BY_WITH_FROM_IN"
    assert FOSTER_SANSKRIT_MAPPINGS.cases["6"] == "POSSESSING"
    assert FOSTER_SANSKRIT_MAPPINGS.cases["7"] == "IN_WHERE"
    assert FOSTER_SANSKRIT_MAPPINGS.cases["8"] == "CALLING"


def test_foster_codes_for_current_feature_dicts() -> None:
    assert foster_codes_for_features(
        "san",
        {"case": "accusative", "number": "dual", "gender": "neuter"},
    ) == {"case": "RECEIVING", "gender": "NEUTER", "number": "PAIR"}

    assert foster_codes_for_features(
        "lat",
        {"case": "abl", "number": "pl", "gender": "m", "tense": "pres", "voice": "act"},
    ) == {
        "case": "BY_WITH_FROM_IN",
        "gender": "MALE",
        "number": "GROUP",
        "tense": "TIME_NOW",
        "voice": "DOING",
    }


def test_foster_display_for_feature_dicts_uses_learner_labels() -> None:
    assert (
        foster_display_for_features(
            "san",
            {"case": "genitive", "number": "plural", "gender": "masculine"},
        )
        == "Possessing Function; Group; Male"
    )

    assert (
        foster_display_for_features(
            "lat",
            {
                "person": "1",
                "number": "plural",
                "tense": "present",
                "voice": "active",
                "mood": "indicative",
            },
        )
        == "Group; Time-Now; Statement; Doing"
    )
