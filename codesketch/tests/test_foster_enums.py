import unittest

from langnet.foster.enums import FosterCase, FosterGender, FosterMisc, FosterNumber, FosterTense


class TestFosterEnums(unittest.TestCase):
    def test_foster_case_values(self):
        self.assertEqual(FosterCase.NAMING.value, "NAMING")
        self.assertEqual(FosterCase.CALLING.value, "CALLING")
        self.assertEqual(FosterCase.RECEIVING.value, "RECEIVING")
        self.assertEqual(FosterCase.POSSESSING.value, "POSSESSING")
        self.assertEqual(FosterCase.TO_FOR.value, "TO_FOR")
        self.assertEqual(FosterCase.BY_WITH_FROM_IN.value, "BY_WITH_FROM_IN")
        self.assertEqual(FosterCase.IN_WHERE.value, "IN_WHERE")
        self.assertEqual(FosterCase.OH.value, "OH")

    def test_foster_tense_values(self):
        self.assertEqual(FosterTense.TIME_NOW.value, "TIME_NOW")
        self.assertEqual(FosterTense.TIME_LATER.value, "TIME_LATER")
        self.assertEqual(FosterTense.TIME_PAST.value, "TIME_PAST")
        self.assertEqual(FosterTense.TIME_WAS_DOING.value, "TIME_WAS_DOING")
        self.assertEqual(FosterTense.TIME_HAD_DONE.value, "TIME_HAD_DONE")
        self.assertEqual(FosterTense.ONCE_DONE.value, "ONCE_DONE")

    def test_foster_gender_values(self):
        self.assertEqual(FosterGender.MALE.value, "MALE")
        self.assertEqual(FosterGender.FEMALE.value, "FEMALE")
        self.assertEqual(FosterGender.NEUTER.value, "NEUTER")

    def test_foster_number_values(self):
        self.assertEqual(FosterNumber.SINGLE.value, "SINGLE")
        self.assertEqual(FosterNumber.GROUP.value, "GROUP")
        self.assertEqual(FosterNumber.PAIR.value, "PAIR")

    def test_foster_misc_values(self):
        self.assertEqual(FosterMisc.PARTICIPLE.value, "PARTICIPLE")
        self.assertEqual(FosterMisc.DOING.value, "DOING")
        self.assertEqual(FosterMisc.BEING_DONE_TO.value, "BEING_DONE_TO")
        self.assertEqual(FosterMisc.STATEMENT.value, "STATEMENT")
        self.assertEqual(FosterMisc.WISH_MAY_BE.value, "WISH_MAY_BE")
        self.assertEqual(FosterMisc.MAYBE_WILL_DO.value, "MAYBE_WILL_DO")
        self.assertEqual(FosterMisc.COMMAND.value, "COMMAND")
        self.assertEqual(FosterMisc.FOR_SELF.value, "FOR_SELF")


if __name__ == "__main__":
    unittest.main()
