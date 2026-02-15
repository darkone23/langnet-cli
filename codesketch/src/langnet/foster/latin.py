from langnet.foster.enums import (
    FosterCase,
    FosterGender,
    FosterMisc,
    FosterNumber,
    FosterTense,
)

FOSTER_LATIN_CASES = {
    "nom": FosterCase.NAMING,
    "voc": FosterCase.CALLING,
    "acc": FosterCase.RECEIVING,
    "gen": FosterCase.POSSESSING,
    "dat": FosterCase.TO_FOR,
    "abl": FosterCase.BY_WITH_FROM_IN,
    "loc": FosterCase.IN_WHERE,
}

FOSTER_LATIN_TENSES = {
    "pres": FosterTense.TIME_NOW,
    "fut": FosterTense.TIME_LATER,
    "imperf": FosterTense.TIME_WAS_DOING,
    "perf": FosterTense.TIME_PAST,
    "plupf": FosterTense.TIME_HAD_DONE,
    "futperf": FosterTense.ONCE_DONE,
}

FOSTER_LATIN_GENDERS = {
    "m": FosterGender.MALE,
    "f": FosterGender.FEMALE,
    "n": FosterGender.NEUTER,
}

FOSTER_LATIN_NUMBERS = {
    "sg": FosterNumber.SINGLE,
    "pl": FosterNumber.GROUP,
    "du": FosterNumber.PAIR,
}

FOSTER_LATIN_MISCELLANEOUS = {
    "part": FosterMisc.PARTICIPLE,
    "act": FosterMisc.DOING,
    "pass": FosterMisc.BEING_DONE_TO,
    "indic": FosterMisc.STATEMENT,
    "subj": FosterMisc.WISH_MAY_BE,
    "imper": FosterMisc.COMMAND,
    "depon": FosterMisc.FOR_SELF,
    "semi_depon": FosterMisc.FOR_SELF,
}
