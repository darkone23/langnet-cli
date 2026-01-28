import unittest

from langnet.foster.enums import FosterCase, FosterGender, FosterMisc, FosterNumber, FosterTense
from langnet.foster.render import render_foster_codes, render_foster_term


class TestFosterRendering(unittest.TestCase):
    def test_render_foster_term_full_case(self):
        result = render_foster_term(FosterCase.NAMING, "full")
        self.assertEqual(result, "Naming Function")

    def test_render_foster_term_full_tense(self):
        result = render_foster_term(FosterTense.TIME_NOW, "full")
        self.assertEqual(result, "Time-Now Function")

    def test_render_foster_term_full_gender(self):
        result = render_foster_term(FosterGender.MALE, "full")
        self.assertEqual(result, "Male Function")

    def test_render_foster_term_full_number(self):
        result = render_foster_term(FosterNumber.SINGLE, "full")
        self.assertEqual(result, "Single Function")

    def test_render_foster_term_full_misc(self):
        result = render_foster_term(FosterMisc.DOING, "full")
        self.assertEqual(result, "Doing Function")

    def test_render_foster_term_short(self):
        result = render_foster_term(FosterCase.NAMING, "short")
        self.assertEqual(result, "NAM")

    def test_render_foster_term_none(self):
        result = render_foster_term(None, "full")
        self.assertIsNone(result)

    def test_render_foster_codes_list(self):
        codes = ["NAMING", "MALE", "SINGLE"]
        result = render_foster_codes(codes, "full")
        self.assertEqual(result, ["Naming Function", "Male Function", "Single Function"])

    def test_render_foster_codes_dict(self):
        codes = {"case": "NAMING", "gender": "MALE", "number": "SINGLE"}
        result = render_foster_codes(codes, "full")
        self.assertEqual(
            result,
            {"case": "Naming Function", "gender": "Male Function", "number": "Single Function"},
        )

    def test_render_foster_codes_unmapped(self):
        codes = ["UNKNOWN"]
        result = render_foster_codes(codes, "full")
        self.assertEqual(result, ["UNKNOWN"])


if __name__ == "__main__":
    unittest.main()
