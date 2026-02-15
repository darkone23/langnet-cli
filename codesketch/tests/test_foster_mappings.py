import unittest

from langnet.foster.greek import (
    FOSTER_GREEK_CASES,
    FOSTER_GREEK_GENDERS,
    FOSTER_GREEK_MISCELLANEOUS,
    FOSTER_GREEK_NUMBERS,
    FOSTER_GREEK_TENSES,
)
from langnet.foster.latin import (
    FOSTER_LATIN_CASES,
    FOSTER_LATIN_GENDERS,
    FOSTER_LATIN_MISCELLANEOUS,
    FOSTER_LATIN_NUMBERS,
    FOSTER_LATIN_TENSES,
)
from langnet.foster.sanskrit import (
    FOSTER_SANSKRIT_CASES,
    FOSTER_SANSKRIT_GENDERS,
    FOSTER_SANSKRIT_NUMBERS,
)


class TestFosterMappings(unittest.TestCase):
    def test_latin_cases(self):
        self.assertEqual(FOSTER_LATIN_CASES["nom"].value, "NAMING")
        self.assertEqual(FOSTER_LATIN_CASES["voc"].value, "CALLING")
        self.assertEqual(FOSTER_LATIN_CASES["acc"].value, "RECEIVING")
        self.assertEqual(FOSTER_LATIN_CASES["gen"].value, "POSSESSING")
        self.assertEqual(FOSTER_LATIN_CASES["dat"].value, "TO_FOR")
        self.assertEqual(FOSTER_LATIN_CASES["abl"].value, "BY_WITH_FROM_IN")
        self.assertEqual(FOSTER_LATIN_CASES["loc"].value, "IN_WHERE")

    def test_latin_tenses(self):
        self.assertEqual(FOSTER_LATIN_TENSES["pres"].value, "TIME_NOW")
        self.assertEqual(FOSTER_LATIN_TENSES["fut"].value, "TIME_LATER")
        self.assertEqual(FOSTER_LATIN_TENSES["imperf"].value, "TIME_WAS_DOING")
        self.assertEqual(FOSTER_LATIN_TENSES["perf"].value, "TIME_PAST")
        self.assertEqual(FOSTER_LATIN_TENSES["plupf"].value, "TIME_HAD_DONE")
        self.assertEqual(FOSTER_LATIN_TENSES["futperf"].value, "ONCE_DONE")

    def test_latin_genders(self):
        self.assertEqual(FOSTER_LATIN_GENDERS["m"].value, "MALE")
        self.assertEqual(FOSTER_LATIN_GENDERS["f"].value, "FEMALE")
        self.assertEqual(FOSTER_LATIN_GENDERS["n"].value, "NEUTER")

    def test_latin_numbers(self):
        self.assertEqual(FOSTER_LATIN_NUMBERS["sg"].value, "SINGLE")
        self.assertEqual(FOSTER_LATIN_NUMBERS["pl"].value, "GROUP")
        self.assertEqual(FOSTER_LATIN_NUMBERS["du"].value, "PAIR")

    def test_latin_miscellaneous(self):
        self.assertEqual(FOSTER_LATIN_MISCELLANEOUS["part"].value, "PARTICIPLE")
        self.assertEqual(FOSTER_LATIN_MISCELLANEOUS["act"].value, "DOING")
        self.assertEqual(FOSTER_LATIN_MISCELLANEOUS["pass"].value, "BEING_DONE_TO")
        self.assertEqual(FOSTER_LATIN_MISCELLANEOUS["indic"].value, "STATEMENT")
        self.assertEqual(FOSTER_LATIN_MISCELLANEOUS["subj"].value, "WISH_MAY_BE")
        self.assertEqual(FOSTER_LATIN_MISCELLANEOUS["imper"].value, "COMMAND")

    def test_greek_cases(self):
        self.assertEqual(FOSTER_GREEK_CASES["nom"].value, "NAMING")
        self.assertEqual(FOSTER_GREEK_CASES["voc"].value, "CALLING")
        self.assertEqual(FOSTER_GREEK_CASES["acc"].value, "RECEIVING")
        self.assertEqual(FOSTER_GREEK_CASES["gen"].value, "POSSESSING")
        self.assertEqual(FOSTER_GREEK_CASES["dat"].value, "TO_FOR")

    def test_greek_tenses(self):
        self.assertEqual(FOSTER_GREEK_TENSES["pres"].value, "TIME_NOW")
        self.assertEqual(FOSTER_GREEK_TENSES["fut"].value, "TIME_LATER")
        self.assertEqual(FOSTER_GREEK_TENSES["imperf"].value, "TIME_WAS_DOING")
        self.assertEqual(FOSTER_GREEK_TENSES["aor"].value, "TIME_PAST")
        self.assertEqual(FOSTER_GREEK_TENSES["perf"].value, "TIME_HAD_DONE")
        self.assertEqual(FOSTER_GREEK_TENSES["plupf"].value, "ONCE_DONE")

    def test_greek_genders(self):
        self.assertEqual(FOSTER_GREEK_GENDERS["m"].value, "MALE")
        self.assertEqual(FOSTER_GREEK_GENDERS["f"].value, "FEMALE")
        self.assertEqual(FOSTER_GREEK_GENDERS["n"].value, "NEUTER")

    def test_greek_numbers(self):
        self.assertEqual(FOSTER_GREEK_NUMBERS["sg"].value, "SINGLE")
        self.assertEqual(FOSTER_GREEK_NUMBERS["pl"].value, "GROUP")
        self.assertEqual(FOSTER_GREEK_NUMBERS["du"].value, "PAIR")

    def test_greek_miscellaneous(self):
        self.assertEqual(FOSTER_GREEK_MISCELLANEOUS["part"].value, "PARTICIPLE")
        self.assertEqual(FOSTER_GREEK_MISCELLANEOUS["act"].value, "DOING")
        self.assertEqual(FOSTER_GREEK_MISCELLANEOUS["mid"].value, "FOR_SELF")
        self.assertEqual(FOSTER_GREEK_MISCELLANEOUS["pass"].value, "BEING_DONE_TO")
        self.assertEqual(FOSTER_GREEK_MISCELLANEOUS["indic"].value, "STATEMENT")
        self.assertEqual(FOSTER_GREEK_MISCELLANEOUS["subj"].value, "WISH_MAY_BE")
        self.assertEqual(FOSTER_GREEK_MISCELLANEOUS["opt"].value, "MAYBE_WILL_DO")
        self.assertEqual(FOSTER_GREEK_MISCELLANEOUS["imper"].value, "COMMAND")

    def test_sanskrit_cases(self):
        self.assertEqual(FOSTER_SANSKRIT_CASES["1"].value, "NAMING")
        self.assertEqual(FOSTER_SANSKRIT_CASES["2"].value, "CALLING")
        self.assertEqual(FOSTER_SANSKRIT_CASES["3"].value, "RECEIVING")
        self.assertEqual(FOSTER_SANSKRIT_CASES["4"].value, "POSSESSING")
        self.assertEqual(FOSTER_SANSKRIT_CASES["5"].value, "TO_FOR")
        self.assertEqual(FOSTER_SANSKRIT_CASES["6"].value, "BY_WITH_FROM_IN")
        self.assertEqual(FOSTER_SANSKRIT_CASES["7"].value, "IN_WHERE")
        self.assertEqual(FOSTER_SANSKRIT_CASES["8"].value, "OH")

    def test_sanskrit_genders(self):
        self.assertEqual(FOSTER_SANSKRIT_GENDERS["m"].value, "MALE")
        self.assertEqual(FOSTER_SANSKRIT_GENDERS["f"].value, "FEMALE")
        self.assertEqual(FOSTER_SANSKRIT_GENDERS["n"].value, "NEUTER")

    def test_sanskrit_numbers(self):
        self.assertEqual(FOSTER_SANSKRIT_NUMBERS["sg"].value, "SINGLE")
        self.assertEqual(FOSTER_SANSKRIT_NUMBERS["pl"].value, "GROUP")
        self.assertEqual(FOSTER_SANSKRIT_NUMBERS["du"].value, "PAIR")


if __name__ == "__main__":
    unittest.main()
