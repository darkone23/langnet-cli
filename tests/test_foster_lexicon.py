import unittest

from langnet.foster.enums import FosterCase, FosterGender, FosterMisc, FosterNumber, FosterTense
from langnet.foster.lexicon import (
    FOSTER_ABBREVIATIONS,
    FOSTER_CASE_DISPLAY,
    FOSTER_GENDER_DISPLAY,
    FOSTER_MISC_DISPLAY,
    FOSTER_NUMBER_DISPLAY,
    FOSTER_TENSE_DISPLAY,
)


class TestFosterLexicon(unittest.TestCase):
    def test_case_display_complete(self):
        for case in FosterCase:
            self.assertIn(case, FOSTER_CASE_DISPLAY, f"Missing display for {case}")
            self.assertIsInstance(FOSTER_CASE_DISPLAY[case], str)

    def test_tense_display_complete(self):
        for tense in FosterTense:
            self.assertIn(tense, FOSTER_TENSE_DISPLAY, f"Missing display for {tense}")
            self.assertIsInstance(FOSTER_TENSE_DISPLAY[tense], str)

    def test_gender_display_complete(self):
        for gender in FosterGender:
            self.assertIn(gender, FOSTER_GENDER_DISPLAY, f"Missing display for {gender}")
            self.assertIsInstance(FOSTER_GENDER_DISPLAY[gender], str)

    def test_number_display_complete(self):
        for number in FosterNumber:
            self.assertIn(number, FOSTER_NUMBER_DISPLAY, f"Missing display for {number}")
            self.assertIsInstance(FOSTER_NUMBER_DISPLAY[number], str)

    def test_misc_display_complete(self):
        for misc in FosterMisc:
            self.assertIn(misc, FOSTER_MISC_DISPLAY, f"Missing display for {misc}")
            self.assertIsInstance(FOSTER_MISC_DISPLAY[misc], str)

    def test_abbreviations_complete(self):
        all_enums = (
            list(FosterCase)
            + list(FosterTense)
            + list(FosterGender)
            + list(FosterNumber)
            + list(FosterMisc)
        )
        for enum in all_enums:
            self.assertIn(enum, FOSTER_ABBREVIATIONS, f"Missing abbreviation for {enum}")
            self.assertIsInstance(FOSTER_ABBREVIATIONS[enum], str)


if __name__ == "__main__":
    unittest.main()
