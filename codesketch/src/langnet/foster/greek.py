from langnet.foster.enums import (
    FosterCase,
    FosterGender,
    FosterMisc,
    FosterNumber,
    FosterTense,
)

FOSTER_GREEK_CASES = {
    "nom": FosterCase.NAMING,
    "voc": FosterCase.CALLING,
    "acc": FosterCase.RECEIVING,
    "gen": FosterCase.POSSESSING,
    "dat": FosterCase.TO_FOR,
}

FOSTER_GREEK_TENSES = {
    "pres": FosterTense.TIME_NOW,
    "fut": FosterTense.TIME_LATER,
    "imperf": FosterTense.TIME_WAS_DOING,
    "aor": FosterTense.TIME_PAST,
    "perf": FosterTense.TIME_HAD_DONE,
    "plupf": FosterTense.ONCE_DONE,
}

FOSTER_GREEK_GENDERS = {
    "m": FosterGender.MALE,
    "f": FosterGender.FEMALE,
    "n": FosterGender.NEUTER,
}

FOSTER_GREEK_NUMBERS = {
    "sg": FosterNumber.SINGLE,
    "pl": FosterNumber.GROUP,
    "du": FosterNumber.PAIR,
}

FOSTER_GREEK_MISCELLANEOUS = {
    "part": FosterMisc.PARTICIPLE,
    "act": FosterMisc.DOING,
    "mid": FosterMisc.FOR_SELF,
    "pass": FosterMisc.BEING_DONE_TO,
    "indic": FosterMisc.STATEMENT,
    "subj": FosterMisc.WISH_MAY_BE,
    "opt": FosterMisc.MAYBE_WILL_DO,
    "imper": FosterMisc.COMMAND,
}
