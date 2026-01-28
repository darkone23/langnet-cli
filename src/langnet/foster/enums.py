from enum import Enum


class FosterCase(Enum):
    NAMING = "NAMING"
    CALLING = "CALLING"
    RECEIVING = "RECEIVING"
    POSSESSING = "POSSESSING"
    TO_FOR = "TO_FOR"
    BY_WITH_FROM_IN = "BY_WITH_FROM_IN"
    IN_WHERE = "IN_WHERE"
    OH = "OH"


class FosterTense(Enum):
    TIME_NOW = "TIME_NOW"
    TIME_LATER = "TIME_LATER"
    TIME_PAST = "TIME_PAST"
    TIME_WAS_DOING = "TIME_WAS_DOING"
    TIME_HAD_DONE = "TIME_HAD_DONE"
    ONCE_DONE = "ONCE_DONE"


class FosterGender(Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    NEUTER = "NEUTER"


class FosterNumber(Enum):
    SINGLE = "SINGLE"
    GROUP = "GROUP"
    PAIR = "PAIR"


class FosterMisc(Enum):
    PARTICIPLE = "PARTICIPLE"
    DOING = "DOING"
    BEING_DONE_TO = "BEING_DONE_TO"
    STATEMENT = "STATEMENT"
    WISH_MAY_BE = "WISH_MAY_BE"
    MAYBE_WILL_DO = "MAYBE_WILL_DO"
    COMMAND = "COMMAND"
    FOR_SELF = "FOR_SELF"
