from langnet.foster.enums import FosterCase, FosterGender, FosterNumber

FOSTER_SANSKRIT_CASES = {
    "1": FosterCase.NAMING,
    "2": FosterCase.CALLING,
    "3": FosterCase.RECEIVING,
    "4": FosterCase.POSSESSING,
    "5": FosterCase.TO_FOR,
    "6": FosterCase.BY_WITH_FROM_IN,
    "7": FosterCase.IN_WHERE,
    "8": FosterCase.OH,
}

FOSTER_SANSKRIT_GENDERS = {
    "m": FosterGender.MALE,
    "f": FosterGender.FEMALE,
    "n": FosterGender.NEUTER,
}

FOSTER_SANSKRIT_NUMBERS = {
    "sg": FosterNumber.SINGLE,
    "pl": FosterNumber.GROUP,
    "du": FosterNumber.PAIR,
}
