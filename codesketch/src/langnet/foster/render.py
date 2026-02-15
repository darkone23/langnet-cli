from langnet.foster.enums import (
    FosterCase,
    FosterGender,
    FosterMisc,
    FosterNumber,
    FosterTense,
)
from langnet.foster.lexicon import (
    FOSTER_ABBREVIATIONS,
    FOSTER_CASE_DISPLAY,
    FOSTER_GENDER_DISPLAY,
    FOSTER_MISC_DISPLAY,
    FOSTER_NUMBER_DISPLAY,
    FOSTER_TENSE_DISPLAY,
)

_FOSTER_DISPLAY_MAP = {
    FosterCase: FOSTER_CASE_DISPLAY,
    FosterTense: FOSTER_TENSE_DISPLAY,
    FosterGender: FOSTER_GENDER_DISPLAY,
    FosterNumber: FOSTER_NUMBER_DISPLAY,
    FosterMisc: FOSTER_MISC_DISPLAY,
}

_FOSTER_CLASSES = [FosterTense, FosterCase, FosterGender, FosterNumber, FosterMisc]


def _render_single_code(code: str, display_style: str) -> str:
    for enum_class in _FOSTER_CLASSES:
        try:
            enum_value = enum_class(code)
            if display_style == "full":
                display_map = _FOSTER_DISPLAY_MAP.get(enum_class)
                if display_map:
                    return display_map.get(enum_value, code)
            else:
                return FOSTER_ABBREVIATIONS.get(enum_value, code)
        except ValueError:
            continue
    return code


def render_foster_term(
    foster_enum: (FosterCase | FosterGender | FosterNumber | FosterTense | FosterMisc | None),
    display_style: str = "full",
) -> str | None:
    if foster_enum is None:
        return None

    if display_style == "full":
        for enum_class, display_map in _FOSTER_DISPLAY_MAP.items():
            if isinstance(foster_enum, enum_class):
                return display_map.get(foster_enum)
    else:
        return FOSTER_ABBREVIATIONS.get(foster_enum)

    return None


def render_foster_codes(
    foster_codes: list[str] | dict[str, str],
    display_style: str = "full",
) -> list[str] | dict[str, str]:
    if isinstance(foster_codes, list):
        return [_render_single_code(code, display_style) for code in foster_codes]
    else:
        return {key: _render_single_code(code, display_style) for key, code in foster_codes.items()}
