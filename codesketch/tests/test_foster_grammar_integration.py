#!/usr/bin/env python3
"""
Comprehensive test suite for Foster functional grammar integration
"""

import os
import sys
import unittest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from langnet.foster.apply import apply_foster_view
from langnet.foster.enums import FosterCase, FosterGender, FosterMisc, FosterNumber, FosterTense


class TestLatinFosterMapping(unittest.TestCase):
    """Test suite for Latin Foster functional grammar mapping"""

    def test_latin_case_mapping(self):
        """Test Latin case mappings"""
        test_cases = [
            ("nom", FosterCase.NAMING),
            ("voc", FosterCase.CALLING),
            ("acc", FosterCase.RECEIVING),
            ("gen", FosterCase.POSSESSING),
            ("dat", FosterCase.TO_FOR),
            ("abl", FosterCase.BY_WITH_FROM_IN),
            ("loc", FosterCase.IN_WHERE),
        ]

        for tag, expected_foster in test_cases:
            with self.subTest(tag=tag):
                result = apply_foster_view(
                    {
                        "diogenes": {
                            "chunks": [
                                {"morphology": {"morphs": [{"stem": ["test"], "tags": [tag]}]}}
                            ]
                        }
                    }
                )

                foster_codes = result["diogenes"]["chunks"][0]["morphology"]["morphs"][0][
                    "foster_codes"
                ]
                self.assertIn(expected_foster.value, foster_codes)

    def test_latin_tense_mapping(self):
        """Test Latin tense mappings"""
        test_cases = [
            ("pres", FosterTense.TIME_NOW),
            ("fut", FosterTense.TIME_LATER),
            ("imperf", FosterTense.TIME_WAS_DOING),
            ("perf", FosterTense.TIME_PAST),
            ("plupf", FosterTense.TIME_HAD_DONE),
            ("futperf", FosterTense.ONCE_DONE),
        ]

        for tag, expected_foster in test_cases:
            with self.subTest(tag=tag):
                result = apply_foster_view(
                    {
                        "diogenes": {
                            "chunks": [
                                {"morphology": {"morphs": [{"stem": ["test"], "tags": [tag]}]}}
                            ]
                        }
                    }
                )

                foster_codes = result["diogenes"]["chunks"][0]["morphology"]["morphs"][0][
                    "foster_codes"
                ]
                self.assertIn(expected_foster.value, foster_codes)

    def test_latin_gender_mapping(self):
        """Test Latin gender mappings"""
        test_cases = [
            ("m", FosterGender.MALE),
            ("f", FosterGender.FEMALE),
            ("n", FosterGender.NEUTER),
        ]

        for tag, expected_foster in test_cases:
            with self.subTest(tag=tag):
                result = apply_foster_view(
                    {
                        "diogenes": {
                            "chunks": [
                                {"morphology": {"morphs": [{"stem": ["test"], "tags": [tag]}]}}
                            ]
                        }
                    }
                )

                foster_codes = result["diogenes"]["chunks"][0]["morphology"]["morphs"][0][
                    "foster_codes"
                ]
                self.assertIn(expected_foster.value, foster_codes)

    def test_latin_number_mapping(self):
        """Test Latin number mappings"""
        test_cases = [
            ("sg", FosterNumber.SINGLE),
            ("pl", FosterNumber.GROUP),
            ("du", FosterNumber.PAIR),
        ]

        for tag, expected_foster in test_cases:
            with self.subTest(tag=tag):
                result = apply_foster_view(
                    {
                        "diogenes": {
                            "chunks": [
                                {"morphology": {"morphs": [{"stem": ["test"], "tags": [tag]}]}}
                            ]
                        }
                    }
                )

                foster_codes = result["diogenes"]["chunks"][0]["morphology"]["morphs"][0][
                    "foster_codes"
                ]
                self.assertIn(expected_foster.value, foster_codes)

    def test_latin_misc_mapping(self):
        """Test Latin miscellaneous mappings"""
        test_cases = [
            ("part", FosterMisc.PARTICIPLE),
            ("act", FosterMisc.DOING),
            ("pass", FosterMisc.BEING_DONE_TO),
            ("indic", FosterMisc.STATEMENT),
            ("subj", FosterMisc.WISH_MAY_BE),
            ("imper", FosterMisc.COMMAND),
            ("depon", FosterMisc.FOR_SELF),
            ("semi_depon", FosterMisc.FOR_SELF),
        ]

        for tag, expected_foster in test_cases:
            with self.subTest(tag=tag):
                result = apply_foster_view(
                    {
                        "diogenes": {
                            "chunks": [
                                {"morphology": {"morphs": [{"stem": ["test"], "tags": [tag]}]}}
                            ]
                        }
                    }
                )

                foster_codes = result["diogenes"]["chunks"][0]["morphology"]["morphs"][0][
                    "foster_codes"
                ]
                self.assertIn(expected_foster.value, foster_codes)

    def test_latin_combined_mapping(self):
        """Test combined Latin mappings"""
        result = apply_foster_view(
            {
                "diogenes": {
                    "chunks": [
                        {
                            "morphology": {
                                "morphs": [
                                    {
                                        "stem": ["puer"],
                                        "tags": ["nom", "sg", "m", "pres", "indic"],
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        )

        foster_codes = result["diogenes"]["chunks"][0]["morphology"]["morphs"][0]["foster_codes"]
        expected_codes = [
            FosterCase.NAMING.value,
            FosterNumber.SINGLE.value,
            FosterGender.MALE.value,
            FosterTense.TIME_NOW.value,
            FosterMisc.STATEMENT.value,
        ]

        for expected_code in expected_codes:
            self.assertIn(expected_code, foster_codes)

    def test_latin_unknown_tag_ignored(self):
        """Test that unknown Latin tags are ignored"""
        result = apply_foster_view(
            {
                "diogenes": {
                    "chunks": [
                        {
                            "morphology": {
                                "morphs": [
                                    {
                                        "stem": ["test"],
                                        "tags": ["unknown_tag"],
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        )

        morph = result["diogenes"]["chunks"][0]["morphology"]["morphs"][0]
        self.assertNotIn("foster_codes", morph)


class TestGreekFosterMapping(unittest.TestCase):
    """Test suite for Greek Foster functional grammar mapping"""

    def test_greek_case_mapping(self):
        """Test Greek case mappings"""
        # Greek cases should be similar to Latin
        test_cases = [
            ("nom", FosterCase.NAMING),
            ("voc", FosterCase.CALLING),
            ("acc", FosterCase.RECEIVING),
            ("gen", FosterCase.POSSESSING),
            ("dat", FosterCase.TO_FOR),
            ("abl", FosterCase.BY_WITH_FROM_IN),
            ("loc", FosterCase.IN_WHERE),
        ]

        for tag, expected_foster in test_cases:
            with self.subTest(tag=tag):
                result = apply_foster_view(
                    {
                        "diogenes": {
                            "chunks": [
                                {"morphology": {"morphs": [{"stem": ["test"], "tags": [tag]}]}}
                            ]
                        }
                    }
                )

                foster_codes = result["diogenes"]["chunks"][0]["morphology"]["morphs"][0][
                    "foster_codes"
                ]
                self.assertIn(expected_foster.value, foster_codes)

    def test_greek_tense_mapping(self):
        """Test Greek tense mappings"""
        test_cases = [
            ("pres", FosterTense.TIME_NOW),
            ("fut", FosterTense.TIME_LATER),
            ("imperf", FosterTense.TIME_WAS_DOING),
            ("perf", FosterTense.TIME_PAST),
            ("plupf", FosterTense.TIME_HAD_DONE),
            ("futperf", FosterTense.ONCE_DONE),
        ]

        for tag, expected_foster in test_cases:
            with self.subTest(tag=tag):
                result = apply_foster_view(
                    {
                        "diogenes": {
                            "chunks": [
                                {"morphology": {"morphs": [{"stem": ["test"], "tags": [tag]}]}}
                            ]
                        }
                    }
                )

                foster_codes = result["diogenes"]["chunks"][0]["morphology"]["morphs"][0][
                    "foster_codes"
                ]
                self.assertIn(expected_foster.value, foster_codes)

    def test_greek_voice_mapping(self):
        """Test Greek voice mapping through miscellaneous"""
        result = apply_foster_view(
            {
                "cltk": {
                    "greek_morphology": {
                        "morphological_features": {
                            "voice": "active",
                            "mood": "indicative",
                        }
                    }
                }
            }
        )

        foster_codes = result["cltk"]["greek_morphology"]["foster_codes"]
        self.assertEqual(foster_codes["voice"], "DOING")
        self.assertEqual(foster_codes["mood"], "STATEMENT")

    def test_greek_combined_mapping(self):
        """Test combined Greek mappings"""
        result = apply_foster_view(
            {
                "cltk": {
                    "greek_morphology": {
                        "morphological_features": {
                            "case": "nom",
                            "tense": "pres",
                            "gender": "m",
                            "number": "sg",
                            "voice": "middle",
                            "mood": "subjunctive",
                        }
                    }
                }
            }
        )

        foster_codes = result["cltk"]["greek_morphology"]["foster_codes"]
        self.assertEqual(foster_codes["case"], "NAMING")
        self.assertEqual(foster_codes["tense"], "TIME_NOW")
        self.assertEqual(foster_codes["gender"], "MALE")
        self.assertEqual(foster_codes["number"], "SINGLE")
        self.assertEqual(foster_codes["voice"], "FOR_SELF")
        self.assertEqual(foster_codes["mood"], "WISH_MAY_BE")

    def test_greek_unknown_feature_ignored(self):
        """Test that unknown Greek features are ignored"""
        result = apply_foster_view(
            {
                "cltk": {
                    "greek_morphology": {
                        "morphological_features": {
                            "unknown_feature": "value",
                        }
                    }
                }
            }
        )

        foster_codes = result["cltk"]["greek_morphology"]["foster_codes"]
        # Should be empty since no known features were found
        self.assertEqual(len(foster_codes), 0)


class TestSanskritFosterMapping(unittest.TestCase):
    """Test suite for Sanskrit Foster functional grammar mapping"""

    def test_sanskrit_case_mapping(self):
        """Test Sanskrit case mappings"""
        test_cases = [
            ("1", FosterCase.NAMING),  # Nominative
            ("2", FosterCase.CALLING),  # Vocative
            ("3", FosterCase.RECEIVING),  # Accusative
            ("4", FosterCase.POSSESSING),  # Genitive
            ("5", FosterCase.TO_FOR),  # Dative
            ("6", FosterCase.BY_WITH_FROM_IN),  # Ablative
            ("7", FosterCase.IN_WHERE),  # Locative
            ("8", FosterCase.OH),  # Instrumental
        ]

        for tag, expected_foster in test_cases:
            with self.subTest(tag=tag):
                result = apply_foster_view(
                    {
                        "dictionaries": {
                            "mw": [
                                {
                                    "id": "1",
                                    "meaning": "test",
                                    "grammar_tags": {"case": tag},
                                }
                            ]
                        }
                    }
                )

                foster_codes = result["dictionaries"]["mw"][0]["foster_codes"]
                self.assertEqual(foster_codes["case"], expected_foster.value)

    def test_sanskrit_gender_mapping(self):
        """Test Sanskrit gender mappings"""
        test_cases = [
            ("m", FosterGender.MALE),
            ("f", FosterGender.FEMALE),
            ("n", FosterGender.NEUTER),
        ]

        for tag, expected_foster in test_cases:
            with self.subTest(tag=tag):
                result = apply_foster_view(
                    {
                        "dictionaries": {
                            "mw": [
                                {
                                    "id": "1",
                                    "meaning": "test",
                                    "grammar_tags": {"gender": tag},
                                }
                            ]
                        }
                    }
                )

                foster_codes = result["dictionaries"]["mw"][0]["foster_codes"]
                self.assertEqual(foster_codes["gender"], expected_foster.value)

    def test_sanskrit_number_mapping(self):
        """Test Sanskrit number mappings"""
        test_cases = [
            ("sg", FosterNumber.SINGLE),
            ("pl", FosterNumber.GROUP),
            ("du", FosterNumber.PAIR),
        ]

        for tag, expected_foster in test_cases:
            with self.subTest(tag=tag):
                result = apply_foster_view(
                    {
                        "dictionaries": {
                            "mw": [
                                {
                                    "id": "1",
                                    "meaning": "test",
                                    "grammar_tags": {"number": tag},
                                }
                            ]
                        }
                    }
                )

                foster_codes = result["dictionaries"]["mw"][0]["foster_codes"]
                self.assertEqual(foster_codes["number"], expected_foster.value)

    def test_sanskrit_combined_mapping(self):
        """Test combined Sanskrit mappings"""
        result = apply_foster_view(
            {
                "dictionaries": {
                    "mw": [
                        {
                            "id": "1",
                            "meaning": "fire",
                            "grammar_tags": {
                                "case": "1",
                                "gender": "m",
                                "number": "sg",
                            },
                        }
                    ]
                }
            }
        )

        foster_codes = result["dictionaries"]["mw"][0]["foster_codes"]
        self.assertEqual(foster_codes["case"], "NAMING")
        self.assertEqual(foster_codes["gender"], "MALE")
        self.assertEqual(foster_codes["number"], "SINGLE")

    def test_sanskrit_unknown_tag_ignored(self):
        """Test that unknown Sanskrit tags are ignored"""
        result = apply_foster_view(
            {
                "dictionaries": {
                    "mw": [
                        {
                            "id": "1",
                            "meaning": "test",
                            "grammar_tags": {"unknown_tag": "value"},
                        }
                    ]
                }
            }
        )

        entry = result["dictionaries"]["mw"][0]
        self.assertNotIn("foster_codes", entry)

    def test_sanskrit_multiple_entries(self):
        """Test Foster mapping with multiple dictionary entries"""
        result = apply_foster_view(
            {
                "dictionaries": {
                    "mw": [
                        {
                            "id": "1",
                            "meaning": "fire",
                            "grammar_tags": {"case": "1", "gender": "m", "number": "sg"},
                        },
                        {
                            "id": "2",
                            "meaning": "gods",
                            "grammar_tags": {"case": "1", "gender": "m", "number": "pl"},
                        },
                    ]
                }
            }
        )

        # First entry
        first_foster = result["dictionaries"]["mw"][0]["foster_codes"]
        self.assertEqual(first_foster["case"], "NAMING")
        self.assertEqual(first_foster["gender"], "MALE")
        self.assertEqual(first_foster["number"], "SINGLE")

        # Second entry
        second_foster = result["dictionaries"]["mw"][1]["foster_codes"]
        self.assertEqual(second_foster["case"], "NAMING")
        self.assertEqual(second_foster["gender"], "MALE")
        self.assertEqual(second_foster["number"], "GROUP")


class TestFosterIntegrationWorkflows(unittest.TestCase):
    """Test suite for complete Foster integration workflows"""

    def test_complete_diogenes_workflow(self):
        """Test complete Diogenes workflow with multiple morphs"""
        result = apply_foster_view(
            {
                "diogenes": {
                    "chunks": [
                        {
                            "chunk_type": "PerseusAnalysisHeader",
                            "morphology": {
                                "morphs": [
                                    {
                                        "stem": ["lup"],
                                        "tags": ["nom", "sg", "m"],
                                    },
                                    {
                                        "stem": ["est"],
                                        "tags": ["pres", "3", "sg", "indic"],
                                    },
                                ]
                            },
                        },
                        {
                            "chunk_type": "PerseusAnalysisHeader",
                            "morphology": {
                                "morphs": [
                                    {
                                        "stem": ["puer"],
                                        "tags": ["acc", "sg", "m"],
                                    }
                                ]
                            },
                        },
                    ]
                }
            }
        )

        # First chunk, first morph
        first_chunk_first_morph = result["diogenes"]["chunks"][0]["morphology"]["morphs"][0]
        self.assertIn("foster_codes", first_chunk_first_morph)
        expected_codes = ["NAMING", "SINGLE", "MALE"]
        for code in expected_codes:
            self.assertIn(code, first_chunk_first_morph["foster_codes"])

        # First chunk, second morph
        first_chunk_second_morph = result["diogenes"]["chunks"][0]["morphology"]["morphs"][1]
        self.assertIn("foster_codes", first_chunk_second_morph)
        expected_codes = ["TIME_NOW", "SINGLE", "STATEMENT"]
        for code in expected_codes:
            self.assertIn(code, first_chunk_second_morph["foster_codes"])

        # Second chunk, first morph
        second_chunk_first_morph = result["diogenes"]["chunks"][1]["morphology"]["morphs"][0]
        self.assertIn("foster_codes", second_chunk_first_morph)
        expected_codes = ["RECEIVING", "SINGLE", "MALE"]
        for code in expected_codes:
            self.assertIn(code, second_chunk_first_morph["foster_codes"])

    def test_complete_cltk_workflow(self):
        """Test complete CLTK Greek workflow"""
        result = apply_foster_view(
            {
                "cltk": {
                    "greek_morphology": {
                        "morphological_features": {
                            "case": "acc",
                            "tense": "aor",
                            "gender": "f",
                            "number": "pl",
                            "voice": "passive",
                            "mood": "indicative",
                        }
                    }
                }
            }
        )

        foster_codes = result["cltk"]["greek_morphology"]["foster_codes"]
        self.assertEqual(foster_codes["case"], "RECEIVING")
        self.assertEqual(foster_codes["tense"], "TIME_PAST")  # aor maps to TIME_PAST
        self.assertEqual(foster_codes["gender"], "FEMALE")
        self.assertEqual(foster_codes["number"], "GROUP")
        self.assertEqual(foster_codes["voice"], "BEING_DONE_TO")
        self.assertEqual(foster_codes["mood"], "STATEMENT")

    def test_complete_sanskrit_workflow(self):
        """Test complete Sanskrit workflow with multiple dictionaries"""
        result = apply_foster_view(
            {
                "dictionaries": {
                    "mw": [
                        {
                            "id": "1",
                            "meaning": "agni",
                            "grammar_tags": {"case": "1", "gender": "m", "number": "sg"},
                        }
                    ],
                    "cdsl": [
                        {
                            "id": "2",
                            "meaning": "fire",
                            "grammar_tags": {"case": "7", "gender": "m", "number": "sg"},
                        }
                    ],
                }
            }
        )

        # MW entry
        mw_foster = result["dictionaries"]["mw"][0]["foster_codes"]
        self.assertEqual(mw_foster["case"], "NAMING")
        self.assertEqual(mw_foster["gender"], "MALE")
        self.assertEqual(mw_foster["number"], "SINGLE")

        # CDSL entry
        cdsl_foster = result["dictionaries"]["cdsl"][0]["foster_codes"]
        self.assertEqual(cdsl_foster["case"], "IN_WHERE")  # case 7
        self.assertEqual(cdsl_foster["gender"], "MALE")
        self.assertEqual(cdsl_foster["number"], "SINGLE")

    def test_mixed_platform_workflow(self):
        """Test workflow with mixed Diogenes, CLTK, and Sanskrit data"""
        result = apply_foster_view(
            {
                "diogenes": {
                    "chunks": [
                        {
                            "morphology": {
                                "morphs": [
                                    {
                                        "stem": ["rosa"],
                                        "tags": ["nom", "sg", "f"],
                                    }
                                ]
                            }
                        }
                    ]
                },
                "cltk": {
                    "greek_morphology": {
                        "morphological_features": {
                            "case": "gen",
                            "tense": "imperf",
                            "number": "pl",
                        }
                    }
                },
                "dictionaries": {
                    "mw": [
                        {
                            "id": "1",
                            "meaning": "deva",
                            "grammar_tags": {"case": "2", "gender": "m", "number": "sg"},
                        }
                    ]
                },
            }
        )

        # Diogenes data
        diogenes_foster = result["diogenes"]["chunks"][0]["morphology"]["morphs"][0]["foster_codes"]
        self.assertIn("NAMING", diogenes_foster)
        self.assertIn("FEMALE", diogenes_foster)
        self.assertIn("SINGLE", diogenes_foster)

        # CLTK data
        cltk_foster = result["cltk"]["greek_morphology"]["foster_codes"]
        self.assertEqual(cltk_foster["case"], "POSSESSING")
        self.assertEqual(cltk_foster["tense"], "TIME_WAS_DOING")
        self.assertEqual(cltk_foster["number"], "GROUP")

        # Sanskrit data
        sanskrit_foster = result["dictionaries"]["mw"][0]["foster_codes"]
        self.assertEqual(sanskrit_foster["case"], "CALLING")  # case 2
        self.assertEqual(sanskrit_foster["gender"], "MALE")
        self.assertEqual(sanskrit_foster["number"], "SINGLE")


class TestFosterEdgeCases(unittest.TestCase):
    """Test suite for Foster grammar edge cases"""

    def test_empty_data_structures(self):
        """Test handling of empty data structures"""
        result = apply_foster_view({})
        self.assertEqual(result, {})  # Should not modify empty dict

        result = apply_foster_view(
            {
                "diogenes": {"chunks": []},
                "cltk": {},
                "dictionaries": {},
            }
        )
        # Should handle gracefully without errors
        self.assertIn("diogenes", result)
        self.assertIn("cltk", result)
        self.assertIn("dictionaries", result)

    def test_malformed_data_structures(self):
        """Test handling of malformed data structures"""
        # Malformed diogenes data
        result = apply_foster_view(
            {
                "diogenes": {
                    "chunks": [
                        {
                            "morphology": {
                                "morphs": [
                                    {"stem": ["test"]},  # Missing tags
                                    {"tags": ["nom"]},  # Missing stem
                                ]
                            }
                        }
                    ]
                }
            }
        )

        # Should not crash and should handle missing fields gracefully
        self.assertIn("diogenes", result)

        # Malformed cltk data
        result = apply_foster_view(
            {
                "cltk": {
                    "greek_morphology": {
                        "morphological_features": "invalid",  # Should be dict
                    }
                }
            }
        )

        # Should not crash
        self.assertIn("cltk", result)

        # Malformed sanskrit data
        result = apply_foster_view(
            {
                "dictionaries": {
                    "mw": [
                        {
                            "id": "1",
                            "meaning": "test",
                            "grammar_tags": "invalid",  # Should be dict
                        }
                    ]
                }
            }
        )

        # Should not crash
        self.assertIn("dictionaries", result)

    def test_case_insensitive_mapping(self):
        """Test that mappings are case-sensitive as expected"""
        # Test uppercase tags (should not match)
        result = apply_foster_view(
            {
                "diogenes": {
                    "chunks": [
                        {
                            "morphology": {
                                "morphs": [
                                    {
                                        "stem": ["test"],
                                        "tags": ["NOM", "SG", "M"],  # Uppercase
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        )

        # Should not find foster codes for uppercase tags
        morph = result["diogenes"]["chunks"][0]["morphology"]["morphs"][0]
        self.assertNotIn("foster_codes", morph)

    def test_whitespace_handling(self):
        """Test handling of whitespace in tags"""
        result = apply_foster_view(
            {
                "diogenes": {
                    "chunks": [
                        {
                            "morphology": {
                                "morphs": [
                                    {
                                        "stem": ["test"],
                                        "tags": [" nom ", " sg ", " m "],  # With whitespace
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        )

        # Should not match due to whitespace
        morph = result["diogenes"]["chunks"][0]["morphology"]["morphs"][0]
        self.assertNotIn("foster_codes", morph)

    def test_numeric_string_tags(self):
        """Test handling of numeric string tags"""
        # Sanskrit uses numeric strings for cases
        result = apply_foster_view(
            {
                "dictionaries": {
                    "mw": [
                        {
                            "id": "1",
                            "meaning": "test",
                            "grammar_tags": {"case": "1", "gender": "m", "number": "sg"},
                        }
                    ]
                }
            }
        )

        foster_codes = result["dictionaries"]["mw"][0]["foster_codes"]
        self.assertEqual(foster_codes["case"], "NAMING")
        self.assertEqual(foster_codes["gender"], "MALE")
        self.assertEqual(foster_codes["number"], "SINGLE")

    def test_partial_mappings(self):
        """Test that partial mappings are handled correctly"""
        # Some tags mapped, others not
        result = apply_foster_view(
            {
                "diogenes": {
                    "chunks": [
                        {
                            "morphology": {
                                "morphs": [
                                    {
                                        "stem": ["test"],
                                        "tags": ["nom", "unknown_tag", "sg"],
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        )

        foster_codes = result["diogenes"]["chunks"][0]["morphology"]["morphs"][0]["foster_codes"]
        # Should only contain mapped codes
        self.assertIn("NAMING", foster_codes)  # nom
        self.assertIn("SINGLE", foster_codes)  # sg
        self.assertNotIn("unknown_tag", foster_codes)


if __name__ == "__main__":
    unittest.main()
