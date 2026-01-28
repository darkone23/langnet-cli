from langnet.foster.enums import (
    FosterCase,
    FosterGender,
    FosterMisc,
    FosterNumber,
    FosterTense,
)

FOSTER_CASE_DISPLAY = {
    FosterCase.NAMING: "Naming Function",
    FosterCase.CALLING: "Calling Function",
    FosterCase.RECEIVING: "Receiving Function",
    FosterCase.POSSESSING: "Possessing Function",
    FosterCase.TO_FOR: "To-For Function",
    FosterCase.BY_WITH_FROM_IN: "By-With-From-In Function",
    FosterCase.IN_WHERE: "In-Where Function",
    FosterCase.OH: "Oh Function",
}

FOSTER_TENSE_DISPLAY = {
    FosterTense.TIME_NOW: "Time-Now Function",
    FosterTense.TIME_LATER: "Time-Later Function",
    FosterTense.TIME_PAST: "Time-Past Function",
    FosterTense.TIME_WAS_DOING: "Time-Was-Doing Function",
    FosterTense.TIME_HAD_DONE: "Time-Had-Done Function",
    FosterTense.ONCE_DONE: "Once-Done Function",
}

FOSTER_GENDER_DISPLAY = {
    FosterGender.MALE: "Male Function",
    FosterGender.FEMALE: "Female Function",
    FosterGender.NEUTER: "Neuter Function",
}

FOSTER_NUMBER_DISPLAY = {
    FosterNumber.SINGLE: "Single Function",
    FosterNumber.GROUP: "Group Function",
    FosterNumber.PAIR: "Pair Function",
}

FOSTER_MISC_DISPLAY = {
    FosterMisc.PARTICIPLE: "Participial Function",
    FosterMisc.DOING: "Doing Function",
    FosterMisc.BEING_DONE_TO: "Being-Done-To Function",
    FosterMisc.STATEMENT: "Statement Function",
    FosterMisc.WISH_MAY_BE: "Wish-May-Be Function",
    FosterMisc.MAYBE_WILL_DO: "Maybe-Will-Do Function",
    FosterMisc.COMMAND: "Command Function",
    FosterMisc.FOR_SELF: "For-Self Function",
}

FOSTER_ABBREVIATIONS = {
    FosterCase.NAMING: "NAM",
    FosterCase.CALLING: "CAL",
    FosterCase.RECEIVING: "REC",
    FosterCase.POSSESSING: "POS",
    FosterCase.TO_FOR: "TOF",
    FosterCase.BY_WITH_FROM_IN: "BYW",
    FosterCase.IN_WHERE: "INW",
    FosterCase.OH: "OH",
    FosterTense.TIME_NOW: "NOW",
    FosterTense.TIME_LATER: "FUT",
    FosterTense.TIME_PAST: "PST",
    FosterTense.TIME_WAS_DOING: "IMP",
    FosterTense.TIME_HAD_DONE: "PLU",
    FosterTense.ONCE_DONE: "PER",
    FosterGender.MALE: "MASC",
    FosterGender.FEMALE: "FEM",
    FosterGender.NEUTER: "NEUT",
    FosterNumber.SINGLE: "SG",
    FosterNumber.GROUP: "PL",
    FosterNumber.PAIR: "DU",
    FosterMisc.PARTICIPLE: "PTCP",
    FosterMisc.DOING: "ACT",
    FosterMisc.BEING_DONE_TO: "PASS",
    FosterMisc.STATEMENT: "IND",
    FosterMisc.WISH_MAY_BE: "OPT",
    FosterMisc.MAYBE_WILL_DO: "SUBJ",
    FosterMisc.COMMAND: "IMP",
    FosterMisc.FOR_SELF: "MID",
}
